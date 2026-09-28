# script/gastos.py

from __future__ import annotations

import pandas as pd

from utils import normalizar_texto


# ============================================================
# ESCOPOS VÁLIDOS
# ============================================================

ESCOPOS_VALIDOS = {
    "gastos",
    "investimentos",
    "saidas",
}

OPERACOES_VALIDAS = {
    "total",
    "media",
}


# ============================================================
# SEPARAÇÃO DOS ESCOPOS
# ============================================================

def filtrar_escopo(
    transacoes: pd.DataFrame,
    escopo: str = "gastos",
) -> pd.DataFrame:
    """
    Separa as saídas financeiras conforme o significado definido
    no projeto.

    gastos:
        despesas cotidianas, excluindo investimentos.

    investimentos:
        somente aportes classificados como Investimento.

    saidas:
        tudo que saiu da conta, incluindo investimentos.
    """

    escopo = normalizar_texto(escopo)

    if escopo not in ESCOPOS_VALIDOS:
        raise ValueError(
            f"Escopo inválido: {escopo}. "
            f"Use um de: {sorted(ESCOPOS_VALIDOS)}"
        )

    saidas = transacoes[
        transacoes["tipo_chave"] == "saida"
    ].copy()

    if escopo == "gastos":
        return saidas[
            saidas["categoria_chave"] != "investimento"
        ].copy()

    if escopo == "investimentos":
        return saidas[
            saidas["categoria_chave"] == "investimento"
        ].copy()

    return saidas


# ============================================================
# CATEGORIAS DISPONÍVEIS
# ============================================================

def categorias_disponiveis(
    transacoes: pd.DataFrame,
    escopo: str = "gastos",
) -> list[str]:
    """
    Retorna os nomes reais das categorias existentes na base.
    """

    dados = filtrar_escopo(
        transacoes,
        escopo=escopo,
    )

    return sorted(
        dados["categoria"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )


# ============================================================
# FILTROS
# ============================================================

def aplicar_filtros(
    transacoes: pd.DataFrame,
    escopo: str = "gastos",
    categoria: str | None = None,
    mes: int | None = None,
    ano: int | None = None,
) -> pd.DataFrame:
    """
    Aplica os parâmetros já interpretados pela Lia.

    A Lia pode interpretar "comida" como "Alimentacao".
    Aqui trabalhamos apenas com a categoria canônica recebida.
    """

    dados = filtrar_escopo(
        transacoes,
        escopo=escopo,
    )

    # --------------------------------------------------------
    # Categoria
    # --------------------------------------------------------

    if categoria is not None:

        categoria_chave = normalizar_texto(
            categoria
        )

        categorias_validas = set(
            dados["categoria_chave"]
        )

        if categoria_chave not in categorias_validas:
            raise ValueError(
                f"Categoria não encontrada: {categoria}"
            )

        dados = dados[
            dados["categoria_chave"]
            == categoria_chave
        ]

    # --------------------------------------------------------
    # Ano
    # --------------------------------------------------------

    if ano is not None:
        dados = dados[
            dados["data"].dt.year == int(ano)
        ]

    # --------------------------------------------------------
    # Mês
    # --------------------------------------------------------

    if mes is not None:

        mes = int(mes)

        if mes < 1 or mes > 12:
            raise ValueError(
                "O mês deve estar entre 1 e 12."
            )

        dados = dados[
            dados["data"].dt.month == mes
        ]

    return dados.copy()


# ============================================================
# CONSULTA PRINCIPAL
# ============================================================

def consultar_gastos(
    transacoes: pd.DataFrame,
    operacao: str = "total",
    escopo: str = "gastos",
    categoria: str | None = None,
    mes: int | None = None,
    ano: int | None = None,
) -> dict:
    """
    Executa uma consulta determinística sobre as transações.

    Exemplo:

        consultar_gastos(
            transacoes,
            operacao="total",
            escopo="gastos",
            categoria="Alimentacao",
            mes=7,
            ano=2026,
        )
    """

    operacao = normalizar_texto(
        operacao
    )

    if operacao not in OPERACOES_VALIDAS:
        raise ValueError(
            f"Operação inválida: {operacao}. "
            f"Use um de: {sorted(OPERACOES_VALIDAS)}"
        )

    dados = aplicar_filtros(
        transacoes=transacoes,
        escopo=escopo,
        categoria=categoria,
        mes=mes,
        ano=ano,
    )

    quantidade = len(dados)

    if quantidade == 0:
        return {
            "encontrado": False,
            "operacao": operacao,
            "escopo": escopo,
            "categoria": categoria,
            "mes": mes,
            "ano": ano,
            "quantidade": 0,
            "valor": 0.0,
        }

    if operacao == "total":
        valor = dados["valor"].sum()

    else:
        valor = dados["valor"].mean()

    return {
        "encontrado": True,
        "operacao": operacao,
        "escopo": escopo,
        "categoria": categoria,
        "mes": mes,
        "ano": ano,
        "quantidade": quantidade,
        "valor": round(float(valor), 2),
    }


# ============================================================
# OPERAÇÕES SEMÂNTICAS DE GASTOS
# ============================================================

def consultar_total_gastos(
    transacoes: pd.DataFrame,
    categoria: str | None = None,
    mes: int | None = None,
    ano: int | None = None,
) -> dict:
    """Retorna somente o valor agregado dos gastos filtrados."""

    dados = aplicar_filtros(
        transacoes,
        escopo="gastos",
        categoria=categoria,
        mes=mes,
        ano=ano,
    )
    return {
        "encontrado": not dados.empty,
        "categoria": categoria,
        "mes": mes,
        "ano": ano,
        "valor": round(float(dados["valor"].sum()), 2),
    }


def listar_gastos(
    transacoes: pd.DataFrame,
    categoria: str | None = None,
    mes: int | None = None,
    ano: int | None = None,
    limite: int = 10,
    ordem: str = "recentes",
) -> dict:
    """Retorna transações individuais, limitadas e ordenadas por data."""

    if type(limite) is not int or limite < 1 or limite > 100:
        raise ValueError("O limite deve ser um inteiro entre 1 e 100.")
    ordem = normalizar_texto(ordem)
    if ordem not in {"recentes", "antigos"}:
        raise ValueError("A ordem deve ser 'recentes' ou 'antigos'.")

    dados = aplicar_filtros(
        transacoes,
        escopo="gastos",
        categoria=categoria,
        mes=mes,
        ano=ano,
    ).sort_values("data", ascending=ordem == "antigos")
    dados = dados.head(limite)
    itens = [
        {
            "data": linha.data.date().isoformat(),
            "descricao": None if pd.isna(linha.descricao) else str(linha.descricao),
            "categoria": str(linha.categoria),
            "valor": round(float(linha.valor), 2),
        }
        for linha in dados.itertuples(index=False)
    ]
    return {
        "encontrado": bool(itens),
        "categoria": categoria,
        "mes": mes,
        "ano": ano,
        "limite": limite,
        "ordem": ordem,
        "transacoes": itens,
    }


def resumo_gastos_por_categoria(
    transacoes: pd.DataFrame,
    mes: int | None = None,
    ano: int | None = None,
) -> dict:
    """Retorna a soma de gastos separada por categoria."""

    categorias = resumo_por_categoria(transacoes, mes=mes, ano=ano)
    return {
        "encontrado": bool(categorias),
        "mes": mes,
        "ano": ano,
        "categorias": categorias,
    }


def contar_transacoes_gastos(
    transacoes: pd.DataFrame,
    categoria: str | None = None,
    mes: int | None = None,
    ano: int | None = None,
) -> dict:
    """Retorna somente a quantidade de transações de gastos filtradas."""

    dados = aplicar_filtros(
        transacoes,
        escopo="gastos",
        categoria=categoria,
        mes=mes,
        ano=ano,
    )
    return {
        "encontrado": not dados.empty,
        "categoria": categoria,
        "mes": mes,
        "ano": ano,
        "quantidade": len(dados),
    }


# ============================================================
# RESUMO POR CATEGORIA
# ============================================================

def resumo_por_categoria(
    transacoes: pd.DataFrame,
    mes: int | None = None,
    ano: int | None = None,
) -> dict[str, float]:
    """
    Soma os gastos cotidianos por categoria.

    Investimentos são excluídos automaticamente.
    """

    dados = aplicar_filtros(
        transacoes,
        escopo="gastos",
        mes=mes,
        ano=ano,
    )

    resumo = (
        dados
        .groupby("categoria")["valor"]
        .sum()
        .sort_values(ascending=False)
    )

    return {
        categoria: round(float(valor), 2)
        for categoria, valor
        in resumo.items()
    }


# ============================================================
# PREVISÃO SIMPLES DE GASTOS
# ============================================================

def estimar_gastos_proximo_mes(
    transacoes: pd.DataFrame,
) -> dict:
    """
    Estima os gastos do próximo mês usando a média mensal
    histórica dos gastos cotidianos.

    Meses sem gastos em determinada categoria contam como zero.

    Investimentos não entram na estimativa.
    """

    dados = filtrar_escopo(
        transacoes,
        escopo="gastos",
    ).copy()

    if dados.empty:
        return {
            "encontrado": False,
            "total_estimado": 0.0,
            "categorias": {},
        }

    dados["mes_referencia"] = (
        dados["data"]
        .dt.to_period("M")
    )

    # Todos os meses existentes no período analisado.
    meses = pd.period_range(
        start=dados["mes_referencia"].min(),
        end=dados["mes_referencia"].max(),
        freq="M",
    )

    # Soma mensal por categoria.
    tabela_mensal = (
        dados
        .groupby(
            [
                "mes_referencia",
                "categoria",
            ]
        )["valor"]
        .sum()
        .unstack(fill_value=0)
    )

    # Garante que todos os meses do período participem.
    tabela_mensal = tabela_mensal.reindex(
        meses,
        fill_value=0,
    )

    # Média mensal real de cada categoria.
    medias = (
        tabela_mensal
        .mean()
        .sort_values(ascending=False)
    )

    categorias = {
        categoria: round(float(valor), 2)
        for categoria, valor
        in medias.items()
    }

    total_estimado = round(
        sum(categorias.values()),
        2,
    )

    return {
        "encontrado": True,
        "metodo": "media_mensal_historica",
        "total_estimado": total_estimado,
        "categorias": categorias,
    }
