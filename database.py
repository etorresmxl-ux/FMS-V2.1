import math
import os
from datetime import date, datetime
from numbers import Number

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
    return create_client(url, key) if url and key else None


def _require_supabase() -> Client:
    client = get_supabase_client()
    if client is None:
        raise RuntimeError(
            "Faltan credenciales de Supabase. Configura st.secrets['supabase'] o define "
            "SUPABASE_URL y SUPABASE_KEY en el entorno."
        )
    return client


def validar_numero_entero(valor, nombre="valor", *, minimo=0) -> int:
    """Valida y devuelve un entero finito; rechaza booleanos, decimales y vacíos."""
    if valor is None or isinstance(valor, bool):
        raise ValueError(f"{nombre.capitalize()} debe ser un número entero.")
    if isinstance(valor, str):
        valor = valor.strip()
        if not valor:
            raise ValueError(f"{nombre.capitalize()} no puede estar vacío.")
    if not isinstance(valor, (Number, str)):
        raise ValueError(f"{nombre.capitalize()} debe ser un número entero.")
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{nombre.capitalize()} debe ser un número entero.") from exc
    if not math.isfinite(numero) or not numero.is_integer():
        raise ValueError(f"{nombre.capitalize()} debe ser un número entero finito.")
    entero = int(numero)
    if minimo is not None and entero < minimo:
        raise ValueError(f"{nombre.capitalize()} no puede ser menor que {minimo}.")
    return entero


def _normalizar_fecha(valor):
    if valor is None:
        raise ValueError("La fecha no puede estar vacía.")
    if isinstance(valor, datetime):
        return valor.date().isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, str):
        texto = valor.strip()
        if texto:
            try:
                return datetime.fromisoformat(texto).date().isoformat()
            except ValueError as exc:
                raise ValueError("La fecha debe tener un formato válido (AAAA-MM-DD).") from exc
    raise ValueError("La fecha debe ser un valor de fecha válido.")


def _normalizar_producto(producto):
    texto = str(producto or "").strip()
    if not texto:
        raise ValueError("El producto no puede estar vacío.")
    return texto.title().replace("_", " ")


def obtener_estaciones():
    return _require_supabase().table("estaciones").select("*").execute().data


def obtener_inventarios():
    return _require_supabase().table("inventarios").select("*").execute().data


def obtener_tanques_estaciones():
    return _require_supabase().table("tanques_estaciones").select("*").execute().data


def obtener_estaciones_usuario():
    try:
        return _require_supabase().table("estaciones_usuario").select("*, estaciones(*)").execute().data
    except Exception as exc:
        st.error(f"Error al obtener estaciones de usuario: {exc}")
        return []


def obtener_programa_cargas():
    try:
        return _require_supabase().table("programa_cargas").select("*").execute().data
    except Exception:
        return []


def obtener_vdp_ponderada_12w():
    try:
        return _require_supabase().table("vdp_ponderada_12w").select("*").execute().data
    except Exception:
        return []


def obtener_factor_venta_diasemanal():
    try:
        return _require_supabase().table("factor_venta_diasemanal").select("*").execute().data
    except Exception:
        return []


def insertar_estacion(id_estacion, nombre, plaza="", tad=""):
    """Los campos descriptivos son texto; los valores cuantitativos se validan como enteros."""
    payload = {
        "id_estacion": str(id_estacion).strip(),
        "nombre": str(nombre).strip(),
        "plaza": str(plaza or "").strip(),
        "tad": str(tad or "").strip(),
    }
    if not payload["id_estacion"] or not payload["nombre"]:
        raise ValueError("El ID y el nombre de la estación son obligatorios.")
    return _require_supabase().table("estaciones").upsert(payload, on_conflict="id_estacion").execute()


def _payload_volumen(id_estacion, fecha, producto, volumen):
    if id_estacion is None or not str(id_estacion).strip():
        raise ValueError("El ID de estación es obligatorio.")
    return {
        "id_estacion": str(id_estacion).strip(),
        "fecha": _normalizar_fecha(fecha),
        "producto": _normalizar_producto(producto),
        "volumen": validar_numero_entero(volumen, "volumen", minimo=0),
    }


def insertar_inventario(id_estacion, fecha, producto, volumen):
    payload = _payload_volumen(id_estacion, fecha, producto, volumen)
    return _require_supabase().table("inventarios").upsert(
        payload, on_conflict="id_estacion,fecha,producto"
    ).execute()


def insertar_venta(id_estacion, fecha, producto, volumen):
    payload = _payload_volumen(id_estacion, fecha, producto, volumen)
    return _require_supabase().table("ventas").upsert(
        payload, on_conflict="id_estacion,fecha,producto"
    ).execute()


def insertar_carga_programada(id_estacion, fecha, producto, volumen):
    payload = _payload_volumen(id_estacion, fecha, producto, volumen)
    return _require_supabase().table("programa_cargas").upsert(
        payload, on_conflict="id_estacion,producto,fecha"
    ).execute()
