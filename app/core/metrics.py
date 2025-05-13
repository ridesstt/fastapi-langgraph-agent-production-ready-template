"""Prometheus metrics configuration for the application.

此模块用于设置和配置应用程序的 Prometheus 监控指标。
This module sets up and configures Prometheus metrics for monitoring the application.
"""

from prometheus_client import Counter, Histogram, Gauge
from starlette_prometheus import metrics, PrometheusMiddleware

# 请求指标 - Request metrics
# 记录 HTTP 请求总数，包含方法、端点和状态码标签
http_requests_total = Counter("http_requests_total", "Total number of HTTP requests", ["method", "endpoint", "status"])

# 记录 HTTP 请求持续时间，包含方法和端点标签
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds", "HTTP request duration in seconds", ["method", "endpoint"]
)

# 数据库指标 - Database metrics
# 记录活跃的数据库连接数
db_connections = Gauge("db_connections", "Number of active database connections")

# 自定义业务指标 - Custom business metrics
# 记录已处理的订单总数
orders_processed = Counter("orders_processed_total", "Total number of orders processed")


def setup_metrics(app):
    """设置 Prometheus 指标中间件和端点。
    Set up Prometheus metrics middleware and endpoints.

    Args:
        app: FastAPI 应用实例
        app: FastAPI application instance
    """
    # 添加 Prometheus 中间件
    app.add_middleware(PrometheusMiddleware)

    # 添加指标端点
    app.add_route("/metrics", metrics)
