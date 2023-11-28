from pathlib import Path
from typing import List, Literal, Optional, Union

from nonebot import get_driver
from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    openai_base_url: str = "https://api.openai.com/v1"
    openai_data_path: str = "data/nonebot_plugin_openai/"
    openai_default_model: str = "gpt-3.5-turbo-1106"
    openai_chat_max_length: int = 8


config = Config.parse_obj(get_driver().config)
