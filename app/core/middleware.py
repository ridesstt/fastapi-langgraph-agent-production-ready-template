"""用于跟踪指标和其他横切关注点的自定义中间件。"""

import time
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.metrics import (
    http_requests_total,  # HTTP请求总数计数器
    http_request_duration_seconds,  # HTTP请求持续时间指标
    db_connections,  # 数据库连接指标
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """用于跟踪HTTP请求指标的中间件。
    
    这个中间件用于收集和记录以下指标：
    - HTTP请求总数
    - 请求处理时间
    - 请求状态码
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """为每个请求跟踪指标。

        Args:
            request: 传入的HTTP请求对象
            call_next: 下一个中间件或路由处理函数

        Returns:
            Response: 应用程序的响应对象
        """
        # 记录请求开始时间
        start_time = time.time()

        try:
            # 调用下一个中间件或路由处理函数
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            # 如果发生异常，设置状态码为500
            status_code = 500
            raise
        finally:
            # 计算请求处理时间
            duration = time.time() - start_time

            # 记录请求总数指标
            # 包含请求方法、端点路径和状态码标签
            http_requests_total.labels(method=request.method, endpoint=request.url.path, status=status_code).inc()

            # 记录请求处理时间指标
            # 包含请求方法和端点路径标签
            http_request_duration_seconds.labels(method=request.method, endpoint=request.url.path).observe(duration)

        return response
