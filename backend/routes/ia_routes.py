"""
Rutas mejoradas para IA y recomendaciones inteligentes
Integra el nuevo sistema de recomendaciones con el backend existente
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta
import requests
import numpy as np
from typing import Optional, Dict, List
import logging

# Importar el nuevo sistema de recomendaciones inteligentes
from utils.recomendaciones_inteligentes import RecomendacionesInteligentes, generar_recomendaciones_para_sucursal

router = APIRouter()

# Configuración Supabase (mantener consistencia con main)
SUPABASE_URL = "https://etblilptaljvewsavooj.supabase.co"
SUPABASE_KEY = "REMOVED_JWT"

logger = logging.getLogger(__name__)

def get_current_tenant(x_tenant_id: Optional[str] = None) -> int:
    """Obtener tenant_id del header o usar default"""
    if x_tenant_id:
        try:
            return int(x_tenant_id)
        except ValueError:
            return 1
    return 1

@router.get("/recomendaciones/compras/inteligentes")
async def get_recomendaciones_inteligentes(
    sucursal_id: Optional[int] = Query(None, description="ID de sucursal específica"),
    tenant_id: int = Depends(get_current_tenant),
    incluir_detalles: bool = Query(True, description="Incluir detalles de cálculo"),
    solo_criticas: bool = Query(False, description="Solo mostrar recomendaciones críticas")
):
    """
    Generar recomendaciones inteligentes de compra con algoritmos avanzados
    
    - **sucursal_id**: Filtrar por sucursal específica (opcional)
    - **incluir_detalles**: Incluir detalles técnicos del cálculo
    - **solo_criticas**: Solo mostrar recomendaciones críticas y altas
    """
    try:
        # Crear instancia del sistema inteligente
        sistema = RecomendacionesInteligentes(SUPABASE_URL, SUPABASE_KEY, tenant_id)
        
        # Generar reporte completo
        reporte = sistema.generar_reporte_recomendaciones(sucursal_id)
        
        # Filtrar solo críticas si se solicita
        if solo_criticas:
            recomendaciones_filtradas = [
                r for r in reporte['recomendaciones'] 
                if r['prioridad'] in ['CRÍTICA', 'ALTA']
            ]
            reporte['recomendaciones'] = recomendaciones_filtradas
            
            # Recalcular estadísticas
            total = len(recomendaciones_filtradas)
            criticas = sum(1 for r in recomendaciones_filtradas if r['prioridad'] == 'CRÍTICA')
            altas = sum(1 for r in recomendaciones_filtradas if r['prioridad'] == 'ALTA')
            
            reporte['estadisticas'].update({
                'total_recomendaciones': total,
                'criticas': criticas,
                'altas': altas,
                'medias': 0,
                'bajas': 0
            })
        
        # Remover detalles técnicos si no se solicitan
        if not incluir_detalles:
            for recomendacion in reporte['recomendaciones']:
                recomendacion.pop('detalles_calculo', None)
        
        # Agregar información adicional útil
        reporte['metadatos']['algoritmo_features'] = [
            'Predicción de demanda con ML',
            'Análisis de tendencias y estacionalidad',
            'Cálculo de stock de seguridad optimizado',
            'EOQ (Economic Order Quantity)',
            'Análisis de riesgo de stockout',
            'Optimización multi-objetivo'
        ]
        
        return reporte
        
    except Exception as e:
        logger.error(f"Error generando recomendaciones inteligentes: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error generando recomendaciones inteligentes: {str(e)}"
        )

@router.get("/analisis/medicamento/{medicamento_id}/prediccion")
async def get_prediccion_medicamento(
    medicamento_id: int,
    sucursal_id: int = Query(..., description="ID de sucursal"),
    dias_prediccion: int = Query(30, description="Días a predecir"),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Análisis predictivo detallado para un medicamento específico
    """
    try:
        sistema = RecomendacionesInteligentes(SUPABASE_URL, SUPABASE_KEY, tenant_id)
        
        # Obtener datos históricos
        datos = sistema._obtener_datos_historicos()
        
        # Calcular métricas del medicamento
        metricas = sistema._calcular_metricas_medicamento(
            medicamento_id, sucursal_id, datos['ventas']
        )
        
        # Predecir demanda futura
        demanda_predicha, stock_seguridad = sistema._predecir_demanda_futura(
            metricas, dias_prediccion
        )
        
        # Obtener información actual del inventario
        inventario_actual = next(
            (inv for inv in datos['inventario'] 
             if inv.get('medicamento_id') == medicamento_id and inv.get('sucursal_id') == sucursal_id),
            {}
        )
        
        stock_actual = inventario_actual.get('stock_actual', 0)
        
        # Calcular riesgo de stockout
        riesgo_stockout = sistema._calcular_riesgo_stockout(
            stock_actual, demanda_predicha, stock_seguridad
        )
        
        # Calcular días hasta agotamiento
        dias_hasta_agotamiento = (
            int(stock_actual / metricas.dias_venta_promedio) 
            if metricas.dias_venta_promedio > 0 else 999
        )
        
        return {
            'medicamento_id': medicamento_id,
            'sucursal_id': sucursal_id,
            'stock_actual': stock_actual,
            'prediccion': {
                'demanda_estimada': round(demanda_predicha, 2),
                'stock_seguridad_recomendado': round(stock_seguridad, 2),
                'dias_prediccion': dias_prediccion,
                'riesgo_stockout': round(riesgo_stockout, 3),
                'dias_hasta_agotamiento': dias_hasta_agotamiento
            },
            'metricas_historicas': {
                'rotacion_promedio_mensual': round(metricas.rotacion_promedio, 2),
                'venta_promedio_diaria': round(metricas.dias_venta_promedio, 2),
                'factor_estacional': round(metricas.estacionalidad_factor, 2),
                'tendencia_ventas': round(metricas.tendencia_ventas, 3),
                'variabilidad_demanda': round(metricas.variabilidad_demanda, 3)
            },
            'recomendaciones': {
                'nivel_critico': riesgo_stockout > 0.7,
                'requiere_pedido_urgente': dias_hasta_agotamiento < 7,
                'pedido_sugerido': riesgo_stockout > 0.3
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en análisis predictivo: {str(e)}"
        )

@router.get("/dashboard/inteligente")
async def get_dashboard_inteligente(
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Dashboard consolidado con métricas inteligentes y KPIs avanzados
    """
    try:
        sistema = RecomendacionesInteligentes(SUPABASE_URL, SUPABASE_KEY, tenant_id)
        
        # Generar recomendaciones para todas las sucursales
        reporte_completo = sistema.generar_reporte_recomendaciones()
        
        # Obtener datos adicionales
        datos = sistema._obtener_datos_historicos()
        
        # Calcular métricas globales
        total_medicamentos = len(set(inv.get('medicamento_id') for inv in datos['inventario']))
        total_sucursales = len(set(inv.get('sucursal_id') for inv in datos['inventario']))
        
        # Valor total del inventario
        valor_total = sum(
            inv.get('stock_actual', 0) * inv.get('precio_venta', 0) 
            for inv in datos['inventario']
        )
        
        # Análisis de rotación global
        medicamentos_alta_rotacion = 0
        medicamentos_baja_rotacion = 0
        
        for inv in datos['inventario']:
            metricas = sistema._calcular_metricas_medicamento(
                inv.get('medicamento_id'), inv.get('sucursal_id'), datos['ventas']
            )
            if metricas.rotacion_promedio > 50:  # Alta rotación (>50 unidades/mes)
                medicamentos_alta_rotacion += 1
            elif metricas.rotacion_promedio < 5:  # Baja rotación (<5 unidades/mes)
                medicamentos_baja_rotacion += 1
        
        # Análisis de alertas por categoría
        alertas_por_categoria = {}
        for rec in reporte_completo['recomendaciones']:
            if rec['prioridad'] in ['CRÍTICA', 'ALTA']:
                # Obtener categoría del medicamento
                medicamento = next(
                    (med for med in datos['medicamentos'] 
                     if med.get('id') == rec['medicamento_id']),
                    {}
                )
                categoria = medicamento.get('categoria', 'Sin categoría')
                alertas_por_categoria[categoria] = alertas_por_categoria.get(categoria, 0) + 1
        
        # Top 5 medicamentos con mayor riesgo
        top_riesgos = sorted(
            reporte_completo['recomendaciones'],
            key=lambda x: x['riesgo_stockout'],
            reverse=True
        )[:5]
        
        return {
            'resumen_ejecutivo': {
                'total_medicamentos': total_medicamentos,
                'total_sucursales': total_sucursales,
                'valor_inventario_total': round(valor_total, 2),
                'recomendaciones_activas': reporte_completo['estadisticas']['total_recomendaciones'],
                'alertas_criticas': reporte_completo['estadisticas']['criticas'],
                'ahorro_potencial': reporte_completo['estadisticas']['ahorro_total_estimado'],
                'riesgo_promedio_sistema': reporte_completo['estadisticas']['riesgo_promedio']
            },
            'analisis_rotacion': {
                'medicamentos_alta_rotacion': medicamentos_alta_rotacion,
                'medicamentos_baja_rotacion': medicamentos_baja_rotacion,
                'porcentaje_optimizado': round(
                    (medicamentos_alta_rotacion / max(total_medicamentos, 1)) * 100, 1
                )
            },
            'alertas_por_categoria': alertas_por_categoria,
            'top_riesgos': [
                {
                    'medicamento': item['medicamento'],
                    'sucursal': item['sucursal_nombre'],
                    'riesgo_stockout': item['riesgo_stockout'],
                    'prioridad': item['prioridad'],
                    'dias_stock': item['dias_stock_estimado']
                }
                for item in top_riesgos
            ],
            'tendencias': {
                'medicamentos_con_tendencia_alza': sum(
                    1 for rec in reporte_completo['recomendaciones']
                    if rec.get('detalles_calculo', {}).get('tendencia_ventas', 0) > 0
                ),
                'factor_estacional_promedio': round(
                    np.mean([
                        rec.get('detalles_calculo', {}).get('factor_estacional', 1.0)
                        for rec in reporte_completo['recomendaciones']
                        if rec.get('detalles_calculo')
                    ]) if reporte_completo['recomendaciones'] else 1.0, 2
                )
            },
            'kpis_inteligentes': {
                'efectividad_prediccion': reporte_completo['estadisticas']['confianza_promedio'],
                'optimizacion_inventario': min(100, 
                    100 - (reporte_completo['estadisticas']['total_recomendaciones'] / max(total_medicamentos, 1) * 100)
                ),
                'nivel_servicio_estimado': round((1 - reporte_completo['estadisticas']['riesgo_promedio']) * 100, 1)
            },
            'metadatos': {
                'tenant_id': tenant_id,
                'fecha_generacion': datetime.now().isoformat(),
                'version_algoritmo': '2.0',
                'datos_analizados': {
                    'dias_historial': sistema.DIAS_HISTORIAL,
                    'registros_ventas': len(datos['ventas']),
                    'items_inventario': len(datos['inventario'])
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error generando dashboard inteligente: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generando dashboard inteligente: {str(e)}"
        )

@router.get("/optimizacion/redistribucion")
async def get_recomendaciones_redistribucion(
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Análisis inteligente para redistribución óptima entre sucursales
    """
    try:
        sistema = RecomendacionesInteligentes(SUPABASE_URL, SUPABASE_KEY, tenant_id)
        datos = sistema._obtener_datos_historicos()
        
        # Agrupar inventario por medicamento
        inventario_por_medicamento = {}
        for inv in datos['inventario']:
            med_id = inv.get('medicamento_id')
            if med_id not in inventario_por_medicamento:
                inventario_por_medicamento[med_id] = []
            inventario_por_medicamento[med_id].append(inv)
        
        recomendaciones_redistribucion = []
        
        for med_id, ubicaciones in inventario_por_medicamento.items():
            if len(ubicaciones) < 2:  # Necesita al menos 2 sucursales
                continue
            
            # Calcular métricas para cada ubicación
            ubicaciones_con_metricas = []
            for ubicacion in ubicaciones:
                metricas = sistema._calcular_metricas_medicamento(
                    med_id, ubicacion.get('sucursal_id'), datos['ventas']
                )
                
                # Calcular necesidad vs disponibilidad
                demanda_predicha, stock_seguridad = sistema._predecir_demanda_futura(metricas)
                stock_actual = ubicacion.get('stock_actual', 0)
                stock_necesario = demanda_predicha + stock_seguridad
                
                ubicaciones_con_metricas.append({
                    'sucursal_id': ubicacion.get('sucursal_id'),
                    'sucursal_nombre': ubicacion.get('sucursal_nombre'),
                    'stock_actual': stock_actual,
                    'stock_necesario': stock_necesario,
                    'exceso_deficit': stock_actual - stock_necesario,
                    'rotacion': metricas.rotacion_promedio,
                    'medicamento_nombre': ubicacion.get('nombre'),
                    'sku': ubicacion.get('sku')
                })
            
            # Identificar oportunidades de redistribución
            exceso_total = sum(max(0, ub['exceso_deficit']) for ub in ubicaciones_con_metricas)
            deficit_total = sum(abs(min(0, ub['exceso_deficit'])) for ub in ubicaciones_con_metricas)
            
            if exceso_total > 10 and deficit_total > 5:  # Umbrales mínimos
                # Encontrar mejores movimientos
                origen = max(ubicaciones_con_metricas, key=lambda x: x['exceso_deficit'])
                destino = min(ubicaciones_con_metricas, key=lambda x: x['exceso_deficit'])
                
                if origen['exceso_deficit'] > 10 and destino['exceso_deficit'] < -5:
                    cantidad_sugerida = min(
                        int(origen['exceso_deficit'] * 0.8),  # 80% del exceso
                        abs(int(destino['exceso_deficit']))   # Lo que necesita el destino
                    )
                    
                    recomendaciones_redistribucion.append({
                        'medicamento_id': med_id,
                        'medicamento_nombre': origen['medicamento_nombre'],
                        'sku': origen['sku'],
                        'sucursal_origen': {
                            'id': origen['sucursal_id'],
                            'nombre': origen['sucursal_nombre'],
                            'stock_actual': origen['stock_actual'],
                            'exceso': int(origen['exceso_deficit'])
                        },
                        'sucursal_destino': {
                            'id': destino['sucursal_id'],
                            'nombre': destino['sucursal_nombre'],
                            'stock_actual': destino['stock_actual'],
                            'deficit': abs(int(destino['exceso_deficit']))
                        },
                        'cantidad_sugerida': cantidad_sugerida,
                        'beneficio_estimado': cantidad_sugerida * 0.1,  # Estimación de beneficio
                        'urgencia': 'ALTA' if abs(destino['exceso_deficit']) > 20 else 'MEDIA'
                    })
        
        # Ordenar por urgencia y beneficio
        recomendaciones_redistribucion.sort(
            key=lambda x: (
                0 if x['urgencia'] == 'ALTA' else 1,
                -x['beneficio_estimado']
            )
        )
        
        return {
            'recomendaciones_redistribucion': recomendaciones_redistribucion[:20],  # Top 20
            'resumen': {
                'total_oportunidades': len(recomendaciones_redistribucion),
                'beneficio_total_estimado': sum(r['beneficio_estimado'] for r in recomendaciones_redistribucion),
                'transferencias_urgentes': sum(1 for r in recomendaciones_redistribucion if r['urgencia'] == 'ALTA')
            },
            'metadatos': {
                'tenant_id': tenant_id,
                'fecha_analisis': datetime.now().isoformat(),
                'medicamentos_analizados': len(inventario_por_medicamento)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en análisis de redistribución: {str(e)}"
        )

@router.get("/alertas/vencimientos/inteligentes")
async def get_alertas_vencimiento_inteligentes(
    sucursal_id: Optional[int] = Query(None),
    dias_adelanto: int = Query(30, description="Días de adelanto para alertas"),
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Alertas inteligentes de vencimiento con priorización por impacto
    """
    try:
        sistema = RecomendacionesInteligentes(SUPABASE_URL, SUPABASE_KEY, tenant_id)
        datos = sistema._obtener_datos_historicos()
        
        fecha_limite = datetime.now() + timedelta(days=dias_adelanto)
        
        # Filtrar lotes próximos a vencer
        lotes_filtrados = datos['lotes']
        if sucursal_id:
            lotes_filtrados = [l for l in lotes_filtrados if l.get('sucursal_id') == sucursal_id]
        
        alertas_inteligentes = []
        
        for lote in lotes_filtrados:
            try:
                fecha_venc = datetime.fromisoformat(lote.get('fecha_vencimiento', '2099-12-31'))
                
                if fecha_venc <= fecha_limite:
                    # Calcular métricas del medicamento
                    metricas = sistema._calcular_metricas_medicamento(
                        lote.get('medicamento_id'), lote.get('sucursal_id'), datos['ventas']
                    )
                    
                    # Obtener información del medicamento
                    medicamento = next(
                        (med for med in datos['medicamentos'] 
                         if med.get('id') == lote.get('medicamento_id')),
                        {}
                    )
                    
                    cantidad_actual = lote.get('cantidad_actual', 0)
                    dias_restantes = (fecha_venc - datetime.now()).days
                    
                    # Calcular impacto de pérdida
                    precio_unitario = medicamento.get('precio_compra', 0)
                    valor_perdida = cantidad_actual * precio_unitario
                    
                    # Probabilidad de venta antes del vencimiento
                    if metricas.dias_venta_promedio > 0:
                        probabilidad_venta = min(1.0, 
                            (dias_restantes * metricas.dias_venta_promedio) / cantidad_actual
                        )
                    else:
                        probabilidad_venta = 0.1
                    
                    # Calcular prioridad inteligente
                    if dias_restantes <= 7 and valor_perdida > 100:
                        prioridad = 'CRÍTICA'
                    elif dias_restantes <= 14 and (valor_perdida > 50 or metricas.rotacion_promedio < 5):
                        prioridad = 'ALTA'
                    elif dias_restantes <= 21:
                        prioridad = 'MEDIA'
                    else:
                        prioridad = 'BAJA'
                    
                    # Generar recomendaciones específicas
                    recomendaciones = []
                    if probabilidad_venta > 0.7:
                        recomendaciones.append("Promoción para acelerar ventas")
                    elif probabilidad_venta > 0.3:
                        recomendaciones.append("Redistribución a sucursal con mayor demanda")
                    else:
                        recomendaciones.append("Considerar devolución a proveedor")
                    
                    if metricas.rotacion_promedio > 20:
                        recomendaciones.append("Producto de alta rotación - priorizar")
                    
                    alertas_inteligentes.append({
                        'lote_id': lote.get('id'),
                        'numero_lote': lote.get('numero_lote'),
                        'medicamento_id': lote.get('medicamento_id'),
                        'medicamento_nombre': medicamento.get('nombre', 'N/A'),
                        'sku': medicamento.get('sku', 'N/A'),
                        'sucursal_id': lote.get('sucursal_id'),
                        'cantidad_actual': cantidad_actual,
                        'fecha_vencimiento': fecha_venc.strftime('%Y-%m-%d'),
                        'dias_restantes': dias_restantes,
                        'valor_perdida_estimado': round(valor_perdida, 2),
                        'probabilidad_venta': round(probabilidad_venta, 2),
                        'prioridad': prioridad,
                        'recomendaciones': recomendaciones,
                        'metricas': {
                            'rotacion_mensual': round(metricas.rotacion_promedio, 1),
                            'venta_diaria_promedio': round(metricas.dias_venta_promedio, 1)
                        }
                    })
                    
            except Exception as e:
                logger.warning(f"Error procesando lote {lote.get('id')}: {e}")
                continue
        
        # Ordenar por prioridad y valor de pérdida
        orden_prioridad = {'CRÍTICA': 0, 'ALTA': 1, 'MEDIA': 2, 'BAJA': 3}
        alertas_inteligentes.sort(
            key=lambda x: (orden_prioridad[x['prioridad']], -x['valor_perdida_estimado'])
        )
        
        # Calcular estadísticas
        valor_total_riesgo = sum(a['valor_perdida_estimado'] for a in alertas_inteligentes)
        criticas = sum(1 for a in alertas_inteligentes if a['prioridad'] == 'CRÍTICA')
        
        return {
            'alertas': alertas_inteligentes,
            'resumen': {
                'total_alertas': len(alertas_inteligentes),
                'alertas_criticas': criticas,
                'alertas_altas': sum(1 for a in alertas_inteligentes if a['prioridad'] == 'ALTA'),
                'valor_total_en_riesgo': round(valor_total_riesgo, 2),
                'productos_afectados': len(set(a['medicamento_id'] for a in alertas_inteligentes))
            },
            'metadatos': {
                'tenant_id': tenant_id,
                'sucursal_id': sucursal_id,
                'dias_adelanto_configurado': dias_adelanto,
                'fecha_analisis': datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error en alertas de vencimiento inteligentes: {str(e)}"
        )

# Endpoint para retrocompatibilidad con el sistema anterior
@router.get("/recomendaciones/compras/sucursal/{sucursal_id}")
async def get_recomendaciones_compra_sucursal_legacy(
    sucursal_id: int,
    tenant_id: int = Depends(get_current_tenant)
):
    """
    Endpoint de retrocompatibilidad - redirige al sistema inteligente
    """
    try:
        return await get_recomendaciones_inteligentes(
            sucursal_id=sucursal_id,
            tenant_id=tenant_id,
            incluir_detalles=False,
            solo_criticas=False
        )
    except Exception as e:
        # Fallback al sistema básico si hay problemas
        return {
            'recomendaciones': [
                {
                    'medicamento_id': 1,
                    'medicamento': 'Paracetamol 500mg',
                    'sku': '010.000.0104',
                    'cantidad_recomendada': 100,
                    'prioridad': 'MEDIA',
                    'motivo': 'Sistema en modo fallback'
                }
            ],
            'estadisticas': {
                'total_recomendaciones': 1,
                'criticas': 0,
                'altas': 0
            },
            'metadatos': {
                'tenant_id': tenant_id,
                'modo': 'fallback',
                'error': str(e)
            }
        }