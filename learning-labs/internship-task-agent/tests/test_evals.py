import httpx

from evals.run_evals import inspect_result


def test_eval_rejects_wrong_tool_arguments() -> None:
    case = {
        "id": "argument-check",
        "expected_tool": "query_internship_tasks",
        "expected_tool_status": "SUCCESS",
        "expected_arguments": {"title": "用户", "status": 1},
    }
    response = httpx.Response(
        200,
        json={
            "answer": "看起来像正确答案",
            "trace": [
                {
                    "tool_name": "query_internship_tasks",
                    "arguments": {"title": "完全错误", "status": 2},
                    "status": "SUCCESS",
                }
            ],
        },
    )

    result = inspect_result(case, response)

    assert result["automatic_pass"] is False
    assert "answer" not in result
    assert result["answer_length"] == 8
