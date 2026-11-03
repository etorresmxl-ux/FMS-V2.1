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
                fill_value=None  # Usar None para mostrar celdas vacías si no hay datos previos
            ).reset_index()

            df_resultado = pd.merge(
                df_estaciones_filtradas[["id_estacion", "nombre", "plaza"]],
                df_pivot,
                on="id_estacion",
                how="left"
            )
        else:
            df_resultado = df_estaciones_filtradas[["id_estacion", "nombre", "plaza"]].copy()
            for prod in productos:
                df_resultado[prod] = None
    else:
        df_resultado = df_estaciones_filtradas[["id_estacion", "nombre", "plaza"]].copy()
        for prod in productos:
            df_resultado[prod] = None

    for col in productos:
        if col not in df_resultado.columns:
            df_resultado[col] = None

    df_resultado = df_resultado[["id_estacion", "nombre", "plaza"] + productos]

    df_resultado = validacion.validar_matriz_productos(df_estaciones_filtradas, df_resultado, productos)

    # Limpieza numérica sin forzar ceros en valores vacíos (permite celdas en blanco)
    for prod in productos:
        if prod in df_resultado.columns:
            df_resultado[prod] = pd.to_numeric(df_resultado[prod], errors="coerce")

    # Configuración de columnas permitiendo edición numérica en regular, premium y diesel
    column_config = {
        "id_estacion": st.column_config.TextColumn("ID", width="small", disabled=True),
        "nombre": st.column_config.TextColumn("Estación", width="medium", disabled=True),
        "plaza": st.column_config.TextColumn("Plaza", width="medium", disabled=True),
        "Regular": st.column_config.NumberColumn("Regular", width="small", min_value=0, step=1, format="%d"),
        "Premium": st.column_config.NumberColumn("Premium", width="small", min_value=0, step=1, format="%d"),
        "Diesel": st.column_config.NumberColumn("Diesel", width="small", min_value=0, step=1, format="%d")
    }

    # Usamos st.data_editor para habilitar la escritura en la tabla
    df_editado = st.data_editor(
        df_resultado,
        width='stretch',
        hide_index=True,
        column_config=column_config,
        height=600,
        key="editor_inventarios"
    )

    # Botón de guardado ubicado en la parte inferior después de la tabla con integración a Supabase
    st.write("")
    if st.button("Guardar/Actualizar Inventario", type="primary", use_container_width=True):
        try:
            exitos = 0
            
            # Iterar sobre cada fila del DataFrame editado para registrar los cambios en Supabase
            for _, row in df_editado.iterrows():
                id_estacion = row["id_estacion"]
                
                for prod in productos:
                    if prod in row:
                        volumen_val = row[prod]
                        
                        # Llamada a la función de inserción/eliminación en la base de datos
                        db.insertar_inventario(
                            id_estacion=id_estacion,
                            fecha=fecha_seleccionada,
                            producto=prod,
                            volumen=volumen_val
                        )
                        exitos += 1
                        
            st.success("¡Inventarios guardados y registrados en Supabase exitosamente!")
            st.rerun()
        except Exception as e:
            st.error(f"Ocurrió un error al guardar los inventarios en la base de datos: {e}")
