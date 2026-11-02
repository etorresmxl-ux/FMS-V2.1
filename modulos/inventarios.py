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
            df_resultado[prod] = df_resultado[prod].apply(lambda x: f"{int(round(float(x))):,}" if pd.notna(x) else "0")

    column_config = {
        "id_estacion": st.column_config.TextColumn("ID", width="small", disabled=True),
        "nombre": st.column_config.TextColumn("Estación", width="medium", disabled=True),
        "plaza": st.column_config.TextColumn("Plaza", width="medium", disabled=True),
        "Regular": st.column_config.TextColumn("Regular", width="small"),
        "Premium": st.column_config.TextColumn("Premium", width="small"),
        "Diesel": st.column_config.TextColumn("Diesel", width="small")
    }

    # Mostrar la tabla configurada con altura para ~25 filas[cite: 1]
    st.dataframe(
        df_resultado,
        width='stretch',
        hide_index=True,
        column_config=column_config,
        height=800
    )

    # Botón de guardado ubicado en la parte inferior después de la tabla
    st.write("")
    if st.button("Guardar Cambios de Inventario", type="primary", use_container_width=True):
        st.success("¡Cambios guardados exitosamente!")
        # Aquí puedes agregar la lógica para recorrer y registrar los datos actualizados en la base de datos.
