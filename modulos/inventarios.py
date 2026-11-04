import datetime
import pandas as pd
import streamlit as st
from servicios.output_service import DataOutputService

def render_inventarios(supabase_client, usuario_actual, data_loader):
    st.subheader("Módulo de Registro de Inventarios")

    # 1. Cargar datos maestros e inventarios normalizados
    datos_maestros = data_loader.cargar_datos_maestros()
    df_tanques = datos_maestros.get("tanques_estaciones", pd.DataFrame())
    df_usr = datos_maestros.get("estaciones_usuario", pd.DataFrame())

    # Carga dedicada para inventarios con la estructura de 4 variables clave
    df_inventarios_cache = data_loader.cargar_inventarios()

    # Normalizar el usuario actual a minúsculas por seguridad
    usuario_norm = str(usuario_actual).lower().strip()

    # Obtener las estaciones pertenecientes al usuario actual
    if not df_usr.empty and "usuario" in df_usr.columns:
        df_usr_filtrado = df_usr[df_usr["usuario"] == usuario_norm]
    else:
        df_usr_filtrado = pd.DataFrame()

    if df_usr_filtrado.empty:
        st.warning(f"El usuario '{usuario_actual}' no tiene estaciones asignadas en este momento.")
        return

    # Extraer la información básica de las estaciones asociadas
    estaciones_list = []
    for _, row in df_usr_filtrado.iterrows():
        est_data = row.get("estaciones")
        if isinstance(est_data, dict):
            estaciones_list.append({
                "id_estacion": str(row.get("id_estacion", "")).lower().strip(),
                "nombre": est_data.get("nombre", ""),
                "plaza": est_data.get("plaza", "")
            })
        elif isinstance(est_data, list) and len(est_data) > 0:
            est_dict = est_data[0]
            estaciones_list.append({
                "id_estacion": str(row.get("id_estacion", "")).lower().strip(),
                "nombre": est_dict.get("nombre", ""),
                "plaza": est_dict.get("plaza", "")
            })

    df_base_estaciones = pd.DataFrame(estaciones_list).drop_duplicates(subset=["id_estacion"])

    if df_base_estaciones.empty:
        st.warning("No se encontraron detalles válidos para las estaciones del usuario.")
        return

    # ---------------------------------------------------------
    # 2. FILTRO DE FECHA
    # ---------------------------------------------------------
    col_fecha, _ = st.columns([1, 2])
    with col_fecha:
        fecha_seleccionada = st.date_input("Seleccionar Fecha de Registro", value=datetime.date.today())

    fecha_str = fecha_seleccionada.strftime("%Y-%m-%d")

    # ---------------------------------------------------------
    # 3. CONSTRUCCIÓN DE LA TABLA MATRIZ CON LAS 4 VARIABLES
    # ---------------------------------------------------------
    df_inv_fecha = pd.DataFrame()
    if not df_inventarios_cache.empty and "fecha" in df_inventarios_cache.columns:
        df_inv_fecha = df_inventarios_cache[df_inventarios_cache["fecha"] == fecha_str]

    if not df_inv_fecha.empty and {"id_estacion", "producto", "volumen"}.issubset(df_inv_fecha.columns):
        df_pivot = df_inv_fecha.pivot(index="id_estacion", columns="producto", values="volumen").reset_index()
    else:
        df_pivot = pd.DataFrame(columns=["id_estacion"])

    for prod in ["regular", "premium", "diesel"]:
        if prod not in df_pivot.columns:
            df_pivot[prod] = None

    df_matriz = pd.merge(df_base_estaciones, df_pivot, on="id_estacion", how="left")

    # Mapear nombres de columnas para visualización
    for prod in ["regular", "premium", "diesel"]:
        if prod in df_matriz.columns:
            df_matriz[prod.capitalize()] = df_matriz[prod]
        else:
            df_matriz[prod.capitalize()] = None

    df_matriz = df_matriz.drop(columns=[c for c in ["regular", "premium", "diesel"] if c in df_matriz.columns], errors="ignore")

    df_matriz = df_matriz.rename(columns={
        "id_estacion": "ID Estacion",
        "nombre": "Nombre",
        "plaza": "Plaza"
    })

    columnas_orden = [c for c in ["ID Estacion", "Nombre", "Plaza", "Regular", "Premium", "Diesel"] if c in df_matriz.columns]
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
    # 4. BOTÓN DE GUARDAR / ACTUALIZAR REGISTRO
    # ---------------------------------------------------------
    if st.button("Guardar / Actualizar Registro", type="primary"):
        df_normalizar = df_editado.rename(columns={
            "ID Estacion": "id_estacion",
            "Regular": "regular",
            "Premium": "premium",
            "Diesel": "diesel"
        })

        output_service = DataOutputService()
        exito, mensaje, registros = output_service.validar_y_normalizar(df_normalizar, df_tanques)

        if not exito:
            st.error(f"❌ **Error de validación:** {mensaje}")
        else:
            if not registros:
                st.warning("⚠️ No hay valores de inventario ingresados para guardar.")
            else:
                for reg in registros:
                    reg["fecha"] = fecha_str
                    # Asegurar normalización en minúsculas antes de enviar
                    reg["id_estacion"] = str(reg["id_estacion"]).lower().strip()
                    reg["producto"] = str(reg["producto"]).lower().strip()

                try:
                    supabase_client.table("inventarios").upsert(
                        registros,
                        on_conflict="id_estacion,fecha,producto"
                    ).execute()

                    # Limpiar la caché exclusiva de inventarios
                    data_loader.invalidar_inventarios()

                    st.success(f"✅ ¡Inventarios actualizados y guardados correctamente para el día {fecha_str}!")
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ **Error al guardar los datos en Supabase:** {e}")
