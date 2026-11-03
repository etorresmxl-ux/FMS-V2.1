import pandas as pd


class ValidadorInventario:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def obtener_estaciones_por_usuario(self, usuario: str) -> list:
        """Retorna los id_estacion asociados a un usuario."""
        if not usuario:
            return []

        response = self.supabase.table("estaciones_usuario") \
            .select("id_estacion") \
            .eq("usuario", usuario) \
            .execute()

        if not response.data:
            return []

        return [item["id_estacion"] for item in response.data if item.get("id_estacion") is not None]

    def obtener_inventario_lote(
        self,
        usuario: str | None = None,
        id_estacion: list | str | None = None,
        fecha: str | None = None,
        producto: str | None = None
    ) -> pd.DataFrame:
        """Obtiene inventarios usando los filtros base: usuario, id_estacion, fecha, producto."""
        query = self.supabase.table("inventarios").select("id_estacion, usuario, fecha, producto, volumen")

        if usuario is not None:
            query = query.eq("usuario", usuario)

        if id_estacion is not None:
            ids = id_estacion if isinstance(id_estacion, list) else [id_estacion]
            ids = [item for item in ids if item is not None]
            if ids:
                query = query.in_("id_estacion", ids)

        if fecha is not None:
            query = query.eq("fecha", str(fecha))

        if producto is not None:
            query = query.eq("producto", producto)

        response = query.execute()
        return pd.DataFrame(response.data or [])

    def obtener_capacidades_lote(self, ids_estaciones: list) -> dict:
        """Consulta en una sola petición los límites de capacidad para todas las estaciones indicadas."""
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
                prod = str(item["producto"]).lower().strip()
                capacidades.setdefault(est, {})[prod] = {
                    "limite_max": item.get("limite_max"),
                    "limite_min": item.get("limite_min")
                }
        return capacidades

    def validar_y_normalizar(self, df_input: pd.DataFrame, usuario: str) -> tuple[bool, str, list]:
        """Normaliza los valores del editor y valida cada volumen de inventario."""
        registros_a_guardar = []
        ids_estaciones = df_input["id_estacion"].tolist()
        capacidades_globales = self.obtener_capacidades_lote(ids_estaciones)
        productos_validos = ["regular", "premium", "diesel"]

        for _, row in df_input.iterrows():
            id_estacion = row["id_estacion"]
            capacidades_estacion = capacidades_globales.get(id_estacion, {})

            for prod in productos_validos:
                val_celda = row.get(prod)

                if pd.isna(val_celda) or val_celda is None:
                    continue

                if prod not in capacidades_estacion:
                    return False, f"El producto '{prod}' no está disponible en la estación {id_estacion}.", []

                try:
                    volumen = int(val_celda)
                except (ValueError, TypeError):
                    return False, f"El volumen para {prod} en la estación {id_estacion} debe ser un número entero.", []

                if volumen < 0:
                    return False, f"El volumen de {prod} en la estación {id_estacion} no puede ser negativo.", []

                limite_max = capacidades_estacion[prod].get("limite_max")
                if limite_max is not None and volumen > limite_max:
                    return False, f"El volumen ({volumen}) de {prod} en la estación {id_estacion} supera el límite máximo permitido ({limite_max}).", []

                registros_a_guardar.append({
                    "id_estacion": id_estacion,
                    "usuario": usuario,
                    "producto": prod,
                    "volumen": int(volumen)
                })

        return True, "Validación exitosa", registros_a_guardar
