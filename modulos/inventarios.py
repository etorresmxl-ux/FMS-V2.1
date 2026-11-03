import streamlit as st
import pandas as pd
from datetime import date
from servicios.validacion import ValidadorInventario

def render_inventarios(supabase_client, usuario_actual: str):
    st.subheader("Gestión de Inventarios")

    # 1. Filtro por fecha
    fecha_seleccionada = st.date_input("Seleccione la fecha de inventario", value=date.today())

    # 2. Obtener estaciones permitidas para el usuario actual desde Supabase
    @st.cache_data(ttl=60)
    def cargar_estaciones_usuario(usuario):
        # Consultar la relación de estaciones por usuario
        res_usr = supabase_client.table("estaciones_usuario").select("id_estacion").eq("usuario", usuario).execute()
        ids = [item["id_estacion"] for item in res_usr.data]
        if not ids:
            return pd.DataFrame()
        
        res_est = supabase_client.table("estaciones").select("id_estacion, nombre, plaza").in_("id_estacion", ids).execute()
        return pd.DataFrame(res_est.data)

    df_estaciones = cargar_estaciones_usuario(usuario_actual)

    if df_estaciones.empty:
        st.warning("No tienes estaciones asignadas o registradas en el sistema.")
        return

    # 3. Buscar registros existentes en la tabla 'inventarios' para las estaciones del usuario y la fecha seleccionada
    ids_estaciones = df_estaciones["id_estacion"].tolist()
    
    res_inv = supabase_client.table("inventarios") \
        .select("id_estacion, producto, volumen") \
        .eq("fecha", str(fecha_seleccionada)) \
        .in_("id_estacion", ids_estaciones) \
        .execute()
    
    df_inv = pd.DataFrame(res_inv.data)

    # 4. Estructurar la matriz combinando estaciones y productos (regular, premium, diesel)
    df_matriz = df_estaciones.copy()
    for prod in ["regular", "premium", "diesel"]:
        df_matriz[prod] = 0

    if not df_inv.empty and "producto" in df_inv.columns and "volumen" in df_inv.columns:
        # Pivotar los datos existentes para que coincidan con las columnas de productos
        df_pivot = df_inv.pivot(index="id_estacion", columns="producto", values="volumen").reset_index()
        for prod in ["regular", "premium", "diesel"]:
            if prod in df_pivot.columns:
                df_matriz[prod] = df_matriz["id_estacion"].map(
                    df_pivot.set_index("id_estacion")[prod]
                ).fillna(0).astype(int)

    st.markdown("Modifique los valores de volumen directamente en la tabla (solo números enteros):")

    # 5. Tabla interactiva con columnas de producto editables
    df_editado = st.data_editor(
        df_matriz,
        column_config={
            "id_estacion": st.column_config.TextColumn("ID Estación", disabled=True),
            "nombre": st.column_config.TextColumn("Nombre", disabled=True),
            "plaza": st.column_config.TextColumn("Plaza", disabled=True),
            "regular": st.column_config.NumberColumn("Regular", min_value=0, step=1, format="%d"),
            "premium": st.column_config.NumberColumn("Premium", min_value=0, step=1, format="%d"),
            "diesel": st.column_config.NumberColumn("Diesel", min_value=0, step=1, format="%d"),
        },
        hide_index=True,
        key=f"editor_inventarios_{usuario_actual}_{fecha_seleccionada}"
    )

    # 6. Botón de guardado y procesamiento mediante el servicio de validación
    if st.button("Guardar Cambios de Inventario", type="primary"):
        validador = ValidadorInventario(supabase_client)
        valido, mensaje, registros = validador.validar_y_normalizar(df_editado, usuario_actual)

        if not valido:
            st.error(mensaje)
        else:
            # Procesar upsert en Supabase asegurando la combinación única (id_estacion, fecha, producto)
            exito = True
            for reg in registros:
                reg["fecha"] = str(fecha_seleccionada)
                res = supabase_client.table("inventarios").upsert(
                    reg, 
                    on_conflict="id_estacion,fecha,producto"
                ).execute()
                if hasattr(res, 'error') and res.error:
                    exito = False
                    st.error(f"Error al guardar estación {reg['id_estacion']}: {res.error}")
                    break

            if exito:
                st.success("¡Inventarios guardados y validados correctamente en Supabase!")
                st.rerun()
