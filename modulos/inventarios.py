import streamlit as st
import pandas as pd
from datetime import date
import database as db
from servicios import validacion


def mostrar_inventarios():
    st.header("📋 Consulta y Actualización de Inventarios")

    datos_estaciones_usuario = db.obtener_estaciones_usuario()
    datos_inventarios = db.obtener_inventarios()

    if not datos_estaciones_usuario:
        st.warning("No hay asignaciones de estaciones y usuarios registradas en la base de datos.")
        return

    df_est_usu = pd.DataFrame(datos_estaciones_usuario)

    col_fecha, col_usuario = st.columns(2)

    with col_fecha:
        fecha_seleccionada = st.date_input(
            "Selecciona la fecha:",
            value=date.today(),
            key="filtro_fecha_inventarios"
        )

    with col_usuario:
        usuarios_disponibles = sorted(list(df_est_usu["usuario"].unique()))
        usuario_seleccionado = st.selectbox(
            "Selecciona el usuario:",
            options=usuarios_disponibles,
            key="filtro_usuario_inventarios"
        )

    df_estaciones_filtradas = df_est_usu[df_est_usu["usuario"] == usuario_seleccionado].copy()

    if df_estaciones_filtradas.empty:
        st.info("No hay estaciones registradas para el usuario seleccionado.")
        return

    if "estaciones" in df_estaciones_filtradas.columns:
        df_estaciones_filtradas["nombre"] = df_estaciones_filtradas["estaciones"].apply(
            lambda x: x.get("nombre") if isinstance(x, dict) else ""
        )
        df_estaciones_filtradas["plaza"] = df_estaciones_filtradas["estaciones"].apply(
            lambda x: x.get("plaza") if isinstance(x, dict) else ""
        )

    productos = ["Regular", "Premium", "Diesel"]

    if datos_inventarios:
        df_inventarios = pd.DataFrame(datos_inventarios)
        df_inventarios["fecha"] = pd.to_datetime(df_inventarios["fecha"]).dt.date
        df_inv_filtrado = df_inventarios[df_inventarios["fecha"] == fecha_seleccionada]

        if not df_inv_filtrado.empty:
            df_pivot = df_inv_filtrado.pivot_table(
                index="id_estacion",
                columns="producto",
                values="volumen",
                aggfunc="sum",
                fill_value=0
            ).reset_index()

            df_resultado = pd.merge(
                df_estaciones_filtradas[["id_estacion", "nombre", "plaza"]],
                df_pivot,
                on="id_estacion",
                how="left"
            ).fillna(0)
        else:
            df_resultado = df_estaciones_filtradas[["id_estacion", "nombre", "plaza"]].copy()
            for prod in productos:
                df_resultado[prod] = 0
    else:
        df_resultado = df_estaciones_filtradas[["id_estacion", "nombre", "plaza"]].copy()
        for prod in productos:
            df_resultado[prod] = 0

    for col in productos:
        if col not in df_resultado.columns:
            df_resultado[col] = 0

    df_resultado = df_resultado[["id_estacion", "nombre", "plaza"] + productos]

    df_resultado = validacion.validar_matriz_productos(df_estaciones_filtradas, df_resultado, productos)

    for prod in productos:
        if prod in df_resultado.columns:
            df_resultado[prod] = pd.to_numeric(df_resultado[prod], errors="coerce").fillna(0)

    column_config = {
        "id_estacion": st.column_config.TextColumn("ID", width="small", disabled=True),
        "nombre": st.column_config.TextColumn("Estación", width="medium", disabled=True),
        "plaza": st.column_config.TextColumn("Plaza", width="medium", disabled=True),
        "Regular": st.column_config.NumberColumn("Regular", width="small", min_value=0, step=1, format="%d"),
        "Premium": st.column_config.NumberColumn("Premium", width="small", min_value=0, step=1, format="%d"),
        "Diesel": st.column_config.NumberColumn("Diesel", width="small", min_value=0, step=1, format="%d")
    }

    df_editado = st.data_editor(
        df_resultado,
        width='stretch',
        hide_index=True,
        column_config=column_config,
        height=600,
        key="editor_inventarios"
    )

    st.write("")
    if st.button("Guardar Cambios de Inventario", type="primary", use_container_width=True):
        try:
            registros = []
            for _, row in df_editado.iterrows():
                for producto in productos:
                    volumen = pd.to_numeric(row.get(producto, 0), errors="coerce")
                    if pd.notna(volumen):
                        registros.append({
                            "id_estacion": row["id_estacion"],
                            "fecha": str(fecha_seleccionada),
                            "producto": producto,
                            "volumen": float(volumen)
                        })

            if not registros:
                st.info("No hay valores para guardar.")
                st.stop()

            supabase = db._require_supabase()
            for registro in registros:
                id_estacion = registro["id_estacion"]
                fecha_str = str(registro["fecha"])
                producto = db._normalizar_producto(registro["producto"])

                existente = (
                    supabase.table("inventarios")
                    .select("*")
                    .eq("id_estacion", id_estacion)
                    .eq("fecha", fecha_str)
                    .eq("producto", producto)
                    .limit(1)
                    .execute()
                )

                if existente.data:
                    supabase.table("inventarios") \
                        .update({"volumen": registro["volumen"]}) \
                        .eq("id_estacion", id_estacion) \
                        .eq("fecha", fecha_str) \
                        .eq("producto", producto) \
                        .execute()
                else:
                    supabase.table("inventarios").insert({
                        "id_estacion": id_estacion,
                        "fecha": fecha_str,
                        "producto": producto,
                        "volumen": registro["volumen"]
                    }).execute()

            st.success("¡Cambios guardados exitosamente!")
            st.rerun()

        except Exception as e:
            st.error(f"No se pudieron guardar los inventarios: {e}")
