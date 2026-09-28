"""Consultas determinísticas sobre a base já preparada por utils.py."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import re

import pandas as pd

from gastos import aplicar_filtros
from utils import normalizar_texto


CAMPOS_PUBLICOS = (
    "nome", "risco", "categoria", "rentabilidade",
    "rentabilidade_historica_12m", "tributacao", "indicado_para",
)


def filtrar_investimentos(
    transacoes: pd.DataFrame,
    mes: int | None = None,
    ano: int | None = None,
) -> pd.DataFrame:
    """Seleciona aportes (saídas), reutilizando os filtros já validados."""
    return aplicar_filtros(transacoes, escopo="investimentos", mes=mes, ano=ano)


def aportes_realizados(
    transacoes: pd.DataFrame,
    mes: int | None = None,
    ano: int | None = None,
) -> dict:
    """Agrupa pela descrição normalizada; total aportado não é saldo atual.

    Preserva a descrição original, sem inferir vínculo com um produto do
    catálogo. Aportes sem descrição continuam incluídos no total.
    """
    dados = filtrar_investimentos(transacoes, mes=mes, ano=ano)
    aportes = []
    for _, grupo in dados.groupby("descricao_chave", sort=True):
        descricoes = grupo["descricao"].dropna()
        descricao = next((str(d) for d in descricoes if str(d).strip()), None)
        aportes.append({
            "descricao": descricao,
            "quantidade": len(grupo),
            "total_aportado": round(float(grupo["valor"].sum()), 2),
        })
    return {
        "encontrado": not dados.empty,
        "mes": mes,
        "ano": ano,
        "quantidade": len(dados),
        "total_aportado": round(float(dados["valor"].sum()), 2),
        "aportes": aportes,
    }


def _produto_publico(produto: dict) -> dict:
    return {campo: produto.get(campo) for campo in CAMPOS_PUBLICOS}


def produtos_compativeis(produtos: list[dict], perfil: dict) -> list[dict]:
    """Compatibilidade cadastral, sem recomendação de compra.

    Renda variável explícita exige aceitação afirmativa. Multimercado não é
    reclassificado como renda variável a partir do nome ou do risco.
    """
    classificacao = normalizar_texto(perfil.get("classificacao"))
    if not classificacao:
        return []
    compativeis = []
    for produto in produtos:
        elegiveis = produto.get("elegivel_perfil") or []
        if not isinstance(elegiveis, list):
            continue
        if classificacao not in {normalizar_texto(p) for p in elegiveis}:
            continue
        categoria = normalizar_texto(produto.get("categoria"))
        if "renda variavel" in categoria and perfil.get("aceita_risco_variavel") is not True:
            continue
        compativeis.append(_produto_publico(produto))
    return compativeis


def encontrar_produto(produtos: list[dict], nome: str) -> dict | None:
    """Busca nome canônico completo, ignorando acentos e caixa.

    Não escolhe por aproximação nem resolve nomes duplicados arbitrariamente.
    O retorno contém apenas os campos permitidos à Lia.
    """
    chave = normalizar_texto(nome)
    if not chave:
        return None
    encontrados = [p for p in produtos if normalizar_texto(p.get("nome")) == chave]
    if len(encontrados) > 1:
        raise ValueError("Nome de produto ambíguo na base.")
    return _produto_publico(encontrados[0]) if encontrados else None


def extrair_percentual(valor: str | None) -> float | None:
    """Aceita somente percentual isolado (13,4% -> 13.4).

    Não extrai 100 de '100% da Selic', nem atribui unidade a número sem %.
    """
    if not isinstance(valor, str):
        return None
    if not re.fullmatch(r"[+-]?[0-9]+(?:[.,][0-9]+)?\s*%", valor.strip()):
        return None
    percentual = Decimal(valor.strip().removesuffix("%").strip().replace(",", "."))
    convertido = float(percentual)
    return convertido if Decimal(str(convertido)).is_finite() else None


def simular_rentabilidade(
    produto: dict | None,
    valor_inicial: float,
    meses: int = 12,
) -> dict:
    """Cenário de 12 meses aplicando uma única vez a taxa histórica de 12m.

    O capital é informado explicitamente; não presume que aportes ocorreram
    juntos. Não extrapola prazos, calcula impostos/taxas ou consulta índices.
    Dados insuficientes retornam simulacao_possivel=False, sem valor simulado.
    """
    if isinstance(valor_inicial, bool) or not isinstance(valor_inicial, (int, float, Decimal)):
        raise ValueError("O valor inicial deve ser um número finito e positivo.")
    capital = Decimal(str(valor_inicial))
    if not capital.is_finite() or capital <= 0:
        raise ValueError("O valor inicial deve ser um número finito e positivo.")
    if isinstance(meses, bool) or not isinstance(meses, int) or meses <= 0:
        raise ValueError("O prazo deve ser um número inteiro positivo de meses.")

    resultado = {"simulacao_possivel": False, "produto": None, "meses": meses}
    if produto is None:
        return {**resultado, "motivo": "Produto não encontrado na base."}
    resultado["produto"] = produto.get("nome")
    if meses != 12:
        return {**resultado, "motivo": "A simulação histórica disponível exige prazo de 12 meses."}
    taxa = extrair_percentual(produto.get("rentabilidade_historica_12m"))
    if taxa is None or taxa < -100:
        return {
            **resultado,
            "rentabilidade": produto.get("rentabilidade"),
            "motivo": (
                "A base não contém uma taxa histórica de 12 meses válida para simular. "
                "Expressões vinculadas à Selic ou ao CDI não fornecem o valor numérico "
                "do índice; não é possível calcular rendimento em reais com esses dados."
            ),
        }

    centavo = Decimal("0.01")
    capital = capital.quantize(centavo, rounding=ROUND_HALF_UP)
    if capital <= 0:
        raise ValueError("O valor inicial deve ser de pelo menos um centavo.")
    rendimento = (capital * Decimal(str(taxa)) / 100).quantize(centavo, rounding=ROUND_HALF_UP)
    return {
        **resultado,
        "simulacao_possivel": True,
        "metodo": "rentabilidade_historica_12m",
        "taxa_percentual": taxa,
        "valor_inicial": float(capital),
        "rendimento_simulado": float(rendimento),
        "valor_final_simulado": float(capital + rendimento),
        "aviso": (
            "Simulação baseada na rentabilidade histórica dos últimos 12 meses. "
            "Rentabilidade passada não garante rentabilidade futura. "
            "Sem cálculo adicional de impostos e taxas; não representa valor líquido de resgate."
        ),
    }
