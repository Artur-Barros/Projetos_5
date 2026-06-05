import streamlit as st
import pandas as pd
from scraper import search_all, search_for_categories, _CATEGORIA_MAP, _CATEGORIA_BUSCA
from analytics import (
    adicionar_variacao_oferta,
    resumo_por_loja,
    variacao_entre_lojas,
    sugerir_melhor_oferta,
)
from charts import (
    grafico_avaliacao_preco,
    grafico_boxplot_precos,
)

MAX_OFERTAS_GRAFICO = 15
LABEL_MAX_CHARS = 40

st.set_page_config(page_title="Pricefy", layout="wide")

st.title("Pricefy")
st.write("Compare preços de produtos entre lojas online.")

TODAS_CATEGORIAS = list(_CATEGORIA_MAP.keys()) + ["Outros"]

CATEGORY_SEARCH_TERMS = {
    "Informática":          "computador notebook",
    "Eletrônicos":          "televisor câmera som",
    "Celulares & Tablets":  "smartphone celular",
    "Eletrodomésticos":     "geladeira microondas fogão",
    "Móveis & Decoração":   "sofá estante guarda-roupa",
    "Roupas & Moda":        "camiseta calça tênis moda",
    "Games":                "videogame console joystick",
    "Outros":               "produto",
}

st.sidebar.header("Filtros")

categorias_selecionadas = st.sidebar.multiselect(
    "Categoria do produto",
    options=TODAS_CATEGORIAS,
    default=[],
    placeholder="Selecione uma ou mais categorias...",
)

if "df_resultados" in st.session_state and not st.session_state.df_resultados.empty:
    df_cache = st.session_state.df_resultados
    preco_min_global = float(df_cache["Preço (R$)"].min())
    preco_max_global = float(df_cache["Preço (R$)"].max())

    if preco_min_global < preco_max_global:
        faixa_preco = st.sidebar.slider(
            "Faixa de preço (R$)",
            min_value=preco_min_global,
            max_value=preco_max_global,
            value=(preco_min_global, preco_max_global),
            format="R$ %.2f",
            step=1.0,
        )
    else:
        faixa_preco = (preco_min_global, preco_max_global)
        st.sidebar.info(f"Preço único encontrado: R$ {preco_min_global:,.2f}")
else:
    faixa_preco = None

query = st.text_input(
    "Buscar produto (opcional — ou selecione uma categoria na barra lateral):",
    placeholder="Ex: notebook, mouse gamer, teclado mecânico...",
)

busca_por_categoria = False

if query:
    search_term = query
elif categorias_selecionadas:
    termos = [CATEGORY_SEARCH_TERMS.get(c, c) for c in categorias_selecionadas[:2]]
    search_term = " ".join(termos)
    busca_por_categoria = True
else:
    search_term = None

if search_term:
    if busca_por_categoria:
        cache_key = "cat:" + "|".join(sorted(categorias_selecionadas[:2]))
    else:
        cache_key = search_term.strip().lower()
    if st.session_state.get("last_search_key") != cache_key:
        with st.spinner("Buscando preços nas lojas..."):
            if busca_por_categoria:
                cats_busca = [c for c in categorias_selecionadas[:2] if c in _CATEGORIA_BUSCA]
                if cats_busca:
                    results = search_for_categories(cats_busca)
                else:
                    results = search_all(search_term)
            else:
                results = search_all(search_term)
        if results:
            df = pd.DataFrame(results)
            df = df[df["Preço (R$)"] > 0].reset_index(drop=True)
            for col, default in [("Avaliação", None), ("Qtd. avaliações", 0)]:
                if col not in df.columns:
                    df[col] = default
            if "Categoria" not in df.columns:
                df["Categoria"] = "Outros"
            else:
                df["Categoria"] = df["Categoria"].fillna("Outros").replace("", "Outros")
            st.session_state.df_resultados = df
        else:
            st.session_state.df_resultados = pd.DataFrame()
        st.session_state.last_search_key = cache_key
        st.rerun()

if "df_resultados" in st.session_state:
    df_full = st.session_state.df_resultados

    if df_full.empty:
        st.warning("Nenhum resultado encontrado. Tente outro termo ou categoria.")
    else:
        for col, default in [("Avaliação", None), ("Qtd. avaliações", 0)]:
            if col not in df_full.columns:
                df_full[col] = default

        if categorias_selecionadas:
            cats_filtro = list(categorias_selecionadas)
            if busca_por_categoria:
                cats_filtro.append("Outros")
        else:
            cats_filtro = list(df_full["Categoria"].unique())

        if faixa_preco:
            df_filtrado = df_full[
                (df_full["Preço (R$)"] >= faixa_preco[0])
                & (df_full["Preço (R$)"] <= faixa_preco[1])
                & (df_full["Categoria"].isin(cats_filtro))
            ].sort_values("Preço (R$)").reset_index(drop=True)
        else:
            df_filtrado = df_full[
                df_full["Categoria"].isin(cats_filtro)
            ].sort_values("Preço (R$)").reset_index(drop=True)

        col1, col2 = st.columns(2)
        col1.metric("Resultados encontrados", len(df_full))
        col2.metric("Resultados após filtros", len(df_filtrado))

        if df_filtrado.empty:
            st.warning("Nenhum resultado com os filtros aplicados. Ajuste os filtros na barra lateral.")
        else:
            df_analise = adicionar_variacao_oferta(df_filtrado)
            melhor = sugerir_melhor_oferta(df_filtrado)
            preco_min = float(df_analise["Preço (R$)"].min())
            preco_max = float(df_analise["Preço (R$)"].max())
            loja_mais_barata = df_analise.loc[df_analise["Preço (R$)"].idxmin(), "Loja"]
            economia = preco_max - preco_min

            m1, m2, m3 = st.columns(3)
            m1.metric("Menor preço", f"R$ {preco_min:,.2f}", loja_mais_barata)
            m2.metric("Maior preço", f"R$ {preco_max:,.2f}")
            m3.metric("Economia potencial", f"R$ {economia:,.2f}")

            if melhor is not None:
                st.subheader("Melhor opção sugerida")
                aval_txt = (
                    f"{melhor['Avaliação']:.1f} ★ ({int(melhor['Qtd. avaliações'])} avaliações)"
                    if pd.notna(melhor.get("Avaliação"))
                    else "sem avaliação"
                )
                st.success(
                    f"**{melhor['Produto']}** — {melhor['Loja']} — "
                    f"R$ {melhor['Preço (R$)']:,.2f} — {aval_txt}. "
                    f"Critério: maior avaliação entre as ofertas, depois menor preço."
                )
                if melhor.get("Link"):
                    st.link_button("Ver oferta", melhor["Link"])

            def highlight_lowest_price(row):
                if row.name == 0:
                    return ["background-color: rgba(40, 167, 69, 0.3); font-weight: bold"] * len(row)
                return [""] * len(row)

            colunas_exibir = [
                "Produto",
                "Loja",
                "Preço (R$)",
                "Δ vs menor (R$)",
                "Δ vs menor (%)",
            ]
            if df_analise["Avaliação"].notna().any():
                colunas_exibir.insert(3, "Avaliação")
                colunas_exibir.insert(4, "Qtd. avaliações")

            format_map = {
                "Preço (R$)": "R$ {:,.2f}",
                "Δ vs menor (R$)": "R$ {:,.2f}",
                "Δ vs menor (%)": "{:.1f}%",
                "Avaliação": "{:.1f}",
                "Qtd. avaliações": "{:.0f}",
            }
            styled_df = (
                df_analise[colunas_exibir]
                .style.apply(highlight_lowest_price, axis=1)
                .format({k: v for k, v in format_map.items() if k in colunas_exibir})
            )

            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Comparação de preços por oferta")
            df_grafico = df_analise.copy()
            df_grafico["label"] = df_grafico.apply(
                lambda r: (
                    (r["Produto"][:LABEL_MAX_CHARS] + "…" if len(r["Produto"]) > LABEL_MAX_CHARS else r["Produto"])
                    + " — "
                    + r["Loja"]
                ),
                axis=1,
            )
            if len(df_grafico) > MAX_OFERTAS_GRAFICO:
                st.caption(
                    f"Exibindo as {MAX_OFERTAS_GRAFICO} ofertas mais baratas "
                    f"de {len(df_grafico)} no total."
                )
                df_grafico = df_grafico.head(MAX_OFERTAS_GRAFICO)
            st.bar_chart(
                df_grafico,
                x="label",
                y="Preço (R$)",
                color="Loja",
            )

            st.subheader("Análise avançada")
            col_a, col_b = st.columns(2)
            fig_avaliacao = grafico_avaliacao_preco(df_analise)
            with col_a:
                if fig_avaliacao:
                    st.plotly_chart(fig_avaliacao, use_container_width=True)
                else:
                    st.info("Sem dados de avaliação para exibir o gráfico.")
            fig_box = grafico_boxplot_precos(df_analise)
            with col_b:
                if fig_box:
                    st.plotly_chart(fig_box, use_container_width=True)

            st.subheader("Comparação por loja")
            df_lojas = variacao_entre_lojas(resumo_por_loja(df_filtrado))
            st.dataframe(
                df_lojas.style.format({
                    "Preço mín. (R$)": "R$ {:,.2f}",
                    "Preço máx. (R$)": "R$ {:,.2f}",
                    "Preço médio (R$)": "R$ {:,.2f}",
                    "Ofertas": "{:.0f}",
                    "Δ vs melhor loja (R$)": "R$ {:,.2f}",
                    "Δ vs melhor loja (%)": "{:.1f}%",
                }),
                use_container_width=True,
                hide_index=True,
            )
elif not search_term:
    st.info("Digite um produto no campo acima ou selecione uma categoria na barra lateral para começar.")