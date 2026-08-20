import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.rbac import Permission
from app.db.redis import redis_client
from app.db.session import get_session
from app.models.entities import BlogPost, Category, Product, Quote
from app.schemas.entities import DashboardMetrics
from app.services.cache import DASHBOARD_KEY

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetrics, dependencies=[Depends(require_permission(Permission.USERS_READ))])
async def metrics(session: AsyncSession = Depends(get_session)):
    if redis_client is not None:
        cached = await redis_client.get(DASHBOARD_KEY)
        if cached:
            return json.loads(cached)

    total_quotes = await session.scalar(select(func.count(Quote.id))) or 0
    today = datetime.now(UTC).date()
    labels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    weekly_activity = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = await session.scalar(
            select(func.count(Quote.id)).where(func.date(Quote.created_at) == day)
        ) or 0
        weekly_activity.append({"label": labels[day.weekday()], "quotes": count})

    categories = (await session.execute(select(Category))).scalars().all()
    products = (await session.execute(select(Product))).scalars().all()
    posts = (await session.execute(select(BlogPost))).scalars().all()
    category_views = [
        {
            "slug": cat.slug,
            "shortLabel": cat.short_label,
            "label": cat.label,
            "total": sum(p.consultations for p in products if p.category_slug == cat.slug),
        }
        for cat in categories
    ]
    top_category = max(category_views, key=lambda item: item["total"], default=None)
    top_product_obj = max(products, key=lambda item: item.consultations, default=None)
    top_post_obj = max(posts, key=lambda item: item.views, default=None)
    payload = {
        "totalQuotes": total_quotes,
        "weeklyActivity": weekly_activity,
        "categoryViews": category_views,
        "topCategory": top_category,
        "topProduct": {"title": top_product_obj.title, "consultations": top_product_obj.consultations} if top_product_obj else None,
        "topPost": {"title": top_post_obj.title, "views": top_post_obj.views} if top_post_obj else None,
    }
    if redis_client is not None:
        await redis_client.setex(DASHBOARD_KEY, 60, json.dumps(payload))
    return payload

