# frontend/utils/api_client.py
import requests
import streamlit as st
from typing import List, Dict, Optional
import pandas as pd

class FarmaciaAPIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Optional[Dict]:
        """Método base para hacer peticiones HTTP"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            if method == "GET":
                response = requests.get(url, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=10)
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            st.error("❌ No se puede conectar con la API. ¿Está corriendo el servidor FastAPI?")
            return None
        except requests.exceptions.Timeout:
            st.error("⏱️ Timeout conectando con la API")
            return None
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ Error HTTP {e.response.status_code}: {e.response.text}")
            return None
        except Exception as e:
            st.error(f"❌ Error inesperado: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """Probar conexión con la API"""
        result = self._make_request("/")
        return result is not None
    
    # ========== MÉTODOS BÁSICOS (COMPATIBILIDAD) ==========
    
    def get_medicamentos(self) -> List[Dict]:
        """Obtener catálogo completo de medicamentos"""
        result = self._make_request("/medicamentos")
        return result if result else []
    
    def get_inventario(self) -> List[Dict]:
        """Obtener inventario consolidado de todas las sucursales"""
        result = self._make_request("/inventario")
        return result if result else []
    
    def get_alertas(self) -> Dict:
        """Obtener alertas consolidadas de todas las sucursales"""
        result = self._make_request("/alertas")
        return result if result else {
            "alertas_vencimiento": [],
            "alertas_stock_bajo": [],
            "alertas_vencidos": [],
            "total_alertas": 0
        }
    
    def get_dashboard_stats(self) -> Dict:
        """Obtener estadísticas consolidadas del dashboard"""
        result = self._make_request("/dashboard/stats")
        return result if result else {
            "total_medicamentos": 0,
            "stock_bajo": 0,
            "por_vencer": 0,
            "vencidos": 0,
            "valor_total_inventario": 0.0
        }
    
    def create_medicamento(self, medicamento_data: Dict) -> Optional[Dict]:
        """Crear nuevo medicamento en el catálogo"""
        return self._make_request("/medicamentos", method="POST", data=medicamento_data)
    
    # ========== MÉTODOS PARA SUCURSALES ==========
    
    def get_sucursales(self) -> List[Dict]:
        """Obtener todas las sucursales"""
        result = self._make_request("/sucursales")
        return result if result else []
    
    def get_inventario_sucursal(self, sucursal_id: int) -> List[Dict]:
        """Obtener inventario de una sucursal específica"""
        result = self._make_request(f"/inventario/sucursal/{sucursal_id}")
        return result if result else []
    
    def get_dashboard_stats_sucursal(self, sucursal_id: int) -> Dict:
        """Obtener estadísticas de una sucursal específica"""
        result = self._make_request(f"/dashboard/stats/sucursal/{sucursal_id}")
        return result if result else {
            "total_medicamentos": 0,
            "stock_bajo": 0,
            "por_vencer": 0,
            "vencidos": 0,
            "valor_total_inventario": 0.0
        }
    
    def get_alertas_sucursal(self, sucursal_id: int) -> Dict:
        """Obtener alertas de una sucursal específica"""
        result = self._make_request(f"/alertas/sucursal/{sucursal_id}")
        return result if result else {
            "alertas_vencimiento": [],
            "alertas_stock_bajo": [],
            "alertas_vencidos": [],
            "total_alertas": 0
        }
    
    # ========== MÉTODOS PARA CONSOLIDACIÓN MULTI-SUCURSAL ==========
    
    def get_stats_todas_sucursales(self) -> Dict:
        """Obtener estadísticas consolidadas con estructura normalizada"""
        result = self._make_request("/dashboard/stats")
        return result if result else {
            "total_medicamentos": 0,
            "stock_bajo": 0,
            "por_vencer": 0,
            "vencidos": 0,
            "valor_total_inventario": 0.0
        }
    
    def get_inventario_todas_sucursales(self) -> List[Dict]:
        """Obtener inventario consolidado de todas las sucursales"""
        result = self._make_request("/inventario")
        return result if result else []
    
    def get_alertas_todas_sucursales(self) -> Dict:
        """Obtener alertas consolidadas de todas las sucursales"""
        result = self._make_request("/alertas")
        return result if result else {
            "alertas_vencimiento": [],
            "alertas_stock_bajo": [],
            "alertas_vencidos": [],
            "total_alertas": 0
        }
    
    def get_comparativo_sucursales(self) -> List[Dict]:
        """Obtener datos comparativos de todas las sucursales"""
        result = self._make_request("/dashboard/comparativo")
        return result if result else []
    
    # ========== MÉTODOS ESPECÍFICOS PARA NUEVA ESTRUCTURA ==========
    
    def get_inventario_por_medicamento(self, medicamento_id: int) -> List[Dict]:
        """Obtener inventario de un medicamento en todas las sucursales"""
        result = self._make_request(f"/inventario/medicamento/{medicamento_id}")
        return result if result else []
    
    def get_resumen_catalogo(self) -> Dict:
        """Obtener resumen del catálogo de medicamentos"""
        result = self._make_request("/catalogo/resumen")
        return result if result else {
            "total_skus": 0,
            "skus_con_inventario": 0,
            "detalle_por_sku": []
        }
    
    # ========== MÉTODOS PARA ANÁLISIS ==========
    
    def get_medicamentos_por_categoria(self) -> Dict:
        """Agrupar medicamentos por categoría"""
        medicamentos = self.get_medicamentos()
        categorias = {}
        
        for med in medicamentos:
            cat = med.get("categoria", "Sin categoría")
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(med)
        
        return categorias
    
    def get_top_medicamentos_por_valor(self, limit: int = 10) -> List[Dict]:
        """Obtener top medicamentos por valor de inventario"""
        inventario = self.get_inventario_todas_sucursales()
        
        # Calcular valor por medicamento
        medicamentos_valor = {}
        for item in inventario:
            sku = item.get("sku")
            if sku:
                if sku not in medicamentos_valor:
                    medicamentos_valor[sku] = {
                        "sku": sku,
                        "nombre": item.get("nombre"),
                        "stock_total": 0,
                        "valor_total": 0,
                        "sucursales": []
                    }
                
                stock = item.get("stock_actual", 0)
                precio = item.get("precio_venta", 0)
                medicamentos_valor[sku]["stock_total"] += stock
                medicamentos_valor[sku]["valor_total"] += stock * precio
                medicamentos_valor[sku]["sucursales"].append({
                    "sucursal": item.get("sucursal_nombre"),
                    "stock": stock
                })
        
        # Ordenar por valor y retornar top N
        top_medicamentos = sorted(
            medicamentos_valor.values(), 
            key=lambda x: x["valor_total"], 
            reverse=True
        )
        
        return top_medicamentos[:limit]
    
    def get_alertas_criticas_consolidadas(self) -> Dict:
        """Obtener resumen de alertas críticas con priorización"""
        alertas = self.get_alertas_todas_sucursales()
        
        # Priorizar alertas
        alertas_criticas = []
        
        # Vencidos (prioridad máxima)
        for alerta in alertas.get("alertas_vencidos", []):
            alertas_criticas.append({
                **alerta,
                "prioridad": "CRÍTICA",
                "tipo_alerta": "VENCIDO"
            })
        
        # Por vencer en menos de 15 días (alta prioridad)
        for alerta in alertas.get("alertas_vencimiento", []):
            alertas_criticas.append({
                **alerta,
                "prioridad": "ALTA",
                "tipo_alerta": "POR_VENCER"
            })
        
        # Stock crítico (stock <= 50% del mínimo)
        for alerta in alertas.get("alertas_stock_bajo", []):
            stock_actual = alerta.get("stock_actual", 0)
            stock_minimo = alerta.get("stock_minimo", 1)
            
            if stock_actual <= (stock_minimo * 0.5):
                prioridad = "CRÍTICA"
            else:
                prioridad = "MEDIA"
            
            alertas_criticas.append({
                **alerta,
                "prioridad": prioridad,
                "tipo_alerta": "STOCK_BAJO"
            })
        
        # Ordenar por prioridad
        orden_prioridad = {"CRÍTICA": 3, "ALTA": 2, "MEDIA": 1}
        alertas_criticas.sort(
            key=lambda x: orden_prioridad.get(x["prioridad"], 0), 
            reverse=True
        )
        
        return {
            "alertas_criticas": alertas_criticas,
            "total_criticas": len([a for a in alertas_criticas if a["prioridad"] == "CRÍTICA"]),
            "total_altas": len([a for a in alertas_criticas if a["prioridad"] == "ALTA"]),
            "total_medias": len([a for a in alertas_criticas if a["prioridad"] == "MEDIA"]),
            "total_alertas": len(alertas_criticas)
        }
    
# ========== MÉTODOS PARA INGRESO DE INVENTARIO ==========
    
    def get_productos_disponibles(self) -> List[Dict]:
        """Obtener productos disponibles para ingreso"""
        result = self._make_request("/productos/disponibles")
        return result if result else []
    
    def crear_ingreso_inventario(self, ingreso_data: Dict) -> Optional[Dict]:
        """Crear nuevo ingreso de inventario"""
        return self._make_request("/inventario/ingreso", method="POST", data=ingreso_data)
    
    def get_historial_movimientos(self, sucursal_id: int) -> List[Dict]:
        """Obtener historial de movimientos de inventario"""
        result = self._make_request(f"/inventario/movimientos/sucursal/{sucursal_id}")
        return result if result else []
    
    def get_lotes_por_sucursal(self, sucursal_id: int) -> List[Dict]:
        """Obtener lotes de inventario por sucursal"""
        result = self._make_request(f"/inventario/lotes/sucursal/{sucursal_id}")
        return result if result else []


    # ========== MÉTODOS PARA DATAFRAMES ==========
    
    def get_inventario_df(self) -> pd.DataFrame:
        """Obtener inventario consolidado como DataFrame"""
        data = self.get_inventario_todas_sucursales()
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    def get_medicamentos_df(self) -> pd.DataFrame:
        """Obtener catálogo de medicamentos como DataFrame"""
        data = self.get_medicamentos()
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    def get_inventario_sucursal_df(self, sucursal_id: int) -> pd.DataFrame:
        """Obtener inventario de sucursal como DataFrame"""
        data = self.get_inventario_sucursal(sucursal_id)
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()
    
    def get_comparativo_df(self) -> pd.DataFrame:
        """Obtener datos comparativos como DataFrame"""
        data = self.get_comparativo_sucursales()
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame()