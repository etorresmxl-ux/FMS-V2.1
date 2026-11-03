import pandas as pd

class ValidadorInventario:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def obtener_capacidades_lote(self, ids_estaciones: list) -> dict:
        """
        Consulta en una sola petición (lote) los límites y capacidades máximas 
        de los tanques para todas las estaciones indicadas, optimizando el rendimiento.
        """
        if not ids_estaciones:
            return {}
            
        response = self.supabase.table("tanques_estaciones") \
            .select("id_estacion, producto, limite_max, limite_min") \
            .in_("id_estacion", ids_estaciones) \
            .execute()
        
        capacidades = {}
        if response.data:
            for item in response.data:
                est = item["id_estacion"]
                prod = item["producto"].lower().strip()
                if est not in capacidades:
                    capacidades[est] = {}
                capacidades[est][prod] = {
                    "limite_max": item.get("limite_max"),
                    "limite_min": item.get("limite_min")
                }
        return capacidades

    def validar_y_normalizar(self, df_input: pd.DataFrame, usuario: str) -> tuple[bool, str, list]:
        """
        Normaliza y valida los datos de entrada de la tabla interactiva frente a los límites 
        de los tanques en Supabase de forma masiva y eficiente.
        """
        registros_a_guardar = []
        ids_estaciones = df_input["id_estacion"].tolist()
        
        # Cargar todas las capacidades en una sola consulta por rendimiento
        capacidades_globales = self.obtener_capacidades_lote(ids_estaciones)
        
        productos_validos = ["regular", "premium", "diesel"]

        for _, row in df_input.iterrows():
            id_estacion = row["id_estacion"]
            capacidades_estacion = capacidades_globales.get(id_estacion, {})
            
            for prod in productos_validos:
                if prod in row and pd.notna(row[prod]):
                    try:
                        # Normalización estricta a número entero
                        volumen = int(row[prod])
                    except ValueError:
                        return False, f"El volumen para {prod} en la estación {id_estacion} debe ser un número entero.", []

                    if volumen < 0:
                        return False, f"El volumen de {prod} en la estación {id_estacion} no puede ser negativo.", []

                    # Validar límites del tanque si están configurados en Supabase
                    if prod in capacidades_estacion:
                        limite_max = capacidades_estacion[prod].get("limite_max")
                        if limite_max is not None and volumen > limite_max:
                            return False, f"El volumen ({volumen}) de {prod} en la estación {id_estacion} supera el límite máximo permitido ({limite_max}).", []

                    # Datos normalizados listos para la salida hacia la BD
                    registros_a_guardar.append({
                        "id_estacion": id_estacion,
                        "producto": prod,
                        "volumen": float(volumen)
                    })
                    
        return True, "Validación exitosa", registros_a_guardar
