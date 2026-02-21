with tab3:
    if len(df) == 0:
        st.info("Belum ada data (atau tidak ada data pada periode terpilih).")
    else:
        stats, _, _, quad_v1_items, quad_v2_items = compute_stats_and_ipa(df)
        dim_stats, _, _, quad_v1_dims, quad_v2_dims = compute_dimension_stats_and_ipa(df)

        quad_order = [
            "I - Concentrate Here",
            "II - Keep Up the Good Work",
            "III - Low Priority",
            "IV - Possible Overkill",
        ]

        def _side_by_side_table(left_list, right_list, left_fmt, right_fmt):
            L = [left_fmt(x) for x in (left_list or [])]
            R = [right_fmt(x) for x in (right_list or [])]
            n = max(len(L), len(R), 1)
            if len(L) < n:
                L += [""] * (n - len(L))
            if len(R) < n:
                R += [""] * (n - len(R))
            return pd.DataFrame({"Versi 1": L, "Versi 2": R})

        # =========================
        # ITEMS
        # =========================
        st.subheader("Daftar item per kuadran (Versi 1 vs Versi 2)")

        for q in quad_order:
            st.markdown(f"### {q}")

            left_items = quad_v1_items.get(q, [])
            right_items = quad_v2_items.get(q, [])

            df_cmp = _side_by_side_table(
                left_items,
                right_items,
                left_fmt=lambda code: f"{code}: {ITEM_TEXT.get(code, '')}",
                right_fmt=lambda code: f"{code}: {ITEM_TEXT.get(code, '')}",
            )

            # ✅ st.table agar teks wrap & tidak terpotong
            st.table(df_cmp)

        st.divider()

        # =========================
        # DIMENSIONS
        # =========================
        st.subheader("Daftar dimensi per kuadran (Versi 1 vs Versi 2)")

        for q in quad_order:
            st.markdown(f"### {q}")

            left_dims = quad_v1_dims.get(q, [])
            right_dims = quad_v2_dims.get(q, [])

            df_cmp = _side_by_side_table(
                left_dims,
                right_dims,
                left_fmt=lambda abbr: f"{abbr}: {DIM_NAME_BY_ABBR.get(abbr, '')}",
                right_fmt=lambda abbr: f"{abbr}: {DIM_NAME_BY_ABBR.get(abbr, '')}",
            )

            # ✅ st.table agar teks wrap & tidak terpotong
            st.table(df_cmp)
