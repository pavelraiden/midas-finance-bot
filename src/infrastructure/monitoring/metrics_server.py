"""
Prometheus Metrics HTTP Server
Exposes /metrics endpoint for Prometheus scraping
"""
import asyncio
from aiohttp import web
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from infrastructure.logging_config import get_logger

logger = get_logger(__name__)


async def metrics_handler(request):
    """
    Handle /metrics endpoint for Prometheus.
    
    Returns:
        Response with Prometheus metrics in text format
    """
    metrics = generate_latest()
    return web.Response(body=metrics, content_type=CONTENT_TYPE_LATEST)


async def health_handler(request):
    """
    Handle /health endpoint for health checks.
    
    Returns:
        JSON response with health status
    """
    return web.json_response({
        "status": "healthy",
        "service": "midas-finance-bot"
    })


async def start_metrics_server(host: str = "0.0.0.0", port: int = 8000):
    """
    Start Prometheus metrics HTTP server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
    """
    app = web.Application()
    app.router.add_get('/metrics', metrics_handler)
    app.router.add_get('/health', health_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, host, port)
    await site.start()
    
    logger.info(f"✅ Prometheus metrics server started on http://{host}:{port}/metrics")
    logger.info(f"✅ Health check endpoint: http://{host}:{port}/health")
    
    return runner


async def stop_metrics_server(runner):
    """
    Stop Prometheus metrics HTTP server.
    
    Args:
        runner: AppRunner instance from start_metrics_server
    """
    await runner.cleanup()
    logger.info("🛑 Prometheus metrics server stopped")


if __name__ == "__main__":
    # Test server
    async def main():
        runner = await start_metrics_server()
        try:
            await asyncio.sleep(3600)  # Run for 1 hour
        finally:
            await stop_metrics_server(runner)
    
    asyncio.run(main())
