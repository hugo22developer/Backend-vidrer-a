"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    role_enum = postgresql.ENUM("Super Admin", "Editor de Contenido", "Ventas", name="role_enum", create_type=False)
    user_status_enum = postgresql.ENUM("active", "inactive", name="user_status_enum", create_type=False)
    product_status_enum = postgresql.ENUM("active", "draft", name="product_status_enum", create_type=False)
    post_status_enum = postgresql.ENUM("published", "draft", name="post_status_enum", create_type=False)
    insumo_categoria_enum = postgresql.ENUM("Perfiles de Aluminio", "Cristales / Vidrios", "Herrajes y Accesorios", "Consumibles / Selladores", name="insumo_categoria_enum", create_type=False)
    unidad_medida_enum = postgresql.ENUM("m", "m²", "pza", "kg", name="unidad_medida_enum", create_type=False)
    insumo_estado_enum = postgresql.ENUM("active", "discontinued", name="insumo_estado_enum", create_type=False)
    quote_status_enum = postgresql.ENUM("draft", "sent", "accepted", "rejected", name="quote_status_enum", create_type=False)
    contact_status_enum = postgresql.ENUM("new", "contacted", "closed", name="contact_status_enum", create_type=False)

    bind = op.get_bind()
    for enum in [role_enum, user_status_enum, product_status_enum, post_status_enum, insumo_categoria_enum, unidad_medida_enum, insumo_estado_enum, quote_status_enum, contact_status_enum]:
        enum.create(bind, checkfirst=True)

    op.create_table("admin_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", role_enum, nullable=False),
        sa.Column("status", user_status_enum, nullable=False),
        sa.Column("created_at", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)
    op.create_table("categories",
        sa.Column("slug", sa.String(120), primary_key=True),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("short_label", sa.String(160), nullable=False),
        sa.Column("eyebrow", sa.String(160), nullable=False),
        sa.Column("hero_description", sa.Text(), nullable=False),
        sa.Column("hero_specs", postgresql.JSONB(), nullable=False),
        sa.Column("accent", sa.String(255), nullable=False),
    )
    op.create_table("blog_posts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("category", sa.String(120), nullable=False),
        sa.Column("title", sa.String(260), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("accent", sa.String(255), nullable=False),
        sa.Column("status", post_status_enum, nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"], unique=True)
    op.create_table("insumos",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("nombre", sa.String(220), nullable=False),
        sa.Column("categoria", insumo_categoria_enum, nullable=False),
        sa.Column("unidad", unidad_medida_enum, nullable=False),
        sa.Column("costo_unitario", sa.Numeric(12, 2), nullable=False),
        sa.Column("factor_desperdicio", sa.Numeric(6, 2), nullable=False),
        sa.Column("notas", sa.Text(), nullable=False),
        sa.Column("ultima_modificacion", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("estado", insumo_estado_enum, nullable=False),
        sa.Column("pending_review", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_insumos_sku", "insumos", ["sku"], unique=True)
    op.create_table("lineas_aluminio",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("label", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("factor", sa.Numeric(12, 2), nullable=False),
    )
    op.create_table("acabados_aluminio",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("label", sa.String(180), nullable=False),
        sa.Column("swatch", sa.String(255), nullable=False),
        sa.Column("extra", sa.Numeric(12, 2), nullable=False),
    )
    op.create_table("tipos_vidrio",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("label", sa.String(180), nullable=False),
        sa.Column("spec", sa.Text(), nullable=False),
        sa.Column("factor", sa.Numeric(12, 2), nullable=False),
    )
    op.create_table("herrajes",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("label", sa.String(180), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
    )
    op.create_table("products",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("category_slug", sa.String(120), sa.ForeignKey("categories.slug", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("image", sa.String(500), nullable=False),
        sa.Column("specs", postgresql.JSONB(), nullable=False),
        sa.Column("status", product_status_enum, nullable=False),
        sa.Column("consultations", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("category_slug", "slug", name="uq_products_category_slug"),
    )
    op.create_index("ix_products_category_slug", "products", ["category_slug"])
    op.create_table("refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("family_id", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=True)
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_table("quotes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("folio", sa.String(40), nullable=False),
        sa.Column("client_name", sa.String(180), nullable=False),
        sa.Column("client_phone", sa.String(40), nullable=False),
        sa.Column("client_email", sa.String(255), nullable=False),
        sa.Column("client_address", sa.Text(), nullable=False),
        sa.Column("client_postal_code", sa.String(20), nullable=False),
        sa.Column("iva_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("iva", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", quote_status_enum, nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("admin_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_quotes_folio", "quotes", ["folio"], unique=True)
    op.create_table("quote_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("quote_id", sa.String(36), sa.ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category_id", sa.String(80), nullable=False),
        sa.Column("category_label", sa.String(180), nullable=False),
        sa.Column("subtype_label", sa.String(180), nullable=False),
        sa.Column("width_cm", sa.Numeric(8, 2), nullable=False),
        sa.Column("height_cm", sa.Numeric(8, 2), nullable=False),
        sa.Column("area_m2", sa.Numeric(10, 4), nullable=False),
        sa.Column("billable_area_m2", sa.Numeric(10, 4), nullable=False),
        sa.Column("linea_id", sa.String(80), nullable=False),
        sa.Column("linea_label", sa.String(180), nullable=False),
        sa.Column("acabado_id", sa.String(80), nullable=False),
        sa.Column("acabado_label", sa.String(180), nullable=False),
        sa.Column("vidrio_id", sa.String(80), nullable=False),
        sa.Column("vidrio_label", sa.String(180), nullable=False),
        sa.Column("herraje_ids", postgresql.JSONB(), nullable=False),
        sa.Column("herraje_labels", postgresql.JSONB(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
    )
    op.create_index("ix_quote_items_quote_id", "quote_items", ["quote_id"])
    op.create_table("contact_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("phone", sa.String(40), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("project_type", sa.String(120), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", contact_status_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

def downgrade() -> None:
    for table in ["contact_requests", "quote_items", "quotes", "refresh_tokens", "products", "herrajes", "tipos_vidrio", "acabados_aluminio", "lineas_aluminio", "insumos", "blog_posts", "categories", "admin_users"]:
        op.drop_table(table)
    for enum_name in ["contact_status_enum", "quote_status_enum", "insumo_estado_enum", "unidad_medida_enum", "insumo_categoria_enum", "post_status_enum", "product_status_enum", "user_status_enum", "role_enum"]:
        postgresql.ENUM(name=enum_name, create_type=False).drop(op.get_bind(), checkfirst=True)

