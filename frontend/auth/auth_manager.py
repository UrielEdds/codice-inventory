import streamlit as st
import requests
import json
from typing import Optional, Dict
from datetime import datetime, timedelta
import base64

class AuthManager:
    def __init__(self, backend_url: str, api_secret: str):
        self.backend_url = backend_url
        self.api_secret = api_secret
        self.headers = {
            "Authorization": f"Bearer {api_secret}",
            "Content-Type": "application/json"
        }
    
    def login(self, email: str, password: str, remember_me: bool = False) -> Dict:
        """Iniciar sesión con opción de recordar"""
        try:
            response = requests.post(
                f"{self.backend_url}/auth/login",
                json={"email": email, "password": password},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Guardar en session state
                st.session_state.authenticated = True
                st.session_state.access_token = data["access_token"]
                st.session_state.user = data["user"]
                st.session_state.login_time = datetime.now()
                st.session_state.remember_me = remember_me
                
                # Si remember_me está activo, guardar en localStorage
                if remember_me:
                    self._save_persistent_session(data["access_token"], data["user"])
                
                return {"success": True, "user": data["user"]}
            else:
                error_detail = response.json().get("detail", "Error de autenticación")
                return {"success": False, "error": error_detail}
                
        except Exception as e:
            return {"success": False, "error": f"Error de conexión: {str(e)}"}
    
    def _save_persistent_session(self, token: str, user: Dict):
        """Guardar sesión persistente usando JavaScript/localStorage"""
        session_data = {
            "token": token,
            "user": user,
            "timestamp": datetime.now().isoformat()
        }
        
        # Inyectar JavaScript para guardar en localStorage
        st.markdown(f"""
        <script>
            localStorage.setItem('codice_session', JSON.stringify({json.dumps(session_data)}));
        </script>
        """, unsafe_allow_html=True)
    
    def check_persistent_session(self) -> bool:
        """Verificar si hay una sesión persistente guardada"""
        # Inyectar JavaScript para leer localStorage
        st.markdown("""
        <script>
            const session = localStorage.getItem('codice_session');
            if (session) {
                const sessionData = JSON.parse(session);
                const timestamp = new Date(sessionData.timestamp);
                const now = new Date();
                const hoursDiff = (now - timestamp) / (1000 * 60 * 60);
                
                // Si la sesión tiene menos de 24 horas
                if (hoursDiff < 24) {
                    // Comunicar con Streamlit usando query params
                    const params = new URLSearchParams(window.location.search);
                    if (!params.has('restore_session')) {
                        params.set('restore_session', 'true');
                        params.set('session_data', btoa(session));
                        window.location.search = params.toString();
                    }
                } else {
                    localStorage.removeItem('codice_session');
                }
            }
        </script>
        """, unsafe_allow_html=True)
        
        # Verificar query params para restaurar sesión
        query_params = st.query_params
        if query_params.get("restore_session") == "true":
            try:
                session_data_b64 = query_params.get("session_data", "")
                if session_data_b64:
                    session_data = json.loads(base64.b64decode(session_data_b64))
                    
                    # Restaurar sesión
                    st.session_state.authenticated = True
                    st.session_state.access_token = session_data["token"]
                    st.session_state.user = session_data["user"]
                    st.session_state.login_time = datetime.fromisoformat(session_data["timestamp"])
                    st.session_state.remember_me = True
                    
                    # Limpiar query params
                    st.query_params.clear()
                    return True
            except Exception as e:
                print(f"Error restaurando sesión: {e}")
        
        return False
    
    def clear_persistent_session(self):
        """Limpiar sesión persistente"""
        st.markdown("""
        <script>
            localStorage.removeItem('codice_session');
        </script>
        """, unsafe_allow_html=True)
    
    def logout(self):
        """Cerrar sesión"""
        # Limpiar localStorage si estaba activo remember_me
        if st.session_state.get("remember_me", False):
            self.clear_persistent_session()
        
        # Limpiar session state
        keys_to_clear = [
            "authenticated", "access_token", "user", "login_time",
            "user_permissions", "user_role", "remember_me"
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def is_authenticated(self) -> bool:
        """Verificar si el usuario está autenticado"""
        # Primero verificar si hay sesión persistente
        if not st.session_state.get("authenticated", False):
            # Intentar restaurar sesión persistente
            if self.check_persistent_session():
                return True
            return False
        
        # Verificar que el token no haya expirado (8 horas o 24 si remember_me)
        login_time = st.session_state.get("login_time")
        if login_time:
            max_hours = 24 if st.session_state.get("remember_me", False) else 8
            if datetime.now() - login_time > timedelta(hours=max_hours):
                self.logout()
                return False
        
        return True
    
    def get_current_user(self) -> Optional[Dict]:
        """Obtener usuario actual"""
        if self.is_authenticated():
            return st.session_state.get("user")
        return None
    
    def get_user_role(self) -> str:
        """Obtener rol del usuario actual"""
        user = self.get_current_user()
        return user.get("rol", "") if user else ""
    
    def get_user_permissions(self) -> list:
        """Obtener permisos del usuario basados en su rol"""
        from .permissions import get_permissions_by_role
        role = self.get_user_role()
        return get_permissions_by_role(role)
    
    def check_permission(self, permission: str) -> bool:
        """Verificar si el usuario tiene un permiso específico"""
        permissions = self.get_user_permissions()
        return permission in permissions or "admin.full" in permissions
    
    def require_permission(self, permission: str) -> bool:
        """Verificar permiso y mostrar error si no lo tiene"""
        if not self.is_authenticated():
            st.error("🔒 Debes iniciar sesión para acceder")
            return False
        
        if not self.check_permission(permission):
            st.error(f"🚫 No tienes permisos para: {permission}")
            return False
        
        return True
    
    def get_auth_headers(self) -> Dict:
        """Obtener headers de autenticación para requests"""
        token = st.session_state.get("access_token")
        if token:
            return {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        return {"Content-Type": "application/json"}

# Instancia global
def get_auth_manager():
    """Obtener instancia del gestor de autenticación"""
    import os
    backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
    api_secret = os.getenv("API_SECRET", "mi-token-api-autenticacion-seguro")
    
    if "auth_manager" not in st.session_state:
        st.session_state.auth_manager = AuthManager(backend_url, api_secret)
    
    return st.session_state.auth_manager