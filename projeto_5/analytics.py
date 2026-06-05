import pandas as pd

COL_PRECO = "Preço (R$)"
COL_AVAL = "Avaliação"


def adicionar_variacao_oferta(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    out = df.copy()
    preco_min = out[COL_PRECO].min()
    if preco_min <= 0:
        out["Δ vs menor (R$)"] = 0.0
        out["Δ vs menor (%)"] = 0.0
        return out

    out["Δ vs menor (R$)"] = out[COL_PRECO] - preco_min
    out["Δ vs menor (%)"] = (out["Δ vs menor (R$)"] / preco_min) * 100
    return out


def resumo_por_loja(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["Loja", "Preço mín. (R$)", "Preço máx. (R$)", "Preço médio (R$)", "Ofertas"]
        )

    agg = (
        df.groupby("Loja")[COL_PRECO]
        .agg(
            **{
                "Preço mín. (R$)": "min",
                "Preço máx. (R$)": "max",
                "Preço médio (R$)": "mean",
                "Ofertas": "count",
            }
        )
        .reset_index()
    )
    return agg.sort_values("Preço mín. (R$)").reset_index(drop=True)


def variacao_entre_lojas(df_loja: pd.DataFrame) -> pd.DataFrame:
    if df_loja.empty:
        return df_loja.copy()

    out = df_loja.copy()
    preco_min = out["Preço mín. (R$)"].min()
    if preco_min <= 0:
        out["Δ vs melhor loja (R$)"] = 0.0
        out["Δ vs melhor loja (%)"] = 0.0
        return out

    out["Δ vs melhor loja (R$)"] = out["Preço mín. (R$)"] - preco_min
    out["Δ vs melhor loja (%)"] = (out["Δ vs melhor loja (R$)"] / preco_min) * 100
    return out


def sugerir_melhor_oferta(df: pd.DataFrame) -> pd.Series | None:
    if df.empty:
        return None

    com_avaliacao = df[df[COL_AVAL].notna()].copy()
    if com_avaliacao.empty:
        return df.loc[df[COL_PRECO].idxmin()]

    max_avaliacao = com_avaliacao[COL_AVAL].max()
    candidatos = com_avaliacao[com_avaliacao[COL_AVAL] == max_avaliacao]
    return candidatos.loc[candidatos[COL_PRECO].idxmin()]
