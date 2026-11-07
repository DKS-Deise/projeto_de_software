from django.contrib import admin

from .models import Compra, Ingrediente, ItemReceita, Lancamento, Perda, Receita

for modelo in (Ingrediente, Compra, Receita, ItemReceita, Perda, Lancamento):
    admin.site.register(modelo)
