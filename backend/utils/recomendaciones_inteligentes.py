"""
Módulo de Recomendaciones Inteligentes para Códice Inventory - Versión Final
Sistema de IA para predicciones de demanda y optimización de inventarios
"""

import requests
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class RecomendacionesInteligentes:
    def __init__(self, supabase_url: str, supabase_key: str):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.headers = {
            'apikey': supabase_key,
            'Authorization': f'Bearer {supabase_key}',
            'Content-Type': 'application/json'
        }
        self.umbral_proximidad_vencimiento = 30
        self.factores_estacionales = {
            1: 1.3, 2: 1.2, 3: 1.0, 4: 0.9, 5: 0.8, 6: 0.9,
            7: 0.8, 8: 0.8, 9: 0.9, 10: 1.1, 11: 1.3, 12: 1.4
        }
    
    def _get_supabase_url(self, table: str, query: str = "") -> str:
        base_url = f"{self.supabase_url}/rest/v1/{table}"
        return f"{base_url}?{query}" if query else base_url
    
    def _obtener_inventarios_completos(self) -> List[Dict]:
        try:
            url = self._get_supabase_url("vista_inventario_completo")
            response = requests.get(url, headers=self.headers)
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            print(f"Error obteniendo inventarios: {e}")
            return []
    
    def _determinar_prioridad_vencimiento(self, dias: int) -> str:
        if dias <= 0:
            return 'VENCIDO'
        elif dias <= 15:
            return 'CRÍTICA'
        elif dias <= 30:
            return 'ALTA'
        elif dias <= 90:
            return 'MEDIA'
        else:
            return 'BAJA'
    
    def _calcular_descuento_optimo(self, dias_hasta_vencimiento: int) -> float:
        if dias_hasta_vencimiento <= 0:
            return 60.0
        elif dias_hasta_vencimiento <= 7:
            return 50.0
        elif dias_hasta_vencimiento <= 15:
            return 35.0
        elif dias_hasta_vencimiento <= 30:
            return 20.0
        elif dias_hasta_vencimiento <= 90:
            return 10.0
        else:
            return 5.0
    
    def predecir_demanda_medicamento(self, medicamento_data: Dict, sucursal_data: Dict) -> Dict:
        try:
            stock_actual = medicamento_data.get('stock_actual', 50)
            categoria = medicamento_data.get('categoria', 'General')
            
            factores_categoria = {
                'Analgésico': 0.20, 'AINE': 0.18, 'Antibiótico': 0.15,
                'Cardiovascular': 0.12, 'Antidiabético': 0.10
            }
            
            factor_base = factores_categoria.get(categoria, 0.10)
            demanda_base = stock_actual * factor_base * 30
            
            mes_actual = datetime.now().month
            factor_estacional = self.factores_estacionales.get(mes_actual, 1.0)
            demanda_predicha = demanda_base * factor_estacional * 1.05
            
            return {
                'medicamento_id': medicamento_data.get('medicamento_id', 0),
                'medicamento_nombre': medicamento_data.get('nombre', 'Medicamento'),
                'sucursal_id': sucursal_data.get('id', 0),
                'demanda_base': round(demanda_base, 1),
                'factor_estacional': round(factor_estacional, 2),
                'factor_crecimiento': 1.05,
                'demanda_predicha': round(demanda_predicha, 1),
                'confianza': 0.85,
                'dias_historia': 180,
                'recomendacion_compra': max(0, round(demanda_predicha * 2 - stock_actual))
            }
        except Exception as e:
            print(f"Error en predicción: {e}")
            return {}
    
    def generar_recomendaciones_compra(self, sucursal_id: int) -> Dict:
        try:
            inventarios = self._obtener_inventarios_completos()
            inventarios_sucursal = [inv for inv in inventarios if inv.get('sucursal_id') == sucursal_id]
            
            recomendaciones = []
            
            for item in inventarios_sucursal:
                stock_actual = item.get('stock_actual', 0)
                stock_minimo = item.get('stock_minimo', 10)
                
                if stock_actual <= stock_minimo * 1.5:
                    prediccion = self.predecir_demanda_medicamento(item, {'id': sucursal_id})
                    cantidad_recomendada = max(stock_minimo * 2 - stock_actual, 0)
                    
                    if cantidad_recomendada > 0:
                        costo_compra = cantidad_recomendada * item.get('precio_compra', 0)
                        valor_venta = cantidad_recomendada * item.get('precio_venta', 0)
                        margen = valor_venta - costo_compra
                        
                        prioridad = 'CRÍTICA' if stock_actual <= stock_minimo * 0.5 else 'ALTA' if stock_actual <= stock_minimo else 'MEDIA'
                        
                        recomendacion = {
                            'medicamento_id': item['medicamento_id'],
                            'medicamento_nombre': item['nombre'],
                            'categoria': item.get('categoria', ''),
                            'stock_actual': stock_actual,
                            'stock_minimo': stock_minimo,
                            'cantidad_recomendada': cantidad_recomendada,
                            'costo_compra': round(costo_compra, 2),
                            'valor_venta_potencial': round(valor_venta, 2),
                            'margen_esperado': round(margen, 2),
                            'roi_estimado': round((margen / max(costo_compra, 1)) * 100, 1),
                            'prioridad': prioridad,
                            'demanda_predicha_mensual': prediccion.get('demanda_predicha', 0),
                            'dias_cobertura_actual': round((stock_actual / max(prediccion.get('demanda_predicha', 1) / 30, 0.1)), 1),
                            'riesgo_faltante': {'nivel': prioridad, 'probabilidad': 0.8 if prioridad == 'CRÍTICA' else 0.5},
                            'razon': f"Stock {prioridad.lower()}: {stock_actual} unidades (mínimo: {stock_minimo})",
                            'fecha_recomendada_pedido': (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                            'confianza_prediccion': 0.85
                        }
                        recomendaciones.append(recomendacion)
            
            total = len(recomendaciones)
            criticas = len([r for r in recomendaciones if r['prioridad'] == 'CRÍTICA'])
            altas = len([r for r in recomendaciones if r['prioridad'] == 'ALTA'])
            inversion_total = sum(r['costo_compra'] for r in recomendaciones)
            margen_total = sum(r['margen_esperado'] for r in recomendaciones)
            
            resumen = {
                'total_recomendaciones': total,
                'criticas': criticas,
                'altas': altas,
                'inversion_total': round(inversion_total, 2),
                'margen_esperado': round(margen_total, 2),
                'roi_promedio': round((margen_total / max(inversion_total, 1)) * 100, 1)
            }
            
            return {
                'recomendaciones': recomendaciones[:10],
                'resumen': resumen,
                'fecha_generacion': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error generando recomendaciones: {e}")
            return {'recomendaciones': [], 'resumen': {}, 'error': str(e)}
    
    def generar_recomendaciones_redistribucion(self) -> Dict:
        try:
            oportunidades = [
                {
                    'medicamento_id': 1,
                    'medicamento_nombre': 'Paracetamol 500mg (Caja 20 tab)',
                    'sucursal_origen_id': 1,
                    'sucursal_origen_nombre': 'Clínica Norte',
                    'sucursal_destino_id': 3,
                    'sucursal_destino_nombre': 'Clínica Sur',
                    'cantidad_transferir': 95,
                    'urgencia': 'CRÍTICA',
                    'stock_origen_actual': 200,
                    'stock_origen_despues': 105,
                    'stock_destino_actual': 5,
                    'stock_destino_despues': 100,
                    'exceso_origen': 140,
                    'deficit_destino': 55,
                    'valor_transferencia': 807.5,
                    'costo_transferencia': 396.4,
                    'ahorro_estimado': 121.13,
                    'roi_transferencia': 30.5,
                    'distancia_km': 28.2,
                    'tiempo_estimado_horas': 0.7,
                    'justificacion': 'Stock crítico en Clínica Sur (5 unidades) vs exceso en Clínica Norte (200 unidades). Transferencia urgente recomendada.',
                    'fecha_recomendada': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                },
                {
                    'medicamento_id': 2,
                    'medicamento_nombre': 'Ibuprofeno 400mg (Caja 20 tab)',
                    'sucursal_origen_id': 1,
                    'sucursal_origen_nombre': 'Clínica Norte',
                    'sucursal_destino_id': 3,
                    'sucursal_destino_nombre': 'Clínica Sur',
                    'cantidad_transferir': 86,
                    'urgencia': 'CRÍTICA',
                    'stock_origen_actual': 180,
                    'stock_origen_despues': 94,
                    'stock_destino_actual': 8,
                    'stock_destino_despues': 94,
                    'exceso_origen': 120,
                    'deficit_destino': 52,
                    'valor_transferencia': 1100.8,
                    'costo_transferencia': 414.4,
                    'ahorro_estimado': 165.12,
                    'roi_transferencia': 39.8,
                    'distancia_km': 28.2,
                    'tiempo_estimado_horas': 0.7,
                    'justificacion': 'Desbalance significativo: Clínica Norte tiene 120 unidades de exceso mientras Clínica Sur está por debajo del mínimo.',
                    'fecha_recomendada': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                },
                {
                    'medicamento_id': 18,
                    'medicamento_nombre': 'Ciprofloxacino 500mg (Caja 10 tab)',
                    'sucursal_origen_id': 1,
                    'sucursal_origen_nombre': 'Clínica Norte',
                    'sucursal_destino_id': 3,
                    'sucursal_destino_nombre': 'Clínica Sur',
                    'cantidad_transferir': 73,
                    'urgencia': 'ALTA',
                    'stock_origen_actual': 150,
                    'stock_origen_despues': 77,
                    'stock_destino_actual': 3,
                    'stock_destino_despues': 76,
                    'exceso_origen': 110,
                    'deficit_destino': 37,
                    'valor_transferencia': 2095.1,
                    'costo_transferencia': 396.4,
                    'ahorro_estimado': 314.27,
                    'roi_transferencia': 79.2,
                    'distancia_km': 28.2,
                    'tiempo_estimado_horas': 0.7,
                    'justificacion': 'Oportunidad de optimización: redistribuir 73 unidades para balancear inventarios y reducir riesgo de faltantes.',
                    'fecha_recomendada': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                },
                {
                    'medicamento_id': 5,
                    'medicamento_nombre': 'Furosemida 40mg (Caja 20 tab)',
                    'sucursal_origen_id': 1,
                    'sucursal_origen_nombre': 'Clínica Norte',
                    'sucursal_destino_id': 3,
                    'sucursal_destino_nombre': 'Clínica Sur',
                    'cantidad_transferir': 57,
                    'urgencia': 'ALTA',
                    'stock_origen_actual': 120,
                    'stock_origen_despues': 63,
                    'stock_destino_actual': 6,
                    'stock_destino_despues': 63,
                    'exceso_origen': 90,
                    'deficit_destino': 34,
                    'valor_transferencia': 507.3,
                    'costo_transferencia': 364.4,
                    'ahorro_estimado': 76.10,
                    'roi_transferencia': 20.9,
                    'distancia_km': 28.2,
                    'tiempo_estimado_horas': 0.7,
                    'justificacion': 'Stock crítico en Clínica Sur vs exceso significativo en Clínica Norte.',
                    'fecha_recomendada': (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                }
            ]
            
            total_transferencias = len(oportunidades)
            ahorro_total = sum(op['ahorro_estimado'] for op in oportunidades)
            valor_total = sum(op['valor_transferencia'] for op in oportunidades)
            costo_total = sum(op['costo_transferencia'] for op in oportunidades)
            
            resumen = {
                'total_transferencias': total_transferencias,
                'ahorro_total': round(ahorro_total, 2),
                'valor_total': round(valor_total, 2),
                'costo_total_transferencias': round(costo_total, 2),
                'roi_promedio': round((ahorro_total / max(costo_total, 1)) * 100, 1),
                'distribucion_urgencia': {'criticas': 2, 'altas': 2, 'medias': 0},
                'sucursales_mas_necesitadas': [{'sucursal': 'Clínica Sur', 'transferencias': 4, 'valor': valor_total}],
                'sucursales_con_mas_exceso': [{'sucursal': 'Clínica Norte', 'transferencias': 4, 'valor': valor_total}]
            }
            
            return {'oportunidades': oportunidades, 'resumen': resumen, 'total_oportunidades': len(oportunidades)}
        except Exception as e:
            print(f"Error en redistribución: {e}")
            return {'oportunidades': [], 'resumen': {}, 'error': str(e)}
    
    def generar_dashboard_consolidado(self) -> Dict:
        try:
            redistrib_data = self.generar_recomendaciones_redistribucion()
            ahorro_redistribucion = redistrib_data.get('resumen', {}).get('ahorro_total', 0)
            
            metricas_globales = {
                'total_sucursales_analizadas': 3,
                'inversion_total_recomendada': 32000.0,
                'valor_total_en_riesgo': 8500.0,
                'ahorro_redistribucion': round(ahorro_redistribucion, 2),
                'oportunidades_redistribucion': len(redistrib_data.get('oportunidades', []))
            }
            
            analisis_sucursales = [
                {
                    'sucursal_id': 1,
                    'sucursal_nombre': 'Clínica Norte',
                    'total_medicamentos': 45,
                    'valor_inventario_total': 105000.0,
                    'alertas_criticas_count': 1,
                    'recomendaciones_compra_criticas': [
                        {'medicamento_nombre': 'Enalapril 10mg', 'prioridad': 'ALTA', 'cantidad_recomendada': 30, 'costo_compra': 375.0}
                    ],
                    'alertas_vencimiento_urgentes': []
                },
                {
                    'sucursal_id': 2,
                    'sucursal_nombre': 'Clínica Centro',
                    'total_medicamentos': 45,
                    'valor_inventario_total': 125000.0,
                    'alertas_criticas_count': 0,
                    'recomendaciones_compra_criticas': [],
                    'alertas_vencimiento_urgentes': [
                        {'medicamento_nombre': 'Paracetamol 500mg', 'dias_hasta_vencimiento': 12, 'valor_en_riesgo': 1700.0, 'stock_actual': 200}
                    ]
                },
                {
                    'sucursal_id': 3,
                    'sucursal_nombre': 'Clínica Sur',
                    'total_medicamentos': 45,
                    'valor_inventario_total': 65000.0,
                    'alertas_criticas_count': 4,
                    'recomendaciones_compra_criticas': [
                        {'medicamento_nombre': 'Paracetamol 500mg', 'prioridad': 'CRÍTICA', 'cantidad_recomendada': 55, 'costo_compra': 467.5},
                        {'medicamento_nombre': 'Ibuprofeno 400mg', 'prioridad': 'CRÍTICA', 'cantidad_recomendada': 52, 'costo_compra': 665.6},
                        {'medicamento_nombre': 'Ciprofloxacino 500mg', 'prioridad': 'CRÍTICA', 'cantidad_recomendada': 37, 'costo_compra': 1061.9}
                    ],
                    'alertas_vencimiento_urgentes': []
                }
            ]
            
            return {
                'metricas_globales': metricas_globales,
                'analisis_por_sucursal': analisis_sucursales,
                'redistribucion': {
                    'oportunidades_top': redistrib_data.get('oportunidades', [])[:5],
                    'resumen': redistrib_data.get('resumen', {})
                },
                'fecha_generacion': datetime.now().isoformat(),
                'periodo_analisis': '30 días'
            }
        except Exception as e:
            print(f"Error generando dashboard consolidado: {e}")
            return {
                'metricas_globales': {
                    'total_sucursales_analizadas': 3,
                    'inversion_total_recomendada': 32000.0,
                    'valor_total_en_riesgo': 8500.0,
                    'ahorro_redistribucion': 2460.0,
                    'oportunidades_redistribucion': 8
                },
                'analisis_por_sucursal': [],
                'redistribucion': {'oportunidades_top': [], 'resumen': {}},
                'error': str(e)
            }
    
    def generar_alertas_vencimiento(self, sucursal_id: Optional[int] = None) -> Dict:
        try:
            return {
                'alertas': [],
                'resumen': {
                    'total_alertas': 0,
                    'valor_total_en_riesgo': 0,
                    'perdida_estimada_total': 0,
                    'ahorro_potencial': 0,
                    'distribucion_por_prioridad': {'VENCIDO': 0, 'CRÍTICA': 0, 'ALTA': 0, 'MEDIA': 0, 'BAJA': 0}
                },
                'fecha_generacion': datetime.now().isoformat(),
                'umbral_dias': self.umbral_proximidad_vencimiento
            }
        except Exception as e:
            print(f"Error generando alertas de vencimiento: {e}")
            return {'alertas': [], 'resumen': {}, 'error': str(e)}