import pandas as pd

class DataOutputService:
    def __init__(self):
        """
        Servicio dedicado a la validación, normalización y preparación 
        de los datos de salida antes de ser escritos en la base de datos.
        """
        pass

    def validar_y_normalizar(self, df_input: pd.DataFrame, df_tanques_cache: pd.DataFrame) -> tuple[bool, str, list]:
        """
        Valida los datos ingresados en la interfaz de usuario frente a los límites 
        maestros de los tanques almacenados en caché por el DataLoaderService.
        """
        registros_a_guardar = []
        productos_validos = ["regular", "premium", "diesel"]

        # Indexar capacidades globales para búsqueda rápida en memoria
        capacidades_globales = {}
        if not df_tanques_cache.empty:
            for _, row in df_tanques_cache.iterrows():
                est = row["id_estacion"]
                prod = str(row["producto"]).lower().strip()
                if est not in capacidades_globales:
                    capacidades_globales[est] = {}
                capacidades_globales[est][prod] = {
                    "limite_max": row.get("limite_max"),
                    "limite_min": row.get("limite_min", 5000)
                }

        for _, row in df_input.iterrows():
            id_estacion = row["id_estacion"]
            capacidades_estacion = capacidades_globales.get(id_estacion, {})
            
            for prod in productos_validos:
                val_celda = row.get(prod)

                # Si la celda está vacía (None / NaN), omitir lectura y escritura
                if pd.isna(val_celda) or val_celda is None:
                    continue

                # Validar si el producto está configurado en los tanques de la estación
                if prod not in capacidades_estacion:
                    return False, f"El producto '{prod}' no está disponible en la estación {id_estacion}.", []

                try:
                    # Normalización estricta a número entero
                    volumen = int(val_celda)
                except (ValueError, TypeError):
                    return False, f"El volumen para {prod} en la estación {id_estacion} debe ser un número entero.", []

                if volumen < 0:
                    return False, f"El volumen de {prod} en la estación {id_estacion} no puede ser negativo.", []

                # Validar límites del tanque desde memoria
                limite_max = capacidades_estacion[prod].get("limite_max")
                limite_min = capacidades_estacion[prod].get("limite_min", 5000)

                if limite_max is not None and volumen > limite_max:
                    return False, f"El volumen ({volumen}) de {prod} en la estación {id_estacion} supera el límite máximo permitido ({limite_max}).", []

                if volumen < limite_min:
                    return False, f"El volumen ({volumen}) de {prod} en la estación {id_estacion} es menor al límite mínimo permitido ({limite_min}).", []

                # Datos normalizados listos para la salida hacia la BD
                registros_a_guardar.append({
                    "id_estacion": id_estacion,
                    "producto": prod,
                    "volumen": int(volumen)
                })
                
        return True, "Validación exitosa", registros_a_guardar
