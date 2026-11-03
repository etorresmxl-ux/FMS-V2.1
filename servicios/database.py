import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Inicializa y retorna una única instancia de la conexión a Supabase leyendo desde la sección [supabase]."""
    try:
        url = st.secrets["supabase"]["SUPABASE_URL"]
        key = st.secrets["supabase"]["SUPABASE_KEY"]
    except KeyError as e:
        st.error(f"Falta configurar la credencial en la sección [supabase] de los secretos: {e}")
        st.stop()
    return create_client(url, key)
