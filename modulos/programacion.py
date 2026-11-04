import datetime
import pandas as pd
import streamlit as st

def render_programacion(supabase_client, usuario_actual, data_loader):
    st.subheader("Módulo de Programación de Cargas")

    # 1. Cargar datos maestros e inventarios
    datos_maestros = data_loader.cargar_datos_maestros()
    df_usr = datos_maestros.get("estaciones_usuario", pd.DataFrame())
    df_tanques = datos_maestros.get("tanques_estaciones", pd.DataFrame())
    df_vdp = datos_maestros.get("vdp_ponderada", pd.DataFrame())
    df_factor = datos_maestros.get("factor_diasemanal", pd.DataFrame())
    
    df_inventarios = data_loader.cargar_inventarios()

    # Filtrar estaciones según el usuario actual
    if not df_usr.empty:
        df_usr_filtrado = df_usr[df_usr["usuario"] == usuario_actual]
    else:
        df_usr_filtrado = pd.DataFrame()

    if df_usr_filtrado.empty:
        st.warning(f"El usuario '{usuario_actual}' no tiene estaciones asignadas.")
        return

    # Extraer lista de estaciones asociadas con nombre y plaza
    estaciones_list = []
    for _, row in df_usr_filtrado.iterrows():
        est_data = row.get("estaciones")
        if isinstance(est_data, dict):
            estaciones_list.append({
                "id_estacion": row.get("id_estacion"),
                "nombre": est_data.get("nombre", ""),
                "plaza": est_data.get("plaza", "")
            })

    df_base_estaciones = pd.DataFrame(estaciones_list).drop_duplicates(subset=["id_estacion"])

    if df_base_estaciones.empty:
        st.warning("No se encontraron detalles para las estaciones del usuario.")
        return

    # ---------------------------------------------------------
    # 2. FILTROS INICIALES: PLAZA Y ESTACIÓN
    # ---------------------------------------------------------
    plazas_disponibles = sorted(list(df_base_estaciones["plaza"].unique()))
    col_plaza, col_estacion = st.columns(2)

    with col_plaza:
        plaza_sel = st.selectbox("Seleccionar Plaza:", options=plazas_disponibles)

    df_estaciones_plaza = df_base_estaciones[df_base_estaciones["plaza"] == plaza_sel]
    nombres_estaciones = sorted(list(df_estaciones_plaza["nombre"].unique()))

    with col_estacion:
        estacion_sel = st.selectbox("Seleccionar Estación:", options=nombres_estaciones)

    # Identificar la estación seleccionada
    estacion_info = df_estaciones_plaza[df_estaciones_plaza["nombre"] == estacion_sel].iloc[0]
    id_estacion_actual = estacion_info["id_estacion"]

    # ---------------------------------------------------------
    # 3. IDENTIFICAR PRODUCTOS DISPONIBLES EN LA ESTACIÓN
    # ---------------------------------------------------------
    tanques_estacion = df_tanques[df_tanques["id_estacion"] == id_estacion_actual]
    
    if tanques_estacion.empty:
        st.info(f"La estación '{estacion_sel}' no tiene tanques configurados.")
        return

    productos_disponibles = tanques_estacion["producto"].unique()

    # Definir rango de 14 días a partir de hoy
    fecha_hoy = datetime.date.today()
    fechas_14d = [fecha_hoy + datetime.timedelta(days=i) for i in range(14)]
    columnas_fechas = [f.strftime("%a %d-%b") for f in fechas_14d]

    # ---------------------------------------------------------
    # 4. GENERAR MATRIZ POR CADA PRODUCTO DISPONIBLE
    # ---------------------------------------------------------
    for producto in productos_disponibles:
        st.markdown(f"### Producto: **{str(producto).upper()}**")

        # Configuración del tanque para este producto
        tanque_prod = tanques_estacion[tanques_estacion["producto"] == producto].iloc[0]
        limite_max = tanque_prod.get("limite_max", 0)

        # Obtener VDP Ponderada
        vdp_row = df_vdp[(df_vdp["id_estacion"] == id_estacion_actual) & (df_vdp["producto"] == producto)]
        vdp_ponderada = vdp_row["vdp_ponderada"].values[0] if not vdp_row.empty else 0.0

        # Obtener Inventario Inicial del día de hoy
        inv_hoy_row = df_inventarios[
            (df_inventarios["id_estacion"] == id_estacion_actual) &
            (df_inventarios["producto"] == producto) &
            (df_inventarios["fecha"].astype(str) == fecha_hoy.strftime("%Y-%m-%d"))
        ]
        inventario_actual_inicial = inv_hoy_row["volumen"].values[0] if not inv_hoy_row.empty else 0.0

        # Inicialización de listas para almacenar los cálculos por día
        row_inv_inicial = []
        row_cap_carga = []
        row_carga_prog = []
        row_venta_est = []
        row_inv_final = []
        row_ds = []

        inv_corrido = inventario_actual_inicial

        for fecha in fechas_14d:
            # ISO dow: 1=Lunes, ..., 7=Domingo (coincide con isodow de Postgres)[cite: 6, 10]
            dia_sem = fecha.isoweekday()

            # Obtener el factor de venta diario semanal[cite: 6]
            factor_row = df_factor[
                (df_factor["id_estacion"] == id_estacion_actual) &
                (df_factor["producto"] == producto) &
                (df_factor["diasemanal"] == dia_sem)
            ]
            factor_venda = factor_row["factor"].values[0] if not factor_row.empty else 1.0

            # Cálculos fórmula por fórmula
            inv_inicial_dia = inv_corrido
            cap_carga_dia = limite_max - inv_inicial_dia
            carga_prog_dia = 0.0  # De momento en 0
            venta_est_dia = vdp_ponderada * factor_venda
            inv_final_dia = inv_inicial_dia + carga_prog_dia - venta_est_dia
            ds_dia = (inv_final_dia / vdp_ponderada) if vdp_ponderada > 0 else 0.0

            # Guardar valores redondeados a 2 decimales
            row_inv_inicial.append(round(inv_inicial_dia, 2))
            row_cap_carga.append(round(cap_carga_dia, 2))
            row_carga_prog.append(round(carga_prog_dia, 2))
            row_venta_est.append(round(venta_est_dia, 2))
            row_inv_final.append(round(inv_final_dia, 2))
            row_ds.append(round(ds_dia, 2))

            # El inventario final de hoy pasa a ser el inicial del día siguiente
            inv_corrido = inv_final_dia

        # Armar el DataFrame de la matriz
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

        for idx, col_nombre in enumerate(columnas_fechas):
            matriz_data[col_nombre] = [
                row_inv_inicial[idx],
                row_cap_carga[idx],
                row_carga_prog[idx],
                row_venta_est[idx],
                row_inv_final[idx],
                row_ds[idx]
            ]

        df_matriz_prod = pd.DataFrame(matriz_data)

        # Mostrar matriz formateada en Streamlit
        st.dataframe(
            df_matriz_prod,
            use_container_width=True,
            hide_index=True
        )
        st.markdown("---")
