from datetime import date, timedelta

import pandas as pd
import streamlit as st

import database as db

PRODUCTOS = ["Regular", "Premium", "Diesel"]
FACTORES = ["factor", "factor_venta_diasemanal", "factor_estacionalidad"]


def formatear_fecha_corta(fecha):
    dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    meses = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{dias[fecha.weekday()]} {fecha:%d}-{meses[fecha.month - 1]}"


def _numero(valor, default=0.0):
    try:
        numero = float(valor)
        return numero if pd.notna(numero) and numero not in (float("inf"), float("-inf")) else default
    except (TypeError, ValueError, OverflowError):
        return default


def _normalizar_catalogo(df):
    if df.empty:
        return df
    if "id_estacion" in df:
        df["id_estacion"] = df["id_estacion"].astype(str).str.strip()
    if "producto" in df:
        df["producto"] = df["producto"].astype(str).str.strip().str.capitalize()
    return df


def _factor_del_dia(df, estacion, producto, fecha):
    if df.empty or "dia_index" not in df:
        return 1.0
    match = df[(df["id_estacion"] == estacion) & (df["producto"] == producto) & (df["dia_index"] == fecha.isoweekday())]
    if match.empty:
        return 1.0
    for columna in FACTORES:
        if columna in match and pd.notna(match.iloc[0][columna]):
            return max(0.0, _numero(match.iloc[0][columna], 1.0))
    return 1.0


def _valor_carga(df, estacion, producto, fecha):
    if df.empty:
        return 0
    filas = df[(df["id_estacion"] == estacion) & (df["producto"] == producto) & (df["fecha"] == fecha)]
    return db.validar_numero_entero(filas.iloc[0]["volumen"], "carga programada", minimo=0) if not filas.empty else 0


def mostrar_programacion():
    st.header("🚚 Programación de Cargas")
    asignaciones = db.obtener_estaciones_usuario()
    if not asignaciones:
        st.warning("No hay asignaciones de estaciones y usuarios registradas en la base de datos.")
        return
    df_asignaciones = pd.DataFrame(asignaciones)
    if "estaciones" in df_asignaciones:
        relacionadas = df_asignaciones["estaciones"]
        df_asignaciones["nombre"] = relacionadas.apply(lambda x: x.get("nombre", "") if isinstance(x, dict) else "")
        df_asignaciones["id_estacion"] = relacionadas.apply(lambda x: str(x.get("id_estacion", "")) if isinstance(x, dict) else "")
    usuarios = sorted(df_asignaciones["usuario"].dropna().unique())
    if not usuarios:
        st.warning("No hay usuarios disponibles.")
        return
    c_usuario, c_estacion = st.columns(2)
    with c_usuario:
        usuario = st.selectbox("Selecciona el usuario:", usuarios, key="filtro_usuario_programacion")
    asignadas = df_asignaciones[df_asignaciones["usuario"] == usuario].copy()
    if asignadas.empty:
        st.info("No hay estaciones para el usuario seleccionado.")
        return
    estaciones = dict(zip(asignadas["id_estacion"].astype(str).str.strip(), asignadas.get("nombre", "")))
    with c_estacion:
        estacion = st.selectbox("Selecciona la Estación:", list(estaciones), format_func=lambda x: f"{x} - {estaciones.get(x, '')}", key="filtro_estacion_programacion")
    estacion = str(estacion).strip()

    factores = _normalizar_catalogo(pd.DataFrame(db.obtener_factor_venta_diasemanal() or []))
    ponderados = _normalizar_catalogo(pd.DataFrame(db.obtener_vdp_ponderada_12w() or []))
    cargas = _normalizar_catalogo(pd.DataFrame(db.obtener_programa_cargas() or []))
    inventarios = _normalizar_catalogo(pd.DataFrame(db.obtener_inventarios() or []))
    tanques = _normalizar_catalogo(pd.DataFrame(db.obtener_tanques_estaciones() or []))
    if tanques.empty:
        st.warning("No hay tanques configurados; la captura de cargas está deshabilitada.")
        return
    permitidos = set(tanques.loc[tanques["id_estacion"] == estacion, "producto"].dropna())
    productos = [p for p in PRODUCTOS if p in permitidos]
    if not productos:
        st.info("Esta estación no tiene productos/tanques habilitados para programar cargas.")
        return

    if not factores.empty:
        dia_col = "diasemanal" if "diasemanal" in factores else "dia_de_la_semana" if "dia_de_la_semana" in factores else None
        if dia_col:
            factores["dia_index"] = pd.to_numeric(factores[dia_col], errors="coerce")
    for df in (cargas, inventarios):
        if not df.empty and "fecha" in df:
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
    if not cargas.empty and "volumen" in cargas:
        cargas["volumen"] = pd.to_numeric(cargas["volumen"], errors="coerce")

    hoy = date.today()
    for producto in productos:
        st.markdown(f"### ⛽ {producto}")
        vdp_rows = ponderados[(ponderados["id_estacion"] == estacion) & (ponderados["producto"] == producto)] if not ponderados.empty else pd.DataFrame()
        vdp = max(0.0, _numero(vdp_rows.iloc[0].get("vdp_ponderada", 0))) if not vdp_rows.empty else 0.0

        inv_rows = inventarios[(inventarios["id_estacion"] == estacion) & (inventarios["producto"] == producto)].copy() if not inventarios.empty else pd.DataFrame()
        inventario = 0.0
        if not inv_rows.empty:
            inv_rows = inv_rows[inv_rows["fecha"].notna() & (inv_rows["fecha"] <= hoy)].sort_values("fecha")
            if not inv_rows.empty:
                ultimo = inv_rows.iloc[-1]
                fecha_inv = ultimo["fecha"]
                inventario = _numero(ultimo.get("volumen"))
                for n in range(1, (hoy - fecha_inv).days + 1):
                    dia_prev = fecha_inv + timedelta(days=n - 1)
                    inventario += _valor_carga(cargas, estacion, producto, dia_prev) - vdp * _factor_del_dia(factores, estacion, producto, dia_prev)

        fechas = [hoy + timedelta(days=n) for n in range(14)]
        cargas_actuales = [_valor_carga(cargas, estacion, producto, fecha) for fecha in fechas]
        filas = {"Concepto": ["Inventario Inicial", "Venta Estimada", "Carga Programada", "Inventario Final", "D/S"]}
        iniciales, ventas, finales, dias = [], [], [], []
        for fecha, carga in zip(fechas, cargas_actuales):
            venta = vdp * _factor_del_dia(factores, estacion, producto, fecha)
            final = inventario + carga - venta
            iniciales.append(round(inventario, 2))
            ventas.append(round(venta, 2))
            finales.append(round(final, 2))
            dias.append(round(final / venta, 1) if venta > 0 else 0.0)
            inventario = final
        for i, fecha in enumerate(fechas):
            filas[formatear_fecha_corta(fecha)] = [iniciales[i], ventas[i], cargas_actuales[i], finales[i], dias[i]]
        st.dataframe(pd.DataFrame(filas), use_container_width=True, hide_index=True)

        st.markdown("**Captura de cargas programadas (solo enteros no negativos):**")
        nuevas = []
        for fecha, actual in zip(fechas, cargas_actuales):
            cols = st.columns([1, 2])
            cols[0].write(formatear_fecha_corta(fecha))
            nuevo = cols[1].number_input(
                "Volumen de carga",
                min_value=0,
                value=actual,
                step=1,
                format="%d",
                key=f"carga_{estacion}_{producto}_{fecha.isoformat()}",
                label_visibility="collapsed",
            )
            nuevas.append(nuevo)
        if st.button(f"Guardar cargas de {producto}", key=f"guardar_cargas_{estacion}_{producto}"):
            try:
                valores = [db.validar_numero_entero(v, f"carga de {fecha}", minimo=0) for v, fecha in zip(nuevas, fechas)]
                actualizadas = [(fecha, valor) for fecha, valor, actual in zip(fechas, valores, cargas_actuales) if valor != actual]
                for fecha, valor in actualizadas:
                    db.insertar_carga_programada(estacion, fecha, producto, valor)
                st.success(f"Cargas guardadas. Cambios: {len(actualizadas)}.")
                st.rerun()
            except (ValueError, TypeError) as exc:
                st.error(f"No se guardaron las cargas: {exc}")
            except Exception as exc:
                st.error(f"Error al registrar las cargas: {exc}")
        st.markdown("---")
