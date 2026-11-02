import os
import math
import streamlit as st
from supabase import create_client, Client


def _normalizar_producto(producto):
    """Normaliza nombres de producto para evitar errores con nulos o valores no string."""
    if producto is None:
        return ""
    if isinstance(producto, float) and math.isnan(producto):
        return ""
    return str(producto).strip().capitalize()


# Inicializar cliente de Supabase usando el caché de Streamlit para no reconectar en cada rerun.
# La conexión no se crea al importar el módulo si faltan credenciales; la app debe avisar al
# ejecutar la operación y no romper el arranque de la aplicación.
@st.cache_resource
def get_supabase_client() -> Client | None:
    try:
        supabase_cfg = st.secrets.get("supabase", {})
    except Exception:
        supabase_cfg = {}

    url = supabase_cfg.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = supabase_cfg.get("SUPABASE_KEY") or os.getenv("SUPABASE_KEY")

    if not url or not key:
        return None

    return create_client(url, key)


def _require_supabase() -> Client:
    client = get_supabase_client()
    if client is None:
        raise RuntimeError(
            "Faltan credenciales de Supabase. Configura st.secrets['supabase'] o define "
            "SUPABASE_URL y SUPABASE_KEY en el entorno."
        )
    return client


def _limpiar_flotante(valor):
    """Convierte valores nulos, NaN o vacíos a 0.0 para cumplir con JSON y Supabase."""
    if valor is None:
        return 0.0
    try:
        f = float(valor)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except (ValueError, TypeError):
        return 0.0


# =========================================================
# --- FUNCIONES DE ESTACIONES ---
# =========================================================
def obtener_estaciones():
    response = _require_supabase().table("estaciones").select("*").execute()
    return response.data


def insertar_estacion(id_estacion, nombre, plaza, tad):
    data = {
        "id_estacion": id_estacion,
        "nombre": nombre,
        "plaza": plaza,
        "tad": tad
    }
    return _require_supabase().table("estaciones").insert(data).execute()


# =========================================================
# --- FUNCIONES DE TANQUES ESTACIONES ---
# =========================================================
def obtener_tanques_estaciones():
    """Obtiene la relación de tanques y productos configurados por estación."""
    response = _require_supabase().table("tanques_estaciones").select("*").execute()
    return response.data


# =========================================================
# --- FUNCIONES DE ESTACIONES USUARIO ---
# =========================================================
def obtener_estaciones_usuario():
    """Obtiene la relación de estaciones y usuarios asignados desde Supabase."""
    response = _require_supabase().table("estaciones_usuario").select("*, estaciones(nombre, plaza, tad)").execute()
    return response.data


def insertar_estacion_usuario(id_estacion, usuario):
    """Inserta la asignación de una estación a un usuario."""
    data = {
        "id_estacion": id_estacion,
        "usuario": usuario
    }
    return _require_supabase().table("estaciones_usuario").insert(data).execute()


# =========================================================
# --- FUNCIONES DE INVENTARIOS ---
# =========================================================
def obtener_inventarios():
    response = _require_supabase().table("inventarios").select("*, estaciones(nombre)").execute()
    return response.data


def insertar_inventario(id_estacion, fecha, producto, volumen):
    data = {
        "id_estacion": id_estacion,
        "fecha": str(fecha),
        "producto": _normalizar_producto(producto),
        "volumen": _limpiar_flotante(volumen)
    }
    return _require_supabase().table("inventarios").insert(data).execute()


def guardar_inventarios_por_fecha(registros):
    """Actualiza o inserta inventarios sin depender de un UNIQUE/UPSERT del esquema."""
    if not registros:
        return {"data": []}

    supabase = _require_supabase()
    resultados = []
    vistos = set()

    for registro in registros:
        if not registro:
            continue

        id_estacion = registro["id_estacion"]
        fecha_str = str(registro["fecha"])
        producto = _normalizar_producto(registro["producto"])
        volumen = _limpiar_flotante(registro["volumen"])
        clave = (str(id_estacion), fecha_str, producto)

        if clave in vistos:
            continue
        vistos.add(clave)

        existente = (
            supabase.table("inventarios")
            .select("*")
            .eq("id_estacion", id_estacion)
            .eq("fecha", fecha_str)
            .eq("producto", producto)
            .limit(1)
            .execute()
        )

        payload = {
            "id_estacion": id_estacion,
            "fecha": fecha_str,
            "producto": producto,
            "volumen": volumen,
        }

        if existente.data:
            respuesta = (
                supabase.table("inventarios")
                .update({"volumen": volumen})
                .eq("id_estacion", id_estacion)
                .eq("fecha", fecha_str)
                .eq("producto", producto)
                .execute()
            )
        else:
            respuesta = supabase.table("inventarios").insert(payload).execute()

        resultados.append(respuesta)

    return {"data": resultados}


# =========================================================
# --- FUNCIONES DE VENTAS ---
# =========================================================
def obtener_ventas():
    response = _require_supabase().table("ventas").select("*, estaciones(nombre)").execute()
    return response.data


def insertar_venta(id_estacion, fecha, producto, volumen):
    data = {
        "id_estacion": id_estacion,
        "fecha": str(fecha),
        "producto": _normalizar_producto(producto),
        "volumen": _limpiar_flotante(volumen)
    }
    return _require_supabase().table("ventas").insert(data).execute()


# =========================================================
# --- FUNCIONES DE VISTAS SQL (ÚLTIMAS 12 SEMANAS) ---
# =========================================================
def obtener_venta_semanal_promedio_12w():
    """Obtiene la venta semanal de las últimas 12 semanas por estación y producto desde Supabase."""
    response = _require_supabase().table("venta_semanal_promedio_12w").select("*").execute()
    return response.data


def obtener_venta_promedio_dia_semana_12w():
    """Obtiene la venta promedio por día de la semana de las últimas 12 semanas por estación y producto desde Supabase."""
    response = _require_supabase().table("venta_promedio_dia_de_la_semana_12w").select("*").execute()
    return response.data
