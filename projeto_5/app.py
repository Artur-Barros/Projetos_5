import streamlit as st
import pandas as pd
from scraper import search_all

st.set_page_config(page_title="Pricefy", layout="wide")

st.title("Pricefy")
st.write("Compare preços de produtos entre lojas online.")

query = st.text_input("Buscar produto:", placeholder="Ex: notebook, mouse gamer, teclado mecânico...")

if query:
    with st.spinner("Buscando preços nas lojas..."):
        results = search_all(query)

    if results:
        df = pd.DataFrame(results)
        df = df.sort_values("Preço (R$)").reset_index(drop=True)

        def highlight_lowest_price(row):
            if row.name == 0:
                return ['background-color: rgba(40, 167, 69, 0.3); font-weight: bold'] * len(row)
            return [''] * len(row)

        styled_df = df[["Produto", "Loja", "Preço (R$)"]].style.apply(highlight_lowest_price, axis=1).format({"Preço (R$)": "R$ {:,.2f}"})

        st.success(f"{len(results)} resultado(s) encontrado(s).")
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Nenhum resultado encontrado. Tente outro termo.")
