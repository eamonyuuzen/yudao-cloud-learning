# 第 6B 步：最小 Agent 业务闭环学习工作台

> 版本：v0.3
> 日期：2026-08-01
> 状态：正式进入，先完成框架无关循环与现有 Java 工具链

## 1. 这一阶段真正要学什么

一句话：

> **不是学习“怎样调一次模型”，而是学习模型怎样在受控循环里选择一个已有业务能力，并让权限、规则、事实和证据仍由普通后端掌握。**

完成后，需要能把任何简单业务 Agent 先压缩成：

```text
用户目标
→ 模型根据工具说明提出 tool name + arguments
→ Agent 运行时匹配并执行工具
→ 工具通过正式 API 调用业务系统
→ Java 继续校验身份、权限、参数和业务规则
→ 数据库返回事实
→ 工具结果回到模型
→ 模型回答或决定下一步
→ 全程留下可检查轨迹
```

这条链里，模型拥有的是“选择和组织”能力，不拥有越权执行权。

这一阶段也不是为了押注“Agent”这个名称或某个框架。即使未来术语和框架变化，下面这些能力仍然保留：

```text
把模糊目标变成能力契约
→ 划定工具权限和数据边界
→ 让确定性系统执行动作
→ 记录状态、轨迹和失败
→ 用固定案例验证过程与结果
```

具体实现采用代表性取样：

```text
必须亲自决定：
工具解决什么问题、参数和返回是什么、谁能调用、
失败怎样表达、什么证据算完成

必须具体看懂：
一条正常工具调用链、一个失败分支、
工具名怎样匹配函数、结果怎样回到模型

可以交给 AI：
FastAPI 脚手架、重复配置、普通 HTTP 客户端代码、
格式整理、构建命令和机械测试收尾
```

完成一条可运行链并抽象出稳定模型后就停止横向扩框架；不以“读过多少 Agent 源码”判断成长。允许增加一个限时源码样本，但它必须回答当前机制问题，不得变成第二条实现主线。

## 2. 为什么选择“实习任务只读查询 Agent”

第一版项目名称：

```text
实习任务只读查询 Agent
```

示例问题：

```text
查询标题包含“用户”的进行中实习任务
```

模型需要生成：

```json
{
  "title": "用户",
  "status": 1,
  "pageNo": 1,
  "pageSize": 10
}
```

工具调用已经存在的接口：

```text
GET /admin-api/system/internship-task/page
```

选择它的原因：

1. 业务对象、状态枚举、分页、权限和 MyBatis 链路已经学过，不会同时引入新业务。
2. 参数不止一个，能真实观察模型怎样根据 Schema 生成结构化参数。
3. 接口是只读操作，错误成本低。
4. 现有 `@PreAuthorize`、Gateway、Service、Mapper 和 MySQL 都可以复用。
5. 可以自然验证 401、403、空结果、参数错误和后端不可用。

第一版明确不做：

```text
新增、编辑、删除、状态切换
→ 防止模型重试造成副作用

直接连接 MySQL
→ 防止绕开 Java 业务和权限边界

多 Agent、MCP、A2A、RAG、长期记忆
→ 它们不是证明最小工具循环所必需的
```

## 3. 两张必须同时拥有的图

### 3.1 静态角色图：谁负责什么

| 组件 | 所在位置 | 只负责什么 | 不负责什么 |
|---|---|---|---|
| 用户 / 前端 | 浏览器 | 提交自然语言和当前登录凭证 | 决定 SQL 和权限 |
| Python Agent API | Python 进程 | 接收问题、保存本次运行上下文 | 保存业务事实 |
| 模型 | 云端 API 或 Ollama | 理解意图、选择工具、填写参数、组织答案 | 直接执行 Java 或 SQL |
| Agent Runner | Python SDK | 维护消息和工具执行循环 | 替代业务规则 |
| 工具契约 | Python 函数 + Schema | 描述能力、参数和返回 | 自动证明调用安全 |
| Yudao HTTP Client | Python 适配器 | 携带 Token 调用 Gateway、翻译错误 | 自己判断业务权限 |
| Gateway | Java 进程 | 接收外部 HTTP、认证和路由 | 实习任务业务规则 |
| System Controller / Service | Java 进程 | 权限、校验、查询规则 | 自然语言理解 |
| Mapper / MySQL | Java / 数据库 | 生成查询并保存事实 | 判断 Agent 意图 |
| Trace / Eval | Agent 侧和测试 | 记录过程、判断是否稳定完成目标 | 替代权限控制 |

### 3.2 动态事件图：一次请求怎样跑

```text
用户发问：
“查询标题包含用户的进行中实习任务”

Python Agent API 收到：
问题 + 当前 Authorization
→ 把问题、工具定义交给模型

模型返回：
tool = query_internship_tasks
args = {title: "用户", status: 1, pageNo: 1, pageSize: 10}

Agent Runner 收到 tool call：
→ 按 tool name 在工具注册表找到函数
→ 先校验参数和页大小
→ 调用工具

工具调用 Yudao：
→ 把参数放入 query string
→ 把当前用户 Token 放入 Authorization
→ 请求 Gateway

Gateway 与 System：
→ Gateway 认证并路由
→ System 的 @PreAuthorize 检查 internship:task:query
→ Service 调用 Mapper
→ MySQL 返回 PageResult

工具收到结果：
→ 只保留 id、title、deadline、status 等允许字段
→ 作为 tool result 交回 Agent Runner

Agent Runner：
→ 把 tool result 追加到本次消息轨迹
→ 再次调用模型

模型：
→ 基于真实结果回答
→ 不得捏造空结果中不存在的任务
```

失败分支也必须闭合：

```text
没有 Token
→ Yudao 返回 401
→ 工具返回 UNAUTHENTICATED
→ Agent 提示重新登录，不重试写操作

没有 query 权限
→ Yudao 返回 403
→ 工具返回 FORBIDDEN
→ Agent 明确无权，不把它改写成“没有数据”

参数非法
→ 工具在发 HTTP 前拒绝，或 Yudao 返回 400
→ Agent 请求用户补充或修正

查询为空
→ 工具返回 items=[]
→ Agent 回答未找到，不编造

Gateway / System 不可用
→ 工具超时或收到 5xx
→ Agent 返回暂时不可用并结束本轮
```

## 4. 所有简单 Agent 代码共同拥有的循环

开源框架写法不同，但最小机制通常都能压缩成：

```text
messages = [用户问题]
tools = [工具名称、描述、参数 Schema]

最多循环 3 次：
    response = 调模型(messages, tools)

    如果 response 已经是最终答案：
        记录结果
        return 最终答案

    对 response 中的每个 tool call：
        根据 tool name 找到本地工具
        校验当前用户、工具白名单和参数
        执行工具
        记录工具名、参数、耗时、状态和结果摘要
        把 tool result 追加到 messages

超过最大步数：
    结束并报告“未能在限制内完成”
```

框架主要替我们封装：

```text
模型请求和响应格式
工具 Schema 生成
tool name → 本地函数匹配
消息追加与循环
会话状态
异常转换
追踪
人工确认或 Guardrail 钩子
```

真正不能外包给框架的是：

```text
业务能力是否值得开放
参数和返回字段怎样设计
谁有权调用
数据范围是什么
失败和重复怎样处理
什么证据算完成
```

## 5. 当前代码中的 Java 参考链

Yudao 已经有两种参考，不需要从空白手写 Agent 框架。

### 5.1 最简单机制样例

```text
PersonServiceImpl 的 @Tool
→ ToolCallbacks.from(personService)
→ List<ToolCallback>
→ 模型选择工具
→ ToolCallingManager 执行
```

它适合回答：

```text
@Tool 保存了什么元数据？
方法怎样变成 ToolCallback？
模型返回的名字怎样找到 Java 方法？
结果怎样回到模型？
```

它不适合直接当业务模板，因为它使用内存数据，而且同时含有写工具。

### 5.2 更接近真实业务的样例

```text
AI 角色的 toolIds
→ AiChatMessageServiceImpl 查询工具
→ ToolCallbackResolver 按名字解析
→ ChatOptions 携带 ToolCallback + ToolContext
→ UserProfileQueryToolFunction
→ AdminUserApi
→ System 服务
```

重点文件第一遍只开五个：

```text
PersonServiceImpl.java
AiAutoConfiguration.java
AiChatMessageServiceImpl.java
AiUtils.java
UserProfileQueryToolFunction.java
```

安全提醒：

`UserProfileQueryToolFunction` 是很好的机制样例，但不能未经审查就当成生产权限模板。它允许模型传入任意 `id`，而其下游 `AdminUserApiImpl#getUser` 明确关闭数据权限。学习时必须区分：

```text
源码已经能运行
≠
这个能力适合原样开放给所有 Agent 用户
```

## 6. 框架与版本决策

### Java 参考链

当前项目固定：

```text
Spring Boot 3.5.15
Spring AI 1.1.5
```

因此源码调试按 1.1.5 解释。Spring AI 2.0.0 已经 GA，但只用来理解未来推荐方向，不在本阶段升级项目。

### Python 实战链

第一版使用：

```text
FastAPI
→ 只提供一个很小的 /agent/query 入口

OpenAI Agents SDK
→ Agent、Runner、function_tool、运行轨迹

Pydantic
→ 请求、工具参数和响应约束

HTTPX
→ 携带 Authorization 调 Yudao Gateway
```

模型提供方通过配置替换：

```text
MODEL_BASE_URL
MODEL_API_KEY
MODEL_NAME
```

如果使用非 OpenAI 的 OpenAI-compatible 接口，优先走 Chat Completions 兼容路径，并验证该 Provider 是否完整支持 Tool Calling。Provider 兼容不是只改一个 URL 就自动成立。

### Pi 在本课程里替换什么

Pi 需要分三层看：

```text
pi-ai：模型 Provider 适配
pi-agent-core：消息、工具、循环、状态和事件
pi-coding-agent：终端界面、文件工具、会话和扩展等完整产品
```

如果我们把 Python Agent 改成 Node/TypeScript 服务，`pi-agent-core`
可以替换 OpenAI Agents SDK 所在的 Runner/运行时层。它不替换：

```text
模型本身
工具背后的 Java 业务 API
Token、RBAC、租户和数据范围
数据库事实
评测标准
操作系统级隔离
```

当前不切换 Python Lab，因为这会同时引入 TypeScript 实现和新的
Provider 适配。Pi 只作为“源码显微镜”：用 45～60 分钟把手写循环
映射到 `runLoop` 、工具名匹配、参数校验、`tool.execute` 和
`toolResult` 回填，然后回到 Yudao 业务链。导读见：

- [Pi Agent Core 源码迁移卡](../courseware/reference-code/step06b-pi-agent-loop.md)
- [Agent 开源仓库取样卡](../courseware/reference-code/step06b-agent-repository-sampling.md)

### “框架没必要”怎样判断

这句话的有效部分是：不要让框架遮住模型请求、tool call、
工具结果和第二次模型调用。它不等于生产中所有运行时能力都应
自己手写。按问题选择：

| 当前问题 | 优先选择 | 引入理由 |
|---|---|---|
| 学机制、单模型、单工具、短任务 | 直接 API + 显式循环 | 每个箭头都可见 |
| Python 业务 Agent，需要 Schema、追踪、Guardrail | 轻量 Agents SDK | 少写运行时机械代码 |
| Node/TypeScript 嵌入，需要透明循环和事件 | `pi-agent-core` | 核心路径直接，易于扩展 |
| 大量 Python 集成或中间件 | LangChain `create_agent` | 使用其 Provider/中间件生态 |
| 长任务、持久状态、失败恢复、人工审批 | LangGraph 或显式工作流 | 需要 checkpoint 和可恢复状态 |

框架只有在“删掉一批重复机械代码，同时不遮住调用链”时才是
收益；如果只增加新名词和调试层，就不应引入。

### 为什么当前不选 LangChain / LangGraph 作主线

第一版只有：

```text
一个 Agent
一个只读工具
一个短循环
```

这时 LangChain v1 的中间件生态和 LangGraph 的持久化、恢复、人工
中断、显式状态图都没有真实用场。这是“暂不选”，不是“框架
无用”。出现以下需求后再评估：

```text
长时间任务
多个明确分支
中间状态持久化
失败后恢复
人工审批后继续
```

### MCP 和 A2A 学到哪里

只掌握边界：

```text
MCP：
Agent / 模型应用连接工具和资源的标准协议

A2A：
独立 Agent 之间发现、委托和跟踪任务的协议
```

第一版内部只有一个工具，普通函数调用足够，不提前协议化。

## 7. 四个学习闭环

### 闭环一：先看见循环

根问题：

> 模型提出工具调用后，谁接住、怎样找到函数、结果回到哪里？

任务：

1. 用上面的框架无关伪代码手动跑一遍。
2. 用 Pi Agent Core 完成一次限时源码迁移，只定位循环、匹配、执行和回填。
3. 对照当前项目的 Spring AI 与本阶段选择的 Python SDK 最小样例。
4. 只比较它们把循环的哪些部分封装了；Pi 不安装、不重写 Lab、不展开完整 coding-agent。

证据：

- 能不说框架名，完整复述一次正常工具调用。
- 能指出工具名匹配、执行和第二次模型调用的位置。

### 闭环二：跑通 Yudao 现有 Java 工具

根问题：

> Yudao 当前版本怎样把 Java 方法暴露给模型？

任务：

1. 只读打开五个核心文件。
2. 在 AI 管理界面为角色选择一个只读 Person / Profile 工具。
3. 触发一次工具调用并观察日志、断点或响应。
4. 检查工具选择来自哪里、ToolContext 中有什么。

证据：

- 一条 `用户问题 → ToolCallback → Java 方法 → 工具结果 → 回答` 轨迹。
- 能说明 Yudao 工具角色配置和业务 RBAC 不是同一个权限层。

### 闭环三：完成实习任务只读 Agent

根问题：

> Python Agent 怎样复用已有 Java 接口，同时保留 Token 和权限链？

任务分配：

```text
用户重点亲手完成：
工具能力、参数、返回、失败语义
query_internship_tasks 的关键函数
对 401 / 403 / 空结果的预期

AI 可完成：
FastAPI 与项目脚手架
重复配置、环境变量模板
HTTP 客户端机械代码
运行命令、格式和测试收尾
```

证据：

- 一条 Python → Gateway → System → MySQL → Python → 模型的正常轨迹。
- 一条真实 403 或 401。
- 后端原有接口不因 Agent 而复制一套业务规则。

### 闭环四：用评测和轨迹收尾

根问题：

> 怎样证明 Agent 不是碰巧成功一次？

固定最小案例：

| 场景 | 主要检查 |
|---|---|
| 标题 + 状态正常查询 | 是否选择正确工具和参数，结果是否来自数据库 |
| 无匹配数据 | 是否明确返回空结果而不编造 |
| 无 Token | 是否得到 401 语义并停止 |
| 无权限 | 是否保留 403 语义而不是伪装成空数据 |
| 非法状态或超大 pageSize | 是否在工具边界拒绝 |
| System 服务不可用 | 是否超时、记录并给出可恢复回答 |
| 无关闲聊 | 是否避免不必要的业务工具调用 |

每个案例至少保存：

```text
输入
期望工具 / 不调用工具
期望参数
实际工具轨迹
最终 HTTP / 数据库结果
最终回答
耗时与错误
```

核心案例重复运行 3 次，观察选择和参数是否稳定。最终答案正确但调用了错误工具、越权或得到错误数据库状态，仍然算失败。

## 8. 完成边界

达到以下能力就结束 6B，不继续扩框架：

1. 能把自然语言需求压缩成明确的工具能力、完成边界和验收证据。
2. 能画出 Agent 工具循环并解释每个返回位置。
3. 能读懂 Yudao 当前 Java 工具链。
4. 能设计并实现一个只读工具契约。
5. 能让 Python Agent 通过正常 HTTP + Authorization 复用 Java。
6. 能区分 400、401、403、空结果、超时和模型错误。
7. 能检查轨迹和最终数据库事实。
8. 能说明 Spring AI、Python SDK、MCP、LangGraph 哪些是可替换层。
9. 能把手写循环映射到 Pi 的 `runLoop → tool.execute → toolResult`，但不依赖 Pi 术语复述机制。

暂时不要求：

```text
写操作
多 Agent
长期记忆
复杂 Planning
RAG
MCP Server
A2A
本地大模型性能优化
```

## 9. 未来扩展顺序

```text
单个只读工具稳定
→ 增加第二个只读工具
→ 观察模型是否需要两步调用
→ 出现明确状态 / 分支 / 恢复需求后引入图工作流
→ 工具需要跨多个客户端复用时引入 MCP
→ 独立 Agent 之间需要委托长任务时再看 A2A
→ 写操作最后加入审批、幂等和审计
```

这个顺序体现的不是“框架落后”，而是先让每一个新增抽象都有真实问题可解决。

## 10. 当前官方依据

- [Spring AI 2.0.0 GA](https://spring.io/blog/2026/06/12/spring-ai-2-0-0-GA-available-now/)
- [Spring AI Tool Calling](https://docs.spring.io/spring-ai/reference/api/tools.html)
- [Spring AI Effective Agents](https://docs.spring.io/spring-ai/reference/api/effective-agents.html)
- [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/)
- [OpenAI Agents SDK 非 OpenAI Provider](https://openai.github.io/openai-agents-python/models/)
- [Pi 官方仓库](https://github.com/earendil-works/pi)
- [Pi Agent Core](https://github.com/earendil-works/pi/tree/main/packages/agent)
- [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- [LangChain v1](https://docs.langchain.com/oss/python/releases/langchain-v1)
- [LangGraph 定位](https://docs.langchain.com/oss/python/langgraph/overview)
- [MCP 工具模型](https://modelcontextprotocol.io/docs/learn/server-concepts)
- [A2A 与 MCP 的边界](https://a2aproject.github.io/A2A/latest/topics/a2a-and-mcp/)
- [Anthropic Agent 评测](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
