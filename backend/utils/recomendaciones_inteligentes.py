"""
Sistema de Recomendaciones Inteligentes para Inventario Farmacéutico
Versión corregida - Soluciona errores NaN, fechas y divisiones por cero
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PrioridadRecomendacion(Enum):
    CRITICA = "CRÍTICA"
    ALTA = "ALTA"
    MEDIA = "MEDIA"
    BAJA = "BAJA"

@dataclass
class RecomendacionCompra:
    medicamento_id: int
    medicamento_nombre: str
    sku: str
    sucursal_id: int
    sucursal_nombre: str
    cantidad_recomendada: int
    prioridad: PrioridadRecomendacion
    motivo: str
    confianza: float  # 0-1, qué tan confiable es la recomendación
    ahorro_estimado: float
    riesgo_stockout: float  # 0-1, probabilidad de quedarse sin stock
    dias_stock_estimado: int
    detalles_calculo: Dict
    fecha_recomendacion: datetime

@dataclass
class MetricasInventario:
    rotacion_promedio: float
    dias_venta_promedio: float
    estacionalidad_factor: float
    tendencia_ventas: float
    variabilidad_demanda: float

# ==================== FUNCIONES DE SEGURIDAD ====================

def clean_nan_values(data):
    """Limpia valores NaN, inf y tipos numpy para serialización JSON"""
    if isinstance(data, dict):
        return {k: clean_nan_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nan_values(item) for item in data]
    elif isinstance(data, (np.floating, float)):
        if np.isnan(data) or np.isinf(data):
            return 0.0  # Convertir NaN/inf a 0
        return float(data)
    elif isinstance(data, np.integer):
        return int(data)
    elif isinstance(data, np.bool_):
        return bool(data)
    elif pd.isna(data):
        return 0.0
    return data

def safe_division(numerator, denominator, default=0.0):
    """División segura que evita errores por división entre cero"""
    try:
        if denominator == 0 or pd.isna(denominator) or pd.isna(numerator):
            return default
        result = float(numerator) / float(denominator)
        if np.isnan(result) or np.isinf(result):
            return default
        return result
    except (ZeroDivisionError, ValueError, TypeError):
        return default

def parse_safe_datetime(date_string):
    """Parsea fechas de manera segura con múltiples formatos"""
    if pd.isna(date_string) or date_string is None:
        return None
    
    try:
        # Usar pandas con format='ISO8601' que maneja ambos formatos
        return pd.to_datetime(date_string, format='ISO8601', errors='coerce')
    except:
        try:
            # Fallback a inferencia automática
            return pd.to_datetime(date_string, errors='coerce')
        except:
            logger.warning(f"No se pudo parsear fecha: {date_string}")
            return None

class RecomendacionesInteligentes:
    """
    Sistema avanzado de recomendaciones de compra para inventario farmacéutico
    """
    
    def __init__(self, supabase_url: str, supabase_key: str, tenant_id: int = 1):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.tenant_id = tenant_id
        self.headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json',
            'X-Tenant-ID': str(tenant_id)
        }
        
        # Parámetros del modelo
        self.DIAS_HISTORIAL = 90  # Días de historial para análisis
        self.NIVEL_SERVICIO_TARGET = 0.95  # 95% nivel de servicio
        self.FACTOR_SEGURIDAD = 1.2  # Factor de seguridad para stock
        self.DIAS_LEAD_TIME_DEFAULT = 7  # Lead time por defecto
        
    def _hacer_peticion(self, endpoint: str, query: str = "") -> List[Dict]:
        """Realizar petición a Supabase con manejo de errores"""
        try:
            url = f"{self.supabase_url}/rest/v1/{endpoint}"
            if query:
                url += f"?{query}"
                
            # Agregar filtro de tenant si no está en la query
            if "tenant_id" not in query and endpoint not in ['proveedores']:
                separator = "&" if query else "?"
                url += f"{separator}tenant_id=eq.{self.tenant_id}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Error HTTP {response.status_code} en {endpoint}")
                return []
                
        except Exception as e:
            logger.error(f"Error en petición a {endpoint}: {e}")
            return []
    
    def _obtener_datos_historicos(self, dias: int = None) -> Dict:
        """Obtener datos históricos del sistema"""
        dias = dias or self.DIAS_HISTORIAL
        fecha_inicio = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        
        # Obtener datos base
        inventario = self._hacer_peticion("vista_inventario_completo")
        ventas = self._hacer_peticion("salidas_inventario", 
                                     f"fecha_salida=gte.{fecha_inicio}&tipo_salida=eq.Venta")
        medicamentos = self._hacer_peticion("medicamentos")
        sucursales = self._hacer_peticion("sucursales")
        lotes = self._hacer_peticion("lotes_inventario")
        
        return {
            'inventario': inventario,
            'ventas': ventas,
            'medicamentos': medicamentos,
            'sucursales': sucursales,
            'lotes': lotes,
            'fecha_inicio': fecha_inicio
        }
    
    def _calcular_metricas_medicamento(self, medicamento_id: int, sucursal_id: int, 
                                     ventas_historicas: List[Dict]) -> MetricasInventario:
        """Calcular métricas avanzadas para un medicamento específico"""
        
        # Filtrar ventas del medicamento y sucursal
        ventas_filtradas = [
            v for v in ventas_historicas 
            if v.get('medicamento_id') == medicamento_id and v.get('sucursal_id') == sucursal_id
        ]
        
        if not ventas_filtradas:
            return MetricasInventario(0, 0, 1.0, 0, 0)
        
        # Convertir a DataFrame para análisis CON PARSING SEGURO
        df_ventas = pd.DataFrame(ventas_filtradas)
        
        # ✅ CORRECCIÓN PRINCIPAL: Usar parsing seguro de fechas
        df_ventas['fecha'] = df_ventas['fecha_salida'].apply(parse_safe_datetime)
        
        # Filtrar fechas válidas
        df_ventas = df_ventas.dropna(subset=['fecha'])
        
        # Convertir cantidad de manera segura
        df_ventas['cantidad'] = pd.to_numeric(df_ventas['cantidad'], errors='coerce').fillna(0)
        
        # Agrupar por día
        if len(df_ventas) == 0:
            return MetricasInventario(0, 0, 1.0, 0, 0)
            
        try:
            ventas_diarias = df_ventas.groupby(df_ventas['fecha'].dt.date)['cantidad'].sum()
        except Exception as e:
            logger.warning(f"Error agrupando ventas por fecha: {e}")
            return MetricasInventario(0, 0, 1.0, 0, 0)
        
        if len(ventas_diarias) == 0:
            return MetricasInventario(0, 0, 1.0, 0, 0)
        
        # Calcular métricas con divisiones seguras
        promedio_venta_diaria = safe_division(ventas_diarias.sum(), len(ventas_diarias), 0)
        rotacion = promedio_venta_diaria * 30 if promedio_venta_diaria > 0 else 0
        dias_venta = len(ventas_diarias)
        
        # Calcular estacionalidad (simplificado) con división segura
        if len(ventas_diarias) >= 7:
            ventas_semana_actual = ventas_diarias.tail(7).mean()
            ventas_promedio = ventas_diarias.mean()
            factor_estacional = safe_division(ventas_semana_actual, ventas_promedio, 1.0)
        else:
            factor_estacional = 1.0
        
        # Calcular tendencia usando regresión lineal con manejo de errores
        if len(ventas_diarias) >= 5:
            try:
                X = np.arange(len(ventas_diarias)).reshape(-1, 1)
                y = ventas_diarias.values
                modelo = LinearRegression().fit(X, y)
                tendencia = float(modelo.coef_[0])
                # Validar que no sea NaN
                if np.isnan(tendencia) or np.isinf(tendencia):
                    tendencia = 0.0
            except Exception as e:
                logger.warning(f"Error calculando tendencia: {e}")
                tendencia = 0.0
        else:
            tendencia = 0.0
        
        # Calcular variabilidad (coeficiente de variación) con división segura
        std_ventas = ventas_diarias.std()
        mean_ventas = ventas_diarias.mean()
        variabilidad = safe_division(std_ventas, mean_ventas, 0.0)
        
        return MetricasInventario(
            rotacion_promedio=rotacion,
            dias_venta_promedio=promedio_venta_diaria,
            estacionalidad_factor=max(0.5, min(2.0, factor_estacional)),  # Limitar entre 0.5 y 2.0
            tendencia_ventas=tendencia,
            variabilidad_demanda=variabilidad
        )
    
    def _predecir_demanda_futura(self, metricas: MetricasInventario, dias_prediccion: int = 30) -> Tuple[float, float]:
        """Predecir demanda futura y calcular stock de seguridad"""
        
        # Demanda esperada considerando tendencia y estacionalidad
        demanda_base = metricas.dias_venta_promedio * dias_prediccion
        demanda_con_tendencia = demanda_base + (metricas.tendencia_ventas * dias_prediccion)
        demanda_final = demanda_con_tendencia * metricas.estacionalidad_factor
        
        # Stock de seguridad basado en variabilidad y nivel de servicio
        z_score = 1.65  # Para 95% nivel de servicio (aproximado)
        lead_time = self.DIAS_LEAD_TIME_DEFAULT
        periodo_revision = 7  # Revisión semanal
        
        desviacion_demanda = metricas.dias_venta_promedio * metricas.variabilidad_demanda
        stock_seguridad = z_score * desviacion_demanda * np.sqrt(lead_time + periodo_revision)
        
        # Validar que no sean NaN o infinitos
        demanda_final = max(0, float(demanda_final)) if not (np.isnan(demanda_final) or np.isinf(demanda_final)) else 0
        stock_seguridad = max(0, float(stock_seguridad)) if not (np.isnan(stock_seguridad) or np.isinf(stock_seguridad)) else 0
        
        return demanda_final, stock_seguridad
    
    def _calcular_riesgo_stockout(self, stock_actual: int, demanda_predicha: float, 
                                stock_seguridad: float) -> float:
        """Calcular probabilidad de stockout"""
        
        stock_disponible = float(stock_actual)
        stock_necesario = demanda_predicha + stock_seguridad
        
        if stock_disponible >= stock_necesario:
            return 0.0
        elif stock_disponible <= 0:
            return 1.0
        else:
            # Función logística para calcular riesgo con división segura
            ratio = safe_division(stock_disponible, stock_necesario, 0.0)
            try:
                riesgo = 1 / (1 + np.exp(10 * (ratio - 0.5)))  # Función sigmoide
                return min(1.0, max(0.0, float(riesgo)))
            except:
                return 0.5  # Valor por defecto si falla el cálculo
    
    def _determinar_prioridad(self, riesgo_stockout: float, importancia_medicamento: str, 
                            stock_actual: int, stock_minimo: int) -> PrioridadRecomendacion:
        """Determinar prioridad de la recomendación"""
        
        # Factores de importancia
        factor_importancia = 1.0
        if importancia_medicamento in ['Antibiótico', 'Cardiovascular']:
            factor_importancia = 1.5
        elif importancia_medicamento in ['Analgésico', 'AINE']:
            factor_importancia = 1.2
        
        # Calcular score de prioridad con divisiones seguras
        score_riesgo = riesgo_stockout * 100
        score_stock = safe_division(max(stock_minimo - stock_actual, 0), max(stock_minimo, 1), 0) * 50
        score_final = (score_riesgo + score_stock) * factor_importancia
        
        if score_final >= 80:
            return PrioridadRecomendacion.CRITICA
        elif score_final >= 60:
            return PrioridadRecomendacion.ALTA
        elif score_final >= 40:
            return PrioridadRecomendacion.MEDIA
        else:
            return PrioridadRecomendacion.BAJA
    
    def _calcular_cantidad_optima(self, demanda_predicha: float, stock_seguridad: float,
                                stock_actual: int, stock_maximo: int, precio_compra: float) -> Tuple[int, float]:
        """Calcular cantidad óptima de compra y ahorro estimado"""
        
        # EOQ simplificado (Economic Order Quantity) con divisiones seguras
        demanda_anual = demanda_predicha * 12  # Aproximación anual
        costo_pedido = 50  # Costo fijo por pedido (estimado)
        costo_almacenamiento = precio_compra * 0.25  # 25% anual de holding cost
        
        if demanda_anual > 0 and costo_almacenamiento > 0:
            try:
                eoq = np.sqrt(safe_division(2 * demanda_anual * costo_pedido, costo_almacenamiento, demanda_predicha + stock_seguridad))
            except:
                eoq = demanda_predicha + stock_seguridad
        else:
            eoq = demanda_predicha + stock_seguridad
        
        # Cantidad necesaria para alcanzar nivel óptimo
        nivel_objetivo = demanda_predicha + stock_seguridad
        cantidad_necesaria = max(0, nivel_objetivo - stock_actual)
        
        # Ajustar por EOQ y límites de stock
        cantidad_optima = min(
            max(cantidad_necesaria, eoq * 0.5),  # Mínimo 50% del EOQ
            stock_maximo - stock_actual if stock_maximo > 0 else eoq * 2  # Máximo según límites
        )
        
        # Calcular ahorro estimado por compra en cantidad óptima
        ahorro_bulk = cantidad_optima * precio_compra * 0.05 if cantidad_optima > 100 else 0  # 5% descuento volumen
        ahorro_stockout = safe_division(demanda_predicha * precio_compra * 1.2 * cantidad_optima, max(demanda_predicha, 1), 0)
        
        # Validar valores finales
        cantidad_optima = max(0, int(cantidad_optima)) if not (np.isnan(cantidad_optima) or np.isinf(cantidad_optima)) else 0
        ahorro_total = max(0, float(ahorro_bulk + ahorro_stockout)) if not (np.isnan(ahorro_bulk + ahorro_stockout) or np.isinf(ahorro_bulk + ahorro_stockout)) else 0
        
        return cantidad_optima, ahorro_total
    
    def generar_recomendaciones_compra(self, sucursal_id: Optional[int] = None) -> List[RecomendacionCompra]:
        """Generar recomendaciones inteligentes de compra"""
        
        logger.info(f"Generando recomendaciones para tenant {self.tenant_id}, sucursal {sucursal_id}")
        
        # Obtener datos históricos
        datos = self._obtener_datos_historicos()
        
        if not datos['inventario']:
            logger.warning("No hay datos de inventario disponibles")
            return []
        
        # Filtrar por sucursal si se especifica
        inventario_filtrado = datos['inventario']
        if sucursal_id:
            inventario_filtrado = [inv for inv in inventario_filtrado if inv.get('sucursal_id') == sucursal_id]
        
        recomendaciones = []
        
        for i, item_inventario in enumerate(inventario_filtrado):
            try:
                # Extraer información básica con valores por defecto
                medicamento_id = item_inventario.get('medicamento_id')
                sucursal_id_item = item_inventario.get('sucursal_id')
                stock_actual = max(0, int(item_inventario.get('stock_actual', 0)))
                stock_minimo = max(0, int(item_inventario.get('stock_minimo', 0)))
                stock_maximo = max(100, int(item_inventario.get('stock_maximo', 1000)))
                precio_compra = max(0.01, float(item_inventario.get('precio_compra', 0)))
                
                # Información del medicamento
                medicamento_nombre = item_inventario.get('nombre', 'N/A')
                sku = item_inventario.get('sku', 'N/A')
                categoria = item_inventario.get('categoria', 'General')
                sucursal_nombre = item_inventario.get('sucursal_nombre', 'N/A')
                
                # Validar IDs requeridos
                if not medicamento_id or not sucursal_id_item:
                    continue
                
                # Calcular métricas del medicamento
                metricas = self._calcular_metricas_medicamento(
                    medicamento_id, sucursal_id_item, datos['ventas']
                )
                
                # Solo recomendar si hay actividad mínima
                if metricas.rotacion_promedio < 1 and stock_actual >= stock_minimo:
                    continue
                
                # Predecir demanda futura
                demanda_predicha, stock_seguridad = self._predecir_demanda_futura(metricas)
                
                # Calcular riesgo de stockout
                riesgo_stockout = self._calcular_riesgo_stockout(
                    stock_actual, demanda_predicha, stock_seguridad
                )
                
                # Solo continuar si hay riesgo significativo o stock bajo
                if riesgo_stockout < 0.1 and stock_actual >= stock_minimo:
                    continue
                
                # Determinar prioridad
                prioridad = self._determinar_prioridad(
                    riesgo_stockout, categoria, stock_actual, stock_minimo
                )
                
                # Calcular cantidad óptima
                cantidad_recomendada, ahorro_estimado = self._calcular_cantidad_optima(
                    demanda_predicha, stock_seguridad, stock_actual, stock_maximo, precio_compra
                )
                
                # Crear motivo detallado
                motivos = []
                if stock_actual < stock_minimo:
                    motivos.append(f"Stock por debajo del mínimo ({stock_actual}/{stock_minimo})")
                if riesgo_stockout > 0.3:
                    motivos.append(f"Alto riesgo de agotamiento ({riesgo_stockout:.1%})")
                if metricas.tendencia_ventas > 0:
                    motivos.append("Tendencia de ventas al alza")
                if metricas.estacionalidad_factor > 1.2:
                    motivos.append("Factor estacional alto")
                
                motivo = "; ".join(motivos) if motivos else "Optimización de inventario"
                
                # Calcular confianza de la recomendación con división segura
                confianza = min(1.0, max(0.3, 
                    safe_division(metricas.dias_venta_promedio, 10, 0.3) * (1 - metricas.variabilidad_demanda / 2)
                ))
                
                # Días de stock estimado con división segura
                dias_stock = int(safe_division(stock_actual, max(metricas.dias_venta_promedio, 0.1), 999))
                
                # Limpiar detalles de cálculo para evitar NaN
                detalles_calculo = {
                    'demanda_predicha': clean_nan_values(demanda_predicha),
                    'stock_seguridad': clean_nan_values(stock_seguridad),
                    'rotacion_promedio': clean_nan_values(metricas.rotacion_promedio),
                    'tendencia_ventas': clean_nan_values(metricas.tendencia_ventas),
                    'factor_estacional': clean_nan_values(metricas.estacionalidad_factor),
                    'variabilidad': clean_nan_values(metricas.variabilidad_demanda)
                }
                
                # Crear recomendación
                recomendacion = RecomendacionCompra(
                    medicamento_id=medicamento_id,
                    medicamento_nombre=medicamento_nombre,
                    sku=sku,
                    sucursal_id=sucursal_id_item,
                    sucursal_nombre=sucursal_nombre,
                    cantidad_recomendada=cantidad_recomendada,
                    prioridad=prioridad,
                    motivo=motivo,
                    confianza=confianza,
                    ahorro_estimado=ahorro_estimado,
                    riesgo_stockout=riesgo_stockout,
                    dias_stock_estimado=dias_stock,
                    detalles_calculo=detalles_calculo,
                    fecha_recomendacion=datetime.now()
                )
                
                recomendaciones.append(recomendacion)
                
            except Exception as e:
                logger.error(f"Error procesando item {i + 1}: {e}")
                continue
        
        # Ordenar por prioridad y riesgo
        prioridad_orden = {
            PrioridadRecomendacion.CRITICA: 0,
            PrioridadRecomendacion.ALTA: 1,
            PrioridadRecomendacion.MEDIA: 2,
            PrioridadRecomendacion.BAJA: 3
        }
        
        recomendaciones.sort(key=lambda x: (prioridad_orden[x.prioridad], -x.riesgo_stockout))
        
        logger.info(f"Generadas {len(recomendaciones)} recomendaciones")
        return recomendaciones
    
    def generar_reporte_recomendaciones(self, sucursal_id: Optional[int] = None) -> Dict:
        """Generar reporte completo de recomendaciones"""
        
        recomendaciones = self.generar_recomendaciones_compra(sucursal_id)
        
        # Convertir a diccionarios para serialización JSON con limpieza de NaN
        recomendaciones_dict = []
        for rec in recomendaciones:
            rec_dict = {
                'medicamento_id': rec.medicamento_id,
                'medicamento': rec.medicamento_nombre,
                'sku': rec.sku,
                'sucursal_id': rec.sucursal_id,
                'sucursal_nombre': rec.sucursal_nombre,
                'cantidad_recomendada': rec.cantidad_recomendada,
                'prioridad': rec.prioridad.value,
                'motivo': rec.motivo,
                'confianza': round(rec.confianza, 2),
                'ahorro_estimado': round(rec.ahorro_estimado, 2),
                'riesgo_stockout': round(rec.riesgo_stockout, 2),
                'dias_stock_estimado': rec.dias_stock_estimado,
                'detalles_calculo': rec.detalles_calculo
            }
            recomendaciones_dict.append(clean_nan_values(rec_dict))
        
        # Calcular estadísticas del reporte con valores seguros
        total_recomendaciones = len(recomendaciones)
        criticas = sum(1 for r in recomendaciones if r.prioridad == PrioridadRecomendacion.CRITICA)
        altas = sum(1 for r in recomendaciones if r.prioridad == PrioridadRecomendacion.ALTA)
        ahorro_total = sum(r.ahorro_estimado for r in recomendaciones)
        riesgo_promedio = safe_division(sum(r.riesgo_stockout for r in recomendaciones), len(recomendaciones), 0) if recomendaciones else 0
        confianza_promedio = safe_division(sum(r.confianza for r in recomendaciones), len(recomendaciones), 0) if recomendaciones else 0
        
        resultado = {
            'recomendaciones': recomendaciones_dict,
            'estadisticas': {
                'total_recomendaciones': total_recomendaciones,
                'criticas': criticas,
                'altas': altas,
                'medias': sum(1 for r in recomendaciones if r.prioridad == PrioridadRecomendacion.MEDIA),
                'bajas': sum(1 for r in recomendaciones if r.prioridad == PrioridadRecomendacion.BAJA),
                'ahorro_total_estimado': round(ahorro_total, 2),
                'riesgo_promedio': round(riesgo_promedio, 2),
                'confianza_promedio': round(confianza_promedio, 2)
            },
            'metadatos': {
                'tenant_id': self.tenant_id,
                'sucursal_id': sucursal_id,
                'fecha_generacion': datetime.now().isoformat(),
                'algoritmo_version': '2.1-corrected'
            }
        }
        
        # Limpiar cualquier NaN restante
        return clean_nan_values(resultado)

    # ========== MÉTODOS ADICIONALES PARA ENDPOINTS FALTANTES ==========
    
    def generar_recomendaciones_redistribucion(self) -> Dict:
        """Generar recomendaciones de redistribución entre sucursales"""
        try:
            # Obtener inventario completo
            inventario = self._hacer_peticion("vista_inventario_completo")
            
            if not inventario:
                return {
                    'recomendaciones': [],
                    'estadisticas': {
                        'total_oportunidades': 0,
                        'ahorro_estimado': 0
                    },
                    'tenant_id': self.tenant_id
                }
            
            # Agrupar por medicamento
            medicamentos_dict = {}
            for item in inventario:
                med_id = item.get('medicamento_id')
                if med_id not in medicamentos_dict:
                    medicamentos_dict[med_id] = []
                medicamentos_dict[med_id].append(item)
            
            recomendaciones_redistrib = []
            
            for med_id, sucursales_med in medicamentos_dict.items():
                if len(sucursales_med) < 2:
                    continue
                
                # Identificar sucursales con exceso y déficit
                sucursales_exceso = []
                sucursales_deficit = []
                
                for suc in sucursales_med:
                    stock_actual = suc.get('stock_actual', 0)
                    stock_minimo = suc.get('stock_minimo', 0)
                    stock_maximo = suc.get('stock_maximo', 1000)
                    
                    if stock_actual < stock_minimo:
                        deficit = stock_minimo - stock_actual
                        sucursales_deficit.append({
                            'sucursal_id': suc.get('sucursal_id'),
                            'sucursal_nombre': suc.get('sucursal_nombre'),
                            'deficit': deficit,
                            'data': suc
                        })
                    elif stock_actual > stock_maximo * 0.8:  # 80% del máximo
                        exceso = stock_actual - (stock_maximo * 0.6)  # Reducir a 60%
                        if exceso > 0:
                            sucursales_exceso.append({
                                'sucursal_id': suc.get('sucursal_id'),
                                'sucursal_nombre': suc.get('sucursal_nombre'),
                                'exceso': exceso,
                                'data': suc
                            })
                
                # Crear recomendaciones de redistribución
                for deficit_suc in sucursales_deficit:
                    for exceso_suc in sucursales_exceso:
                        if deficit_suc['sucursal_id'] != exceso_suc['sucursal_id']:
                            cantidad_redistribuir = min(deficit_suc['deficit'], exceso_suc['exceso'])
                            
                            if cantidad_redistribuir > 0:
                                precio_unitario = exceso_suc['data'].get('precio_venta', 0)
                                ahorro = cantidad_redistribuir * precio_unitario * 0.1  # 10% ahorro vs compra nueva
                                
                                recomendaciones_redistrib.append({
                                    'medicamento_id': med_id,
                                    'medicamento_nombre': exceso_suc['data'].get('nombre', 'N/A'),
                                    'sucursal_origen_id': exceso_suc['sucursal_id'],
                                    'sucursal_origen_nombre': exceso_suc['sucursal_nombre'],
                                    'sucursal_destino_id': deficit_suc['sucursal_id'],
                                    'sucursal_destino_nombre': deficit_suc['sucursal_nombre'],
                                    'cantidad_recomendada': int(cantidad_redistribuir),
                                    'ahorro_estimado': round(ahorro, 2),
                                    'prioridad': 'ALTA' if deficit_suc['deficit'] > 10 else 'MEDIA'
                                })
            
            # Estadísticas
            total_oportunidades = len(recomendaciones_redistrib)
            ahorro_total = sum(r['ahorro_estimado'] for r in recomendaciones_redistrib)
            
            resultado = {
                'recomendaciones': recomendaciones_redistrib,
                'estadisticas': {
                    'total_oportunidades': total_oportunidades,
                    'ahorro_estimado': round(ahorro_total, 2)
                },
                'metadatos': {
                    'tenant_id': self.tenant_id,
                    'fecha_generacion': datetime.now().isoformat()
                }
            }
            
            return clean_nan_values(resultado)
            
        except Exception as e:
            logger.error(f"Error generando recomendaciones redistribución: {e}")
            return {
                'recomendaciones': [],
                'estadisticas': {
                    'total_oportunidades': 0,
                    'ahorro_estimado': 0
                },
                'error': str(e),
                'tenant_id': self.tenant_id
            }

# Función de utilidad para uso directo
def generar_recomendaciones_para_sucursal(supabase_url: str, supabase_key: str, 
                                         sucursal_id: int, tenant_id: int = 1) -> Dict:
    """Función de utilidad para generar recomendaciones para una sucursal específica"""
    
    sistema = RecomendacionesInteligentes(supabase_url, supabase_key, tenant_id)
    return sistema.generar_reporte_recomendaciones(sucursal_id)