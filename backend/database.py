# backend/database.py
import os
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_headers():
    """Headers para las peticiones a Supabase"""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

def get_supabase_url(table_name, query=""):
    """Construir URL para Supabase REST API"""
    base_url = f"{SUPABASE_URL}/rest/v1/{table_name}"
    if query:
        return f"{base_url}?{query}"
    return base_url

def test_connection():
    """Función para probar la conexión"""
    try:
        url = get_supabase_url("medicamentos", "select=count")
        response = requests.get(url, headers=get_headers())
        
        if response.status_code == 200:
            print("✅ Conexión a Supabase exitosa")
            print(f"✅ Respuesta: {response.json()}")
            return True
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error conectando a Supabase: {e}")
        return False

# Funciones para operaciones básicas
def get_medicamentos():
    """Obtener todos los medicamentos"""
    try:
        url = get_supabase_url("medicamentos")
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error obteniendo medicamentos: {e}")
        return []

def get_inventario():
    """Obtener inventario actual con datos combinados"""
    try:
        # Query para unir medicamentos con lotes
        query = "select=id,nombre,categoria,stock_total:lotes_inventario(cantidad_actual).sum(),punto_reorden"
        url = get_supabase_url("medicamentos", query)
        response = requests.get(url, headers=get_headers())
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error obteniendo inventario: {e}")
        return []

# ========== SQLALCHEMY CONFIGURATION (para autenticación) ==========
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# URL de conexión de Supabase con la contraseña
DATABASE_URL = "REMOVED_DATABASE_URL"@aws-0-us-east-1.pooler.supabase.com:6543/postgres"

# Crear engine de SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependencia para obtener sesión de base de datos (SQLAlchemy)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()