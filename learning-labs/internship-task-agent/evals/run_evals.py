"""Run the stable local eval set without persisting credentials."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent


def load_cases() -> list[dict[str, Any]]:
    return json.loads((ROOT / "cases.json").read_text(encoding="utf-8"))


def token_for(credential: str) -> str | None:
    if credential == "missing":
        return None
    variable = {
        "normal": "AGENT_TOKEN_NORMAL",
        "forbidden": "AGENT_TOKEN_FORBIDDEN",
    }[credential]
    token = os.getenv(variable, "").strip()
    if not token:
        raise RuntimeError(f"缺少环境变量 {variable}")
    return token


def inspect_result(case: dict[str, Any], response: httpx.Response) -> dict[str, Any]:
    expected_http = int(case.get("expected_http_status", 200))
    passed = response.status_code == expected_http
    body: dict[str, Any]
    try:
        body = response.json()
    except ValueError:
        body = {"raw": response.text[:500]}
        passed = False

    trace = body.get("trace") if isinstance(body, dict) else None
    trace = trace if isinstance(trace, list) else []
    expected_tool = case.get("expected_tool")

    if expected_http == 200:
        matching_traces = [
            item
            for item in trace
            if item.get("tool_name") == expected_tool
        ]
        actual_tools = [item.get("tool_name") for item in trace]
        if expected_tool is None:
            passed = passed and not actual_tools
        else:
            passed = passed and bool(matching_traces)

        expected_status = case.get("expected_tool_status")
        if expected_status:
            passed = passed and any(
                item.get("status") == expected_status
                for item in matching_traces
            )

        expected_arguments = case.get("expected_arguments")
        if expected_arguments:
            passed = passed and any(
                all(
                    item.get("arguments", {}).get(key) == value
                    for key, value in expected_arguments.items()
                )
                for item in matching_traces
            )

    result = {
        "case_id": case["id"],
        "http_status": response.status_code,
        "trace": trace,
        "automatic_pass": passed,
        "human_rule": case.get("expected_answer_rule"),
    }
    answer = body.get("answer") if isinstance(body, dict) else None
    result["answer_length"] = len(answer) if isinstance(answer, str) else 0
    if os.getenv("EVAL_STORE_ANSWERS", "").lower() in {"1", "true", "yes"}:
        result["answer"] = answer
    return result


def main() -> None:
    url = os.getenv(
        "AGENT_URL",
        "http://127.0.0.1:8001/agent/query",
    )
    runs = max(1, int(os.getenv("EVAL_RUNS", "3")))
    results: list[dict[str, Any]] = []

    with httpx.Client(timeout=60) as client:
        for case in load_cases():
            for run in range(1, runs + 1):
                headers = {"tenant-id": "1"}
                token = token_for(case["credential"])
                if token:
                    headers["Authorization"] = f"Bearer {token}"
                response = client.post(
                    url,
                    headers=headers,
                    json={"question": case["question"]},
                )
                result = inspect_result(case, response)
                result["run"] = run
                results.append(result)
                print(
                    f"{case['id']} run={run} "
                    f"automatic_pass={result['automatic_pass']}"
                )

    output_dir = ROOT / "results"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = output_dir / f"{timestamp}.json"
    output.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"脱敏结果：{output}")
    if not all(result["automatic_pass"] for result in results):
        print("存在自动检查失败的案例。", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
