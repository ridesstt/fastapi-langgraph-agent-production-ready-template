"""This file contains the graph utilities for the application."""
"""此文件包含应用程序的图工具函数。"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import trim_messages as _trim_messages

from app.core.config import settings
from app.schemas import Message


def dump_messages(messages: list[Message]) -> list[dict]:
    """Dump the messages to a list of dictionaries.

    Args:
        messages (list[Message]): The messages to dump.

    Returns:
        list[dict]: The dumped messages.
    """
    """将消息转换为字典列表。

    参数:
        messages (list[Message]): 需要转换的消息列表。

    返回:
        list[dict]: 转换后的消息字典列表。
    """
    return [message.model_dump() for message in messages]


def prepare_messages(messages: list[Message], llm: BaseChatModel, system_prompt: str) -> list[Message]:
    """Prepare the messages for the LLM.

    Args:
        messages (list[Message]): The messages to prepare.
        llm (BaseChatModel): The LLM to use.
        system_prompt (str): The system prompt to use.

    Returns:
        list[Message]: The prepared messages.
    """
    """为语言模型准备消息。

    参数:
        messages (list[Message]): 需要准备的消息列表。
        llm (BaseChatModel): 使用的语言模型。
        system_prompt (str): 系统提示词。

    返回:
        list[Message]: 处理后的消息列表。
    """
    # 使用语言模型的token计数器来裁剪消息
    trimmed_messages = _trim_messages(
        dump_messages(messages),
        strategy="last",  # 从最后开始裁剪
        token_counter=llm,  # 使用语言模型的token计数器
        max_tokens=settings.MAX_TOKENS,  # 最大token数
        start_on="human",  # 从人类消息开始
        include_system=False,  # 不包含系统消息
        allow_partial=False,  # 不允许部分消息
    )
    # 在裁剪后的消息前添加系统提示词
    return [Message(role="system", content=system_prompt)] + trimmed_messages
