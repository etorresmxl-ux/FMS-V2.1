import streamlit as st
import pandas as pd
from servicios.data_output import DataOutputService

def render_inventarios(supabase_client, usuario_actual, data_loader):
    st.subheader("Gestión de Inventarios")
    
    # 1. Obtener los datos maestros cacheados mediante el data_loader
    datos_maestros = data_loader.cargar_datos_maestros()
    df_tanques = datos_maestros.get("tanques_estaciones", pd.DataFrame())
    df_usr = datos_maestros.get("estaciones_usuario", pd.DataFrame())
    
    # Filtrar estaciones correspondientes al usuario actual
    if not df_usr.empty:
        # Nota: Asegúrate de adaptar la condición según la estructura exacta de tu DataFrame de estaciones_usuario
        estaciones_usuario = df_usr[df_usr["usuario"] == usuario_actual]
    else:
        estaciones_usuario = pd.DataFrame()
        
    if estaciones_usuario.empty:
        st.warning(f"El usuario '{usuario_actual}' no tiene estaciones asignadas en este momento.")
        return

    st.write(f"Estaciones asignadas cargadas correctamente para **{usuario_actual}**.")

    # 2. Instanciar el servicio de salida y validación
    output_service = DataOutputService()
    
    # --- AQUí VA TU COMPONENTE DE INTERFAZ (ej. st.data_editor o formularios) ---
    st.info("Utilice el formulario o la tabla interactiva para registrar los inventarios del día.")
    
    # Simulación del DataFrame ingresado por el usuario (reemplaza esto con tu st.data_editor)
    # df_input = ... 
    
    # Ejemplo de botón para procesar y guardar la salida
    if st.button("Guardar Inventarios"):
        # Supongamos que df_input contiene los datos capturados por el usuario
        df_input = pd.DataFrame() # Reemplazar con el DataFrame real de la interfaz
        
        # 3. Validar y normalizar usando el servicio de salida con los datos de los tanques en caché
        exito, mensaje, registros = output_service.validar_y_normalizar(df_input, df_tanques)
        
        if not exito:
            st.error(mensaje)
        else:
            try:
                # Escritura real en la base de datos de Supabase
                if registros:
                    supabase_client.table("inventarios").upsert(registros).execute()
                
                # 4. Invalidar de forma quirúrgica la caché de inventarios para reflejar los cambios al instante[cite: 3]
                data_loader.invalidar_inventarios()
                
                st.success("¡Inventarios guardados y validados correctamente en Supabase!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error al escribir en la base de datos: {e}")
