import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, parse_file_as, root_validator


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
    a_list: List[ToolCallConfig] = []
    string: str = "test"

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

    def reload(self):
        if self.file_path.is_file():
            new_self = parse_file_as(self.__class__, self.file_path)
            for key, value in new_self.dict().items():
                self_value = getattr(self, key)
                if isinstance(value, dict):
                    self_value.clear()
                    self_value.update(getattr(new_self, key))
                elif isinstance(value, list):
                    self_value.clear()
                    self_value.extend(getattr(new_self, key))
                else:
                    setattr(self, key, getattr(new_self, key))


tools_func = ToolsFunction()

tools_func.a_list.append(ToolCallConfig(name="test"))
print(tools_func)
print(id(tools_func.a_list))
tools_func.save()
tools_func.a_list.clear()
tools_func.string = "test2"
# After some changes in the file, you can reload the data
tools_func.reload()
print(tools_func)
print(id(tools_func.a_list))
tools_func.a_list.pop()
tools_func.save()
