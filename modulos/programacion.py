import datetime
import pandas as pd
import streamlit as st
from servicios.data_output import DataOutputService

def render_programacion(supabase_client, usuario_actual, data_loader):
    st.subheader("Módulo de Programación de Cargas")

    # Inicializar el servicio de normalización de salidas
    data_output = DataOutputService()

    # 1. Cargar datos maestros e inventarios estructurados
    datos_maestros = data_loader.cargar_datos_maestros()
    df_usr = datos_maestros.get("estaciones_usuario", pd.DataFrame())
    df_tanques = datos_maestros.get("tanques_estaciones", pd.DataFrame())
    df_vdp = datos_maestros.get("vdp_ponderada", pd.DataFrame())
    df_factor = datos_maestros.get("factor_diasemanal", pd.DataFrame())

    df_inventarios = data_loader.cargar_inventarios()

    # Normalizar usuario actual
    usuario_norm = str(usuario_actual).lower().strip()

    # Filtrar estaciones según el usuario actual
    if not df_usr.empty and "usuario" in df_usr.columns:
        df_usr_filtrado = df_usr[df_usr["usuario"] == usuario_norm]
    else:
        df_usr_filtrado = pd.DataFrame()

    if df_usr_filtrado.empty:
        st.warning(f"El usuario '{usuario_actual}' no tiene estaciones asignadas.")
        return

    # Extraer lista de estaciones asociadas de forma robusta
    estaciones_list = []
    for _, row in df_usr_filtrado.iterrows():
        raw_id = str(row.get("id_estacion", "")).strip()
        est_data = row.get("estaciones")
        if isinstance(est_data, dict):
            estaciones_list.append({
                "id_estacion_db": raw_id.lower(),
                "id_estacion": raw_id,
                "nombre": est_data.get("nombre", ""),
                "plaza": est_data.get("plaza", "")
            })
        elif isinstance(est_data, list) and len(est_data) > 0:
            est_dict = est_data[0]
            estaciones_list.append({
                "id_estacion_db": raw_id.lower(),
                "id_estacion": raw_id,
                "nombre": est_dict.get("nombre", ""),
                "plaza": est_dict.get("plaza", "")
            })
        else:
            estaciones_list.append({
                "id_estacion_db": raw_id.lower(),
                "id_estacion": raw_id,
                "nombre": "",
                "plaza": ""
            })

    df_base_estaciones = pd.DataFrame(estaciones_list).drop_duplicates(subset=["id_estacion_db"])

    if df_base_estaciones.empty or "plaza" not in df_base_estaciones.columns:
        st.warning("No se encontraron detalles válidos para las estaciones del usuario.")
        return

    # ---------------------------------------------------------
    # 2. FILTROS INICIALES: PLAZA Y ESTACIÓN
    # ---------------------------------------------------------
    plazas_disponibles = sorted(list(df_base_estaciones["plaza"].dropna().unique()))
    if not plazas_disponibles:
        st.warning("No hay plazas disponibles para mostrar.")
        return

    col_plaza, col_estacion = st.columns(2)

    with col_plaza:
        plaza_sel = st.selectbox("Seleccionar Plaza:", options=plazas_disponibles, key="prog_plaza")

    df_estaciones_plaza = df_base_estaciones[df_base_estaciones["plaza"] == plaza_sel]
    nombres_estaciones = sorted(list(df_estaciones_plaza["nombre"].dropna().unique()))

    with col_estacion:
        estacion_sel = st.selectbox("Seleccionar Estación:", options=nombres_estaciones, key="prog_estacion")

    # Identificar la estación seleccionada
    estacion_info = df_estaciones_plaza[df_estaciones_plaza["nombre"] == estacion_sel].iloc[0]
    id_estacion_actual_db = estacion_info["id_estacion_db"]
    id_estacion_actual_raw = estacion_info["id_estacion"]

    # ---------------------------------------------------------
    # 3. IDENTIFICAR PRODUCTOS DISPONIBLES EN LA ESTACIÓN
    # ---------------------------------------------------------
    if df_tanques.empty or "id_estacion" not in df_tanques.columns:
        st.info("No hay información de tanques cargada en el sistema.")
        return

    tanques_estacion = df_tanques[df_tanques["id_estacion"] == id_estacion_actual_db]

    if tanques_estacion.empty:
        st.info(f"La estación '{estacion_sel}' no tiene tanques configurados.")
        return

    productos_disponibles = tanques_estacion["producto"].dropna().unique()

    # Definir rango de 14 días a partir de hoy (Strings YYYY-MM-DD para Supabase y etiquetas)
    fecha_hoy = datetime.date.today()
    fechas_14d = [fecha_hoy + datetime.timedelta(days=i) for i in range(14)]
    columnas_fechas_strs = [f.strftime("%Y-%m-%d") for f in fechas_14d]

    # ---------------------------------------------------------
    # 4. GENERAR MATRIZ Y TABLA DE PROGRAMA DE CARGAS POR CADA PRODUCTO
    # ---------------------------------------------------------
    colores_acento = {
        "regular": "green",
        "premium": "darkorange",
        "diesel": "dimgray"
    }

    for producto in productos_disponibles:
        prod_lower = str(producto).lower().strip()
        color_titulo = colores_acento.get(prod_lower, "black")
        
        st.markdown(f"### <span style='color:{color_titulo};'>{str(producto).upper()}</span>", unsafe_allow_html=True)

        # Configuración del tanque para este producto
        tanque_prod = tanques_estacion[tanques_estacion["producto"] == producto].iloc[0]
        limite_max = tanque_prod.get("limite_max", 0)

        # Obtener VDP Ponderada
        vdp_ponderada = 0.0
        if not df_vdp.empty and {"id_estacion", "producto"}.issubset(df_vdp.columns):
            vdp_row = df_vdp[(df_vdp["id_estacion"] == id_estacion_actual_db) & (df_vdp["producto"] == producto)]
            if not vdp_row.empty:
                vdp_ponderada = float(vdp_row["vdp_ponderada"].values[0])

        # Obtener Inventario Inicial de hoy
        inventario_actual_inicial = 0.0
        if not df_inventarios.empty and {"id_estacion", "producto", "fecha"}.issubset(df_inventarios.columns):
            inv_hoy_row = df_inventarios[
                (df_inventarios["id_estacion"] == id_estacion_actual_db) &
                (df_inventarios["producto"] == producto) &
                (df_inventarios["fecha"] == fecha_hoy.strftime("%Y-%m-%d"))
            ]
            if not inv_hoy_row.empty:
                inventario_actual_inicial = float(inv_hoy_row["volumen"].values[0])

        # Cargar el programa de cargas existente desde Supabase para los próximos 14 días
        try:
            response = supabase_client.table("programa_cargas") \
                .select("fecha, volumen") \
                .eq("id_estacion", id_estacion_actual_db) \
                .eq("producto", prod_lower) \
                .in_("fecha", columnas_fechas_strs) \
                .execute()
            df_prog_existente = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        except Exception as e:
            st.error(f"Error al cargar programa_cargas para {producto}: {e}")
            df_prog_existente = pd.DataFrame()

        # Mapear volumen de carga programada por fecha
        mapa_cargas_prog = {}
        if not df_prog_existente.empty and {"fecha", "volumen"}.issubset(df_prog_existente.columns):
            for _, r_prog in df_prog_existente.iterrows():
                mapa_cargas_prog[str(r_prog["fecha"])] = float(r_prog["volumen"])

        # Simulación de los 14 días
        row_inv_inicial = []
        row_cap_carga = []
        row_carga_prog = []
        row_venta_est = []
        row_inv_final = []
        row_ds = []

        inv_corrido = inventario_actual_inicial

        for fecha_dt in fechas_14d:
            f_str = fecha_dt.strftime("%Y-%m-%d")
            dia_sem = fecha_dt.isoweekday()

            # Obtener el factor de venta diario semanal
            factor_venda = 1.0
            if not df_factor.empty and {"id_estacion", "producto", "diasemanal"}.issubset(df_factor.columns):
                factor_row = df_factor[
                    (df_factor["id_estacion"] == id_estacion_actual_db) &
                    (df_factor["producto"] == producto) &
                    (df_factor["diasemanal"] == dia_sem)
                ]
                if not factor_row.empty:
                    factor_venda = float(factor_row["factor"].values[0])

            inv_inicial_dia = inv_corrido
            cap_carga_dia = limite_max - inv_inicial_dia
            
            # Carga programada extraída de Supabase (si existe)
            carga_prog_dia = mapa_cargas_prog.get(f_str, 0.0)
            
            venta_est_dia = vdp_ponderada * factor_venda
            inv_final_dia = inv_inicial_dia + carga_prog_dia - venta_est_dia
            ds_dia = (inv_final_dia / vdp_ponderada) if vdp_ponderada > 0 else 0.0

            row_inv_inicial.append(round(inv_inicial_dia))
            row_cap_carga.append(round(cap_carga_dia))
            row_carga_prog.append(round(carga_prog_dia))
            row_venta_est.append(round(venta_est_dia))
            row_inv_final.append(round(inv_final_dia))
            row_ds.append(round(ds_dia, 4))

            inv_corrido = inv_final_dia

        # Armar etiquetas de columnas legibles para la matriz visual
        columnas_fechas_labels = [f.strftime("%a %d-%b") for f in fechas_14d]

        matriz_data = {
            "Concepto": [
                "Inventario Inicial",
                "Capacidad de Carga",
                "Carga Programada",
                "Venta Estimada",
                "Inventario Final",
                "D/S"
            ]
        }

        for idx, col_nombre in enumerate(columnas_fechas_labels):
            matriz_data[col_nombre] = [
                row_inv_inicial[idx],
                row_cap_carga[idx],
                row_carga_prog[idx],
                row_venta_est[idx],
                row_inv_final[idx],
                row_ds[idx]
            ]

        df_matriz_prod = pd.DataFrame(matriz_data)

        df_display = df_matriz_prod.copy()
        for col in columnas_fechas_labels:
            df_display[col] = df_display.apply(
                lambda row: f"{int(row[col]):,}" if row["Concepto"] != "D/S" else f"{row[col]:.1f}",
                axis=1
            )

        # Mostrar matriz de proyección analítica
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )

        # --- SECCIÓN: TABLA DE ESCRITURA / PROGRAMA DE CARGAS (14 DÍAS) ---
        st.markdown(f"##### ✏️ Editar Programa de Cargas (14 días) - {str(producto).capitalize()}")

        # Construir formato tabular para st.data_editor (1 sola fila con los 14 días para la estación seleccionada)
        fila_editable = {"id_estacion": id_estacion_actual_raw, "Estación": estacion_sel}
        for idx, f_str in enumerate(columnas_fechas_strs):
            fila_editable[f_str] = row_carga_prog[idx] if row_carga_prog[idx] > 0 else None

        df_editor_input = pd.DataFrame([fila_editable])

        # Configuración de columnas para el editor
        column_config_dict = {
            "id_estacion": st.column_config.TextColumn("ID Estación", disabled=True),
            "Estación": st.column_config.TextColumn("Estación", disabled=True),
        }

        for idx, f_str in enumerate(columnas_fechas_strs):
            f_dt = fechas_14d[idx]
            header_label = f_dt.strftime("%a %d-%b")
            column_config_dict[f_str] = st.column_config.NumberColumn(
                header_label, min_value=0, step=1, format="%,d"
            )

        df_editado_prog = st.data_editor(
            df_editor_input,
            use_container_width=True,
            hide_index=True,
            key=f"editor_prog_{prod_lower}_{id_estacion_actual_db}",
            column_config=column_config_dict
        )

        # Botón para guardar el programa de cargas de este producto
        if st.button(f"Guardar Programa - {str(producto).capitalize()}", key=f"btn_save_prog_{prod_lower}_{id_estacion_actual_db}", type="primary"):
            # Normalizar y estructurar datos usando DataOutputService (varchars en minúsculas, enteros numéricos)
            registros_prog = data_output.normalizar_programa_cargas(
                df_editado=df_editado_prog,
                columnas_fechas_str=columnas_fechas_strs,
                producto_target=prod_lower
            )

            try:
                # Incluso si la lista está vacía, podemos guardar/limpiar o hacer upsert de lo registrado
                # Realizamos el upsert masivo en Supabase respetando la restricción única (id_estacion, fecha, producto)
                if registros_prog:
                    supabase_client.table("programa_cargas").upsert(
                        registros_prog,
                        on_conflict="id_estacion,fecha,producto"
                    ).execute()
                
                st.success(f"✅ Programa de cargas para **{str(producto).upper()}** guardado correctamente.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error al guardar el programa de cargas: {e}")

        st.markdown("---")
