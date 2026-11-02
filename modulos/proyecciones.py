import streamlit as st
import pandas as pd
from datetime import date, timedelta
import database as db
from servicios import calculos

def formatear_fecha_corta(fecha):
    """ Devuelve la fecha en el formato pedido: 'ddd dd-mmm' (p. ej. 'lun 28-oct'). """
    dias_semana = {0: "lun", 1: "mar", 2: "mié", 3: "jue", 4: "vie", 5: "sáb", 6: "dom"}
    meses = { 
        1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun", 
        7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic" 
    }
    dia_str = dias_semana[fecha.weekday()]
    mes_str = meses[fecha.month]
    return f"{dia_str} {fecha.day:02d}-{mes_str}"

def normalizar_dia_semana(valor_dia):
    """ Mapea nombres largos, con acentos o capitalizados a un índice entero (0 = Lunes, 6 = Domingo). """
    if not isinstance(valor_dia, str):
        return None
    val = valor_dia.strip().lower()
    mapa = {
        'lunes': 0, 'lun': 0,
        'martes': 1, 'mar': 1,
        'miércoles': 2, 'miercoles': 2, 'mié': 2, 'mie': 2,
        'jueves': 3, 'jue': 3,
        'viernes': 4, 'vie': 4,
        'sábado': 5, 'sabado': 5, 'sáb': 5, 'sab': 5,
        'domingo': 6, 'dom': 6
    }
    return mapa.get(val, None)

def mostrar_proyecciones():
    st.header("📈 Proyección e Integridad de Inventarios (14 Días)")
    
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

    df_factores = calculos.obtener_factores_estacionalidad_dia()
    df_inv_hoy = db.obtener_inventarios()
    
    if df_inv_hoy:
        df_inv_hoy = pd.DataFrame(df_inv_hoy)
        if "fecha" in df_inv_hoy.columns:
            df_inv_hoy["fecha"] = pd.to_datetime(df_inv_hoy["fecha"]).dt.date
        if "producto" in df_inv_hoy.columns:
            df_inv_hoy["producto"] = df_inv_hoy["producto"].astype(str).str.capitalize()
    else:
        df_inv_hoy = pd.DataFrame()

    fecha_hoy = date.today()
    productos = ["Regular", "Premium", "Diesel"]

    for producto in productos:
        if producto == "Regular":
            color_Hex = "#2e7d32"
        elif producto == "Premium":
            color_Hex = "#d84315"
        else:
            color_Hex = "#424242"

        st.markdown(f"<h3 style='color: {color_Hex};'>⛽ {producto}</h3>", unsafe_allow_html=True)

        # --- LÓGICA DE INVENTARIO INICIAL Y PROYECCIÓN HASTA HOY ---
        inv_inicial_hoy = 0.0
        if not df_inv_hoy.empty and "id_estacion" in df_inv_hoy.columns and "producto" in df_inv_hoy.columns:
            df_inv_est_prod = df_inv_hoy[
                (df_inv_hoy["id_estacion"] == id_estacion_sel) &
                (df_inv_hoy["producto"].str.capitalize() == producto)
            ].copy()
            
            if not df_inv_est_prod.empty:
                # 1. Verificar si hay inventario exacto para hoy
                match_hoy = df_inv_est_prod[df_inv_est_prod["fecha"] == fecha_hoy]
                if not match_hoy.empty:
                    inv_inicial_hoy = float(match_hoy["volumen"].values[0])
                else:
                    # 2. Si no hay para hoy, buscar el último inventario registrado anterior a hoy
                    df_anteriores = df_inv_est_prod[df_inv_est_prod["fecha"] < fecha_hoy]
                    if not df_anteriores.empty:
                        df_anteriores = df_anteriores.sort_values(by="fecha", ascending=False)
                        ultima_fecha = df_anteriores["fecha"].values[0]
                        volumen_ultimo = float(df_anteriores["volumen"].values[0])
                        
                        # Proyectar el inventario desde la última fecha registrada hasta el día anterior a hoy
                        inv_actual_proyectado = volumen_ultimo
                        current_date = ultima_fecha
                        
                        while current_date < fecha_hoy:
                            venta_dia_intermedio = 0.0
                            if not df_factores.empty:
                                mask_f = (
                                    (df_factores["id_estacion"] == id_estacion_sel) &
                                    (df_factores["producto"].str.capitalize() == producto)
                                )
                                if "dia_index" in df_factores.columns:
                                    match_v = df_factores[mask_f & (df_factores["dia_index"] == current_date.weekday())]
                                    if not match_v.empty:
                                        if "venta_proyectada_dia" in match_v.columns and pd.notna(match_v["venta_proyectada_dia"].values[0]):
                                            venta_dia_intermedio = float(match_v["venta_proyectada_dia"].values[0])
                                        elif "vdp_ponderada" in match_v.columns and pd.notna(match_v["vdp_ponderada"].values[0]):
                                            venta_dia_intermedio = float(match_v["vdp_ponderada"].values[0])
                            
                            inv_actual_proyectado -= venta_dia_intermedio
                            current_date += timedelta(days=1)
                        
                        inv_inicial_hoy = inv_actual_proyectado

        # --- CICLO DE PROYECCIÓN DE LOS 14 DÍAS ---
        fechas_cols = []
        inv_iniciales = []
        ventas_est = []
        inv_finales = []
        dias_inventario = []

        inv_actual = inv_inicial_hoy

        for i in range(14):
            fecha_dia = fecha_hoy + timedelta(days=i)
            fecha_fmt = formatear_fecha_corta(fecha_dia)
            fechas_cols.append(fecha_fmt)

            venta_estimada_dia = 0.0
            if not df_factores.empty:
                mask = (
                    (df_factores["id_estacion"] == id_estacion_sel) &
                    (df_factores["producto"].str.capitalize() == producto)
                )

                if "dia_index" in df_factores.columns:
                    match_venta = df_factores[mask & (df_factores["dia_index"] == fecha_dia.weekday())]
                    if not match_venta.empty and "venta_proyectada_dia" in match_venta.columns:
                        val = match_venta["venta_proyectada_dia"].values[0]
                        if pd.notna(val):
                            venta_estimada_dia = float(val)
                    elif not match_venta.empty and "vdp_ponderada" in match_venta.columns:
                        val = match_venta["vdp_ponderada"].values[0]
                        if pd.notna(val):
                            venta_estimada_dia = float(val)

            # El inventario inicial del día actual es el inventario final del día anterior
            inv_inicial = inv_actual
            inv_final = inv_inicial - venta_estimada_dia
            ds = (inv_final / venta_estimada_dia) if venta_estimada_dia > 0 else 0.0

            inv_iniciales.append(round(inv_inicial, 2))
            ventas_est.append(round(venta_estimada_dia, 2))
            inv_finales.append(round(inv_final, 2))
            dias_inventario.append(round(ds, 1))

            # Actualizamos inv_actual para que en la siguiente iteración tome el inventario final calculado
            inv_actual = inv_final

        data_dict = {
            "Concepto": ["Inventario Inicial", "Venta Estimada", "Inventario Final", "D/S"]
        }
        for idx, fecha_fmt in enumerate(fechas_cols):
            data_dict[fecha_fmt] = [
                inv_iniciales[idx],
                ventas_est[idx],
                inv_finales[idx],
                dias_inventario[idx]
            ]

        df_proyeccion = pd.DataFrame(data_dict)

        for col in df_proyeccion.columns:
            if col != "Concepto":
                df_proyeccion[col] = df_proyeccion.apply(
                    lambda row, c=col: (
                        f"{int(round(float(row[c]))):,}" if row["Concepto"] in ["Inventario Inicial", "Venta Estimada", "Inventario Final"]
                        else f"{float(row[c]):.1f}"
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
