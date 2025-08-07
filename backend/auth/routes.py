from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import jwt
from datetime import datetime, timedelta

router = APIRouter()
security = HTTPBearer()

# ========== DATOS MOCK PARA PRUEBAS ==========
MOCK_USERS = {
    "admin@codice.com": {
        "id": 1,
        "email": "admin@codice.com",
        "password": "admin123",
        "nombre": "Carlos",
        "apellido": "Administrador",
        "rol": "admin",
        "sucursal_id": None,
        "sucursal_nombre": None
    },
    "gerente1@codice.com": {
        "id": 2,
        "email": "gerente1@codice.com", 
        "password": "gerente123",
        "nombre": "María",
        "apellido": "García",
        "rol": "gerente",
        "sucursal_id": 1,
        "sucursal_nombre": "Clínica Centro"
    },
    "farmaceutico1@codice.com": {
        "id": 3,
        "email": "farmaceutico1@codice.com",
        "password": "farmaceutico123", 
        "nombre": "Dr. Juan",
        "apellido": "Pérez",
        "rol": "farmaceutico",
        "sucursal_id": 1,
        "sucursal_nombre": "Clínica Centro"
    },
    "empleado1@codice.com": {
        "id": 4,
        "email": "empleado1@codice.com",
        "password": "empleado123",
        "nombre": "Ana",
        "apellido": "López", 
        "rol": "empleado",
        "sucursal_id": 2,
        "sucursal_nombre": "Clínica Norte"
    }
}

SECRET_KEY = "mi-clave-secreta-para-jwt"

def create_access_token(data: dict):
    """Crear JWT token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=8)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(token: str):
    """Verificar JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("email")
        if email is None:
            return None
        return email
    except jwt.PyJWTError:
        return None

# ========== ENDPOINTS DE AUTENTICACIÓN ==========

@router.post("/auth/login")
async def login(credentials: dict):
    """Login usando datos mock"""
    email = credentials.get("email")
    password = credentials.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email y contraseña requeridos")
    
    # Verificar credenciales
    if email in MOCK_USERS:
        user = MOCK_USERS[email]
        if user["password"] == password:
            # Crear token
            access_token = create_access_token({"email": user["email"]})
            
            # Retornar datos del usuario
            user_data = {
                "id": user["id"],
                "email": user["email"],
                "nombre": user["nombre"],
                "apellido": user["apellido"],
                "rol": user["rol"],
                "sucursal_id": user["sucursal_id"],
                "sucursal_nombre": user["sucursal_nombre"]
            }
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user_data
            }
    
    raise HTTPException(status_code=401, detail="Credenciales inválidas")

@router.get("/auth/me")
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtener usuario actual"""
    token = credentials.credentials
    email = verify_token(token)
    
    if email is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    if email in MOCK_USERS:
        user = MOCK_USERS[email]
        return {
            "id": user["id"],
            "email": user["email"],
            "nombre": user["nombre"],
            "apellido": user["apellido"],
            "rol": user["rol"],
            "sucursal_id": user["sucursal_id"],
            "sucursal_nombre": user["sucursal_nombre"]
        }
    
    raise HTTPException(status_code=404, detail="Usuario no encontrado")

@router.get("/auth/users")
async def get_users(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtener lista de usuarios (solo admin)"""
    token = credentials.credentials
    email = verify_token(token)
    
    if email is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    if email in MOCK_USERS and MOCK_USERS[email]["rol"] == "admin":
        users = []
        for user_email, user_data in MOCK_USERS.items():
            users.append({
                "id": user_data["id"],
                "email": user_data["email"],
                "nombre": user_data["nombre"],
                "apellido": user_data["apellido"],
                "rol": user_data["rol"],
                "sucursal_id": user_data["sucursal_id"]
            })
        return users
    
    raise HTTPException(status_code=403, detail="Sin permisos suficientes")

@router.post("/auth/users")
async def create_user(user_data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Crear nuevo usuario (solo admin)"""
    token = credentials.credentials
    email = verify_token(token)
    
    if email is None:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    if email not in MOCK_USERS or MOCK_USERS[email]["rol"] != "admin":
        raise HTTPException(status_code=403, detail="Sin permisos suficientes")
    
    # Simular creación de usuario
    return {"message": "Usuario creado exitosamente (modo demo)"}