# backend/utils/prediccion_multi_sucursal.py
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import requests

class PrediccionMultiSucursal:
    def __init__(self):
        # Factores estacionales específicos para México
        self.factores_estacionales = {
            1: 1.3,    # Enero - Post-fiestas, gripe
            2: 1.2,    # Febrero - Gripe  
            3: 0.9,    # Marzo - Normal
            4: 0.8,    # Abril - Semana Santa
            5: 1.0,    # Mayo - Día de las madres
            6: 0.9,    # Junio - Normal
            7: 0.8,    # Julio - Vacaciones
            8: 1.1,    # Agosto - Regreso a clases
            9: 1.0,    # Septiembre - Normal
            10: 1.2,   # Octubre - Inicio temporada gripe
            11: 1.1,   # Noviembre - Temporada gripe
            12: 0.7    # Diciembre - Vacaciones
        }
        
        # Factores por tipo de sucursal
        self.factores_sucursal = {
            'Principal': 1.2,    # Sucursal principal tiene más demanda
            'Sucursal': 1.0,     # Sucursales normales
            'Especializada': 1.4  # Clínicas especializadas
        }
        
        # Factores por categoría de medicamento
        self.factores_categoria = {
            'Analgésicos': 1.3,        # Alta demanda constante
            'Antibióticos': 0.8,       # Controlados, menor rotación
            'Diabetes': 1.1,           # Medicamentos crónicos
            'Cardiovascular': 1.0,     # Demanda estable
            'Antiinflamatorios': 1.2,  # Alta demanda
            'Gastroprotectores': 0.9   # Demanda media
        }
    
    def simular_ventas_historicas(self, medicamento_data: Dict, sucursal_data: Dict, meses_historia: int = 6) -> List[Dict]:
        """
        Simula ventas históricas basadas en características del medicamento y sucursal
        En producción esto vendría de datos reales de ventas
        """
        ventas = []
        base_ventas = medicamento_data.get('stock_actual', 50) * 0.15  # 15% del stock como base
        
        for i in range(meses_historia):
            fecha = datetime.now() - timedelta(days=30 * (meses_historia - i))
            mes = fecha.month
            
            # Aplicar factores
            factor_estacional = self.factores_estacionales.get(mes, 1.0)
            factor_sucursal = self.factores_sucursal.get(sucursal_data.get('tipo', 'Sucursal'), 1.0)
            factor_categoria = self.factores_categoria.get(medicamento_data.get('categoria', 'Otros'), 1.0)
            
            # Agregar variabilidad aleatoria
            variabilidad = np.random.normal(1.0, 0.2)  # ±20% variabilidad
            
            cantidad_vendida = int(base_ventas * factor_estacional * factor_sucursal * factor_categoria * variabilidad)
            cantidad_vendida = max(1, cantidad_vendida)  # Mínimo 1
            
            ventas.append({
                'fecha': fecha.strftime('%Y-%m-%d'),
                'cantidad': cantidad_vendida,
                'mes': mes,
                'medicamento_sku': medicamento_data.get('sku'),
                'sucursal_id': sucursal_data.get('id')
            })
        
        return ventas
    
    def predecir_demanda_mensual(self, medicamento_data: Dict, sucursal_data: Dict, mes_prediccion: int = None) -> Dict:
        """
        Predice la demanda mensual de un medicamento en una sucursal específica
        """
        if mes_prediccion is None:
            mes_prediccion = datetime.now().month
        
        # Simular ventas históricas
        ventas_historicas = self.simular_ventas_historicas(medicamento_data, sucursal_data)
        
        # Calcular demanda base promedio
        demanda_base = np.mean([v['cantidad'] for v in ventas_historicas])
        
        # Aplicar factores para el mes de predicción
        factor_estacional = self.factores_estacionales.get(mes_prediccion, 1.0)
        factor_sucursal = self.factores_sucursal.get(sucursal_data.get('tipo', 'Sucursal'), 1.0)
        factor_categoria = self.factores_categoria.get(medicamento_data.get('categoria', 'Otros'), 1.0)
        
        # Calcular predicción
        demanda_predicha = demanda_base * factor_estacional * factor_sucursal * factor_categoria
        
        # Calcular intervalo de confianza
        std_historica = np.std([v['cantidad'] for v in ventas_historicas])
        intervalo_inferior = max(1, demanda_predicha - (1.96 * std_historica))  # 95% confianza
        intervalo_superior = demanda_predicha + (1.96 * std_historica)
        
        return {
            'medicamento_sku': medicamento_data.get('sku'),
            'medicamento_nombre': medicamento_data.get('nombre'),
            'sucursal_id': sucursal_data.get('id'),
            'sucursal_nombre': sucursal_data.get('nombre'),
            'mes_prediccion': mes_prediccion,
            'demanda_predicha': round(demanda_predicha, 1),
            'demanda_base': round(demanda_base, 1),
            'factor_estacional': factor_estacional,
            'factor_sucursal': factor_sucursal,
            'factor_categoria': factor_categoria,
            'intervalo_confianza': {
                'inferior': round(intervalo_inferior, 1),
                'superior': round(intervalo_superior, 1)
            },
            'recomendacion_compra': round(demanda_predicha * 1.3, 0),  # 30% buffer
            'ventas_historicas': ventas_historicas
        }
    
    def calcular_punto_reorden_inteligente(self, medicamento_data: Dict, sucursal_data: Dict) -> Dict:
        """
        Calcula punto de reorden inteligente considerando predicción de demanda
        """
        prediccion = self.predecir_demanda_mensual(medicamento_data, sucursal_data)
        
        # Parámetros de gestión de inventario
        tiempo_entrega_dias = 7  # Tiempo promedio de reabastecimiento
        nivel_servicio = 0.95    # 95% nivel de servicio
        
        # Demanda durante tiempo de entrega
        demanda_mensual = prediccion['demanda_predicha']
        demanda_diaria = demanda_mensual / 30
        demanda_tiempo_entrega = demanda_diaria * tiempo_entrega_dias
        
        # Stock de seguridad considerando variabilidad
        ventas_historicas = [v['cantidad'] for v in prediccion['ventas_historicas']]
        std_demanda = np.std(ventas_historicas) / 30 * tiempo_entrega_dias  # Std diaria
        from scipy import stats
        z_score = stats.norm.ppf(nivel_servicio)
        stock_seguridad = z_score * std_demanda
        
        # Punto de reorden
        punto_reorden = demanda_tiempo_entrega + stock_seguridad
        
        return {
            'medicamento_sku': medicamento_data.get('sku'),
            'sucursal_id': sucursal_data.get('id'),
            'punto_reorden_actual': medicamento_data.get('stock_minimo', 10),
            'punto_reorden_recomendado': round(punto_reorden),
            'stock_seguridad': round(stock_seguridad),
            'demanda_tiempo_entrega': round(demanda_tiempo_entrega),
            'mejora_propuesta': round(punto_reorden) - medicamento_data.get('stock_minimo', 10),
            'nivel_servicio': nivel_servicio * 100,
            'tiempo_entrega_dias': tiempo_entrega_dias
        }
    
    def analizar_redistribucion_inteligente(self, inventario_consolidado: List[Dict], sucursales: List[Dict]) -> List[Dict]:
        """
        Analiza oportunidades de redistribución de inventario entre sucursales
        """
        recomendaciones = []
        
        # Agrupar inventario por SKU
        inventario_por_sku = {}
        for item in inventario_consolidado:
            sku = item['sku']
            if sku not in inventario_por_sku:
                inventario_por_sku[sku] = []
            inventario_por_sku[sku].append(item)
        
        # Analizar cada SKU
        for sku, items in inventario_por_sku.items():
            if len(items) < 2:  # Necesitamos al menos 2 sucursales para redistribuir
                continue
            
            # Encontrar sucursales con exceso y déficit
            sucursales_exceso = []
            sucursales_deficit = []
            
            for item in items:
                stock_actual = item['stock_actual']
                stock_minimo = item['stock_minimo']
                ratio_stock = stock_actual / max(stock_minimo, 1)
                
                if stock_actual <= stock_minimo:
                    sucursales_deficit.append({
                        **item,
                        'deficit': stock_minimo - stock_actual,
                        'ratio': ratio_stock
                    })
                elif ratio_stock > 2.0:  # Más del 200% del mínimo
                    exceso = stock_actual - (stock_minimo * 1.5)  # Mantener 150% como buffer
                    if exceso > 0:
                        sucursales_exceso.append({
                            **item,
                            'exceso': int(exceso),
                            'ratio': ratio_stock
                        })
            
            # Crear recomendaciones de redistribución
            for deficit in sucursales_deficit:
                for exceso in sucursales_exceso:
                    if exceso['exceso'] > 0 and deficit['deficit'] > 0:
                        cantidad_transferir = min(exceso['exceso'], deficit['deficit'])
                        
                        if cantidad_transferir >= 5:  # Mínimo transferible
                            recomendaciones.append({
                                'sku': sku,
                                'medicamento_nombre': deficit['nombre'],
                                'sucursal_origen': exceso['sucursal_nombre'],
                                'sucursal_destino': deficit['sucursal_nombre'],
                                'cantidad_transferir': cantidad_transferir,
                                'stock_origen_actual': exceso['stock_actual'],
                                'stock_destino_actual': deficit['stock_actual'],
                                'deficit_destino': deficit['deficit'],
                                'exceso_origen': exceso['exceso'],
                                'prioridad': 'ALTA' if deficit['ratio'] < 0.5 else 'MEDIA',
                                'valor_transferencia': cantidad_transferir * deficit['precio_venta'],
                                'ahorro_estimado': cantidad_transferir * deficit['precio_compra'] * 0.1  # 10% ahorro vs compra nueva
                            })
                            
                            # Actualizar para próximas iteraciones
                            exceso['exceso'] -= cantidad_transferir
                            deficit['deficit'] -= cantidad_transferir
        
        # Ordenar por prioridad y valor
        recomendaciones.sort(key=lambda x: (
            0 if x['prioridad'] == 'ALTA' else 1,
            -x['valor_transferencia']
        ))
        
        return recomendaciones