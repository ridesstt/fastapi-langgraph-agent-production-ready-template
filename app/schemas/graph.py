"""This file contains the graph schema for the application."""
"""此文件包含应用程序的图模式定义。"""

import re
import uuid
from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class GraphState(BaseModel):
    """State definition for the LangGraph Agent/Workflow."""
    """LangGraph 代理/工作流的状态定义。"""

    messages: Annotated[list, add_messages] = Field(
        default_factory=list, description="The messages in the conversation"
    )
    # 会话中的消息列表，使用 add_messages 注解来支持消息的添加操作
    session_id: str = Field(..., description="The unique identifier for the conversation session")
    # 会话的唯一标识符

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate that the session ID is a valid UUID or follows safe pattern.

        Args:
            v: The thread ID to validate

        Returns:
            str: The validated session ID

        Raises:
            ValueError: If the session ID is not valid
        """
        """验证会话ID是否为有效的UUID或符合安全模式。

        参数:
            v: 要验证的会话ID

        返回:
            str: 验证后的会话ID

        异常:
            ValueError: 如果会话ID无效
        """
        # 尝试将其验证为UUID
        try:
            uuid.UUID(v)
            return v
        except ValueError:
            # 如果不是UUID，检查是否只包含安全字符
            if not re.match(r"^[a-zA-Z0-9_\-]+$", v):
                raise ValueError("Session ID must contain only alphanumeric characters, underscores, and hyphens")
                # 会话ID必须只包含字母数字字符、下划线和连字符
            return v
