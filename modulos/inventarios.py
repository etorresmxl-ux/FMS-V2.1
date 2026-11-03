import streamlit as st
import pandas as pd
from datetime import date
from servicios.validacion import ValidadorInventario


@st.cache_data(ttl=60)
def cargar_estaciones_usuario(supabase_client, usuario: str):
    validador = ValidadorInventario(supabase_client)
    ids = validador.obtener_estaciones_por_usuario(usuario)
    if not ids:
        return pd.DataFrame(columns=["id_estacion", "nombre", "plaza"])

    res_est = supabase_client.table("estaciones") \
        .select("id_estacion, nombre, plaza") \
        .in_("id_estacion", ids) \
        .execute()
    return pd.DataFrame(res_est.data or [])


def render_inventarios(supabase_client, usuario_actual: str):
    st.subheader("Gestión de Inventarios")

    fecha_seleccionada = st.date_input(
        "Seleccione la fecha de inventario",
        value=date.today(),
        key="fecha_inventario_fms"
    )

    df_estaciones = cargar_estaciones_usuario(supabase_client, usuario_actual)
    if df_estaciones.empty:
        st.warning("No tienes estaciones asignadas o registradas en el sistema.")
        return

    ids_estaciones = df_estaciones["id_estacion"].tolist()
    validador = ValidadorInventario(supabase_client)

    df_inv = validador.obtener_inventario_lote(
        usuario=usuario_actual,
        id_estacion=ids_estaciones,
        fecha=fecha_seleccionada,
        producto=None
    )

    res_tanques = supabase_client.table("tanques_estaciones") \
        .select("id_estacion, producto") \
        .in_("id_estacion", ids_estaciones) \
        .execute()

    tanques_por_estacion = {}
    if res_tanques.data:
        for item in res_tanques.data:
            est = item["id_estacion"]
            prod = str(item["producto"]).lower().strip()
            tanques_por_estacion.setdefault(est, set()).add(prod)

    df_matriz = df_estaciones.copy()

    df_pivot = pd.DataFrame()
    if not df_inv.empty and {"producto", "volumen"}.issubset(df_inv.columns):
        df_inv = df_inv.copy()
        df_inv["producto"] = df_inv["producto"].astype(str).str.lower().str.strip()
        df_pivot = df_inv.pivot_table(
            index="id_estacion",
            columns="producto",
            values="volumen",
            aggfunc="first"
        )

    for prod in ["regular", "premium", "diesel"]:
        valores_columna = []
        for _, row in df_estaciones.iterrows():
            est_id = row["id_estacion"]
            productos_permitidos = tanques_por_estacion.get(est_id, set())

            if prod not in productos_permitidos:
                valores_columna.append(None)
                continue

            if not df_pivot.empty and est_id in df_pivot.index and prod in df_pivot.columns:
                val = df_pivot.loc[est_id, prod]
                valores_columna.append(int(val) if pd.notna(val) else 0)
            else:
                valores_columna.append(0)

        df_matriz[prod] = valores_columna

    df_editado = st.data_editor(
        df_matriz,
        height=600,
        column_config={
            "id_estacion": st.column_config.TextColumn("ID Estación", disabled=True),
            "nombre": st.column_config.TextColumn("Nombre", disabled=True),
            "plaza": st.column_config.TextColumn("Plaza", disabled=True),
            "regular": st.column_config.NumberColumn("Regular", min_value=0, step=1, format="%,d"),
            "premium": st.column_config.NumberColumn("Premium", min_value=0, step=1, format="%,d"),
            "diesel": st.column_config.NumberColumn("Diesel", min_value=0, step=1, format="%,d"),
        },
        hide_index=True,
        key=f"editor_inventarios_{usuario_actual}_{fecha_seleccionada}"
    )

    if st.button("Guardar Cambios de Inventario", type="primary"):
        valido, mensaje, registros = validador.validar_y_normalizar(df_editado, usuario_actual)

        if not valido:
            st.error(mensaje)
            return

        payload = []
        for reg in registros:
            payload.append({
                "id_estacion": reg["id_estacion"],
                "usuario": usuario_actual,
                "fecha": str(fecha_seleccionada),
                "producto": reg["producto"],
                "volumen": reg["volumen"]
            })

        if not payload:
            st.info("No hay cambios para guardar.")
            return

        res = supabase_client.table("inventarios").upsert(
            payload,
            on_conflict="id_estacion,fecha,producto"
        ).execute()

        if hasattr(res, "error") and res.error:
            st.error(f"Error al guardar inventarios: {res.error}")
            return

        st.success("¡Inventarios guardados y validados correctamente en Supabase!")
        st.rerun()
