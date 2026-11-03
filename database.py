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

### --- FUNCIONES DE ESTACIONES E INVENTARIOS ---
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
    """Obtiene las asignaciones de estaciones por usuario desde Supabase."""
    try:
        response = _require_supabase().table("estaciones_usuario").select("*, estaciones(*)").execute()
        return response.data
    except Exception:
        return []

def insertar_inventario(id_estacion, fecha, producto, volumen):
    """
    Inserta, actualiza o elimina un registro de inventario según el valor del volumen.
    Si el volumen es None, NaN o está vacío, elimina el registro de la base de datos.
    """
    client = _require_supabase()
    
    id_estacion_str = str(id_estacion).strip()
    fecha_str = str(fecha)
    producto_str = str(producto).strip().capitalize()
    
    # Validar si el volumen es nulo, NaN, cadena vacía o indicativo de no registro
    if volumen is None or volumen == "" or (isinstance(volumen, float) and (math.isnan(volumen) or math.isinf(volumen))):
        # Eliminar el registro de Supabase si existe para no almacenar ceros ni datos nulos
        response = client.table("inventarios").delete().eq("id_estacion", id_estacion_str).eq("fecha", fecha_str).eq("producto", producto_str).execute()
        return response.data
    
    try:
        val_float = float(volumen)
    except (ValueError, TypeError):
        # Si no se puede convertir a número válido, eliminar el registro
        response = client.table("inventarios").delete().eq("id_estacion", id_estacion_str).eq("fecha", fecha_str).eq("producto", producto_str).execute()
        return response.data

    data = {
        "id_estacion": id_estacion_str,
        "fecha": fecha_str,
        "producto": producto_str,
        "volumen": val_float
    }
    
    # Realizar 'upsert' si el valor es un número real válido
    response = client.table("inventarios").upsert(
        data,
        on_conflict="id_estacion,fecha,producto"
    ).execute()
    
    return response.data

### --- FUNCIONES DE VISTAS DE SUPABASE ---
def obtener_vdp_ponderada_12w():
    """Obtiene la VDP ponderada calculada directamente desde la vista de Supabase[cite: 2]."""
    try:
        response = _require_supabase().table("vdp_ponderada_12w").select("*").execute()
        return response.data
    except Exception:
        return []

def obtener_factor_venta_diasemanal():
    """Obtiene los factores de venta por día de la semana desde la vista de Supabase[cite: 2]."""
    try:
        response = _require_supabase().table("factor_venta_diasemanal").select("*").execute()
        return response.data
    except Exception:
        return []
