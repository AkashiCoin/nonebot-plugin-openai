from httpx import AsyncClient
from loguru import logger
from . import ToolCallResponse, ToolCallConfig, tools_func, FuncContext
from typing import Literal


class Config(ToolCallConfig):
    name: str = "MoeGoe TTS"


async def func_moegoe_tts(
    ctx: FuncContext[Config], text: str, speak_id: Literal[0, 1, 2, 3, 4, 5] = 0
):
    """
    This function is a Text-to-Speech (TTS) function that converts Japanese text into speech.

    Args:
        text (str): The Japanese text to be converted into speech.
        speak_id (Literal[0, 1, 2, 3, 4, 5], optional): The ID of the speaker voice to use. Defaults to 0.

    Returns:
        ToolCallResponse: An instance of ToolCallResponse class which contains the name, content type, content, and data of the response.

    Raises:
        Exception: If there is an error in the TTS conversion or in parsing the response.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63"
    }

    url = "https://moegoe.azurewebsites.net/api/speak"
    config = ctx.config
    try:
        response = await ctx.http_client.get(
            url,
            headers=headers,
            params={"text": text, "id": speak_id},
            timeout=100,
        )
    except:
        logger.exception("生成失败")
        return ToolCallResponse(
            name=config.name,
            content_type="str",
            content="语音生成失败",
            data="generate error",
        )
    return ToolCallResponse(
        name=config.name,
        content_type="audio",
        content=response.content,
        data="success to generate audio, it has been send.",
    )


tools_func.register(func_moegoe_tts, Config())
