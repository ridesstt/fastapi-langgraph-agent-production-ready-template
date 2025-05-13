"""This file contains the authentication schema for the application."""

import re
from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)


class Token(BaseModel):
    """Token model for authentication.
    认证令牌模型

    Attributes:
        access_token: The JWT access token. JWT访问令牌
        token_type: The type of token (always "bearer"). 令牌类型（始终为"bearer"）
        expires_at: The token expiration timestamp. 令牌过期时间戳
    """

    access_token: str = Field(..., description="The JWT access token")  # JWT访问令牌
    token_type: str = Field(default="bearer", description="The type of token")  # 令牌类型
    expires_at: datetime = Field(..., description="The token expiration timestamp")  # 令牌过期时间戳


class TokenResponse(BaseModel):
    """Response model for login endpoint.
    登录接口的响应模型

    Attributes:
        access_token: The JWT access token JWT访问令牌
        token_type: The type of token (always "bearer") 令牌类型（始终为"bearer"）
        expires_at: When the token expires 令牌过期时间
    """

    access_token: str = Field(..., description="The JWT access token")  # JWT访问令牌
    token_type: str = Field(default="bearer", description="The type of token")  # 令牌类型
    expires_at: datetime = Field(..., description="When the token expires")  # 令牌过期时间


class UserCreate(BaseModel):
    """Request model for user registration.
    用户注册请求模型

    Attributes:
        email: User's email address 用户的电子邮件地址
        password: User's password 用户的密码
    """

    email: EmailStr = Field(..., description="User's email address")  # 用户的电子邮件地址
    password: SecretStr = Field(..., description="User's password", min_length=8, max_length=64)  # 用户的密码

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: SecretStr) -> SecretStr:
        """Validate password strength.
        验证密码强度

        Args:
            v: The password to validate 待验证的密码

        Returns:
            SecretStr: The validated password 验证后的密码

        Raises:
            ValueError: If the password is not strong enough 如果密码强度不够
        """
        password = v.get_secret_value()

        # Check for common password requirements
        # 检查常见密码要求
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")  # 密码长度必须至少为8个字符

        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter")  # 密码必须包含至少一个大写字母

        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter")  # 密码必须包含至少一个小写字母

        if not re.search(r"[0-9]", password):
            raise ValueError("Password must contain at least one number")  # 密码必须包含至少一个数字

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("Password must contain at least one special character")  # 密码必须包含至少一个特殊字符

        return v


class UserResponse(BaseModel):
    """Response model for user operations.
    用户操作的响应模型

    Attributes:
        id: User's ID 用户ID
        email: User's email address 用户的电子邮件地址
        token: Authentication token 认证令牌
    """

    id: int = Field(..., description="User's ID")  # 用户ID
    email: str = Field(..., description="User's email address")  # 用户的电子邮件地址
    token: Token = Field(..., description="Authentication token")  # 认证令牌


class SessionResponse(BaseModel):
    """Response model for session creation.
    会话创建的响应模型

    Attributes:
        session_id: The unique identifier for the chat session 聊天会话的唯一标识符
        name: Name of the session (defaults to empty string) 会话名称（默认为空字符串）
        token: The authentication token for the session 会话的认证令牌
    """

    session_id: str = Field(..., description="The unique identifier for the chat session")  # 聊天会话的唯一标识符
    name: str = Field(default="", description="Name of the session", max_length=100)  # 会话名称
    token: Token = Field(..., description="The authentication token for the session")  # 会话的认证令牌

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """Sanitize the session name.
        清理会话名称

        Args:
            v: The name to sanitize 待清理的名称

        Returns:
            str: The sanitized name 清理后的名称
        """
        # Remove any potentially harmful characters
        # 移除任何潜在的有害字符
        sanitized = re.sub(r'[<>{}[\]()\'"`]', "", v)
        return sanitized
