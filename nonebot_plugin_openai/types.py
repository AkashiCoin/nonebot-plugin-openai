from io import BytesIO
from pathlib import Path
import httpx
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCall,
    ChatCompletionSystemMessageParam,
)
from openai.types.image import Image
from typing import Any, Callable, Coroutine, Generic, List, Literal, Optional, TypeVar, Union
from pydantic import BaseModel


class Channel(BaseModel):
    api_key: str = ""
    base_url: Optional[str] = None
    organization: Optional[str] = None


class ToolCallResponse:
    name: str
    content_type: Literal["str", "openai_image", "image", "audio"]  # 发送给用户内容的格式
    content: Optional[Union[Any, str, Image, bytes, Path]]  # 用于发送给用户的内容
    data: str  # 用于回复给openai的内容

    def __init__(
        self,
        name: str,
        content_type: Literal["str", "openai_image", "image", "audio"],
        content: Optional[Union[Any, str, Image, bytes, Path]],
        data: str,
    ):
        self.name = name
        self.content_type = content_type
        self.content = content
        self.data = data


class ToolCallConfig(BaseModel):
    name: str
    enable: bool = True


class ToolCall:
    name: str
    func: Callable[..., Coroutine[Any, Any, ToolCallResponse]]
    func_info: dict
    config: ToolCallConfig

    def __init__(
        self,
        name: str = "",
        func: Callable[..., Coroutine[Any, Any, ToolCallResponse]] = None,
        func_info: dict = None,
        config: ToolCallConfig = ToolCallConfig(name="Unknown"),
    ):
        self.name = name
        self.func = func
        self.func_info = func_info
        self.config = config


class ToolCallRequest:
    tool_call: ChatCompletionMessageToolCall
    func: Callable[..., Coroutine[Any, Any, ToolCallResponse]]
    config: ToolCallConfig

    def __init__(
        self,
        tool_call: ChatCompletionMessageToolCall,
        func: Callable[..., Coroutine[Any, Any, ToolCallResponse]],
        config: ToolCallConfig,
    ):
        self.tool_call = tool_call
        self.func = func
        self.config = config


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
            _preset = [
                ChatCompletionSystemMessageParam(content=preset.prompt, role="system")
            ]
        return _preset + self.messages[-self.max_length :]


T = TypeVar('T', bound=ToolCallConfig)


class FuncContext(Generic[T]):
    session: Session
    http_client: httpx.AsyncClient
    openai_client: AsyncOpenAI
    config: T

    def __init__(
        self,
        session: Session,
        http_client: httpx.AsyncClient,
        openai_client: AsyncOpenAI,
        config: T,
    ):
        self.session = session
        self.http_client = http_client
        self.openai_client = openai_client
        self.config = config
