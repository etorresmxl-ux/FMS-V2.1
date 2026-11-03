import pandas as pd

class ValidadorInventario:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def obtener_capacidades_tanques(self, id_estacion: str) -> dict:
        """Consulta los límites y capacidades máximas de los tanques por estación."""
        response = self.supabase.table("tanques_estaciones") \
            .select("producto, limite_max, limite_min") \
            .eq("id_estacion", id_estacion) \
            .execute()
        
        capacidades = {}
        if response.data:
            for item in response.data:
                capacidades[item["producto"].lower()] = {
                    "limite_max": item["limite_max"],
                    "limite_min": item["limite_min"]
                }
        return capacidades

    def validar_y_normalizar(self, df_input: pd.DataFrame, usuario: str) -> tuple[bool, str, list]:
        """
        Normaliza los datos de entrada a enteros y valida contra los límites de los tanques.
        """
        registros_a_guardar = []
        
        for _, row in df_input.iterrows():
            id_estacion = row["id_estacion"]
            capacidades = self.obtener_capacidades_tanques(id_estacion)
            
            productos = ["regular", "premium", "diesel"]
            for prod in productos:
                if prod in row and pd.notna(row[prod]):
                    try:
                        # Asegurar que sea número entero
                        volumen = int(row[prod])
                    except ValueError:
                        return False, f"El volumen para {prod} en la estación {id_estacion} debe ser un número entero.", []

                    # Validar límites del tanque si existen configurados
                    if prod in capacidades:
                        limite_max = capacidades[prod]["limite_max"]
                        if limite_max is not None and volumen > limite_max:
                            return False, f"El volumen ({volumen}) de {prod} en la estación {id_estacion} supera el límite máximo permitido ({limite_max}).", []
                    
                    if volumen < 0:
                        return False, f"El volumen de {prod} en la estación {id_estacion} no puede ser negativo.", []

                    registros_a_guardar.append({
                        "id_estacion": id_estacion,
                        "producto": prod,
                        "volumen": float(volumen)
                    })
                    
        return True, "Validación exitosa", registros_a_guardar
