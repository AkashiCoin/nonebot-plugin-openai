import asyncio
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import time

from argparse import Namespace
from typing import Coroutine
from loguru import logger
from nonebot import on_command, on_shell_command, get_driver
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    Message,
    GroupMessageEvent,
    MessageSegment,
)
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.adapters.onebot.v11.helpers import HandleCancellation
from nonebot.params import CommandArg, ShellCommandArgs
from nonebot.rule import ArgumentParser
from nonebot.permission import SUPERUSER
from nonebot.typing import T_State
from nonebot.drivers import Driver

from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

from .utils import get_message_img
from ._openai import OpenAIClient
from .config import config, Config
from .types import Channel, ToolCallConfig, ToolCallResponse, ToolCallRequest
from .settings import settings
from .function import tools_func


__plugin_meta__ = PluginMetadata(
    name="OpenAI",
    description="同步openai功能",
    usage="openai",
    type="application",
    homepage="https://github.com/AkashiCoin/nonebot-plugin-openai",
    config=Config,
    extra={
        "unique_name": "openai",
        "author": "AkashiCoin <i@loli.vet>",
        "version": "0.1.0",
    },
)

openai_client = OpenAIClient(
    base_url=config.openai_base_url,
    channels=settings.channels,
    tool_func=tools_func,
    default_model=config.openai_default_model,
)
driver = get_driver()


@driver.on_startup
async def load_func():
    tools_func.register(openai_client.tts, ToolCallConfig(name="TTS"))
    tools_func.register(openai_client.gen_image, ToolCallConfig(name="DALL-E"))
    # 从config.openai_data_path配置的文件夹中的func文件夹中读取出所有开头为func的文件名
    func_dir = os.path.join(config.openai_data_path, 'func')
    func_files = [
        f for f in os.listdir(func_dir) 
        if f.startswith('func') and f.endswith('.py')
    ]

    # 将func文件夹中的所有文件复制进入cache_func目录
    cache_dir = os.path.join(Path(__file__).parent, 'cache_func')
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    with open(os.path.join(cache_dir, "__init__.py"), "w") as f:
        f.write("from ..types import ToolCallResponse, ToolCallConfig\nfrom ..function import tools_func")
    for func_file in func_files:
        shutil.copy(os.path.join(func_dir, func_file), cache_dir)

    # 从当前文件夹cache_func文件夹中
    for func_file in func_files:
        module_name, _ = os.path.splitext(func_file)  # remove .py extension
        importlib.import_module(f'.cache_func.{module_name}', package=__package__)
    tools_func.save()

openai_parser = ArgumentParser(description="Openai指令")
openai_parser.add_argument("text", nargs="*", help="指令文本")
openai_parser.add_argument("-c", "--clear", action="store_true", help="清空上下文")
openai_parser.add_argument("-a", "--add", nargs="*", help="添加预设")
openai_parser.add_argument("-e", "--edit", nargs="*", help="编辑预设")
openai_parser.add_argument("-d", "--delete", help="删除预设")
openai_parser.add_argument("-s", "--set", help="使用预设")
openai_parser.add_argument("--set-default", help="配置默认预设")
openai_parser.add_argument("--reload", help="重载配置文件")
openai_parser.add_argument("-v", "--view", help="查看状态")
openai_parser.add_argument("-m", "--model", help="自定义模型", default=config.openai_default_model)
openai = on_shell_command("openai", parser=openai_parser)


@openai.handle()
async def _(bot: Bot, event: MessageEvent, args: Namespace = ShellCommandArgs()):
    await handle_command(bot, event, args)
    session = settings.get_session(event)
    text = ""
    for arg in args.text:
        if isinstance(arg, str):
            text += arg + " "
    img_url = get_message_img(event)
    results = []
    try:
        results = await openai_client.chat(session, prompt=text, model=args.model, image_url=img_url)
        tasks = []
        for result in results:
            if isinstance(result, ToolCallRequest):
                await openai.send(f"[Function] 开始调用 {result.config.name} ...")
                tasks.append(result.func)
        results.extend(await asyncio.gather(*tasks, return_exceptions=True))
        asyncio.ensure_future(send_msg(openai, results))
        # if tasks:
        #     results = await openai_client.chat(session=session, tool_choice="none")
        #     await send_msg(openai, results)
        settings.save()
    except Exception as e:
        logger.opt(exception=e).error(e)
        await openai.send(f"发生了一些错误: {e}")


async def handle_command(bot: Bot, event: MessageEvent, args: Namespace):
    if args.clear:
        settings.del_session(event)
        settings.save()
        if not args.text:
            await openai.finish("已清空上下文。")
    if args.set:
        session = settings.get_session(event)
        session.preset = settings.get_preset(args.set)
        if session.preset:
            await openai.finish(f"已配置预设 {session.preset.name}")
        else:
            await openai.finish(f"预设 {args.set} 不存在.")
    if event.get_user_id() in bot.config.superusers:
        if args.set_default:
            name = args.set_default
            preset = settings.get_preset(name)
            if preset:
                settings.default_preset = preset
                settings.save()
                await openai.finish(f"已配置默认预设 {preset.name}")
            else:
                await openai.finish(f"预设 {args.set} 不存在.")
        if args.reload:
            settings.reload()
            await openai.finish("已重载配置文件。")
        if args.add or args.edit:
            args_parts = args.add if args.add else args.edit
            if len(args_parts) < 2:
                await openai.finish("参数不足。")
            name = args_parts[0]
            content = " ".join(args_parts[1:])
            settings.add_preset(name, content)
            await openai.finish(f"已编辑预设 {name} 。")
        if args.delete:
            settings.del_preset(args.delete)
            await openai.finish(f"已删除预设 {args.delete} 。")
        if args.view:
            if args.view == "preset":
                if args.text:
                    preset = settings.get_preset(args.text[0])
                    if preset:
                        await openai.finish(f"预设 {preset.name}:\n {preset.prompt}")
                    else:
                        await openai.finish(f"预设 {args.text[0]} 不存在。")
                else:
                    preset_names = [preset for preset in settings.presets]
                    await openai.finish("预设列表：\n" + "\n".join(preset_names))
            elif args.view == "session":
                pass
            elif args.view == "channel":
                pass
            else:
                await openai.finish("参数错误。")


async def send_msg(matcher, results):
    for result in results:
        if isinstance(result, ChatCompletionMessage):
            if result.content:
                await matcher.send(result.content)
        elif isinstance(result, ToolCallResponse):
            if result.content_type == "str":
                await matcher.send(result.content)
            elif result.content_type == "audio":
                await matcher.send(MessageSegment.record(result.content))
            elif result.content_type == "openai_image":
                await matcher.send(MessageSegment.image(result.content.url) + "\n" + result.content.revised_prompt)
            elif result.content_type == "image":
                await matcher.send(MessageSegment.image(result.content))
        elif isinstance(result, Exception):
            await matcher.send(f"发生了一些错误：{result}")


# 以下是tts部分
# 使用tts需要gocq安装ffmpeg
tts_parser = ArgumentParser(description="TTS 参数设定")
tts_parser.add_argument("text", default="", nargs="*", help="语音文本")
tts_parser.add_argument(
    "-v",
    "--voice",
    default="shimmer",
    choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
    help="选择声音",
)
tts_parser.add_argument(
    "-m", "--model", default="tts-1", choices=["tts-1", "tts-1-hd"], help="选择模型"
)
tts_parser.add_argument("-s", "--speed", type=float, default=1.0, help="设定语速")
tts = on_shell_command("tts", priority=5, block=True, parser=tts_parser)


@tts.handle()
async def handle_tts(event: MessageEvent, args: Namespace = ShellCommandArgs()):
    if not args.text:
        await tts.finish("请输入要转换为语音的文本。")
    msg = "".join(args.text)

    voice = args.voice
    model = args.model
    speed = args.speed
    if speed < 0.25 or speed > 4.0:
        await tts.send("速度参数必须在 0.25 到 4.0 之间。")
        return
    try:
        record = await openai_client.tts(msg, model=model, voice=voice, speed=speed)
    except Exception:
        await tts.finish("语音转换失败，请稍后再试。")
    await tts.send(MessageSegment.record(record.content))


# 以下是dall-e部分
# 创建解析器
dalle_parser = ArgumentParser(description="图像参数设定")
# 添加参数
dalle_parser.add_argument("prompt", nargs="*", help="图像生成提示词")
dalle_parser.add_argument(
    "-size",
    default="1024x1024",
    choices=["1024x1024", "1024x1792", "1792x1024"],
    help="选择尺寸",
)
dalle_parser.add_argument(
    "-q", "--quality", default="standard", choices=["standard", "hd"], help="选择质量"
)
dalle_parser.add_argument(
    "-s", "--style", default="vivid", choices=["vivid", "natural"], help="选择风格"
)
dalle = on_shell_command("dalle", priority=5, block=True, parser=dalle_parser)


@dalle.handle()
async def generate_image(
    event: MessageEvent,
    args: Namespace = ShellCommandArgs(),
):
    if not args.prompt:
        await dalle.finish("请输入要生成图像的提示词。")
    size = args.size
    quality = args.quality
    style = args.style
    result = await openai_client.gen_image(
        " ".join(args.prompt), size=size, quality=quality, style=style
    )
    await dalle.send(
        MessageSegment.image(result.content.url) + "\n" + result.content.revised_prompt
    )  # 将响应内容作为图片消息发送
