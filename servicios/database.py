import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    """Inicializa y retorna una única instancia de la conexión a Supabase."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except KeyError as e:
        st.error(f"Falta configurar la credencial secreta en .streamlit/secrets.toml: {e}")
        st.stop()
    return create_client(url, key)
