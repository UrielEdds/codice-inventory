from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional, Dict, List
import os

# Configuración
SECRET_KEY = os.getenv("SECRET_KEY", "mi-secreto-super-seguro-jwt-2025")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 horas

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Generar hash de contraseña"""
    return pwd_context.hash(password)

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crear token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[Dict]:
    """Verificar y decodificar token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        return payload
    except JWTError:
        return None

def get_user_permissions(rol: str) -> List[str]:
    """Obtener permisos basados en el rol"""
    permissions = {
        "admin": [
            "dashboard.full", "inventario.full", "analisis.full", 
            "ia.full", "ingreso.full", "salidas.full", "users.manage"
        ],
        "gerente": [
            "dashboard.full", "inventario.full", "analisis.full",
            "ia.limited", "ingreso.full", "salidas.full"
        ],
        "farmaceutico": [
            "dashboard.basic", "inventario.read", "ingreso.full", "salidas.full"
        ],
        "empleado": [
            "dashboard.basic", "inventario.read", "salidas.limited"
        ]
    }
    
    return permissions.get(rol, [])

def check_permission(user_permissions: List[str], required_permission: str) -> bool:
    """Verificar si el usuario tiene el permiso requerido"""
    return required_permission in user_permissions or "admin" in str(user_permissions)