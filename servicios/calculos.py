import pandas as pd
import streamlit as st
import database as db

@st.cache_data
def obtener_calculos_combustible():
    """
    Servicio centralizado que obtiene la venta semanal de las últimas 12 semanas, 
    calcula la VSP ponderada y la VDP ponderada por estación y producto.
    """
    data = db.obtener_venta_semanal_promedio_12w()
    df = pd.DataFrame(data)

    if df.empty:
        return pd.DataFrame()

    # Normalizar identificadores y productos
    df["id_estacion"] = df["id_estacion"].astype(str).str.strip()
    df["producto"] = df["producto"].astype(str).str.strip().str.capitalize()

    # 1. Ordenar de la semana más reciente a la más antigua por estación y producto
    df = df.sort_values(by=['id_estacion', 'producto', 'semana'], ascending=[True, True, False])

    # 2. Ranking de recencia (1 = la más reciente)
    df['ranking_semana'] = df.groupby(['id_estacion', 'producto']).cumcount() + 1

    # 3. Ponderaciones: 50% (sem 1-2), 30% (sem 3-8), 20% (sem 9-12)
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

    # 4. Cálculo VSP y VDP Ponderada
    df['volumen_ponderado'] = df['volumen'] * df['peso']

    df_resultado = df.groupby(['id_estacion', 'producto']).agg(
        vsp_ponderada=('volumen_ponderado', 'sum')
    ).reset_index()

    df_resultado['vdp_ponderada'] = df_resultado['vsp_ponderada'] / 7.0

    return df_resultado

@st.cache_data
def obtener_vdp_diario_12w():
    """ 
    Obtiene el promedio por día de la semana (Lunes, Martes, etc.) de las últimas 12 semanas desde Supabase[cite: 3]. 
    """
    data = db.obtener_venta_promedio_dia_semana_12w()
    df = pd.DataFrame(data)
    
    if not df.empty:
        df["id_estacion"] = df["id_estacion"].astype(str).str.strip()
        df["producto"] = df["producto"].astype(str).str.strip().str.capitalize()
        
    return df

@st.cache_data
def obtener_factores_estacionalidad_dia():
    """
    Cruza la VDP Ponderada con la Venta Promedio por Día de la Semana para calcular 
    la venta proyectada específica por día sin redundancias.
    """
    df_ponderados = obtener_calculos_combustible()
    df_diarios = obtener_vdp_diario_12w()

    if df_ponderados.empty or df_diarios.empty:
        return pd.DataFrame()

    if 'volumen' in df_diarios.columns:
        df_diarios = df_diarios.rename(columns={'volumen': 'vp_dia'})

    # Cruzar datos por estación y producto con claves limpias
    df_factor = pd.merge(
        df_diarios,
        df_ponderados[['id_estacion', 'producto', 'vdp_ponderada']],
        on=['id_estacion', 'producto'],
        how='inner'
    )

    if df_factor.empty:
        return pd.DataFrame()

    # Cálculo del factor y asignación directa de la venta del día
    df_factor['factor_dia'] = df_factor.apply(
        lambda row: row['vp_dia'] / row['vdp_ponderada'] if row['vdp_ponderada'] > 0 else 1.0, 
        axis=1
    )

    df_factor['venta_proyectada_dia'] = df_factor['vp_dia']

    return df_factor
