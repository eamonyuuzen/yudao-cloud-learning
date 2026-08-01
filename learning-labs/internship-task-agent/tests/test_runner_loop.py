import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from agents import Agent, RunConfig, Runner
from agents.items import ModelResponse
from agents.models.interface import Model, ModelTracing
from agents.run_config import ToolExecutionConfig
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)

from internship_task_agent.context import AgentRequestContext
from internship_task_agent.tools import query_internship_tasks
from internship_task_agent.trace import TraceCollector
from internship_task_agent.yudao_client import YudaoClient


class TwoTurnFakeModel(Model):
    """First requests the tool, then returns a final answer."""

    def __init__(self) -> None:
        self.inputs: list[object] = []

    async def get_response(
        self,
        system_instructions: str | None,
        input: object,
        model_settings: object,
        tools: object,
        output_schema: object,
        handoffs: object,
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: object,
    ) -> ModelResponse:
        self.inputs.append(input)
        if len(self.inputs) == 1:
            output = [
                ResponseFunctionToolCall(
                    id="fake-response-id",
                    call_id="call-1",
                    name="query_internship_tasks",
                    arguments='{"title":"用户","status":1}',
                    type="function_call",
                )
            ]
        else:
            output = [
                ResponseOutputMessage(
                    id="fake-response-id",
                    type="message",
                    role="assistant",
                    status="completed",
                    content=[
                        ResponseOutputText(
                            type="output_text",
                            text="查到一条任务。",
                            annotations=[],
                            logprobs=[],
                        )
                    ],
                )
            ]
        return ModelResponse(output=output, usage=Usage(), response_id=None)

    async def stream_response(
        self,
        *_: Any,
        **__: Any,
    ) -> AsyncIterator[object]:
        if False:
            yield None
        raise NotImplementedError


@pytest.mark.asyncio
async def test_full_runner_loop_keeps_context_local_and_minimizes_result() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "list": [
                        {
                            "id": 10,
                            "title": "用户权限任务",
                            "description": "private-description",
                            "deadline": None,
                            "status": 1,
                        }
                    ],
                    "total": 1,
                },
            },
        )

    model = TwoTurnFakeModel()
    context = AgentRequestContext(
        authorization="Bearer secret-token",
        tenant_id="1",
        yudao_client=YudaoClient(
            "http://yudao.test/admin-api",
            1,
            transport=httpx.MockTransport(handler),
        ),
        trace=TraceCollector(),
    )
    agent = Agent[AgentRequestContext](
        name="runner-loop-test",
        instructions="Use the read-only task tool.",
        model=model,
        tools=[query_internship_tasks],
    )

    result = await Runner.run(
        agent,
        input="查询进行中的实习任务",
        context=context,
        max_turns=3,
        run_config=RunConfig(
            tracing_disabled=True,
            trace_include_sensitive_data=False,
        ),
    )

    second_model_input = json.dumps(
        model.inputs[1],
        ensure_ascii=False,
        default=str,
    )
    assert result.final_output == "查到一条任务。"
    assert "用户权限任务" in second_model_input
    assert "secret-token" not in second_model_input
    assert "private-description" not in second_model_input
    assert context.trace.snapshot()[0].status == "SUCCESS"


class RepeatedToolFakeModel(TwoTurnFakeModel):
    """Requests the same backend tool twice in one model turn."""

    async def get_response(
        self,
        system_instructions: str | None,
        input: object,
        model_settings: object,
        tools: object,
        output_schema: object,
        handoffs: object,
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: object,
    ) -> ModelResponse:
        if self.inputs:
            return await super().get_response(
                system_instructions,
                input,
                model_settings,
                tools,
                output_schema,
                handoffs,
                tracing,
                previous_response_id=previous_response_id,
                conversation_id=conversation_id,
                prompt=prompt,
            )
        self.inputs.append(input)
        return ModelResponse(
            output=[
                ResponseFunctionToolCall(
                    id="fake-response-1",
                    call_id="call-1",
                    name="query_internship_tasks",
                    arguments='{"page_no":1}',
                    type="function_call",
                ),
                ResponseFunctionToolCall(
                    id="fake-response-2",
                    call_id="call-2",
                    name="query_internship_tasks",
                    arguments='{"page_no":2}',
                    type="function_call",
                ),
            ],
            usage=Usage(),
            response_id=None,
        )


@pytest.mark.asyncio
async def test_full_runner_loop_enforces_one_backend_call_budget() -> None:
    backend_calls = 0

    async def handler(_: httpx.Request) -> httpx.Response:
        nonlocal backend_calls
        backend_calls += 1
        return httpx.Response(
            200,
            json={"code": 0, "data": {"list": [], "total": 0}},
        )

    model = RepeatedToolFakeModel()
    context = AgentRequestContext(
        authorization="Bearer secret-token",
        tenant_id="1",
        yudao_client=YudaoClient(
            "http://yudao.test/admin-api",
            1,
            transport=httpx.MockTransport(handler),
        ),
        trace=TraceCollector(),
    )
    agent = Agent[AgentRequestContext](
        name="runner-budget-test",
        instructions="Use the read-only task tool.",
        model=model,
        tools=[query_internship_tasks],
    )

    await Runner.run(
        agent,
        input="查询两页任务",
        context=context,
        max_turns=3,
        run_config=RunConfig(
            tracing_disabled=True,
            trace_include_sensitive_data=False,
            tool_execution=ToolExecutionConfig(
                max_function_tool_concurrency=1,
            ),
        ),
    )

    assert backend_calls == 1
    assert [entry.status for entry in context.trace.snapshot()] == [
        "SUCCESS",
        "TOOL_LIMIT_EXCEEDED",
    ]
