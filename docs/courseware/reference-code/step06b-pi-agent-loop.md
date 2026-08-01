# Step 06B Pi Agent Core 源码迁移卡

```text
状态：SOURCE-READING
快照日期：2026-08-01
时间上限：45～60 分钟
目标：用一个透明的工业化源码样本，证明手写 Agent loop 如何变成真实运行时
```

## 1. 先分清 Pi 的三层

```text
pi-ai
→ 统一不同模型 Provider 的请求和响应

pi-agent-core
→ 管理消息、工具调用、循环、状态和事件

pi-coding-agent
→ 把核心变成可使用的终端编码产品
```

本卡只读 `pi-agent-core`。不学 TUI、主题、快捷键、完整会话树和扩展市场。

## 2. 它可以替换哪一层

```text
用户问题
→ [Agent Runner / Runtime]  ← pi-agent-core 可替换这一层
→ 业务工具
→ Yudao Gateway / System
→ MySQL
```

它不替换模型、Yudao 业务 API、RBAC、数据范围和评测标准。
Pi 官方也明确说明：完整 coding agent 默认继承启动进程的文件、
网络、进程和凭证权限，不自带操作系统级权限沙箱。工具调用钩子不等于强隔离。

## 3. 一条可执行的源码路线

第一入口：

- [`packages/agent/src/agent-loop.ts`](https://github.com/earendil-works/pi/blob/main/packages/agent/src/agent-loop.ts)

只按下面顺序定位：

```text
agentLoop / runAgentLoop
→ 把用户消息加入 context，发出 agent_start / turn_start

runLoop
→ 调模型
→ 判断是最终答案还是 toolCall
→ 有 toolCall 就执行，再开下一轮

streamAssistantResponse
→ 把 AgentMessage 转成模型消息
→ 调 Provider
→ 收集流式文本或 toolCall

prepareToolCall
→ 按 toolCall.name 在 context.tools 中查找
→ 校验 arguments
→ 执行 beforeToolCall，可以拒绝

executePreparedToolCall
→ 真正调用 tool.execute(...)
→ 捕获工具错误

createToolResultMessage
→ 生成 role=toolResult 的消息
→ 追加到 context.messages
→ runLoop 再次调模型
```

只在“谁保存状态、谁收到运行时事件”仍不清楚时，再打开：

- [`packages/agent/src/agent.ts`](https://github.com/earendil-works/pi/blob/main/packages/agent/src/agent.ts)
- [`packages/agent/src/types.ts`](https://github.com/earendil-works/pi/blob/main/packages/agent/src/types.ts)

## 4. 与手写循环逐项对齐

| 手写模型 | Pi 中的实现身份 |
|---|---|
| `messages` | `AgentContext.messages` |
| `while` / 最大轮次 | `runLoop` / 外部停止配置 |
| `call_model(messages, tools)` | `streamAssistantResponse` |
| `tools[tool_name]` | `currentContext.tools.find(...)` |
| 校验参数 | `validateToolArguments` |
| 执行工具 | `tool.execute(...)` |
| 记录工具结果 | `ToolResultMessage` |
| 再调模型 | `toolResult` 进入 messages 后回到 `runLoop` |

## 5. 只需回答的五个问题

1. 真正收到模型 `toolCall` 的是谁？
2. 它根据什么找到具体工具？
3. 参数在什么时候校验？
4. 工具结果先回给谁，为什么还要再调一次模型？
5. `beforeToolCall` 能拒绝一次工具执行，为什么仍不能替代 Yudao RBAC 或操作系统沙箱？

## 6. 停止条件

能不看 Pi 名词复述：

```text
运行时收到模型的工具请求
→ 按工具名找实现
→ 校验与执行
→ 把结果记为新消息
→ 再请模型组织答案或选择下一步
```

到这里立即回到 Python 实习任务 Agent。不克隆 Pi，不把 Lab 改写为
TypeScript，不逐行阅读完整 `agent.ts`。

## 7. 官方依据

- [Pi 官方仓库与包分层](https://github.com/earendil-works/pi)
- [Pi Agent Core 说明](https://github.com/earendil-works/pi/tree/main/packages/agent)
- [Pi 扩展机制](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md)
