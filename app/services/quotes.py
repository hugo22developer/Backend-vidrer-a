from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AcabadoAluminio, Herraje, LineaAluminio, Quote, QuoteItem, TipoVidrio
from app.schemas.entities import QuoteCreate, QuoteItemCreate

MIN_BILLABLE_AREA_M2 = Decimal("0.36")


def round_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


async def calc_unit_price(session: AsyncSession, item: QuoteItemCreate) -> dict:
    linea = await session.get(LineaAluminio, item.linea_id)
    acabado = await session.get(AcabadoAluminio, item.acabado_id)
    vidrio = await session.get(TipoVidrio, item.vidrio_id)
    if not linea or not acabado or not vidrio:
        raise HTTPException(status_code=422, detail="Configuración de cotización inválida")

    herrajes = []
    if item.herraje_ids:
        result = await session.execute(select(Herraje).where(Herraje.id.in_(item.herraje_ids)))
        herrajes = list(result.scalars().all())
        if len(herrajes) != len(set(item.herraje_ids)):
            raise HTTPException(status_code=422, detail="Herraje inválido")

    area_m2 = (item.width_cm / Decimal("100")) * (item.height_cm / Decimal("100"))
    billable_area_m2 = max(area_m2, MIN_BILLABLE_AREA_M2)
    base = billable_area_m2 * (linea.factor + vidrio.factor + acabado.extra)
    herrajes_total = sum((h.price for h in herrajes), Decimal("0"))
    unit_price = round_money(base + herrajes_total)
    return {
        "area_m2": area_m2,
        "billable_area_m2": billable_area_m2,
        "unit_price": unit_price,
        "linea": linea,
        "acabado": acabado,
        "vidrio": vidrio,
        "herrajes": herrajes,
    }


async def next_folio(session: AsyncSession) -> str:
    year = datetime.now(UTC).year
    prefix = f"COT-{year}-"
    result = await session.execute(select(func.count(Quote.id)).where(Quote.folio.like(f"{prefix}%")))
    sequential = int(result.scalar_one()) + 1
    return f"{prefix}{sequential:04d}"


async def build_quote(session: AsyncSession, payload: QuoteCreate, user_id: str) -> Quote:
    quote = Quote(
        folio=await next_folio(session),
        client_name=payload.client_name,
        client_phone=payload.client_phone,
        client_email=str(payload.client_email),
        client_address=payload.client_address,
        client_postal_code=payload.client_postal_code,
        iva_percent=payload.iva_percent,
        subtotal=Decimal("0"),
        iva=Decimal("0"),
        total=Decimal("0"),
        status="sent",
        created_by_user_id=user_id,
    )
    items: list[QuoteItem] = []
    subtotal = Decimal("0")
    for payload_item in payload.items:
        priced = await calc_unit_price(session, payload_item)
        item_subtotal = priced["unit_price"] * payload_item.quantity
        subtotal += item_subtotal
        items.append(
            QuoteItem(
                category_id=payload_item.category_id,
                category_label=payload_item.category_label,
                subtype_label=payload_item.subtype_label,
                width_cm=payload_item.width_cm,
                height_cm=payload_item.height_cm,
                area_m2=priced["area_m2"],
                billable_area_m2=priced["billable_area_m2"],
                linea_id=priced["linea"].id,
                linea_label=priced["linea"].label,
                acabado_id=priced["acabado"].id,
                acabado_label=priced["acabado"].label,
                vidrio_id=priced["vidrio"].id,
                vidrio_label=priced["vidrio"].label,
                herraje_ids=payload_item.herraje_ids,
                herraje_labels=[h.label for h in priced["herrajes"]],
                quantity=payload_item.quantity,
                unit_price=priced["unit_price"],
                subtotal=item_subtotal,
            )
        )
    quote.items = items
    session.add(quote)
    iva = round_money(subtotal * (payload.iva_percent / Decimal("100")))
    quote.subtotal = subtotal
    quote.iva = iva
    quote.total = subtotal + iva
    return quote

