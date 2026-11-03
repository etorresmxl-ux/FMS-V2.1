import streamlit as st
import pandas as pd
from datetime import date, timedelta
import database as db

def formatear_fecha_corta(f):
    return f.strftime("%d/%m")

def mostrar_proyecciones():
    st.header("📈 Proyección e Integridad de Inventarios (14 Días)")

    # 1. Filtros de Plaza y Estación
    datos_estaciones = db.obtener_estaciones()
    if not datos_estaciones:
        st.warning("No hay estaciones registradas en la base de datos.")
        return

    df_estaciones = pd.DataFrame(datos_estaciones)

    col_plaza, col_estacion = st.columns(2)

    with col_plaza:
        plazas_disponibles = sorted(list(df_estaciones["plaza"].unique()))
        plaza_seleccionada = st.selectbox(
            "Selecciona la Plaza:",
            options=plazas_disponibles,
            key="filtro_plaza_proyecciones"
        )

    df_estaciones_plaza = df_estaciones[df_estaciones["plaza"] == plaza_seleccionada]

    with col_estacion:
        estaciones_dict = dict(zip(df_estaciones_plaza["id_estacion"], df_estaciones_plaza["nombre"]))
        id_estacion_sel = st.selectbox(
            "Selecciona la Estación:",
            options=list(estaciones_dict.keys()),
            format_func=lambda x: f"{x} - {estaciones_dict[x]}",
            key="filtro_estacion_proyecciones"
        )

    if not id_estacion_sel:
        return

    id_estacion_str = str(id_estacion_sel).strip()

    # 2. Carga de información desde base de datos
    datos_factores = db.obtener_factor_venta_diasemanal()
    datos_ponderados = db.obtener_vdp_ponderada_12w()
    datos_inventarios = db.obtener_inventarios()
    datos_tanques = db.obtener_tanques_estaciones()

    df_factores = pd.DataFrame(datos_factores) if datos_factores else pd.DataFrame()
    df_ponderados = pd.DataFrame(datos_ponderados) if datos_ponderados else pd.DataFrame()
    df_inv_hoy = pd.DataFrame(datos_inventarios) if datos_inventarios else pd.DataFrame()
    df_tanques = pd.DataFrame(datos_tanques) if datos_tanques else pd.DataFrame()

    # Normalización de datos
    if not df_factores.empty:
        df_factores["id_estacion"] = df_factores["id_estacion"].astype(str).str.strip()
        df_factores["producto"] = df_factores["producto"].astype(str).str.strip().str.capitalize()
        if "dia_de_la_semana" in df_factores.columns:
            df_factores["dia_index"] = pd.to_numeric(df_factores["dia_de_la_semana"], errors="coerce")

    if not df_ponderados.empty:
        df_ponderados["id_estacion"] = df_ponderados["id_estacion"].astype(str).str.strip()
        df_ponderados["producto"] = df_ponderados["producto"].astype(str).str.strip().str.capitalize()

    if not df_inv_hoy.empty:
        df_inv_hoy["id_estacion"] = df_inv_hoy["id_estacion"].astype(str).str.strip()
        df_inv_hoy["producto"] = df_inv_hoy["producto"].astype(str).str.strip().str.capitalize()
        if "fecha" in df_inv_hoy.columns:
            df_inv_hoy["fecha"] = pd.to_datetime(df_inv_hoy["fecha"]).dt.date

    if not df_tanques.empty:
        df_tanques["id_estacion"] = df_tanques["id_estacion"].astype(str).str.strip()
        df_tanques["producto"] = df_tanques["producto"].astype(str).str.strip().str.capitalize()

    # 3. Filtrar los productos disponibles únicamente para la estación seleccionada
    if not df_tanques.empty and "id_estacion" in df_tanques.columns:
        productos_disponibles = df_tanques[df_tanques["id_estacion"] == id_estacion_str]["producto"].dropna().unique().tolist()
    else:
        productos_disponibles = ["Regular", "Premium", "Diesel"]

    if not productos_disponibles:
        st.info("No hay productos o tanques registrados para esta estación.")
        return

    fecha_hoy = date.today()

    # 4. Renderizado y Cálculo de matrices por Producto
    for producto in productos_disponibles:
        if producto == "Regular":
            color_Hex = "#2e7d32"
        elif producto == "Premium":
            color_Hex = "#d84315"
        else:
            color_Hex = "#424242"

        st.markdown(f"<h3 style='color: {color_Hex};'>⛽ {producto}</h3>", unsafe_allow_html=True)

        # Obtener capacidad máxima y límite mínimo de la estación/producto
        limite_max_val = 0.0
        limite_min_val = 0.0
        if not df_tanques.empty:
            match_tanque = df_tanques[
                (df_tanques["id_estacion"] == id_estacion_str) & 
                (df_tanques["producto"] == producto)
            ]
            if not match_tanque.empty:
                if "limite_max" in match_tanque.columns and pd.notna(match_tanque["limite_max"].values[0]):
                    limite_max_val = float(match_tanque["limite_max"].values[0])
                elif "capacidad" in match_tanque.columns and pd.notna(match_tanque["capacidad"].values[0]):
                    limite_max_val = float(match_tanque["capacidad"].values[0])

                if "limite_min" in match_tanque.columns and pd.notna(match_tanque["limite_min"].values[0]):
                    limite_min_val = float(match_tanque["limite_min"].values[0])

        # Obtener VDP Ponderada de 12 semanas
        vdp_ponderada = 0.0
        if not df_ponderados.empty:
            match_pond = df_ponderados[
                (df_ponderados["id_estacion"] == id_estacion_str) &
                (df_ponderados["producto"] == producto)
            ]
            if not match_pond.empty and "vdp_ponderada" in match_pond.columns:
                vdp_ponderada = float(match_pond["vdp_ponderada"].values[0])

        # Obtener Inventario Inicial del día
        inv_inicial_hoy = 0.0
        if not df_inv_hoy.empty:
            df_inv_est_prod = df_inv_hoy[
                (df_inv_hoy["id_estacion"] == id_estacion_str) &
                (df_inv_hoy["producto"] == producto)
            ]
            if not df_inv_est_prod.empty:
                match_hoy = df_inv_est_prod[df_inv_est_prod["fecha"] == fecha_hoy]
                if not match_hoy.empty:
                    inv_inicial_hoy = float(match_hoy["volumen"].values[0])
                else:
                    df_anteriores = df_inv_est_prod[df_inv_est_prod["fecha"] < fecha_hoy].sort_values(by="fecha", ascending=False)
                    if not df_anteriores.empty:
                        inv_inicial_hoy = float(df_anteriores["volumen"].values[0])

        # Ciclo de proyección a 14 Días
        fechas_cols = []
        inv_iniciales = []
        por_llenar_list = []
        ventas_est = []
        inv_finales = []
        dias_inventario = []

        inv_actual = inv_inicial_hoy

        for i in range(14):
            fecha_dia = fecha_hoy + timedelta(days=i)
            fecha_fmt = formatear_fecha_corta(fecha_dia)
            fechas_cols.append(fecha_fmt)

            # Cálculo de factor del día de la semana (1 = Lunes, ..., 7 = Domingo)
            dia_semana_iso = fecha_dia.isoweekday()
            factor_dia = 1.0

            if not df_factores.empty:
                match_factor = df_factores[
                    (df_factores["id_estacion"] == id_estacion_str) &
                    (df_factores["producto"] == producto) &
                    (df_factores["dia_index"] == dia_semana_iso)
                ]
                if not match_factor.empty:
                    for col_factor in ["factor_venta_diasemanal", "factor", "vp_dia"]:
                        if col_factor in match_factor.columns and pd.notna(match_factor[col_factor].values[0]):
                            factor_dia = float(match_factor[col_factor].values[0])
                            break

            # 1. Inventario Inicial
            inv_inicial = inv_actual

            # 2. Por llenar = (limite_max - inventario actual)
            por_llenar = max(0.0, limite_max_val - inv_inicial) if limite_max_val > 0 else 0.0

            # 3. Venta estimada = (vdp_ponderada * factor_venta_diasemanal)
            venta_estimada = vdp_ponderada * factor_dia

            # 4. Inventario final = (inventario inicial - venta estimada)
            inv_final = inv_inicial - venta_estimada

            # 5. D/S = (inventario final / vdp_ponderada)
            ds = (inv_final / vdp_ponderada) if vdp_ponderada > 0 else 0.0

            # Guardar resultados
            inv_iniciales.append(round(inv_inicial, 2))
            por_llenar_list.append(round(por_llenar, 2))
            ventas_est.append(round(venta_estimada, 2))
            inv_finales.append(round(inv_final, 2))
            dias_inventario.append(round(ds, 1))

            # El inventario final de hoy pasa a ser el inicial de mañana
            inv_actual = inv_final

        # Construcción del DataFrame para mostrar en Streamlit
        data_dict = {
            "Concepto": [
                "Inventario Inicial",
                "Por Llenar",
                "Venta Estimada",
                "Inventario Final",
                "D/S"
            ]
        }

        for idx, fecha_fmt in enumerate(fechas_cols):
            data_dict[fecha_fmt] = [
                inv_iniciales[idx],
                por_llenar_list[idx],
                ventas_est[idx],
                inv_finales[idx],
                dias_inventario[idx]
            ]

        df_proyeccion = pd.DataFrame(data_dict)

        # Formatear números (enteros formateados con comas para volúmenes, decimales para D/S)
        for col in df_proyeccion.columns:
            if col != "Concepto":
                df_proyeccion[col] = df_proyeccion.apply(
                    lambda row, c=col: (
                        f"{int(round(float(row[c]))):,}" if row["Concepto"] in [
                            "Inventario Inicial", "Por Llenar", "Venta Estimada", "Inventario Final"
                        ] else f"{float(row[c]):.1f}"
                    ),
                    axis=1
                )

        column_config = {
            "Concepto": st.column_config.TextColumn("Concepto", width="medium")
        }
        for col in [c for c in df_proyeccion.columns if c != "Concepto"]:
            column_config[col] = st.column_config.TextColumn(col, width="small")

        st.dataframe(
            df_proyeccion,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )
