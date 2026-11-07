"""Validação no servidor (RNF02): tipos, limites e listas fechadas vêm dos formulários do Django."""
from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone

from .models import Compra, Ingrediente, ItemReceita, Lancamento, Perda, Receita

DATA = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")


class BaseForm:
    """Aplica estilo, teclado numérico e data de hoje como padrão."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            w = campo.widget
            w.attrs["class"] = "form-select" if isinstance(w, forms.Select) else "form-control"
            if isinstance(campo, forms.DecimalField):
                w.attrs["inputmode"] = "decimal"
        if "data" in self.fields and not self.is_bound:
            self.fields["data"].initial = timezone.localdate()


class IngredienteForm(BaseForm, forms.ModelForm):
    class Meta:
        model = Ingrediente
        fields = ["nome", "unidade"]


class CompraForm(BaseForm, forms.ModelForm):
    class Meta:
        model = Compra
        fields = ["ingrediente", "quantidade", "valor_total", "data"]
        widgets = {"data": DATA}
        localized_fields = ["quantidade", "valor_total"]


class PerdaForm(BaseForm, forms.ModelForm):
    class Meta:
        model = Perda
        fields = ["ingrediente", "quantidade", "motivo", "data", "observacao"]
        widgets = {"data": DATA}
        localized_fields = ["quantidade"]
        labels = {"quantidade": "Quantidade perdida", "observacao": "Observação (opcional)"}


class ReceitaForm(BaseForm, forms.ModelForm):
    class Meta:
        model = Receita
        fields = ["nome", "rendimento", "unidade_rendimento"]
        localized_fields = ["rendimento"]


class ItemReceitaForm(BaseForm, forms.ModelForm):
    class Meta:
        model = ItemReceita
        fields = ["ingrediente", "quantidade"]
        localized_fields = ["quantidade"]


ItensFormSet = inlineformset_factory(Receita, ItemReceita, form=ItemReceitaForm, extra=4, can_delete=False)


class LancamentoForm(BaseForm, forms.ModelForm):
    class Meta:
        model = Lancamento
        fields = ["tipo", "descricao", "valor", "data", "receita"]
        widgets = {"data": DATA}
        localized_fields = ["valor"]
