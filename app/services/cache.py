from app.db.redis import redis_client

DASHBOARD_KEY = "dashboard:metrics"


async def invalidate_dashboard_metrics() -> None:
    if redis_client is not None:
        await redis_client.delete(DASHBOARD_KEY)

