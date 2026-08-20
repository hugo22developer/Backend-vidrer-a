from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import require_permission
from app.core.rbac import Permission
from app.core.security import hash_password
from app.db.session import get_session
from app.models.entities import (
    AcabadoAluminio,
    AdminUser,
    BlogPost,
    Category,
    Herraje,
    Insumo,
    LineaAluminio,
    Product,
    Quote,
    TipoVidrio,
)
from app.schemas.entities import (
    AcabadoAluminioRead,
    AdminUserCreate,
    AdminUserRead,
    AdminUserUpdate,
    BlogPostBase,
    BlogPostRead,
    BlogPostUpdate,
    BulkInsumoUpdate,
    CategoryBase,
    CategoryRead,
    CategoryUpdate,
    HerrajeRead,
    InsumoBase,
    InsumoRead,
    InsumoUpdate,
    LineaAluminioRead,
    ProductBase,
    ProductRead,
    ProductUpdate,
    QuoteConfigRead,
    QuoteCreate,
    QuoteRead,
    TipoVidrioRead,
)
from app.services.cache import invalidate_dashboard_metrics
from app.services.quote_pdf import render_quote_pdf
from app.services.quotes import build_quote
from fastapi import UploadFile, File
import io
import anyio
import cloudinary.uploader

router = APIRouter(tags=["admin"])


@router.get("/users", response_model=list[AdminUserRead], dependencies=[Depends(require_permission(Permission.USERS_READ))])
async def list_users(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(AdminUser).order_by(AdminUser.created_at.desc()))).scalars().all()


@router.post("/users", response_model=AdminUserRead, dependencies=[Depends(require_permission(Permission.USERS_WRITE))])
async def create_user(payload: AdminUserCreate, session: AsyncSession = Depends(get_session)):
    user = AdminUser(
        name=payload.name,
        email=str(payload.email).lower(),
        role=payload.role,
        status=payload.status,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=AdminUserRead, dependencies=[Depends(require_permission(Permission.USERS_WRITE))])
async def update_user(user_id: str, payload: AdminUserUpdate, session: AsyncSession = Depends(get_session)):
    user = await session.get(AdminUser, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    for key, value in data.items():
        setattr(user, key, str(value).lower() if key == "email" else value)
    if password:
        user.password_hash = hash_password(password)
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=204, dependencies=[Depends(require_permission(Permission.USERS_DELETE))])
async def delete_user(user_id: str, session: AsyncSession = Depends(get_session)):
    user = await session.get(AdminUser, user_id)
    if user:
        await session.delete(user)
        await session.commit()


@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Category).order_by(Category.label))).scalars().all()


@router.post("/categories", response_model=CategoryRead, dependencies=[Depends(require_permission(Permission.CONTENT_WRITE))])
async def create_category(payload: CategoryBase, session: AsyncSession = Depends(get_session)):
    category = Category(**payload.model_dump())
    session.add(category)
    await session.commit()
    await session.refresh(category)
    await invalidate_dashboard_metrics()
    return category


@router.patch("/categories/{slug}", response_model=CategoryRead, dependencies=[Depends(require_permission(Permission.CONTENT_WRITE))])
async def update_category(slug: str, payload: CategoryUpdate, session: AsyncSession = Depends(get_session)):
    category = await session.get(Category, slug)
    if not category:
        raise HTTPException(404, "Categoría no encontrada")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    await session.commit()
    await session.refresh(category)
    await invalidate_dashboard_metrics()
    return category


@router.delete("/categories/{slug}", status_code=204, dependencies=[Depends(require_permission(Permission.CONTENT_DELETE))])
async def delete_category(slug: str, session: AsyncSession = Depends(get_session)):
    category = await session.get(Category, slug)
    if category:
        await session.delete(category)
        await session.commit()
        await invalidate_dashboard_metrics()


@router.get("/products", response_model=list[ProductRead])
async def list_products(category_slug: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    stmt = select(Product).order_by(Product.consultations.desc())
    if category_slug:
        stmt = stmt.where(Product.category_slug == category_slug)
    return (await session.execute(stmt)).scalars().all()


@router.post("/products", response_model=ProductRead, dependencies=[Depends(require_permission(Permission.CONTENT_WRITE))])
async def create_product(payload: ProductBase, session: AsyncSession = Depends(get_session)):
    data = payload.model_dump(exclude={"id"})
    if payload.id:
        data["id"] = payload.id
    product = Product(**data)
    session.add(product)
    await session.commit()
    await session.refresh(product)
    await invalidate_dashboard_metrics()
    return product


@router.patch("/products/{product_id}", response_model=ProductRead, dependencies=[Depends(require_permission(Permission.CONTENT_WRITE))])
async def update_product(product_id: str, payload: ProductUpdate, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(404, "Producto no encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    await session.commit()
    await session.refresh(product)
    await invalidate_dashboard_metrics()
    return product



@router.post("/uploads", dependencies=[Depends(require_permission(Permission.CONTENT_WRITE))])
async def upload_image(file: UploadFile = File(...)):
    """Upload image to Cloudinary and return the secure URL."""
    content = await file.read()

    def _upload():
        # cloudinary.uploader.upload accepts file path or file-like; pass BytesIO
        return cloudinary.uploader.upload(io.BytesIO(content), folder="products")

    try:
        result = await anyio.to_thread.run_sync(_upload)
    except Exception as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"Upload failed: {exc}")

    return {"url": result.get("secure_url")}


@router.delete("/products/{product_id}", status_code=204, dependencies=[Depends(require_permission(Permission.CONTENT_DELETE))])
async def delete_product(product_id: str, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, product_id)
    if product:
        await session.delete(product)
        await session.commit()
        await invalidate_dashboard_metrics()


@router.get("/blog", response_model=list[BlogPostRead])
async def list_blog(status_filter: str | None = Query(default=None, alias="status"), session: AsyncSession = Depends(get_session)):
    stmt = select(BlogPost).order_by(BlogPost.date.desc())
    if status_filter:
        stmt = stmt.where(BlogPost.status == status_filter)
    return (await session.execute(stmt)).scalars().all()


@router.post("/blog", response_model=BlogPostRead, dependencies=[Depends(require_permission(Permission.CONTENT_WRITE))])
async def create_post(payload: BlogPostBase, session: AsyncSession = Depends(get_session)):
    data = payload.model_dump(exclude={"id"})
    if payload.id:
        data["id"] = payload.id
    post = BlogPost(**data)
    session.add(post)
    await session.commit()
    await session.refresh(post)
    await invalidate_dashboard_metrics()
    return post


@router.patch("/blog/{post_id}", response_model=BlogPostRead, dependencies=[Depends(require_permission(Permission.CONTENT_WRITE))])
async def update_post(post_id: str, payload: BlogPostUpdate, session: AsyncSession = Depends(get_session)):
    post = await session.get(BlogPost, post_id)
    if not post:
        raise HTTPException(404, "Artículo no encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(post, key, value)
    await session.commit()
    await session.refresh(post)
    await invalidate_dashboard_metrics()
    return post


@router.delete("/blog/{post_id}", status_code=204, dependencies=[Depends(require_permission(Permission.CONTENT_DELETE))])
async def delete_post(post_id: str, session: AsyncSession = Depends(get_session)):
    post = await session.get(BlogPost, post_id)
    if post:
        await session.delete(post)
        await session.commit()
        await invalidate_dashboard_metrics()


@router.get("/insumos", response_model=list[InsumoRead])
async def list_insumos(categoria: str | None = None, session: AsyncSession = Depends(get_session)):
    stmt = select(Insumo).order_by(Insumo.nombre)
    if categoria:
        stmt = stmt.where(Insumo.categoria == categoria)
    return (await session.execute(stmt)).scalars().all()


@router.post("/insumos", response_model=InsumoRead, dependencies=[Depends(require_permission(Permission.INSUMOS_WRITE))])
async def create_insumo(payload: InsumoBase, session: AsyncSession = Depends(get_session)):
    data = payload.model_dump(exclude={"id"})
    data["ultima_modificacion"] = data["ultima_modificacion"] or date.today()
    if payload.id:
        data["id"] = payload.id
    insumo = Insumo(**data)
    session.add(insumo)
    await session.commit()
    await session.refresh(insumo)
    return insumo


@router.patch("/insumos/{insumo_id}", response_model=InsumoRead, dependencies=[Depends(require_permission(Permission.INSUMOS_WRITE))])
async def update_insumo(insumo_id: str, payload: InsumoUpdate, session: AsyncSession = Depends(get_session)):
    insumo = await session.get(Insumo, insumo_id)
    if not insumo:
        raise HTTPException(404, "Insumo no encontrado")
    data = payload.model_dump(exclude_unset=True)
    data.setdefault("ultima_modificacion", date.today())
    for key, value in data.items():
        setattr(insumo, key, value)
    await session.commit()
    await session.refresh(insumo)
    return insumo


@router.delete("/insumos/{insumo_id}", status_code=204, dependencies=[Depends(require_permission(Permission.INSUMOS_WRITE))])
async def delete_insumo(insumo_id: str, session: AsyncSession = Depends(get_session)):
    insumo = await session.get(Insumo, insumo_id)
    if insumo:
        await session.delete(insumo)
        await session.commit()


@router.post("/insumos/bulk-update", response_model=list[InsumoRead], dependencies=[Depends(require_permission(Permission.INSUMOS_WRITE))])
async def bulk_update_insumos(payload: BulkInsumoUpdate, session: AsyncSession = Depends(get_session)):
    stmt = select(Insumo)
    if payload.scope != "all":
        stmt = stmt.where(Insumo.categoria == payload.scope)
    insumos = (await session.execute(stmt)).scalars().all()
    multiplier = Decimal("1") + (payload.percent / Decimal("100"))
    for insumo in insumos:
        insumo.costo_unitario = (insumo.costo_unitario * multiplier).quantize(Decimal("0.01"))
        insumo.ultima_modificacion = date.today()
    await session.commit()
    return insumos


@router.get("/quote-config", response_model=QuoteConfigRead)
async def quote_config(session: AsyncSession = Depends(get_session)):
    return {
        "lineas_aluminio": (await session.execute(select(LineaAluminio))).scalars().all(),
        "acabados_aluminio": (await session.execute(select(AcabadoAluminio))).scalars().all(),
        "tipos_vidrio": (await session.execute(select(TipoVidrio))).scalars().all(),
        "herrajes": (await session.execute(select(Herraje))).scalars().all(),
    }


@router.post("/quotes", response_model=QuoteRead, dependencies=[Depends(require_permission(Permission.SALES_WRITE))])
async def create_quote(payload: QuoteCreate, user: AdminUser = Depends(require_permission(Permission.SALES_WRITE)), session: AsyncSession = Depends(get_session)):
    quote = await build_quote(session, payload, user.id)
    await session.commit()
    result = await session.execute(select(Quote).options(selectinload(Quote.items)).where(Quote.id == quote.id))
    created = result.scalar_one()
    await invalidate_dashboard_metrics()
    try:
        from app.tasks.jobs import send_quote_email
        send_quote_email.delay(created.id, created.client_email)
    except Exception:
        pass
    return created


@router.get("/quotes", response_model=list[QuoteRead], dependencies=[Depends(require_permission(Permission.SALES_WRITE))])
async def list_quotes(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Quote).options(selectinload(Quote.items)).order_by(Quote.created_at.desc()))).scalars().all()


@router.get("/quotes/{quote_id}", response_model=QuoteRead, dependencies=[Depends(require_permission(Permission.SALES_WRITE))])
async def get_quote(quote_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Quote).options(selectinload(Quote.items)).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(404, "Cotización no encontrada")
    return quote


@router.get("/quotes/{quote_id}/pdf", dependencies=[Depends(require_permission(Permission.SALES_WRITE))])
async def get_quote_pdf(quote_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Quote).options(selectinload(Quote.items)).where(Quote.id == quote_id))
    quote = result.scalar_one_or_none()
    if not quote:
        raise HTTPException(404, "Cotización no encontrada")
    try:
        pdf_bytes = await anyio.to_thread.run_sync(render_quote_pdf, quote)
    except Exception as exc:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, f"No se pudo generar el PDF: {exc}") from exc
    filename = f"{quote.folio}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )

