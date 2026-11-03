import math
import os
from datetime import date, datetime

import streamlit as st
from supabase import Client, create_client


@st.cache_resource
def get_supabase_client() -> Client | None:
    """Obtiene el cliente de Supabase desde secrets o variables de entorno."""
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
    if valor is None:
        return 0.0
    try:
        valor_float = float(valor)
        if math.isnan(valor_float) or math.isinf(valor_float):
            return 0.0
        return valor_float
    except (TypeError, ValueError):
        return 0.0


def _normalizar_fecha(valor):
    if valor is None:
        raise ValueError("La fecha no puede estar vacía.")
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            raise ValueError("La fecha no puede estar vacía.")
        try:
            return datetime.fromisoformat(texto).date().isoformat()
        except ValueError:
            # Permite valores tipo YYYY-MM-DD u otros comúnmente enviados por Excel
            return texto
    return str(valor)


def _normalizar_producto(producto):
    texto = str(producto or "").strip()
    if not texto:
        raise ValueError("El producto no puede estar vacío.")
    return texto.title().replace("_", " ")


# --- FUNCIONES DE ESTACIONES E INVENTARIOS ---
def obtener_estaciones():
    response = _require_supabase().table("estaciones").select("*").execute()
    return response.data


def obtener_inventarios():
    response = _require_supabase().table("inventarios").select("*").execute()
    return response.data


def obtener_tanques_estaciones():
    response = _require_supabase().table("tanques_estaciones").select("*").execute()
    return response.data


def obtener_estaciones_usuario():
    try:
        response = _require_supabase().table("estaciones_usuario").select("*, estaciones(*)").execute()
        return response.data
    except Exception as exc:
        st.error(f"Error al obtener estaciones de usuario: {exc}")
        return []


# --- FUNCIONES DE PROGRAMA DE CARGAS ---
def obtener_programa_cargas():
    """Obtiene el programa de cargas desde la tabla de Supabase."""
    try:
        response = _require_supabase().table("programa_cargas").select("*").execute()
        return response.data
    except Exception:
        return []


# --- FUNCIONES DE VISTAS DE SUPABASE ---
def obtener_vdp_ponderada_12w():
    """Obtiene la VDP ponderada desde la vista definida en Supabase."""
    try:
        response = _require_supabase().table("vdp_ponderada_12w").select("*").execute()
        return response.data
    except Exception:
        return []


def obtener_factor_venta_diasemanal():
    """Obtiene los factores de venta por día de la semana desde la vista de Supabase."""
    try:
        response = _require_supabase().table("factor_venta_diasemanal").select("*").execute()
        return response.data
    except Exception:
        return []


# --- INSERCIONES SEGURAS ---
def insertar_estacion(id_estacion, nombre, plaza="", tad=""):
    supabase = _require_supabase()
    payload = {
        "id_estacion": str(id_estacion).strip(),
        "nombre": str(nombre).strip(),
        "plaza": str(plaza or "").strip(),
        "tad": str(tad or "").strip(),
    }
    if not payload["id_estacion"]:
        raise ValueError("El ID de la estación es obligatorio.")
    if not payload["nombre"]:
        raise ValueError("El nombre de la estación es obligatorio.")

    supabase.table("estaciones").upsert(payload, on_conflict="id_estacion").execute()
    return payload


def insertar_inventario(id_estacion, fecha, producto, volumen):
    supabase = _require_supabase()
    payload = {
        "id_estacion": str(id_estacion).strip(),
        "fecha": _normalizar_fecha(fecha),
        "producto": _normalizar_producto(producto),
        "volumen": _limpiar_flotante(volumen),
    }
    if not payload["id_estacion"]:
        raise ValueError("El ID de estación es obligatorio.")

    supabase.table("inventarios").upsert(
        payload,
        on_conflict="id_estacion,fecha,producto"
    ).execute()
    return payload


def insertar_venta(id_estacion, fecha, producto, volumen):
    supabase = _require_supabase()
    payload = {
        "id_estacion": str(id_estacion).strip(),
        "fecha": _normalizar_fecha(fecha),
        "producto": _normalizar_producto(producto),
        "volumen": _limpiar_flotante(volumen),
    }
    if not payload["id_estacion"]:
        raise ValueError("El ID de estación es obligatorio.")

    supabase.table("ventas").upsert(
        payload,
        on_conflict="id_estacion,fecha,producto"
    ).execute()
    return payload


def insertar_carga_programada(id_estacion, fecha, producto, volumen):
    supabase = _require_supabase()
    payload = {
        "id_estacion": str(id_estacion).strip(),
        "fecha": _normalizar_fecha(fecha),
        "producto": _normalizar_producto(producto),
        "volumen": _limpiar_flotante(volumen),
    }
    if not payload["id_estacion"]:
        raise ValueError("El ID de estación es obligatorio.")

    supabase.table("programa_cargas").upsert(
        payload,
        on_conflict="id_estacion,fecha,producto"
    ).execute()
    return payload


__all__ = [
    "get_supabase_client",
    "_require_supabase",
    "obtener_estaciones",
    "obtener_inventarios",
    "obtener_tanques_estaciones",
    "obtener_estaciones_usuario",
    "obtener_programa_cargas",
    "obtener_vdp_ponderada_12w",
    "obtener_factor_venta_diasemanal",
    "insertar_estacion",
    "insertar_inventario",
    "insertar_venta",
    "insertar_carga_programada",
]
