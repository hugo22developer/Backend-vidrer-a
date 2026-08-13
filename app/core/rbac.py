from enum import StrEnum


class Permission(StrEnum):
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    USERS_DELETE = "users:delete"
    CONTENT_WRITE = "content:write"
    CONTENT_DELETE = "content:delete"
    SALES_WRITE = "sales:write"
    INSUMOS_WRITE = "insumos:write"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "Super Admin": set(Permission),
    "Editor de Contenido": {
        Permission.USERS_READ,
        Permission.CONTENT_WRITE,
        Permission.CONTENT_DELETE,
    },
    "Ventas": {
        Permission.USERS_READ,
        Permission.SALES_WRITE,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())

