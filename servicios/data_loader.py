import streamlit as st
import pandas as pd

class DataLoaderService:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    @st.cache_data(ttl=3600)
    def cargar_datos_maestros(_self) -> dict:
        """
        Carga y cachea por 1 hora los datos maestros estáticos (usuarios, estaciones, tanques, vdp, factores).
        Normaliza todos los campos varchar a minúsculas y sin espacios.
        """
        try:
            usuarios = ["Brenda", "Daniela", "Jazmin", "Yesenia"]

            # Estaciones y usuarios
            res_usr = _self.supabase.table("estaciones_usuario").select("id_estacion, usuario, estaciones(id_estacion, nombre, plaza)").execute()
            df_usr = pd.DataFrame(res_usr.data) if res_usr.data else pd.DataFrame()
            
            if not df_usr.empty:
                df_usr["id_estacion"] = df_usr["id_estacion"].astype(str).str.lower().str.strip()
                df_usr["usuario"] = df_usr["usuario"].astype(str).str.lower().str.strip()

            # Tanques de estaciones
            res_tanques = _self.supabase.table("tanques_estaciones").select("id_estacion, producto, limite_max").execute()
            df_tanques = pd.DataFrame(res_tanques.data) if res_tanques.data else pd.DataFrame()
            if not df_tanques.empty:
                df_tanques["id_estacion"] = df_tanques["id_estacion"].astype(str).str.lower().str.strip()
                df_tanques["producto"] = df_tanques["producto"].astype(str).str.lower().str.strip()
                df_tanques["limite_min"] = 5000

            # VDP Ponderada
            res_vdp = _self.supabase.table("vdp_ponderada_12w").select("id_estacion, producto, vdp_ponderada").execute()
            df_vdp = pd.DataFrame(res_vdp.data) if res_vdp.data else pd.DataFrame()
            if not df_vdp.empty:
                df_vdp["id_estacion"] = df_vdp["id_estacion"].astype(str).str.lower().str.strip()
                df_vdp["producto"] = df_vdp["producto"].astype(str).str.lower().str.strip()

            # Factores de venta día semanal
            res_diasemanal = _self.supabase.table("factor_venta_diasemanal").select("id_estacion, producto, diasemanal, factor").execute()
            df_diasemanal = pd.DataFrame(res_diasemanal.data) if res_diasemanal.data else pd.DataFrame()
            if not df_diasemanal.empty:
                df_diasemanal["id_estacion"] = df_diasemanal["id_estacion"].astype(str).str.lower().str.strip()
                df_diasemanal["producto"] = df_diasemanal["producto"].astype(str).str.lower().str.strip()

            return {
                "usuarios": usuarios,
                "estaciones_usuario": df_usr,
                "tanques_estaciones": df_tanques,
                "vdp_ponderada": df_vdp,
                "factor_diasemanal": df_diasemanal
            }
        except Exception as e:
            st.error(f"Error al cargar los datos maestros desde Supabase: {e}")
            return {}

    @st.cache_data(ttl=3600)
    def cargar_inventarios(_self) -> pd.DataFrame:
        """
        Carga, normaliza y estructura los registros de inventarios desde Supabase.
        Estructura estándar garantizada para joins de 4 variables:
        - id_estacion
        - fecha
        - producto
        - volumen
        """
        try:
            res_inv = _self.supabase.table("inventarios").select("id_estacion, fecha, producto, volumen").order("fecha", desc=True).execute()
            df = pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()

            columnas_requeridas = ["id_estacion", "fecha", "producto", "volumen"]
            if not df.empty:
                for col in columnas_requeridas:
                    if col not in df.columns:
                        df[col] = None

                # Normalización estricta de tipos y minúsculas para campos varchar
                df["id_estacion"] = df["id_estacion"].astype(str).str.lower().str.strip()
                df["producto"] = df["producto"].astype(str).str.lower().str.strip()
                df["fecha"] = pd.to_datetime(df["fecha"]).dt.strftime("%Y-%m-%d")
                df["volumen"] = pd.to_numeric(df["volumen"], errors="coerce").fillna(0.0)

                df = df[columnas_requeridas].sort_values(by=["fecha", "id_estacion", "producto"], ascending=[False, True, True])
            else:
                df = pd.DataFrame(columns=columnas_requeridas)

            return df
        except Exception as e:
            st.error(f"Error al cargar los inventarios desde Supabase: {e}")
            return pd.DataFrame(columns=["id_estacion", "fecha", "producto", "volumen"])

    def invalidar_inventarios(self):
        """
        Limpia de forma explícita y exclusiva la caché de los inventarios 
        al momento de guardar o actualizar información en la tabla.
        """
        self.cargar_inventarios.clear()
