"""
Backend FastAPI para Sistema de Inventario Farmacéutico - MODO HÍBRIDO
Sistema con fallback automático: intenta datos reales, usa demo si falla
"""
from fastapi import FastAPI, HTTPException, Security, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import requests
from datetime import datetime, date
from typing import List, Dict, Optional
import json
import os
import time
import logging
from dotenv import load_dotenv

# Importar módulo de recomendaciones inteligentes
from utils.recomendaciones_inteligentes import RecomendacionesInteligentes
from auth.routes import router as auth_router

# Cargar variables de entorno
load_dotenv()

# Configuración de seguridad
security = HTTPBearer(auto_error=False)
SECRET_KEY = os.getenv("SECRET_KEY", "default-secret-change-in-production")
API_SECRET = os.getenv("API_SECRET", "default-api-secret-change-in-production")

# Configurar logging de seguridad
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración para producción
PORT = int(os.environ.get("PORT", 8000))

# ========== CONFIGURACIÓN SUPABASE ==========
SUPABASE_URL = "https://etblilptaljvewsavooj.supabase.co"
SUPABASE_KEY = "REMOVED_JWT"

# ========== CONFIGURACIÓN FASTAPI ==========
app = FastAPI(
    title="Códice Inventory API",
    description="Sistema de inventario farmacéutico inteligente con autenticación",
    version="1.0.0"
)

from routes import ia_routes
app.include_router(auth_router)
app.include_router(ia_routes.router, tags=["IA"])


# ========== MIDDLEWARE DE SEGURIDAD (AGREGAR AQUÍ) ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Función de verificación de token
def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Verificar token de autenticación para endpoints sensibles"""
    if not credentials:
        return None  # Permitir acceso sin token para endpoints públicos
    
    if credentials.credentials != API_SECRET:
        logger.warning(f"Token inválido usado desde IP: {credentials.credentials[:10]}...")
        raise HTTPException(status_code=401, detail="Token de autenticación inválido")
    
    return credentials

# Middleware de logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    client_ip = request.client.host
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    logger.info(
        f"IP: {client_ip} | "
        f"Method: {request.method} | "
        f"URL: {request.url.path} | "
        f"Status: {response.status_code} | "
        f"Time: {process_time:.3f}s"
    )
    
    # Log de intentos sospechosos
    if response.status_code >= 400:
        logger.warning(
            f"Suspicious activity - IP: {client_ip} | "
            f"URL: {request.url.path} | "
            f"Status: {response.status_code}"
        )
    
    return response

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Headers para Supabase
headers = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json'
}

# Instancia global de recomendaciones
recomendaciones = RecomendacionesInteligentes(SUPABASE_URL, SUPABASE_KEY)

# ========== MODELOS PYDANTIC ==========

class MedicamentoCreate(BaseModel):
    sku: str
    nombre: str
    descripcion: Optional[str] = None
    categoria: str
    subcategoria: Optional[str] = None
    precio_compra: float
    precio_venta: float
    requiere_receta: bool = False
    principio_activo: Optional[str] = None

class InventarioCreate(BaseModel):
    medicamento_id: int
    sucursal_id: int
    stock_actual: int
    stock_minimo: int
    stock_maximo: int
    ubicacion: Optional[str] = None

class LoteCreate(BaseModel):
    medicamento_id: int
    sucursal_id: int
    numero_lote: str
    cantidad_recibida: int
    cantidad_actual: int
    fecha_vencimiento: date
    fecha_recepcion: Optional[date] = None
    costo_unitario: Optional[float] = None
    fabricante: Optional[str] = None
    registro_sanitario: Optional[str] = None

class SucursalCreate(BaseModel):
    nombre: str
    direccion: str
    telefono: Optional[str] = None
    email: Optional[str] = None
    encargado: Optional[str] = None

# ========== DATOS DEMO ==========

def get_demo_data(endpoint: str, method: str, query: str = ""):
    """Datos de demo cuando Supabase no está disponible"""
    
    if endpoint == "sucursales" and method == "GET":
        return [
            {"id": 1, "nombre": "Clínica Norte", "direccion": "Av. Revolución 123, Col. Centro", "telefono": "555-1001", "email": "norte@clinicas.com", "encargado": "Dr. José García"},
            {"id": 2, "nombre": "Clínica Centro", "direccion": "Calle Hidalgo 456, Centro Histórico", "telefono": "555-1002", "email": "centro@clinicas.com", "encargado": "Dra. María López"},
            {"id": 3, "nombre": "Clínica Sur", "direccion": "Blvd. Sur 789, Col. San José", "telefono": "555-1003", "email": "sur@clinicas.com", "encargado": "Dr. Carlos Ruiz"}
        ]
    
    elif endpoint == "medicamentos" and method == "GET":
        return [
            {"id": 1, "sku": "ANAL001", "nombre": "Paracetamol 500mg (Caja 20 tab)", "descripcion": "Analgésico y antipirético", "categoria": "Analgésico", "precio_compra": 8.5, "precio_venta": 15.5, "requiere_receta": False},
            {"id": 2, "sku": "ANAL002", "nombre": "Ibuprofeno 400mg (Caja 20 tab)", "descripcion": "Antiinflamatorio no esteroideo", "categoria": "AINE", "precio_compra": 12.8, "precio_venta": 22.5, "requiere_receta": False},
            {"id": 3, "sku": "AB001", "nombre": "Ciprofloxacino 500mg (Caja 10 tab)", "descripcion": "Antibiótico de amplio espectro", "categoria": "Antibiótico", "precio_compra": 28.7, "precio_venta": 48.5, "requiere_receta": True},
            {"id": 4, "sku": "CV001", "nombre": "Enalapril 10mg (Caja 30 tab)", "descripcion": "Inhibidor ECA para hipertensión", "categoria": "Cardiovascular", "precio_compra": 15.2, "precio_venta": 28.0, "requiere_receta": True},
            {"id": 5, "sku": "CV005", "nombre": "Furosemida 40mg (Caja 20 tab)", "descripcion": "Diurético para insuficiencia cardíaca", "categoria": "Cardiovascular", "precio_compra": 9.8, "precio_venta": 18.5, "requiere_receta": True},
            {"id": 6, "sku": "DIA001", "nombre": "Metformina 850mg (Caja 30 tab)", "descripcion": "Antidiabético oral", "categoria": "Antidiabético", "precio_compra": 12.5, "precio_venta": 23.0, "requiere_receta": True},
            {"id": 7, "sku": "DIA002", "nombre": "Glibenclamida 5mg (Caja 30 tab)", "descripcion": "Hipoglucemiante oral", "categoria": "Antidiabético", "precio_compra": 8.9, "precio_venta": 16.5, "requiere_receta": True},
            {"id": 8, "sku": "PED001", "nombre": "Amoxicilina 250mg/5ml (120ml)", "descripcion": "Antibiótico pediátrico", "categoria": "Pediátrico", "precio_compra": 18.5, "precio_venta": 32.0, "requiere_receta": True},
            {"id": 9, "sku": "PED002", "nombre": "Paracetamol Infantil 160mg/5ml", "descripcion": "Analgésico y antipirético infantil", "categoria": "Pediátrico", "precio_compra": 14.2, "precio_venta": 25.0, "requiere_receta": False},
            {"id": 10, "sku": "TOP001", "nombre": "Hidrocortisona Crema 1% (30g)", "descripcion": "Corticoide tópico", "categoria": "Dermatológico", "precio_compra": 22.5, "precio_venta": 38.0, "requiere_receta": False}
        ]
    
    elif endpoint == "vista_inventario_completo" and method == "GET":
        inventario_completo = [
            # Clínica Norte - Stocks altos
            {"id": 1, "medicamento_id": 1, "sucursal_id": 1, "sku": "ANAL001", "nombre": "Paracetamol 500mg (Caja 20 tab)", "categoria": "Analgésico", "sucursal_nombre": "Clínica Norte", "stock_actual": 200, "stock_minimo": 50, "stock_maximo": 300, "precio_compra": 8.5, "precio_venta": 15.5, "ubicacion": "A1-01", "estado": "DISPONIBLE"},
            {"id": 2, "medicamento_id": 2, "sucursal_id": 1, "sku": "ANAL002", "nombre": "Ibuprofeno 400mg (Caja 20 tab)", "categoria": "AINE", "sucursal_nombre": "Clínica Norte", "stock_actual": 180, "stock_minimo": 40, "stock_maximo": 250, "precio_compra": 12.8, "precio_venta": 22.5, "ubicacion": "A1-02", "estado": "DISPONIBLE"},
            {"id": 3, "medicamento_id": 3, "sucursal_id": 1, "sku": "AB001", "nombre": "Ciprofloxacino 500mg (Caja 10 tab)", "categoria": "Antibiótico", "sucursal_nombre": "Clínica Norte", "stock_actual": 150, "stock_minimo": 30, "stock_maximo": 200, "precio_compra": 28.7, "precio_venta": 48.5, "ubicacion": "B2-15", "estado": "DISPONIBLE"},
            {"id": 4, "medicamento_id": 4, "sucursal_id": 1, "sku": "CV001", "nombre": "Enalapril 10mg (Caja 30 tab)", "categoria": "Cardiovascular", "sucursal_nombre": "Clínica Norte", "stock_actual": 95, "stock_minimo": 25, "stock_maximo": 150, "precio_compra": 15.2, "precio_venta": 28.0, "ubicacion": "C1-08", "estado": "DISPONIBLE"},
            {"id": 5, "medicamento_id": 5, "sucursal_id": 1, "sku": "CV005", "nombre": "Furosemida 40mg (Caja 20 tab)", "categoria": "Cardiovascular", "sucursal_nombre": "Clínica Norte", "stock_actual": 120, "stock_minimo": 35, "stock_maximo": 180, "precio_compra": 9.8, "precio_venta": 18.5, "ubicacion": "C1-12", "estado": "DISPONIBLE"},
            
            # Clínica Centro - Stocks medios
            {"id": 6, "medicamento_id": 1, "sucursal_id": 2, "sku": "ANAL001", "nombre": "Paracetamol 500mg (Caja 20 tab)", "categoria": "Analgésico", "sucursal_nombre": "Clínica Centro", "stock_actual": 85, "stock_minimo": 50, "stock_maximo": 300, "precio_compra": 8.5, "precio_venta": 15.5, "ubicacion": "A2-01", "estado": "DISPONIBLE"},
            {"id": 7, "medicamento_id": 2, "sucursal_id": 2, "sku": "ANAL002", "nombre": "Ibuprofeno 400mg (Caja 20 tab)", "categoria": "AINE", "sucursal_nombre": "Clínica Centro", "stock_actual": 70, "stock_minimo": 40, "stock_maximo": 250, "precio_compra": 12.8, "precio_venta": 22.5, "ubicacion": "A2-02", "estado": "DISPONIBLE"},
            {"id": 8, "medicamento_id": 3, "sucursal_id": 2, "sku": "AB001", "nombre": "Ciprofloxacino 500mg (Caja 10 tab)", "categoria": "Antibiótico", "sucursal_nombre": "Clínica Centro", "stock_actual": 45, "stock_minimo": 30, "stock_maximo": 200, "precio_compra": 28.7, "precio_venta": 48.5, "ubicacion": "B2-15", "estado": "DISPONIBLE"},
            {"id": 9, "medicamento_id": 6, "sucursal_id": 2, "sku": "DIA001", "nombre": "Metformina 850mg (Caja 30 tab)", "categoria": "Antidiabético", "sucursal_nombre": "Clínica Centro", "stock_actual": 110, "stock_minimo": 40, "stock_maximo": 200, "precio_compra": 12.5, "precio_venta": 23.0, "ubicacion": "D1-05", "estado": "DISPONIBLE"},
            {"id": 10, "medicamento_id": 7, "sucursal_id": 2, "sku": "DIA002", "nombre": "Glibenclamida 5mg (Caja 30 tab)", "categoria": "Antidiabético", "sucursal_nombre": "Clínica Centro", "stock_actual": 75, "stock_minimo": 30, "stock_maximo": 150, "precio_compra": 8.9, "precio_venta": 16.5, "ubicacion": "D1-08", "estado": "DISPONIBLE"},
            
            # Clínica Sur - Stocks bajos (necesita compra/redistribución)
            {"id": 11, "medicamento_id": 1, "sucursal_id": 3, "sku": "ANAL001", "nombre": "Paracetamol 500mg (Caja 20 tab)", "categoria": "Analgésico", "sucursal_nombre": "Clínica Sur", "stock_actual": 5, "stock_minimo": 50, "stock_maximo": 300, "precio_compra": 8.5, "precio_venta": 15.5, "ubicacion": "A3-01", "estado": "STOCK_BAJO"},
            {"id": 12, "medicamento_id": 2, "sucursal_id": 3, "sku": "ANAL002", "nombre": "Ibuprofeno 400mg (Caja 20 tab)", "categoria": "AINE", "sucursal_nombre": "Clínica Sur", "stock_actual": 8, "stock_minimo": 40, "stock_maximo": 250, "precio_compra": 12.8, "precio_venta": 22.5, "ubicacion": "A3-02", "estado": "STOCK_BAJO"},
            {"id": 13, "medicamento_id": 3, "sucursal_id": 3, "sku": "AB001", "nombre": "Ciprofloxacino 500mg (Caja 10 tab)", "categoria": "Antibiótico", "sucursal_nombre": "Clínica Sur", "stock_actual": 3, "stock_minimo": 30, "stock_maximo": 200, "precio_compra": 28.7, "precio_venta": 48.5, "ubicacion": "B3-15", "estado": "STOCK_BAJO"},
            {"id": 14, "medicamento_id": 4, "sucursal_id": 3, "sku": "CV001", "nombre": "Enalapril 10mg (Caja 30 tab)", "categoria": "Cardiovascular", "sucursal_nombre": "Clínica Sur", "stock_actual": 12, "stock_minimo": 25, "stock_maximo": 150, "precio_compra": 15.2, "precio_venta": 28.0, "ubicacion": "C3-08", "estado": "STOCK_BAJO"},
            {"id": 15, "medicamento_id": 5, "sucursal_id": 3, "sku": "CV005", "nombre": "Furosemida 40mg (Caja 20 tab)", "categoria": "Cardiovascular", "sucursal_nombre": "Clínica Sur", "stock_actual": 6, "stock_minimo": 35, "stock_maximo": 180, "precio_compra": 9.8, "precio_venta": 18.5, "ubicacion": "C3-12", "estado": "STOCK_BAJO"}
        ]
        
        # Filtrar por sucursal si se especifica en query
        if "sucursal_id=eq." in query:
            sucursal_id = int(query.split("sucursal_id=eq.")[1].split("&")[0])
            inventario_completo = [item for item in inventario_completo if item['sucursal_id'] == sucursal_id]
        
        # Filtrar stock bajo si se especifica
        if "stock_actual=lt.stock_minimo" in query:
            inventario_completo = [item for item in inventario_completo if item['stock_actual'] < item['stock_minimo']]
        
        return inventario_completo
    
    elif endpoint == "lotes_inventario" and method == "GET":
        return [
            {"id": 1, "medicamento_id": 1, "sucursal_id": 1, "numero_lote": "LOT001", "cantidad_inicial": 100, "cantidad_actual": 80, "fecha_vencimiento": "2025-07-25", "fecha_ingreso": "2024-12-01", "proveedor": "Farma Norte SA"},
            {"id": 2, "medicamento_id": 1, "sucursal_id": 1, "numero_lote": "LOT002", "cantidad_inicial": 120, "cantidad_actual": 120, "fecha_vencimiento": "2025-12-15", "fecha_ingreso": "2024-12-15", "proveedor": "Farma Norte SA"},
            {"id": 3, "medicamento_id": 2, "sucursal_id": 1, "numero_lote": "LOT003", "cantidad_inicial": 90, "cantidad_actual": 80, "fecha_vencimiento": "2025-07-28", "fecha_ingreso": "2024-11-20", "proveedor": "Laboratorios Unión"},
            {"id": 4, "medicamento_id": 3, "sucursal_id": 2, "numero_lote": "LOT004", "cantidad_inicial": 60, "cantidad_actual": 45, "fecha_vencimiento": "2025-07-30", "fecha_ingreso": "2024-12-10", "proveedor": "Antibióticos SA"}
        ]
    
    elif endpoint == "lotes_inventario" and method == "GET":
        return [
            {"id": 1, "medicamento_id": 1, "sucursal_id": 1, "numero_lote": "LOT001", "cantidad_inicial": 100, "cantidad_actual": 80, "fecha_vencimiento": "2025-07-25", "fecha_ingreso": "2024-12-01", "proveedor": "Farma Norte SA"},
            {"id": 2, "medicamento_id": 1, "sucursal_id": 1, "numero_lote": "LOT002", "cantidad_inicial": 120, "cantidad_actual": 120, "fecha_vencimiento": "2025-12-15", "fecha_ingreso": "2024-12-15", "proveedor": "Farma Norte SA"},
            {"id": 3, "medicamento_id": 2, "sucursal_id": 1, "numero_lote": "LOT003", "cantidad_inicial": 90, "cantidad_actual": 80, "fecha_vencimiento": "2025-07-28", "fecha_ingreso": "2024-11-20", "proveedor": "Laboratorios Unión"},
            {"id": 4, "medicamento_id": 3, "sucursal_id": 2, "numero_lote": "LOT004", "cantidad_inicial": 60, "cantidad_actual": 45, "fecha_vencimiento": "2025-07-30", "fecha_ingreso": "2024-12-10", "proveedor": "Antibióticos SA"}
        ]
    
    elif endpoint == "proveedores" and method == "GET":
        return [
            {"id": 1, "codigo": "LAB001", "nombre": "Laboratorios Pisa", "telefono": "555-1001", "activo": True},
            {"id": 2, "codigo": "LAB002", "nombre": "Laboratorios Liomont", "telefono": "555-1002", "activo": True},
            {"id": 3, "codigo": "LAB003", "nombre": "Laboratorios Silanes", "telefono": "555-1003", "activo": True},
            {"id": 4, "codigo": "LAB004", "nombre": "Laboratorios Sophia", "telefono": "555-1004", "activo": True},
            {"id": 5, "codigo": "LAB005", "nombre": "Laboratorios Best", "telefono": "555-1005", "activo": True},
            {"id": 6, "codigo": "LAB006", "nombre": "Laboratorios Carnot", "telefono": "555-1006", "activo": True},
            {"id": 7, "codigo": "LAB007", "nombre": "Laboratorios Collins", "telefono": "555-1007", "activo": True},
            {"id": 8, "codigo": "LAB008", "nombre": "Laboratorios Grossman", "telefono": "555-1008", "activo": True}
        ]
    
    else:
        return []

# ========== FUNCIONES AUXILIARES ==========

def get_supabase_url(endpoint: str, query: str = ""):
    """Construye URL para consultas a Supabase"""
    base_url = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    return f"{base_url}?{query}" if query else base_url

def make_supabase_request(method: str, endpoint: str, data: dict = None, query: str = ""):
    """Petición híbrida con logs MUY detallados y manejo mejorado de errores"""
    
    try:
        url = get_supabase_url(endpoint, query)
        print(f"🔍 TRYING: {method} {endpoint} | Query: '{query}' | Full URL: {url}")
        
        # Log de datos enviados para POST/PATCH
        if data and method in ["POST", "PATCH"]:
            print(f"📤 DATA SENT: {data}")
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        else:
            raise ValueError(f"Método HTTP no soportado: {method}")
        
        print(f"📊 RESPONSE: {response.status_code} for {endpoint}")
        
        # Manejar respuestas exitosas
        if response.status_code in [200, 201]:
            print(f"✅ DATOS REALES obtenidos para: {endpoint}")
            try:
                return response.json()
            except ValueError:
                print(f"⚠️ Respuesta vacía o no JSON para {endpoint}")
                return {"success": True}
        
        # Manejar errores HTTP con más detalle
        elif response.status_code >= 400:
            print(f"❌ ERROR HTTP {response.status_code} para {endpoint}")
            print(f"📄 Query problemática: {query}")
            print(f"🔗 URL completa: {url}")
            
            # Intentar parsear el error de Supabase
            try:
                error_detail = response.json()
                print(f"💬 Error JSON: {error_detail}")
                
                # Extraer mensaje de error específico de Supabase
                if isinstance(error_detail, dict):
                    if 'message' in error_detail:
                        error_message = error_detail['message']
                    elif 'error' in error_detail:
                        error_message = error_detail['error']
                    elif 'details' in error_detail:
                        error_message = error_detail['details']
                    else:
                        error_message = str(error_detail)
                else:
                    error_message = str(error_detail)
                    
            except ValueError:
                # Si no es JSON válido, usar el texto plano
                error_message = response.text[:300]
                print(f"💬 Error text: {error_message}")
            
            # Para errores 422, devolver información específica
            if response.status_code == 422:
                print(f"🔍 ERROR 422 DETALLADO:")
                print(f"   - Endpoint: {endpoint}")
                print(f"   - Método: {method}")
                print(f"   - Datos enviados: {data}")
                print(f"   - Respuesta Supabase: {error_message}")
                
                # Retornar None para que el endpoint pueda manejar el error
                return {
                    "error": True,
                    "status_code": 422,
                    "message": error_message,
                    "endpoint": endpoint,
                    "method": method,
                    "data_sent": data
                }
            
            # Para otros errores, también retornar información detallada
            return {
                "error": True,
                "status_code": response.status_code,
                "message": error_message,
                "endpoint": endpoint,
                "method": method
            }
            
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
        print(f"🔄 Conectividad fallida para {endpoint}: {str(e)}")
        print(f"📊 Usando datos demo como fallback")
        return get_demo_data(endpoint, method, query)
    
    except Exception as e:
        print(f"🔄 Error inesperado para {endpoint}: {str(e)}")
        print(f"📊 Usando datos demo como fallback")
        return get_demo_data(endpoint, method, query)

# Función auxiliar para validar datos antes de enviar a Supabase
def validar_datos_supabase(data: dict, tabla: str) -> dict:
    """Validar y limpiar datos antes de enviar a Supabase"""
    
    if tabla == "salidas_inventario":
        # Validaciones específicas para salidas_inventario
        required_fields = ["sucursal_id", "medicamento_id", "lote_id", "cantidad", "tipo_salida"]
        
        # Verificar campos requeridos
        for field in required_fields:
            if field not in data or data[field] is None:
                return {"error": f"Campo requerido faltante: {field}"}
        
        # Limpiar y validar tipos de datos
        cleaned_data = {}
        
        try:
            cleaned_data["sucursal_id"] = int(data["sucursal_id"])
            cleaned_data["medicamento_id"] = int(data["medicamento_id"])
            cleaned_data["lote_id"] = int(data["lote_id"])
            cleaned_data["cantidad"] = int(data["cantidad"])
            
            if cleaned_data["cantidad"] <= 0:
                return {"error": "La cantidad debe ser mayor a 0"}
                
        except (ValueError, TypeError) as e:
            return {"error": f"Error de tipo de dato: {str(e)}"}
        
        # Validar tipo_salida
        tipos_validos = [
            "Venta", "Transferencia", "Consumo Interno", 
            "Devolución", "Vencimiento", "Ajuste de Inventario",
            "Muestra Médica", "Investigación", "Dispensación"
        ]
        
        if data["tipo_salida"] not in tipos_validos:
            return {"error": f"Tipo de salida inválido. Debe ser uno de: {', '.join(tipos_validos)}"}
        
        cleaned_data["tipo_salida"] = str(data["tipo_salida"])
        
        # Campos opcionales con valores por defecto
        cleaned_data["destino"] = str(data.get("destino", ""))
        cleaned_data["observaciones"] = str(data.get("observaciones", ""))
        cleaned_data["usuario"] = str(data.get("usuario", "Sistema"))
        cleaned_data["numero_receta"] = str(data.get("numero_receta", ""))
        cleaned_data["medico_prescriptor"] = str(data.get("medico_prescriptor", ""))
        
        # Validar campos numéricos opcionales
        try:
            cleaned_data["precio_unitario"] = float(data.get("precio_unitario", 0.0))
            cleaned_data["total"] = float(data.get("total", 0.0))
        except (ValueError, TypeError):
            cleaned_data["precio_unitario"] = 0.0
            cleaned_data["total"] = 0.0
        
        # Agregar timestamp si no existe
        if "fecha_salida" not in data:
            from datetime import datetime
            cleaned_data["fecha_salida"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        else:
            cleaned_data["fecha_salida"] = data["fecha_salida"]
        
        return cleaned_data
    
    # Para otras tablas, retornar datos sin cambios por ahora
    return data

# ========== ENDPOINTS DE SALUD ==========

@app.get("/")
async def root():
    """Endpoint raíz - Verificación de salud"""
    return {
        "message": "Sistema de Inventario Farmacéutico API - MODO HÍBRIDO",
        "version": "1.0.0",
        "status": "online",
        "mode": "hybrid",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    """Verificación de salud del sistema"""
    return {
        "status": "healthy",
        "mode": "hybrid",
        "supabase": "auto_fallback",
        "timestamp": datetime.now().isoformat()
    }

# ========== ENDPOINTS DE SUCURSALES ==========

@app.get("/sucursales")
async def get_sucursales():
    """Obtener todas las sucursales"""
    return make_supabase_request("GET", "sucursales", query="order=id")

@app.post("/sucursales")
async def create_sucursal(sucursal: SucursalCreate):
    """Crear nueva sucursal"""
    return make_supabase_request("POST", "sucursales", sucursal.dict())

@app.get("/sucursales/{sucursal_id}")
async def get_sucursal(sucursal_id: int):
    """Obtener sucursal específica"""
    result = make_supabase_request("GET", "sucursales", query=f"id=eq.{sucursal_id}")
    if not result:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return result[0]

# ========== ENDPOINTS DE MEDICAMENTOS ==========

@app.get("/medicamentos")
async def get_medicamentos():
    """Obtener todos los medicamentos"""
    return make_supabase_request("GET", "medicamentos", query="order=id")

@app.post("/medicamentos")
async def create_medicamento(medicamento: MedicamentoCreate):
    """Crear nuevo medicamento"""
    return make_supabase_request("POST", "medicamentos", medicamento.dict())

@app.get("/medicamentos/{medicamento_id}")
async def get_medicamento(medicamento_id: int):
    """Obtener medicamento específico"""
    result = make_supabase_request("GET", "medicamentos", query=f"id=eq.{medicamento_id}")
    if not result:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")
    return result[0]

# ========== ENDPOINTS DE PROVEEDORES ==========

@app.get("/proveedores")
async def get_proveedores():
    """Obtener todos los proveedores activos"""
    return make_supabase_request("GET", "proveedores", query="activo=eq.true&order=nombre")

@app.post("/proveedores")
async def create_proveedor(proveedor_data: dict):
    """Crear nuevo proveedor"""
    return make_supabase_request("POST", "proveedores", proveedor_data)

@app.get("/proveedores/{proveedor_id}")
async def get_proveedor(proveedor_id: int):
    """Obtener proveedor específico"""
    result = make_supabase_request("GET", "proveedores", query=f"id=eq.{proveedor_id}")
    return result[0] if result else None

# ========== ENDPOINTS DE INVENTARIO ==========

@app.get("/inventario")
async def get_inventario():
    """Obtener inventario con queries separadas"""
    try:
        # En lugar de usar la vista, hacer queries separadas
        inventario = make_supabase_request("GET", "inventario")
        medicamentos = make_supabase_request("GET", "medicamentos")
        sucursales = make_supabase_request("GET", "sucursales")
        
        # JOIN manual en Python
        resultado = []
        for inv in inventario:
            med = next((m for m in medicamentos if m['id'] == inv['medicamento_id']), {})
            suc = next((s for s in sucursales if s['id'] == inv['sucursal_id']), {})
            
            resultado.append({
                'id': inv['id'],
                'medicamento_id': inv['medicamento_id'],
                'sucursal_id': inv['sucursal_id'],
                'sku': med.get('sku', ''),
                'nombre': med.get('nombre', ''),
                'categoria': med.get('categoria', ''),
                'fabricante': med.get('fabricante', ''),
                'sucursal_nombre': suc.get('nombre', ''),
                'stock_actual': inv.get('stock_actual', 0),
                'stock_minimo': inv.get('stock_minimo', 0),
                'precio_compra': med.get('precio_compra', 0),
                'precio_venta': med.get('precio_venta', 0),
                'estado': 'STOCK_BAJO' if inv.get('stock_actual', 0) <= inv.get('stock_minimo', 0) else 'DISPONIBLE'
            })
        
        return resultado
        
    except Exception as e:
        print(f"Error inventario: {e}")
        return get_demo_data("vista_inventario_completo", "GET")

@app.get("/inventario/sucursal/{sucursal_id}")
async def get_inventario_sucursal(sucursal_id: int):
    """Obtener inventario de una sucursal específica"""
    return make_supabase_request("GET", "vista_inventario_completo", query=f"sucursal_id=eq.{sucursal_id}&order=medicamento_id")

@app.post("/inventario")
async def create_inventario(inventario: InventarioCreate):
    """Crear registro de inventario"""
    return make_supabase_request("POST", "inventario", inventario.dict())

@app.get("/inventario/alertas")
async def get_alertas_inventario():
    """Obtener alertas de stock bajo - CORREGIDO"""
    try:
        # Obtener todo el inventario y filtrar en Python
        inventario_completo = make_supabase_request("GET", "vista_inventario_completo", 
                                                   query="order=sucursal_nombre,nombre")
        
        # Filtrar en Python en lugar de SQL
        alertas = []
        for item in inventario_completo:
            if item.get('stock_actual', 0) <= item.get('stock_minimo', 0):
                alertas.append(item)
        
        return alertas
        
    except Exception as e:
        print(f"Error en alertas, usando demo: {e}")
        return get_demo_data("vista_inventario_completo", "GET")

@app.patch("/inventario/{inventario_id}")
async def update_inventario(inventario_id: int, data: dict):
    """Actualizar registro de inventario"""
    return make_supabase_request("PATCH", "inventario", data, query=f"id=eq.{inventario_id}")

@app.get("/inventario/sucursal/{sucursal_id}")
async def get_inventario_por_sucursal(sucursal_id: int):
    """Obtener inventario específico de una sucursal"""
    try:
        inventario = make_supabase_request("GET", "vista_inventario_completo", 
                                         query=f"sucursal_id=eq.{sucursal_id}")
        return inventario
    except Exception as e:
        print(f"Error obteniendo inventario de sucursal {sucursal_id}: {e}")
        # Fallback con datos demo filtrados
        demo_data = get_demo_data("vista_inventario_completo", "GET")
        return [item for item in demo_data if item.get('sucursal_id') == sucursal_id]


# ========== ENDPOINTS DE LOTES ==========

@app.get("/lotes")
async def get_lotes():
    """Obtener todos los lotes"""
    return make_supabase_request("GET", "lotes_inventario", query="order=fecha_vencimiento")

@app.post("/lotes")
async def create_lote(request: Request):
    """Crear nuevo lote con debug completo"""
    try:
        # Obtener datos raw del request
        body = await request.body()
        json_data = json.loads(body)
        
        print(f"🔍 DATOS RECIBIDOS EN /lotes: {json_data}")
        
        # Validar campos uno por uno
        required_fields = ['medicamento_id', 'sucursal_id', 'numero_lote', 'cantidad_recibida', 'cantidad_actual', 'fecha_vencimiento']
        missing_fields = [field for field in required_fields if field not in json_data]
        
        if missing_fields:
            print(f"❌ CAMPOS FALTANTES: {missing_fields}")
            raise HTTPException(status_code=422, detail=f"Campos faltantes: {missing_fields}")
        
        # Verificar tipos de datos
        try:
            medicamento_id = int(json_data['medicamento_id'])
            sucursal_id = int(json_data['sucursal_id'])
            cantidad_recibida = int(json_data['cantidad_recibida'])
            cantidad_actual = int(json_data['cantidad_actual'])
        except (ValueError, TypeError) as e:
            print(f"❌ ERROR DE TIPOS: {str(e)}")
            raise HTTPException(status_code=422, detail=f"Error en tipos de datos: {str(e)}")
        
        # Convertir fecha si es string
        if isinstance(json_data['fecha_vencimiento'], str):
            try:
                fecha_vencimiento = datetime.strptime(json_data['fecha_vencimiento'], '%Y-%m-%d').date()
            except ValueError:
                print(f"❌ ERROR EN FECHA: {json_data['fecha_vencimiento']}")
                raise HTTPException(status_code=422, detail="Formato de fecha incorrecto")
        else:
            fecha_vencimiento = json_data['fecha_vencimiento']
        
        # Preparar datos para Supabase (solo campos que existen en la tabla)
        lote_data = {
            "medicamento_id": medicamento_id,
            "sucursal_id": sucursal_id,
            "numero_lote": json_data['numero_lote'],
            "cantidad_recibida": cantidad_recibida,
            "cantidad_actual": cantidad_actual,
            "fecha_vencimiento": fecha_vencimiento.isoformat() if hasattr(fecha_vencimiento, 'isoformat') else str(fecha_vencimiento),
            "fecha_recepcion": json_data.get('fecha_recepcion', datetime.now().date().isoformat()),
            "costo_unitario": float(json_data.get('costo_unitario', 0.0)),
            "fabricante": json_data.get('fabricante', ''),
            "registro_sanitario": json_data.get('registro_sanitario', '')
        }
        
        print(f"📤 ENVIANDO A SUPABASE: {lote_data}")
        
        # Enviar a Supabase
        resultado = make_supabase_request("POST", "lotes_inventario", lote_data)
        
        if resultado:
            print(f"✅ LOTE CREADO EXITOSAMENTE: {resultado}")
            return resultado
        else:
            print(f"❌ ERROR EN SUPABASE")
            raise HTTPException(status_code=500, detail="Error creando lote en base de datos")
            
    except json.JSONDecodeError as e:
        print(f"❌ ERROR JSON: {str(e)}")
        raise HTTPException(status_code=422, detail=f"JSON inválido: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ ERROR GENERAL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
# ========== ENDPOINTS DE INTELIGENCIA ARTIFICIAL ==========

@app.get("/inteligente/recomendaciones/compras/sucursal/{sucursal_id}")
async def get_recomendaciones_compra_sucursal(sucursal_id: int):
    """Recomendaciones inteligentes de compra para una sucursal"""
    try:
        recomendaciones_data = recomendaciones.generar_recomendaciones_compra(sucursal_id)
        return recomendaciones_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando recomendaciones de compra: {str(e)}")

@app.get("/inteligente/recomendaciones/redistribucion")
async def get_recomendaciones_redistribucion():
    """Recomendaciones de redistribución entre sucursales"""
    try:
        redistrib_data = recomendaciones.generar_recomendaciones_redistribucion()
        return redistrib_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando recomendaciones de redistribución: {str(e)}")

@app.get("/inteligente/dashboard/consolidado")
async def get_dashboard_consolidado():
    """Dashboard consolidado con métricas inteligentes"""
    try:
        dashboard_data = recomendaciones.generar_dashboard_consolidado()
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando dashboard consolidado: {str(e)}")

@app.get("/inteligente/alertas/vencimiento")
async def get_alertas_vencimiento_inteligentes(sucursal_id: Optional[int] = None):
    """Alertas inteligentes de productos próximos a vencer"""
    try:
        alertas_data = recomendaciones.generar_alertas_vencimiento(sucursal_id)
        return alertas_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando alertas de vencimiento: {str(e)}")

# ========== ENDPOINTS DE ANÁLISIS ==========

@app.get("/analisis/inventario/resumen")
async def get_resumen_inventario():
    """Resumen general del inventario"""
    try:
        inventario = make_supabase_request("GET", "vista_inventario_completo")
        
        # Calcular métricas
        total_medicamentos = len(set(item['medicamento_id'] for item in inventario))
        total_stock = sum(item['stock_actual'] for item in inventario)
        valor_total = sum(item['stock_actual'] * item['precio_venta'] for item in inventario)
        alertas_stock = len([item for item in inventario if item['stock_actual'] <= item['stock_minimo']])
        
        return {
            'resumen_general': {
                'total_medicamentos': total_medicamentos,
                'total_stock': total_stock,
                'valor_total_inventario': round(valor_total, 2),
                'alertas_stock_bajo': alertas_stock
            },
            'fecha_calculo': datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculando resumen: {str(e)}")

@app.get("/categorias")
async def get_categorias():
    """Obtener lista de categorías únicas"""
    return ["Analgésico", "AINE", "Antibiótico", "Cardiovascular", "Antidiabético", "Pediátrico", "Dermatológico"]

@app.get("/estadisticas/generales")
async def get_estadisticas_generales():
    """Estadísticas generales del sistema"""
    return {
        'total_sucursales': 3,
        'total_medicamentos': 10,
        'total_registros_inventario': 15,
        'total_lotes': 4,
        'timestamp': datetime.now().isoformat()
    }


# ========== END POINT TEMPORAL ==========

@app.get("/debug-vista")
async def debug_vista():
    """Debug específico para vista_inventario_completo"""
    
    # Test 1: URL que se está construyendo
    url = get_supabase_url("vista_inventario_completo", "order=sucursal_id,medicamento_id")
    
    # Test 2: Request directo con detalles
    try:
        response = requests.get(url, headers=headers, timeout=10)
        return {
            "url_construida": url,
            "status_code": response.status_code,
            "headers_enviados": dict(headers),
            "response_text": response.text[:500] if response.text else "Sin contenido",
            "response_headers": dict(response.headers)
        }
    except Exception as e:
        return {
            "url_construida": url,
            "error": str(e),
            "error_type": type(e).__name__
        }

@app.get("/test-endpoints")
async def test_endpoints():
    """Probar todos los endpoints problemáticos"""
    results = {}
    
    endpoints_to_test = [
        ("inventario", ""),
        ("vista_inventario_completo", ""),
        ("vista_inventario_completo", "order=sucursal_id,medicamento_id"),
        ("medicamentos", ""),
        ("sucursales", ""),
        ("lotes_inventario", "")
    ]
    
    for endpoint, query in endpoints_to_test:
        try:
            url = get_supabase_url(endpoint, query)
            response = requests.get(url, headers=headers, timeout=5)
            results[f"{endpoint}{'?' + query if query else ''}"] = {
                "status": response.status_code,
                "response_length": len(response.text),
                "first_100_chars": response.text[:100]
            }
        except Exception as e:
            results[f"{endpoint}{'?' + query if query else ''}"] = {
                "error": str(e)
            }
    
    return results

@app.get("/debug-ingreso")
async def debug_modulo_ingreso():
    """Debug específico para módulo de ingreso"""
    results = {}
    
    # Test todos los endpoints que usa el módulo de ingreso
    test_endpoints = [
        ("medicamentos", ""),
        ("sucursales", ""),
        ("proveedores", ""),
        ("lotes_inventario", ""),
        ("vista_inventario_completo", ""),
        ("vista_inventario_completo", "order=sucursal_id,medicamento_id"),
        ("vista_inventario_completo", "stock_actual=lt.stock_minimo"),
        ("vista_inventario_completo", "sucursal_id=eq.1"),
        ("analisis/inventario/resumen", "")
    ]
    
    for endpoint, query in test_endpoints:
        try:
            if endpoint.startswith("analisis"):
                url = f"http://localhost:8000/{endpoint}"
                response = requests.get(url)
            else:
                url = get_supabase_url(endpoint, query)
                response = requests.get(url, headers=headers, timeout=5)
            
            results[f"{endpoint}{'?' + query if query else ''}"] = {
                "status": response.status_code,
                "url": url,
                "error": response.text[:200] if response.status_code >= 400 else None
            }
        except Exception as e:
            results[f"{endpoint}{'?' + query if query else ''}"] = {"error": str(e)}
    
    return results

# ========== MANEJO DE ERRORES ==========

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Error interno del servidor", "detail": str(exc)}
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Recurso no encontrado", "detail": "El recurso solicitado no existe"}
    )

@app.get("/inventario/sucursal/{sucursal_id}")
async def get_inventario_por_sucursal(sucursal_id: int):
    """Obtener inventario específico de una sucursal"""
    try:
        inventario = make_supabase_request("GET", "vista_inventario_completo", 
                                         query=f"sucursal_id=eq.{sucursal_id}")
        return inventario
    except Exception as e:
        print(f"Error obteniendo inventario de sucursal {sucursal_id}: {e}")
        # Fallback con datos demo filtrados por sucursal
        demo_data = get_demo_data("vista_inventario_completo", "GET")
        return [item for item in demo_data if item.get('sucursal_id') == sucursal_id]

# ========== ENDPOINTS OPTIMIZADOS PARA SALIDAS ==========

@app.post("/salidas")
async def crear_salida(salida_data: dict):
    """Crear nueva salida de inventario y actualizar stock automáticamente"""
    try:
        # 1. Insertar la salida en la tabla
        salida_response = make_supabase_request("POST", "salidas_inventario", data=salida_data)
        
        if salida_response:
            # 2. Actualizar cantidad del lote
            lote_id = salida_data.get('lote_id')
            cantidad_salida = salida_data.get('cantidad')
            
            # Obtener lote actual
            lote_actual = make_supabase_request("GET", "lotes_inventario", query=f"id=eq.{lote_id}")
            
            if lote_actual and len(lote_actual) > 0:
                nueva_cantidad = lote_actual[0]['cantidad_actual'] - cantidad_salida
                
                # Actualizar lote
                update_lote = make_supabase_request(
                    "PATCH", 
                    f"lotes_inventario?id=eq.{lote_id}", 
                    data={"cantidad_actual": nueva_cantidad}
                )
                
                # 3. Actualizar stock total en inventario
                inventario_id = lote_actual[0].get('inventario_id')
                if inventario_id:
                    # Recalcular stock total sumando todos los lotes
                    lotes_medicamento = make_supabase_request(
                        "GET", 
                        "lotes_inventario", 
                        query=f"inventario_id=eq.{inventario_id}"
                    )
                    
                    if lotes_medicamento:
                        stock_total = sum(lote.get('cantidad_actual', 0) for lote in lotes_medicamento)
                        
                        # Actualizar inventario
                        make_supabase_request(
                            "PATCH", 
                            f"inventario?id=eq.{inventario_id}", 
                            data={"stock_actual": stock_total}
                        )
                
                print(f"✅ Salida registrada: {cantidad_salida} unidades del lote {lote_actual[0].get('numero_lote')}")
        
        return salida_response
        
    except Exception as e:
        print(f"❌ Error creando salida: {e}")
        raise HTTPException(status_code=500, detail=f"Error creando salida: {str(e)}")

@app.get("/salidas")
async def get_salidas(sucursal_id: int = None, limit: int = 100):
    """Obtener salidas con filtros optimizados"""
    try:
        query_parts = []
        
        if sucursal_id:
            query_parts.append(f"sucursal_id=eq.{sucursal_id}")
        
        query_parts.append(f"limit={limit}")
        query_parts.append("order=fecha_salida.desc")
        
        query = "&".join(query_parts)
        
        salidas = make_supabase_request("GET", "vista_salidas_completo", query=query)
        print(f"✅ Salidas obtenidas: {len(salidas) if salidas else 0} registros")
        return salidas
        
    except Exception as e:
        print(f"❌ Error obteniendo salidas: {e}")
        return []

@app.get("/inventario/sucursal/{sucursal_id}")
async def get_inventario_por_sucursal(sucursal_id: int):
    """Obtener inventario específico de una sucursal - OPTIMIZADO"""
    try:
        # Query optimizada: solo medicamentos con stock > 0, ordenados por nombre
        inventario = make_supabase_request(
            "GET", 
            "vista_inventario_completo", 
            query=f"sucursal_id=eq.{sucursal_id}&stock_actual=gte.1&order=nombre.asc"
        )
        
        print(f"✅ Inventario sucursal {sucursal_id}: {len(inventario) if inventario else 0} medicamentos con stock")
        return inventario
        
    except Exception as e:
        print(f"❌ Error obteniendo inventario de sucursal {sucursal_id}: {e}")
        # Fallback con datos demo filtrados
        demo_data = get_demo_data("vista_inventario_completo", "GET")
        inventario_filtrado = [
            item for item in demo_data 
            if item.get('sucursal_id') == sucursal_id and item.get('stock_actual', 0) > 0
        ]
        print(f"📊 Usando datos demo: {len(inventario_filtrado)} medicamentos")
        return inventario_filtrado

@app.get("/lotes/medicamento/{medicamento_id}/sucursal/{sucursal_id}")
async def get_lotes_por_medicamento_sucursal(medicamento_id: int, sucursal_id: int):
    """Obtener lotes específicos por medicamento y sucursal - OPTIMIZADO"""
    try:
        # Query optimizada: solo lotes con stock > 0, ordenados por vencimiento
        lotes = make_supabase_request(
            "GET", 
            "lotes_inventario", 
            query=f"medicamento_id=eq.{medicamento_id}&sucursal_id=eq.{sucursal_id}&cantidad_actual=gte.1&order=fecha_vencimiento.asc"
        )
        
        print(f"✅ Lotes encontrados: {len(lotes) if lotes else 0} para medicamento {medicamento_id} en sucursal {sucursal_id}")
        return lotes
        
    except Exception as e:
        print(f"❌ Error obteniendo lotes: {e}")
        return []

@app.get("/dashboard/metricas/sucursal/{sucursal_id}")
async def get_metricas_sucursal(sucursal_id: int):
    """Métricas optimizadas por sucursal"""
    try:
        # Query única para obtener todas las métricas
        inventario = make_supabase_request(
            "GET", 
            "vista_inventario_completo", 
            query=f"sucursal_id=eq.{sucursal_id}"
        )
        
        if not inventario:
            return {
                "total_medicamentos": 0,
                "total_stock": 0,
                "alertas_stock_bajo": 0,
                "valor_total_inventario": 0
            }
        
        # Calcular métricas en una sola pasada
        total_medicamentos = len(inventario)
        total_stock = sum(item.get('stock_actual', 0) for item in inventario)
        stock_bajo = len([
            item for item in inventario 
            if item.get('stock_actual', 0) <= item.get('stock_minimo', 0)
        ])
        valor_total = sum(
            item.get('stock_actual', 0) * item.get('precio_venta', 0) 
            for item in inventario
        )
        
        metricas = {
            "total_medicamentos": total_medicamentos,
            "total_stock": total_stock,
            "alertas_stock_bajo": stock_bajo,
            "valor_total_inventario": round(valor_total, 2)
        }
        
        print(f"✅ Métricas calculadas para sucursal {sucursal_id}: {metricas}")
        return metricas
        
    except Exception as e:
        print(f"❌ Error calculando métricas: {e}")
        return {
            "error": str(e),
            "total_medicamentos": 0,
            "total_stock": 0,
            "alertas_stock_bajo": 0,
            "valor_total_inventario": 0
        }

@app.post("/salidas/lote")
async def procesar_multiples_salidas(request: Request):
    """Procesar múltiples salidas con debug detallado"""
    try:
        # Obtener body raw
        body = await request.body()
        print(f"📥 BODY RAW: {body[:200]}...")  # Primeros 200 chars
        
        # Parsear JSON
        salidas_data = await request.json()
        print(f"📥 DATOS PARSEADOS: {type(salidas_data)}")
        print(f"📥 CANTIDAD DE SALIDAS: {len(salidas_data) if isinstance(salidas_data, list) else 'No es lista'}")
        
        if not isinstance(salidas_data, list):
            return {"error": "Se esperaba una lista", "tipo_recibido": type(salidas_data).__name__}
        
        resultados = []
        errores = []
        
        for i, salida in enumerate(salidas_data):
            try:
                print(f"\n🔍 === PROCESANDO SALIDA {i} ===")
                print(f"📋 Datos de salida: {salida}")
                print(f"📋 Tipo: {type(salida)}")
                
                # Verificar campos requeridos
                campos_requeridos = ['sucursal_id', 'medicamento_id', 'lote_id', 'numero_lote', 'cantidad', 'tipo_salida']
                for campo in campos_requeridos:
                    if campo not in salida:
                        print(f"❌ FALTA CAMPO REQUERIDO: {campo}")
                    else:
                        print(f"✅ {campo}: {salida[campo]} (tipo: {type(salida[campo])})")
                
                # Verificar claves foráneas
                print(f"\n🔑 Verificando claves foráneas:")
                
                # Verificar sucursal
                suc_check = make_supabase_request("GET", "sucursales", query=f"id=eq.{salida.get('sucursal_id')}")
                print(f"  - Sucursal {salida.get('sucursal_id')}: {'✅ Existe' if suc_check else '❌ NO EXISTE'}")
                
                # Verificar medicamento
                med_check = make_supabase_request("GET", "medicamentos", query=f"id=eq.{salida.get('medicamento_id')}")
                print(f"  - Medicamento {salida.get('medicamento_id')}: {'✅ Existe' if med_check else '❌ NO EXISTE'}")
                
                # Verificar lote
                lote_check = make_supabase_request("GET", "lotes_inventario", query=f"id=eq.{salida.get('lote_id')}")
                print(f"  - Lote {salida.get('lote_id')}: {'✅ Existe' if lote_check else '❌ NO EXISTE'}")
                
                # Procesar salida
                resultado = await crear_salida(salida)
                resultados.append(resultado)
                print(f"✅ Salida {i} procesada exitosamente")
                
            except Exception as e:
                print(f"❌ ERROR en salida {i}: {str(e)}")
                print(f"❌ Tipo de error: {type(e).__name__}")
                import traceback
                print(f"❌ Traceback: {traceback.format_exc()}")
                
                errores.append({
                    "salida": salida,
                    "error": str(e),
                    "tipo": type(e).__name__
                })
        
        respuesta = {
            "exitos": len(resultados),
            "errores": len(errores),
            "resultados": resultados,
            "errores_detalle": errores
        }
        
        print(f"\n📊 RESUMEN FINAL: {respuesta}")
        return respuesta
        
    except json.JSONDecodeError as e:
        print(f"❌ Error parseando JSON: {e}")
        return {"error": "JSON inválido", "detalle": str(e)}
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        print(f"❌ Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error procesando salidas: {str(e)}")

@app.post("/test-insercion-salida")
async def test_insercion_salida():
    """Test directo de inserción"""
    # Datos mínimos requeridos
    test_data = {
        "sucursal_id": 1,
        "medicamento_id": 1,
        "lote_id": 1,
        "numero_lote": "TEST-001",
        "cantidad": 1,
        "tipo_salida": "Venta",
        "precio_unitario": 10.0,
        "total": 10.0
    }
    
    print(f"🧪 Intentando insertar datos de prueba: {test_data}")
    
    try:
        resultado = make_supabase_request("POST", "salidas_inventario", data=test_data)
        return {"success": True, "resultado": resultado}
    except Exception as e:
        return {"success": False, "error": str(e), "datos_enviados": test_data}

@app.post("/salidas/debug")
async def debug_salida_data(data: dict):
    print(f"Datos recibidos: {data}")
    return {"received": data}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)