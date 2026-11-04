import datetime
import pandas as pd
import streamlit as st
from servicios.data_output import DataOutputService

def render_programacion(supabase_client, data_loader, usuario_actual):
    st.markdown("## 📊 Módulo de Programación de Cargas")

    # Inicializar el servicio de normalización de salidas
    data_output = DataOutputService()

    # 1. Cargar datos maestros e inventarios/proyecciones necesarios
    datos_maestros = data_loader.cargar_datos_maestros()
    df_usr = datos_maestros.get("estaciones_usuario", pd.DataFrame())

    # Normalizar usuario actual a minúsculas
    usuario_norm = str(usuario_actual).lower().strip()

    # Filtrar estaciones del usuario
    if not df_usr.empty:
        df_usr_filtrado = df_usr[df_usr["usuario"] == usuario_norm]
    else:
        df_usr_filtrado = pd.DataFrame()

    if df_usr_filtrado.empty:
        st.warning(f"El usuario '{usuario_actual}' no tiene estaciones asignadas en este momento.")
        return

    # Extraer estaciones base (id_estacion_db en minúsculas para cruces, id_estacion y nombre originales)
    estaciones_list = []
    for _, row in df_usr_filtrado.iterrows():
        raw_id = str(row.get("id_estacion", "")).strip()
        est_data = row.get("estaciones")
        if isinstance(est_data, dict):
            estaciones_list.append({
                "id_estacion_db": raw_id.lower(),
                "id_estacion": raw_id,
                "nombre": str(est_data.get("nombre", "")),
                "plaza": str(est_data.get("plaza", ""))
            })
        elif isinstance(est_data, list) and len(est_data) > 0:
            est_dict = est_data[0]
            estaciones_list.append({
                "id_estacion_db": raw_id.lower(),
                "id_estacion": raw_id,
                "nombre": str(est_dict.get("nombre", "")),
                "plaza": str(est_dict.get("plaza", ""))
            })
        else:
            estaciones_list.append({
                "id_estacion_db": raw_id.lower(),
                "id_estacion": raw_id,
                "nombre": "",
                "plaza": ""
            })

    df_base_estaciones = pd.DataFrame(estaciones_list).drop_duplicates(subset=["id_estacion_db"])

    # Lista de productos a manejar en el sistema
    productos_objetivo = ["regular", "premium", "diesel"]

    # Generar rango de fechas para los próximos 14 días
    hoy = datetime.date.today()
    fechas_14d = [hoy + datetime.timedelta(days=i) for i in range(14)]
    columnas_fechas_strs = [f.strftime("%Y-%m-%d") for f in fechas_14d]

    # Iterar sobre cada producto para mostrar su matriz de proyección y su tabla de programa de cargas debajo
    for producto in productos_objetivo:
        st.markdown("---")
        st.markdown(f"### ⛽ Producto: {producto.upper()}")

        # Simulación / Renderizado de la matriz principal de proyección del producto (ejemplo visual o espacio reservado)
        st.info(f"Matriz de proyección y análisis para el producto **{producto.upper()}**.")

        # --- SECCIÓN: PROGRAMA DE CARGAS (14 DÍAS) ---
        st.markdown(f"#### 📅 Programa de Cargas (14 días) - {producto.capitalize()}")

        # Cargar los programas existentes de Supabase para este producto y rango de fechas
        try:
            response = supabase_client.table("programa_cargas") \
                .select("id_estacion, fecha, volumen") \
                .eq("producto", producto.lower()) \
                .in_("fecha", columnas_fechas_strs) \
                .execute()
            df_prog_existente = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Error al cargar programa_cargas para {producto}: {e}")
            df_prog_existente = pd.DataFrame()

        # Construir la matriz pivotada (Estaciones x 14 Días)
        if not df_prog_existente.empty:
            df_pivot_prog = df_prog_existente.pivot(index="id_estacion", columns="fecha", values="volumen").reset_index()
            df_pivot_prog = df_pivot_prog.rename(columns={"id_estacion": "id_estacion_db"})
        else:
            df_pivot_prog = pd.DataFrame(columns=["id_estacion_db"])

        # Asegurar que todas las columnas de fechas existan
        for f_str in columnas_fechas_strs:
            if f_str not in df_pivot_prog.columns:
                df_pivot_prog[f_str] = None

        # Fusionar con las estaciones base
        df_matriz_prog = pd.merge(df_base_estaciones, df_pivot_prog, on="id_estacion_db", how="left")

        # Renombrar columnas para la visualización amigable
        renombres = {"id_estacion": "ID Estacion", "nombre": "Nombre", "plaza": "Plaza"}
        df_matriz_prog = df_matriz_prog.rename(columns=renombres)

        # Ordenar columnas: Datos de estación + 14 fechas
        columnas_orden = ["ID Estacion", "Nombre", "Plaza"] + columnas_fechas_strs
        df_matriz_prog = df_matriz_prog[[c for c in columnas_orden if c in df_matriz_prog.columns]]

        # Configurar las columnas de fecha como NumberColumn para edición (enteros)
        column_config_dict = {
            "ID Estacion": st.column_config.TextColumn("ID Estacion", disabled=True),
            "Nombre": st.column_config.TextColumn("Nombre", disabled=True),
            "Plaza": st.column_config.TextColumn("Plaza", disabled=True),
        }
        for f_str in columnas_fechas_strs:
            f_dt = datetime.datetime.strptime(f_str, "%Y-%m-%d").date()
            header_label = f_dt.strftime("%d/%b")
            column_config_dict[f_str] = st.column_config.NumberColumn(
                header_label, min_value=0, step=1, format="%,d"
            )

        # Editor de datos interactivo en Streamlit
        df_editado_prog = st.data_editor(
            df_matriz_prog,
            use_container_width=True,
            hide_index=True,
            key=f"editor_prog_{producto}",
            column_config=column_config_dict
        )

        # Botón de Guardar específico para el producto actual
        if st.button(f"Guardar Programa - {producto.capitalize()}", key=f"btn_save_prog_{producto}", type="primary"):
            # Procesar y normalizar mediante DataOutputService (varchars en minúsculas, enteros en numéricos)
            registros_prog = data_output.normalizar_programa_cargas(
                df_editado=df_editado_prog,
                columnas_fechas_str=columnas_fechas_strs,
                producto_target=producto
            )

            if not registros_prog:
                st.warning(f"⚠️ No hay volúmenes válidos ingresados para guardar en el programa de {producto}.")
            else:
                try:
                    # Inserción o actualización masiva en Supabase respetando la restricción única
                    supabase_client.table("programa_cargas").upsert(
                        registros_prog,
                        on_conflict="id_estacion,fecha,producto"
                    ).execute()
                    
                    st.success(f"✅ Programa de cargas para **{producto.capitalize()}** guardado correctamente.")
                except Exception as e:
                    st.error(f"❌ Error al guardar el programa de cargas: {e}")
