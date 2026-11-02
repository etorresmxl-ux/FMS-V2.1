import pandas as pd
import database as db
import streamlit as st

@st.cache_data 
def obtener_calculos_combustible():
    """ Obtiene la venta semanal ponderada desde la vista de Supabase, aplicando normalización estricta de texto al inicio. """
    try:
        data = db.obtener_venta_semanal_promedio_12w()
        df = pd.DataFrame(data)
    except Exception:
        df = pd.DataFrame()
        
    if df.empty:
        return pd.DataFrame()

    # 1. Normalización estricta e inmediata de claves y productos
    df["id_estacion"] = df["id_estacion"].astype(str).str.strip()
    df["producto"] = df["producto"].astype(str).str.strip().str.capitalize()

    # 2. Ordenar de la semana más reciente a la más antigua
    df = df.sort_values(by=['id_estacion', 'producto', 'semana'], ascending=[True, True, False])

    # 3. Ranking de recencia (1 = la más reciente)
    df['ranking_semana'] = df.groupby(['id_estacion', 'producto']).cumcount() + 1

    # 4. Ponderaciones: 50% (sem 1-2), 30% (sem 3-8), 20% (sem 9-12)
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

    # 5. Cálculo VSP y VDP Ponderada
    df['volumen_ponderado'] = df['volumen'] * df['peso']

    df_resultado = df.groupby(['id_estacion', 'producto']).agg(
        vsp_ponderada=('volumen_ponderado', 'sum')
    ).reset_index()

    df_resultado['vdp_ponderada'] = df_resultado['vsp_ponderada'] / 7.0

    return df_resultado


@st.cache_data 
def obtener_vdp_diario_12w(): 
    """ Obtiene el promedio por día de la semana desde la vista de Supabase con normalización numérica. """ 
    try: 
        data = db.obtener_venta_promedio_dia_semana_12w() 
        df = pd.DataFrame(data) 
    except Exception: 
        df = pd.DataFrame()

    if not df.empty:
        df["id_estacion"] = df["id_estacion"].astype(str).str.strip()
        df["producto"] = df["producto"].astype(str).str.strip().str.capitalize()
        # Asegurar que el día de la semana sea numérico entero (1=Lunes ... 7=Domingo)
        if "dia_de_la_semana" in df.columns:
            df["dia_de_la_semana"] = pd.to_numeric(df["dia_de_la_semana"], errors="coerce")

    return df


@st.cache_data 
def obtener_factores_estacionalidad_dia(): 
    """ Cruza la VDP Ponderada con la Venta Promedio por Día de la Semana para calcular la venta proyectada específica por día de manera limpia. """ 
    df_ponderados = obtener_calculos_combustible() 
    df_diarios = obtener_vdp_diario_12w()
    
    if df_diarios.empty:
        return pd.DataFrame()
        
    return df_diarios
