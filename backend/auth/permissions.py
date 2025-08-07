def get_role_description(role):
    """Obtener descripción del rol"""
    descriptions = {
        "admin": "Administrador del Sistema",
        "gerente": "Gerente de Sucursal", 
        "farmaceutico": "Farmacéutico Responsable",
        "empleado": "Empleado General"
    }
    return descriptions.get(role, "Usuario")