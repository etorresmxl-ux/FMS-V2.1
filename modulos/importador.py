import pandas as pd
import streamlit as st

import database as db


def limpiar_y_normalizar_estaciones(df):
    if df is None or df.empty:
        raise ValueError("El archivo Excel está vacío o no tiene registros.")

    df = df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    columnas_requeridas = ["id_estacion", "nombre", "plaza", "tad"]
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltantes)}")

    df["id_estacion"] = df["id_estacion"].apply(lambda x: "" if pd.isna(x) else str(x).strip().upper())
    df["nombre"] = df["nombre"].apply(lambda x: "" if pd.isna(x) else str(x).strip())
    df["plaza"] = df["plaza"].apply(lambda x: "" if pd.isna(x) else str(x).strip())
    df["tad"] = df["tad"].apply(lambda x: "" if pd.isna(x) else str(x).strip())

    df = df[df["id_estacion"].ne("")].copy()
    df = df.drop_duplicates(subset=["id_estacion"], keep="last")
    return df


def _normalizar_valores_excel(df, columnas_requeridas):
    df = df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas obligatorias: {', '.join(faltantes)}")
    return df


def _coerce_numeric(value):
    if pd.isna(value):
        return None
    try:
        numero = float(value)
    except (TypeError, ValueError):
        return None
    return numero if pd.notna(numero) else None


def procesar_importacion_estaciones(archivo_subido):
    try:
        df_raw = pd.read_excel(archivo_subido)
        df_limpio = limpiar_y_normalizar_estaciones(df_raw)

        exitos = 0
        errores = 0
        mensajes = []

        for _, row in df_limpio.iterrows():
            try:
                db.insertar_estacion(
                    id_estacion=row["id_estacion"],
                    nombre=row["nombre"],
                    plaza=row["plaza"],
                    tad=row["tad"],
                )
                exitos += 1
            except Exception as exc:
                errores += 1
                mensajes.append(str(exc))

        if errores and exitos == 0:
            return False, f"Fallaron todos los registros. Último error: {mensajes[-1] if mensajes else 'sin detalle'}", errores, df_limpio

        if errores:
            return True, f"Se procesaron {exitos} registros correctamente. {errores} registros fallaron.", errores, df_limpio

        return True, exitos, 0, df_limpio
    except Exception as exc:
        return False, str(exc), 0, None


def procesar_importacion_inventarios(archivo_subido):
    try:
        df_raw = pd.read_excel(archivo_subido)
        df_limpio = _normalizar_valores_excel(df_raw, ["id_estacion", "fecha", "producto", "volumen"])
        df_limpio["id_estacion"] = df_limpio["id_estacion"].apply(lambda x: "" if pd.isna(x) else str(x).strip().upper())
        df_limpio["producto"] = df_limpio["producto"].apply(lambda x: "" if pd.isna(x) else str(x).strip())
        df_limpio["volumen"] = df_limpio["volumen"].apply(_coerce_numeric)
        df_limpio = df_limpio[df_limpio["id_estacion"].ne("")].copy()

        exitos = 0
        errores = 0
        mensajes = []

        for _, row in df_limpio.iterrows():
            try:
                if row["volumen"] is None:
                    raise ValueError("El volumen no es válido.")
                db.insertar_inventario(
                    id_estacion=row["id_estacion"],
                    fecha=row["fecha"],
                    producto=row["producto"],
                    volumen=row["volumen"],
                )
                exitos += 1
            except Exception as exc:
                errores += 1
                mensajes.append(str(exc))

        if errores and exitos == 0:
            return False, f"Fallaron todos los registros. Último error: {mensajes[-1] if mensajes else 'sin detalle'}", errores, df_limpio

        if errores:
            return True, f"Se procesaron {exitos} registros correctamente. {errores} registros fallaron.", errores, df_limpio

        return True, exitos, 0, df_limpio
    except Exception as exc:
        return False, str(exc), 0, None


def procesar_importacion_ventas(archivo_subido):
    try:
        df_raw = pd.read_excel(archivo_subido)
        df_limpio = _normalizar_valores_excel(df_raw, ["id_estacion", "fecha", "producto", "volumen"])
        df_limpio["id_estacion"] = df_limpio["id_estacion"].apply(lambda x: "" if pd.isna(x) else str(x).strip().upper())
        df_limpio["producto"] = df_limpio["producto"].apply(lambda x: "" if pd.isna(x) else str(x).strip())
        df_limpio["volumen"] = df_limpio["volumen"].apply(_coerce_numeric)
        df_limpio = df_limpio[df_limpio["id_estacion"].ne("")].copy()

        exitos = 0
        errores = 0
        mensajes = []

        for _, row in df_limpio.iterrows():
            try:
                if row["volumen"] is None:
                    raise ValueError("El volumen no es válido.")
                db.insertar_venta(
                    id_estacion=row["id_estacion"],
                    fecha=row["fecha"],
                    producto=row["producto"],
                    volumen=row["volumen"],
                )
                exitos += 1
            except Exception as exc:
                errores += 1
                mensajes.append(str(exc))

        if errores and exitos == 0:
            return False, f"Fallaron todos los registros. Último error: {mensajes[-1] if mensajes else 'sin detalle'}", errores, df_limpio

        if errores:
            return True, f"Se procesaron {exitos} registros correctamente. {errores} registros fallaron.", errores, df_limpio

        return True, exitos, 0, df_limpio
    except Exception as exc:
        return False, str(exc), 0, None


def mostrar_importador():
    st.header("📥 Módulo de Importación de Datos")

    tipo_archivo = st.selectbox(
        "Selecciona el tipo de datos a importar:",
        ["Estaciones", "Inventarios", "Ventas"],
    )

    archivo_subido = st.file_uploader(
        f"Sube el archivo Excel para {tipo_archivo}",
        type=["xlsx", "xls"],
    )

    if archivo_subido is not None:
        if st.button("Procesar e Importar"):
            with st.spinner("Procesando archivo..."):
                if tipo_archivo == "Estaciones":
                    exitos, resultado_msg, errores, df_resultado = procesar_importacion_estaciones(archivo_subido)
                elif tipo_archivo == "Inventarios":
                    exitos, resultado_msg, errores, df_resultado = procesar_importacion_inventarios(archivo_subido)
                else:
                    exitos, resultado_msg, errores, df_resultado = procesar_importacion_ventas(archivo_subido)

                if exitos:
                    st.success(f"¡Importación procesada! {resultado_msg}")
                    if df_resultado is not None:
                        st.dataframe(df_resultado.head(), use_container_width=True)
                else:
                    st.error(f"Hubo un error en la importación: {resultado_msg}")
