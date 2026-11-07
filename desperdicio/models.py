"""Camada de dados e regras de domínio: seis entidades do MVP."""
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

CENTAVO = Decimal("0.01")
MAIOR_QUE_ZERO = MinValueValidator(Decimal("0.001"), "Informe um valor maior que zero.")


def nao_futura(data):
    if data > timezone.localdate():
        raise ValidationError("A data não pode ser futura.")


class Ingrediente(models.Model):
    UNIDADES = [("kg", "kg"), ("g", "g"), ("l", "l"), ("ml", "ml"), ("un", "unidade")]
    nome = models.CharField(max_length=80, unique=True)
    unidade = models.CharField(max_length=2, choices=UNIDADES)
    preco_atual = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"),
                                      validators=[MinValueValidator(Decimal("0"))])

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.unidade})"


class Compra(models.Model):
    data = models.DateField(validators=[nao_futura])
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.PROTECT, related_name="compras")
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, validators=[MAIOR_QUE_ZERO])
    valor_total = models.DecimalField(max_digits=10, decimal_places=2,
                                      validators=[MinValueValidator(Decimal("0.01"), "Informe um valor maior que zero.")])

    class Meta:
        ordering = ["-data", "-id"]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Regra: o preço atual do ingrediente passa a ser o da última compra informada.
        self.ingrediente.preco_atual = (self.valor_total / self.quantidade).quantize(CENTAVO, ROUND_HALF_UP)
        self.ingrediente.save(update_fields=["preco_atual"])


class Receita(models.Model):
    nome = models.CharField(max_length=80, unique=True)
    rendimento = models.DecimalField(max_digits=10, decimal_places=2, validators=[MAIOR_QUE_ZERO])
    unidade_rendimento = models.CharField(max_length=7, choices=[("kg", "kg"), ("unidade", "unidade")])

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def custo(self):
        """Custo calculado na consulta (não é armazenado): soma de quantidade × preço atual."""
        total = sum((i.quantidade * i.ingrediente.preco_atual for i in self.itens.select_related("ingrediente")),
                    Decimal("0"))
        return total.quantize(CENTAVO, ROUND_HALF_UP)


class ItemReceita(models.Model):
    receita = models.ForeignKey(Receita, on_delete=models.CASCADE, related_name="itens")
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.PROTECT, related_name="itens_receita")
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, validators=[MAIOR_QUE_ZERO])

    class Meta:
        constraints = [models.UniqueConstraint(fields=["receita", "ingrediente"], name="item_unico_por_receita")]


class Perda(models.Model):
    MOTIVOS = [("preparo", "Preparo que não deu certo"), ("validade", "Validade vencida"),
               ("acidente", "Acidente"), ("outro", "Outro")]
    data = models.DateField(validators=[nao_futura])
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.PROTECT, related_name="perdas")
    quantidade = models.DecimalField(max_digits=10, decimal_places=3, validators=[MAIOR_QUE_ZERO])
    motivo = models.CharField(max_length=10, choices=MOTIVOS)
    observacao = models.CharField(max_length=200, blank=True)
    valor_perdido = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"), editable=False)

    class Meta:
        ordering = ["-data", "-id"]

    def save(self, *args, **kwargs):
        if self._state.adding:
            # O valor é gravado no registro, para o histórico não mudar quando o preço variar.
            self.valor_perdido = (self.quantidade * self.ingrediente.preco_atual).quantize(CENTAVO, ROUND_HALF_UP)
        super().save(*args, **kwargs)


class Lancamento(models.Model):
    TIPOS = [("entrada", "Entrada (venda)"), ("saida", "Saída (gasto)")]
    data = models.DateField(validators=[nao_futura])
    tipo = models.CharField(max_length=7, choices=TIPOS)
    descricao = models.CharField(max_length=120)
    valor = models.DecimalField(max_digits=10, decimal_places=2,
                                validators=[MinValueValidator(Decimal("0.01"), "Informe um valor maior que zero.")])
    receita = models.ForeignKey(Receita, null=True, blank=True, on_delete=models.SET_NULL, related_name="lancamentos")

    class Meta:
        ordering = ["-data", "-id"]

    def clean(self):
        if self.receita_id and self.tipo != "entrada":
            raise ValidationError("Só vendas (entradas) podem ser ligadas a uma receita.")
