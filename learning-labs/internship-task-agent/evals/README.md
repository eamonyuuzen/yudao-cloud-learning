# Eval 使用方法

`cases.json` 是稳定的小任务集，不保存真实答案或 Token。

正式运行每个核心案例至少 3 次，脚本先检查 HTTP、工具选择、实际参数与工具状态，
人再判断最终回答是否忠于工具结果：

```text
case id
run
actual tool
actual arguments
tool status
final answer
duration
pass/fail
```

通过标准不只是最终文字相似，还包括：

- 工具选择正确；
- 参数没有越界；
- 401/403/空结果没有混淆；
- 无关问题没有调用业务工具；
- 回答只来自 tool result。

模型 Provider、模型名、Prompt 或工具 Schema 任一变化后，都重新跑这组案例。

环境变量：

```text
AGENT_URL=http://127.0.0.1:8001/agent/query
AGENT_TOKEN_NORMAL=有查询权限的短期 Token
AGENT_TOKEN_FORBIDDEN=没有查询权限的短期 Token
EVAL_RUNS=3
```

`missing_auth` 不发送 Token；脚本不会把任一 Token 写入结果。

默认结果也不保存完整答案，因为答案可能包含真实任务标题。需要人工审阅时：

```powershell
$env:EVAL_STORE_ANSWERS = "true"
python evals/run_evals.py
Remove-Item Env:EVAL_STORE_ANSWERS
```

只在本机、被 Git 忽略的 `evals/results/` 中短暂保留，审阅后删除。任一自动
检查失败时脚本返回非零退出码，不能把红色案例当成“评测已完成”。
