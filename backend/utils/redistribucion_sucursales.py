# backend/utils/redistribucion_sucursales.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math

class RedistribucionSucursales:
    def __init__(self):
        # Costos de transferencia (MXN)
        self.costo_base_transferencia = 50.0    # Costo fijo por transferencia
        self.costo_por_unidad = 2.0            # Costo por unidad transferida
        self.costo_por_km = 1.5                # Costo por km de distancia
        
        # Parámetros de optimización
        self.min_cantidad_transferencia = 5    # Mínimo a transferir
        self.max_distancia_km = 50            # Máxima distancia para transferencia
        self.factor_urgencia = 1.5             # Multiplicador para casos urgentes
        
        # Umbrales de decisión
        self.umbral_exceso = 2.0               # 200% del stock mínimo
        self.umbral_deficit_critico = 0.5      # 50% del stock mínimo
        self.umbral_deficit_alto = 0.8         # 80% del stock mínimo
    
    def calcular_distancias_sucursales(self, sucursales: List[Dict]) -> Dict:
        """
        Calcula distancias simuladas entre sucursales
        En producción usaría APIs de geolocalización reales
        """
        distancias = {}
        
        # Coordenadas simuladas para las sucursales de ejemplo
        coordenadas_simuladas = {
            'Clínica Centro': {'lat': 19.4326, 'lng': -99.1332},    # Centro de CDMX
            'Clínica Norte': {'lat': 19.5051, 'lng': -99.2147},     # Satélite
            'Clínica Sur': {'lat': 19.3000, 'lng': -99.1500}       # Sur CDMX
        }
        
        for i, suc1 in enumerate(sucursales):
            for j, suc2 in enumerate(sucursales):
                if i != j:
                    # Calcular distancia euclidiana simulada
                    coord1 = coordenadas_simuladas.get(suc1['nombre'], {'lat': 19.4, 'lng': -99.1})
                    coord2 = coordenadas_simuladas.get(suc2['nombre'], {'lat': 19.4, 'lng': -99.1})
                    
                    # Fórmula haversine simplificada
                    lat_diff = abs(coord1['lat'] - coord2['lat'])
                    lng_diff = abs(coord1['lng'] - coord2['lng'])
                    distancia_km = math.sqrt(lat_diff**2 + lng_diff**2) * 111  # Aproximación
                    
                    key = f"{suc1['id']}-{suc2['id']}"
                    distancias[key] = {
                        'sucursal_origen': suc1['nombre'],
                        'sucursal_destino': suc2['nombre'],
                        'distancia_km': round(distancia_km, 1),
                        'tiempo_estimado_horas': round(distancia_km / 30, 1),  # 30 km/h promedio
                        'costo_transporte': round(self.costo_base_transferencia + (distancia_km * self.costo_por_km), 2)
                    }
        
        return distancias
    
    def analizar_oportunidades_redistribucion(self, inventario_consolidado: List[Dict], sucursales: List[Dict]) -> Dict:
        """
        Analiza oportunidades de redistribución entre sucursales
        """
        # Calcular distancias
        distancias = self.calcular_distancias_sucursales(sucursales)
        
        # Agrupar inventario por SKU
        inventario_por_sku = {}
        for item in inventario_consolidado:
            sku = item['sku']
            if sku not in inventario_por_sku:
                inventario_por_sku[sku] = {
                    'medicamento_nombre': item['nombre'],
                    'categoria': item['categoria'],
                    'precio_compra': item['precio_compra'],
                    'precio_venta': item['precio_venta'],
                    'sucursales': {}
                }
            
            inventario_por_sku[sku]['sucursales'][item['sucursal_id']] = {
                'sucursal_nombre': item['sucursal_nombre'],
                'stock_actual': item['stock_actual'],
                'stock_minimo': item['stock_minimo'],
                'proxima_caducidad': item.get('proxima_caducidad'),
                'estado': item['estado']
            }
        
        # Analizar cada SKU para oportunidades
        oportunidades = []
        for sku, data in inventario_por_sku.items():
            oportunidades_sku = self._analizar_sku_redistribucion(sku, data, distancias)
            oportunidades.extend(oportunidades_sku)
        
        # Calcular resumen y métricas
        resumen = self._calcular_resumen_redistribucion(oportunidades)
        
        # Priorizar oportunidades
        oportunidades_priorizadas = self._priorizar_oportunidades(oportunidades)
        
        return {
            'oportunidades': oportunidades_priorizadas,
            'resumen': resumen,
            'total_oportunidades': len(oportunidades),
            'valor_total_transferible': sum(op['valor_transferencia'] for op in oportunidades),
            'ahorro_total_estimado': sum(op['ahorro_estimado'] for op in oportunidades),
            'fecha_analisis': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    def _analizar_sku_redistribucion(self, sku: str, data: Dict, distancias: Dict) -> List[Dict]:
        """
        Analiza oportunidades de redistribución para un SKU específico
        """
        oportunidades = []
        sucursales_data = data['sucursales']
        
        # Identificar sucursales con exceso y déficit
        sucursales_exceso = []
        sucursales_deficit = []
        
        for suc_id, suc_data in sucursales_data.items():
            stock_actual = suc_data['stock_actual']
            stock_minimo = suc_data['stock_minimo']
            ratio = stock_actual / max(stock_minimo, 1)
            
            if ratio <= self.umbral_deficit_critico:
                sucursales_deficit.append({
                    'sucursal_id': suc_id,
                    'sucursal_nombre': suc_data['sucursal_nombre'],
                    'stock_actual': stock_actual,
                    'stock_minimo': stock_minimo,
                    'deficit': stock_minimo - stock_actual,
                    'ratio': ratio,
                    'urgencia': 'CRÍTICA',
                    'estado': suc_data['estado']
                })
            elif ratio <= self.umbral_deficit_alto:
                sucursales_deficit.append({
                    'sucursal_id': suc_id,
                    'sucursal_nombre': suc_data['sucursal_nombre'],
                    'stock_actual': stock_actual,
                    'stock_minimo': stock_minimo,
                    'deficit': stock_minimo - stock_actual,
                    'ratio': ratio,
                    'urgencia': 'ALTA',
                    'estado': suc_data['estado']
                })
            elif ratio >= self.umbral_exceso:
                exceso = stock_actual - int(stock_minimo * 1.2)  # Mantener 120% como buffer
                if exceso > 0:
                    sucursales_exceso.append({
                        'sucursal_id': suc_id,
                        'sucursal_nombre': suc_data['sucursal_nombre'],
                        'stock_actual': stock_actual,
                        'stock_minimo': stock_minimo,
                        'exceso': exceso,
                        'ratio': ratio,
                        'proxima_caducidad': suc_data.get('proxima_caducidad')
                    })
        
        # Crear recomendaciones de transferencia
        for deficit in sucursales_deficit:
            for exceso in sucursales_exceso:
                if deficit['sucursal_id'] != exceso['sucursal_id']:
                    # Buscar distancia entre sucursales
                    key_distancia = f"{exceso['sucursal_id']}-{deficit['sucursal_id']}"
                    distancia_info = distancias.get(key_distancia, {})
                    
                    if distancia_info.get('distancia_km', 999) <= self.max_distancia_km:
                        cantidad_optima = self._calcular_cantidad_optima_transferencia(
                            deficit, exceso, distancia_info, data
                        )
                        
                        if cantidad_optima >= self.min_cantidad_transferencia:
                            oportunidad = self._crear_oportunidad_transferencia(
                                sku, data, deficit, exceso, cantidad_optima, distancia_info
                            )
                            oportunidades.append(oportunidad)
        
        return oportunidades
    
    def _calcular_cantidad_optima_transferencia(self, deficit: Dict, exceso: Dict, distancia_info: Dict, medicamento_data: Dict) -> int:
        """
        Calcula la cantidad óptima a transferir considerando costos y beneficios
        """
        # Cantidad máxima transferible
        max_transferible = min(
            exceso['exceso'],
            deficit['deficit'] + int(deficit['stock_minimo'] * 0.5)  # Agregar buffer
        )
        
        if max_transferible <= 0:
            return 0
        
        # Calcular costo de transferencia
        costo_transferencia = distancia_info.get('costo_transporte', 100)
        costo_por_unidad_total = self.costo_por_unidad + (costo_transferencia / max(max_transferible, 1))
        
        # Calcular beneficio vs costo de compra nueva
        precio_compra = medicamento_data['precio_compra']
        beneficio_por_unidad = precio_compra - costo_por_unidad_total
        
        # Solo transferir si es beneficioso
        if beneficio_por_unidad > 0:
            # Aplicar factor de urgencia
            if deficit['urgencia'] == 'CRÍTICA':
                cantidad_recomendada = max_transferible
            else:
                cantidad_recomendada = min(max_transferible, deficit['deficit'])
            
            return int(cantidad_recomendada)
        
        return 0
    
    def _crear_oportunidad_transferencia(self, sku: str, medicamento_data: Dict, deficit: Dict, exceso: Dict, cantidad: int, distancia_info: Dict) -> Dict:
        """
        Crea un registro de oportunidad de transferencia
        """
        precio_compra = medicamento_data['precio_compra']
        precio_venta = medicamento_data['precio_venta']
        
        # Calcular costos y beneficios
        costo_transferencia = distancia_info.get('costo_transporte', 100)
        costo_total = (cantidad * self.costo_por_unidad) + costo_transferencia
        
        # Ahorro vs compra nueva
        ahorro_compra = cantidad * precio_compra
        ahorro_neto = ahorro_compra - costo_total
        
        # Valor de la transferencia
        valor_transferencia = cantidad * precio_venta
        
        # Calcular urgencia y prioridad
        urgencia_score = self._calcular_score_urgencia(deficit, exceso)
        
        return {
            'sku': sku,
            'medicamento_nombre': medicamento_data['medicamento_nombre'],
            'categoria': medicamento_data['categoria'],
            'sucursal_origen_id': exceso['sucursal_id'],
            'sucursal_origen_nombre': exceso['sucursal_nombre'],
            'sucursal_destino_id': deficit['sucursal_id'],
            'sucursal_destino_nombre': deficit['sucursal_nombre'],
            'cantidad_transferir': cantidad,
            'stock_origen_actual': exceso['stock_actual'],
            'stock_destino_actual': deficit['stock_actual'],
            'stock_origen_despues': exceso['stock_actual'] - cantidad,
            'stock_destino_despues': deficit['stock_actual'] + cantidad,
            'exceso_origen': exceso['exceso'],
            'deficit_destino': deficit['deficit'],
            'urgencia': deficit['urgencia'],
            'prioridad_score': urgencia_score,
            'distancia_km': distancia_info.get('distancia_km', 0),
            'tiempo_estimado_horas': distancia_info.get('tiempo_estimado_horas', 0),
            'costo_transferencia': round(costo_total, 2),
            'ahorro_estimado': round(ahorro_neto, 2),
            'valor_transferencia': round(valor_transferencia, 2),
            'roi_transferencia': round((ahorro_neto / max(costo_total, 1)) * 100, 1),
            'fecha_recomendada': self._calcular_fecha_recomendada(deficit['urgencia']),
            'justificacion': self._generar_justificacion(deficit, exceso, cantidad, ahorro_neto)
        }
    
    def _calcular_score_urgencia(self, deficit: Dict, exceso: Dict) -> int:
        """
        Calcula score de urgencia para priorización
        """
        score = 0
        
        # Factor por urgencia del déficit
        if deficit['urgencia'] == 'CRÍTICA':
            score += 100
        elif deficit['urgencia'] == 'ALTA':
            score += 70
        else:
            score += 30
        
        # Factor por ratio de stock
        score += int((1 - deficit['ratio']) * 50)  # Más puntos por menor ratio
        
        # Factor por exceso en origen
        score += min(int(exceso['ratio'] * 10), 30)  # Más puntos por mayor exceso
        
        # Factor por proximidad de vencimiento en origen
        if exceso.get('proxima_caducidad'):
            try:
                fecha_venc = datetime.strptime(exceso['proxima_caducidad'], '%Y-%m-%d')
                dias_hasta_venc = (fecha_venc - datetime.now()).days
                if dias_hasta_venc <= 30:
                    score += 50
                elif dias_hasta_venc <= 60:
                    score += 25
            except:
                pass
        
        return score
    
    def _calcular_fecha_recomendada(self, urgencia: str) -> str:
        """
        Calcula fecha recomendada para la transferencia
        """
        if urgencia == 'CRÍTICA':
            fecha = datetime.now() + timedelta(days=1)  # Mañana
        elif urgencia == 'ALTA':
            fecha = datetime.now() + timedelta(days=3)  # En 3 días
        else:
            fecha = datetime.now() + timedelta(days=7)  # En una semana
        
        return fecha.strftime('%Y-%m-%d')
    
    def _generar_justificacion(self, deficit: Dict, exceso: Dict, cantidad: int, ahorro: float) -> str:
        """
        Genera justificación textual para la transferencia
        """
        justificaciones = []
        
        if deficit['urgencia'] == 'CRÍTICA':
            justificaciones.append(f"Stock crítico en {deficit['sucursal_nombre']}")
        
        if exceso['ratio'] > 3:
            justificaciones.append(f"Exceso significativo en {exceso['sucursal_nombre']}")
        
        if ahorro > 0:
            justificaciones.append(f"Ahorro de ${ahorro:.2f} vs compra nueva")
        
        return '; '.join(justificaciones)
    
    def _priorizar_oportunidades(self, oportunidades: List[Dict]) -> List[Dict]:
        """
        Prioriza oportunidades por urgencia y beneficio
        """
        return sorted(oportunidades, key=lambda x: (
            -x['prioridad_score'],
            -x['ahorro_estimado']
        ))
    
    def _calcular_resumen_redistribucion(self, oportunidades: List[Dict]) -> Dict:
        """
        Calcula resumen de oportunidades de redistribución
        """
        if not oportunidades:
            return {
                'total_transferencias': 0,
                'ahorro_total': 0,
                'valor_total': 0,
                'transferencias_por_urgencia': {}
            }
        
        transferencias_por_urgencia = {}
        for op in oportunidades:
            urgencia = op['urgencia']
            if urgencia not in transferencias_por_urgencia:
                transferencias_por_urgencia[urgencia] = {
                    'cantidad': 0,
                    'valor': 0,
                    'ahorro': 0
                }
            transferencias_por_urgencia[urgencia]['cantidad'] += 1
            transferencias_por_urgencia[urgencia]['valor'] += op['valor_transferencia']
            transferencias_por_urgencia[urgencia]['ahorro'] += op['ahorro_estimado']
        
        return {
            'total_transferencias': len(oportunidades),
            'ahorro_total': round(sum(op['ahorro_estimado'] for op in oportunidades), 2),
            'valor_total': round(sum(op['valor_transferencia'] for op in oportunidades), 2),
            'costo_total_transferencias': round(sum(op['costo_transferencia'] for op in oportunidades), 2),
            'transferencias_por_urgencia': transferencias_por_urgencia,
            'sucursales_mas_necesitadas': self._identificar_sucursales_necesitadas(oportunidades),
            'sucursales_con_mas_exceso': self._identificar_sucursales_exceso(oportunidades)
        }
    
    def _identificar_sucursales_necesitadas(self, oportunidades: List[Dict]) -> List[Dict]:
        """
        Identifica sucursales que más necesitan transferencias
        """
        necesidades = {}
        for op in oportunidades:
            suc = op['sucursal_destino_nombre']
            if suc not in necesidades:
                necesidades[suc] = {'transferencias': 0, 'valor': 0}
            necesidades[suc]['transferencias'] += 1
            necesidades[suc]['valor'] += op['valor_transferencia']
        
        return sorted(
            [{'sucursal': k, **v} for k, v in necesidades.items()],
            key=lambda x: x['valor'],
            reverse=True
        )[:3]
    
    def _identificar_sucursales_exceso(self, oportunidades: List[Dict]) -> List[Dict]:
        """
        Identifica sucursales con más exceso para transferir
        """
        excesos = {}
        for op in oportunidades:
            suc = op['sucursal_origen_nombre']
            if suc not in excesos:
                excesos[suc] = {'transferencias': 0, 'valor': 0}
            excesos[suc]['transferencias'] += 1
            excesos[suc]['valor'] += op['valor_transferencia']
        
        return sorted(
            [{'sucursal': k, **v} for k, v in excesos.items()],
            key=lambda x: x['valor'],
            reverse=True
        )[:3]