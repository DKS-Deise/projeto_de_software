"""Camada de apresentação: toda tela exige login (RNF01/RNF02)."""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from . import services
from .forms import CompraForm, IngredienteForm, ItensFormSet, LancamentoForm, PerdaForm, ReceitaForm
from .models import Lancamento, Receita


def _brl(valor):
    return f"{valor:.2f}".replace(".", ",")


def _periodo(request):
    """Lê ?mes=AAAA-MM; valores inválidos voltam ao mês atual."""
    hoje = timezone.localdate()
    try:
        ano, mes = (int(p) for p in request.GET.get("mes", "").split("-"))
        date(ano, mes, 1)
    except ValueError:
        ano, mes = hoje.year, hoje.month
    return ano, mes


def _cadastro(request, Form, titulo, destino, sucesso, **extra):
    form = Form(request.POST or None)
    if request.method == "POST" and form.is_valid():
        objeto = form.save()
        messages.success(request, sucesso(objeto))
        return redirect(destino)
    return render(request, "desperdicio/form.html", {"form": form, "titulo": titulo, **extra})


@login_required
def menu(request):
    return render(request, "desperdicio/menu.html")


@login_required
def perda_nova(request):
    return _cadastro(request, PerdaForm, "Registrar perda", "perda_nova",
                     lambda p: f"Perda registrada: R$ {_brl(p.valor_perdido)}", ver_resumo=True)


@login_required
def compra_nova(request):
    return _cadastro(request, CompraForm, "Registrar compra", "compra_nova",
                     lambda c: f"Compra registrada: {c.ingrediente.nome}, R$ {_brl(c.valor_total)}",
                     link_ingrediente=True)


@login_required
def ingrediente_novo(request):
    return _cadastro(request, IngredienteForm, "Cadastrar ingrediente", "compra_nova",
                     lambda i: f"Ingrediente cadastrado: {i.nome}. Agora registre a compra.")


@login_required
def receitas(request):
    return render(request, "desperdicio/receitas.html", {"receitas": Receita.objects.all()})


@login_required
def receita_nova(request):
    form = ReceitaForm(request.POST or None)
    formset = ItensFormSet(request.POST or None, instance=Receita())
    if request.method == "POST" and form.is_valid():
        receita = form.save(commit=False)
        formset = ItensFormSet(request.POST, instance=receita)
        if formset.is_valid():
            itens = [f.cleaned_data["ingrediente"].pk for f in formset.forms if f.has_changed()]
            if not itens:
                messages.error(request, "Adicione ao menos um ingrediente à receita.")
            elif len(itens) != len(set(itens)):
                messages.error(request, "Não repita o mesmo ingrediente na receita.")
            else:
                receita.save()
                formset.save()
                messages.success(request, f"Receita cadastrada: {receita.nome}. Custo: R$ {_brl(receita.custo)}")
                return redirect("receitas")
    return render(request, "desperdicio/form.html", {"form": form, "formset": formset, "titulo": "Cadastrar receita"})


@login_required
def caixa(request):
    ano, mes = _periodo(request)
    form = LancamentoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Lançamento registrado.")
        return redirect("caixa")
    contexto = {"form": form, "caixa": services.saldo_caixa(ano, mes), "mes": f"{ano}-{mes:02d}",
                "lancamentos": Lancamento.objects.filter(data__year=ano, data__month=mes)[:10]}
    return render(request, "desperdicio/caixa.html", contexto)


@login_required
def resumo(request):
    ano, mes = _periodo(request)
    return render(request, "desperdicio/resumo.html",
                  {"r": services.resumo_mensal(ano, mes), "mes": f"{ano}-{mes:02d}"})
