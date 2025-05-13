"""应用程序的速率限制配置。

此模块使用 slowapi 配置速率限制，默认限制在应用程序设置中定义。
速率限制基于远程 IP 地址进行应用。
"""

# 导入必要的模块
from slowapi import Limiter  # 导入限流器类
from slowapi.util import get_remote_address  # 导入获取远程地址的工具函数

from app.core.config import settings  # 导入应用配置

# 初始化限流器
# key_func=get_remote_address: 使用客户端IP地址作为限流的键
# default_limits=settings.RATE_LIMIT_DEFAULT: 使用配置文件中设置的默认限流规则
limiter = Limiter(key_func=get_remote_address, default_limits=settings.RATE_LIMIT_DEFAULT)
