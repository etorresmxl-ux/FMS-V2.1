import streamlit as st
import pandas as pd
from datetime import date, timedelta
import database as db
from servicios import calculos

def normalizar_dia_semana(valor_dia):
    """Mapea nombres largos, con acentos o capitalizados a un índice entero (0 = Lunes, 6 = Domingo)."""
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

def formatear_fecha_corta(f):
    return f.strftime("%d/%m")

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
    df_ponderados = calculos.obtener_calculos_combustible()

    if not df_factores.empty and "dia_de_la_semana" in df_factores.columns:
        df_factores["dia_index"] = df_factores["dia_de_la_semana"].apply(normalizar_dia_semana)
        df_factores["id_estacion"] = df_factores["id_estacion"].astype(str).str.strip()
        df_factores["producto"] = df_factores["producto"].astype(str).str.strip().str.capitalize()

    if not df_ponderados.empty:
        df_ponderados["id_estacion"] = df_ponderados["id_estacion"].astype(str).str.strip()
        df_ponderados["producto"] = df_ponderados["producto"].astype(str).str.strip().str.capitalize()

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
    productos = ["Regular", "Premium", "Diesel"]

    for producto in productos:
        if producto == "Regular":
            color_Hex = "#2e7d32"
        elif producto == "Premium":
            color_Hex = "#d84315"
        else:
            color_Hex = "#424242"

        st.markdown(f"<h3 style='color: {color_Hex};'>⛽ {producto}</h3>", unsafe_allow_html=True)

        limite_min_val = 0.0
        if not df_tanques.empty and "id_estacion" in df_tanques.columns and "producto" in df_tanques.columns and "limite_min" in df_tanques.columns:
            match_tanque = df_tanques[
                (df_tanques["id_estacion"] == str(id_estacion_sel).strip()) & 
                (df_tanques["producto"] == producto)
            ]
            if not match_tanque.empty and pd.notna(match_tanque["limite_min"].values[0]):
                limite_min_val = float(match_tanque["limite_min"].values[0])

        vdp_base = 0.0
        if not df_ponderados.empty:
            match_pond = df_ponderados[
                (df_ponderados["id_estacion"] == str(id_estacion_sel).strip()) &
                (df_ponderados["producto"] == producto)
            ]
            if not match_pond.empty and "vdp_ponderada" in match_pond.columns:
                vdp_base = float(match_pond["vdp_ponderada"].values[0])

        # --- LÓGICA DE INVENTARIO INICIAL Y PROYECCIÓN HASTA HOY ---
        inv_inicial_hoy = 0.0
        if not df_inv_hoy.empty and "id_estacion" in df_inv_hoy.columns and "producto" in df_inv_hoy.columns:
            df_inv_est_prod = df_inv_hoy[
                (df_inv_hoy["id_estacion"] == str(id_estacion_sel).strip()) &
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
                            venta_dia_intermedio = 0.0
                            encontro_venta = False
                            
                            if not df_factores.empty:
                                mask_f = (
                                    (df_factores["id_estacion"] == str(id_estacion_sel).strip()) &
                                    (df_factores["producto"] == producto)
                                )
                                if "dia_index" in df_factores.columns:
                                    match_v = df_factores[mask_f & (df_factores["dia_index"] == current_date.weekday())]
                                    if not match_v.empty:
                                        for col_val in ["venta_proyectada_dia", "vp_dia", "volumen", "vdp_ponderada"]:
                                            if col_val in match_v.columns and pd.notna(match_v[col_val].values[0]):
                                                val = float(match_v[col_val].values[0])
                                                if val > 0:
                                                    venta_dia_intermedio = val
                                                    encontro_venta = True
                                                    break
                            
                            if not encontro_venta and vdp_base > 0:
                                venta_dia_intermedio = vdp_base
                            
                            if inv_actual_proyectado - venta_dia_intermedio < limite_min_val:
                                venta_dia_intermedio = max(0.0, inv_actual_proyectado - limite_min_val)

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
            encontro_venta = False

            if not df_factores.empty:
                mask = (
                    (df_factores["id_estacion"].astype(str).str.strip() == str(id_estacion_sel).strip()) &
                    (df_factores["producto"] == producto)
                )

                if "dia_index" in df_factores.columns:
                    match_venta = df_factores[mask & (df_factores["dia_index"] == fecha_dia.weekday())]
                    if not match_venta.empty:
                        for col_val in ["venta_proyectada_dia", "vp_dia", "volumen", "vdp_ponderada"]:
                            if col_val in match_venta.columns and pd.notna(match_venta[col_val].values[0]):
                                val = float(match_venta[col_val].values[0])
                                if val > 0:
                                    venta_estimada_dia = val
                                    encontro_venta = True
                                    break

            if not encontro_venta and vdp_base > 0:
                venta_estimada_dia = vdp_base

            inv_inicial = inv_actual
            
            if inv_inicial <= limite_min_val:
                venta_estimada_dia = 0.0
                inv_final = inv_inicial
            else:
                inv_final_prov = inv_inicial - venta_estimada_dia
                if inv_final_prov < limite_min_val:
                    venta_estimada_dia = max(0.0, inv_inicial - limite_min_val)
                    inv_final = limite_min_val
                else:
                    inv_final = inv_final_prov

            ds = (inv_final / venta_estimada_dia) if venta_estimada_dia > 0 else 0.0

            inv_iniciales.append(round(inv_inicial, 2))
            ventas_est.append(round(venta_estimada_dia, 2))
            inv_finales.append(round(inv_final, 2))
            dias_inventario.append(round(ds, 1))

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
