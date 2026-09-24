import base64
import binascii

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import contact_rate_limit
from app.core.cloudinary import upload_image_bytes
from app.db.session import get_session
from app.models.entities import BlogPost, Category, ContactRequest, Product
from app.schemas.entities import (
    BlogPostRead,
    CategoryRead,
    ContactRequestCreate,
    ContactRequestRead,
    ProductRead,
    SimulationRequest,
    SimulationResponse,
)
from app.services.gemini_service import MAX_IMAGE_BYTES, generate_product_simulation

router = APIRouter(prefix="/public", tags=["public"])


def _decode_base64_image(value: str, field_name: str) -> bytes:
    raw_value = value.strip()
    if "," in raw_value and raw_value.lower().startswith("data:"):
        raw_value = raw_value.split(",", 1)[1]
    if len(raw_value) > MAX_IMAGE_BYTES * 4 // 3 + 4:
        raise HTTPException(status_code=413, detail=f"{field_name} supera el limite de 8 MB.")
    try:
        decoded = base64.b64decode(raw_value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} no es una imagen base64 valida.") from exc
    if len(decoded) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail=f"{field_name} supera el limite de 8 MB.")
    return decoded


def _simulation_prompt_for_product(product: Product) -> str:
    if product.simulation_prompt and product.simulation_prompt.strip():
        return product.simulation_prompt.strip()
    specs = ", ".join(product.specs or [])
    return (
        f"Instalar {product.title} en la zona marcada. "
        f"Descripcion: {product.description}. "
        f"Especificaciones: {specs or 'vidrio y aluminio a medida'}."
    )


@router.get("/categories", response_model=list[CategoryRead])
async def public_categories(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Category).order_by(Category.label))).scalars().all()


@router.get("/products", response_model=list[ProductRead])
async def public_products(category_slug: str | None = Query(default=None), session: AsyncSession = Depends(get_session)):
    stmt = select(Product).where(Product.status == "active").order_by(Product.consultations.desc())
    if category_slug:
        stmt = stmt.where(Product.category_slug == category_slug)
    return (await session.execute(stmt)).scalars().all()


@router.post("/simulate", response_model=SimulationResponse)
async def simulate_product(payload: SimulationRequest, session: AsyncSession = Depends(get_session)):
    product = await session.get(Product, payload.product_id)
    if not product or product.status != "active":
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    client_image_bytes = _decode_base64_image(payload.client_image_base64, "client_image_base64")
    mask_bytes = _decode_base64_image(payload.mask_base64, "mask_base64")
    prompt = _simulation_prompt_for_product(product)

    try:
        try:
            simulated_image_bytes = await generate_product_simulation(
                client_image_bytes=client_image_bytes,
                mask_bytes=mask_bytes,
                prompt_text=prompt,
            )
        except ValueError as exc:
            raise HTTPException(status_code=413, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="No se pudo generar la simulacion con Gemini.") from exc

        try:
            simulation_url = upload_image_bytes(simulated_image_bytes, folder="cercho/simulations")
        except Exception as exc:
            raise HTTPException(status_code=500, detail="No se pudo subir la simulacion a Cloudinary.") from exc

        return SimulationResponse(simulation_url=simulation_url, product_id=product.id)
    finally:
        del client_image_bytes
        del mask_bytes
        if "simulated_image_bytes" in locals():
            del simulated_image_bytes


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
