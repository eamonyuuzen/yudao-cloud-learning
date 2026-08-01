# Step 06B Agent 开源仓库取样卡

```text
状态：SOURCE-READING
调研日期：2026-08-01
目标：为当前根问题选一个代表样本，不按热度同时学多个框架
```

## 1. 取样顺序

```text
自己的显式循环
→ 先建立最小机制模型

Pi Agent Core
→ 看真实运行时怎样实现循环、工具匹配和事件

OpenAI Agents SDK Python Lab
→ 完成 Python → Yudao 的真实业务闭环

Triple-pi
→ 最小闭环稳定后，看记忆、审查、并发和评测怎样变成工程系统

LangGraph 或其他编排框架
→ 真实出现持久状态、恢复、人工审批后再学
```

这是“同一模型逐级放大”，不是框架横向收集。

## 2. Triple-pi 适合借鉴什么

仓库：[Triple-pi](https://github.com/npm-DreaMaX/Triple-pi)

它不是 Pi 的最小教程，而是一个基于 Pi 扩展的作品：

```text
Pi 上游
→ Agent loop、模型、会话、扩展钩子

Triple-pi Memory
→ 跨会话记忆提取、证据、校验、合并和存储

Triple-pi Reviewer
→ 收集 Git diff、检索规则、运行隔离审查、校验结果
```

当前课程只借鉴五个设计：

1. **先分上游与自研边界**：不把 Pi 提供的 Agent loop 宣称为业务层自研。
2. **结论带证据与来源**：模型生成的长期记忆必须能追溯到原对话。
3. **fail-closed**：提取、校验或存储任一失败时，不把未验证内容当成成功。
4. **三层评测**：确定性单测、recorded/fake-model 全链接线、真实模型评测分开。
5. **权限用程序限制**：Reviewer 只注册读工具，并在前后比较工作树，不只靠 prompt 说“请勿修改”。

与本路线的映射：

| Triple-pi 样本 | 当前或未来阶段 |
|---|---|
| recorded/live eval 分层 | 6B 评测收尾 |
| 证据和 provenance | 6B 轨迹、未来数据治理血缘 |
| 补偿式批量写入 | 第 7 步事务边界对照 |
| scheduler / branch fencing | 第 8 步异步与并发 |
| 内容寻址幂等与锁 | 第 9 步 Redis/幂等对照 |
| 长期记忆和隔离 Reviewer | 第 15 步候选案例 |

暂时不做：

```text
不把 Triple-pi 安装到当前 Yudao 学习环境
不在 6B 实现长期记忆或 Reviewer 子 Agent
不通读它的全部技术教材
不用它的 pi-runtime fork 代替 Pi 官方源码作底层事实
```

## 3. GitHub 仓库怎样借鉴

| 仓库 | 本路线用途 | 不采用的部分 |
|---|---|---|
| [Pi](https://github.com/earendil-works/pi) | 核心循环源码事实 | 不通读完整 coding-agent |
| [Pi Tutorial](https://github.com/earendil-works/pi-tutorial) | 需要熟悉 Pi 扩展操作时候选 | 它是 Pi 使用引导，不是 Agent loop 教材 |
| [OpenAI Agents SDK Python](https://github.com/openai/openai-agents-python) | 当前 Python 业务实现与 tracing | 不学全部多 Agent/语音能力 |
| [Anthropic Cookbook](https://github.com/anthropics/anthropic-cookbook) | 手动 tool loop、工具契约和模式 | 不把 Provider 特有语法当稳定抽象 |
| [AI Agents for Beginners](https://github.com/microsoft/ai-agents-for-beginners) | 查缺补漏的概念索引 | 不按课表全量学，不转向 Azure 主线 |
| [smolagents](https://github.com/huggingface/smolagents) | 6B 后按需比较 JSON tool call 与 code agent | 不在最小闭环同时引入 |
| [Triple-pi](https://github.com/npm-DreaMaX/Triple-pi) | 工程化记忆、审查和评测案例 | 不当 Pi 官方教程，不作 6B 起点 |

## 4. 判断一个热门仓库是否进课程

只问五个问题：

1. 它能回答哪个当前根问题？
2. 它展示的是角色图、真实运行时链，还是一个完整产品？
3. 哪些是上游能力，哪些是它自己的设计？
4. 是否有测试、失败语义、边界和可复算证据？
5. 读完后应该回到哪条业务主线？

不能明确回答第 1 和第 5 题时，只收藏链接，不进当前课程。
