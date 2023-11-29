from weakref import proxy
from httpx import AsyncClient
from loguru import logger
from . import ToolCallResponse, ToolCallConfig, tools_func


class Config(ToolCallConfig):
    name: str = "谷歌搜素"
    api_key: str = ""
    cx_key: str = ""


async def func_google_search(config: Config, keyword: str, max_results: int = 3):
    """
    This function performs a Google search using the Google Custom Search JSON API.

    Args:
        keyword (str): The search term to use in the Google search.
        max_results (int, optional): The maximum number of search results to return. Defaults to 3.

    Returns:
        ToolCallResponse: An instance of ToolCallResponse class which contains the name, content type, content, and data of the response.

    Raises:
        Exception: If there is an error in the search or in parsing the search results.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36 Edg/110.0.1587.63"
    }

    url = "https://www.googleapis.com/customsearch/v1"
    try:
        async with AsyncClient(proxies=proxy) as cli:
            response = (
                await cli.get(
                    url,
                    headers=headers,
                    params={"key": config.api_key, "cx": config.cx_key, "q": keyword},
                )
            ).json()
    except:
        logger.exception("搜索失败")
        return ToolCallResponse(
            name=config.name,
            content_type="str",
            content="搜素失败，检查函数配置",
            data="search error"
        )
    try:
        items = response["items"]
        text = "\n".join(
            [
                f"[{item['title']}] {item['snippet']} - from: {item['link']}"
                for item in items[:max_results]
            ]
        )
    except:
        return ToolCallResponse(
            name=config.name,
            content_type="str",
            content="搜索失败，无法找到相关结果",
            data=f"search error, can not found {keyword}"
        )

    return ToolCallResponse(
        name=config.name,
        content_type="str",
        content=text,
        data=text,
    )

tools_func.register(func_google_search, Config())