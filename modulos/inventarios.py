import pandas as pd
import streamlit as st

import database as db
from servicios import validacion

PRODUCTOS = ["Regular", "Premium", "Diesel"]


def _id_estacion(row):
    relacion = row.get("estaciones")
    if isinstance(relacion, dict) and relacion.get("id_estacion") is not None:
        return str(relacion["id_estacion"]).strip()
    value = row.get("id_estacion")
    return "" if pd.isna(value) else str(value).strip()


def _valor_existente(df_inv, estacion, producto, fecha):
    if df_inv.empty:
        return 0
    fechas = pd.to_datetime(df_inv["fecha"], errors="coerce").dt.date
    mask = (
        df_inv["id_estacion"].astype(str).str.strip().eq(estacion)
        & df_inv["producto"].astype(str).str.strip().str.casefold().eq(producto.casefold())
        & fechas.eq(fecha)
    )
    filas = df_inv.loc[mask, "volumen"]
    if filas.empty:
        return 0
    return db.validar_numero_entero(filas.iloc[-1], "inventario", minimo=0)


def mostrar_inventarios():
    st.header("📋 Consulta y Actualización de Inventarios")
    asignaciones = db.obtener_estaciones_usuario()
    if not asignaciones:
        st.warning("No hay asignaciones de estaciones y usuarios registradas en la base de datos.")
        return
    df_asignaciones = pd.DataFrame(asignaciones)
    if "usuario" not in df_asignaciones:
        st.error("Las asignaciones no contienen la columna usuario.")
        return

    fecha = st.date_input("Selecciona la fecha:", key="filtro_fecha_inventarios")
    usuarios = sorted(df_asignaciones["usuario"].dropna().unique())
    if not usuarios:
        st.warning("No hay usuarios disponibles.")
        return
    usuario = st.selectbox("Selecciona el usuario:", usuarios, key="filtro_usuario_inventarios")
    asignadas = df_asignaciones[df_asignaciones["usuario"] == usuario].copy()
    asignadas["_id"] = asignadas.apply(_id_estacion, axis=1)
    asignadas = asignadas[asignadas["_id"].ne("")]
    if asignadas.empty:
        st.info("No hay estaciones registradas para el usuario seleccionado.")
        return

    df_inv = pd.DataFrame(db.obtener_inventarios() or [])
    df_tanques = validacion.obtener_mapa_tanques()
    if df_tanques.empty:
        st.warning("No hay tanques/productos configurados; no se habilita ninguna captura.")
        return
    df_tanques = df_tanques.copy()
    df_tanques["id_estacion"] = df_tanques["id_estacion"].astype(str).str.strip()
    df_tanques["producto"] = df_tanques["producto"].astype(str).str.strip().str.casefold()
    permitidos = set(zip(df_tanques["id_estacion"], df_tanques["producto"]))

    entradas = {}
    for _, estacion_row in asignadas.iterrows():
        estacion = estacion_row["_id"]
        relacion = estacion_row.get("estaciones")
        nombre = relacion.get("nombre", "") if isinstance(relacion, dict) else estacion_row.get("nombre", "")
        plaza = relacion.get("plaza", "") if isinstance(relacion, dict) else estacion_row.get("plaza", "")
        st.markdown(f"#### {estacion} — {nombre} ({plaza})")
        columnas = st.columns(3)
        for columna, producto in zip(columnas, PRODUCTOS):
            with columna:
                if (estacion, producto.casefold()) not in permitidos:
                    st.caption(f"{producto}: sin tanque asignado; captura deshabilitada")
                    continue
                valor = _valor_existente(df_inv, estacion, producto, fecha)
                entradas[(estacion, producto)] = st.number_input(
                    producto,
                    min_value=0,
                    value=valor,
                    step=1,
                    format="%d",
                    key=f"inventario_{estacion}_{producto}_{fecha.isoformat()}",
                )

    if st.button("Guardar/Actualizar Inventario", type="primary", use_container_width=True):
        try:
            cambios = 0
            for (estacion, producto), valor in entradas.items():
                entero = db.validar_numero_entero(valor, f"{producto} de {estacion}", minimo=0)
                anterior = _valor_existente(df_inv, estacion, producto, fecha)
                if entero != anterior:
                    db.insertar_inventario(estacion, fecha, producto, entero)
                    cambios += 1
            st.success(f"Inventarios actualizados correctamente. Cambios guardados: {cambios}.")
            st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(f"No se guardaron los cambios: {exc}")
        except Exception as exc:
            st.error(f"Ocurrió un error al guardar los inventarios: {exc}")
