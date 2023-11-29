import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, root_validator


class ToolCallConfig(BaseModel):
    name: str
    enable: bool = True


class FuncGoogleSearchConfig(ToolCallConfig):
    name: str
    enable: bool
    api_key: str
    cx_key: Optional[str]


class ToolsFunction(BaseModel):
    tool_config: Dict[str, Union[Dict, ToolCallConfig]] = {}

    __file_path = Path(__file__).parent / "data.json"

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

tools_func = ToolsFunction()
print(tools_func)