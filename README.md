\# 🏥 Códice Inventory



\## Sistema de Inventario Farmacéutico Inteligente



Un sistema completo de gestión de inventario farmacéutico con capacidades de inteligencia artificial, análisis predictivo y gestión multi-sucursal en tiempo real.



!\[Códice Inventory](https://img.shields.io/badge/Version-1.0.0-blue)

!\[Python](https://img.shields.io/badge/Python-3.8+-green)

!\[FastAPI](https://img.shields.io/badge/FastAPI-0.104+-red)

!\[Streamlit](https://img.shields.io/badge/Streamlit-1.28+-orange)

!\[Supabase](https://img.shields.io/badge/Database-Supabase-teal)



---



\## 🎯 \*\*Características Principales\*\*



\### 🏥 \*\*Multi-Sucursal\*\*

\- Gestión centralizada de múltiples sucursales farmacéuticas

\- Sincronización en tiempo real entre ubicaciones

\- Control de inventario independiente por sucursal



\### 🤖 \*\*Inteligencia Artificial\*\*

\- Predicción de demanda utilizando algoritmos avanzados

\- Alertas automáticas de stock bajo

\- Optimización de redistribución entre sucursales

\- Análisis de tendencias de consumo



\### 📊 \*\*Dashboard Ejecutivo\*\*

\- Métricas en tiempo real

\- Reportes automáticos

\- Visualizaciones interactivas

\- Análisis de rendimiento por sucursal



\### 📋 \*\*Gestión Completa\*\*

\- Control de medicamentos y lotes

\- Seguimiento de fechas de vencimiento

\- Registro de entradas y salidas

\- Trazabilidad completa del inventario



---



\## 🛠️ \*\*Tecnologías Utilizadas\*\*



\### \*\*Backend\*\*

\- \*\*FastAPI\*\* - API REST de alto rendimiento

\- \*\*Python 3.8+\*\* - Lenguaje principal

\- \*\*Pydantic\*\* - Validación de datos

\- \*\*Pandas\*\* - Análisis de datos

\- \*\*Uvicorn\*\* - Servidor ASGI



\### \*\*Frontend\*\*

\- \*\*Streamlit\*\* - Interfaz web interactiva

\- \*\*Plotly\*\* - Visualizaciones dinámicas

\- \*\*CSS3\*\* - Diseño personalizado



\### \*\*Base de Datos\*\*

\- \*\*Supabase\*\* - PostgreSQL como servicio

\- \*\*SQL\*\* - Consultas optimizadas

\- \*\*Views materializadas\*\* - Performance mejorada



\### \*\*Deploy\*\*

\- \*\*Railway\*\* - Backend en la nube

\- \*\*Streamlit Cloud\*\* - Frontend público

\- \*\*GitHub Actions\*\* - CI/CD automático



---



\## 📁 \*\*Estructura del Proyecto\*\*



```

codice-inventory/

├── backend/                    # API Backend

│   ├── main.py                # Aplicación FastAPI principal

│   ├── requirements.txt       # Dependencias Python

│   └── Procfile              # Configuración Railway

├── frontend/                   # Dashboard Frontend

│   ├── dashboard.py           # Aplicación Streamlit

│   ├── requirements.txt       # Dependencias frontend

│   ├── .streamlit/           # Configuración Streamlit

│   └── assets/               # Recursos estáticos

├── docs/                      # Documentación

├── tests/                     # Pruebas automatizadas

└── README.md                  # Documentación principal

```



---



\## 🚀 \*\*Instalación y Configuración\*\*



\### \*\*Prerequisitos\*\*

\- Python 3.8 o superior

\- Git

\- Cuenta en Supabase

\- Cuenta en Railway (opcional)



\### \*\*1. Clonar el Repositorio\*\*

```bash

git clone https://github.com/UrielEdds/codice-inventory.git

cd codice-inventory

```



\### \*\*2. Configurar Backend\*\*

```bash

cd backend

pip install -r requirements.txt

```



\*\*Crear archivo `.env`:\*\*

```env

SUPABASE\_URL=https://tu-proyecto.supabase.co

SUPABASE\_KEY=tu\_anon\_key

PORT=8000

```



\*\*Ejecutar API:\*\*

```bash

python main.py

```



\### \*\*3. Configurar Frontend\*\*

```bash

cd ../frontend

pip install -r requirements.txt

```



\*\*Crear archivo `.env`:\*\*

```env

BACKEND\_URL=http://localhost:8000

```



\*\*Ejecutar Dashboard:\*\*

```bash

streamlit run dashboard.py

```



---



\## 📊 \*\*Funcionalidades del Sistema\*\*



\### \*\*📈 Dashboard Principal\*\*

\- Métricas generales del inventario

\- Gráficos de tendencias

\- Alertas de stock crítico

\- Resumen por sucursales



\### \*\*📋 Inventario Detallado\*\*

\- Listado completo de medicamentos

\- Filtros avanzados por categoría

\- Estados de stock en tiempo real

\- Información de proveedores



\### \*\*🤖 IA \& Predicciones\*\*

\- Algoritmos de predicción de demanda

\- Sugerencias de redistribución

\- Análisis de patrones de consumo

\- Optimización automática



\### \*\*📥 Ingreso de Inventario\*\*

\- Registro de nuevos medicamentos

\- Control de lotes y vencimientos

\- Validaciones automáticas

\- Actualización en tiempo real



\### \*\*📈 Análisis Avanzado\*\*

\- Reportes personalizados

\- Análisis de tendencias

\- Comparativas entre sucursales

\- Métricas de rendimiento



\### \*\*📤 Salidas de Inventario\*\*

\- Registro de ventas y transferencias

\- Sistema de carrito para múltiples salidas

\- Tipos de salida configurables

\- Actualización automática de stock



---



\## 🗃️ \*\*Modelo de Base de Datos\*\*



\### \*\*Tablas Principales\*\*

\- \*\*`sucursales`\*\* - Información de sucursales

\- \*\*`medicamentos`\*\* - Catálogo de medicamentos

\- \*\*`inventario`\*\* - Stock por sucursal

\- \*\*`lotes\_inventario`\*\* - Control de lotes

\- \*\*`salidas\_inventario`\*\* - Registro de movimientos



\### \*\*Vistas Optimizadas\*\*

\- \*\*`vista\_inventario\_completo`\*\* - Join optimizado

\- \*\*`vista\_salidas\_completo`\*\* - Historial completo

\- \*\*`mv\_metricas\_sucursales`\*\* - Métricas en caché



---



\## 🎯 \*\*APIs Disponibles\*\*



\### \*\*Base URL:\*\* `https://api.codice-inventory.com`



\#### \*\*Medicamentos\*\*

\- `GET /medicamentos` - Listar medicamentos

\- `POST /medicamentos` - Crear medicamento

\- `GET /medicamentos/{id}` - Obtener medicamento específico



\#### \*\*Inventario\*\*

\- `GET /inventario` - Inventario completo

\- `GET /inventario/sucursal/{id}` - Por sucursal

\- `POST /inventario` - Agregar stock



\#### \*\*Salidas\*\*

\- `GET /salidas` - Historial de salidas

\- `POST /salidas` - Registrar salida

\- `POST /salidas/lote` - Múltiples salidas



\#### \*\*Métricas\*\*

\- `GET /dashboard/metricas/sucursal/{id}` - Métricas por sucursal

\- `GET /analytics/tendencias` - Análisis de tendencias



---



\## 🔧 \*\*Configuración Avanzada\*\*



\### \*\*Variables de Entorno\*\*



\#### \*\*Backend (.env)\*\*

```env

SUPABASE\_URL=https://tu-proyecto.supabase.co

SUPABASE\_KEY=tu\_anon\_key

SUPABASE\_SECRET=tu\_secret\_key

PORT=8000

ENVIRONMENT=production

DEBUG=False

```



\#### \*\*Frontend (.env)\*\*

```env

BACKEND\_URL=https://api.codice-inventory.com

STREAMLIT\_SERVER\_PORT=8501

STREAMLIT\_SERVER\_ADDRESS=0.0.0.0

```



\### \*\*Configuración de Supabase\*\*



\#### \*\*Row Level Security (RLS)\*\*

```sql

-- Habilitar RLS en todas las tablas

ALTER TABLE medicamentos ENABLE ROW LEVEL SECURITY;

ALTER TABLE inventario ENABLE ROW LEVEL SECURITY;

ALTER TABLE salidas\_inventario ENABLE ROW LEVEL SECURITY;

```



\#### \*\*Índices de Performance\*\*

```sql

-- Índices optimizados para consultas frecuentes

CREATE INDEX idx\_inventario\_sucursal\_stock ON inventario(sucursal\_id, stock\_actual);

CREATE INDEX idx\_lotes\_medicamento\_sucursal ON lotes\_inventario(medicamento\_id, sucursal\_id);

CREATE INDEX idx\_salidas\_fecha ON salidas\_inventario(fecha\_salida DESC);

```



---



\## 🧪 \*\*Testing\*\*



\### \*\*Ejecutar Pruebas\*\*

```bash

\# Backend tests

cd backend

python -m pytest tests/ -v



\# Frontend tests  

cd frontend

python -m pytest tests/ -v

```



\### \*\*Cobertura de Código\*\*

```bash

coverage run -m pytest tests/

coverage report

coverage html

```



---



\## 📦 \*\*Deploy en Producción\*\*



\### \*\*1. Deploy Backend (Railway)\*\*

1\. Conectar repositorio a Railway

2\. Configurar variables de entorno

3\. Deploy automático desde `main` branch



\### \*\*2. Deploy Frontend (Streamlit Cloud)\*\*

1\. Conectar repositorio a Streamlit Cloud

2\. Configurar `frontend/dashboard.py` como main file

3\. Configurar variables de entorno



\### \*\*3. Dominio Personalizado (Opcional)\*\*

```bash

\# Configurar CNAME records

api.codice-inventory.com -> railway-app-url

app.codice-inventory.com -> streamlit-app-url

```



---



\## 🔒 \*\*Seguridad\*\*



\### \*\*Autenticación\*\*

\- API Keys para acceso a endpoints

\- Row Level Security en Supabase

\- CORS configurado para dominios específicos



\### \*\*Validación de Datos\*\*

\- Pydantic models para validación

\- Sanitización de inputs

\- Validación de tipos SQL



\### \*\*Backup y Recuperación\*\*

\- Backups automáticos en Supabase

\- Exportación de datos en formato JSON

\- Restauración punto en el tiempo



---



\## 📈 \*\*Roadmap y Mejoras Futuras\*\*



\### \*\*Versión 1.1\*\* (Q2 2025)

\- \[ ] Módulo de reportes en PDF

\- \[ ] Notificaciones push

\- \[ ] API de terceros (proveedores)

\- \[ ] Dashboard móvil



\### \*\*Versión 1.2\*\* (Q3 2025)

\- \[ ] Machine Learning avanzado

\- \[ ] Blockchain para trazabilidad

\- \[ ] Integración con ERPs

\- \[ ] Multi-idioma



\### \*\*Versión 2.0\*\* (Q4 2025)

\- \[ ] Microservicios

\- \[ ] GraphQL API

\- \[ ] Real-time notifications

\- \[ ] Advanced analytics



---



\## 🤝 \*\*Contribución\*\*



\### \*\*Cómo Contribuir\*\*

1\. Fork el repositorio

2\. Crear branch feature (`git checkout -b feature/nueva-funcionalidad`)

3\. Commit cambios (`git commit -am 'Agregar nueva funcionalidad'`)

4\. Push branch (`git push origin feature/nueva-funcionalidad`)

5\. Crear Pull Request



\### \*\*Estándares de Código\*\*

\- \*\*Python:\*\* PEP 8

\- \*\*Commits:\*\* Conventional Commits

\- \*\*Testing:\*\* Mínimo 80% cobertura

\- \*\*Documentación:\*\* Docstrings obligatorios



---



\## 📞 \*\*Soporte y Contacto\*\*



\### \*\*Desarrollador Principal\*\*

\- \*\*Nombre:\*\* Uriel Edds

\- \*\*GitHub:\*\* \[@UrielEdds](https://github.com/UrielEdds)

\- \*\*Email:\*\* uriel@codice-inventory.com



\### \*\*Reportar Issues\*\*

\- \[GitHub Issues](https://github.com/UrielEdds/codice-inventory/issues)

\- \[Documentación](https://docs.codice-inventory.com)

\- \[Slack Community](https://codice-inventory.slack.com)



---



\## 📄 \*\*Licencia\*\*



Este proyecto está bajo la Licencia MIT. Ver el archivo \[LICENSE](LICENSE) para más detalles.



```

MIT License



Copyright (c) 2025 Uriel Edds - Códice Inventory



Permission is hereby granted, free of charge, to any person obtaining a copy

of this software and associated documentation files (the "Software"), to deal

in the Software without restriction, including without limitation the rights

to use, copy, modify, merge, publish, distribute, sublicense, and/or sell

copies of the Software, and to permit persons to whom the Software is

furnished to do so, subject to the following conditions:



The above copyright notice and this permission notice shall be included in all

copies or substantial portions of the Software.



THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR

IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,

FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE

AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER

LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,

OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE

SOFTWARE.

```



---



\## 🙏 \*\*Agradecimientos\*\*



\- \*\*Streamlit\*\* por la increíble plataforma de desarrollo

\- \*\*FastAPI\*\* por el framework API de alta performance

\- \*\*Supabase\*\* por la base de datos como servicio

\- \*\*Railway\*\* por el hosting cloud simplificado

\- \*\*Plotly\*\* por las visualizaciones interactivas



---



\## 📊 \*\*Estadísticas del Proyecto\*\*



!\[GitHub stars](https://img.shields.io/github/stars/UrielEdds/codice-inventory?style=social)

!\[GitHub forks](https://img.shields.io/github/forks/UrielEdds/codice-inventory?style=social)

!\[GitHub watchers](https://img.shields.io/github/watchers/UrielEdds/codice-inventory?style=social)



!\[GitHub repo size](https://img.shields.io/github/repo-size/UrielEdds/codice-inventory)

!\[Lines of code](https://img.shields.io/tokei/lines/github/UrielEdds/codice-inventory)

!\[GitHub language count](https://img.shields.io/github/languages/count/UrielEdds/codice-inventory)



---



\*\*🎉 ¡Gracias por usar Códice Inventory! Transformando la gestión farmacéutica con tecnología inteligente.\*\* 



\*Desarrollado con ❤️ por Uriel Edds\*

