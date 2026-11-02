        if producto == "Regular":
            color_Hex = "#2e7d32"
        elif producto == "Premium":
            color_Hex = "#d84315"
        else:
            color_Hex = "#424242"

        st.markdown(f"<h3 style='color: {color_Hex};'>⛽ {producto}</h3>", unsafe_allow_html=True)

        inv_inicial_hoy = 0.0
        if not df_inv_hoy.empty and "producto" in df_inv_hoy.columns:
            match_prod = df_inv_hoy[df_inv_hoy["producto"].str.capitalize() == producto]
            if not match_prod.empty:
                inv_inicial_hoy = float(match_prod["volumen"].values[0])

        fechas_cols = []
        inv_iniciales = []
        ventas_est = []
        inv_finales = []
        dias_inventario = []

        inv_actual = inv_inicial_hoy

        for i in range(14):
            fecha_dia = fecha_hoy + timedelta(days=i)
            fecha_fmt = formatear_fecha_corta(fecha_dia)
            fechas_cols.append(fecha_fmt)

            venta_estimada_dia = 0.0
            if not df_factores.empty:
                mask = (
                    (df_factores["id_estacion"] == id_estacion_sel) &
                    (df_factores["producto"].str.capitalize() == producto)
                )

                if "dia_index" in df_factores.columns:
                    match_venta = df_factores[mask & (df_factores["dia_index"] == fecha_dia.weekday())]
                    if not match_venta.empty and "venta_proyectada_dia" in match_venta.columns:
                        val = match_venta["venta_proyectada_dia"].values[0]
                        if pd.notna(val):
                            venta_estimada_dia = float(val)
                    elif not match_venta.empty and "vdp_ponderada" in match_venta.columns:
                        val = match_venta["vdp_ponderada"].values[0]
                        if pd.notna(val):
                            venta_estimada_dia = float(val)

            inv_inicial = inv_actual
            inv_final = inv_inicial - venta_estimada_dia
            ds = (inv_final / venta_estimada_dia) if venta_estimada_dia > 0 else 0.0

            inv_iniciales.append(round(inv_inicial, 2))
            ventas_est.append(round(venta_estimada_dia, 2))
            inv_finales.append(round(inv_final, 2))
            dias_inventario.append(round(ds, 1))

            inv_actual = inv_final

        data_dict = {
            "Concepto": ["Inventario Inicial", "Venta Estimada", "Inventario Final", "D/S"]
        }
        for idx, fecha_fmt in enumerate(fechas_cols):
            data_dict[fecha_fmt] = [
                inv_iniciales[idx],
                ventas_est[idx],
                inv_finales[idx],
                dias_inventario[idx]
            ]

        df_proyeccion = pd.DataFrame(data_dict)

        column_config = {
            "Concepto": st.column_config.TextColumn("Concepto", width="medium")
        }
        for col in [c for c in df_proyeccion.columns if c != "Concepto"]:
            column_config[col] = st.column_config.NumberColumn(col, width="small", format="%.2f")

        st.dataframe(
            df_proyeccion,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )
