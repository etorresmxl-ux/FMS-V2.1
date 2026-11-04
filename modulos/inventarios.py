import streamlit as st
import pandas as pd
from datetime import date
from servicios.validacion import ValidadorInventario
from servicios.data_loader import DataLoaderService

def render_inventarios(supabase_client, usuario_actual: str):
    st.subheader("Gestión de Inventarios")
    
    # 1. Instanciar el servicio de carga de datos y obtener los datos maestros cacheados
    data_loader = DataLoaderService(supabase_client)
    datos_maestros = data_loader.cargar_datos_maestros()
    
    # 2. Extraer catálogos e inventarios desde la estructura centralizada
    df_usr = datos_maestros.get("estaciones_usuario", pd.DataFrame())
    df_tanques = datos_maestros.get("tanques_estaciones", pd.DataFrame())
    df_inventarios = datos_maestros.get("inventarios", pd.DataFrame())
    
    # 3. Filtrar estaciones asignadas al usuario actual
    if not df_usr.empty and "usuario" in df_usr.columns:
        estaciones_usuario = df_usr[df_usr["usuario"] == usuario_actual]
    else:
        estaciones_usuario = pd.DataFrame()
        
    if estaciones_usuario.empty:
        st.warning(f"No hay estaciones asignadas para el usuario: {usuario_actual}")
        return

    # 4. Construir opciones de selección de estación
    options_estaciones = {}
    for _, row in estaciones_usuario.iterrows():
        id_est = row["id_estacion"]
        est_info = row.get("estaciones", {})
        nombre_est = est_info.get("nombre", f"Estación {id_est}") if isinstance(est_info, dict) else f"Estación {id_est}"
        options_estaciones[f"{id_est} - {nombre_est}"] = id_est

    if not options_estaciones:
        st.error("No se pudieron cargar las estaciones para este usuario.")
        return

    selected_label = st.selectbox("Selecciona la Estación:", options=list(options_estaciones.keys()))
    id_estacion_seleccionada = options_estaciones[selected_label]

    # 5. Selección de fecha de registro
    fecha_inventario = st.date_input("Fecha de Registro:", value=date.today())

    st.markdown("### Captura de Volúmenes por Tanque")
    
    # Filtrar tanques de la estación seleccionada usando los datos del data_loader
    tanques_estacion = df_tanques[df_tanques["id_estacion"] == id_estacion_seleccionada] if not df_tanques.empty else pd.DataFrame()
    
    if tanques_estacion.empty:
        st.info("No hay tanques configurados para esta estación en los datos maestros.")
        return

    volumenes_capturados = {}
    validador = ValidadorInventario()

    # Renderizar inputs para cada producto/tanque
    for _, tanque in tanques_estacion.iterrows():
        producto = tanque["producto"]
        limite_max = tanque.get("limite_max", 10000)
        limite_min = tanque.get("limite_min", 5000)
        
        volumen = st.number_input(
            f"Volumen para {producto} (Límites: Mín {limite_min:,} - Máx {limite_max:,})",
            min_value=0.0,
            max_value=float(limite_max) * 1.5,
            step=100.0,
            key=f"vol_{id_estacion_seleccionada}_{producto}"
        )
        volumenes_capturados[producto] = volumen

    st.markdown("---")
    
    # 6. Botón de guardado y validación
    if st.button("Guardar Inventarios", type="primary"):
        # Validar con la clase ValidadorInventario usando el inventario maestro en caché
        valido, mensaje = validador.validar(
            id_estacion_seleccionada, 
            fecha_inventario, 
            volumenes_capturados, 
            df_tanques, 
            df_inventarios
        )
        
        if not valido:
            st.error(f"Error de validación: {mensaje}")
        else:
            try:
                registros_a_guardar = []
                for producto, volumen in volumenes_capturados.items():
                    registros_a_guardar.append({
                        "id_estacion": id_estacion_seleccionada,
                        "fecha": str(fecha_inventario),
                        "producto": producto,
                        "volumen": volumen
                    })
                
                # Insertar en Supabase
                res = supabase_client.table("inventarios").insert(registros_a_guardar).execute()
                exito = True if res.data else False
            except Exception as e:
                st.error(f"Error al guardar en Supabase: {e}")
                exito = False

            if exito:
                # 7. Invalidar la caché del data_loader de forma quirúrgica para refrescar inventarios
                data_loader.invalidar_inventarios()
                
                st.success("¡Inventarios guardados y validados correctamente en Supabase!")
                st.rerun()
