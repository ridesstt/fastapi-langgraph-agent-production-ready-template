"""应用程序配置管理模块。

此模块处理应用程序的环境特定配置加载、解析和管理。
包括环境检测、.env文件加载和配置值解析。
"""

import json
import os
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from dotenv import load_dotenv


# 定义环境类型
class Environment(str, Enum):
    """应用程序环境类型。

    定义应用程序可以运行的环境类型：
    - development: 开发环境
    - staging: 预发布环境
    - production: 生产环境
    - test: 测试环境
    """

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


# 确定当前环境
def get_environment() -> Environment:
    """获取当前环境。

    Returns:
        Environment: 当前环境（development、staging、production 或 test）
    """
    match os.getenv("APP_ENV", "development").lower():
        case "production" | "prod":
            return Environment.PRODUCTION
        case "staging" | "stage":
            return Environment.STAGING
        case "test":
            return Environment.TEST
        case _:
            return Environment.DEVELOPMENT


# Load appropriate .env file based on environment
def load_env_file():
    """Load environment-specific .env file."""
    env = get_environment()
    print(f"Loading environment: {env}")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    # Define env files in priority order
    env_files = [
        os.path.join(base_dir, f".env.{env.value}.local"),
        os.path.join(base_dir, f".env.{env.value}"),
        os.path.join(base_dir, ".env.local"),
        os.path.join(base_dir, ".env"),
    ]

    # Load the first env file that exists
    for env_file in env_files:
        if os.path.isfile(env_file):
            load_dotenv(dotenv_path=env_file)
            print(f"Loaded environment from {env_file}")
            return env_file

    # Fall back to default if no env file found
    return None


ENV_FILE = load_env_file()


# Parse list values from environment variables
def parse_list_from_env(env_key, default=None):
    """Parse a comma-separated list from an environment variable."""
    value = os.getenv(env_key)
    if not value:
        return default or []

    # Remove quotes if they exist
    value = value.strip("\"'")
    # Handle single value case
    if "," not in value:
        return [value]
    # Split comma-separated values
    return [item.strip() for item in value.split(",") if item.strip()]


# Parse dict of lists from environment variables with prefix
def parse_dict_of_lists_from_env(prefix, default_dict=None):
    """Parse dictionary of lists from environment variables with a common prefix."""
    result = default_dict or {}

    # Look for all env vars with the given prefix
    for key, value in os.environ.items():
        if key.startswith(prefix):
            endpoint = key[len(prefix) :].lower()  # Extract endpoint name
            # Parse the values for this endpoint
            if value:
                value = value.strip("\"'")
                if "," in value:
                    result[endpoint] = [item.strip() for item in value.split(",") if item.strip()]
                else:
                    result[endpoint] = [value]

    return result


class Settings:
    """应用程序设置类（不使用pydantic）。"""

    def __init__(self):
        """从环境变量初始化应用程序设置。

        加载并设置所有来自环境变量的配置值，
        为每个设置提供适当的默认值。
        同时根据当前环境应用环境特定的覆盖设置。
        """
        # 设置环境
        self.ENVIRONMENT = get_environment()

        # 应用程序基本设置
        self.PROJECT_NAME = os.getenv("PROJECT_NAME", "FastAPI LangGraph Template")  # 项目名称
        self.VERSION = os.getenv("VERSION", "1.0.0")  # 版本号
        self.DESCRIPTION = os.getenv(  # 项目描述
            "DESCRIPTION", "A production-ready FastAPI template with LangGraph and Langfuse integration"
        )
        self.API_V1_STR = os.getenv("API_V1_STR", "/api/v1")  # API版本路径
        self.DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "t", "yes")  # 调试模式开关

        # CORS（跨域资源共享）设置
        self.ALLOWED_ORIGINS = parse_list_from_env("ALLOWED_ORIGINS", ["*"])  # 允许的跨域来源

        # Langfuse配置（用于LLM应用监控和分析）
        self.LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY", "")  # Langfuse公钥
        self.LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY", "")  # Langfuse密钥
        self.LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")  # Langfuse服务器地址

        # LangGraph配置（LLM应用框架）
        self.LLM_API_KEY = os.getenv("LLM_API_KEY", "")  # LLM API密钥
        self.LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # 使用的LLM模型
        self.DEFAULT_LLM_TEMPERATURE = float(os.getenv("DEFAULT_LLM_TEMPERATURE", "0.2"))  # LLM温度参数
        self.MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))  # 最大token数
        self.MAX_LLM_CALL_RETRIES = int(os.getenv("MAX_LLM_CALL_RETRIES", "3"))  # LLM调用最大重试次数

        # JWT（JSON Web Token）配置
        self.JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")  # JWT密钥
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")  # JWT算法
        self.JWT_ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_DAYS", "30"))  # JWT令牌过期天数

        # 日志配置
        self.LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))  # 日志目录
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # 日志级别
        self.LOG_FORMAT = os.getenv("LOG_FORMAT", "json")  # 日志格式（json或console）

        # PostgreSQL数据库配置
        self.POSTGRES_URL = os.getenv("POSTGRES_URL", "")  # 数据库连接URL
        self.POSTGRES_POOL_SIZE = int(os.getenv("POSTGRES_POOL_SIZE", "20"))  # 连接池大小
        self.POSTGRES_MAX_OVERFLOW = int(os.getenv("POSTGRES_MAX_OVERFLOW", "10"))  # 最大溢出连接数
        self.CHECKPOINT_TABLES = ["checkpoint_blobs", "checkpoint_writes", "checkpoints"]  # 检查点相关表

        # 速率限制配置
        self.RATE_LIMIT_DEFAULT = parse_list_from_env("RATE_LIMIT_DEFAULT", ["200 per day", "50 per hour"])  # 默认速率限制

        # 各端点的速率限制默认值
        default_endpoints = {
            "chat": ["30 per minute"],  # 聊天接口限制
            "chat_stream": ["20 per minute"],  # 流式聊天接口限制
            "messages": ["50 per minute"],  # 消息接口限制
            "register": ["10 per hour"],  # 注册接口限制
            "login": ["20 per minute"],  # 登录接口限制
            "root": ["10 per minute"],  # 根接口限制
            "health": ["20 per minute"],  # 健康检查接口限制
        }

        # 从环境变量更新速率限制端点配置
        self.RATE_LIMIT_ENDPOINTS = default_endpoints.copy()
        for endpoint in default_endpoints:
            env_key = f"RATE_LIMIT_{endpoint.upper()}"
            value = parse_list_from_env(env_key)
            if value:
                self.RATE_LIMIT_ENDPOINTS[endpoint] = value

        # 评估配置
        self.EVALUATION_LLM = os.getenv("EVALUATION_LLM", "gpt-4o-mini")  # 评估使用的LLM模型
        self.EVALUATION_BASE_URL = os.getenv("EVALUATION_BASE_URL", "https://api.openai.com/v1")  # 评估API基础URL
        self.EVALUATION_API_KEY = os.getenv("EVALUATION_API_KEY", self.LLM_API_KEY)  # 评估API密钥
        self.EVALUATION_SLEEP_TIME = int(os.getenv("EVALUATION_SLEEP_TIME", "10"))  # 评估间隔时间

        # 应用环境特定设置
        self.apply_environment_settings()

    def apply_environment_settings(self):
        """根据当前环境应用环境特定的设置。"""
        env_settings = {
            Environment.DEVELOPMENT: {  # 开发环境设置
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "console",
                "RATE_LIMIT_DEFAULT": ["1000 per day", "200 per hour"],
            },
            Environment.STAGING: {  # 预发布环境设置
                "DEBUG": False,
                "LOG_LEVEL": "INFO",
                "RATE_LIMIT_DEFAULT": ["500 per day", "100 per hour"],
            },
            Environment.PRODUCTION: {  # 生产环境设置
                "DEBUG": False,
                "LOG_LEVEL": "WARNING",
                "RATE_LIMIT_DEFAULT": ["200 per day", "50 per hour"],
            },
            Environment.TEST: {  # 测试环境设置
                "DEBUG": True,
                "LOG_LEVEL": "DEBUG",
                "LOG_FORMAT": "console",
                "RATE_LIMIT_DEFAULT": ["1000 per day", "1000 per hour"],  # 测试环境放宽限制
            },
        }

        # 获取当前环境的设置
        current_env_settings = env_settings.get(self.ENVIRONMENT, {})

        # 如果环境变量中没有明确设置，则应用默认设置
        for key, value in current_env_settings.items():
            env_var_name = key.upper()
            # 仅当环境变量未明确设置时才覆盖
            if env_var_name not in os.environ:
                setattr(self, key, value)


# 创建设置实例
settings = Settings()
