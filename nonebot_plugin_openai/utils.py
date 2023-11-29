import inspect
import json
from typing import List, get_type_hints, Literal, get_args
from nonebot.adapters.onebot.v11 import MessageEvent, Message, MessageSegment
from docstring_parser import parse


def function_to_json_schema(function):
    """
    将给定的函数转换为 JSON Schema。

    这个函数会获取给定函数的签名，包括参数的名称、类型、默认值以及文档字符串，
    并将这些信息转换为 JSON Schema 格式。

    参数:
        function (function): 需要转换的函数。

    返回:
        dict: 表示函数的 JSON Schema 的字典。

    注意:
        这个函数只能处理简单的参数类型，例如 str、int、float、bool、list、dict 和 None。
        对于其他复杂的参数类型，它们将被视为 "string" 类型。
    """
    # Python类型到JSON Schema类型的映射
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        None: "null",
    }

    # 获取函数签名
    signature = inspect.signature(function)
    parameters = signature.parameters

    # 解析函数的文档字符串
    docstring = parse(function.__doc__)

    # 准备用于存储参数信息的字典
    param_properties = {}

    # 遍历每个参数
    for param_name, param in parameters.items():
        if param_name == "self":  # 忽略self参数
            continue
        if param_name == "config":  # 忽略config参数
            continue
        # 查找参数的文档字符串
        param_doc = next(
            (arg for arg in docstring.params if arg.arg_name == param_name), None
        )

        # 准备用于存储当前参数信息的字典
        param_info = {
            "type": type_mapping.get(param.annotation, "string")
            if param.annotation not in type_mapping
            else "string",  # 参数类型
            "description": param_doc.description.replace("\n", " ") if param_doc else "",  # 参数描述
        }

        # 如果参数有默认值，添加默认值信息
        if param.default != inspect.Parameter.empty:
            param_info["default"] = param.default

        # 如果参数是Literal类型，添加enum信息
        if (
            hasattr(param.annotation, "__origin__")
            and param.annotation.__origin__ is Literal
        ):
            param_info["enum"] = list(get_args(param.annotation))

        # 将参数信息添加到参数信息字典中
        param_properties[param_name] = param_info

    # 准备用于存储函数信息的字典
    function_info = {
        "type": "function",
        "function": {
            "name": function.__name__,
            "description": docstring.short_description,
            "parameters": {
                "type": "object",
                "properties": param_properties,
                "required": [
                    name
                    for name, param in parameters.items()
                    if param.default == inspect.Parameter.empty and name != "self"
                ],
            },
        },
    }

    return function_info


def get_message_imgs(event: MessageEvent) -> List[str]:
    """
    获取消息中的图片。

    这个函数会从消息中获取图片，如果消息中没有图片，它会返回 None。

    参数:
        event (MessageEvent): 消息事件。

    返回:
        List[str]: 图片的 URL。
    """
    messages = []
    urls = []
    if event.reply:
        messages.append(event.reply.message)
    messages.append(event.message)
    for message in messages:
        if isinstance(message, Message):
            for seg in message:
                if seg.type == "image":
                    urls.append(seg.data["url"].strip())
                elif seg.type == "at":
                    urls.append(f"http://q1.qlogo.cn/g?b=qq&nk={seg.data['qq']}&s=640")
        elif isinstance(message, MessageSegment):
            urls.append(message.data["url"].strip())
    return urls


def get_message_img(event: MessageEvent) -> str:
    """
    获取消息中的第一张图片。

    这个函数会从消息中获取第一张图片，如果消息中没有图片，它会返回 None。

    参数:
        event (MessageEvent): 消息事件。

    返回:
        str: 图片的 URL。
    """
    imgs = get_message_imgs(event)
    if imgs:
        return imgs[0]
    return ""


def test():
    async def gen_image(
        self,
        prompt: str,
        model: Literal["dall-e-2", "dall-e-3"] = "dall-e-3",
        quality: Literal["standard", "hd"] = "standard",
        size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
        style: Literal["vivid", "natural"] = "vivid",
    ):
        """
        Creates an image given a prompt.

        Args:
          prompt: A text description of the desired image(s). The maximum length is 1000
              characters for `dall-e-2` and 4000 characters for `dall-e-3`.

          model: The model to use for image generation.

          quality: The quality of the image that will be generated. `hd` creates images with finer
              details and greater consistency across the image. This param is only supported
              for `dall-e-3`.

          size: The size of the generated images. Must be one of `256x256`, `512x512`, or
              `1024x1024` for `dall-e-2`. Must be one of `1024x1024`, `1792x1024`, or
              `1024x1792` for `dall-e-3` models.

          style: The style of the generated images. Must be one of `vivid` or `natural`. Vivid
              causes the model to lean towards generating hyper-real and dramatic images.
              Natural causes the model to produce more natural, less hyper-real looking
              images. This param is only supported for `dall-e-3`.
        """
        pass

    print(function_to_json_schema(gen_image))


if __name__ == "__main__":
    test()
