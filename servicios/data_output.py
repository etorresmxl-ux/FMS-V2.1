import pandas as pd

class DataOutputService:
    def __init__(self):
        """
        Servicio dedicado a la validación, normalización y preparación de los datos de salida 
        antes de ser escritos en la base de datos (Supabase).
        Reglas aplicadas:
        - id_estacion EXCLUIDO de minúsculas (respeta el formato original E##### de la BD).
        - Varchars secundarios (producto) siempre en minúsculas.
        - Datos numéricos siempre en enteros.
        """
        pass

    def normalizar_programa_cargas(self, df_editado: pd.DataFrame, columnas_fechas_str: list, producto_target: str) -> list:
        """
        Procesa el DataFrame editado desde la interfaz de Streamlit para la tabla programa_cargas,
        aplicando la normalización:
        - id_estacion preserva su formato original (E#####).
        - producto en minúsculas (varchar).
        - volumen convertido estrictamente a entero.
        """
        registros_a_guardar = []
        producto_norm = str(producto_target).lower().strip()

        for _, row in df_editado.iterrows():
            # Obtener id_estacion conservando su formato original (sin .lower() para evitar error de FK)
            id_estacion_raw = row.get("ID Estacion") or row.get("id_estacion") or row.get("id_estacion_db_hidden")
            if pd.isna(id_estacion_raw) or not str(id_estacion_raw).strip():
                continue
            
            id_estacion_val = str(id_estacion_raw).strip()

            for f_str in columnas_fechas_str:
                val = row.get(f_str)

                # Si la celda está vacía o nula, se omite
                if pd.isna(val) or val == "" or val is None:
                    continue

                try:
                    # Normalización estricta a número entero
                    volumen_entero = int(float(val))
                except (ValueError, TypeError):
                    continue

                # Solo registrar si hay volumen válido
                if volumen_entero > 0:
                    registros_a_guardar.append({
                        "id_estacion": id_estacion_val,    # Formato original E##### (respetando mayúscula inicial)
                        "fecha": f_str,                    # Fecha en formato YYYY-MM-DD
                        "producto": producto_norm,         # Varchar en minúsculas
                        "volumen": volumen_entero          # Numérico entero
                    })

        return registros_a_guardar

    def validar_y_normalizar(self, df_input: pd.DataFrame, df_tanques_cache: pd.DataFrame) -> tuple[bool, str, list]:
        """
        Valida y normaliza datos generales frente a los límites maestros de tanques.
        Asegura el formato original en id_estacion y minúsculas en productos.
        """
        registros_a_guardar = []
        productos_validos = ["regular", "premium", "diesel"]

        capacidades_globales = {}
        if not df_tanques_cache.empty:
            for _, row in df_tanques_cache.iterrows():
                # Para mapeo interno con caché se puede usar minúsculas de forma segura
                est = str(row["id_estacion"]).strip()
                prod = str(row["producto"]).lower().strip()
                if est not in capacidades_globales:
                    capacidades_globales[est] = {}
                capacidades_globales[est][prod] = {
                    "limite_max": int(row.get("limite_max")) if pd.notna(row.get("limite_max")) else None,
                    "limite_min": int(row.get("limite_min", 5000))
                }

        for _, row in df_input.iterrows():
            id_estacion = str(row.get("id_estacion", "")).strip()
            capacidades_estacion = capacidades_globales.get(id_estacion, {})
            
            for prod in productos_validos:
                prod_norm = str(prod).lower().strip()
                val_celda = row.get(prod_norm)

                if pd.isna(val_celda) or val_celda is None:
                    continue

                if prod_norm not in capacidades_estacion:
                    return False, f"El producto '{prod_norm}' no está disponible en la estación {id_estacion}.", []

                try:
                    volumen = int(float(val_celda))
                except (ValueError, TypeError):
                    return False, f"El volumen para {prod_norm} en la estación {id_estacion} debe ser un número entero.", []

                if volumen < 0:
                    return False, f"El volumen de {prod_norm} en la estación {id_estacion} no puede ser negativo.", []

                limite_max = capacidades_estacion[prod_norm].get("limite_max")
                limite_min = capacidades_estacion[prod_norm].get("limite_min", 5000)

                if limite_max is not None and volumen > limite_max:
                    return False, f"El volumen ({volumen}) de {prod_norm} en la estación {id_estacion} supera el límite máximo permitido ({limite_max}).", []

                if volumen < limite_min:
                    return False, f"El volumen ({volumen}) de {prod_norm} en la estación {id_estacion} es menor al límite mínimo permitido ({limite_min}).", []

                registros_a_guardar.append({
                    "id_estacion": id_estacion,  # Conserva formato original E#####
                    "producto": prod_norm,       # Varchar minúsculas
                    "volumen": int(volumen)      # Numérico entero
                })
                
        return True, "Validación exitosa", registros_a_guardar
