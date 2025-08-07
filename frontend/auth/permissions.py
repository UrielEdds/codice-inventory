def get_permissions_by_role(role: str) -> list:
    """Obtener permisos basados en el rol del usuario"""
    permissions = {
        "admin": [
            "admin.full",
            "dashboard.full", 
            "inventario.full", 
            "analisis.full",
            "ia.full", 
            "ingreso.full", 
            "salidas.full", 
            "users.manage",
            "reports.full"
        ],
        "gerente": [
            "dashboard.full", 
            "inventario.full", 
            "analisis.full",
            "ia.limited", 
            "ingreso.full", 
            "salidas.full",
            "reports.view"
        ],
        "farmaceutico": [
            "dashboard.basic", 
            "inventario.read", 
            "inventario.update",
            "ingreso.full", 
            "salidas.full",
            "reports.basic"
        ],
        "empleado": [
            "dashboard.basic", 
            "inventario.read", 
            "salidas.limited",
            "reports.basic"
        ]
    }
    
    return permissions.get(role, [])

def get_tab_permissions() -> dict:
    """Mapeo de pestañas con permisos requeridos"""
    return {
        "Dashboard Principal": "dashboard.basic",
        "Inventario Detallado": "inventario.read", 
        "Análisis Comparativo": "analisis.full",
        "IA & Predicciones": "ia.limited",
        "Ingreso Inventario": "ingreso.full",
        "Salidas de Inventario": "salidas.limited"
    }

def filter_tabs_by_permissions(user_permissions: list) -> list:
    """Filtrar pestañas basadas en permisos del usuario"""
    tab_permissions = get_tab_permissions()
    allowed_tabs = []
    
    for tab_name, required_permission in tab_permissions.items():
        if required_permission in user_permissions or "admin.full" in user_permissions:
            allowed_tabs.append(tab_name)
    
    return allowed_tabs

def get_role_description(role: str) -> str:
    """Obtener descripción del rol"""
    descriptions = {
        "admin": "👑 Administrador del Sistema",
        "gerente": "🏢 Gerente de Sucursal", 
        "farmaceutico": "⚕️ Farmacéutico Responsable",
        "empleado": "👤 Empleado"
    }
    
    return descriptions.get(role, "👤 Usuario")

def get_role_color(role: str) -> str:
    """Obtener color del rol para UI"""
    colors = {
        "admin": "#ef4444",      # Rojo
        "gerente": "#2563eb",    # Azul
        "farmaceutico": "#10b981", # Verde
        "empleado": "#64748b"    # Gris
    }
    
    return colors.get(role, "#64748b")

def get_role_description(role):
    """Obtener descripción del rol"""
    descriptions = {
        "admin": "Administrador del Sistema",
        "gerente": "Gerente de Sucursal", 
        "farmaceutico": "Farmacéutico Responsable",
        "empleado": "Empleado General"
    }
    return descriptions.get(role, "Usuario")