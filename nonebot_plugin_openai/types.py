from io import BytesIO
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionSystemMessageParam,
)
from openai.types.image import Image
from typing import Any, Callable, Coroutine, List, Literal, Optional, Union
from pydantic import BaseModel


class Channel(BaseModel):
    api_key: str = ""
    base_url: Optional[str] = None
    organization: Optional[str] = None


class ToolCallResponse:
    name: str
    content_type: Literal["json", "image", "audio"]
    content: Optional[Union[Any, str, dict, Image, bytes]]
    data: str

    def __init__(
        self,
        name: str,
        content_type: Literal["json", "image", "audio"],
        content: Optional[Union[Any, str, dict, Image, bytes]],
        data: str,
    ):
        self.name = name
        self.content_type = content_type
        self.content = content
        self.data = data


class ToolCall:
    name: str
    func: Callable[..., Coroutine[Any, Any, ToolCallResponse]]
    func_info: dict

    def __init__(
        self,
        name: str,
        func: Callable[..., Coroutine[Any, Any, ToolCallResponse]],
        func_info: dict,
    ):
        self.name = name
        self.func = func
        self.func_info = func_info


class ToolCallRequest:
    tool_call: ChatCompletionMessageToolCall
    func: Callable[..., Coroutine[Any, Any, ToolCallResponse]]

    def __init__(
        self,
        tool_call: ChatCompletionMessageToolCall,
        func: Callable[..., Coroutine[Any, Any, ToolCallResponse]],
    ):
        self.tool_call = tool_call
        self.func = func


class Preset(BaseModel):
    name: str
    prompt: str


class Session(BaseModel):
    id: str
    messages: List[ChatCompletionMessageParam] = []
    user: str = ""
    preset: Optional[Preset] = None
    max_length: int = 8

    def get_messages(self, preset: Preset = None):
        if self.preset:
            preset = self.preset
        _preset = []
        if preset:
            _preset =  [
                ChatCompletionSystemMessageParam(
                    content=preset.prompt, role="system"
                )
            ]
        return _preset + self.messages[-self.max_length-1:-1]
