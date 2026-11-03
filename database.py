import os
import math
import streamlit as st
from supabase import create_client, Client

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
    if valor is None:
        return 0.0
    try:
        f = float(valor)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except (ValueError, TypeError):
        return 0.0

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

# --- FUNCIONES DE VISTAS DE SUPABASE (Reemplazan a calculos.py) ---

def obtener_vdp_ponderada_12w():
    """Obtiene la VDP ponderada calculada directamente desde la vista de Supabase."""
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
