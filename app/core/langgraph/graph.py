"""这个文件包含了 LangGraph Agent/工作流以及与 LLM 的交互。"""

from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Literal,
    Optional,
)

from asgiref.sync import sync_to_async
from langchain_core.messages import (
    BaseMessage,
    ToolMessage,
    convert_to_openai_messages,
)
from langchain_openai import ChatOpenAI
from langfuse.callback import CallbackHandler
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import (
    END,
    StateGraph,
)
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import StateSnapshot
from openai import OpenAIError
from psycopg_pool import AsyncConnectionPool

from app.core.config import (
    Environment,
    settings,
)
from app.core.langgraph.tools import tools
from app.core.logging import logger
from app.core.prompts import SYSTEM_PROMPT
from app.schemas import (
    GraphState,
    Message,
)
from app.utils import (
    dump_messages,
    prepare_messages,
)


class LangGraphAgent:
    """管理 LangGraph Agent/工作流以及与 LLM 的交互。

    这个类负责创建和管理 LangGraph 工作流，
    包括 LLM 交互、数据库连接和响应处理。
    """

    def __init__(self):
        """初始化 LangGraph Agent 及其必要组件。"""
        # 使用环境特定的 LLM 模型
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=settings.DEFAULT_LLM_TEMPERATURE,
            api_key=settings.LLM_API_KEY,
            max_tokens=settings.MAX_TOKENS,
            **self._get_model_kwargs(),
        ).bind_tools(tools)
        self.tools_by_name = {tool.name: tool for tool in tools}
        self._connection_pool: Optional[AsyncConnectionPool] = None
        self._graph: Optional[CompiledStateGraph] = None

        logger.info("llm_initialized", model=settings.LLM_MODEL, environment=settings.ENVIRONMENT.value)

    def _get_model_kwargs(self) -> Dict[str, Any]:
        """获取环境特定的模型参数。

        Returns:
            Dict[str, Any]: 基于环境的额外模型参数
        """
        model_kwargs = {}

        # 开发环境 - 可以使用较低的速度以节省成本
        if settings.ENVIRONMENT == Environment.DEVELOPMENT:
            model_kwargs["top_p"] = 0.8

        # 生产环境 - 使用更高质量的设置
        elif settings.ENVIRONMENT == Environment.PRODUCTION:
            model_kwargs["top_p"] = 0.95
            model_kwargs["presence_penalty"] = 0.1
            model_kwargs["frequency_penalty"] = 0.1

        return model_kwargs

    async def _get_connection_pool(self) -> AsyncConnectionPool:
        """获取使用环境特定设置的 PostgreSQL 连接池。

        Returns:
            AsyncConnectionPool: PostgreSQL 数据库的连接池。
        """
        if self._connection_pool is None:
            try:
                # 根据环境配置连接池大小
                max_size = settings.POSTGRES_POOL_SIZE

                self._connection_pool = AsyncConnectionPool(
                    settings.POSTGRES_URL,
                    open=False,
                    max_size=max_size,
                    kwargs={
                        "autocommit": True,
                        "connect_timeout": 5,
                        "prepare_threshold": None,
                    },
                )
                await self._connection_pool.open()
                logger.info("connection_pool_created", max_size=max_size, environment=settings.ENVIRONMENT.value)
            except Exception as e:
                logger.error("connection_pool_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # 在生产环境中，我们可能需要优雅降级
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_connection_pool", environment=settings.ENVIRONMENT.value)
                    return None
                raise e
        return self._connection_pool

    async def _chat(self, state: GraphState) -> dict:
        """处理聊天状态并生成响应。

        Args:
            state (GraphState): 当前对话状态。

        Returns:
            dict: 包含新消息的更新状态。
        """
        messages = prepare_messages(state.messages, self.llm, SYSTEM_PROMPT)

        llm_calls_num = 0

        # 根据环境配置重试次数
        max_retries = settings.MAX_LLM_CALL_RETRIES

        for attempt in range(max_retries):
            try:
                generated_state = {"messages": [await self.llm.ainvoke(dump_messages(messages))]}
                logger.info(
                    "llm_response_generated",
                    session_id=state.session_id,
                    llm_calls_num=llm_calls_num + 1,
                    model=settings.LLM_MODEL,
                    environment=settings.ENVIRONMENT.value,
                )
                return generated_state
            except OpenAIError as e:
                logger.error(
                    "llm_call_failed",
                    llm_calls_num=llm_calls_num,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                    environment=settings.ENVIRONMENT.value,
                )
                llm_calls_num += 1

                # 在生产环境中，我们可能需要回退到更可靠的模型
                if settings.ENVIRONMENT == Environment.PRODUCTION and attempt == max_retries - 2:
                    fallback_model = "gpt-4o"
                    logger.warning(
                        "using_fallback_model", model=fallback_model, environment=settings.ENVIRONMENT.value
                    )
                    self.llm.model_name = fallback_model

                continue

        raise Exception(f"在 {max_retries} 次尝试后未能从 LLM 获取响应")

    async def _tool_call(self, state: GraphState) -> GraphState:
        """处理最后一条消息中的工具调用。

        Args:
            state: 包含消息和工具调用的当前代理状态。

        Returns:
            Dict: 包含工具响应的更新消息。
        """
        outputs = []
        for tool_call in state.messages[-1].tool_calls:
            tool_result = await self.tools_by_name[tool_call["name"]].ainvoke(tool_call["args"])
            outputs.append(
                ToolMessage(
                    content=tool_result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        return {"messages": outputs}

    def _should_continue(self, state: GraphState) -> Literal["end", "continue"]:
        """根据最后一条消息决定代理是否应该继续或结束。

        Args:
            state: 包含消息的当前代理状态。

        Returns:
            Literal["end", "continue"]: 如果没有工具调用则返回 "end"，否则返回 "continue"。
        """
        messages = state.messages
        last_message = messages[-1]
        # 如果没有函数调用，则结束
        if not last_message.tool_calls:
            return "end"
        # 否则继续
        else:
            return "continue"

    async def create_graph(self) -> Optional[CompiledStateGraph]:
        """创建和配置 LangGraph 工作流。

        Returns:
            Optional[CompiledStateGraph]: 配置好的 LangGraph 实例，如果初始化失败则返回 None
        """
        if self._graph is None:
            try:
                graph_builder = StateGraph(GraphState)
                graph_builder.add_node("chat", self._chat)
                graph_builder.add_node("tool_call", self._tool_call)
                graph_builder.add_conditional_edges(
                    "chat",
                    self._should_continue,
                    {"continue": "tool_call", "end": END},
                )
                graph_builder.add_edge("tool_call", "chat")
                graph_builder.set_entry_point("chat")
                graph_builder.set_finish_point("chat")

                # 获取连接池（在生产环境中如果数据库不可用可能为 None）
                connection_pool = await self._get_connection_pool()
                if connection_pool:
                    checkpointer = AsyncPostgresSaver(connection_pool)
                    await checkpointer.setup()
                else:
                    # 在生产环境中，如果需要可以继续运行而不使用检查点
                    checkpointer = None
                    if settings.ENVIRONMENT != Environment.PRODUCTION:
                        raise Exception("连接池初始化失败")

                self._graph = graph_builder.compile(
                    checkpointer=checkpointer, name=f"{settings.PROJECT_NAME} Agent ({settings.ENVIRONMENT.value})"
                )

                logger.info(
                    "graph_created",
                    graph_name=f"{settings.PROJECT_NAME} Agent",
                    environment=settings.ENVIRONMENT.value,
                    has_checkpointer=checkpointer is not None,
                )
            except Exception as e:
                logger.error("graph_creation_failed", error=str(e), environment=settings.ENVIRONMENT.value)
                # 在生产环境中，我们不希望应用崩溃
                if settings.ENVIRONMENT == Environment.PRODUCTION:
                    logger.warning("continuing_without_graph")
                    return None
                raise e

        return self._graph

    async def get_response(
        self,
        messages: list[Message],
        session_id: str,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """从 LLM 获取响应。

        Args:
            messages (list[Message]): 要发送给 LLM 的消息。
            session_id (str): 用于 Langfuse 跟踪的会话 ID。
            user_id (Optional[str]): 用于 Langfuse 跟踪的用户 ID。

        Returns:
            list[dict]: LLM 的响应。
        """
        if self._graph is None:
            self._graph = await self.create_graph()
        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [
                CallbackHandler(
                    environment=settings.ENVIRONMENT.value,
                    debug=False,
                    user_id=user_id,
                    session_id=session_id,
                )
            ],
        }
        try:
            response = await self._graph.ainvoke(
                {"messages": dump_messages(messages), "session_id": session_id}, config
            )
            return self.__process_messages(response["messages"])
        except Exception as e:
            logger.error(f"获取响应时出错: {str(e)}")
            raise e

    async def get_stream_response(
        self, messages: list[Message], session_id: str, user_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """从 LLM 获取流式响应。

        Args:
            messages (list[Message]): 要发送给 LLM 的消息。
            session_id (str): 会话的会话 ID。
            user_id (Optional[str]): 会话的用户 ID。

        Yields:
            str: LLM 响应的令牌。
        """
        config = {
            "configurable": {"thread_id": session_id},
            "callbacks": [
                CallbackHandler(
                    environment=settings.ENVIRONMENT.value, debug=False, user_id=user_id, session_id=session_id
                )
            ],
        }
        if self._graph is None:
            self._graph = await self.create_graph()

        try:
            async for token, _ in self._graph.astream(
                {"messages": dump_messages(messages), "session_id": session_id}, config, stream_mode="messages"
            ):
                try:
                    yield token.content
                except Exception as token_error:
                    logger.error("处理令牌时出错", error=str(token_error), session_id=session_id)
                    # 即使当前令牌处理失败，也继续处理下一个
                    continue
        except Exception as stream_error:
            logger.error("流处理时出错", error=str(stream_error), session_id=session_id)
            raise stream_error

    async def get_chat_history(self, session_id: str) -> list[Message]:
        """获取给定线程 ID 的聊天历史。

        Args:
            session_id (str): 会话的会话 ID。

        Returns:
            list[Message]: 聊天历史。
        """
        if self._graph is None:
            self._graph = await self.create_graph()

        state: StateSnapshot = await sync_to_async(self._graph.get_state)(
            config={"configurable": {"thread_id": session_id}}
        )
        return self.__process_messages(state.values["messages"]) if state.values else []

    def __process_messages(self, messages: list[BaseMessage]) -> list[Message]:
        """处理消息列表，转换为 OpenAI 风格的消息格式。

        Args:
            messages (list[BaseMessage]): 要处理的消息列表。

        Returns:
            list[Message]: 处理后的消息列表，只包含助手和用户的消息。
        """
        openai_style_messages = convert_to_openai_messages(messages)
        # 只保留助手和用户的消息
        return [
            Message(**message)
            for message in openai_style_messages
            if message["role"] in ["assistant", "user"] and message["content"]
        ]

    async def clear_chat_history(self, session_id: str) -> None:
        """清除给定线程 ID 的所有聊天历史。

        Args:
            session_id: 要清除历史的会话 ID。

        Raises:
            Exception: 如果清除聊天历史时出错。
        """
        try:
            # 确保在当前事件循环中初始化连接池
            conn_pool = await self._get_connection_pool()

            # 为此特定操作使用新连接
            async with conn_pool.connection() as conn:
                for table in settings.CHECKPOINT_TABLES:
                    try:
                        await conn.execute(f"DELETE FROM {table} WHERE thread_id = %s", (session_id,))
                        logger.info(f"已清除会话 {session_id} 的 {table}")
                    except Exception as e:
                        logger.error(f"清除 {table} 时出错", error=str(e))
                        raise

        except Exception as e:
            logger.error("清除聊天历史失败", error=str(e))
            raise
