"""API v1 路由配置模块.

该模块设置主API路由，并包含所有子路由（如认证和聊天机器人功能的路由）。
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router  # 导入认证路由
from app.api.v1.chatbot import router as chatbot_router  # 导入聊天机器人路由
from app.core.logging import logger  # 导入日志记录器

# 创建API路由实例
api_router = APIRouter()

# 包含子路由
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])  # 添加认证路由，前缀为/auth
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])  # 添加聊天机器人路由，前缀为/chatbot


@api_router.get("/health")
async def health_check():
    """健康检查端点.

    返回:
        dict: 包含健康状态和版本信息的字典.
    """
    logger.info("health_check_called")  # 记录健康检查被调用的日志
    return {"status": "healthy", "version": "1.0.0"}  # 返回健康状态和版本信息