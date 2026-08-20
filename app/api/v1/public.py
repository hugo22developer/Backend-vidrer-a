from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import contact_rate_limit
from app.db.session import get_session
from app.models.entities import BlogPost, Category, ContactRequest, Product
from app.schemas.entities import BlogPostRead, CategoryRead, ContactRequestCreate, ContactRequestRead, ProductRead

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/categories", response_model=list[CategoryRead])
async def public_categories(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Category).order_by(Category.label))).scalars().all()


@router.get("/products", response_model=list[ProductRead])
async def public_products(category_slug: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    stmt = select(Product).where(Product.status == "active").order_by(Product.consultations.desc())
    if category_slug:
        stmt = stmt.where(Product.category_slug == category_slug)
    return (await session.execute(stmt)).scalars().all()


@router.get("/blog", response_model=list[BlogPostRead])
async def public_blog(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(BlogPost).where(BlogPost.status == "published").order_by(BlogPost.date.desc()))).scalars().all()


@router.post("/contact", response_model=ContactRequestRead, dependencies=[Depends(contact_rate_limit)])
async def create_contact(payload: ContactRequestCreate, session: AsyncSession = Depends(get_session)):
    contact = ContactRequest(
        name=payload.name,
        phone=payload.phone,
        email=str(payload.email),
        project_type=payload.project_type,
        message=payload.message,
        status="new",
    )
    session.add(contact)
    await session.commit()
    await session.refresh(contact)
    if contact.email:
        try:
            from app.tasks.jobs import send_contact_email
            send_contact_email.delay(contact.id, contact.email)
        except Exception:
            pass
    return contact

