import pandas as pd
import plotly.express as px

COL_PRECO = "Preço (R$)"
COL_AVAL = "Avaliação"
LABEL_MAX = 35


def _label_oferta(df: pd.DataFrame) -> pd.Series:
    return df.apply(
        lambda r: (
            (r["Produto"][:LABEL_MAX] + "…" if len(r["Produto"]) > LABEL_MAX else r["Produto"])
            + " — "
            + r["Loja"]
        ),
        axis=1,
    )


def grafico_avaliacao_preco(df: pd.DataFrame):
    dados = df[df[COL_AVAL].notna()].copy()
    if dados.empty:
        return None
    dados["label"] = _label_oferta(dados)
    fig = px.scatter(
        dados,
        x=COL_PRECO,
        y=COL_AVAL,
        color="Loja",
        hover_name="label",
        labels={COL_PRECO: "Preço (R$)", COL_AVAL: "Avaliação"},
        title="Avaliação dos clientes vs preço",
    )
    fig.update_traces(marker={"size": 10, "opacity": 0.85})
    fig.update_layout(hovermode="closest")
    return fig


def grafico_boxplot_precos(df: pd.DataFrame):
    if df.empty:
        return None
    fig = px.box(
        df,
        x="Loja",
        y=COL_PRECO,
        color="Loja",
        points="outliers",
        labels={COL_PRECO: "Preço (R$)", "Loja": "Loja"},
        title="Variação de preços por loja",
    )
    fig.update_layout(showlegend=False)
    return fig
