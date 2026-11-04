import datetime
import pandas as pd
import streamlit as st

def render_inventarios(supabase_client, usuario_actual, data_loader):
    st.subheader("Gestión de Inventarios")

    # 1. Cargar datos maestros estáticos e inventarios por separado
    datos_maestros = data_loader.cargar_datos_maestros()
    df_tanques = datos_maestros.get("tanques_estaciones", pd.DataFrame())
    df_usr = datos_maestros.get("estaciones_usuario", pd.DataFrame())

    # Carga dedicada para inventarios con actualización selectiva
    df_inventarios_cache = data_loader.cargar_inventarios()

    # Normalizar usuario actual a minúsculas
    usuario_norm = str(usuario_actual).lower().strip()

    # Obtener las estaciones pertenecientes al usuario actual
    if not df_usr.empty:
        df_usr_filtrado = df_usr[df_usr["usuario"] == usuario_norm]
    else:
        df_usr_filtrado = pd.DataFrame()

    if df_usr_filtrado.empty:
        st.warning(f"El usuario '{usuario_actual}' no tiene estaciones asignadas en este momento.")
        return

    # Extraer la información básica de las estaciones asociadas
    estaciones_list = []
    for _, row in df_usr_filtrado.iterrows():
        raw_id = str(row.get("id_estacion", "")).strip()
        est_data = row.get("estaciones")
        if isinstance(est_data, dict):
            estaciones_list.append({
                "id_estacion_db": raw_id.lower(),
                "id_estacion": raw_id.upper(),
                "nombre": str(est_data.get("nombre", "")).title(),
                "plaza": str(est_data.get("plaza", "")).title()
            })
        elif isinstance(est_data, list) and len(est_data) > 0:
            est_dict = est_data[0]
            estaciones_list.append({
                "id_estacion_db": raw_id.lower(),
                "id_estacion": raw_id.upper(),
                "nombre": str(est_dict.get("nombre", "")).title(),
                "plaza": str(est_dict.get("plaza", "")).title()
            })
        else:
            estaciones_list.append({
                "id_estacion_db": raw_id.lower(),
                "id_estacion": raw_id.upper(),
                "nombre": "",
                "plaza": ""
            })

    df_base_estaciones = pd.DataFrame(estaciones_list).drop_duplicates(subset=["id_estacion_db"])

    # ---------------------------------------------------------
    # 1. FILTRO DE FECHA
    # ---------------------------------------------------------
    col_fecha, _ = st.columns([1, 2])
    with col_fecha:
        fecha_seleccionada = st.date_input("Seleccionar Fecha de Registro", value=datetime.date.today())

    fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")

    # ---------------------------------------------------------
    # 2. CONSTRUCCIÓN DE LA TABLA MATRIZ
    # ---------------------------------------------------------
    df_inv_fecha = pd.DataFrame()
    if not df_inventarios_cache.empty and "fecha" in df_inventarios_cache.columns:
        df_inv_fecha = df_inventarios_cache[df_inventarios_cache["fecha"].astype(str) == fecha_str]

    if not df_inv_fecha.empty and "producto" in df_inv_fecha.columns and "volumen" in df_inv_fecha.columns:
        df_pivot = df_inv_fecha.pivot(index="id_estacion", columns="producto", values="volumen").reset_index()
        df_pivot = df_pivot.rename(columns={"id_estacion": "id_estacion_db"})
    else:
        df_pivot = pd.DataFrame(columns=["id_estacion_db"])

    for prod in ["regular", "premium", "diesel"]:
        if prod not in df_pivot.columns:
            df_pivot[prod] = None

    df_matriz = pd.merge(df_base_estaciones, df_pivot[["id_estacion_db", "regular", "premium", "diesel"]], on="id_estacion_db", how="left")

    df_matriz["Regular"] = df_matriz["regular"]
    df_matriz["Premium"] = df_matriz["premium"]
    df_matriz["Diesel"] = df_matriz["diesel"]

    df_matriz = df_matriz.drop(columns=["regular", "premium", "diesel", "id_estacion_db"], errors="ignore")

    df_matriz = df_matriz.rename(columns={
        "id_estacion": "ID Estacion",
        "nombre": "Nombre",
        "plaza": "Plaza"
    })

    columnas_orden = ["ID Estacion", "Nombre", "Plaza", "Regular", "Premium", "Diesel"]
    df_matriz = df_matriz[columnas_orden]

    # Mostrar la tabla interactiva de edición
    df_editado = st.data_editor(
        df_matriz,
        use_container_width=True,
        hide_index=True,
        height=600,
        disabled=["ID Estacion", "Nombre", "Plaza"],
        column_config={
            "Regular": st.column_config.NumberColumn("Regular", min_value=0, step=1, format="%,d"),
            "Premium": st.column_config.NumberColumn("Premium", min_value=0, step=1, format="%,d"),
            "Diesel": st.column_config.NumberColumn("Diesel", min_value=0, step=1, format="%,d"),
        }
    )

    # ---------------------------------------------------------
    # 3. BOTÓN DE GUARDAR / ACTUALIZAR REGISTRO
    # ---------------------------------------------------------
    if st.button("Guardar / Actualizar Registro", type="primary"):
        registros = []
        for _, row in df_editado.iterrows():
            id_est = str(row["ID Estacion"]).lower().strip()
            for prod in ["Regular", "Premium", "Diesel"]:
                val = row[prod]
                if pd.notna(val) and val != "":
                    registros.append({
                        "id_estacion": id_est,
                        "fecha": fecha_str,
                        "producto": prod.lower(),
                        "volumen": float(val)
                    })

        if not registros:
            st.warning("⚠️ No hay valores de inventario ingresados para guardar.")
        else:
            try:
                # Inserción o actualización en Supabase
                supabase_client.table("inventarios").upsert(
                    registros,
                    on_conflict="id_estacion,fecha,producto"
                ).execute()

                # Refrescar caché de inventarios
                data_loader.invalidar_inventarios()

                st.success(f"✅ ¡Inventarios actualizados y guardados correctamente para el día {fecha_str}!")
                st.rerun()

            except Exception as e:
                st.error(f"❌ **Error al guardar los datos en Supabase:** {e}")
