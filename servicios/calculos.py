import pandas as pd 
import database as db
import streamlit as st
import pandas as pd
import database as db

@st.cache_data 
def obtener_calculos_combustible(): 
    """ 
    Obtiene la venta semanal ponderada desde la vista de Supabase, 
    aplicando normalización estricta y la regla de ponderación (50%, 30%, 20%) 
    para calcular la vdp_ponderada. 
    """ 
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


def obtener_factores_estacionalidad_dia(): 
    """ 
    Obtiene los datos de la vista de estacionalidad por día de la semana[cite: 3], 
    calcula el factor de estacionalidad y lo multiplica estrictamente por la 
    vdp_ponderada de las 12 semanas. 
    """ 
    try: 
        data = db.obtener_venta_promedio_dia_de_la_semana_12w() 
        df = pd.DataFrame(data) 
    except Exception: 
        df = pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # Normalización estricta
    df["id_estacion"] = df["id_estacion"].astype(str).str.strip()
    df["producto"] = df["producto"].astype(str).str.strip().str.capitalize()
    df["dia_de_la_semana"] = pd.to_numeric(df["dia_de_la_semana"], errors="coerce")
    df["volumen"] = pd.to_numeric(df["volumen"], errors="coerce").fillna(0.0)

    # Promedio histórico general de los días para sacar la proporción base
    promedio_general = df.groupby(["id_estacion", "producto"])["volumen"].mean().reset_index(name="volumen_medio_general")
    df = pd.merge(df, promedio_general, on=["id_estacion", "producto"], how="left")

    # Factor de estacionalidad relativo del día
    df["factor_estacionalidad"] = df.apply(
        lambda row: row["volumen"] / row["volumen_medio_general"] if row["volumen_medio_general"] > 0 else 1.0, 
        axis=1
    )

    # Integración con la VDP ponderada real de 12 semanas
    df_pond = obtener_calculos_combustible()
    if not df_pond.empty:
        df = pd.merge(df, df_pond[["id_estacion", "producto", "vdp_ponderada"]], on=["id_estacion", "producto"], how="left")
        df["vdp_ponderada"] = df["vdp_ponderada"].fillna(df["volumen_medio_general"])
    else:
        df["vdp_ponderada"] = df["volumen_medio_general"]

    # Generación de la columna clave 'vp_dia' (VDP Ponderada * Factor de Estacionalidad)
    df["vp_dia"] = df["vdp_ponderada"] * df["factor_estacionalidad"]
    df["dia_index"] = df["dia_de_la_semana"]

    return df
