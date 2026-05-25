import streamlit as st
import pandas as pd
from scraper import search_all, _CATEGORIA_MAP

st.set_page_config(page_title="Pricefy", layout="wide")

st.title("Pricefy")
st.write("Compare preços de produtos entre lojas online.")

TODAS_CATEGORIAS = list(_CATEGORIA_MAP.keys()) + ["Outros"]

CATEGORY_SEARCH_TERMS = {
    "Informática":          "computador notebook",
    "Eletrônicos":          "televisor câmera som",
    "Celulares & Tablets":  "smartphone celular",
    "Eletrodomésticos":     "geladeira microondas fogão",
    "Móveis & Decoração":   "sofá cadeira mesa",
    "Roupas & Moda":        "camiseta calçado roupa",
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
    cache_key = search_term.strip().lower()
    if st.session_state.get("last_search_key") != cache_key:
        with st.spinner("Buscando preços nas lojas..."):
            results = search_all(search_term)
        if results:
            df = pd.DataFrame(results)
            df = df[df["Preço (R$)"] > 0].reset_index(drop=True)
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
        if categorias_selecionadas and not busca_por_categoria:
            cats_filtro = categorias_selecionadas
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
            def highlight_lowest_price(row):
                if row.name == 0:
                    return ["background-color: rgba(40, 167, 69, 0.3); font-weight: bold"] * len(row)
                return [""] * len(row)

            colunas_exibir = ["Produto", "Loja", "Preço (R$)"]
            styled_df = (
                df_filtrado[colunas_exibir]
                .style.apply(highlight_lowest_price, axis=1)
                .format({"Preço (R$)": "R$ {:,.2f}"})
            )

            st.dataframe(
                styled_df,
                use_container_width=True,
                hide_index=True,
            )
elif not search_term:
    st.info("Digite um produto no campo acima ou selecione uma categoria na barra lateral para começar.")