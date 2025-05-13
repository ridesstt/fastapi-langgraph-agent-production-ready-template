"""This file contains the sanitization utilities for the application."""
# 此文件包含应用程序的净化工具

import html
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)


def sanitize_string(value: str) -> str:
    """Sanitize a string to prevent XSS and other injection attacks.

    Args:
        value: The string to sanitize

    Returns:
        str: The sanitized string
    """
    # 净化字符串以防止XSS和其他注入攻击
    # Convert to string if not already
    if not isinstance(value, str):
        value = str(value)

    # HTML escape to prevent XSS
    # HTML转义以防止XSS攻击
    value = html.escape(value)

    # Remove any script tags that might have been escaped
    # 移除可能被转义的script标签
    value = re.sub(r"&lt;script.*?&gt;.*?&lt;/script&gt;", "", value, flags=re.DOTALL)

    # Remove null bytes
    # 移除空字节
    value = value.replace("\0", "")

    return value


def sanitize_email(email: str) -> str:
    """Sanitize an email address.

    Args:
        email: The email address to sanitize

    Returns:
        str: The sanitized email address
    """
    # 净化电子邮件地址
    # Basic sanitization
    email = sanitize_string(email)

    # Ensure email format (simple check)
    # 确保电子邮件格式正确（简单检查）
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("Invalid email format")

    return email.lower()


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize all string values in a dictionary.

    Args:
        data: The dictionary to sanitize

    Returns:
        Dict[str, Any]: The sanitized dictionary
    """
    # 递归净化字典中的所有字符串值
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list(value)
        else:
            sanitized[key] = value
    return sanitized


def sanitize_list(data: List[Any]) -> List[Any]:
    """Recursively sanitize all string values in a list.

    Args:
        data: The list to sanitize

    Returns:
        List[Any]: The sanitized list
    """
    # 递归净化列表中的所有字符串值
    sanitized = []
    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_string(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item))
        else:
            sanitized.append(item)
    return sanitized


def validate_password_strength(password: str) -> bool:
    """Validate password strength.

    Args:
        password: The password to validate

    Returns:
        bool: Whether the password is strong enough

    Raises:
        ValueError: If the password is not strong enough with reason
    """
    # 验证密码强度
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
        # 密码长度必须至少为8个字符

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
        # 密码必须包含至少一个大写字母

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
        # 密码必须包含至少一个小写字母

    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one number")
        # 密码必须包含至少一个数字

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValueError("Password must contain at least one special character")
        # 密码必须包含至少一个特殊字符

    return True
