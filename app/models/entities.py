import enum
from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def uuid_str() -> str:
    return str(uuid4())

def _use_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [e.value for e in enum_cls]


class RoleEnum(str, enum.Enum):
    super_admin = "Super Admin"
    editor_de_contenido = "Editor de Contenido"
    ventas = "Ventas"

class UserStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class ProductStatusEnum(str, enum.Enum):
    active = "active"
    draft = "draft"


class PostStatusEnum(str, enum.Enum):
    published = "published"
    draft = "draft"


class InsumoCategoriaEnum(str, enum.Enum):
    perfiles = "Perfiles de Aluminio"
    cristales = "Cristales / Vidrios"
    herrajes = "Herrajes y Accesorios"
    consumibles = "Consumibles / Selladores"


class UnidadMedidaEnum(str, enum.Enum):
    m = "m"
    m2 = "m²"
    pza = "pza"
    kg = "kg"


class InsumoEstadoEnum(str, enum.Enum):
    active = "active"
    discontinued = "discontinued"


class QuoteStatusEnum(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    accepted = "accepted"
    rejected = "rejected"


class ContactStatusEnum(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    closed = "closed"


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[RoleEnum] = mapped_column( Enum(RoleEnum, name="role_enum", values_callable=_use_values), nullable=False, )    
    status: Mapped[UserStatusEnum] = mapped_column(Enum(UserStatusEnum, name="user_status_enum", values_callable=_use_values), nullable=False)
    created_at: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="created_by")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    user_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_jti: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped[AdminUser] = relationship(back_populates="refresh_tokens")


class Category(Base):
    __tablename__ = "categories"

    slug: Mapped[str] = mapped_column(String(120), primary_key=True)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    short_label: Mapped[str] = mapped_column(String(160), nullable=False)
    eyebrow: Mapped[str] = mapped_column(String(160), nullable=False)
    hero_description: Mapped[str] = mapped_column(Text, nullable=False)
    hero_specs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    accent: Mapped[str] = mapped_column(String(255), nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("category_slug", "slug", name="uq_products_category_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    category_slug: Mapped[str] = mapped_column(ForeignKey("categories.slug", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    image: Mapped[str] = mapped_column(String(500), nullable=False)
    specs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[ProductStatusEnum] = mapped_column( Enum(ProductStatusEnum, name="product_status_enum", values_callable=_use_values), nullable=False, )
    consultations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    category: Mapped[Category] = relationship(back_populates="products")


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    slug: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(260), nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    accent: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[PostStatusEnum] = mapped_column(Enum(PostStatusEnum, name="post_status_enum", values_callable=_use_values), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    views: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Insumo(Base):
    __tablename__ = "insumos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    sku: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(220), nullable=False)
    categoria: Mapped[InsumoCategoriaEnum] = mapped_column(Enum(InsumoCategoriaEnum, name="insumo_categoria_enum", values_callable=_use_values), nullable=False)
    unidad: Mapped[UnidadMedidaEnum] = mapped_column(Enum(UnidadMedidaEnum, name="unidad_medida_enum", values_callable=_use_values), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    factor_desperdicio: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    notas: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ultima_modificacion: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    estado: Mapped[InsumoEstadoEnum] = mapped_column(Enum(InsumoEstadoEnum, name="insumo_estado_enum", values_callable=_use_values), nullable=False)
    pending_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class LineaAluminio(Base):
    __tablename__ = "lineas_aluminio"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    factor: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class AcabadoAluminio(Base):
    __tablename__ = "acabados_aluminio"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    swatch: Mapped[str] = mapped_column(String(255), nullable=False)
    extra: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class TipoVidrio(Base):
    __tablename__ = "tipos_vidrio"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    spec: Mapped[str] = mapped_column(Text, nullable=False)
    factor: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class Herraje(Base):
    __tablename__ = "herrajes"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)


class Quote(Base):
    __tablename__ = "quotes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    folio: Mapped[str] = mapped_column(String(40), unique=True, nullable=False, index=True)
    client_name: Mapped[str] = mapped_column(String(180), nullable=False)
    client_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    client_email: Mapped[str] = mapped_column(String(255), nullable=False)
    client_address: Mapped[str] = mapped_column(Text, nullable=False)
    client_postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    iva_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    iva: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[QuoteStatusEnum] = mapped_column(Enum(QuoteStatusEnum, name="quote_status_enum", values_callable=_use_values), nullable=False)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    created_by: Mapped[AdminUser] = relationship(back_populates="quotes")
    items: Mapped[list["QuoteItem"]] = relationship(back_populates="quote", cascade="all, delete-orphan")


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    quote_id: Mapped[str] = mapped_column(ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id: Mapped[str] = mapped_column(String(80), nullable=False)
    category_label: Mapped[str] = mapped_column(String(180), nullable=False)
    subtype_label: Mapped[str] = mapped_column(String(180), nullable=False)
    width_cm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    area_m2: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    billable_area_m2: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    linea_id: Mapped[str] = mapped_column(String(80), nullable=False)
    linea_label: Mapped[str] = mapped_column(String(180), nullable=False)
    acabado_id: Mapped[str] = mapped_column(String(80), nullable=False)
    acabado_label: Mapped[str] = mapped_column(String(180), nullable=False)
    vidrio_id: Mapped[str] = mapped_column(String(80), nullable=False)
    vidrio_label: Mapped[str] = mapped_column(String(180), nullable=False)
    herraje_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    herraje_labels: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    quote: Mapped[Quote] = relationship(back_populates="items")


class ContactRequest(Base):
    __tablename__ = "contact_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    project_type: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ContactStatusEnum] = mapped_column(Enum(ContactStatusEnum, name="contact_status_enum", values_callable=_use_values), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

