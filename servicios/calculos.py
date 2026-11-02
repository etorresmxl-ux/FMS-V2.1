import pandas as pd
import streamlit as st
import database as db


@st.cache_data
def obtener_calculos_combustible():
    """
    Obtiene la venta semanal ponderada desde la vista de Supabase,
    aplicando normalización estricta de texto al inicio.
    """
    try:
        data = db.obtener_venta_semanal_promedio_12w()
        df = pd.DataFrame(data)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["id_estacion"] = df["id_estacion"].astype(str).str.strip()
    df["producto"] = df["producto"].astype(str).str.strip().str.capitalize()

    df = df.sort_values(by=['id_estacion', 'producto', 'semana'], ascending=[True, True, False])
    df['ranking_semana'] = df.groupby(['id_estacion', 'producto']).cumcount() + 1

    def asignar_peso(row):
        r = row['ranking_semana']
        if r in [1, 2]:
            return 0.50 / 2
        elif 3 <= r <= 8:
            return 0.30 / 6
        elif 9 <= r <= 12:
            return 0.20 / 4
        return 0.0

    df['peso'] = df.apply(asignar_peso, axis=1)
    df['volumen_ponderado'] = df['volumen'] * df['peso']

    df_resultado = df.groupby(['id_estacion', 'producto']).agg(
        vsp_ponderada=('volumen_ponderado', 'sum')
    ).reset_index()

    df_resultado['vdp_ponderada'] = df_resultado['vsp_ponderada'] / 7.0
    return df_resultado


@st.cache_data
def obtener_vdp_diario_12w():
    """Obtiene el promedio por día de la semana desde la vista de Supabase con normalización."""
    try:
        data = db.obtener_venta_promedio_dia_semana_12w()
        df = pd.DataFrame(data)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return df

    df = df.copy()
    df["id_estacion"] = df["id_estacion"].astype(str).str.strip()
    df["producto"] = df["producto"].astype(str).str.strip().str.capitalize()
    return df


@st.cache_data
def obtener_ventas_estimadas_diarias():
    """
    Calcula la venta estimada diaria por estación/producto a partir de la tabla de ventas.
    Si la tabla ventas no tiene registros, cae a la visión histórica de 12 semanas.
    """
    try:
        df_ventas = pd.DataFrame(db.obtener_ventas())
    except Exception:
        df_ventas = pd.DataFrame()

    if df_ventas.empty:
        return pd.DataFrame()

    df_ventas = df_ventas.copy()

    if 'fecha' in df_ventas.columns:
        df_ventas['fecha'] = pd.to_datetime(df_ventas['fecha'], errors='coerce')
        df_ventas = df_ventas.dropna(subset=['fecha'])
        df_ventas['dia_index'] = df_ventas['fecha'].dt.weekday
    else:
        df_ventas['dia_index'] = 0

    if 'id_estacion' in df_ventas.columns:
        df_ventas['id_estacion'] = df_ventas['id_estacion'].astype(str).str.strip()
    if 'producto' in df_ventas.columns:
        df_ventas['producto'] = df_ventas['producto'].astype(str).str.strip().str.capitalize()
    if 'volumen' in df_ventas.columns:
        df_ventas['volumen'] = pd.to_numeric(df_ventas['volumen'], errors='coerce').fillna(0.0)

    fecha_hoy = pd.Timestamp.today().normalize()
    fecha_limite = fecha_hoy - pd.DateOffset(weeks=12)
    df_ventas = df_ventas[df_ventas['fecha'] >= fecha_limite]

    if df_ventas.empty:
        return pd.DataFrame()

    df_estimado = (
        df_ventas.groupby(['id_estacion', 'producto', 'dia_index'], as_index=False)['volumen']
        .mean()
        .rename(columns={'volumen': 'venta_estimada_dia'})
    )
    df_estimado['venta_estimada_dia'] = pd.to_numeric(df_estimado['venta_estimada_dia'], errors='coerce').fillna(0.0)
    return df_estimado


@st.cache_data
def obtener_factores_estacionalidad_dia():
    """
    Cruza la VDP ponderada con la venta promedio por día de la semana, pero prioriza
    una venta estimada diaria real calculada desde la tabla de ventas cuando existe historial.
    """
    df_ponderados = obtener_calculos_combustible()
    df_diarios = obtener_vdp_diario_12w()
    df_ventas_estimadas = obtener_ventas_estimadas_diarias()

    if df_ponderados.empty or df_diarios.empty:
        return pd.DataFrame()

    if 'volumen' in df_diarios.columns:
        df_diarios = df_diarios.rename(columns={'volumen': 'vp_dia'})

    if 'dia_de_la_semana' in df_diarios.columns:
        df_diarios['dia_index'] = df_diarios['dia_de_la_semana'].apply(
            lambda x: x.strip().lower() if isinstance(x, str) else x
        )
        df_diarios['dia_index'] = df_diarios['dia_index'].map({
            'lunes': 0, 'monday': 0,
            'martes': 1, 'tuesday': 1,
            'miércoles': 2, 'miercoles': 2, 'wednesday': 2,
            'jueves': 3, 'thursday': 3,
            'viernes': 4, 'friday': 4,
            'sábado': 5, 'sabado': 5, 'saturday': 5,
            'domingo': 6, 'sunday': 6,
        })

    if 'dia_index' not in df_diarios.columns:
        df_diarios['dia_index'] = pd.to_numeric(df_diarios.get('dia_index', 0), errors='coerce').fillna(0)

    if not df_ventas_estimadas.empty:
        df_ventas_estimadas = df_ventas_estimadas.copy()
        df_ventas_estimadas['id_estacion'] = df_ventas_estimadas['id_estacion'].astype(str).str.strip()
        df_ventas_estimadas['producto'] = df_ventas_estimadas['producto'].astype(str).str.strip().str.capitalize()
        df_ventas_estimadas['dia_index'] = pd.to_numeric(df_ventas_estimadas['dia_index'], errors='coerce').fillna(0).astype(int)

    df_factor = pd.merge(
        df_diarios,
        df_ponderados[['id_estacion', 'producto', 'vdp_ponderada']],
        on=['id_estacion', 'producto'],
        how='inner'
    )

    if not df_ventas_estimadas.empty:
        df_factor = pd.merge(
            df_factor,
            df_ventas_estimadas[['id_estacion', 'producto', 'dia_index', 'venta_estimada_dia']],
            on=['id_estacion', 'producto', 'dia_index'],
            how='left'
        )
        df_factor['venta_proyectada_dia'] = df_factor['venta_estimada_dia'].combine_first(df_factor.get('vp_dia', pd.Series(0.0, index=df_factor.index)))
    else:
        df_factor['venta_proyectada_dia'] = df_factor['vp_dia']

    df_factor['factor_dia'] = df_factor.apply(
        lambda row: row['venta_proyectada_dia'] / row['vdp_ponderada'] if row['vdp_ponderada'] > 0 else 1.0,
        axis=1
    )

    return df_factor


__all__ = [
    'obtener_calculos_combustible',
    'obtener_vdp_diario_12w',
    'obtener_ventas_estimadas_diarias',
    'obtener_factores_estacionalidad_dia',
]

