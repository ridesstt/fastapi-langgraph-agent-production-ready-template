"""This file contains the authentication utilities for the application."""
"""此文件包含应用程序的认证工具。"""

import re
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from typing import Optional

from jose import (
    JWTError,
    jwt,
)

from app.core.config import settings
from app.core.logging import logger
from app.schemas.auth import Token
from app.utils.sanitization import sanitize_string


def create_access_token(thread_id: str, expires_delta: Optional[timedelta] = None) -> Token:
    """Create a new access token for a thread.

    Args:
        thread_id: The unique thread ID for the conversation.
        expires_delta: Optional expiration time delta.

    Returns:
        Token: The generated access token.
    """
    """为会话创建一个新的访问令牌。

    参数:
        thread_id: 会话的唯一线程ID。
        expires_delta: 可选的过期时间增量。

    返回:
        Token: 生成的访问令牌。
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=settings.JWT_ACCESS_TOKEN_EXPIRE_DAYS)

    # 准备要编码的数据
    to_encode = {
        "sub": thread_id,  # 主题（用户标识）
        "exp": expire,     # 过期时间
        "iat": datetime.now(UTC),  # 签发时间
        "jti": sanitize_string(f"{thread_id}-{datetime.now(UTC).timestamp()}"),  # 添加唯一令牌标识符
    }

    # 使用JWT算法编码令牌
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    logger.info("token_created", thread_id=thread_id, expires_at=expire.isoformat())

    return Token(access_token=encoded_jwt, expires_at=expire)


def verify_token(token: str) -> Optional[str]:
    """Verify a JWT token and return the thread ID.

    Args:
        token: The JWT token to verify.

    Returns:
        Optional[str]: The thread ID if token is valid, None otherwise.

    Raises:
        ValueError: If the token format is invalid
    """
    """验证JWT令牌并返回线程ID。

    参数:
        token: 要验证的JWT令牌。

    返回:
        Optional[str]: 如果令牌有效则返回线程ID，否则返回None。

    异常:
        ValueError: 如果令牌格式无效
    """
    if not token or not isinstance(token, str):
        logger.warning("token_invalid_format")
        raise ValueError("Token must be a non-empty string")

    # 在尝试解码之前进行基本格式验证
    # JWT令牌由3个用点分隔的base64url编码段组成
    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        logger.warning("token_suspicious_format")
        raise ValueError("Token format is invalid - expected JWT format")

    try:
        # 解码并验证令牌
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        thread_id: str = payload.get("sub")
        if thread_id is None:
            logger.warning("token_missing_thread_id")
            return None

        logger.info("token_verified", thread_id=thread_id)
        return thread_id

    except JWTError as e:
        logger.error("token_verification_failed", error=str(e))
        return None
