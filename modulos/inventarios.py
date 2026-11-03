import streamlit as st
import pandas as pd
from datetime import date
from servicios.validacion import ValidadorInventario

def render_inventarios(supabase_client, usuario_actual: str):
    st.subheader("Gestión de Inventarios")

    # 1. Filtro por fecha
    fecha_seleccionada = st.date_input("Seleccione la fecha de inventario", value=date.today())

    # 2. Obtener estaciones permitidas para el usuario actual (con caché para rendimiento)
    @st.cache_data(ttl=60)
    def cargar_estaciones_usuario(usuario):
        res_usr = supabase_client.table("estaciones_usuario").select("id_estacion").eq("usuario", usuario).execute()
        ids = [item["id_estacion"] for item in res_usr.data]
        if not ids:
            return pd.DataFrame()
        
        res_est = supabase_client.table("estaciones").select("id_estacion, nombre, plaza").in_("id_estacion", ids).execute()
        return pd.DataFrame(res_est.data)

    df_estaciones = cargar_estaciones_usuario(usuario_actual)

    if df_estaciones.empty:
        st.warning("No tienes estaciones asignadas o registradas en el sistema.")
        return

    # 3. Buscar registros existentes en la base de datos filtrando estrictamente por estaciones y fecha
    ids_estaciones = df_estaciones["id_estacion"].tolist()

    res_inv = supabase_client.table("inventarios") \
        .select("id_estacion, producto, volumen") \
        .eq("fecha", str(fecha_seleccionada)) \
        .in_("id_estacion", ids_estaciones) \
        .execute()

    df_inv = pd.DataFrame(res_inv.data)

    # 4. Obtener tanques/productos disponibles por estación desde tanques_estaciones
    res_tanques = supabase_client.table("tanques_estaciones") \
        .select("id_estacion, producto") \
        .in_("id_estacion", ids_estaciones) \
        .execute()

    tanques_por_estacion = {}
    if res_tanques.data:
        for item in res_tanques.data:
            est = item["id_estacion"]
            prod = item["producto"].lower().strip()
            if est not in tanques_por_estacion:
                tanques_por_estacion[est] = set()
            tanques_por_estacion[est].add(prod)

    # 5. Estructurar la matriz base: Asignar None si el producto no existe en tanques_estaciones
    df_matriz = df_estaciones.copy()

    df_pivot = pd.DataFrame()
    if not df_inv.empty and "producto" in df_inv.columns and "volumen" in df_inv.columns:
        df_inv["producto"] = df_inv["producto"].astype(str).str.lower().str.strip()
        df_pivot = df_inv.pivot_table(index="id_estacion", columns="producto", values="volumen", aggfunc="first")

    for prod in ["regular", "premium", "diesel"]:
        valores_columna = []
        for _, row in df_estaciones.iterrows():
            est_id = row["id_estacion"]
            productos_permitidos = tanques_por_estacion.get(est_id, set())
            
            if prod not in productos_permitidos:
                # Producto NO disponible en esta estación -> Mostrar vacío (None)
                valores_columna.append(None)
            else:
                # Producto disponible -> Mapear valor existente o poner 0 inicial
                if not df_pivot.empty and est_id in df_pivot.index and prod in df_pivot.columns:
                    val = df_pivot.loc[est_id, prod]
                    valores_columna.append(int(val) if pd.notna(val) else 0)
                else:
                    valores_columna.append(0)
                    
        df_matriz[prod] = valores_columna

    st.markdown("Modifique los valores de volumen directamente en la tabla (solo números enteros). Las celdas vacías indican productos no disponibles:")

    # 6. Tabla interactiva (con altura ajustada a 600px)
    df_editado = st.data_editor(
        df_matriz,
        height=600,
        column_config={
            "id_estacion": st.column_config.TextColumn("ID Estación", disabled=True),
            "nombre": st.column_config.TextColumn("Nombre", disabled=True),
            "plaza": st.column_config.TextColumn("Plaza", disabled=True),
            "regular": st.column_config.NumberColumn("Regular", min_value=0, step=1, format="%,d"),
            "premium": st.column_config.NumberColumn("Premium", min_value=0, step=1, format="%,d"),
            "diesel": st.column_config.NumberColumn("Diesel", min_value=0, step=1, format="%,d"),
        },
        hide_index=True,
        key=f"editor_inventarios_{usuario_actual}_{fecha_seleccionada}"
    )

    # 7. Guardado eficiente procesado a través de validacion.py
    if st.button("Guardar Cambios de Inventario", type="primary"):
        validador = ValidadorInventario(supabase_client)
        valido, mensaje, registros = validador.validar_y_normalizar(df_editado, usuario_actual)

        if not valido:
            st.error(mensaje)
        else:
            exito = True
            for reg in registros:
                reg["fecha"] = str(fecha_seleccionada)
                res = supabase_client.table("inventarios").upsert(
                    reg, 
                    on_conflict="id_estacion,fecha,producto"
                ).execute()
                if hasattr(res, 'error') and res.error:
                    exito = False
                    st.error(f"Error al guardar estación {reg['id_estacion']}: {res.error}")
                    break

            if exito:
                st.success("¡Inventarios guardados y validados correctamente en Supabase!")
                st.rerun()
