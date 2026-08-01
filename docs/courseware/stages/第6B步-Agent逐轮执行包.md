# 第 6B 步：Agent 逐轮执行包

> 建议用时：6 个有效学习日。
> 根业务：自然语言查询实习任务，不新增写操作。
> 完整机制背景见：[第 6B 步工作台](../../stages/第6B步-最小Agent业务闭环学习工作台.md)。
> 导师答案不在用户入口中展示，由导师按提示层级解锁。

## 0. 本阶段唯一主模型

静态角色：

```text
模型：选择能力、填写参数、组织答案
Runner：维护消息和工具循环
工具：把受限能力暴露给模型
HTTP Client：运输参数和用户凭证
Gateway/System：认证、权限、业务规则
MySQL：保存业务事实
Trace/Eval：检查过程和结果
```

动态事件：

```text
用户提问
→ Runner 把问题和工具说明发给模型
→ 模型返回 tool name + arguments
→ Runner 按名字找到函数并调用
→ 函数携带当前 Authorization 请求 Yudao
→ Yudao 返回真实业务结果或明确错误
→ Runner 把 tool result 放回消息
→ 模型只根据结果回答
```

代表性比喻：

> 模型像前台接待员，工具目录像办事清单，Runner 像值班主管，Java 业务系统像真正的业务科室。前台可以判断客人该办什么，但不能绕过科室的权限和规章直接改档案。

比喻边界：Runner 不只是“转交纸条”，还维护循环、参数校验、最大步数和运行轨迹。

## 1. 第 1 日：手动跑一次工具循环

### 根问题

> 模型返回的不是最终答案，而是 tool call 时，谁先收到它？

### 先不打开源码

使用固定输入：

```text
查询标题包含“用户”的进行中实习任务
```

先运行显式循环：

```powershell
cd learning-labs/internship-task-agent
python examples/manual_agent_loop.py
python examples/manual_agent_loop.py --scenario unknown-tool
python examples/manual_agent_loop.py --scenario tool-error
```

在输出上标出“谁决定、谁调度、谁执行、谁持有事实”，再补完整：

```text
模型输入：问题 + ______
模型输出：toolName = ______，arguments = ______
第一个接住 tool call 的组件：______
它按 ______ 找到本地函数
函数结果先回到 ______
然后由 ______ 再次调用模型
```

不要先看预期答案。正常分支完成后，再口头模拟“未知工具名”和“工具抛异常”
分别停在哪里。

### Pi 源码迁移（扩展 45～60 分钟）

手写循环能复述后，打开
[Pi Agent Core 源码迁移卡](../reference-code/step06b-pi-agent-loop.md)。
只把下面五个身份与手写代码对齐：

```text
runLoop
streamAssistantResponse
prepareToolCall
tool.execute
createToolResultMessage
```

这是源码迁移练习，不是第二个 Agent 实现项目。当天不安装 Pi，
不打开 coding-agent 的 TUI/扩展/会话树源码。

### 代码观察

第一入口：[manual_agent_loop.py](../../../learning-labs/internship-task-agent/examples/manual_agent_loop.py)。

只在手工循环复述清楚后打开 Python Lab 的三个文件：

- [schemas.py](../../../learning-labs/internship-task-agent/src/internship_task_agent/schemas.py)：参数和返回契约
- [tools.py](../../../learning-labs/internship-task-agent/src/internship_task_agent/tools.py)：工具入口
- [agent.py](../../../learning-labs/internship-task-agent/src/internship_task_agent/agent.py)：Runner 与循环入口

不解释 FastAPI、HTTPX 和 Pydantic 全部语法，只回答：

1. tool name 在哪里确定？
2. 参数 Schema 从哪里来？
3. 当前用户凭证为什么不能写进工具描述？
4. tool result 的接收者是谁？

注意字段边界：

```text
模型工具参数：page_no / page_size
HTTP 查询参数：pageNo / pageSize
```

转换发生在 `YudaoClient`，两层不要混写。

### 验收

- 不说框架名，也能复述一次完整调用。
- 能区分“模型调用函数”和“Runner 根据模型结果调用函数”。
- 能说出工具描述是给模型看的元数据，不是权限系统。
- 能在 Pi 中指出“调模型 → 按名找工具 → 执行 → 回填结果”的位置。

### 停车场

Tracing 后端、模型内部如何产生 token、Pi 的 Provider/TUI/会话树源码。

## 2. 第 2 日：对照 Yudao 的 Java `@Tool`

### 根问题

> Java 方法为什么加上 `@Tool` 后就能进入模型可选能力？

### 五段闭环

```text
声明：
PersonServiceImpl 方法上的 @Tool 保存名称和描述

启动：
AiAutoConfiguration 调用 ToolCallbacks.from(personService)
→ 扫描方法元数据并生成 ToolCallback

连接：
ToolCallback 被放入模型调用选项

运行：
模型返回同名 tool call
→ Spring AI 的工具执行管理器按名字匹配 ToolCallback

结果：
ToolCallback 调用原 Java 方法
→ 返回值序列化成 tool result
→ 进入下一次模型调用
```

### 核心文件

第一入口：

1. [PersonServiceImpl.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/tool/method/PersonServiceImpl.java)

只有需要证明连接机制时再打开：

2. [AiAutoConfiguration.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/framework/ai/config/AiAutoConfiguration.java)
3. [AiUtils.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/util/AiUtils.java)
4. [Java Tool 注册证据卡](../reference-code/step06b-java-tool-registration.md)

仍不清楚时才定位 Spring AI 1.1.5 依赖或断点，不追完整源码。

### 用户任务

选 `ps_get_person_by_id`，写出：

```text
能力：
输入：
输出：
失败：
副作用：
是否适合第一版 Agent：
```

再判断 `ps_create_person` 为什么不适合第一版。

### 运行证据

先跑不调用模型的确定性测试：

```powershell
mvn -pl yudao-module-ai/yudao-module-ai-server -am `
  "-Dtest=PersonToolRegistrationTest" `
  "-Dsurefire.failIfNoSpecifiedTests=false" test
```

它证明“扫描 → 名称匹配 → JSON 参数 → 原 Java 方法”；真实模型是否会选对
工具留到第 5～6 日验证。

### 验收

能回答：

```text
谁在启动期把方法变成工具？
运行期谁先接住模型返回的名字？
按什么身份匹配？
原方法返回后先到哪里？
```

## 3. 第 3 日：Yudao 真实工具目录与安全审查

### 根问题

> 能运行的工具，为什么不一定适合开放给当前用户？

### 真实链

```text
AI 角色保存 toolIds
→ AiChatMessageServiceImpl 根据角色查询工具名
→ ToolCallbackResolver 按名称解析工具
→ ChatOptions 携带 ToolCallback + ToolContext
→ UserProfileQueryToolFunction 执行
→ AdminUserApi 调 System
```

### 核心文件

第一入口：

1. [UserProfileQueryToolFunction.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/tool/function/UserProfileQueryToolFunction.java)

按问题最多再打开四个：

2. [AiChatMessageServiceImpl.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/service/chat/AiChatMessageServiceImpl.java)
3. [AiToolServiceImpl.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/service/model/AiToolServiceImpl.java)
4. [AiUtils.java](../../../yudao-module-ai/yudao-module-ai-server/src/main/java/cn/iocoder/yudao/module/ai/util/AiUtils.java)
5. [AdminUserApiImpl.java](../../../yudao-module-system/yudao-module-system-server/src/main/java/cn/iocoder/yudao/module/system/api/user/AdminUserApiImpl.java)

### 用户审查表

| 问题 | 必须得到的证据 |
|---|---|
| 哪些工具可选？ | 角色的 `toolIds` 与解析代码 |
| 当前登录人是谁？ | `ToolContext` 的 `LoginUser` 来源 |
| tenantId 在哪恢复？ | `AiUtils` 与 `TenantUtils.execute` |
| 任意 userId 是否可查？ | Request 的 `id` 与下游 API |
| 业务数据权限是否保留？ | `AdminUserApiImpl#getUser` 的注解/实现 |

### 本轮关键纠偏

```text
AI 角色允许使用某工具
≠
当前业务用户有权查询工具参数指定的所有数据
```

这是两层权限：

```text
工具目录权限：这个 Agent 能不能选择此能力
业务数据权限：当前人能不能对这条数据执行此动作
```

### 验收

提出一个更安全的用户资料工具契约，例如：

```text
query_my_profile()
```

而不是允许模型任意传 `userId`。

## 4. 第 4 日：定义实习任务工具契约

### 根问题

> 在写 SDK 代码前，怎样把自然语言能力变成可审查的契约？

### 用户必须亲自定稿

```text
工具名：
query_internship_tasks

能力：
按标题和状态分页调用 Yudao 的实习任务查询接口。

参数：
title        可空，最大 200 字符
status       可空，只允许 0/1/2
page_no      默认 1，最小 1
page_size    默认 10，范围 1～50

返回：
total
items[id, title, deadline, status]

权限：
必须携带当前请求的 Authorization 和 tenant-id，
由 Yudao 继续验证登录、租户和 internship:task:query。

当前数据范围事实：
有 query 权限的用户可查看本租户全部实习任务；
尚未实现“仅本人、认领人或部门”的任务行级数据权限。

失败：
INVALID_ARGUMENT
TOOL_LIMIT_EXCEEDED
UNAUTHENTICATED
FORBIDDEN
BACKEND_UNAVAILABLE
BACKEND_ERROR

副作用：
无
```

请用 [工具契约卡模板](../templates/工具契约卡模板.md) 先决定：

- 是否接受“本租户全部”，还是新增本人/部门范围；
- 哪些任务字段允许进入外部模型上下文；
- 模型轮次、工具调用总数、并发数、工具超时和总超时预算。

### 为什么参数不直接叫 `request`

模型需要看见每个字段的语义、类型和范围。一个模糊 `request` 会让 Schema 失去约束，也让评测无法检查具体参数。

### 为什么工具不直接查 MySQL

```text
直接查库
→ 绕过 Gateway、Token、@PreAuthorize、Service 规则和统一错误

调用正式 HTTP API
→ Agent 与普通前端共享同一业务边界
```

### 用户决策，AI 映射

用户决定字段、范围、权限和错误语义；AI 将已定稿契约机械映射为
`QueryInternshipTasksArgs`、错误模型和 JSON Schema。用户最后审查生成的
Schema，不要求手抄整个 DTO。

### 验收

分成两类证据：

模型行为评测 5 个：

1. 标题 + 状态正常查询；
2. 无匹配；
3. 无 Token；
4. 无权限；
5. 与实习任务无关的闲聊。

确定性 Schema 单测 2 个：

1. `status=99`；
2. `page_size=1000`。

## 5. 第 5 日：跑通 Python → Yudao

### 根问题

> Python 进程怎样代表“当前用户”调用 Java，而不是变成一个万能系统账号？

### 进程拓扑

```text
浏览器/curl
→ Python :8001
→ 模型 Provider
→ Python Tool
→ Yudao Gateway :48080
→ System
→ MySQL
```

### 只看五个 Lab 文件

1. [api.py](../../../learning-labs/internship-task-agent/src/internship_task_agent/api.py)
2. [agent.py](../../../learning-labs/internship-task-agent/src/internship_task_agent/agent.py)
3. [tools.py](../../../learning-labs/internship-task-agent/src/internship_task_agent/tools.py)
4. [yudao_client.py](../../../learning-labs/internship-task-agent/src/internship_task_agent/yudao_client.py)
5. [schemas.py](../../../learning-labs/internship-task-agent/src/internship_task_agent/schemas.py)

开始前先运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\preflight.ps1 -RequireLive
```

### 用户重点实现或审查

`tools.py` 中的关键逻辑：

```text
收到经过 Schema 校验的参数
→ 从 RunContext 取当前 Authorization/tenantId
→ 检查本请求是否还有工具调用预算
→ 调 YudaoClient
→ 保留业务错误类型
→ 记录工具轨迹
→ 返回允许字段
```

Agent HTTP 入口还会在调用模型前向
`/system/auth/get-permission-info` 验证 Session。后端工具调用时仍再次验证业务
权限，两者不是重复浪费：

```text
入口验证：阻止无效 Token 消耗模型费用
工具后端验证：保护每次真实业务读取
```

数据外发边界：

```text
Token 不发给模型
≠
工具结果不发给模型
```

Runner 会把允许字段的 tool result 发回模型，因此第一版不返回 `description`。

### AI 可自动处理

- FastAPI 启动；
- Pydantic 配置；
- HTTPX 超时；
- `.env.example`；
- pytest 的 MockTransport；
- 导包和格式。

### 正常验证

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8001/agent/query `
  -Headers @{
    Authorization = "Bearer <当前浏览器 Token>"
    "tenant-id" = "1"
  } `
  -ContentType "application/json" `
  -Body '{"question":"查询进行中的实习任务"}'
```

成功标志：

- Python trace 出现 `query_internship_tasks`；
- Yudao 收到正常 Authorization；
- HTTP 调用了 `/admin-api/system/internship-task/page`；
- 最终结果能与浏览器/数据库对齐。

### 失败验证

去掉 Authorization，再使用无权限角色，各跑一次。

必须区分：

```text
401：没有可用身份
403：身份存在但不允许执行
空列表：允许执行，只是没有数据
```

## 6. 第 6 日：评测、故障与收口

### 根问题

> 最终答案看起来正确，为什么仍可能是一次失败运行？

### 固定评测

使用 `evals/cases.json`，每个核心案例运行 3 次。检查：

```text
是否应该调用工具
实际工具名
实际参数
工具结果状态
最终回答是否只使用工具事实
耗时
```

错误示例：

- 回答正确，但调用了不该调用的写工具；
- 把 403 说成“没有数据”；
- `page_size` 超界但仍请求后端；
- 后端超时后编造任务；
- 闲聊也调用业务工具；
- 多次运行参数含义漂移。

脚本必须比较 `expected_arguments`；工具名正确但 `title/status` 错误不能判为
通过。默认结果不保存完整答案，任一自动检查失败时退出码非零。

### 故障实验

关闭 Yudao System 或改错 `YUDAO_BASE_URL`：

```text
观察超时/连接失败
→ 工具映射为 BACKEND_UNAVAILABLE
→ Runner 不无限循环
→ 最终答案明确“暂时无法查询”
```

### 三种实现压缩

| 机制 | Pi Agent Core | Spring AI | Python SDK | 稳定抽象 |
|---|---|---|---|---|
| 工具声明 | `AgentTool` | `@Tool` / Function | `@function_tool` | 名称、描述、Schema |
| 工具注册 | `context.tools` | `ToolCallback` | Agent tools | 工具目录 |
| 循环执行 | `runLoop` | ToolCallingManager | Runner | 调模型→执行→回填 |
| 请求上下文 | 应用自定义 | ToolContext | RunContext | 用户身份与请求状态 |
| 业务事实 | Java API | Java API | Java API | 确定性后端 |

### 完成标准

用户不看笔记只先回答三道主问题：

1. 从自然语言到 Java 业务事实，谁决定、谁按名称调度、谁真正执行？
2. Token、工具参数和工具结果分别对谁可见，权限/租户/数据范围在哪层裁决？
3. 用 401、403、空结果或超时中的一个失败分支，说明为什么还要检查轨迹而
   不能只看最终答案。

其余细节由导师根据回答逐个追问，不一次铺成八题问卷。

完成后按 [第 6B 步基线与冷启动](../evaluations/第6B步基线与冷启动.md)
做 24 小时和 7 天复测。

## 7. 第 6B 步结束后补 6A 欠账

只用 1～2 日完成：

```text
pnpm build 生成 dist
→ Nginx 提供静态文件并代理 /admin-api
→ Compose 描述 MySQL/Redis/Nacos 等依赖
→ 浏览器完成真实查询
```

Agent 的 Python 服务暂不要求加入 Compose；先把普通前后端交付链补齐。
