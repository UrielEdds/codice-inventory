class RecomendacionesInteligentes:
    def __init__(self, supabase_url, supabase_key):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
    
    def generar_recomendaciones_compra(self, sucursal_id):
        return {
            "recomendaciones": [
                {
                    "medicamento_nombre": "Paracetamol 500mg",
                    "cantidad_recomendada": 100,
                    "prioridad": "ALTA",
                    "costo_compra": 850.0,
                    "roi_estimado": 45.5,
                    "demanda_predicha_mensual": 80.0,
                    "stock_actual": 20
                }
            ],
            "resumen": {
                "total_recomendaciones": 1,
                "criticas": 0,
                "inversion_total": 850.0,
                "roi_promedio": 45.5
            }
        }
    
    def generar_recomendaciones_redistribucion(self):
        return {
            "oportunidades": [
                {
                    "medicamento_nombre": "Ibuprofeno 400mg",
                    "sucursal_origen_nombre": "Clínica Norte",
                    "sucursal_destino_nombre": "Clínica Sur",
                    "cantidad_transferir": 50,
                    "ahorro_estimado": 676.0,
                    "roi_transferencia": 42.3,
                    "distancia_km": 15,
                    "urgencia": "ALTA",
                    "justificacion": "Clínica Sur tiene stock crítico mientras Norte tiene exceso"
                }
            ],
            "resumen": {
                "ahorro_total": 676.0,
                "valor_total": 1500.0,
                "roi_promedio": 42.3
            }
        }
    
    def generar_dashboard_consolidado(self):
        return {
            "metricas_globales": {
                "inversion_total_recomendada": 32000.0,
                "valor_total_en_riesgo": 8500.0,
                "ahorro_redistribucion": 676.0,
                "total_sucursales_analizadas": 3
            },
            "analisis_por_sucursal": [
                {
                    "sucursal_nombre": "Clínica Norte",
                    "total_medicamentos": 15,
                    "alertas_criticas_count": 2,
                    "valor_inventario_total": 25000.0,
                    "recomendaciones_compra_criticas": [
                        {
                            "medicamento_nombre": "Paracetamol 500mg",
                            "cantidad_recomendada": 100
                        }
                    ]
                }
            ]
        }
    
    def generar_alertas_vencimiento(self, sucursal_id=None):
        return {
            "alertas": [
                {
                    "medicamento_nombre": "Aspirina 100mg",
                    "sucursal_nombre": "Clínica Centro",
                    "fecha_vencimiento": "2025-08-15",
                    "dias_restantes": 29,
                    "cantidad_afectada": 50,
                    "valor_riesgo": 750.0,
                    "prioridad": "ALTA"
                }
            ],
            "resumen": {
                "total_alertas": 1,
                "criticas": 1,
                "valor_en_riesgo": 750.0
            }
        }