import json
from typing import Dict, Callable, Union, Coroutine, Any
from openai.types.chat import (
    ChatCompletionMessageToolCall,
    ChatCompletionToolMessageParam,
    ChatCompletionContentPartImageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionFunctionMessageParam,
)

from .utils import function_to_json_schema
from .types import Session, ToolCall, ToolCallResponse


class ToolsFunction:
    tools: Dict[str, ToolCall]

    def __init__(self):
        self.tools = {}

    def register(
        self,
        func: Callable[
            ..., Union[ToolCallResponse, Coroutine[Any, Any, ToolCallResponse]]
        ],
    ):
        tool_info = function_to_json_schema(func)
        self.tools[tool_info["function"]["name"]] = ToolCall(
            name=tool_info["function"]["name"],
            func=func,
            func_info=tool_info,
        )

    def get(self, name) -> ToolCall:
        return self.tools.get(name)

    def __call__(self, name):
        return self.get(name)

    def tools_info(self):
        return list(tool_call.func_info for tool_call in self.tools.values())

    async def call_function(
        self, function_call: ChatCompletionFunctionMessageParam, session: Session
    ):
        tool = self.tools.get(function_call.name)
        if tool:
            result = await tool.func(**json.loads(function_call.arguments))
            session.messages.append(
                ChatCompletionFunctionMessageParam(
                    role="function",
                    name=function_call.name,
                    content=result.data,
                )
            )
            return result
        return ToolCallResponse(
            name=function_call.name,
            content_type="json",
            content=None,
            data=f"failed, tool({function_call.name}) not found",
        )

    async def call_tool(
        self, tool_call: ChatCompletionMessageToolCall, session: Session
    ):
        tool = self.tools.get(tool_call.function.name)
        if tool:
            kwargs = json.loads(tool_call.function.arguments)
            result = await tool.func(**kwargs)
            session.messages.append(
                ChatCompletionToolMessageParam(
                    tool_call_id=tool_call.id,
                    role="function",  # OpenAI中，使用tool会报错 Invalid parameter: messages with role 'tool' must be a response to a preceeding message with 'tool_calls'
                    name=tool_call.function.name,
                    content=result.data,
                )
            )
            return result
        return ToolCallResponse(
            name=tool_call.function.name,
            content_type="json",
            content=None,
            data=f"failed, tool({tool_call.function.name}) not found",
        )


tools_func = ToolsFunction()
