from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    apellido = Column(String, nullable=False)
    rol = Column(String, nullable=False)  # admin, gerente, farmaceutico, empleado
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), nullable=True)
    activo = Column(String, default="activo")
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    ultimo_acceso = Column(DateTime, nullable=True)
    
    # Relación con sucursal (se definirá después de que Sucursal esté definida)
    # sucursal = relationship("Sucursal", back_populates="usuarios")

class Sucursal(Base):
    __tablename__ = "sucursales"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    direccion = Column(String, nullable=True)
    telefono = Column(String, nullable=True)
    correo = Column(String, nullable=True)
    gerente = Column(String, nullable=True)
    responsable_sanitario = Column(String, nullable=True)
    activo = Column(String, default="activo")
    
    # Relación con usuarios
    # usuarios = relationship("Usuario", back_populates="sucursal")

# Ahora definir las relaciones después de que ambas clases estén definidas
# Usuario.sucursal = relationship("Sucursal", back_populates="usuarios")
# Sucursal.usuarios = relationship("Usuario", back_populates="sucursal")