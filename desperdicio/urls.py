from django.contrib.auth import views as auth
from django.urls import path

from . import views

urlpatterns = [
    path("entrar/", auth.LoginView.as_view(), name="login"),
    path("sair/", auth.LogoutView.as_view(), name="logout"),
    path("", views.menu, name="menu"),
    path("perdas/nova/", views.perda_nova, name="perda_nova"),
    path("compras/nova/", views.compra_nova, name="compra_nova"),
    path("ingredientes/novo/", views.ingrediente_novo, name="ingrediente_novo"),
    path("receitas/", views.receitas, name="receitas"),
    path("receitas/nova/", views.receita_nova, name="receita_nova"),
    path("caixa/", views.caixa, name="caixa"),
    path("resumo/", views.resumo, name="resumo"),
]
