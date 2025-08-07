from .auth_manager import get_auth_manager, AuthManager
from .login import show_login_page, show_user_info, require_auth
from .permissions import (
    get_permissions_by_role, 
    get_tab_permissions, 
    filter_tabs_by_permissions,
    get_role_description,
    get_role_color
)

__all__ = [
    "get_auth_manager",
    "AuthManager", 
    "show_login_page",
    "show_user_info",
    "require_auth",
    "get_permissions_by_role",
    "get_tab_permissions", 
    "filter_tabs_by_permissions",
    "get_role_description",
    "get_role_color"
]