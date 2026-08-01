# Internship Task Agent Lab

一个独立于 Yudao Maven 构建的最小 Python Agent，用自然语言调用现有只读接口：

```text
POST /agent/query
→ OpenAI Agents SDK Runner
→ query_internship_tasks
→ GET Yudao /admin-api/system/internship-task/page
→ 保留 Authorization、tenant-id、401/403/空结果
```

## 1. 设计边界

- 只读，不提供新增、修改、删除和状态切换；
- 不直接连接 MySQL；
- 不保存 access token；
- Java 继续拥有参数、权限和业务事实；
- Python 只保存一次请求期间的凭证上下文；
- 每次 Agent 请求最多执行一次业务查询工具，避免模型循环放大后端压力；
- 调模型前先向 Yudao 验证当前 Token，避免无效凭证消耗模型调用；
- trace 只记录工具名、非敏感参数、耗时和结果摘要。

必须分清两个数据边界：

```text
Authorization、tenant-id
→ 只留在 Python 的请求上下文和发给 Yudao 的 Header
→ 不进入工具 Schema，不发送给模型

用户问题、模型选择的工具参数、工具返回的允许字段
→ 会进入 Runner 消息轨迹
→ 下一轮模型调用会看到
```

因此第一版工具只把 `id/title/deadline/status` 发给模型，不发送任务
`description`。真实接入前仍要确认所选 Provider 的数据使用与留存政策。

## 2. 环境

当前电脑已有 Python 3.10，可直接创建虚拟环境：

```powershell
cd learning-labs/internship-task-agent
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[test]"
Copy-Item .env.example .env
```

编辑 `.env`：

```text
MODEL_NAME=支持 Tool Calling 的模型名
MODEL_API_KEY=模型 Provider 的 API Key
MODEL_BASE_URL=Provider 的 OpenAI-compatible Base URL，可留空使用官方地址
```

不要提交 `.env`。

当前脚手架按 OpenAI Agents SDK `0.16.x` 的公开接口准备。进入本阶段时先安装
并跑测试；如 SDK 已升级，先在本实验室内适配，不要让实验性依赖侵入 Yudao
Maven 工程。

## 3. 先跑不需要真实模型的测试

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test.ps1
```

测试覆盖：

- 参数范围；
- Yudao CommonResult 拆包；
- 401/403 业务码；
- 无 Token 不发 HTTP；
- 工具结果和 trace；
- 后端超时/不可用。
- 空响应 401/403/500 的稳定映射；
- 后端畸形数据；
- HTTP 协议中断的可重试映射；
- 调模型前必须取得合法正数 `user.id` 的 Session 验证边界；
- 请求级工具调用总预算；
- 参数错误、内部错误和工具超时的稳定 trace；
- Eval 必须检查实际参数。
- 使用假模型跑完整 Runner 两轮，证明 Token 不进入模型输入、description 被裁剪。

若暂时没有模型 Key，先运行纯 Python 的循环示例：

```powershell
python examples/manual_agent_loop.py
python examples/manual_agent_loop.py --scenario unknown-tool
python examples/manual_agent_loop.py --scenario tool-error
```

它故意不用 SDK，显式展示正常、未知工具和工具异常三个分支：

```text
模型决定调用工具
→ 程序按名字找到工具并执行
→ 工具结果放回历史
→ 模型基于结果生成最终回答
```

运行前先预测两个失败会停在哪里，再用输出核对。

## 4. 启动

先启动 Yudao Gateway/System/MySQL/Redis，再运行：

```powershell
.\.venv\Scripts\python -m uvicorn internship_task_agent.api:app `
  --host 127.0.0.1 `
  --port 8001 `
  --reload
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
```

它只是 liveness：只证明 Python HTTP 进程活着，不证明模型、Gateway、
System、MySQL 都可用。真实查询前可运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\preflight.ps1
```

真实查询：

```powershell
$headers = @{
  Authorization = "Bearer <从浏览器当前请求复制的短期 Token>"
  "tenant-id" = "1"
}
$body = @{
  question = "查询标题包含用户的进行中实习任务"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri http://127.0.0.1:8001/agent/query `
  -Headers $headers `
  -ContentType "application/json" `
  -Body $body
```

## 5. 文件地图

```text
api.py
→ HTTP 入口；先验证 Header，再向 Yudao 验证 Session

agent.py
→ 创建 Agent/Runner，管理一次运行

tools.py
→ 工具契约与工具执行边界

yudao_client.py
→ 调 Gateway，翻译 CommonResult/HTTP 错误

schemas.py
→ 请求、工具参数、业务结果和 trace 结构

context.py
→ 一次 Agent 请求的短期上下文

evals/
→ 固定任务集，不把一次成功当成完成
```

## 6. Provider 兼容边界

`MODEL_BASE_URL` 只代表网络/API 形状兼容，不保证 Provider 完整支持：

- Tool Calling；
- 严格 JSON Schema；
- 多轮 tool result；
- Agents SDK tracing；
- 相同错误和 token 统计。

第一次更换 Provider 时必须重新跑固定评测集。

## 7. 真实验证

至少保存：

```text
正常查询
空结果
无 Authorization
无 query 权限
非法状态/页大小
Yudao 不可用
无关闲聊不调用工具
```

正式 Token 只用于当次本地请求，不写进文档、测试、日志或 Git。

准备好普通权限与无权限两个测试账号后，可运行：

```powershell
$env:AGENT_TOKEN_NORMAL = "<普通可查询账号的短期 Token>"
$env:AGENT_TOKEN_FORBIDDEN = "<无查询权限账号的短期 Token>"
python evals/run_evals.py
```

结果写到被 Git 忽略的 `evals/results/`；默认不记录 Token 和完整答案，只保存
脱敏 trace 与答案长度。确需本机人工复核时，可临时设置
`EVAL_STORE_ANSWERS=true`，用后立即删除结果。

## 8. 官方接口核对点

进入本阶段时重新核对：

- <https://openai.github.io/openai-agents-python/>
- <https://openai.github.io/openai-agents-python/tools/>
- <https://openai.github.io/openai-agents-python/context/>
- <https://openai.github.io/openai-agents-python/running_agents/>

本实验只使用 `Agent`、`Runner`、`function_tool`、`RunContextWrapper` 四个核心概念。
Handoff、Session、Guardrail 等能力先认识名字，不在第一轮实现。

## 9. 版本复现说明

已验证组合：

```text
Python 3.10
openai-agents 0.16.1
openai 2.40.0
```

`openai 2.49.0` 与当前 `openai-agents 0.16.1` 的 token-detail 默认值存在
运行时不兼容，哪怕导入成功，创建 Runner 上下文也会失败。因此
`pyproject.toml` 暂时精确固定 `openai==2.40.0`；升级时必须先跑完整测试，
不能只看 `pip install` 成功。
