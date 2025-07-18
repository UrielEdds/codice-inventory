# backend/models.py
from pydantic import BaseModel
from datetime import datetime, date
from typing import List, Optional
from enum import Enum

class EstadoInventario(str, Enum):
    NORMAL = "NORMAL"
    STOCK_BAJO = "STOCK_BAJO"
    POR_VENCER = "POR_VENCER"
    VENCIDO = "VENCIDO"

# ========== MODELOS DE SUCURSALES ==========
class SucursalBase(BaseModel):
    codigo: str
    nombre: str
    direccion: Optional[str] = None
    gerente: Optional[str] = None
    tipo: str = "Sucursal"
    telefono: Optional[str] = None

class SucursalRead(SucursalBase):
    id: int
    created_at: Optional[datetime] = None

# ========== MODELOS DE MEDICAMENTOS (CATÁLOGO) ==========
class MedicamentoBase(BaseModel):
    sku: str
    nombre: str
    nombre_generico: Optional[str] = None
    categoria: str
    precio_compra: float
    precio_venta: float
    punto_reorden: int = 10
    fabricante: Optional[str] = None

class MedicamentoCreate(MedicamentoBase):
    pass

class MedicamentoRead(MedicamentoBase):
    id: int
    created_at: Optional[datetime] = None

# ========== MODELOS DE INVENTARIO ==========
class InventarioBase(BaseModel):
    medicamento_id: int
    sucursal_id: int
    stock_actual: int
    stock_minimo: int

class InventarioCreate(InventarioBase):
    pass

class InventarioRead(InventarioBase):
    id: int
    fecha_ultimo_movimiento: Optional[datetime] = None
    created_at: Optional[datetime] = None

class InventarioCompleto(BaseModel):
    """Vista completa del inventario con datos del medicamento y sucursal"""
    inventario_id: int
    medicamento_id: int
    sku: str
    nombre: str
    categoria: str
    precio_compra: float
    precio_venta: float
    fabricante: Optional[str] = None
    sucursal_id: int
    sucursal_nombre: str
    stock_actual: int
    stock_minimo: int
    estado: EstadoInventario
    proxima_caducidad: Optional[date] = None

# ========== MODELOS DE LOTES ==========
class LoteBase(BaseModel):
    medicamento_id: int
    inventario_id: int
    numero_lote: str
    fecha_vencimiento: date
    cantidad_recibida: int
    cantidad_actual: int
    costo_unitario: float

class LoteCreate(LoteBase):
    pass

class LoteRead(LoteBase):
    id: int
    fecha_recepcion: Optional[date] = None

# ========== MODELOS PARA DASHBOARD ==========
class DashboardStats(BaseModel):
    total_medicamentos: int
    total_skus_unicos: int
    stock_bajo: int
    por_vencer: int
    vencidos: int
    valor_total_inventario: float

class AlertaItem(BaseModel):
    tipo: str
    medicamento: str
    sucursal: str
    mensaje: str
    prioridad: str
    datos_extra: dict

class ComparativoSucursal(BaseModel):
    sucursal_id: int
    sucursal_nombre: str
    gerente: str
    total_medicamentos: int
    stock_bajo: int
    por_vencer: int
    valor_inventario: float
    eficiencia: float
    productos_unicos: int