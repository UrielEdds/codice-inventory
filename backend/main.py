# main.py — Códice Inventory API (FastAPI)
# Objetivo: Backend estable para dashboard.py
# - Multi-tenant vía header X-Tenant-Id (default: DEFAULT_TENANT_ID)
# - Supabase PostgREST REST (/rest/v1/*) usando ANON JWT (eyJ...)
# - Endpoints CRUD + endpoints "inteligentes" consumidos por el dashboard
# - Escrituras protegidas por X-API-Secret (API_SECRET en .env)
#
# Nota: Con ANON key, INSERT/UPDATE/DELETE requieren RLS policies en Supabase.
#       (Opción A) Mantener ANON key y habilitar policies (control MVP desde backend con API_SECRET).
#
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


# ============================================================
# ENV
# ============================================================
load_dotenv()

DEFAULT_TENANT_ID = int(os.getenv("DEFAULT_TENANT_ID", "1"))

SUPABASE_URL = (os.getenv("SUPABASE_URL", "") or "").rstrip("/")

# Preferimos el JWT ANON ("eyJhbGci...") porque es el que funciona con PostgREST + RLS.
SUPABASE_KEY = (
    os.getenv("SUPABASE_ANON_KEY")
    or os.getenv("SUPABASE_KEY")
    or os.getenv("SUPABASE_ANON_KEY_LEGACY")
    or ""
).strip()

# Compatibilidad (no se usa en esta versión)
SUPABASE_SERVICE_ROLE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_SERVICE_ROLE")
    or ""
).strip()

API_SECRET = (os.getenv("API_SECRET") or "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ Falta SUPABASE_URL o SUPABASE_ANON_KEY en .env")

# Debug: no imprime secretos completos
print("SUPABASE_URL:", SUPABASE_URL)
print("SUPABASE_KEY prefix:", SUPABASE_KEY[:16])
print("ANON prefix:", SUPABASE_KEY[:12])
print("API_SECRET loaded:", bool(API_SECRET))


# ============================================================
# APP
# ============================================================
app = FastAPI(title="Códice Inventory API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod: restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODELOS
# ============================================================
class InventarioCreate(BaseModel):
    medicamento_id: int
    sucursal_id: int
    stock_actual: int = 0
    stock_minimo: int = 0


class InventarioPatch(BaseModel):
    stock_actual: Optional[int] = None
    stock_minimo: Optional[int] = None


class MedicamentoCreate(BaseModel):
    nombre: str
    sku: Optional[str] = None
    categoria: Optional[str] = None
    fabricante: Optional[str] = None
    precio_compra: Optional[float] = None
    precio_venta: Optional[float] = None
    presentacion: Optional[str] = None
    descripcion: Optional[str] = None
    # Campos "catálogo" (si existen en tabla)
    unidad: Optional[str] = None
    activo: Optional[bool] = True


class SucursalCreate(BaseModel):
    nombre: str


class LoteCreate(BaseModel):
    medicamento_id: int
    sucursal_id: int
    numero_lote: str
    fecha_vencimiento: Optional[str] = None  # YYYY-MM-DD
    cantidad_inicial: int = 0
    cantidad_actual: Optional[int] = None
    precio_compra: Optional[float] = None
    proveedor: Optional[str] = None
    fecha_ingreso: Optional[str] = None  # ISO


class SalidaLoteCreate(BaseModel):
    lote_id: int
    cantidad: int = Field(gt=0)
    tipo_salida: str = "Venta"
    observaciones: Optional[str] = None
    usuario: Optional[str] = "DEMO_SYSTEM"
    fecha_salida: Optional[str] = None  # ISO


# ============================================================
# TENANT / AUTH (backend)
# ============================================================
def get_current_tenant(x_tenant_id: Optional[str] = Header(default=None)) -> int:
    """Obtiene tenant_id desde header X-Tenant-Id."""
    if not x_tenant_id:
        return DEFAULT_TENANT_ID
    try:
        return int(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Tenant-Id debe ser un entero")


def require_api_secret(x_api_secret: Optional[str] = Header(default=None)) -> None:
    """Protege endpoints de escritura.
    - Si API_SECRET NO existe en .env => modo demo (no bloquea).
    - Si existe => requiere header X-API-Secret exacto.
    """
    if API_SECRET and x_api_secret != API_SECRET:
        raise HTTPException(status_code=401, detail="API secret inválido")


# ============================================================
# SUPABASE HELPERS (PostgREST)
# ============================================================
# Si alguna tabla NO tiene tenant_id (global), agregar aquí
TABLAS_SIN_TENANT = {"proveedores"}


def get_headers(method: str = "GET") -> Dict[str, str]:
    key = SUPABASE_KEY or ""
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if (method or "GET").upper() in ("POST", "PATCH", "PUT"):
        headers["Prefer"] = "return=representation"
    return headers


def get_supabase_url(endpoint: str, query: str = "") -> str:
    base = f"{SUPABASE_URL}/rest/v1/{endpoint}"
    return f"{base}?{query}" if query else base


def _has_tenant_filter(q: str) -> bool:
    q = q or ""
    # soporta tenant_id=eq.X y tenant_id=in.(...)
    return "tenant_id=eq." in q or "tenant_id=in." in q


def make_supabase_request(
    method: str,
    endpoint: str,
    data: Optional[Union[dict, list]] = None,
    query: str = "",
    tenant_id: Optional[int] = None,
) -> Any:
    """Petición a Supabase vía REST (PostgREST).
    - GET: inyecta tenant_id=eq.{tenant} salvo tablas globales y salvo si ya viene tenant_id en query.
    - POST/PATCH/DELETE: inyecta tenant_id en payload (si dict o lista de dicts) salvo tablas globales.
    """
    m = (method or "GET").upper()
    current_tenant_id = tenant_id or DEFAULT_TENANT_ID

    # GET: inyectar filtro tenant si aplica
    if m == "GET" and endpoint not in TABLAS_SIN_TENANT and not _has_tenant_filter(query):
        tenant_filter = f"tenant_id=eq.{current_tenant_id}"
        query = f"{query}&{tenant_filter}" if query else tenant_filter

    # Escrituras: inyectar tenant_id en payload si aplica
    if data is not None and m in ("POST", "PATCH", "PUT") and endpoint not in TABLAS_SIN_TENANT:
        if isinstance(data, dict):
            data = dict(data)
            data["tenant_id"] = current_tenant_id
        elif isinstance(data, list):
            patched = []
            for row in data:
                r = dict(row or {})
                r["tenant_id"] = current_tenant_id
                patched.append(r)
            data = patched

    url = get_supabase_url(endpoint, query)
    headers = get_headers(m)

    print(f"🔍 REQUEST: {m} {endpoint} | {url}")

    try:
        if m == "GET":
            r = requests.get(url, headers=headers, timeout=20)
        elif m == "POST":
            r = requests.post(url, headers=headers, json=data, timeout=20)
        elif m == "PATCH":
            r = requests.patch(url, headers=headers, json=data, timeout=20)
        elif m == "PUT":
            r = requests.put(url, headers=headers, json=data, timeout=20)
        elif m == "DELETE":
            r = requests.delete(url, headers=headers, timeout=20)
        else:
            raise ValueError(f"Método no soportado: {method}")

        print(f"📊 RESPONSE: {r.status_code}")

        if r.status_code in (200, 201, 204):
            if not r.text:
                return {"success": True}
            try:
                return r.json()
            except Exception:
                return r.text

        # error
        try:
            body = r.json()
        except Exception:
            body = {"message": r.text[:600]}

        return {
            "error": True,
            "status_code": r.status_code,
            "message": body,
            "endpoint": endpoint,
            "method": m,
            "url": url,
            "tenant_id": current_tenant_id,
        }

    except requests.RequestException as e:
        return {
            "error": True,
            "status_code": 0,
            "message": str(e),
            "endpoint": endpoint,
            "method": m,
            "url": url,
            "tenant_id": current_tenant_id,
        }


def _raise_if_supabase_error(resp: Any) -> None:
    if isinstance(resp, dict) and resp.get("error"):
        sc = int(resp.get("status_code") or 502)
        detail = {"supabase_error": resp.get("message"), "url": resp.get("url")}
        raise HTTPException(status_code=502 if sc == 0 else sc, detail=detail)


# ============================================================
# UTILS
# ============================================================
def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except Exception:
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        if x is None:
            return default
        return int(float(x))
    except Exception:
        return default


def _parse_date_yyyy_mm_dd(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except Exception:
        return None


# ============================================================
# HEALTH / DEBUG
# ============================================================
@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/debug/supabase")
async def debug_supabase(tenant_id: int = Depends(get_current_tenant)):
    """Prueba rápida (limit=1) de endpoints base."""
    endpoints = [
        ("inventario", "limit=1"),
        ("medicamentos", "limit=1"),
        ("sucursales", "limit=1"),
        ("vista_inventario_completo", "limit=1"),
        ("lotes_inventario", "limit=1"),
        ("promociones", "limit=1"),
    ]
    out: Dict[str, Any] = {}
    for ep, q in endpoints:
        r = make_supabase_request("GET", ep, query=q, tenant_id=tenant_id)
        if isinstance(r, dict) and r.get("error"):
            out[ep] = {"ok": False, "status_code": r.get("status_code"), "message": r.get("message")}
        else:
            out[ep] = {"ok": True, "sample": (r[:1] if isinstance(r, list) else r)}
    return out


# ============================================================
# CRUD: MEDICAMENTOS (PRODUCTOS)
# ============================================================
@app.get("/medicamentos")
async def get_medicamentos(tenant_id: int = Depends(get_current_tenant)):
    data = make_supabase_request("GET", "medicamentos", query="order=nombre.asc", tenant_id=tenant_id)
    _raise_if_supabase_error(data)
    return data or []


@app.post("/medicamentos")
async def create_medicamento(
    payload: MedicamentoCreate,
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    data = make_supabase_request("POST", "medicamentos", data=payload.model_dump(), tenant_id=tenant_id)
    _raise_if_supabase_error(data)
    return data


@app.patch("/medicamentos/{medicamento_id}")
async def update_medicamento(
    medicamento_id: int,
    payload: Dict[str, Any],
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    data = dict(payload or {})
    if not data:
        raise HTTPException(status_code=400, detail="Payload vacío")
    data.pop("id", None)
    data.pop("tenant_id", None)

    resp = make_supabase_request(
        "PATCH",
        "medicamentos",
        data=data,
        query=f"id=eq.{int(medicamento_id)}",
        tenant_id=tenant_id,
    )
    _raise_if_supabase_error(resp)
    if isinstance(resp, list) and resp:
        return resp[0]
    return {"ok": True}


# Alias /productos -> medicamentos (para dashboard.py)
@app.get("/productos")
async def get_productos(tenant_id: int = Depends(get_current_tenant)):
    return await get_medicamentos(tenant_id=tenant_id)


@app.post("/productos")
async def create_producto(
    payload: MedicamentoCreate,
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    return await create_medicamento(payload=payload, tenant_id=tenant_id, _=_)


@app.patch("/productos/{producto_id}")
async def update_producto(
    producto_id: int,
    payload: Dict[str, Any],
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    return await update_medicamento(medicamento_id=int(producto_id), payload=payload, tenant_id=tenant_id, _=_)


# ============================================================
# CRUD: SUCURSALES / PROVEEDORES
# ============================================================
@app.get("/sucursales")
async def get_sucursales(tenant_id: int = Depends(get_current_tenant)):
    data = make_supabase_request("GET", "sucursales", query="order=nombre.asc", tenant_id=tenant_id)
    _raise_if_supabase_error(data)
    return data or []


@app.post("/sucursales")
async def create_sucursal(
    payload: SucursalCreate,
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    data = make_supabase_request("POST", "sucursales", data=payload.model_dump(), tenant_id=tenant_id)
    _raise_if_supabase_error(data)
    return data


@app.get("/proveedores")
async def get_proveedores(tenant_id: int = Depends(get_current_tenant)):
    data = make_supabase_request("GET", "proveedores", query="order=nombre.asc", tenant_id=tenant_id)
    if isinstance(data, dict) and data.get("error"):
        return []
    return data or []


@app.post("/proveedores")
async def create_proveedor(
    payload: Dict[str, Any],
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    data = {
        "codigo": payload.get("codigo"),
        "nombre": payload.get("nombre"),
        "contacto": payload.get("contacto"),
        "telefono": payload.get("telefono"),
        "email": payload.get("email"),
    }
    data = {k: v for k, v in data.items() if v is not None}
    resp = make_supabase_request("POST", "proveedores", data=data, tenant_id=tenant_id)
    _raise_if_supabase_error(resp)
    return resp


# ============================================================
# INVENTARIO (vista -> fallback join manual)
# ============================================================
def _inventario_from_view(tenant_id: int, extra_query: str = "") -> Any:
    q = "order=sucursal_nombre,nombre"
    if extra_query:
        q = f"{extra_query}&{q}"
    return make_supabase_request("GET", "vista_inventario_completo", query=q, tenant_id=tenant_id)


def _inventario_join_manual(tenant_id: int) -> List[dict]:
    inv = make_supabase_request("GET", "inventario", query="order=sucursal_id,medicamento_id", tenant_id=tenant_id)
    _raise_if_supabase_error(inv)
    meds = make_supabase_request("GET", "medicamentos", query="order=nombre.asc", tenant_id=tenant_id)
    _raise_if_supabase_error(meds)
    sucs = make_supabase_request("GET", "sucursales", query="order=nombre.asc", tenant_id=tenant_id)
    _raise_if_supabase_error(sucs)

    meds_map = {m["id"]: m for m in (meds or []) if isinstance(m, dict) and "id" in m}
    sucs_map = {s["id"]: s for s in (sucs or []) if isinstance(s, dict) and "id" in s}

    out: List[dict] = []
    for row in inv or []:
        m = meds_map.get(row.get("medicamento_id"), {})
        s = sucs_map.get(row.get("sucursal_id"), {})
        out.append(
            {
                "id": row.get("id"),
                "tenant_id": row.get("tenant_id"),
                "medicamento_id": row.get("medicamento_id"),
                "sucursal_id": row.get("sucursal_id"),
                "sku": m.get("sku") or row.get("sku"),
                "nombre": m.get("nombre") or row.get("nombre"),
                "categoria": m.get("categoria"),
                "fabricante": m.get("fabricante") or "",
                "precio_compra": m.get("precio_compra"),
                "precio_venta": m.get("precio_venta"),
                "sucursal_nombre": s.get("nombre") or row.get("sucursal_nombre"),
                "stock_actual": row.get("stock_actual", 0),
                "stock_minimo": row.get("stock_minimo", 0),
                "unidad": m.get("unidad"),
                "activo": m.get("activo"),
            }
        )
    out.sort(key=lambda x: (x.get("sucursal_nombre") or "", x.get("nombre") or ""))
    return out


@app.get("/inventario")
async def get_inventario(tenant_id: int = Depends(get_current_tenant)):
    data = _inventario_from_view(tenant_id)
    if isinstance(data, dict) and data.get("error"):
        return _inventario_join_manual(tenant_id)
    return data or []


@app.get("/inventario/sucursal/{sucursal_id}")
async def get_inventario_sucursal(sucursal_id: int, tenant_id: int = Depends(get_current_tenant)):
    q = f"sucursal_id=eq.{sucursal_id}&stock_actual=gte.1"
    data = _inventario_from_view(tenant_id, extra_query=q)
    if isinstance(data, dict) and data.get("error"):
        all_rows = _inventario_join_manual(tenant_id)
        return [r for r in all_rows if r.get("sucursal_id") == sucursal_id and _safe_int(r.get("stock_actual")) >= 1]
    return data or []


@app.get("/inventario/alertas")
async def get_alertas_inventario(tenant_id: int = Depends(get_current_tenant)):
    rows = await get_inventario(tenant_id)
    return [r for r in (rows or []) if _safe_int(r.get("stock_actual")) <= _safe_int(r.get("stock_minimo"))]


@app.post("/inventario")
async def create_inventario(
    payload: InventarioCreate,
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    data = make_supabase_request("POST", "inventario", data=payload.model_dump(), tenant_id=tenant_id)
    _raise_if_supabase_error(data)
    return data


@app.patch("/inventario/{inventario_id}")
async def update_inventario(
    inventario_id: int,
    payload: InventarioPatch,
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="Nada que actualizar")
    data = make_supabase_request("PATCH", "inventario", data=patch, query=f"id=eq.{inventario_id}", tenant_id=tenant_id)
    _raise_if_supabase_error(data)
    return data


# ============================================================
# LOTES
# ============================================================
@app.get("/lotes")
async def get_lotes(tenant_id: int = Depends(get_current_tenant)):
    q = "order=fecha_caducidad.asc"
    data = make_supabase_request("GET", "vista_lotes_api", query=q, tenant_id=tenant_id)
    if isinstance(data, dict) and data.get("error"):
        data = make_supabase_request("GET", "lotes_inventario", query="order=fecha_vencimiento.asc", tenant_id=tenant_id)
        if isinstance(data, dict) and data.get("error"):
            return []
    return data or []


@app.get("/lotes/medicamento/{medicamento_id}")
async def get_lotes_medicamento(
    medicamento_id: int,
    sucursal_id: Optional[int] = None,
    tenant_id: int = Depends(get_current_tenant),
):
    q = f"medicamento_id=eq.{medicamento_id}"
    if sucursal_id:
        q += f"&sucursal_id=eq.{sucursal_id}"
    q += "&order=fecha_caducidad.asc"
    data = make_supabase_request("GET", "vista_lotes_api", query=q, tenant_id=tenant_id)
    if isinstance(data, dict) and data.get("error"):
        q2 = f"medicamento_id=eq.{medicamento_id}"
        if sucursal_id:
            q2 += f"&sucursal_id=eq.{sucursal_id}"
        q2 += "&order=fecha_vencimiento.asc"
        data = make_supabase_request("GET", "lotes_inventario", query=q2, tenant_id=tenant_id)
        if isinstance(data, dict) and data.get("error"):
            return []
    return data or []


@app.get("/lotes/medicamento/{medicamento_id}/sucursal/{sucursal_id}")
async def get_lotes_medicamento_sucursal(medicamento_id: int, sucursal_id: int, tenant_id: int = Depends(get_current_tenant)):
    return await get_lotes_medicamento(medicamento_id=medicamento_id, sucursal_id=sucursal_id, tenant_id=tenant_id)


@app.post("/lotes")
async def create_lote(
    payload: LoteCreate,
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    incoming = payload.model_dump()

    numero_lote = incoming.get("numero_lote") or incoming.get("lote_codigo") or incoming.get("lote") or ""
    fecha_vencimiento = incoming.get("fecha_vencimiento") or incoming.get("fecha_caducidad")

    cantidad_recibida = int(incoming.get("cantidad_recibida") or incoming.get("cantidad_inicial") or 0)
    cantidad_actual = incoming.get("cantidad_actual")
    cantidad_actual = int(cantidad_actual) if cantidad_actual is not None else cantidad_recibida

    costo_unitario = incoming.get("costo_unitario")
    if costo_unitario is None:
        costo_unitario = incoming.get("precio_compra")

    fecha_recepcion = incoming.get("fecha_recepcion") or incoming.get("fecha_ingreso")
    if not fecha_recepcion:
        fecha_recepcion = datetime.utcnow().date().isoformat()

    data = {
        "medicamento_id": int(incoming["medicamento_id"]),
        "sucursal_id": int(incoming["sucursal_id"]),
        "numero_lote": numero_lote,
        "fecha_vencimiento": fecha_vencimiento,
        "cantidad_recibida": cantidad_recibida,
        "cantidad_actual": cantidad_actual,
        "costo_unitario": costo_unitario,
        "fecha_recepcion": fecha_recepcion,
        "fabricante": incoming.get("fabricante"),
        "registro_sanitario": incoming.get("registro_sanitario"),
        "inventario_id": incoming.get("inventario_id"),
    }
    data = {k: v for k, v in data.items() if v is not None}

    resp = make_supabase_request("POST", "lotes_inventario", data=data, tenant_id=tenant_id)
    _raise_if_supabase_error(resp)
    return resp


# ============================================================
# PROMOCIONES
# ============================================================
@app.get("/promociones")
async def get_promociones(tenant_id: int = Depends(get_current_tenant)):
    resp = make_supabase_request("GET", "promociones", query="order=id.desc", tenant_id=tenant_id)
    _raise_if_supabase_error(resp)
    return resp or []


@app.post("/promociones")
async def create_promocion(
    payload: Dict[str, Any],
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    data = dict(payload or {})
    if not data:
        raise HTTPException(status_code=400, detail="Payload vacío")
    resp = make_supabase_request("POST", "promociones", data=data, tenant_id=tenant_id)
    _raise_if_supabase_error(resp)
    if isinstance(resp, list) and resp:
        return resp[0]
    return resp


@app.patch("/promociones/{promo_id}")
async def update_promocion(
    promo_id: int,
    payload: Dict[str, Any],
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    data = dict(payload or {})
    if not data:
        raise HTTPException(status_code=400, detail="Payload vacío")
    data.pop("id", None)
    data.pop("tenant_id", None)
    resp = make_supabase_request("PATCH", "promociones", data=data, query=f"id=eq.{int(promo_id)}", tenant_id=tenant_id)
    _raise_if_supabase_error(resp)
    if isinstance(resp, list) and resp:
        return resp[0]
    return {"ok": True}


@app.delete("/promociones/{promo_id}")
async def delete_promocion(
    promo_id: int,
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    resp = make_supabase_request("DELETE", "promociones", query=f"id=eq.{int(promo_id)}", tenant_id=tenant_id)
    _raise_if_supabase_error(resp)
    return {"ok": True}


# ============================================================
# ANÁLISIS (para dashboard.py)
# ============================================================
@app.get("/analisis/inventario/resumen")
async def get_resumen_inventario(tenant_id: int = Depends(get_current_tenant)):
    inventario = await get_inventario(tenant_id)
    if not inventario:
        return {
            "resumen_general": {
                "total_medicamentos": 0,
                "total_stock": 0,
                "valor_total_inventario": 0,
                "items_disponibles": 0,
                "alertas_stock_bajo": 0,
            },
            "tenant_id": tenant_id,
            "fecha_calculo": datetime.utcnow().isoformat(),
        }

    total_meds = len(set(i.get("medicamento_id") for i in inventario if i.get("medicamento_id") is not None))
    total_stock = sum(_safe_int(i.get("stock_actual")) for i in inventario)
    items_disponibles = len([i for i in inventario if _safe_int(i.get("stock_actual")) > 0])
    valor_total = sum(_safe_int(i.get("stock_actual")) * _safe_float(i.get("precio_venta")) for i in inventario)
    alertas = len([i for i in inventario if _safe_int(i.get("stock_actual")) <= _safe_int(i.get("stock_minimo"))])

    return {
        "resumen_general": {
            "total_medicamentos": total_meds,
            "total_stock": total_stock,
            "valor_total_inventario": round(valor_total, 2),
            "items_disponibles": items_disponibles,
            "alertas_stock_bajo": alertas,
        },
        "tenant_id": tenant_id,
        "fecha_calculo": datetime.utcnow().isoformat(),
    }


@app.get("/dashboard/metricas/sucursal/{sucursal_id}")
async def get_metricas_sucursal(sucursal_id: int, tenant_id: int = Depends(get_current_tenant)):
    rows = await get_inventario_sucursal(sucursal_id, tenant_id)
    total_meds = len(set(i.get("medicamento_id") for i in rows if i.get("medicamento_id") is not None))
    total_stock = sum(_safe_int(i.get("stock_actual")) for i in rows)
    alertas = len([i for i in rows if _safe_int(i.get("stock_actual")) <= _safe_int(i.get("stock_minimo"))])
    valor_total = sum(_safe_int(i.get("stock_actual")) * _safe_float(i.get("precio_venta")) for i in rows)
    return {
        "sucursal_id": sucursal_id,
        "total_medicamentos": total_meds,
        "total_stock": total_stock,
        "alertas_stock_bajo": alertas,
        "valor_total_inventario": round(valor_total, 2),
        "tenant_id": tenant_id,
    }


# ============================================================
# SALIDAS (real con lotes_inventario / salidas_inventario)
# ============================================================
@app.get("/salidas")
async def get_salidas(tenant_id: int = Depends(get_current_tenant)):
    """Compat: algunos dashboards llaman GET /salidas."""
    data = make_supabase_request("GET", "vista_salidas_completo", query="order=fecha_salida.desc&limit=100", tenant_id=tenant_id)
    if isinstance(data, dict) and data.get("error"):
        data = make_supabase_request("GET", "salidas_inventario", query="order=fecha_salida.desc&limit=100", tenant_id=tenant_id)
        if isinstance(data, dict) and data.get("error"):
            return []
    return data or []


@app.post("/salidas/lote")
async def registrar_salida_lote(
    payload: SalidaLoteCreate,
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    p = payload.model_dump()
    lote_id = int(p["lote_id"])
    qty = int(p["cantidad"])
    tipo_salida = (p.get("tipo_salida") or "Venta").strip()
    observaciones = p.get("observaciones")
    usuario = p.get("usuario") or "DEMO_SYSTEM"
    fecha_salida = p.get("fecha_salida") or datetime.utcnow().isoformat()

    # 1) Leer lote
    lote_rows = make_supabase_request(
        "GET",
        "lotes_inventario",
        query=f"id=eq.{lote_id}&select=id,tenant_id,medicamento_id,sucursal_id,numero_lote,cantidad_actual",
        tenant_id=tenant_id,
    )
    _raise_if_supabase_error(lote_rows)
    if not lote_rows:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    lote = lote_rows[0]
    if int(lote.get("tenant_id") or tenant_id) != tenant_id:
        raise HTTPException(status_code=403, detail="Lote no pertenece al tenant")

    disponible = int(lote.get("cantidad_actual") or 0)
    if qty > disponible:
        raise HTTPException(status_code=400, detail=f"Cantidad insuficiente en lote. Disponible: {disponible}")

    # 2) Descontar lote
    nuevo = disponible - qty
    upd = make_supabase_request("PATCH", "lotes_inventario", data={"cantidad_actual": nuevo}, query=f"id=eq.{lote_id}", tenant_id=tenant_id)
    _raise_if_supabase_error(upd)

    # 3) Insertar salida
    salida_data = {
        "sucursal_id": int(lote["sucursal_id"]),
        "medicamento_id": int(lote["medicamento_id"]),
        "lote_id": lote_id,
        "numero_lote": lote.get("numero_lote"),
        "cantidad": qty,
        "tipo_salida": tipo_salida,
        "observaciones": observaciones,
        "usuario": usuario,
        "fecha_salida": fecha_salida,
    }
    salida_data = {k: v for k, v in salida_data.items() if v is not None}
    ins = make_supabase_request("POST", "salidas_inventario", data=salida_data, tenant_id=tenant_id)
    _raise_if_supabase_error(ins)

    # 4) Best-effort: descontar inventario.stock_actual
    inv_rows = make_supabase_request(
        "GET",
        "inventario",
        query=f"medicamento_id=eq.{int(lote['medicamento_id'])}&sucursal_id=eq.{int(lote['sucursal_id'])}&select=id,stock_actual",
        tenant_id=tenant_id,
    )
    if isinstance(inv_rows, list) and inv_rows:
        inv = inv_rows[0]
        stock_actual = int(inv.get("stock_actual") or 0)
        nuevo_stock = max(stock_actual - qty, 0)
        make_supabase_request("PATCH", "inventario", data={"stock_actual": nuevo_stock}, query=f"id=eq.{inv['id']}", tenant_id=tenant_id)

    return {"ok": True, "lote_id": lote_id, "cantidad": qty, "lote_cantidad_actual": nuevo, "salida": ins}


# ============================================================
# ENDPOINTS "INTELIGENTES" (compat dashboard.py)
# ============================================================
@app.get("/dashboard/inteligente")
async def dashboard_inteligente(tenant_id: int = Depends(get_current_tenant)):
    resumen = await get_resumen_inventario(tenant_id)
    inventario = await get_inventario(tenant_id)
    lotes = await get_lotes(tenant_id)

    compras = await recomendaciones_compras_inteligentes(solo_criticas=True, incluir_detalles=False, tenant_id=tenant_id)
    redis = await optimizacion_redistribucion(tenant_id=tenant_id)
    venc = await alertas_vencimientos_inteligentes(dias_adelanto=30, tenant_id=tenant_id)

    return {
        "resumen": resumen,
        "top_stock_bajo": (await get_alertas_inventario(tenant_id))[:10],
        "compras_sugeridas": compras,
        "redistribucion_sugerida": redis,
        "alertas_vencimiento": venc,
        "counts": {"inventario": len(inventario or []), "lotes": len(lotes or [])},
        "tenant_id": tenant_id,
        "fecha_generacion": datetime.utcnow().isoformat(),
    }


@app.get("/recomendaciones/compras/inteligentes")
async def recomendaciones_compras_inteligentes(
    solo_criticas: bool = False,
    incluir_detalles: bool = False,
    tenant_id: int = Depends(get_current_tenant),
):
    inventario = await get_inventario(tenant_id)
    recs: List[dict] = []

    for item in inventario or []:
        stock = _safe_int(item.get("stock_actual"))
        minimo = _safe_int(item.get("stock_minimo"))
        if minimo <= 0:
            continue

        is_critica = stock <= minimo
        is_preventiva = stock <= int(minimo * 1.25)

        if solo_criticas and not is_critica:
            continue
        if (not solo_criticas) and not (is_critica or is_preventiva):
            continue

        sugerido = max(minimo * 2 - stock, 0)
        if sugerido <= 0:
            continue

        row = {
            "medicamento_id": item.get("medicamento_id"),
            "nombre": item.get("nombre"),
            "sku": item.get("sku"),
            "sucursal_id": item.get("sucursal_id"),
            "sucursal_nombre": item.get("sucursal_nombre"),
            "stock_actual": stock,
            "stock_minimo": minimo,
            "cantidad_sugerida": int(sugerido),
            "prioridad": "CRITICA" if is_critica else "PREVENTIVA",
        }
        if incluir_detalles:
            precio = _safe_float(item.get("precio_compra"), 0.0)
            row["costo_estimado"] = round(precio * row["cantidad_sugerida"], 2)

        recs.append(row)

    recs.sort(key=lambda r: (0 if r["prioridad"] == "CRITICA" else 1, -(r["cantidad_sugerida"])))
    return recs[:50]


@app.get("/optimizacion/redistribucion")
async def optimizacion_redistribucion(tenant_id: int = Depends(get_current_tenant)):
    inventario = await get_inventario(tenant_id)
    if not inventario:
        return []

    by_med: Dict[int, List[dict]] = {}
    for it in inventario:
        mid = it.get("medicamento_id")
        if mid is None:
            continue
        by_med.setdefault(int(mid), []).append(it)

    suggestions: List[dict] = []
    for mid, items in by_med.items():
        if len(items) < 2:
            continue

        donors: List[Tuple[dict, int]] = []
        receivers: List[Tuple[dict, int]] = []

        for it in items:
            stock = _safe_int(it.get("stock_actual"))
            minimo = _safe_int(it.get("stock_minimo"))
            exceso = stock - int(minimo * 1.5)
            deficit = minimo - stock
            if exceso > 0:
                donors.append((it, exceso))
            if deficit > 0:
                receivers.append((it, deficit))

        donors.sort(key=lambda x: -x[1])
        receivers.sort(key=lambda x: -x[1])

        for recv, need in receivers:
            remaining = need
            for i in range(len(donors)):
                donor, avail = donors[i]
                if avail <= 0 or remaining <= 0:
                    continue
                move = min(avail, remaining)
                donors[i] = (donor, avail - move)
                remaining -= move

                suggestions.append(
                    {
                        "medicamento_id": mid,
                        "nombre": recv.get("nombre"),
                        "sku": recv.get("sku"),
                        "from_sucursal_id": donor.get("sucursal_id"),
                        "from_sucursal": donor.get("sucursal_nombre"),
                        "to_sucursal_id": recv.get("sucursal_id"),
                        "to_sucursal": recv.get("sucursal_nombre"),
                        "cantidad_sugerida": int(move),
                        "razon": "Balanceo por stock bajo",
                    }
                )
                if remaining <= 0:
                    break

    suggestions.sort(key=lambda s: -_safe_int(s.get("cantidad_sugerida")))
    return suggestions[:50]


@app.get("/alertas/vencimientos/inteligentes")
async def alertas_vencimientos_inteligentes(dias_adelanto: int = 30, tenant_id: int = Depends(get_current_tenant)):
    lotes = await get_lotes(tenant_id)
    if not lotes:
        return []

    hoy = date.today()
    limite = hoy + timedelta(days=int(dias_adelanto))

    alerts: List[dict] = []
    for lote in lotes:
        fv = _parse_date_yyyy_mm_dd(lote.get("fecha_vencimiento") or lote.get("fecha_caducidad"))
        if not fv:
            continue
        if fv <= limite:
            dias = (fv - hoy).days
            alerts.append(
                {
                    "lote_id": lote.get("id"),
                    "numero_lote": lote.get("numero_lote"),
                    "medicamento_id": lote.get("medicamento_id"),
                    "sucursal_id": lote.get("sucursal_id"),
                    "fecha_vencimiento": fv.isoformat(),
                    "dias_restantes": dias,
                    "prioridad": "VENCIDO" if dias < 0 else ("CRITICO" if dias <= 7 else "PROXIMO"),
                    "cantidad_actual": lote.get("cantidad_actual"),
                }
            )

    alerts.sort(key=lambda a: a["dias_restantes"])
    return alerts[:100]


# ============================================================
# VENTAS (compat + básico)
# ============================================================
@app.get("/ventas")
async def get_ventas(
    tenant_id: int = Depends(get_current_tenant),
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sucursal_id: Optional[int] = None,
):
    filters = []
    if date_from:
        filters.append(f"fecha=gte.{date_from}T00:00:00")
    if date_to:
        filters.append(f"fecha=lte.{date_to}T23:59:59")
    if sucursal_id:
        filters.append(f"sucursal_id=eq.{int(sucursal_id)}")

    q = "&".join(filters) + ("&" if filters else "") + "order=fecha.desc"
    data = make_supabase_request("GET", "vista_ventas_detalle", query=q, tenant_id=tenant_id)

    if isinstance(data, dict) and data.get("error"):
        q2 = "&".join(filters) + ("&" if filters else "") + "order=id.desc"
        ventas = make_supabase_request("GET", "ventas", query=q2, tenant_id=tenant_id)
        if isinstance(ventas, dict) and ventas.get("error"):
            return []
        return ventas or []

    return data or []


@app.post("/ventas")
async def create_venta(
    payload: Dict[str, Any],
    tenant_id: int = Depends(get_current_tenant),
    _: None = Depends(require_api_secret),
):
    sucursal_id = payload.get("sucursal_id")
    items = payload.get("items") or []
    if not sucursal_id:
        raise HTTPException(status_code=400, detail="sucursal_id es requerido")
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="items es requerido y debe traer al menos 1 item")

    subtotal = 0.0
    normalized_items: List[Dict[str, Any]] = []

    for i, it in enumerate(items):
        try:
            medicamento_id = int(it.get("medicamento_id"))
            lote_id = it.get("lote_id")
            lote_id = int(lote_id) if lote_id is not None else None
            cantidad = int(it.get("cantidad"))
            precio_unitario = float(it.get("precio_unitario", 0))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Item inválido en posición {i}")

        if cantidad <= 0:
            raise HTTPException(status_code=400, detail=f"cantidad debe ser > 0 (item {i})")
        if precio_unitario < 0:
            raise HTTPException(status_code=400, detail=f"precio_unitario inválido (item {i})")

        line_subtotal = round(cantidad * precio_unitario, 2)
        subtotal += line_subtotal

        normalized_items.append(
            {
                "medicamento_id": medicamento_id,
                "lote_id": lote_id,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "subtotal": line_subtotal,
            }
        )

    subtotal = round(subtotal, 2)
    descuento = float(payload.get("descuento", 0) or 0)
    impuestos = float(payload.get("impuestos", 0) or 0)
    total = round(subtotal - descuento + impuestos, 2)

    venta_row = {
        "sucursal_id": int(sucursal_id),
        "fecha": datetime.utcnow().isoformat() + "Z",
        "folio": payload.get("folio"),
        "metodo_pago": payload.get("metodo_pago") or "Efectivo",
        "cliente_nombre": payload.get("cliente_nombre"),
        "notas": payload.get("notas"),
        "subtotal": subtotal,
        "descuento": descuento,
        "impuestos": impuestos,
        "total": total,
    }
    venta_row = {k: v for k, v in venta_row.items() if v is not None}

    venta_resp = make_supabase_request("POST", "ventas", data=venta_row, tenant_id=tenant_id)
    _raise_if_supabase_error(venta_resp)

    if isinstance(venta_resp, list) and venta_resp:
        venta = venta_resp[0]
    elif isinstance(venta_resp, dict) and venta_resp.get("id"):
        venta = venta_resp
    else:
        last = make_supabase_request("GET", "ventas", query="order=id.desc&limit=1", tenant_id=tenant_id)
        _raise_if_supabase_error(last)
        if isinstance(last, list) and last:
            venta = last[0]
        else:
            raise HTTPException(status_code=500, detail="No se pudo obtener id de la venta creada")

    venta_id = int(venta["id"])

    items_rows = []
    for it in normalized_items:
        items_rows.append(
            {
                "venta_id": venta_id,
                "medicamento_id": it["medicamento_id"],
                "sucursal_id": int(sucursal_id),
                "lote_id": it["lote_id"],
                "cantidad": it["cantidad"],
                "precio_unitario": it["precio_unitario"],
                "subtotal": it["subtotal"],
            }
        )

    items_resp = make_supabase_request("POST", "venta_items", data=items_rows, tenant_id=tenant_id)
    _raise_if_supabase_error(items_resp)

    # Descontar stock por lote si viene lote_id
    for it in normalized_items:
        lote_id = it.get("lote_id")
        if not lote_id:
            continue

        lote_data = make_supabase_request("GET", "lotes_inventario", query=f"id=eq.{int(lote_id)}&limit=1", tenant_id=tenant_id)
        _raise_if_supabase_error(lote_data)
        if not isinstance(lote_data, list) or not lote_data:
            raise HTTPException(status_code=400, detail=f"Lote no encontrado: {lote_id}")

        lote = lote_data[0]
        stock_actual = int(float(lote.get("cantidad_actual") or 0))
        if stock_actual < it["cantidad"]:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente en lote {lote.get('numero_lote', lote_id)}")

        nuevo_stock = stock_actual - it["cantidad"]
        upd = make_supabase_request("PATCH", "lotes_inventario", query=f"id=eq.{int(lote_id)}", data={"cantidad_actual": nuevo_stock}, tenant_id=tenant_id)
        _raise_if_supabase_error(upd)

    return {"venta_id": venta_id, "total": total, "items": normalized_items}


# ============================================================
# ERRORES
# ============================================================
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=404, content={"detail": "Not Found"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "error": str(exc)})