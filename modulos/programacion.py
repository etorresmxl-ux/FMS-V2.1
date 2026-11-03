from datetime import date, timedelta
import pandas as pd
import streamlit as st
import database as db

def formatear_fecha_corta(f):
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{dias[f.weekday()]} {f.strftime('%d')}-{meses[f.month - 1]}"

def obtener_programa_cargas():
    """Obtiene el programa de cargas desde la tabla de Supabase[cite: 3, 4]."""
    try:
        response = db._require_supabase().table("programa_cargas").select("*").execute()
        return response.data
    except Exception:
        return []

def mostrar_programacion():
    st.header("📅 Programa de Cargas y Proyecciones")

    # 1. Carga de asignaciones de estaciones por usuario
    datos_estaciones_usuario = db.obtener_estaciones_usuario()
    if not datos_estaciones_usuario:
        st.warning("No hay asignaciones de estaciones y usuarios registradas en la base de datos.")
        return

    df_est_usu = pd.DataFrame(datos_estaciones_usuario)

    # Normalizar columnas si vienen anidadas en un diccionario desde Supabase
    if "estaciones" in df_est_usu.columns:
        df_est_usu["nombre"] = df_est_usu["estaciones"].apply(
            lambda x: x.get("nombre") if isinstance(x, dict) else ""
        )
        df_est_usu["plaza"] = df_est_usu["estaciones"].apply(
            lambda x: x.get("plaza") if isinstance(x, dict) else ""
        )
        df_est_usu["id_estacion"] = df_est_usu["estaciones"].apply(
            lambda x: str(x.get("id_estacion")) if isinstance(x, dict) and x.get("id_estacion") is not None else df_est_usu.get("id_estacion")
        )

    # Selectores en columnas: Usuario y Estación
    col_usuario, col_espacio = st.columns(2)

    with col_usuario:
        usuarios_disponibles = sorted(list(df_est_usu["usuario"].dropna().unique()))
        usuario_seleccionado = st.selectbox(
            "Selecciona el usuario:",
            options=usuarios_disponibles,
            key="filtro_usuario_programacion"
        )

    df_estaciones_filtradas = df_est_usu[df_est_usu["usuario"] == usuario_seleccionado].copy()

    if df_estaciones_filtradas.empty:
        st.info("No hay estaciones registradas para el usuario seleccionado.")
        return

    with col_espacio:
        estaciones_dict = dict(zip(df_estaciones_filtradas["id_estacion"], df_estaciones_filtradas["nombre"]))
        id_estacion_sel = st.selectbox(
            "Selecciona la Estación:",
            options=list(estaciones_dict.keys()),
            format_func=lambda x: f"{x} - {estaciones_dict.get(x, '')}",
            key="filtro_estacion_programacion"
        )

    if not id_estacion_sel:
        return

    id_estacion_str = str(id_estacion_sel).strip()

    # Obtención de datos directamente desde las vistas y tablas de Supabase
    datos_factores = db.obtener_factor_venta_diasemanal()
    datos_ponderados = db.obtener_vdp_ponderada_12w()
    datos_cargas = obtener_programa_cargas()

    df_factores = pd.DataFrame(datos_factores) if datos_factores else pd.DataFrame()
    df_ponderados = pd.DataFrame(datos_ponderados) if datos_ponderados else pd.DataFrame()
    df_cargas = pd.DataFrame(datos_cargas) if datos_cargas else pd.DataFrame()

    if not df_factores.empty:
        df_factores["id_estacion"] = df_factores["id_estacion"].astype(str).str.strip()
        df_factores["producto"] = df_factores["producto"].astype(str).str.strip().str.capitalize()
        if "diasemanal" in df_factores.columns:
            df_factores["dia_index"] = pd.to_numeric(df_factores["diasemanal"], errors="coerce")
        elif "dia_de_la_semana" in df_factores.columns:
            df_factores["dia_index"] = pd.to_numeric(df_factores["dia_de_la_semana"], errors="coerce")

    if not df_ponderados.empty:
        df_ponderados["id_estacion"] = df_ponderados["id_estacion"].astype(str).str.strip()
        df_ponderados["producto"] = df_ponderados["producto"].astype(str).str.strip().str.capitalize()

    if not df_cargas.empty:
        df_cargas["id_estacion"] = df_cargas["id_estacion"].astype(str).str.strip()
        df_cargas["producto"] = df_cargas["producto"].astype(str).str.strip().str.capitalize()
        if "fecha" in df_cargas.columns:
            df_cargas["fecha"] = pd.to_datetime(df_cargas["fecha"]).dt.date
        if "volumen" in df_cargas.columns:
            df_cargas["volumen"] = pd.to_numeric(df_cargas["volumen"], errors="coerce").fillna(0.0)

    df_inv_hoy = db.obtener_inventarios()

    if df_inv_hoy:
        df_inv_hoy = pd.DataFrame(df_inv_hoy)
        if "fecha" in df_inv_hoy.columns:
            df_inv_hoy["fecha"] = pd.to_datetime(df_inv_hoy["fecha"]).dt.date
        if "producto" in df_inv_hoy.columns:
            df_inv_hoy["producto"] = df_inv_hoy["producto"].astype(str).str.strip().str.capitalize()
        if "id_estacion" in df_inv_hoy.columns:
            df_inv_hoy["id_estacion"] = df_inv_hoy["id_estacion"].astype(str).str.strip()
    else:
        df_inv_hoy = pd.DataFrame()

    datos_tanques = db.obtener_tanques_estaciones()
    if datos_tanques:
        df_tanques = pd.DataFrame(datos_tanques)
        if "producto" in df_tanques.columns:
            df_tanques["producto"] = df_tanques["producto"].astype(str).str.strip().str.capitalize()
        if "id_estacion" in df_tanques.columns:
            df_tanques["id_estacion"] = df_tanques["id_estacion"].astype(str).str.strip()
    else:
        df_tanques = pd.DataFrame()

    fecha_hoy = date.today()

    # Validación y obtención dinámica de productos disponibles por estación desde tanques_estaciones
    productos_disponibles = []
    if not df_tanques.empty and "id_estacion" in df_tanques.columns:
        df_tanques_estacion = df_tanques[df_tanques["id_estacion"] == id_estacion_str]
        if not df_tanques_estacion.empty and "producto" in df_tanques_estacion.columns:
            productos_disponibles = (
                df_tanques_estacion["producto"]
                .dropna()
                .astype(str)
                .str.strip()
                .str.capitalize()
                .unique()
                .tolist()
            )

    if not productos_disponibles:
        st.info("No hay productos o tanques registrados para esta estación en la base de datos.")
        return

    for producto in productos_disponibles:
        if producto == "Regular":
            color_Hex = "#2e7d32"
        elif producto == "Premium":
            color_Hex = "#d84315"
        else:
            color_Hex = "#424242"

        st.markdown(f"<h3 style='color: {color_Hex};'>⛽ {producto}</h3>", unsafe_allow_html=True)

        vdp_base = 0.0
        if not df_ponderados.empty:
            match_pond = df_ponderados[
                (df_ponderados["id_estacion"] == id_estacion_str) &
                (df_ponderados["producto"] == producto)
            ]
            if not match_pond.empty and "vdp_ponderada" in match_pond.columns:
                vdp_base = float(match_pond["vdp_ponderada"].values[0])

        # --- LÓGICA DE INVENTARIO INICIAL Y PROYECCIÓN HASTA HOY ---
        inv_inicial_hoy = 0.0
        if not df_inv_hoy.empty and "id_estacion" in df_inv_hoy.columns and "producto" in df_inv_hoy.columns:
            df_inv_est_prod = df_inv_hoy[
                (df_inv_hoy["id_estacion"] == id_estacion_str) &
                (df_inv_hoy["producto"] == producto)
            ].copy()
            
            if not df_inv_est_prod.empty:
                match_hoy = df_inv_est_prod[df_inv_est_prod["fecha"] == fecha_hoy]
                if not match_hoy.empty:
                    inv_inicial_hoy = float(match_hoy["volumen"].values[0])
                else:
                    df_anteriores = df_inv_est_prod[df_inv_est_prod["fecha"] < fecha_hoy]
                    if not df_anteriores.empty:
                        df_anteriores = df_anteriores.sort_values(by="fecha", ascending=False)
                        ultima_fecha = df_anteriores["fecha"].values[0]
                        volumen_ultimo = float(df_anteriores["volumen"].values[0])
                        
                        inv_actual_proyectado = volumen_ultimo
                        current_date = ultima_fecha
                        
                        while current_date < fecha_hoy:
                            factor_intermedio = 1.0
                            if not df_factores.empty and "dia_index" in df_factores.columns:
                                match_f = df_factores[
                                    (df_factores["id_estacion"] == id_estacion_str) &
                                    (df_factores["producto"] == producto) &
                                    (df_factores["dia_index"] == current_date.isoweekday())
                                ]
                                if not match_f.empty:
                                    for col_factor in ["factor", "factor_venta_diasemanal", "factor_estacionalidad"]:
                                        if col_factor in match_f.columns and pd.notna(match_f[col_factor].values[0]):
                                            factor_intermedio = float(match_f[col_factor].values[0])
                                            break
                            
                            venta_dia_intermedio = vdp_base * factor_intermedio

                            carga_intermedia = 0.0
                            if not df_cargas.empty:
                                match_c_ant = df_cargas[
                                    (df_cargas["id_estacion"] == id_estacion_str) &
                                    (df_cargas["producto"] == producto) &
                                    (df_cargas["fecha"] == current_date)
                                ]
                                if not match_c_ant.empty:
                                    carga_intermedia = float(match_c_ant["volumen"].values[0])

                            inv_actual_proyectado = inv_actual_proyectado + carga_intermedia - venta_dia_intermedio
                            current_date += timedelta(days=1)
                        
                        inv_inicial_hoy = inv_actual_proyectado

        # --- CICLO DE PROYECCIÓN DE LOS 14 DÍAS ---
        fechas_cols = []
        fechas_reales = []
        inv_iniciales = []
        ventas_est = []
        cargas_prog = []
        inv_finales = []
        dias_inventario = []

        inv_actual = inv_inicial_hoy

        for i in range(14):
            fecha_dia = fecha_hoy + timedelta(days=i)
            fecha_fmt = formatear_fecha_corta(fecha_dia)
            fechas_cols.append(fecha_fmt)
            fechas_reales.append(fecha_dia)

            # Buscar factor de temporalidad para el día de la semana correspondiente
            factor_dia = 1.0
            if not df_factores.empty and "dia_index" in df_factores.columns:
                match_factor = df_factores[
                    (df_factores["id_estacion"] == id_estacion_str) &
                    (df_factores["producto"] == producto) &
                    (df_factores["dia_index"] == fecha_dia.isoweekday())
                ]
                if not match_factor.empty:
                    for col_factor in ["factor", "factor_venta_diasemanal", "factor_estacionalidad"]:
                        if col_factor in match_factor.columns and pd.notna(match_factor[col_factor].values[0]):
                            factor_dia = float(match_factor[col_factor].values[0])
                            break

            venta_estimada_dia = vdp_base * factor_dia

            carga_programada_dia = 0.0
            if not df_cargas.empty:
                match_carg = df_cargas[
                    (df_cargas["id_estacion"] == id_estacion_str) &
                    (df_cargas["producto"] == producto) &
                    (df_cargas["fecha"] == fecha_dia)
                ]
                if not match_carg.empty:
                    carga_programada_dia = float(match_carg["volumen"].values[0])

            inv_inicial = inv_actual
            inv_final = inv_inicial + carga_programada_dia - venta_estimada_dia
            ds = (inv_final / venta_estimada_dia) if venta_estimada_dia > 0 else 0.0

            inv_iniciales.append(round(inv_inicial, 2))
            ventas_est.append(round(venta_estimada_dia, 2))
            cargas_prog.append(round(carga_programada_dia, 2))
            inv_finales.append(round(inv_final, 2))
            dias_inventario.append(round(ds, 1))

            inv_actual = inv_final

        data_dict = {
            "Concepto": ["Inventario Inicial", "Venta Estimada", "Carga Programada", "Inventario Final", "D/S"]
        }
        for idx, fecha_fmt in enumerate(fechas_cols):
            data_dict[fecha_fmt] = [
                inv_iniciales[idx],
                ventas_est[idx],
                cargas_prog[idx],
                inv_finales[idx],
                dias_inventario[idx]
            ]

        df_proyeccion = pd.DataFrame(data_dict)

        # Configuración de columnas para el editor
        column_config = {
            "Concepto": st.column_config.TextColumn("Concepto", width="medium", disabled=True)
        }
        for col in [c for c in df_proyeccion.columns if c != "Concepto"]:
            column_config[col] = st.column_config.NumberColumn(col, format="%.2f", width="small")

        # Tabla interactiva con st.data_editor
        edited_df = st.data_editor(
            df_proyeccion,
            use_container_width=True,
            hide_index=True,
            column_config=column_config,
            key=f"editor_proyeccion_{producto}_{id_estacion_str}"
        )

        # Botón para guardar cambios de la carga programada
        if st.button(f"Guardar Cambios de Carga - {producto}", key=f"btn_guardar_{producto}_{id_estacion_str}"):
            try:
                fila_carga = edited_df[edited_df["Concepto"] == "Carga Programada"]
                if not fila_carga.empty:
                    supabase = db._require_supabase()
                    for idx, fecha_fmt in enumerate(fechas_cols):
                        if fecha_fmt in fila_carga.columns:
                            nuevo_volumen = float(fila_carga[fecha_fmt].values[0])
                            fecha_real = fechas_reales[idx]

                            data_upsert = {
                                "id_estacion": id_estacion_str,
                                "producto": producto,
                                "fecha": fecha_real.isoformat(),
                                "volumen": nuevo_volumen
                            }
                            supabase.table("programa_cargas").upsert(
                                data_upsert,
                                on_conflict="id_estacion,producto,fecha"
                            ).execute()
                    st.success(f"¡Cargas programadas para {producto} guardadas y registradas correctamente en Supabase!")
                    st.rerun()
                else:
                    st.warning("No se encontró la fila de Carga Programada para guardar.")
            except Exception as e:
                st.error(f"Error al registrar los cambios: {e}")

        st.markdown("---")
