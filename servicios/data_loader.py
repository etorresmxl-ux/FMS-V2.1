import streamlit as st
import pandas as pd

class DataLoaderService:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    @st.cache_data(ttl=3600)
    def cargar_datos_maestros(_self) -> dict:
        """
        Carga y cachea por 1 hora (3600 segundos) exclusivamente los datos necesarios:
        - Listado fijo de usuarios autorizados.
        - Estaciones y asignación de usuarios.
        - Tanques (con limite_max y limite_min fijo en 5000).
        - VDP Ponderada (solo vdp_ponderada).
        - Factor venta día semanal (solo factor).
        - Inventarios más recientes.
        """
        try:
            # 1. Listado fijo de usuarios autorizado
            usuarios = ["Brenda", "Daniela", "Jazmin", "Yesenia"]

            # 2. Estaciones y asignación de usuarios
            res_usr = _self.supabase.table("estaciones_usuario").select("id_estacion, usuario, estaciones(id_estacion, nombre, plaza)").execute()
            df_usr = pd.DataFrame(res_usr.data) if res_usr.data else pd.DataFrame()

            # 3. Tanques (solo id_estacion, producto, limite_max; límite mínimo fijo en 5000)
            res_tanques = _self.supabase.table("tanques_estaciones").select("id_estacion, producto, limite_max").execute()
            df_tanques = pd.DataFrame(res_tanques.data) if res_tanques.data else pd.DataFrame()
            if not df_tanques.empty:
                df_tanques["limite_min"] = 5000

            # 4. VDP Ponderada (solo id_estacion, producto, vdp_ponderada)
            res_vdp = _self.supabase.table("vdp_ponderada_12w").select("id_estacion, producto, vdp_ponderada").execute()
            df_vdp = pd.DataFrame(res_vdp.data) if res_vdp.data else pd.DataFrame()

            # 5. Factor de venta día semanal (solo id_estacion, producto, diasemanal, factor)
            res_diasemanal = _self.supabase.table("factor_venta_diasemanal").select("id_estacion, producto, diasemanal, factor").execute()
            df_diasemanal = pd.DataFrame(res_diasemanal.data) if res_diasemanal.data else pd.DataFrame()

            # 6. Inventarios (registros más recientes ordenados por fecha)
            res_inv = _self.supabase.table("inventarios").select("id_estacion, fecha, producto, volumen").order("fecha", desc=True).execute()
            df_inventarios = pd.DataFrame(res_inv.data) if res_inv.data else pd.DataFrame()

            return {
                "usuarios": usuarios,
                "estaciones_usuario": df_usr,
                "tanques_estaciones": df_tanques,
                "vdp_ponderada": df_vdp,
                "factor_diasemanal": df_diasemanal,
                "inventarios": df_inventarios
            }
        except Exception as e:
            st.error(f"Error al cargar los datos maestros desde Supabase: {e}")
            return {}

    def invalidar_inventarios(self):
        """
        Limpia de forma explícita la caché del data loader para forzar 
        la recarga de los inventarios actualizados desde Supabase.
        """
        self.cargar_datos_maestros.clear()
