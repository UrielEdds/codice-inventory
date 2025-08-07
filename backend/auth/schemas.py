from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

# Esquemas para Login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: 'UserResponse'

# Esquemas para Usuario
class UserBase(BaseModel):
    email: EmailStr
    nombre: str
    apellido: str
    rol: str
    sucursal_id: Optional[int] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    rol: Optional[str] = None
    sucursal_id: Optional[int] = None
    activo: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    activo: bool
    ultimo_login: Optional[datetime] = None
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    
# Para el frontend
class CurrentUser(BaseModel):
    id: int
    email: str
    nombre: str
    apellido: str
    rol: str
    sucursal_id: Optional[int] = None
    sucursal_nombre: Optional[str] = None
    permissions: list[str] = []