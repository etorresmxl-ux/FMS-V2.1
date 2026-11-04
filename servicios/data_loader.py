import streamlit as st
import pandas as pd

class DataLoaderService:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    @st.cache_data(ttl=3600)
    def cargar_datos_maestros(_self) -> dict:
        """
        Carga y cachea por 1 hora los datos maestros estáticos (usuarios, estaciones, tanques, vdp, factores).
        """
        try:
            usuarios = ["Brenda", "Daniela", "Jazmin", "Yesenia"]

            res_usr = _self.supabase.table("estaciones_usuario").select("id_estacion, usuario, estaciones(id_estacion, nombre, plaza)").execute()
            df_usr = pd.DataFrame(res_usr.data) if res_usr.data else pd.DataFrame()

            res_tanques = _self.supabase.table("tanques_estaciones").select("id_estacion, producto, limite_max").execute()
            df_tanques = pd.DataFrame(res_tanques.data) if res_tanques.data else pd.DataFrame()
            if not df_tanques.empty:
                df_tanques["limite_min"] = 5000

            res_vdp = _self.supabase.table("vdp_ponderada_12w").select("id_estacion, producto, vdp_ponderada").execute()
            df_vdp = pd.DataFrame(res_vdp.data) if res_vdp.data else pd.DataFrame()

            res_diasemanal = _self.supabase.table("factor_venta_diasemanal").select("id_estacion, producto, diasemanal, factor").execute()
            df_diasemanal = pd.DataFrame(res_diasemanal.data) if res_diasemanal.data else pd.DataFrame()

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
        Carga de forma independiente los registros de inventarios desde Supabase.
        """
        try:
            res_inv = _self.supabase.table("inventarios").select("id_estacion, fecha, producto, volumen").order("fecha", desc=True).execute()
            return pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Error al cargar los inventarios desde Supabase: {e}")
            return pd.DataFrame()

    def invalidar_inventarios(self):
        """
        Limpia de forma explícita y exclusiva la caché de los inventarios 
        al momento de guardar o actualizar información en la tabla.
        """
        self.cargar_inventarios.clear()
