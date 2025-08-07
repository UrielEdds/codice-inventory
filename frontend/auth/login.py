import streamlit as st
import base64
import os
from .auth_manager import get_auth_manager
from .permissions import get_role_description, get_role_color

# ========== FUNCIÓN GLOBAL PARA LOGO ==========
@st.cache_data
def get_logo_base64():
    """Cargar logo como base64 para embedding"""
    try:
        # Probar múltiples rutas posibles
        possible_paths = [
            'assets/logo_codice.png',
            'frontend/assets/logo_codice.png',
            './assets/logo_codice.png',
            os.path.join(os.path.dirname(__file__), '..', 'assets', 'logo_codice.png'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'assets', 'logo_codice.png')
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
    LOGO_HEADER_IMG = f'<img src="data:image/png;base64,{logo_b64}" style="height: 80px; width: auto;">'
else:
    # Logo no encontrado - usar emoji
    LOGO_HEADER_IMG = '<span style="font-size: 4rem;">🏥</span>'

print(f"📷 Logo status en login: {'✅ Loaded' if logo_b64 else '❌ Using emoji fallback'}")

def show_login_page():
    """Mostrar página de login"""
    auth_manager = get_auth_manager()
    
    # Header de la aplicación con logo real
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border-radius: 16px; margin-bottom: 2rem; box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);">
        <div style="margin-bottom: 1rem;">
            {LOGO_HEADER_IMG}
        </div>
        <h1 style="color: #1e293b; font-size: 2.5rem; font-weight: 700; margin: 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            CÓDICE INVENTORY
        </h1>
        <p style="color: #64748b; font-size: 1.1rem; margin: 0.5rem 0 0 0; font-weight: 500;">
            Sistema de Inventario Inteligente
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Formulario de login con estilo mejorado
    st.markdown("""
    <style>
        .login-form {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(37, 99, 235, 0.1);
            margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="login-form">', unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### 🔐 Iniciar Sesión")
            
            col_login1, col_login2 = st.columns(2)
            
            with col_login1:
                email = st.text_input(
                    "📧 Email",
                    placeholder="usuario@codice.com",
                    value="admin@codice.com"
                )
            
            with col_login2:
                password = st.text_input(
                    "🔒 Contraseña",
                    type="password",
                    placeholder="Ingresa tu contraseña",
                    value="admin123"
                )
            
            remember_me = st.checkbox("🔄 Recordar sesión")
            
            submitted = st.form_submit_button(
                "🚀 Iniciar Sesión", 
                use_container_width=True,
                type="primary"
            )
            
            if submitted:
                if not email or not password:
                    st.error("❌ Por favor completa todos los campos")
                else:
                    with st.spinner("🔄 Autenticando..."):
                        result = auth_manager.login(email, password, remember_me)
                    
                    if result["success"]:
                        st.success(f"✅ ¡Bienvenido {result['user']['nombre']}!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ {result['error']}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Usuarios de demostración con estilo
    st.markdown("""
    <div style="background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%); padding: 1.5rem; border-radius: 12px; border-left: 4px solid #2563eb;">
        <h4 style="margin: 0 0 1rem 0; color: #1e293b;">👥 Usuarios de Demostración</h4>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **👑 Admin:** admin@codice.com / admin123  
        **🏢 Gerente:** gerente1@codice.com / gerente123
        """)
    
    with col2:
        st.markdown("""
        **⚕️ Farmacéutico:** farmaceutico1@codice.com / farmaceutico123  
        **👤 Empleado:** empleado1@codice.com / empleado123
        """)
    
    st.info("💡 Puedes usar cualquiera de estos usuarios para probar el sistema")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #64748b; font-size: 0.8rem;">
        © 2025 Códice Inventory • Sistema Seguro de Autenticación
    </div>
    """, unsafe_allow_html=True)

def show_user_info():
    """Mostrar información del usuario en el sidebar"""
    auth_manager = get_auth_manager()
    user = auth_manager.get_current_user()
    
    if user:
        role_color = get_role_color(user["rol"])
        role_desc = get_role_description(user["rol"])
        
        # Logo pequeño para sidebar
        logo_sidebar = f'<img src="data:image/png;base64,{logo_b64}" style="height: 30px; width: auto;">' if logo_b64 else '👤'
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {role_color} 0%, #1e293b 100%); 
                    padding: 1rem; border-radius: 12px; margin-bottom: 1rem; color: white;">
            <div style="text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">{logo_sidebar}</div>
                <div style="font-weight: 700;">{user['nombre']} {user['apellido']}</div>
                <div style="font-size: 0.8rem; opacity: 0.9;">{role_desc}</div>
                <div style="font-size: 0.7rem; opacity: 0.7; margin-top: 0.5rem;">
                    {user['email']}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón de logout
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            auth_manager.logout()
            st.rerun()

def require_auth():
    """Decorator para requerir autenticación"""
    auth_manager = get_auth_manager()
    
    if not auth_manager.is_authenticated():
        show_login_page()
        st.stop()
    
    return auth_manager.get_current_user()