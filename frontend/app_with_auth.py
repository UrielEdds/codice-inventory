"""
CÓDICE INVENTORY - Sistema Completo con Autenticación
Punto de entrada principal con sistema de roles y permisos
"""

import streamlit as st
import sys
import os

# Configuración de página DEBE estar primero
st.set_page_config(
    page_title="Códice Inventory - Sistema Seguro",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Agregar el directorio actual al path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar sistema de autenticación
from auth import require_auth, get_auth_manager

# Verificar autenticación ANTES de ejecutar el dashboard
try:
    current_user = require_auth()
    
    # Si llegamos aquí, el usuario está autenticado
    # Ejecutar el dashboard principal
    with open("dashboard.py", "r", encoding="utf-8") as f:
        dashboard_code = f.read()
    
    # Ejecutar el código del dashboard
    exec(dashboard_code)
    
except Exception as e:
    st.error(f"❌ Error cargando el sistema: {str(e)}")
    st.info("🔄 Recarga la página para intentar nuevamente")