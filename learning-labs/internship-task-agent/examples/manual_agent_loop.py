"""A dependency-free model of the Agent loop.

This is deliberately not an LLM simulation. It only exposes the control flow
that an SDK later packages for us.
"""

import argparse
from collections.abc import Callable
from typing import Any


def query_internship_tasks(title: str) -> dict[str, Any]:
    """Fake business tool used only to make the loop visible."""

    return {
        "list": [{"id": 7, "title": f"{title}权限学习", "status": 1}],
        "total": 1,
    }


def failing_query_internship_tasks(title: str) -> dict[str, Any]:
    raise RuntimeError(f"模拟后端暂时不可用：{title}")


TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "query_internship_tasks": query_internship_tasks,
    "failing_query_internship_tasks": failing_query_internship_tasks,
}


def fake_model(
    history: list[dict[str, Any]],
    scenario: str,
) -> dict[str, Any]:
    """Return one model decision based on the current history."""

    if not any(item["role"] == "tool" for item in history):
        tool_name = {
            "normal": "query_internship_tasks",
            "unknown-tool": "missing_tool",
            "tool-error": "failing_query_internship_tasks",
        }[scenario]
        return {
            "type": "tool_call",
            "name": tool_name,
            "arguments": {"title": "用户"},
        }
    tool_result = next(item["content"] for item in history if item["role"] == "tool")
    return {
        "type": "final",
        "content": f"查到 {tool_result['total']} 条任务："
        f"{tool_result['list'][0]['title']}",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario",
        choices=("normal", "unknown-tool", "tool-error"),
        default="normal",
    )
    args = parser.parse_args()

    history: list[dict[str, Any]] = [
        {"role": "user", "content": "查询标题包含用户的实习任务"}
    ]

    while True:
        decision = fake_model(history, args.scenario)
        print("模型决定：", decision)

        if decision["type"] == "final":
            print("最终回答：", decision["content"])
            return

        tool = TOOLS.get(decision["name"])
        if tool is None:
            print("调度失败：工具目录中没有这个 name；程序不会凭空执行函数。")
            return
        try:
            tool_result = tool(**decision["arguments"])
        except Exception as exc:
            print("执行失败：Runner 应把稳定错误放回轨迹，而不是编造结果。")
            print("本次模拟错误类型：", type(exc).__name__)
            return
        print("程序执行工具：", decision["name"], tool_result)
        history.append(
            {
                "role": "tool",
                "name": decision["name"],
                "content": tool_result,
            }
        )


if __name__ == "__main__":
    main()
