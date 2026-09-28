from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


# ============================================================
# COLUNAS UTILIZADAS PELA APLICAÇÃO
# ============================================================

COLUNAS_TRANSACOES = [
    "data",
    "descricao",
    "categoria",
    "valor",
    "tipo",
]


# ============================================================
# NORMALIZAÇÃO DE TEXTO
# ============================================================

def normalizar_texto(valor: Any) -> str:
    """
    Cria uma versão padronizada de textos para comparações internas.

    Exemplos:
        "Alimentação" -> "alimentacao"
        " SAÍDA "     -> "saida"

    O valor original continua preservado no DataFrame.
    """

    if valor is None:
        return ""

    try:
        if pd.isna(valor):
            return ""
    except (TypeError, ValueError):
        pass

    texto = str(valor).strip().lower()

    texto = unicodedata.normalize("NFKD", texto)

    texto = "".join(
        caractere
        for caractere in texto
        if not unicodedata.combining(caractere)
    )

    return " ".join(texto.split())


# ============================================================
# CARREGAMENTO DOS ARQUIVOS
# ============================================================

def carregar_json(caminho: str | Path):
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def carregar_transacoes(caminho: str | Path) -> pd.DataFrame:
    return pd.read_csv(caminho)


# ============================================================
# VALIDAÇÃO
# ============================================================

def validar_colunas(
    df: pd.DataFrame,
    obrigatorias: list[str],
) -> None:

    faltando = [
        coluna
        for coluna in obrigatorias
        if coluna not in df.columns
    ]

    if faltando:
        raise ValueError(
            "A base de transações não possui as colunas obrigatórias: "
            + ", ".join(faltando)
        )


# ============================================================
# PREPARAÇÃO DAS TRANSAÇÕES
# ============================================================

def preparar_transacoes(
    transacoes: pd.DataFrame,
) -> pd.DataFrame:

    """
    Remove informações que a aplicação não utiliza e normaliza
    os campos necessários para gastos e investimentos.

    O DataFrame resultante contém:

        data
        descricao
        categoria
        valor
        tipo

        descricao_chave
        categoria_chave
        tipo_chave
    """

    validar_colunas(
        transacoes,
        COLUNAS_TRANSACOES,
    )

    # Mantém somente os campos relevantes para a aplicação.
    df = transacoes[
        COLUNAS_TRANSACOES
    ].copy()

    # --------------------------------------------------------
    # Datas
    # --------------------------------------------------------

    df["data"] = pd.to_datetime(
        df["data"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Valores monetários
    # --------------------------------------------------------

    df["valor"] = pd.to_numeric(
        df["valor"],
        errors="coerce",
    )

    # O sentido financeiro vem de "tipo".
    # O valor representa apenas a magnitude monetária.
    df["valor"] = df["valor"].abs()

    # --------------------------------------------------------
    # Textos
    # --------------------------------------------------------

    for coluna in [
        "descricao",
        "categoria",
        "tipo",
    ]:

        df[coluna] = (
            df[coluna]
            .astype("string")
            .str.strip()
        )

    # --------------------------------------------------------
    # Remove registros inutilizáveis
    # --------------------------------------------------------

    df = df.dropna(
        subset=[
            "data",
            "categoria",
            "valor",
            "tipo",
        ]
    ).copy()

    # --------------------------------------------------------
    # Chaves normalizadas
    #
    # São usadas apenas pelo Python.
    # A Lia não precisa vê-las.
    # --------------------------------------------------------

    df["descricao_chave"] = (
        df["descricao"]
        .map(normalizar_texto)
    )

    df["categoria_chave"] = (
        df["categoria"]
        .map(normalizar_texto)
    )

    df["tipo_chave"] = (
        df["tipo"]
        .map(normalizar_texto)
    )

    # Organização cronológica.
    df = (
        df
        .sort_values("data")
        .reset_index(drop=True)
    )

    return df


# ============================================================
# PREPARAÇÃO DO PERFIL
# ============================================================

def preparar_perfil(
    perfil: dict,
) -> dict:

    """
    Entrega somente as informações do cliente relevantes
    para as capacidades atuais da Lia.
    """

    perfil_investidor = perfil.get(
        "perfil_investidor",
        {},
    )

    return {
        "nome": perfil.get("nome"),

        "classificacao":
            perfil_investidor.get(
                "classificacao"
            ),

        "aceita_risco_variavel":
            perfil_investidor.get(
                "aceita_risco_variavel"
            ),
    }


# ============================================================
# PREPARAÇÃO DOS PRODUTOS FINANCEIROS
# ============================================================

def preparar_produtos(
    produtos: list[dict],
) -> list[dict]:

    """
    Remove campos que não serão utilizados pela Lia ou
    pelos cálculos do módulo de investimentos.

    Mantemos separadas:
        rentabilidade
        rentabilidade_historica_12m

    porque possuem significados diferentes.
    """

    produtos_limpos = []

    for produto in produtos:

        produto_limpo = {
            "nome":
                produto.get("nome"),

            "categoria":
                produto.get("categoria"),

            "risco":
                produto.get("risco"),

            "rentabilidade":
                produto.get("rentabilidade"),

            "rentabilidade_historica_12m":
                produto.get(
                    "rentabilidade_historica_12m"
                ),

            "tributacao":
                produto.get("tributacao"),

            "indicado_para":
                produto.get("indicado_para"),

            # Campo usado pelo Python para filtragem.
            # Não precisa ser apresentado ao cliente.
            "elegivel_perfil":
                produto.get(
                    "elegivel_perfil",
                    [],
                ),
        }

        produtos_limpos.append(
            produto_limpo
        )

    return produtos_limpos


# ============================================================
# CARREGAMENTO COMPLETO DA BASE
# ============================================================

def carregar_e_preparar_base(
    pasta_dados: str | Path,
):

    """
    Ponto único de entrada da base de dados.

    Os demais módulos não precisam saber como CSV/JSON
    são carregados ou limpos.
    """

    pasta_dados = Path(pasta_dados)

    transacoes_brutas = carregar_transacoes(
        pasta_dados / "transacoes.csv"
    )

    perfil_bruto = carregar_json(
        pasta_dados / "perfil_investidor.json"
    )

    produtos_brutos = carregar_json(
        pasta_dados / "produtos_financeiros.json"
    )

    transacoes = preparar_transacoes(
        transacoes_brutas
    )

    perfil = preparar_perfil(
        perfil_bruto
    )

    produtos = preparar_produtos(
        produtos_brutos
    )

    return (
        transacoes,
        perfil,
        produtos,
    )

if __name__ == "__main__":
    print(carregar_e_preparar_base(Path(__file__).resolve().parent / "dados"))
