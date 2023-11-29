import importlib
import json
import os
import shutil

from pathlib import Path
from typing import Dict, Callable, Optional, Union, Coroutine, Any
from loguru import logger
from openai.types.chat import (
    ChatCompletionMessageToolCall,
    ChatCompletionToolMessageParam,
    ChatCompletionContentPartImageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionContentPartTextParam,
    ChatCompletionFunctionMessageParam,
)
from pydantic import BaseModel, parse_file_as, root_validator

from .utils import function_to_json_schema, reload
from .config import config
from .types import Session, ToolCall, ToolCallConfig, ToolCallResponse, FuncContext


class ToolsFunction(BaseModel):
    __tools = {}
    tool_config: Dict[str, Union[Dict, ToolCallConfig]] = {}

    __file_path = Path(os.path.join(config.openai_data_path, "tool_config.json"))

    @property
    def file_path(self) -> Path:
        return self.__class__.__file_path

    def save(self) -> None:
        if not self.file_path.is_file():
            os.makedirs(self.file_path.parent, exist_ok=True)
        self.file_path.write_text(self.json(indent=4), encoding="utf-8")

    @root_validator(pre=True)
    def init(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if cls.__file_path.is_file():
            return json.loads(cls.__file_path.read_text("utf-8"))
        return values

    def reload(self):
        reload(self)

    @property
    def tools(self) -> Dict[str, ToolCall]:
        return self.__tools

    def register(
        self,
        func: Callable[
            ..., Union[ToolCallResponse, Coroutine[Any, Any, ToolCallResponse]]
        ],
        config: ToolCallConfig = ToolCallConfig(name="Unknown"),
    ):
        tool_info = function_to_json_schema(func)
        func_name = tool_info["function"]["name"]
        if func_name in self.tool_config:
            config = config.parse_obj(self.tool_config[func_name])
        self.tool_config[tool_info["function"]["name"]] = config
        self.tools[func_name] = ToolCall(
            name=tool_info["function"]["name"],
            func=func,
            func_info=tool_info,
            config=config,
        )
        logger.info(f"[Function] 注册 {config.name} 函数 {func_name} 成功.")

    def tool_names(self):
        return list(self.tools.keys()).extend(
            [tool.config.name for tool in self.tools.values()]
        )

    def get_tool_from_name(self, name: str) -> Optional[ToolCall]:
        if name in self.tools:
            return self.tools[name]
        for tool in self.tools.values():
            if tool.config.name == name:
                return tool
        return None

    def is_registered(self, func_name: str) -> bool:
        return func_name in self.tool_names()

    def disable(self, func_name: str) -> None:
        tool = self.get_tool_from_name(func_name)
        if tool:
            tool.config.enable = False
            self.save()

    def enable(self, func_name: str) -> None:
        tool = self.get_tool_from_name(func_name)
        if tool:
            tool.config.enable = True
            self.save()

    def is_enabled(self, func_name: str) -> bool:
        tool = self.get_tool_from_name(func_name)
        if tool:
            return tool.config.enable
        return False

    def enabled_func_names(self):
        return list(
            f"{tool.config.name}({tool.name})"
            for tool in self.tools.values()
            if tool.config.enable
        )

    def disabled_func_names(self):
        return list(
            f"{tool.config.name}({tool.name})"
            for tool in self.tools.values()
            if not tool.config.enable
        )

    def get(self, name) -> ToolCall:
        return self.tools.get(name)

    def __call__(self, name):
        return self.get(name)

    def tools_info(self):
        return list(
            tool.func_info for tool in self.tools.values() if tool.config.enable
        )

    async def call_function(
        self,
        function_call: ChatCompletionFunctionMessageParam,
        session: Session,
        ctx: FuncContext[ToolCallConfig],
    ):
        tool = self.tools.get(function_call.name)
        if tool:
            kwargs = json.loads(function_call.arguments)
            kwargs["ctx"] = ctx
            result = await tool.func(**kwargs)
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
            content_type="str",
            content=None,
            data=f"failed, tool({function_call.name}) not found",
        )

    async def call_tool(
        self,
        tool_call: ChatCompletionMessageToolCall,
        session: Session,
        ctx: FuncContext[ToolCallConfig],
    ):
        tool = self.tools.get(tool_call.function.name)
        if tool:
            kwargs = json.loads(tool_call.function.arguments)
            kwargs["ctx"] = ctx
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
            content_type="str",
            content=None,
            data=f"failed, tool({tool_call.function.name}) not found",
        )


tools_func = ToolsFunction()
