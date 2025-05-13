"""API认证授权端点模块

本模块提供用户注册、登录、会话管理和令牌验证等端点
"""

import uuid
from typing import List

from fastapi import (
    APIRouter,  # FastAPI路由组件
    Depends,    # 依赖注入系统
    Form,       # 表单数据处理
    HTTPException,  # HTTP异常处理
    Request,    # 请求对象
)
from fastapi.security import (
    HTTPAuthorizationCredentials,  # Bearer token认证凭证
    HTTPBearer,  # Bearer token认证方案
)

# 导入项目模块
from app.core.config import settings  # 应用配置
from app.core.limiter import limiter  # 请求限流器
from app.core.logging import logger  # 日志记录
from app.models.session import Session  # 会话模型
from app.models.user import User  # 用户模型
from app.schemas.auth import (  # 数据模型
    SessionResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.database import DatabaseService  # 数据库服务
from app.utils.auth import (  # 认证工具
    create_access_token,  # 创建JWT令牌
    verify_token,  # 验证令牌
)
from app.utils.sanitization import (  # 数据清洗工具
    sanitize_email,  # 邮箱清洗
    sanitize_string,  # 字符串清洗
    validate_password_strength,  # 密码强度验证
)

# 初始化路由和依赖项
router = APIRouter()
security = HTTPBearer()  # Bearer token认证方案
db_service = DatabaseService()  # 数据库服务实例


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """从令牌中获取当前用户
    
    参数:
        credentials: 包含JWT令牌的HTTP认证凭证
        
    返回:
        User: 从令牌中提取的用户对象
        
    异常:
        HTTPException: 令牌无效或缺失时抛出
    """
    try:
        # 清洗令牌防止注入攻击
        token = sanitize_string(credentials.credentials)

        # 验证令牌有效性
        user_id = verify_token(token)
        if user_id is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="无效的认证凭证",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查用户是否存在
        user_id_int = int(user_id)
        user = await db_service.get_user(user_id_int)
        if user is None:
            logger.error("user_not_found", user_id=user_id_int)
            raise HTTPException(
                status_code=404,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="无效的令牌格式",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Session:
    """从令牌中获取当前会话
    
    参数:
        credentials: 包含JWT令牌的HTTP认证凭证
        
    返回:
        Session: 从令牌中提取的会话对象
        
    异常:
        HTTPException: 令牌无效或缺失时抛出
    """
    try:
        # 清洗令牌
        token = sanitize_string(credentials.credentials)

        # 验证令牌获取会话ID
        session_id = verify_token(token)
        if session_id is None:
            logger.error("session_id_not_found", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="无效的认证凭证",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 二次清洗会话ID
        session_id = sanitize_string(session_id)

        # 检查会话是否存在
        session = await db_service.get_session(session_id)
        if session is None:
            logger.error("session_not_found", session_id=session_id)
            raise HTTPException(
                status_code=404,
                detail="会话不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return session
    except ValueError as ve:
        logger.error("token_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(
            status_code=422,
            detail="无效的令牌格式",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse)  # 用户注册端点
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])  # 注册限流
async def register_user(request: Request, user_data: UserCreate):
    """注册新用户
    
    参数:
        request: FastAPI请求对象(用于限流)
        user_data: 用户注册数据
        
    返回:
        UserResponse: 创建的用户信息
        
    异常:
        HTTPException: 注册失败时抛出
    """
    try:
        # 清洗邮箱
        sanitized_email = sanitize_email(user_data.email)

        # 提取并验证密码
        password = user_data.password.get_secret_value()
        validate_password_strength(password)

        # 检查邮箱是否已注册
        if await db_service.get_user_by_email(sanitized_email):
            raise HTTPException(status_code=400, detail="邮箱已被注册")

        # 创建用户
        user = await db_service.create_user(
            email=sanitized_email,
            password=User.hash_password(password)  # 密码哈希存储
        )

        # 生成访问令牌
        token = create_access_token(str(user.id))

        return UserResponse(
            id=user.id,
            email=user.email,
            token=token
        )
    except ValueError as ve:
        logger.error("user_registration_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/login", response_model=TokenResponse)  # 用户登录端点
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])  # 登录限流
async def login(
    request: Request,
    username: str = Form(...),  # 表单格式的用户名
    password: str = Form(...),  # 表单格式的密码
    grant_type: str = Form(default="password")  # OAuth2授权类型
):
    """用户登录
    
    参数:
        request: FastAPI请求对象
        username: 用户邮箱
        password: 用户密码
        grant_type: 必须为"password"
        
    返回:
        TokenResponse: 访问令牌信息
        
    异常:
        HTTPException: 凭证无效时抛出
    """
    try:
        # 输入清洗
        username = sanitize_string(username)
        password = sanitize_string(password)
        grant_type = sanitize_string(grant_type)

        # 验证授权类型
        if grant_type != "password":
            raise HTTPException(
                status_code=400,
                detail="不支持的授权类型，必须为'password'",
            )

        # 验证用户凭证
        user = await db_service.get_user_by_email(username)
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=401,
                detail="邮箱或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 生成访问令牌
        token = create_access_token(str(user.id))
        return TokenResponse(
            access_token=token.access_token,
            token_type="bearer",  # Bearer token类型
            expires_at=token.expires_at  # 过期时间
        )
    except ValueError as ve:
        logger.error("login_validation_failed", error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/session", response_model=SessionResponse)  # 创建会话端点
async def create_session(user: User = Depends(get_current_user)):
    """为认证用户创建新会话
    
    参数:
        user: 已认证的用户对象
        
    返回:
        SessionResponse: 会话ID、名称和访问令牌
    """
    try:
        # 生成唯一会话ID
        session_id = str(uuid.uuid4())

        # 在数据库中创建会话
        session = await db_service.create_session(session_id, user.id)

        # 为会话创建访问令牌
        token = create_access_token(session_id)

        # 记录日志
        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user.id,
            name=session.name,
            expires_at=token.expires_at.isoformat(),
        )

        return SessionResponse(
            session_id=session_id,
            name=session.name,
            token=token
        )
    except ValueError as ve:
        logger.error("session_creation_validation_failed", error=str(ve), user_id=user.id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.patch("/session/{session_id}/name", response_model=SessionResponse)  # 更新会话名称端点
async def update_session_name(
    session_id: str,  # 路径参数:会话ID
    name: str = Form(...),  # 表单格式的新名称
    current_session: Session = Depends(get_current_session)  # 当前认证会话
):
    """更新会话名称
    
    参数:
        session_id: 要更新的会话ID
        name: 新会话名称
        current_session: 当前认证会话
        
    返回:
        SessionResponse: 更新后的会话信息
        
    异常:
        HTTPException: 更新失败时抛出
    """
    try:
        # 输入清洗
        sanitized_session_id = sanitize_string(session_id)
        sanitized_name = sanitize_string(name)
        sanitized_current_session = sanitize_string(current_session.id)

        # 验证会话所有权
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="不能修改其他用户的会话")

        # 更新会话名称
        session = await db_service.update_session_name(sanitized_session_id, sanitized_name)

        # 生成新令牌(保持一致性)
        token = create_access_token(sanitized_session_id)

        return SessionResponse(
            session_id=sanitized_session_id,
            name=session.name,
            token=token
        )
    except ValueError as ve:
        logger.error("session_update_validation_failed", error=str(ve), session_id=session_id, exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))


@router.get("/sessions", response_model=List[SessionResponse])  # 获取用户会话列表端点
async def get_user_sessions(user: User = Depends(get_current_user)):
    """获取认证用户的所有会话
    
    参数:
        user: 已认证的用户对象
        
    返回:
        List[SessionResponse]: 会话ID列表
    """
    try:
        # 从数据库获取用户会话
        sessions = await db_service.get_user_sessions(user.id)
        
        # 构造响应列表
        return [
            SessionResponse(
                session_id=sanitize_string(session.id),
                name=sanitize_string(session.name),
                token=create_access_token(session.id),
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.error("get_sessions_validation_failed", user_id=user.id, error=str(ve), exc_info=True)
        raise HTTPException(status_code=422, detail=str(ve))