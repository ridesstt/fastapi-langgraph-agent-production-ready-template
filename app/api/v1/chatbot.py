"""聊天机器人API端点模块，用于处理聊天交互。

本模块提供聊天交互相关的API端点，包括：
- 常规聊天
- 流式聊天
- 消息历史记录管理
- 聊天记录清除
"""

import json
from typing import List

from fastapi import (
    APIRouter,  # FastAPI路由组件
    Depends,    # 依赖注入
    HTTPException,  # HTTP异常处理
    Request,    # 请求对象
)
from fastapi.responses import StreamingResponse  # 流式响应

from app.api.v1.auth import get_current_session  # 获取当前会话
from app.core.config import settings  # 应用配置
from app.core.langgraph.graph import LangGraphAgent  # 语言图代理(核心聊天逻辑)
from app.core.limiter import limiter  # 限流器
from app.core.logging import logger  # 日志记录
from app.models.session import Session  # 会话模型
from app.schemas.chat import (  # 数据模型
    ChatRequest,
    ChatResponse,
    Message,
    StreamResponse,
)

# 创建路由实例
router = APIRouter()
# 初始化语言图代理
agent = LangGraphAgent()


@router.post("/chat", response_model=ChatResponse)  # 定义POST端点，指定响应模型
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat"][0])  # 应用限流规则
async def chat(
    request: Request,  # FastAPI请求对象(用于限流)
    chat_request: ChatRequest,  # 聊天请求数据
    session: Session = Depends(get_current_session),  # 通过依赖注入获取当前会话
):
    """处理常规聊天请求
    
    参数:
        request: FastAPI请求对象(用于限流)
        chat_request: 包含消息内容的聊天请求
        session: 从认证令牌获取的当前会话
        
    返回:
        ChatResponse: 处理后的聊天响应
        
    异常:
        HTTPException: 如果请求处理出错则抛出500异常
    """
    try:
        # 记录接收到的请求日志
        logger.info(
            "chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        # 通过LangGraph处理请求
        result = await agent.get_response(chat_request.messages, session.id, user_id=session.user_id)

        # 记录处理完成日志
        logger.info("chat_request_processed", session_id=session.id)

        # 返回处理结果
        return ChatResponse(messages=result)
    except Exception as e:
        # 记录错误日志并抛出异常
        logger.error("chat_request_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")  # 流式聊天端点
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["chat_stream"][0])  # 应用限流
async def chat_stream(
    request: Request,
    chat_request: ChatRequest,
    session: Session = Depends(get_current_session),
):
    """处理流式聊天请求
    
    参数:
        request: FastAPI请求对象(用于限流)
        chat_request: 包含消息内容的聊天请求
        session: 当前会话
        
    返回:
        StreamingResponse: 流式响应对象
        
    异常:
        HTTPException: 处理出错时抛出500异常
    """
    try:
        # 记录流式请求接收日志
        logger.info(
            "stream_chat_request_received",
            session_id=session.id,
            message_count=len(chat_request.messages),
        )

        async def event_generator():
            """生成服务器发送事件(SSE)的生成器
            
            生成:
                str: JSON格式的服务器事件
                
            异常:
                如果流式处理过程中出错，会生成错误事件
            """
            try:
                full_response = ""
                # 异步获取流式响应
                async for chunk in agent.get_stream_response(
                    chat_request.messages, session.id, user_id=session.user_id
                ):
                    full_response += chunk
                    # 构造流式响应对象
                    response = StreamResponse(content=chunk, done=False)
                    # 生成SSE格式数据
                    yield f"data: {json.dumps(response.model_dump())}\n\n"

                # 发送完成事件
                final_response = StreamResponse(content="", done=True)
                yield f"data: {json.dumps(final_response.model_dump())}\n\n"

            except Exception as e:
                # 记录流式处理错误
                logger.error(
                    "stream_chat_request_failed",
                    session_id=session.id,
                    error=str(e),
                    exc_info=True,
                )
                # 生成错误事件
                error_response = StreamResponse(content=str(e), done=True)
                yield f"data: {json.dumps(error_response.model_dump())}\n\n"

        # 返回流式响应
        return StreamingResponse(event_generator(), media_type="text/event-stream")

    except Exception as e:
        # 记录并抛出异常
        logger.error(
            "stream_chat_request_failed",
            session_id=session.id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=ChatResponse)  # 获取消息历史端点
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])  # 限流
async def get_session_messages(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """获取会话的所有消息
    
    参数:
        request: FastAPI请求对象
        session: 当前会话
        
    返回:
        ChatResponse: 包含所有消息的响应
        
    异常:
        HTTPException: 获取失败时抛出500异常
    """
    try:
        # 从代理获取聊天历史
        messages = await agent.get_chat_history(session.id)
        return ChatResponse(messages=messages)
    except Exception as e:
        # 记录错误日志
        logger.error("get_messages_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/messages")  # 清除聊天历史端点
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["messages"][0])  # 限流
async def clear_chat_history(
    request: Request,
    session: Session = Depends(get_current_session),
):
    """清除会话的所有消息
    
    参数:
        request: FastAPI请求对象
        session: 当前会话
        
    返回:
        dict: 包含操作结果的字典
        
    异常:
        HTTPException: 清除失败时抛出500异常
    """
    try:
        # 调用代理清除历史
        await agent.clear_chat_history(session.id)
        return {"message": "聊天记录已成功清除"}
    except Exception as e:
        # 记录错误日志
        logger.error("clear_chat_history_failed", session_id=session.id, error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))