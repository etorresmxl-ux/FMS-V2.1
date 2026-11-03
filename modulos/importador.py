import pandas as pd
import streamlit as st

import database as db

PRODUCTOS_VALIDOS = {"regular", "premium", "diesel"}


def limpiar_y_normalizar_estaciones(df):
    if df is None or df.empty:
        raise ValueError("El archivo Excel está vacío o no tiene registros.")
    df = df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    requeridas = ["id_estacion", "nombre", "plaza", "tad"]
    faltantes = [col for col in requeridas if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltantes)}")
    for col in requeridas:
        df[col] = df[col].apply(lambda x: "" if pd.isna(x) else str(x).strip())
    df["id_estacion"] = df["id_estacion"].str.upper()
    df = df[df["id_estacion"].ne("") & df["nombre"].ne("")].copy()
    return df.drop_duplicates(subset=["id_estacion"], keep="last")


def _leer_excel(archivo, columnas_requeridas):
    df = pd.read_excel(archivo)
    if df.empty:
        raise ValueError("El archivo Excel no contiene registros.")
    df.columns = [str(col).strip().lower() for col in df.columns]
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltantes)}")
    return df


def _normalizar_filas_volumen(df):
    df = df.copy()
    df["id_estacion"] = df["id_estacion"].apply(lambda x: "" if pd.isna(x) else str(x).strip().upper())
    df["producto"] = df["producto"].apply(lambda x: "" if pd.isna(x) else str(x).strip())
    df["_error"] = ""
    for idx, row in df.iterrows():
        if not row["id_estacion"]:
            df.at[idx, "_error"] = "ID de estación obligatorio"
            continue
        if row["producto"].casefold() not in PRODUCTOS_VALIDOS:
            df.at[idx, "_error"] = "Producto inválido"
            continue
        try:
            df.at[idx, "volumen"] = db.validar_numero_entero(row["volumen"], "volumen", minimo=0)
        except ValueError as exc:
            df.at[idx, "_error"] = str(exc)
    return df


def _procesar_importacion_volumen(archivo, tabla):
    try:
        df = _normalizar_filas_volumen(_leer_excel(archivo, ["id_estacion", "fecha", "producto", "volumen"]))
        aceptadas = df[df["_error"].eq("")].copy()
        rechazadas = df[~df["_error"].eq("")].copy()
        guardadas, errores_db = 0, []
        for _, row in aceptadas.iterrows():
            try:
                guardar = db.insertar_inventario if tabla == "inventarios" else db.insertar_venta
                guardar(row["id_estacion"], row["fecha"], row["producto"], row["volumen"])
                guardadas += 1
            except Exception as exc:
                errores_db.append(str(exc))
        cantidad_rechazada = len(rechazadas) + len(errores_db)
        mensaje = f"Guardados: {guardadas}; rechazados: {cantidad_rechazada}."
        if errores_db:
            mensaje += f" Último error de base de datos: {errores_db[-1]}"
        return guardadas > 0, mensaje, cantidad_rechazada, rechazadas
    except Exception as exc:
        return False, str(exc), 0, None


def procesar_importacion_estaciones(archivo_subido):
    try:
        df = limpiar_y_normalizar_estaciones(_leer_excel(archivo_subido, ["id_estacion", "nombre", "plaza", "tad"]))
        guardadas, errores = 0, []
        for _, row in df.iterrows():
            try:
                db.insertar_estacion(row["id_estacion"], row["nombre"], row["plaza"], row["tad"])
                guardadas += 1
            except Exception as exc:
                errores.append(str(exc))
        rechazadas = len(errores)
        mensaje = f"Guardadas: {guardadas}; rechazadas: {rechazadas}."
        if errores:
            mensaje += f" Último error: {errores[-1]}"
        return guardadas > 0, mensaje, rechazadas, df
    except Exception as exc:
        return False, str(exc), 0, None


def procesar_importacion_inventarios(archivo_subido):
    return _procesar_importacion_volumen(archivo_subido, "inventarios")


def procesar_importacion_ventas(archivo_subido):
    return _procesar_importacion_volumen(archivo_subido, "ventas")


def mostrar_importador():
    st.header("📥 Módulo de Importación de Datos")
    tipo = st.selectbox("Selecciona el tipo de datos a importar:", ["Estaciones", "Inventarios", "Ventas"])
    archivo = st.file_uploader(f"Sube el archivo Excel para {tipo}", type=["xlsx", "xls"])
    if archivo is not None and st.button("Procesar e Importar"):
        with st.spinner("Validando e importando archivo..."):
            if tipo == "Estaciones":
                exito, mensaje, errores, resultado = procesar_importacion_estaciones(archivo)
            elif tipo == "Inventarios":
                exito, mensaje, errores, resultado = procesar_importacion_inventarios(archivo)
            else:
                exito, mensaje, errores, resultado = procesar_importacion_ventas(archivo)
        if exito and errores == 0:
            st.success(mensaje)
        elif exito:
            st.warning(mensaje)
        else:
            st.error(mensaje)
        if resultado is not None:
            st.dataframe(resultado.head(), use_container_width=True)
