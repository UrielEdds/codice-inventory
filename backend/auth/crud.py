from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import datetime

from backend.auth.models import Usuario
from backend.auth.schemas import UserCreate, UserUpdate
from backend.auth.utils import get_password_hash, verify_password

def get_user_by_email(db: Session, email: str) -> Optional[Usuario]:
    """Obtener usuario por email"""
    return db.query(Usuario).filter(Usuario.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[Usuario]:
    """Obtener usuario por ID"""
    return db.query(Usuario).filter(Usuario.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Obtener lista de usuarios"""
    return db.query(Usuario).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate, created_by_id: Optional[int] = None) -> Usuario:
    """Crear nuevo usuario"""
    hashed_password = get_password_hash(user.password)
    
    db_user = Usuario(
        email=user.email,
        password_hash=hashed_password,
        nombre=user.nombre,
        apellido=user.apellido,
        rol=user.rol,
        sucursal_id=user.sucursal_id,
        created_by=created_by_id
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[Usuario]:
    """Autenticar usuario"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.activo:
        return None
    
    # Actualizar último login
    user.ultimo_login = datetime.utcnow()
    db.commit()
    return user

def update_user(db: Session, user_id: int, user_update: UserUpdate) -> Optional[Usuario]:
    """Actualizar usuario"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_user, field, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> bool:
    """Desactivar usuario (soft delete)"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False
    
    db_user.activo = False
    db.commit()
    return True

def get_users_by_sucursal(db: Session, sucursal_id: int):
    """Obtener usuarios de una sucursal específica"""
    return db.query(Usuario).filter(
        and_(Usuario.sucursal_id == sucursal_id, Usuario.activo == True)
    ).all()

def change_password(db: Session, user_id: int, new_password: str) -> bool:
    """Cambiar contraseña de usuario"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return False
    
    db_user.password_hash = get_password_hash(new_password)
    db.commit()
    return True