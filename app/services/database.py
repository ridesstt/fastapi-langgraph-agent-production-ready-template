"""This file contains the database service for the application."""
"""此文件包含应用程序的数据库服务。"""

from typing import (
    List,
    Optional,
)

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from sqlmodel import (
    Session,
    SQLModel,
    create_engine,
    select,
)

from app.core.config import (
    Environment,
    settings,
)
from app.core.logging import logger
from app.models.session import Session as ChatSession
from app.models.user import User


class DatabaseService:
    """Service class for database operations.

    This class handles all database operations for Users, Sessions, and Messages.
    It uses SQLModel for ORM operations and maintains a connection pool.
    """
    """数据库操作服务类。

    该类处理所有与用户、会话和消息相关的数据库操作。
    使用SQLModel进行ORM操作并维护连接池。
    """

    def __init__(self):
        """Initialize database service with connection pool."""
        """使用连接池初始化数据库服务。"""
        try:
            # Configure environment-specific database connection pool settings
            # 配置特定环境的数据库连接池设置
            pool_size = settings.POSTGRES_POOL_SIZE
            max_overflow = settings.POSTGRES_MAX_OVERFLOW

            # Create engine with appropriate pool configuration
            # 使用适当的池配置创建数据库引擎
            self.engine = create_engine(
                settings.POSTGRES_URL,
                pool_pre_ping=True,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_timeout=30,  # Connection timeout (seconds) 连接超时（秒）
                pool_recycle=1800,  # Recycle connections after 30 minutes 30分钟后回收连接
            )

            # Create tables (only if they don't exist)
            # 创建数据表（仅当表不存在时）
            SQLModel.metadata.create_all(self.engine)

            logger.info(
                "database_initialized",
                environment=settings.ENVIRONMENT.value,
                pool_size=pool_size,
                max_overflow=max_overflow,
            )
        except SQLAlchemyError as e:
            logger.error("database_initialization_error", error=str(e), environment=settings.ENVIRONMENT.value)
            # In production, don't raise - allow app to start even with DB issues
            # 在生产环境中，不抛出异常 - 即使数据库有问题也允许应用启动
            if settings.ENVIRONMENT != Environment.PRODUCTION:
                raise

    async def create_user(self, email: str, password: str) -> User:
        """Create a new user.

        Args:
            email: User's email address
            password: Hashed password

        Returns:
            User: The created user
        """
        """创建新用户。

        参数：
            email: 用户的电子邮件地址
            password: 加密后的密码

        返回：
            User: 创建的用户对象
        """
        with Session(self.engine) as session:
            user = User(email=email, hashed_password=password)
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info("user_created", email=email)
            return user

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID.

        Args:
            user_id: The ID of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        """通过ID获取用户。

        参数：
            user_id: 要检索的用户ID

        返回：
            Optional[User]: 如果找到则返回用户对象，否则返回None
        """
        with Session(self.engine) as session:
            user = session.get(User, user_id)
            return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.

        Args:
            email: The email of the user to retrieve

        Returns:
            Optional[User]: The user if found, None otherwise
        """
        """通过电子邮件获取用户。

        参数：
            email: 要检索的用户电子邮件

        返回：
            Optional[User]: 如果找到则返回用户对象，否则返回None
        """
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            user = session.exec(statement).first()
            return user

    async def delete_user_by_email(self, email: str) -> bool:
        """Delete a user by email.

        Args:
            email: The email of the user to delete

        Returns:
            bool: True if deletion was successful, False if user not found
        """
        """通过电子邮件删除用户。

        参数：
            email: 要删除的用户电子邮件

        返回：
            bool: 如果删除成功返回True，如果用户未找到返回False
        """
        with Session(self.engine) as session:
            user = session.exec(select(User).where(User.email == email)).first()
            if not user:
                return False

            session.delete(user)
            session.commit()
            logger.info("user_deleted", email=email)
            return True

    async def create_session(self, session_id: str, user_id: int, name: str = "") -> ChatSession:
        """Create a new chat session.

        Args:
            session_id: The ID for the new session
            user_id: The ID of the user who owns the session
            name: Optional name for the session (defaults to empty string)

        Returns:
            ChatSession: The created session
        """
        """创建新的聊天会话。

        参数：
            session_id: 新会话的ID
            user_id: 拥有该会话的用户ID
            name: 会话的可选名称（默认为空字符串）

        返回：
            ChatSession: 创建的会话对象
        """
        with Session(self.engine) as session:
            chat_session = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_created", session_id=session_id, user_id=user_id, name=name)
            return chat_session

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID.

        Args:
            session_id: The ID of the session to retrieve

        Returns:
            Optional[ChatSession]: The session if found, None otherwise
        """
        """通过ID获取会话。

        参数：
            session_id: 要检索的会话ID

        返回：
            Optional[ChatSession]: 如果找到则返回会话对象，否则返回None
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            return chat_session

    async def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        """Get all sessions for a user.

        Args:
            user_id: The ID of the user

        Returns:
            List[ChatSession]: List of user's sessions
        """
        """获取用户的所有会话。

        参数：
            user_id: 用户ID

        返回：
            List[ChatSession]: 用户的会话列表
        """
        with Session(self.engine) as session:
            statement = select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.created_at)
            sessions = session.exec(statement).all()
            return sessions

    async def update_session_name(self, session_id: str, name: str) -> ChatSession:
        """Update a session's name.

        Args:
            session_id: The ID of the session to update
            name: The new name for the session

        Returns:
            ChatSession: The updated session

        Raises:
            HTTPException: If session is not found
        """
        """更新会话名称。

        参数：
            session_id: 要更新的会话ID
            name: 会话的新名称

        返回：
            ChatSession: 更新后的会话对象

        异常：
            HTTPException: 如果会话未找到
        """
        with Session(self.engine) as session:
            chat_session = session.get(ChatSession, session_id)
            if not chat_session:
                raise HTTPException(status_code=404, detail="Session not found")

            chat_session.name = name
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            logger.info("session_name_updated", session_id=session_id, name=name)
            return chat_session

    def get_session_maker(self):
        """Get a session maker for creating database sessions.

        Returns:
            Session: A SQLModel session maker
        """
        """获取用于创建数据库会话的会话创建器。

        返回：
            Session: SQLModel会话创建器
        """
        return Session(self.engine)

    async def health_check(self) -> bool:
        """Check database connection health.

        Returns:
            bool: True if database is healthy, False otherwise
        """
        """检查数据库连接健康状态。

        返回：
            bool: 如果数据库健康则返回True，否则返回False
        """
        try:
            with Session(self.engine) as session:
                # Execute a simple query to check connection
                # 执行简单查询以检查连接
                session.exec(select(1)).first()
                return True
        except Exception as e:
            logger.error("database_health_check_failed", error=str(e))
            return False


# Create a singleton instance
# 创建单例实例
database_service = DatabaseService()
