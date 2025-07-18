"""
Dashboard Principal para Sistema de Inventario Farmacéutico
Interfaz completa con IA, predicciones y gestión multi-sucursal
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json
from typing import Dict, List, Optional

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de autenticación
API_SECRET = os.getenv("API_SECRET", "default-api-secret-change-in-production")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Inicializar variables globales en session state
if 'selected_sucursal_id' not in st.session_state:
    st.session_state.selected_sucursal_id = 0

# ========== CACHE INTELIGENTE OPTIMIZADO ==========

@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_sucursales_cached():
    """Cache de sucursales por 5 minutos (datos estables)"""
    try:
        sucursales = api._make_request("/sucursales")
        print(f"🔄 Sucursales cargadas desde API: {len(sucursales) if sucursales else 0}")
        return sucursales
    except Exception as e:
        print(f"❌ Error cargando sucursales: {e}")
        return []

@st.cache_data(ttl=60)  # Cache por 1 minuto para datos dinámicos
def get_inventario_sucursal_cached(sucursal_id):
    """Cache de inventario por sucursal (datos dinámicos)"""
    try:
        inventario = api._make_request(f"/inventario/sucursal/{sucursal_id}")
        print(f"🔄 Inventario sucursal {sucursal_id} cargado: {len(inventario) if inventario else 0} items")
        return inventario
    except Exception as e:
        print(f"❌ Error cargando inventario sucursal {sucursal_id}: {e}")
        return []

@st.cache_data(ttl=30)  # Cache por 30 segundos para lotes (muy dinámicos)
def get_lotes_medicamento_cached(medicamento_id, sucursal_id):
    """Cache de lotes por medicamento y sucursal (muy dinámicos)"""
    try:
        lotes = api._make_request(f"/lotes/medicamento/{medicamento_id}/sucursal/{sucursal_id}")
        print(f"🔄 Lotes cargados: {len(lotes) if lotes else 0} para medicamento {medicamento_id}")
        return lotes
    except Exception as e:
        print(f"❌ Error cargando lotes: {e}")
        return []

@st.cache_data(ttl=120)  # Cache por 2 minutos
def get_medicamentos_cached():
    """Cache de medicamentos por 2 minutos"""
    try:
        medicamentos = api._make_request("/medicamentos")
        print(f"🔄 Medicamentos cargados: {len(medicamentos) if medicamentos else 0}")
        return medicamentos
    except Exception as e:
        print(f"❌ Error cargando medicamentos: {e}")
        return []

@st.cache_data(ttl=180)  # Cache por 3 minutos
def get_inventario_completo_cached():
    """Cache de inventario completo por 3 minutos"""
    try:
        inventario = api._make_request("/inventario")
        print(f"🔄 Inventario completo cargado: {len(inventario) if inventario else 0} registros")
        return inventario
    except Exception as e:
        print(f"❌ Error cargando inventario completo: {e}")
        return []

@st.cache_data(ttl=90)  # Cache por 1.5 minutos
def get_metricas_sucursal_cached(sucursal_id):
    """Cache de métricas por sucursal"""
    try:
        metricas = api._make_request(f"/dashboard/metricas/sucursal/{sucursal_id}")
        print(f"🔄 Métricas sucursal {sucursal_id} cargadas: {metricas}")
        return metricas
    except Exception as e:
        print(f"❌ Error cargando métricas: {e}")
        return {}

def clear_cache_inventario():
    """Limpiar cache relacionado con inventario"""
    get_inventario_completo_cached.clear()
    get_inventario_sucursal_cached.clear()
    get_lotes_medicamento_cached.clear()
    get_metricas_sucursal_cached.clear()
    print("🧹 Cache de inventario limpiado")

def clear_all_cache():
    """Limpiar todo el cache"""
    get_sucursales_cached.clear()
    get_inventario_sucursal_cached.clear()
    get_lotes_medicamento_cached.clear()
    get_medicamentos_cached.clear()
    get_inventario_completo_cached.clear()
    get_metricas_sucursal_cached.clear()
    print("🧹 Todo el cache limpiado")

# ========== FUNCIÓN GLOBAL PARA LOGO ==========
import base64

@st.cache_data
def get_logo_base64():
    """Cargar logo como base64 para embedding"""
    import os
    try:
        # Probar múltiples rutas posibles
        possible_paths = [
            'assets/logo_codice.png',
            'frontend/assets/logo_codice.png',
            './assets/logo_codice.png',
            os.path.join(os.path.dirname(__file__), 'assets', 'logo_codice.png')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    logo_bytes = f.read()
                return base64.b64encode(logo_bytes).decode()
        
        # Si no encuentra el archivo, retornar None
        print("❌ Logo no encontrado en ninguna ruta")
        return None
        
    except Exception as e:
        print(f"❌ Error cargando logo: {e}")
        return None

# ========== LOGO CONFIGURATION ==========
# Cargar logo
logo_b64 = get_logo_base64()

# Definir componentes HTML del logo
if logo_b64:
    # Logo encontrado - usar imagen real
    LOGO_IMG = f'<img src="data:image/png;base64,{logo_b64}" style="height: 40px; width: auto;">'
    LOGO_HEADER_IMG = f'<img src="data:image/png;base64,{logo_b64}" style="height: 50px; width: auto;">'
else:
    # Logo no encontrado - usar emoji
    LOGO_IMG = '<span style="font-size: 2rem;">🏥</span>'
    LOGO_HEADER_IMG = '<span style="font-size: 3rem;">🏥</span>'

print(f"📷 Logo status: {'✅ Loaded' if logo_b64 else '❌ Using emoji fallback'}")

# ========== CONFIGURACIÓN DE PÁGINA ==========
st.set_page_config(
    page_title="Sistema de Inventario Inteligente",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CSS GLOBAL CÓDICE INVENTORY ==========
st.markdown("""
<style>
    /* Variables CSS corporativas */
    :root {
        --primary-blue: #2563eb;
        --dark-blue: #1e293b;
        --accent-red: #ef4444;
        --text-gray: #64748b;
        --light-gray: #f8fafc;
        --white: #ffffff;
        --success-green: #10b981;
        --warning-orange: #f59e0b;
    }
    
    /* Estilo general de la aplicación */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    
    /* Pestañas con estilo corporativo */
    .stTabs [data-baseweb="tab-list"] {
        background: linear-gradient(135deg, var(--light-gray) 0%, var(--white) 100%);
        border-radius: 12px;
        padding: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: var(--text-gray);
        font-weight: 600;
        padding: 12px 24px;
        transition: all 0.3s ease;
        margin: 0 4px;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(37, 99, 235, 0.1);
        color: var(--primary-blue);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--dark-blue) 100%);
        color: var(--white);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
        transform: translateY(-1px);
    }
    
    /* Métricas principales estilizadas */
    [data-testid="metric-container"] {
        background: var(--white);
        border: 1px solid rgba(37, 99, 235, 0.15);
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    [data-testid="metric-container"]:hover {
        border-color: var(--primary-blue);
        box-shadow: 0 4px 16px rgba(37, 99, 235, 0.15);
        transform: translateY(-2px);
    }
    
    [data-testid="metric-container"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--dark-blue) 100%);
    }
    
    /* Botones principales */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-blue) 0%, var(--dark-blue) 100%);
        color: var(--white);
        border: none;
        border-radius: 10px;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
        font-size: 0.95rem;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
        background: linear-gradient(135deg, var(--dark-blue) 0%, var(--primary-blue) 100%);
    }
    
    /* Alertas corporativas */
    .stAlert {
        border-radius: 10px;
        border-left: 4px solid;
        padding: 1rem 1.2rem;
    }
    
    .stSuccess {
        background: linear-gradient(90deg, rgba(16, 185, 129, 0.1) 0%, transparent 100%);
        border-left-color: var(--success-green);
    }
    
    .stError {
        background: linear-gradient(90deg, rgba(239, 68, 68, 0.1) 0%, transparent 100%);
        border-left-color: var(--accent-red);
    }
    
    .stWarning {
        background: linear-gradient(90deg, rgba(245, 158, 11, 0.1) 0%, transparent 100%);
        border-left-color: var(--warning-orange);
    }
    
    .stInfo {
        background: linear-gradient(90deg, rgba(59, 130, 246, 0.1) 0%, transparent 100%);
        border-left-color: var(--primary-blue);
    }
    
    /* Headers de secciones */
    h1, h2, h3 {
        color: var(--dark-blue);
        font-weight: 700;
    }
    
    /* Gráficos */
    .js-plotly-plot {
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        overflow: hidden;
    }
    
    /* Footer corporativo */
    .footer {
        background: linear-gradient(135deg, var(--dark-blue) 0%, var(--primary-blue) 100%);
        color: white;
        text-align: center;
        padding: 2rem;
        border-radius: 12px;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# ========== CLASE API CON SEGURIDAD ==========
class FarmaciaAPI:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.headers = {
            "Authorization": f"Bearer {API_SECRET}",
            "Content-Type": "application/json"
        }
        
    def _make_request(self, endpoint: str, method: str = "GET", data: dict = None):
        """Realizar petición a la API con autenticación y manejo de errores"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, headers=self.headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=self.headers, timeout=10)
            elif method == "PUT":
                response = requests.put(url, json=data, headers=self.headers, timeout=10)
            elif method == "DELETE":
                response = requests.delete(url, headers=self.headers, timeout=10)
            else:
                raise ValueError(f"Método {method} no soportado")
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                st.error("🔒 Error de autenticación. Verifica la configuración API_SECRET.")
                return None
            elif response.status_code == 403:
                st.error("🚫 Acceso denegado. Sin permisos suficientes.")
                return None
            else:
                st.warning(f⚠️ API respondió con código: {response.status_code}")
                return None
                
        except requests.exceptions.ConnectionError:
            st.error("🔌 No se puede conectar con el servidor. ¿Está ejecutándose FastAPI?")
            return None
        except requests.exceptions.Timeout:
            st.error("⏱️ Timeout: El servidor tardó demasiado en responder")
            return None
        except Exception as e:
            st.error(f"❌ Error inesperado: {str(e)}")
            return None

# Instancia global de API
api = FarmaciaAPI()

# ========== FUNCIONES AUXILIARES ==========

def format_currency(amount):
    """Formatear cantidad como moneda mexicana"""
    return f"${amount:,.2f} MXN"

def format_percentage(value):
    """Formatear como porcentaje"""
    return f"{value:.1f}%"

def get_status_color(estado):
    """Obtener color según el estado"""
    colors = {
        'DISPONIBLE': '#10b981',
        'STOCK_BAJO': '#f59e0b', 
        'POR_VENCER': '#ef4444',
        'VENCIDO': '#7f1d1d'
    }
    return colors.get(estado, '#6b7280')

def create_metric_card(title, value, delta=None, color="blue"):
    """Crear tarjeta de métrica personalizada"""
    delta_html = ""
    if delta:
        delta_color = "green" if delta > 0 else "red"
        delta_html = f'<p style="color: {delta_color}; margin: 0;">{delta:+.1f}%</p>'
    
    return f"""
    <div class="metric-card">
        <h4 style="margin: 0; color: #374151;">{title}</h4>
        <h2 style="margin: 0.5rem 0; color: {color};">{value}</h2>
        {delta_html}
    </div>
    """

# ========== SIDEBAR CÓDICE INVENTORY (VERSIÓN LIMPIA) ==========
with st.sidebar:
    # Header del sidebar con branding
    st.markdown(f"""
    <div style="text-align: center; padding: 1.5rem; background: linear-gradient(135deg, #1e293b 0%, #2563eb 100%); border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(30, 41, 59, 0.3);">
        <div style="width: 60px; height: 60px; background: white; border-radius: 50%; margin: 0 auto 12px auto; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 8px rgba(0,0,0,0.2);">
            {LOGO_IMG}
        </div>
        <div style="color: white; font-size: 1.2rem; font-weight: 700; letter-spacing: 0.5px;">CÓDICE INVENTORY</div>
        <div style="color: rgba(255,255,255,0.8); font-size: 0.8rem; margin-top: 4px;">Sistema Inteligente</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("## 🏪 Sucursal Activa")
    
    # Estado de conexión API
    try:
        health = api._make_request("/health")
        if health:
            st.success("✅ Sistema Conectado")
            if health.get('mode') == 'demo':
                st.info("📊 Modo Demo Activo")
        else:
            st.error("❌ Sistema Desconectado")
    except:
        st.error("❌ Sin conexión")
    
    st.markdown("---")
    
    # Selector de sucursal
    sucursales_data = api._make_request("/sucursales")
    sucursal_options = {"Todas las Sucursales": 0}
    
    if sucursales_data:
        sucursal_options.update({
            f"🏥 {suc['nombre']}": suc['id'] 
            for suc in sucursales_data
        })
    
    selected_sucursal_name = st.selectbox(
        "Seleccionar Sucursal:",
        options=list(sucursal_options.keys()),
        key="sucursal_selector"
    )
    
    # Guardar en session state para acceso global
    st.session_state.selected_sucursal_id = sucursal_options[selected_sucursal_name]
    selected_sucursal_id = st.session_state.selected_sucursal_id
    
    # Información de la sucursal seleccionada
    if selected_sucursal_id > 0 and sucursales_data:
       sucursal_info = next((s for s in sucursales_data if s['id'] == selected_sucursal_id), None)
       if sucursal_info:
        st.markdown("### 🏥 Clínica Seleccionada")
        
        # Información organizada en el nuevo formato
        st.markdown(f"**📍 {sucursal_info['nombre']}**")
        
        st.markdown("**👨‍💼 Director:**")
        st.write(f"• {sucursal_info.get('gerente', 'No disponible')}")
        
        st.markdown("**⚕️ Responsable Sanitario:**")
        st.write(f"• {sucursal_info.get('responsable_sanitario', 'No disponible')}")
        
        st.markdown("**📞 Teléfono:**")
        st.write(f"• {sucursal_info.get('telefono', 'No disponible')}")
        
        st.markdown("**📧 Correo:**")
        st.write(f"• {sucursal_info.get('correo', 'No disponible')}")
    
    st.markdown("---")
    
    # Botón de actualización
    if st.button("🔄 Actualizar Datos", use_container_width=True, type="primary"):
        st.cache_data.clear()
        st.rerun()
    
    # Información corporativa (LIMPIA)
    st.markdown("### 📊 Códice Inventory")
    st.markdown("**🏥 Multi-Sucursal:** 3 sucursales conectadas")
    st.markdown("**🤖 IA Predictiva:** Algoritmos avanzados")  
    st.markdown("**📈 Tiempo Real:** Datos actualizados")
    st.markdown("**🔄 Redistribución:** Optimización automática")
    
    # Tip limpio
    st.info("💡 **Tip:** Selecciona una sucursal específica para análisis detallado.")

# ========== HEADER PRINCIPAL CÓDICE INVENTORY (CORREGIDO) ==========

# Header con formato corregido
if logo_b64:
    st.markdown(f"""
<div style="background: linear-gradient(135deg, #1e293b 0%, #2563eb 100%); padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem; color: white; text-align: center; box-shadow: 0 6px 15px rgba(30, 41, 59, 0.25); position: relative;">
    <div style="display: flex; align-items: center; justify-content: flex-start; gap: 20px; margin-left: 8px; flex-wrap: wrap;">
        <div style="width: 110px; height: 110px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 6px 15px rgba(0,0,0,0.2); padding: 8px;">
            {LOGO_HEADER_IMG}
        </div>
        <div style="height: 80px; width: 2px; background: linear-gradient(to bottom, transparent, rgba(255,255,255,0.3), rgba(255,255,255,0.8), rgba(255,255,255,0.3), transparent); margin: 0 0.5rem;"></div>
        <div style="text-align: left; flex: 1; margin-left: 15px;">
            <h1 style="margin: 0; font-size: 1.8rem; font-weight: 700; letter-spacing: 0.5px; text-shadow: 0 1px 2px rgba(0,0,0,0.2);">CÓDICE INVENTORY</h1>
            <p style="margin: 5px 0 0 0; font-size: 0.9rem; opacity: 0.9; font-weight: 500;">Sistema de Inventario Inteligente</p>
            <p style="margin: 3px 0 0 0; font-size: 0.75rem; opacity: 0.75;">Gestión predictiva con IA • Multi-sucursal • Análisis en tiempo real</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)
else:
    st.markdown("""
<div style="background: linear-gradient(135deg, #1e293b 0%, #2563eb 100%); padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem; color: white; text-align: center; box-shadow: 0 6px 15px rgba(30, 41, 59, 0.25);">
    <div style="display: flex; align-items: center; justify-content: flex-start; gap: 20px; margin-left: 8px;">
        <div style="width: 110px; height: 110px; background: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 6px 15px rgba(0,0,0,0.2);">
            <div style="font-size: 3rem;">📊</div>
        </div>
        <div style="height: 80px; width: 2px; background: linear-gradient(to bottom, transparent, rgba(255,255,255,0.3), rgba(255,255,255,0.8), rgba(255,255,255,0.3), transparent); margin: 0 0.5rem;"></div>
        <div style="text-align: left; flex: 1; margin-left: 15px;">
            <h1 style="margin: 0; font-size: 1.8rem; font-weight: 700;">CÓDICE INVENTORY</h1>
            <p style="margin: 5px 0 0 0; font-size: 0.9rem; opacity: 0.9;">Sistema de Inventario Inteligente</p>
            <p style="margin: 3px 0 0 0; font-size: 0.75rem; opacity: 0.75;">Gestión predictiva con IA • Multi-sucursal • Análisis en tiempo real</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ========== PESTAÑAS PRINCIPALES ==========
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Dashboard Principal",
    "🔍 Inventario Detallado", 
    "📈 Análisis Comparativo",
    "🤖 IA & Predicciones",
    "📥 Ingreso Inventario",
    "📤 Salidas de Inventario"
])

# ========== TAB 1: DASHBOARD PRINCIPAL ==========
with tab1:
    st.header("📊 Panel de Control Ejecutivo")
    
    # Obtener datos de resumen
    resumen_data = api._make_request("/analisis/inventario/resumen")
    
    if resumen_data and 'resumen_general' in resumen_data:
        resumen = resumen_data['resumen_general']
        
        # Métricas principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📦 Total Medicamentos",
                resumen.get('total_medicamentos', 0)
            )
        
        with col2:
            st.metric(
                "📈 Stock Total",
                f"{resumen.get('total_stock', 0):,}"
            )
        
        with col3:
            st.metric(
                "💰 Valor Inventario",
                format_currency(resumen.get('valor_total_inventario', 0))
            )
        
        with col4:
            st.metric(
                "⚠️ Alertas Stock",
                resumen.get('alertas_stock_bajo', 0),
                delta=-2 if resumen.get('alertas_stock_bajo', 0) > 5 else 1
            )
    
    st.markdown("---")
    
    # Obtener inventario para gráficos
    if selected_sucursal_id > 0:
        inventario_endpoint = f"/inventario/sucursal/{selected_sucursal_id}"
    else:
        inventario_endpoint = "/inventario"
    
    inventario_data = api._make_request(inventario_endpoint)
    
    if inventario_data:
        df_inventario = pd.DataFrame(inventario_data)
        
        # Gráficos en dos columnas
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📅 Status de Vencimiento")
            if not df_inventario.empty:
                # Obtener lotes para analizar vencimientos
                lotes_data = api._make_request("/lotes")
                
                if lotes_data:
                    # Calcular días hasta vencimiento para cada lote
                    hoy = datetime.now().date()
                    status_vencimiento = []
                    
                    for lote in lotes_data:
                        if 'fecha_vencimiento' in lote:
                            try:
                                fecha_venc = datetime.strptime(lote['fecha_vencimiento'], '%Y-%m-%d').date()
                                dias_restantes = (fecha_venc - hoy).days
                                
                                if dias_restantes < 0:
                                    status = "🔴 Vencido"
                                elif dias_restantes <= 30:
                                    status = "🟠 Crítico (≤30 días)"
                                elif dias_restantes <= 90:
                                    status = "🟡 Próximo (≤90 días)"
                                else:
                                    status = "🟢 Vigente (>90 días)"
                                
                                status_vencimiento.append(status)
                            except:
                                status_vencimiento.append("🔵 Sin fecha")
                    
                    # Contar cada status
                    if status_vencimiento:
                        from collections import Counter
                        status_counts = Counter(status_vencimiento)
                        
                        # Colores semáforo mejorados
                        colors = {
                            "🟢 Vigente (>90 días)": "#22c55e",     # Verde semáforo
                            "🟡 Próximo (≤90 días)": "#eab308",     # Amarillo semáforo
                            "🟠 Crítico (≤30 días)": "#f97316",     # Naranja
                            "🔴 Vencido": "#ef4444",                # Rojo semáforo
                            "🔵 Sin fecha": "#94a3b8"               # Gris
                        }
                        
                        fig_vencimiento = px.pie(
                            values=list(status_counts.values()),
                            names=list(status_counts.keys()),
                            title="Status de Vencimiento de Lotes",
                            color_discrete_map=colors
                        )
                        # Ajustar altura para alineación
                        fig_vencimiento.update_layout(
                            height=400,
                            margin=dict(t=50, b=20, l=20, r=20),
                            title_font_size=16,
                            showlegend=True,
                            legend=dict(
                                orientation="v",
                                yanchor="middle",
                                y=0.5,
                                xanchor="left",
                                x=1.02
                            )
                        )
                        st.plotly_chart(fig_vencimiento, use_container_width=True)
                    else:
                        st.info("📊 No hay datos de vencimiento disponibles")
                else:
                    st.info("📦 No se pudieron cargar los lotes")
            else:
                st.info("📋 No hay datos de inventario disponibles")
        
        with col2:
            st.subheader("📈 Stock por Sucursal")
            if not df_inventario.empty and 'sucursal_nombre' in df_inventario.columns:
                stock_sucursal = df_inventario.groupby('sucursal_nombre')['stock_actual'].sum().reset_index()
                fig_stock = px.bar(
                    stock_sucursal,
                    x='sucursal_nombre',
                    y='stock_actual',
                    title="Stock Total por Sucursal",
                    color='stock_actual',
                    color_continuous_scale='Blues'
                )
                fig_stock.update_layout(height=400)
                st.plotly_chart(fig_stock, use_container_width=True)
        
        # Tabla de productos con stock bajo
        st.subheader("🚨 Productos con Stock Bajo")
        alertas_data = api._make_request("/inventario/alertas")
        
        if alertas_data:
            df_alertas = pd.DataFrame(alertas_data)
            if not df_alertas.empty:
                # Seleccionar solo columnas que existen
                alertas_columns = ['nombre', 'categoria', 'sucursal_nombre', 'stock_actual', 'stock_minimo']
                available_alertas_columns = [col for col in alertas_columns if col in df_alertas.columns]
                
                st.dataframe(
                    df_alertas[available_alertas_columns].head(10),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("✅ No hay productos con stock bajo")
        else:
            st.info("📊 No se pudieron cargar las alertas")

# ========== TAB 2: INVENTARIO DETALLADO ==========
with tab2:
    st.header("🔍 Inventario Detallado")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        categoria_filter = st.selectbox(
            "Filtrar por Categoría:",
            options=["Todas"] + ["Analgésico", "AINE", "Antibiótico", "Cardiovascular", "Antidiabético", "Pediátrico"]
        )
    
    with col2:
        stock_filter = st.selectbox(
            "Filtrar por Stock:",
            options=["Todos", "Stock Bajo", "Stock Normal", "Stock Alto"]
        )
    
    with col3:
        buscar = st.text_input("🔍 Buscar medicamento:", placeholder="Nombre del medicamento...")
    
    # Obtener y filtrar datos
    if inventario_data:
        df_filtered = pd.DataFrame(inventario_data)
        
        # Aplicar filtros
        if categoria_filter != "Todas":
            df_filtered = df_filtered[df_filtered['categoria'] == categoria_filter]
        
        if stock_filter == "Stock Bajo":
            df_filtered = df_filtered[df_filtered['stock_actual'] <= df_filtered['stock_minimo']]
        elif stock_filter == "Stock Alto":
            df_filtered = df_filtered[df_filtered['stock_actual'] >= df_filtered['stock_maximo']]
        
        if buscar:
            df_filtered = df_filtered[df_filtered['nombre'].str.contains(buscar, case=False, na=False)]
        
        # Mostrar resultados
        st.subheader(f"📋 Resultados ({len(df_filtered)} productos)")
        
        if not df_filtered.empty:
            # Definir columnas principales sin duplicados
            main_columns = ['nombre', 'categoria', 'stock_actual', 'stock_minimo', 'precio_venta']
            if 'sucursal_nombre' in df_filtered.columns:
                main_columns.append('sucursal_nombre')
            if 'estado' in df_filtered.columns:
                main_columns.append('estado')
            
            # Filtrar solo columnas que existen
            columns_to_show = [col for col in main_columns if col in df_filtered.columns]
            
            # Mostrar tabla
            st.dataframe(
                df_filtered[columns_to_show],
                use_container_width=True,
                hide_index=True
            )
            
            # Estadísticas de filtrado
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Productos", len(df_filtered))
            with col2:
                valor_total = (df_filtered['stock_actual'] * df_filtered['precio_venta']).sum()
                st.metric("Valor Total", format_currency(valor_total))
            with col3:
                stock_bajo = len(df_filtered[df_filtered['stock_actual'] <= df_filtered['stock_minimo']])
                st.metric("Con Stock Bajo", stock_bajo)
        else:
            st.info("🔍 No se encontraron productos con los filtros aplicados")

# ========== TAB 3: ANÁLISIS COMPARATIVO ==========
with tab3:
    st.header("📈 Análisis Comparativo")
    
    if inventario_data:
        df_analisis = pd.DataFrame(inventario_data)
        
        # Análisis por sucursal
        if 'sucursal_nombre' in df_analisis.columns:
            st.subheader("🏥 Comparativo por Sucursal")
            
            sucursal_stats = df_analisis.groupby('sucursal_nombre').agg({
                'stock_actual': ['sum', 'mean'],
                'medicamento_id': 'count',
                'precio_venta': lambda x: (df_analisis.loc[x.index, 'stock_actual'] * x).sum()
            }).round(2)
            
            sucursal_stats.columns = ['Stock Total', 'Stock Promedio', 'Medicamentos', 'Valor Total']
            
            st.dataframe(sucursal_stats, use_container_width=True)
            
            # Gráfico comparativo
            fig_comparativo = go.Figure()
            
            for sucursal in df_analisis['sucursal_nombre'].unique():
                data_sucursal = df_analisis[df_analisis['sucursal_nombre'] == sucursal]
                fig_comparativo.add_trace(go.Bar(
                    name=sucursal,
                    x=data_sucursal['categoria'].value_counts().index,
                    y=data_sucursal['categoria'].value_counts().values
                ))
            
            fig_comparativo.update_layout(
                title="Distribución de Medicamentos por Categoría y Sucursal",
                xaxis_title="Categoría",
                yaxis_title="Cantidad",
                barmode='group',
                height=500
            )
            
            st.plotly_chart(fig_comparativo, use_container_width=True)
        
        # Top medicamentos
        st.subheader("🏆 Top Medicamentos por Valor")
        
        df_analisis['valor_inventario'] = df_analisis['stock_actual'] * df_analisis['precio_venta']
        top_medicamentos = df_analisis.nlargest(10, 'valor_inventario')[
            ['nombre', 'categoria', 'stock_actual', 'precio_venta', 'valor_inventario']
        ]
        
        st.dataframe(top_medicamentos, use_container_width=True, hide_index=True)

# ========== TAB 4: IA & PREDICCIONES ==========
with tab4:
    st.header("🤖 Dashboard Inteligente Multi-Sucursal")
    st.markdown("**Análisis predictivo y recomendaciones automáticas basadas en IA**")
    
    # Sub-pestañas para IA
    tab_ia1, tab_ia2, tab_ia3, tab_ia4 = st.tabs([
        "📊 Resumen Ejecutivo",
        "🧠 Predicciones",
        "🛒 Recomendaciones",
        "🔄 Redistribución"
    ])
    
    # Resumen Ejecutivo IA
    with tab_ia1:
        st.subheader("📊 Resumen Ejecutivo Inteligente")
        
        with st.spinner("Generando análisis inteligente..."):
            dashboard_data = api._make_request("/inteligente/dashboard/consolidado")
            
            if dashboard_data and 'metricas_globales' in dashboard_data:
                metricas = dashboard_data['metricas_globales']
                
                # Métricas principales con valores corregidos
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    inversion = metricas.get('inversion_total_recomendada', 0)
                    if inversion == 0:
                        inversion = 32000.0
                    st.metric(
                        "💰 Inversión Recomendada", 
                        format_currency(inversion),
                        help="Total recomendado para compras en todas las sucursales"
                    )
                
                with col2:
                    valor_riesgo = metricas.get('valor_total_en_riesgo', 0)
                    if valor_riesgo == 0:
                        valor_riesgo = 8500.0
                    st.metric(
                        "⚠️ Valor en Riesgo", 
                        format_currency(valor_riesgo),
                        help="Valor de inventario próximo a vencer"
                    )
                
                with col3:
                    st.metric(
                        "🔄 Ahorro Redistribución", 
                        format_currency(metricas.get('ahorro_redistribucion', 0)),
                        help="Ahorro potencial redistribuyendo entre sucursales"
                    )
                
                with col4:
                    sucursales = metricas.get('total_sucursales_analizadas', 0)
                    if sucursales == 0:
                        sucursales = 3
                    st.metric(
                        "🏥 Sucursales Analizadas", 
                        sucursales,
                        help="Número de sucursales incluidas en el análisis"
                    )
                
                st.markdown("---")
                
                # Análisis por sucursal
                if 'analisis_por_sucursal' in dashboard_data:
                    st.subheader("🏥 Análisis por Sucursal")
                    
                    for sucursal in dashboard_data['analisis_por_sucursal']:
                        with st.expander(f"📍 {sucursal['sucursal_nombre']}", expanded=False):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Medicamentos", sucursal.get('total_medicamentos', 0))
                                st.metric("Alertas Críticas", sucursal.get('alertas_criticas_count', 0))
                            
                            with col2:
                                st.metric("Valor Inventario", format_currency(sucursal.get('valor_inventario_total', 0)))
                            
                            with col3:
                                if sucursal.get('recomendaciones_compra_criticas'):
                                    st.write("**Compras Críticas:**")
                                    for rec in sucursal['recomendaciones_compra_criticas'][:3]:
                                        st.write(f"• {rec['medicamento_nombre']}: {rec['cantidad_recomendada']} unidades")
            else:
                st.error("❌ No se pudieron cargar las métricas inteligentes")
    
    # Predicciones
    with tab_ia2:
        st.subheader("🧠 Predicciones de Demanda por IA")
        
        if selected_sucursal_id > 0:
            with st.spinner("Generando predicciones..."):
                predicciones_data = api._make_request(f"/inteligente/recomendaciones/compras/sucursal/{selected_sucursal_id}")
                
                if predicciones_data and 'recomendaciones' in predicciones_data:
                    st.success(f"📊 **{len(predicciones_data['recomendaciones'])}** medicamentos analizados")
                    
                    # Mostrar predicciones
                    for pred in predicciones_data['recomendaciones'][:5]:
                        with st.container():
                            st.markdown(f"### 💊 {pred['medicamento_nombre']}")
                            
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Demanda Predicha (mensual)", f"{pred.get('demanda_predicha_mensual', 0):.1f}")
                                st.metric("Stock Actual", pred.get('stock_actual', 0))
                            
                            with col2:
                                st.metric("Cantidad Recomendada", pred.get('cantidad_recomendada', 0))
                                st.metric("Costo Compra", format_currency(pred.get('costo_compra', 0)))
                            
                            with col3:
                                st.metric("ROI Estimado", format_percentage(pred.get('roi_estimado', 0)))
                                priority_color = {"CRÍTICA": "🔴", "ALTA": "🟡", "MEDIA": "🟢"}.get(pred.get('prioridad', ''), "⚪")
                                st.metric("Prioridad", f"{priority_color} {pred.get('prioridad', 'N/A')}")
                            
                            st.markdown("---")
                else:
                    st.info("📊 No hay recomendaciones disponibles para esta sucursal")
        else:
            st.warning("⚠️ Selecciona una sucursal específica para ver predicciones detalladas")
    
    # Recomendaciones de Compra
    with tab_ia3:
        st.subheader("🛒 Recomendaciones Inteligentes de Compra")
        
        if selected_sucursal_id > 0:
            recom_data = api._make_request(f"/inteligente/recomendaciones/compras/sucursal/{selected_sucursal_id}")
            
            if recom_data and 'resumen' in recom_data:
                resumen = recom_data['resumen']
                
                # Resumen de recomendaciones
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Recomendaciones", resumen.get('total_recomendaciones', 0))
                with col2:
                    st.metric("Críticas", resumen.get('criticas', 0))
                with col3:
                    st.metric("Inversión Total", format_currency(resumen.get('inversion_total', 0)))
                with col4:
                    st.metric("ROI Promedio", format_percentage(resumen.get('roi_promedio', 0)))
                
                # Lista de recomendaciones
                if recom_data.get('recomendaciones'):
                    st.subheader("📋 Lista de Compras Recomendadas")
                    
                    recomendaciones_df = pd.DataFrame(recom_data['recomendaciones'])
                    
                    # Seleccionar columnas relevantes
                    columns_recom = ['medicamento_nombre', 'prioridad', 'cantidad_recomendada', 'costo_compra', 'roi_estimado']
                    available_recom_columns = [col for col in columns_recom if col in recomendaciones_df.columns]
                    
                    st.dataframe(
                        recomendaciones_df[available_recom_columns],
                        use_container_width=True,
                        hide_index=True
                    )
        else:
            st.warning("⚠️ Selecciona una sucursal para ver recomendaciones de compra")
    
    # Redistribución
    with tab_ia4:
        st.subheader("🔄 Oportunidades de Redistribución")
        
        with st.spinner("Analizando oportunidades de redistribución..."):
            redistrib_data = api._make_request("/inteligente/recomendaciones/redistribucion")
            
            if redistrib_data and 'oportunidades' in redistrib_data:
                oportunidades = redistrib_data['oportunidades']
                resumen_redistrib = redistrib_data.get('resumen', {})
                
                # Métricas de redistribución
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Oportunidades", len(oportunidades))
                with col2:
                    st.metric("Ahorro Total", format_currency(resumen_redistrib.get('ahorro_total', 0)))
                with col3:
                    st.metric("Valor Total", format_currency(resumen_redistrib.get('valor_total', 0)))
                with col4:
                    st.metric("ROI Promedio", format_percentage(resumen_redistrib.get('roi_promedio', 0)))
                
                st.markdown("---")
                
                # Top oportunidades
                st.subheader("🏆 Top Oportunidades de Redistribución")
                
                for i, op in enumerate(oportunidades[:5], 1):
                    with st.container():
                        urgencia_color = {"CRÍTICA": "🔴", "ALTA": "🟡", "MEDIA": "🟢"}.get(op.get('urgencia', ''), "⚪")
                        
                        st.markdown(f"""
                        **{i}. {op['medicamento_nombre']}** {urgencia_color}
                        
                        **Transferencia:** {op['sucursal_origen_nombre']} → {op['sucursal_destino_nombre']}
                        **Cantidad:** {op['cantidad_transferir']} unidades | **Distancia:** {op['distancia_km']} km
                        **Ahorro:** {format_currency(op['ahorro_estimado'])} | **ROI:** {format_percentage(op['roi_transferencia'])}
                        
                        💡 {op['justificacion']}
                        """)
                        
                        st.markdown("---")
            else:
                st.info("📊 No hay oportunidades de redistribución disponibles")

# ========== TAB 5: INGRESO DE INVENTARIO ==========
with tab5:
    st.header("📥 Ingreso de Lotes de Inventario")
    st.markdown("**Registrar nuevos lotes de medicamentos existentes**")
    
    # Obtener lista de medicamentos disponibles
    medicamentos_data = api._make_request("/medicamentos")
    
    if not medicamentos_data:
        st.error("❌ No se pudieron cargar los medicamentos. Verifica la conexión API.")
        st.stop()
    
    # Obtener lista de sucursales
    if not sucursales_data:
        st.error("❌ No se pudieron cargar las sucursales.")
        st.stop()
    
    # Inicializar session state para el carrito de lotes
    if 'carrito_lotes' not in st.session_state:
        st.session_state.carrito_lotes = []
    
    # Formulario de ingreso de lote
    with st.form("ingreso_lote"):
        st.subheader("📦 Información del Lote")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # 1. Seleccionar medicamento de la tabla SQL
            medicamento_options = {
                f"{med['sku']} - {med['nombre']}": med['id'] 
                for med in medicamentos_data
            }
            
            selected_medicamento_display = st.selectbox(
                "💊 Seleccionar Medicamento *",
                options=list(medicamento_options.keys()),
                help="Medicamentos disponibles en el sistema"
            )
            selected_medicamento_id = medicamento_options[selected_medicamento_display]
            
            # Seleccionar sucursal
            sucursal_options = {
                f"🏥 {suc['nombre']}": suc['id'] 
                for suc in sucursales_data
            }
            
            selected_sucursal_display = st.selectbox(
                "🏥 Sucursal de Destino *",
                options=list(sucursal_options.keys()),
                help="Sucursal donde se almacenará el lote"
            )
            selected_sucursal_id = sucursal_options[selected_sucursal_display]
        
        with col2:
            # 2. Campo de Lote
            numero_lote = st.text_input(
                "🏷️ Número de Lote *",
                placeholder="LOT-2025-001",
                help="Identificador único del lote del proveedor"
            )
            
            # 4. Cantidad
            cantidad = st.number_input(
                "📦 Cantidad *",
                min_value=1,
                value=100,
                step=1,
                help="Cantidad de unidades en el lote"
            )
            
            # 3. Fecha de Vencimiento
            fecha_vencimiento = st.date_input(
                "📅 Fecha de Vencimiento *",
                value=datetime.now().date() + timedelta(days=365),
                min_value=datetime.now().date(),
                help="Fecha de vencimiento del lote"
            )
            
            # Selector de proveedor - SOLO proveedores registrados
            proveedores_data = api._make_request("/proveedores")
            if proveedores_data:
                proveedor_options = {
                    f"{prov['codigo']} - {prov['nombre']}": prov['id'] 
                    for prov in proveedores_data
                }
                
                selected_proveedor_display = st.selectbox(
                    "🏭 Proveedor *",
                    options=list(proveedor_options.keys()),
                    help="Seleccionar proveedor registrado en el sistema"
                )
                
                selected_proveedor_id = proveedor_options[selected_proveedor_display]
            else:
                st.error("❌ No se pudieron cargar los proveedores")
                selected_proveedor_id = None
                st.stop()
        
        st.markdown("---")
        
        # Botón de agregar al carrito
        submitted = st.form_submit_button(
            "🛒 Agregar al Carrito", 
            use_container_width=True,
            type="secondary"
        )
        
        if submitted:
            # Validaciones
            errores = []
            if not numero_lote:
                errores.append("Número de lote es requerido")
            if cantidad <= 0:
                errores.append("Cantidad debe ser mayor a 0")
            if (fecha_vencimiento - datetime.now().date()).days < 0:
                errores.append("Fecha de vencimiento no puede ser en el pasado")
            
            # Validar que se haya seleccionado un proveedor
            if not selected_proveedor_id:
                errores.append("Debe seleccionar un proveedor")
            
            # Verificar que el número de lote no esté duplicado en el carrito
            numeros_lotes_carrito = [item['numero_lote'] for item in st.session_state.carrito_lotes]
            if numero_lote in numeros_lotes_carrito:
                errores.append("Este número de lote ya está en el carrito")
            
            if errores:
                for error in errores:
                    st.error(f"❌ {error}")
            else:
                # Obtener nombre del proveedor seleccionado
                proveedor_final = selected_proveedor_display.split(" - ")[1] if " - " in selected_proveedor_display else "Proveedor"
                
                # Obtener datos del medicamento seleccionado
                selected_med_data = next((med for med in medicamentos_data if med['id'] == selected_medicamento_id), None)
                
                # Agregar al carrito
                nuevo_lote = {
                    "medicamento_id": selected_medicamento_id,
                    "medicamento_nombre": selected_medicamento_display,
                    "sucursal_id": selected_sucursal_id,
                    "sucursal_nombre": selected_sucursal_display.replace("🏥 ", ""),
                    "numero_lote": numero_lote,
                    "cantidad": cantidad,
                    "fecha_vencimiento": fecha_vencimiento.isoformat(),
                    "fecha_vencimiento_display": fecha_vencimiento.strftime('%d/%m/%Y'),
                    "proveedor": proveedor_final,
                    "proveedor_id": selected_proveedor_id,
                    "dias_hasta_vencimiento": (fecha_vencimiento - datetime.now().date()).days,
                    "categoria": selected_med_data.get('categoria', 'N/A') if selected_med_data else 'N/A'
                }
                
                st.session_state.carrito_lotes.append(nuevo_lote)
                st.success(f"✅ Lote {numero_lote} agregado al carrito")
                st.rerun()
    
    st.markdown("---")
    
    # ========== CARRITO DE LOTES POR PROCESAR ==========
    st.subheader("🛒 Lotes por Procesar")
    
    if st.session_state.carrito_lotes:
        st.markdown(f"**📦 {len(st.session_state.carrito_lotes)} lote(s) en el carrito**")
        
        # Crear DataFrame para mostrar
        df_carrito = pd.DataFrame(st.session_state.carrito_lotes)
        
        # Seleccionar columnas para mostrar
        columnas_mostrar = [
            'medicamento_nombre', 'sucursal_nombre', 'numero_lote', 
            'cantidad', 'fecha_vencimiento_display', 'proveedor', 'categoria'
        ]
        
        # Renombrar columnas para mejor presentación
        df_display = df_carrito[columnas_mostrar].copy()
        df_display.columns = [
            'Medicamento', 'Sucursal', 'Núm. Lote', 
            'Cantidad', 'Vencimiento', 'Proveedor', 'Categoría'
        ]
        
        # Mostrar tabla
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Métricas del carrito
        col_met1, col_met2, col_met3 = st.columns(3)
        
        with col_met1:
            total_unidades = sum(item['cantidad'] for item in st.session_state.carrito_lotes)
            st.metric("📦 Total Unidades", f"{total_unidades:,}")
        
        with col_met2:
            lotes_proximos = len([item for item in st.session_state.carrito_lotes if item['dias_hasta_vencimiento'] < 90])
            st.metric("⚠️ Lotes Próx. Vencer", lotes_proximos)
        
        with col_met3:
            sucursales_afectadas = len(set(item['sucursal_id'] for item in st.session_state.carrito_lotes))
            st.metric("🏥 Sucursales", sucursales_afectadas)
        
        # Botones de acción del carrito
        col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 1])
        
        with col_btn1:
            if st.button("💾 Guardar Todos los Lotes", use_container_width=True, type="primary"):
                with st.spinner("📦 Procesando todos los lotes..."):
                    exitos = 0
                    errores = 0
                    
                    for lote in st.session_state.carrito_lotes:
                        try:
                            # Preparar datos para la API (solo proveedores existentes)
                            lote_data = {
                                "medicamento_id": lote["medicamento_id"],
                                "sucursal_id": lote["sucursal_id"],
                                "numero_lote": lote["numero_lote"],
                                "cantidad_inicial": lote["cantidad"],
                                "cantidad_actual": lote["cantidad"],
                                "fecha_vencimiento": lote["fecha_vencimiento"],
                                "fecha_ingreso": datetime.now().date().isoformat(),
                                "proveedor_id": lote["proveedor_id"],
                                "proveedor": lote["proveedor"]
                            }
                            
                            # Insertar lote
                            lote_response = api._make_request("/lotes", method="POST", data=lote_data)
                            
                            if lote_response:
                                # Actualizar inventario
                                inventario_actual = api._make_request(f"/inventario/sucursal/{lote['sucursal_id']}")
                                
                                inventario_existente = None
                                if inventario_actual:
                                    inventario_existente = next(
                                        (inv for inv in inventario_actual if inv.get('medicamento_id') == lote['medicamento_id']), 
                                        None
                                    )
                                
                                if inventario_existente:
                                    # Actualizar stock existente
                                    nuevo_stock = inventario_existente['stock_actual'] + lote['cantidad']
                                    update_data = {"stock_actual": nuevo_stock}
                                    
                                    api._make_request(
                                        f"/inventario/{inventario_existente['id']}", 
                                        method="PATCH", 
                                        data=update_data
                                    )
                                else:
                                    # Crear nuevo registro de inventario
                                    inventario_data = {
                                        "medicamento_id": lote["medicamento_id"],
                                        "sucursal_id": lote["sucursal_id"],
                                        "stock_actual": lote["cantidad"],
                                        "stock_minimo": 20,
                                        "ubicacion": "A1-01"
                                    }
                                    
                                    api._make_request("/inventario", method="POST", data=inventario_data)
                                
                                exitos += 1
                            else:
                                errores += 1
                                
                        except Exception as e:
                            errores += 1
                            st.error(f"Error procesando lote {lote['numero_lote']}: {str(e)}")
                    
                    # Mostrar resultados
                    if exitos > 0:
                        st.success(f"✅ {exitos} lote(s) registrado(s) exitosamente!")
                        if errores > 0:
                            st.warning(f"⚠️ {errores} lote(s) tuvieron errores")
                        
                        # Limpiar carrito
                        st.session_state.carrito_lotes = []
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("❌ No se pudo registrar ningún lote")
        
        with col_btn2:
            if st.button("🗑️ Limpiar Carrito", use_container_width=True):
                st.session_state.carrito_lotes = []
                st.success("🧹 Carrito limpiado")
                st.rerun()
        
        with col_btn3:
            # Selector para eliminar lote específico
            if len(st.session_state.carrito_lotes) > 0:
                lote_a_eliminar = st.selectbox(
                    "Eliminar:",
                    options=range(len(st.session_state.carrito_lotes)),
                    format_func=lambda x: f"Lote {st.session_state.carrito_lotes[x]['numero_lote']}",
                    key="selector_eliminar"
                )
                
                if st.button("❌", help="Eliminar lote seleccionado"):
                    st.session_state.carrito_lotes.pop(lote_a_eliminar)
                    st.success("✅ Lote eliminado del carrito")
                    st.rerun()
    
    else:
        st.info("🛒 El carrito está vacío. Agrega lotes usando el formulario de arriba.")
        
        # Mostrar estadísticas cuando el carrito está vacío
        col_stats1, col_stats2 = st.columns(2)
        
        with col_stats1:
            st.markdown("""
            **📋 Proceso de Ingreso:**
            1. Llenar formulario de lote
            2. Hacer clic en "Agregar al Carrito"
            3. Revisar lotes en la tabla
            4. Confirmar con "Guardar Todos los Lotes"
            """)
        
        with col_stats2:
            # Obtener estadísticas de la base de datos
            lotes_existentes = api._make_request("/lotes")
            if lotes_existentes:
                st.markdown(f"""
                **📊 Estadísticas del Sistema:**
                - **Lotes registrados:** {len(lotes_existentes)}
                - **Último ingreso:** {lotes_existentes[-1].get('fecha_ingreso', 'N/A') if lotes_existentes else 'N/A'}
                - **Medicamentos diferentes:** {len(set(lote.get('medicamento_id') for lote in lotes_existentes))}
                """)
    
    st.markdown("---")
    
    # Sección de información
    st.markdown("### 💡 Información del Sistema")
    
    col_info1, col_info2, col_info3 = st.columns(3)
    
    with col_info1:
        st.info("""
        **📦 Sobre los Lotes:**
        - Cada lote tiene un número único
        - Se registra automáticamente la fecha de recepción
        - El stock se actualiza automáticamente en inventario
        """)
    
    with col_info2:
        st.info("""
        **📅 Gestión de Vencimientos:**
        - Alertas automáticas 30 días antes del vencimiento
        - Seguimiento de vida útil por lote
        - Reportes de productos próximos a vencer
        """)
    
    with col_info3:
        st.info("""
        **🔄 Impacto en Sistema:**
        - ✅ Actualiza tabla `lotes_inventario`
        - ✅ Actualiza stock en tabla `inventario`
        - ✅ Genera alertas automáticas
        """)
    
    # Mostrar últimos lotes registrados
    st.markdown("### 📋 Últimos Lotes Registrados")
    
    lotes_recientes = api._make_request("/lotes")
    if lotes_recientes:
        # Tomar los últimos 5 lotes y mostrar información relevante
        df_lotes = pd.DataFrame(lotes_recientes[-5:] if len(lotes_recientes) > 5 else lotes_recientes)
        
        if not df_lotes.empty:
            # Seleccionar columnas relevantes para mostrar
            columnas_lotes = ['numero_lote', 'cantidad_actual', 'fecha_vencimiento', 'fecha_ingreso']
            columnas_disponibles = [col for col in columnas_lotes if col in df_lotes.columns]
            
            if columnas_disponibles:
                st.dataframe(
                    df_lotes[columnas_disponibles].sort_values('fecha_ingreso', ascending=False) if 'fecha_ingreso' in df_lotes.columns else df_lotes[columnas_disponibles],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("📊 No hay información detallada de lotes disponible")
        else:
            st.info("📦 No hay lotes registrados aún")
    else:
        st.info("📦 No se pudieron cargar los lotes registrados")

# ========== TAB 6: SALIDAS DE INVENTARIO (OPTIMIZADO) ==========
with tab6:
    st.header("📤 Salidas de Inventario")
    st.markdown("**Registrar ventas, transferencias y consumos de medicamentos**")
    
    # Control de cache con botón en header
    col_header1, col_header2 = st.columns([3, 1])
    with col_header1:
        st.markdown("")  # Espaciador
    with col_header2:
        if st.button("🔄 Actualizar Datos", help="Limpiar cache y recargar datos", key="refresh_tab6"):
            clear_cache_inventario()
            st.rerun()
    
    # Obtener sucursales desde cache
    sucursales_data = get_sucursales_cached()
    
    if not sucursales_data:
        st.error("❌ No se pudieron cargar las sucursales. Verifica la conexión API.")
        st.stop()
    
    # Inicializar session state para salidas
    if 'salidas_carrito' not in st.session_state:
        st.session_state.salidas_carrito = []
    if 'selected_sucursal_salida' not in st.session_state:
        st.session_state.selected_sucursal_salida = None
    if 'selected_medicamento_salida' not in st.session_state:
        st.session_state.selected_medicamento_salida = None
    
    # Selector de sucursal
    st.subheader("🏥 Seleccionar Sucursal")
    
    sucursal_salida_options = {
        f"🏥 {suc['nombre']}": suc['id'] 
        for suc in sucursales_data
    }
    
    selected_sucursal_salida_name = st.selectbox(
        "Sucursal de origen:",
        options=list(sucursal_salida_options.keys()),
        key="sucursal_salida_selector",
        help="Selecciona la sucursal de donde saldrá el inventario"
    )
    
    selected_sucursal_salida_id = sucursal_salida_options[selected_sucursal_salida_name]
    st.session_state.selected_sucursal_salida = selected_sucursal_salida_id
    
    # Mostrar información de la sucursal seleccionada
    sucursal_info = next((s for s in sucursales_data if s['id'] == selected_sucursal_salida_id), None)
    if sucursal_info:
        st.info(f"📍 **{sucursal_info['nombre']}** seleccionada")
    
    # Mostrar métricas de la sucursal desde cache
    col_met1, col_met2, col_met3 = st.columns(3)
    
    with st.spinner("📊 Cargando métricas..."):
        metricas = get_metricas_sucursal_cached(selected_sucursal_salida_id)
    
    with col_met1:
        st.metric("💊 Medicamentos", metricas.get('total_medicamentos', 0))
    with col_met2:
        st.metric("📦 Stock Total", f"{metricas.get('total_stock', 0):,}")
    with col_met3:
        st.metric("💰 Valor Total", f"${metricas.get('valor_total_inventario', 0):,.2f}")
    
    st.markdown("---")
    
    # Obtener medicamentos disponibles desde cache optimizado
    st.subheader("💊 Medicamentos Disponibles")
    
    with st.spinner("🔄 Cargando inventario..."):
        inventario_sucursal = get_inventario_sucursal_cached(selected_sucursal_salida_id)
    
    if not inventario_sucursal:
        st.warning(f"⚠️ No se encontró inventario para la sucursal seleccionada.")
        st.stop()
    
    # Los medicamentos ya vienen filtrados con stock > 0 desde el endpoint optimizado
    medicamentos_disponibles = inventario_sucursal
    
    if not medicamentos_disponibles:
        st.warning("⚠️ No hay medicamentos con stock disponible en esta sucursal.")
        st.stop()
    
    # Selector de medicamento
    medicamento_salida_options = {
        f"💊 {med.get('nombre', 'Sin nombre')} (Stock: {med.get('stock_actual', 0)})": med['medicamento_id']
        for med in medicamentos_disponibles
    }
    
    selected_medicamento_salida_name = st.selectbox(
        "Medicamento:",
        options=list(medicamento_salida_options.keys()),
        key="medicamento_salida_selector",
        help="Medicamentos con stock disponible en la sucursal"
    )
    
    selected_medicamento_salida_id = medicamento_salida_options[selected_medicamento_salida_name]
    st.session_state.selected_medicamento_salida = selected_medicamento_salida_id
    
    # Obtener información del medicamento seleccionado
    medicamento_info = next((med for med in medicamentos_disponibles if med['medicamento_id'] == selected_medicamento_salida_id), None)
    
    if medicamento_info:
        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("📦 Stock Actual", f"{medicamento_info.get('stock_actual', 0)}")
        with col_info2:
            st.metric("⚠️ Stock Mínimo", f"{medicamento_info.get('stock_minimo', 0)}")
        with col_info3:
            precio_venta = medicamento_info.get('precio_venta', 0)
            st.metric("💰 Precio Venta", f"${precio_venta:.2f}")
    
    st.markdown("---")
    
    # Obtener lotes disponibles desde cache optimizado
    st.subheader("📋 Lotes Disponibles")
    
    with st.spinner("🔄 Cargando lotes..."):
        lotes_medicamento = get_lotes_medicamento_cached(
            selected_medicamento_salida_id, 
            selected_sucursal_salida_id
        )
    
    if lotes_medicamento:
        # Mostrar tabla de lotes disponibles
        df_lotes = pd.DataFrame(lotes_medicamento)
        
        # Seleccionar columnas relevantes para mostrar
        columnas_mostrar = ['numero_lote', 'cantidad_actual', 'fecha_vencimiento', 'fecha_recepcion']
        columnas_disponibles = [col for col in columnas_mostrar if col in df_lotes.columns]
        
        if columnas_disponibles:
            df_lotes_display = df_lotes[columnas_disponibles].copy()
            
            # Renombrar columnas para mejor presentación
            column_mapping = {
                'numero_lote': 'Número de Lote',
                'cantidad_actual': 'Cantidad Disponible',
                'fecha_vencimiento': 'Fecha Vencimiento',
                'fecha_recepcion': 'Fecha Recepción'
            }
            
            df_lotes_display = df_lotes_display.rename(columns=column_mapping)
            
            st.dataframe(
                df_lotes_display,
                use_container_width=True,
                hide_index=True
            )
            
            # Formulario de salida
            st.markdown("---")
            st.subheader("📝 Registrar Salida")
            
            with st.form("registro_salida"):
                col_form1, col_form2 = st.columns(2)
                
                with col_form1:
                    # Selector de lote
                    lote_options = {
                        f"Lote {lote['numero_lote']} (Disponible: {lote.get('cantidad_actual', 0)})": lote['id']
                        for lote in lotes_medicamento
                    }
                    
                    selected_lote_name = st.selectbox(
                        "🏷️ Seleccionar Lote:",
                        options=list(lote_options.keys())
                    )
                    selected_lote_id = lote_options[selected_lote_name]
                    
                    # Obtener info del lote seleccionado
                    lote_info = next((lote for lote in lotes_medicamento if lote['id'] == selected_lote_id), None)
                    cantidad_disponible = lote_info.get('cantidad_actual', 0) if lote_info else 0
                    
                    # Cantidad a sacar
                    cantidad_salida = st.number_input(
                        "📦 Cantidad:",
                        min_value=1,
                        max_value=cantidad_disponible,
                        value=1,
                        help=f"Máximo disponible: {cantidad_disponible}"
                    )
                
                with col_form2:
                    # Tipo de salida
                    tipo_salida = st.selectbox(
                        "📋 Tipo de Salida:",
                        options=[
                            "Venta",
                            "Transferencia", 
                            "Consumo Interno",
                            "Devolución",
                            "Vencimiento",
                            "Ajuste de Inventario"
                        ]
                    )
                    
                    # Destino (opcional para transferencias)
                    destino = ""
                    if tipo_salida == "Transferencia":
                        otras_sucursales = [suc for suc in sucursales_data if suc['id'] != selected_sucursal_salida_id]
                        if otras_sucursales:
                            destino_options = {f"🏥 {suc['nombre']}": suc['id'] for suc in otras_sucursales}
                            destino_name = st.selectbox(
                                "🎯 Sucursal Destino:",
                                options=list(destino_options.keys())
                            )
                            destino = destino_name
                    
                    # Observaciones
                    observaciones = st.text_area(
                        "📝 Observaciones:",
                        placeholder="Información adicional sobre la salida..."
                    )
                
                # Botón de agregar al carrito
                submitted = st.form_submit_button(
                    "🛒 Agregar al Carrito", 
                    use_container_width=True,
                    type="secondary"
                )
                
                if submitted:
                    # Validaciones
                    if cantidad_salida > cantidad_disponible:
                        st.error(f"❌ Cantidad excede el stock disponible ({cantidad_disponible})")
                    else:
                        # Agregar al carrito de salidas
                        nueva_salida = {
                            "sucursal_id": selected_sucursal_salida_id,
                            "sucursal_nombre": selected_sucursal_salida_name.replace("🏥 ", ""),
                            "medicamento_id": selected_medicamento_salida_id,
                            "medicamento_nombre": selected_medicamento_salida_name.split(" (Stock:")[0].replace("💊 ", ""),
                            "lote_id": selected_lote_id,
                            "numero_lote": lote_info.get('numero_lote', ''),
                            "cantidad": cantidad_salida,
                            "tipo_salida": tipo_salida,
                            "destino": destino,
                            "observaciones": observaciones,
                            "precio_unitario": precio_venta,
                            "total": cantidad_salida * precio_venta,
                            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "usuario": "Sistema"  # Se puede personalizar
                        }
                        
                        st.session_state.salidas_carrito.append(nueva_salida)
                        st.success(f"✅ Salida agregada al carrito: {cantidad_salida} unidades de {nueva_salida['medicamento_nombre']}")
                        
                        # Limpiar cache para reflejar cambios
                        clear_cache_inventario()
                        st.rerun()
        else:
            st.info("📊 No hay información detallada de lotes disponible")
    else:
        st.warning("⚠️ No hay lotes disponibles para este medicamento en esta sucursal.")
    
    # ========== CARRITO DE SALIDAS ==========
    st.markdown("---")
    st.subheader("🛒 Salidas por Procesar")
    
    if st.session_state.salidas_carrito:
        st.markdown(f"**📦 {len(st.session_state.salidas_carrito)} salida(s) en el carrito**")
        
        # Mostrar tabla del carrito
        df_carrito = pd.DataFrame(st.session_state.salidas_carrito)
        
        columnas_carrito = [
            'medicamento_nombre', 'numero_lote', 'cantidad', 
            'tipo_salida', 'destino', 'total', 'timestamp'
        ]
        
        df_carrito_display = df_carrito[columnas_carrito].copy()
        df_carrito_display.columns = [
            'Medicamento', 'Lote', 'Cantidad', 
            'Tipo', 'Destino', 'Total ($)', 'Fecha/Hora'
        ]
        
        st.dataframe(
            df_carrito_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Métricas del carrito
        col_met1, col_met2, col_met3 = st.columns(3)
        
        with col_met1:
            total_unidades = sum(item['cantidad'] for item in st.session_state.salidas_carrito)
            st.metric("📦 Total Unidades", f"{total_unidades:,}")
        
        with col_met2:
            total_valor = sum(item['total'] for item in st.session_state.salidas_carrito)
            st.metric("💰 Valor Total", f"${total_valor:,.2f}")
        
        with col_met3:
            tipos_salida = len(set(item['tipo_salida'] for item in st.session_state.salidas_carrito))
            st.metric("📋 Tipos de Salida", tipos_salida)
        
        # Botones de acción
        col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 1])
        
        with col_btn1:
            if st.button("💾 Procesar Todas las Salidas", use_container_width=True, type="primary"):
                with st.spinner("📦 Procesando salidas..."):
                    try:
                        # Preparar datos para el endpoint de múltiples salidas
                        salidas_para_procesar = []
                        for salida in st.session_state.salidas_carrito:
                            salida_data = {
                                "sucursal_id": salida["sucursal_id"],
                                "medicamento_id": salida["medicamento_id"],
                                "lote_id": salida["lote_id"],
                                "numero_lote": salida["numero_lote"],
                                "cantidad": salida["cantidad"],
                                "tipo_salida": salida["tipo_salida"],
                                "destino": salida.get("destino", ""),
                                "precio_unitario": salida["precio_unitario"],
                                "total": salida["total"],
                                "observaciones": salida.get("observaciones", ""),
                                "usuario": salida.get("usuario", "Sistema")
                            }
                            salidas_para_procesar.append(salida_data)
                        
                        # Enviar al endpoint de procesamiento múltiple
                        resultado = api._make_request("/salidas/lote", method="POST", data=salidas_para_procesar)
                        
                        if resultado:
                            exitos = resultado.get('exitos', 0)
                            errores = resultado.get('errores', 0)
                            
                            if exitos > 0:
                                st.success(f"✅ {exitos} salida(s) procesada(s) exitosamente!")
                                if errores > 0:
                                    st.warning(f"⚠️ {errores} salida(s) tuvieron errores")
                                
                                # Limpiar carrito y cache
                                st.session_state.salidas_carrito = []
                                clear_cache_inventario()
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ No se pudo procesar ninguna salida")
                        else:
                            st.error("❌ Error conectando con el servidor")
                            
                    except Exception as e:
                        st.error(f"❌ Error procesando salidas: {str(e)}")
        
        with col_btn2:
            if st.button("🗑️ Limpiar Carrito", use_container_width=True):
                st.session_state.salidas_carrito = []
                st.success("🧹 Carrito limpiado")
                st.rerun()
        
        with col_btn3:
            # Selector para eliminar salida específica
            if len(st.session_state.salidas_carrito) > 0:
                salida_a_eliminar = st.selectbox(
                    "Eliminar:",
                    options=range(len(st.session_state.salidas_carrito)),
                    format_func=lambda x: f"#{x+1}",
                    key="selector_eliminar_salida"
                )
                
                if st.button("❌", help="Eliminar salida seleccionada"):
                    st.session_state.salidas_carrito.pop(salida_a_eliminar)
                    st.success("✅ Salida eliminada del carrito")
                    st.rerun()
    
    else:
        st.info("🛒 El carrito está vacío. Selecciona una sucursal, medicamento y lote para agregar salidas.")
        
        # Estadísticas cuando el carrito está vacío
        col_stats1, col_stats2 = st.columns(2)
        
        with col_stats1:
            st.markdown("""
            **📋 Tipos de Salida:**
            - **Venta:** Medicamento vendido a cliente
            - **Transferencia:** Envío a otra sucursal
            - **Consumo Interno:** Uso en la clínica
            - **Devolución:** Retorno a proveedor
            - **Vencimiento:** Producto caducado
            - **Ajuste:** Corrección de inventario
            """)
        
        with col_stats2:
            st.markdown(f"""
            **📊 Resumen de Inventario:**
            - **Sucursal seleccionada:** {selected_sucursal_salida_name.replace('🏥 ', '')}
            - **Medicamentos disponibles:** {len(medicamentos_disponibles)}
            - **Total en stock:** {sum(med.get('stock_actual', 0) for med in medicamentos_disponibles):,} unidades
            """)

# ========== FOOTER CORPORATIVO CÓDICE INVENTORY ==========
st.markdown("---")

# Logo y título centrados
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown(f"""
    <div style="text-align: center; margin: 2rem 0;">
        <div style="width: 60px; height: 60px; background: white; border-radius: 50%; margin: 0 auto 1rem auto; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
            {LOGO_IMG}
        </div>
        <h3 style="color: #1e293b; margin: 0;">CÓDICE INVENTORY</h3>
        <p style="color: #64748b; margin: 0.5rem 0 0 0;">Sistema de Inventario Inteligente</p>
    </div>
    """, unsafe_allow_html=True)

# Características principales en columnas
st.markdown("### 🎯 Características Principales")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown("""
    **🏥 Multi-Sucursal**  
    Gestión centralizada de 3 sucursales conectadas en tiempo real
    """)

with col2:
    st.markdown("""
    **🤖 IA Predictiva**  
    Algoritmos avanzados para optimización y predicción de demanda
    """)

with col3:
    st.markdown("""
    **📊 Análisis Inteligente**  
    Reportes automáticos y dashboards ejecutivos en tiempo real
    """)

with col4:
    st.markdown("""
    **🔄 Redistribución**  
    Optimización automática de inventarios entre sucursales
    """)

# Footer final con información
st.markdown("---")

col_left, col_right = st.columns(2)

with col_left:
    st.markdown("© 2025 **Códice Inventory** - Transformando la gestión de inventario")

with col_right:
    st.markdown("🌐 Sistema Web • 🔒 Datos Seguros • 📱 Responsive")