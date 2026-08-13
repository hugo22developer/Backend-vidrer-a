from __future__ import annotations
from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Literal

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import CamelModel

Role = Literal["Super Admin", "Editor de Contenido", "Ventas"]
UserStatus = Literal["active", "inactive"]
ProductStatus = Literal["active", "draft"]
PostStatus = Literal["published", "draft"]
InsumoCategoria = Literal[
    "Perfiles de Aluminio",
    "Cristales / Vidrios",
    "Herrajes y Accesorios",
    "Consumibles / Selladores",
]
UnidadMedida = Literal["m", "m²", "pza", "kg"]
InsumoEstado = Literal["active", "discontinued"]
QuoteStatus = Literal["draft", "sent", "accepted", "rejected"]
ContactStatus = Literal["new", "contacted", "closed"]


class AdminUserRead(CamelModel):
    id: str
    name: str
    email: EmailStr
    role: Role
    status: UserStatus
    created_at: date_type


class AdminUserCreate(CamelModel):
    name: str = Field(min_length=2, max_length=160)
    email: EmailStr
    role: Role
    status: UserStatus = "active"
    password: str = Field(default="Admin123!", min_length=8, max_length=128)


class AdminUserUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    email: EmailStr | None = None
    role: Role | None = None
    status: UserStatus | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


class AuthUser(CamelModel):
    id: str
    name: str
    email: EmailStr
    role: Role


class LoginRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenPair(CamelModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: AuthUser


class RefreshRequest(CamelModel):
    refresh_token: str


class CategoryBase(CamelModel):
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    label: str = Field(min_length=2, max_length=160)
    short_label: str = Field(min_length=2, max_length=160)
    eyebrow: str = Field(min_length=1, max_length=160)
    hero_description: str = Field(min_length=1)
    hero_specs: list[str] = Field(default_factory=list)
    accent: str = Field(min_length=1, max_length=255)

    @field_validator("hero_specs")
    @classmethod
    def non_empty_specs(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class CategoryRead(CategoryBase):
    pass


class CategoryUpdate(CamelModel):
    label: str | None = Field(default=None, min_length=2, max_length=160)
    short_label: str | None = Field(default=None, min_length=2, max_length=160)
    eyebrow: str | None = Field(default=None, min_length=1, max_length=160)
    hero_description: str | None = Field(default=None, min_length=1)
    hero_specs: list[str] | None = None
    accent: str | None = Field(default=None, min_length=1, max_length=255)


class ProductBase(CamelModel):
    id: str | None = None
    slug: str = Field(min_length=2, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    category_slug: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=2, max_length=220)
    description: str = Field(min_length=1)
    image: str = Field(min_length=1, max_length=500)
    specs: list[str] = Field(default_factory=list)
    status: ProductStatus = "draft"
    consultations: int = Field(default=0, ge=0)


class ProductRead(ProductBase):
    id: str


class ProductUpdate(CamelModel):
    slug: str | None = Field(default=None, min_length=2, max_length=160)
    category_slug: str | None = Field(default=None, min_length=2, max_length=120)
    title: str | None = Field(default=None, min_length=2, max_length=220)
    description: str | None = Field(default=None, min_length=1)
    image: str | None = Field(default=None, min_length=1, max_length=500)
    specs: list[str] | None = None
    status: ProductStatus | None = None
    consultations: int | None = Field(default=None, ge=0)


class BlogPostBase(CamelModel):
    id: str | None = None
    slug: str = Field(min_length=2, max_length=160, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    category: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=2, max_length=260)
    excerpt: str = Field(min_length=1)
    content: str = Field(default="")
    accent: str = Field(min_length=1, max_length=255)
    status: PostStatus = "draft"
    date: date_type
    views: int = Field(default=0, ge=0)


class BlogPostRead(BlogPostBase):
    id: str


class BlogPostUpdate(CamelModel):
    slug: str | None = Field(default=None, min_length=2, max_length=160)
    category: str | None = Field(default=None, min_length=1, max_length=120)
    title: str | None = Field(default=None, min_length=2, max_length=260)
    excerpt: str | None = Field(default=None, min_length=1)
    content: str | None = None
    accent: str | None = Field(default=None, min_length=1, max_length=255)
    status: PostStatus | None = None
    date: date_type | None = None
    views: int | None = Field(default=None, ge=0)


class InsumoBase(CamelModel):
    id: str | None = None
    sku: str = Field(min_length=2, max_length=80)
    nombre: str = Field(min_length=2, max_length=220)
    categoria: InsumoCategoria
    unidad: UnidadMedida
    costo_unitario: Decimal = Field(gt=0)
    factor_desperdicio: Decimal = Field(ge=0, le=100)
    notas: str = ""
    ultima_modificacion: date_type | None = None
    estado: InsumoEstado = "active"
    pending_review: bool = False


class InsumoRead(InsumoBase):
    id: str
    ultima_modificacion: date_type


class InsumoUpdate(CamelModel):
    sku: str | None = Field(default=None, min_length=2, max_length=80)
    nombre: str | None = Field(default=None, min_length=2, max_length=220)
    categoria: InsumoCategoria | None = None
    unidad: UnidadMedida | None = None
    costo_unitario: Decimal | None = Field(default=None, gt=0)
    factor_desperdicio: Decimal | None = Field(default=None, ge=0, le=100)
    notas: str | None = None
    ultima_modificacion: date_type | None = None
    estado: InsumoEstado | None = None
    pending_review: bool | None = None


class BulkInsumoUpdate(CamelModel):
    scope: InsumoCategoria | Literal["all"]
    percent: Decimal = Field(ge=-100, le=500)


class LineaAluminioRead(CamelModel):
    id: str
    label: str
    description: str
    factor: Decimal


class AcabadoAluminioRead(CamelModel):
    id: str
    label: str
    swatch: str
    extra: Decimal


class TipoVidrioRead(CamelModel):
    id: str
    label: str
    spec: str
    factor: Decimal


class HerrajeRead(CamelModel):
    id: str
    label: str
    price: Decimal


class QuoteConfigRead(CamelModel):
    lineas_aluminio: list[LineaAluminioRead]
    acabados_aluminio: list[AcabadoAluminioRead]
    tipos_vidrio: list[TipoVidrioRead]
    herrajes: list[HerrajeRead]


class QuoteItemCreate(CamelModel):
    category_id: str
    category_label: str
    subtype_label: str
    width_cm: Decimal = Field(gt=0)
    height_cm: Decimal = Field(gt=0)
    linea_id: str
    acabado_id: str
    vidrio_id: str
    herraje_ids: list[str] = Field(default_factory=list)
    quantity: int = Field(ge=1)


class QuoteCreate(CamelModel):
    client_name: str = Field(min_length=2, max_length=180)
    client_phone: str = Field(min_length=6, max_length=40)
    client_email: EmailStr
    client_address: str = Field(default="")
    client_postal_code: str = Field(default="", max_length=20)
    iva_percent: Decimal = Field(default=16, ge=0, le=100)
    items: list[QuoteItemCreate] = Field(min_length=1)


class QuoteItemRead(CamelModel):
    id: str
    category_id: str
    category_label: str
    subtype_label: str
    width_cm: Decimal
    height_cm: Decimal
    area_m2: Decimal
    billable_area_m2: Decimal
    linea_id: str
    linea_label: str
    acabado_id: str
    acabado_label: str
    vidrio_id: str
    vidrio_label: str
    herraje_ids: list[str]
    herraje_labels: list[str]
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class QuoteRead(CamelModel):
    id: str
    folio: str
    client_name: str
    client_phone: str
    client_email: EmailStr
    client_address: str
    client_postal_code: str
    iva_percent: Decimal
    subtotal: Decimal
    iva: Decimal
    total: Decimal
    status: QuoteStatus
    created_by_user_id: str
    created_at: datetime
    items: list[QuoteItemRead] = Field(default_factory=list)


class ContactRequestCreate(CamelModel):
    name: str = Field(min_length=2, max_length=180)
    phone: str = Field(min_length=6, max_length=40)
    email: EmailStr | str = ""
    project_type: str = Field(min_length=1, max_length=120)
    message: str = ""


class ContactRequestRead(ContactRequestCreate):
    id: str
    status: ContactStatus
    created_at: datetime


class DashboardMetrics(CamelModel):
    total_quotes: int
    weekly_activity: list[dict[str, int | str]]
    category_views: list[dict[str, int | str]]
    top_category: dict[str, int | str] | None
    top_product: dict[str, int | str] | None
    top_post: dict[str, int | str] | None

