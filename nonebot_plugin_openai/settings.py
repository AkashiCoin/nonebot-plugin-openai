import json
import os
from pathlib import Path
from pydantic import BaseModel, root_validator
from nonebot.adapters.onebot.v11 import (
    MessageEvent,
    Message,
    GroupMessageEvent,
    MessageSegment,
)
from typing import Any, List, Literal, Optional, Union, Dict

from .types import Channel, Session, Preset
from .config import config


class Settings(BaseModel):
    channels: List[Channel] = [Channel(api_key="sk-")]
    sessions: Dict[str, Session] = {}
    presets: Dict[str, Preset] = {}
    default_preset: Optional[Preset] = None

    __file_path = Path(os.path.join(config.openai_data_path, "settings.json"))
    # __file_path = Path(os.path.join("", "settings.json"))

    @property
    def file_path(self) -> Path:
        return self.__class__.__file_path

    @root_validator(pre=True)
    def init(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if cls.__file_path.is_file():
            return json.loads(cls.__file_path.read_text("utf-8"))
        return values

    def reload(self) -> None:
        self.__init__()

    def save(self) -> None:
        if not self.file_path.is_file():
            os.makedirs(self.file_path.parent, exist_ok=True)
        self.file_path.write_text(self.json(indent=4), encoding="utf-8")

    def add_preset(self, name: str, prompt: str):
        self.presets[name] = Preset(name=name, prompt=prompt)

    def get_preset(self, name: str):
        if self.presets.get(name):
            return self.presets[name]
        return None

    def del_preset(self, name: str):
        if self.presets.get(name):
            del self.presets[name]

    def get_session(self, event: MessageEvent, preset: Optional[Preset] = None) -> Session:
        _id = event.get_session_id()
        if not self.sessions.get(_id):
            session = Session(id=_id)
            self.sessions[_id] = session
            session.preset = self.default_preset
            session.max_length = config.openai_chat_max_length
        return self.sessions[_id]

    def del_session(self, event: MessageEvent):
        _id = event.get_session_id()
        if not self.sessions.get(_id):
            del self.sessions[_id]


settings = Settings()
settings.save()
