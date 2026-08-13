from app.core.rbac import Permission, has_permission
from app.schemas.entities import BlogPostUpdate
from app.services.quotes import MIN_BILLABLE_AREA_M2


def test_blog_post_update_schema_loads():
    payload = {"date": "2026-01-15", "title": "Nuevo artículo"}
    model = BlogPostUpdate.model_validate(payload)
    assert model.date.isoformat() == "2026-01-15"
    assert model.title == "Nuevo artículo"


def test_rbac_roles_are_distinct():
    assert has_permission("Super Admin", Permission.USERS_DELETE)
    assert has_permission("Editor de Contenido", Permission.CONTENT_WRITE)
    assert not has_permission("Editor de Contenido", Permission.INSUMOS_WRITE)
    assert has_permission("Ventas", Permission.SALES_WRITE)
    assert not has_permission("Ventas", Permission.CONTENT_DELETE)


def test_quote_minimum_area_constant_matches_frontend():
    assert str(MIN_BILLABLE_AREA_M2) == "0.36"

