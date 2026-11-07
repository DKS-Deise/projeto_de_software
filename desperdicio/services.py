"""Camada de regras de negócio: cálculos do resumo mensal e do caixa."""
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Count, Sum

from .models import Compra, Lancamento, Perda

ZERO = Decimal("0")


def _soma(qs, campo):
    return qs.aggregate(t=Sum(campo))["t"] or ZERO


def taxa_desperdicio(ano, mes):
    """Perdas ÷ compras do mês × 100. Sem compras no mês, devolve None ("sem dados")."""
    compras = _soma(Compra.objects.filter(data__year=ano, data__month=mes), "valor_total")
    perdido = _soma(Perda.objects.filter(data__year=ano, data__month=mes), "valor_perdido")
    if compras <= 0:
        return None
    return (perdido / compras * 100).quantize(Decimal("0.1"), ROUND_HALF_UP)


def resumo_mensal(ano, mes):
    compras = _soma(Compra.objects.filter(data__year=ano, data__month=mes), "valor_total")
    perdas = Perda.objects.filter(data__year=ano, data__month=mes)
    topo = perdas.values("motivo").annotate(n=Count("id")).order_by("-n", "motivo").first()
    ano_ant, mes_ant = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    taxa, taxa_ant = taxa_desperdicio(ano, mes), taxa_desperdicio(ano_ant, mes_ant)
    return {
        "total_comprado": compras,
        "total_perdido": _soma(perdas, "valor_perdido"),
        "taxa": taxa,
        "taxa_anterior": taxa_ant,
        "variacao": (taxa - taxa_ant) if taxa is not None and taxa_ant is not None else None,
        "motivo_frequente": dict(Perda.MOTIVOS)[topo["motivo"]] if topo else None,
        "ultimas": perdas.select_related("ingrediente")[:5],
    }


def saldo_caixa(ano, mes):
    qs = Lancamento.objects.filter(data__year=ano, data__month=mes)
    entradas = _soma(qs.filter(tipo="entrada"), "valor")
    saidas = _soma(qs.filter(tipo="saida"), "valor")
    return {"entradas": entradas, "saidas": saidas, "saldo": entradas - saidas}
