"""Testes das regras (RF01–RF05) e dos controles de segurança (RNF01/RNF02)."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.db.models import ProtectedError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from . import services
from .models import Compra, Ingrediente, ItemReceita, Lancamento, Perda, Receita


def hoje():
    return timezone.localdate()


class RegrasDeNegocio(TestCase):
    def setUp(self):
        self.morango = Ingrediente.objects.create(nome="Morango", unidade="kg")
        self.acucar = Ingrediente.objects.create(nome="Açúcar", unidade="kg")

    def test_compra_atualiza_preco_atual(self):  # RF01
        Compra.objects.create(data=hoje(), ingrediente=self.morango, quantidade=Decimal("2"), valor_total=Decimal("20"))
        self.morango.refresh_from_db()
        self.assertEqual(self.morango.preco_atual, Decimal("10.00"))

    def test_custo_da_receita(self):  # RF02
        Compra.objects.create(data=hoje(), ingrediente=self.morango, quantidade=Decimal("1"), valor_total=Decimal("10"))
        Compra.objects.create(data=hoje(), ingrediente=self.acucar, quantidade=Decimal("1"), valor_total=Decimal("5"))
        r = Receita.objects.create(nome="Morango do amor", rendimento=Decimal("1"), unidade_rendimento="kg")
        ItemReceita.objects.create(receita=r, ingrediente=self.morango, quantidade=Decimal("0.5"))
        ItemReceita.objects.create(receita=r, ingrediente=self.acucar, quantidade=Decimal("0.2"))
        self.assertEqual(r.custo, Decimal("6.00"))

    def test_perda_grava_valor_e_nao_muda_com_novo_preco(self):  # RF03
        Compra.objects.create(data=hoje(), ingrediente=self.morango, quantidade=Decimal("1"), valor_total=Decimal("10"))
        p = Perda.objects.create(data=hoje(), ingrediente=self.morango, quantidade=Decimal("0.5"), motivo="preparo")
        self.assertEqual(p.valor_perdido, Decimal("5.00"))
        Compra.objects.create(data=hoje(), ingrediente=self.morango, quantidade=Decimal("1"), valor_total=Decimal("20"))
        p.refresh_from_db()
        self.assertEqual(p.valor_perdido, Decimal("5.00"))

    def test_taxa_de_desperdicio_e_motivo(self):  # RF04
        Compra.objects.create(data=hoje(), ingrediente=self.morango, quantidade=Decimal("10"), valor_total=Decimal("100"))
        Perda.objects.create(data=hoje(), ingrediente=self.morango, quantidade=Decimal("0.5"), motivo="preparo")
        r = services.resumo_mensal(hoje().year, hoje().month)
        self.assertEqual(r["total_comprado"], Decimal("100.00"))
        self.assertEqual(r["total_perdido"], Decimal("5.00"))
        self.assertEqual(r["taxa"], Decimal("5.0"))
        self.assertEqual(r["motivo_frequente"], "Preparo que não deu certo")

    def test_sem_compras_taxa_sem_dados(self):  # RF04
        self.assertIsNone(services.resumo_mensal(hoje().year, hoje().month)["taxa"])

    def test_saldo_do_caixa(self):  # RF05
        Lancamento.objects.create(data=hoje(), tipo="entrada", descricao="Bolo", valor=Decimal("150"))
        Lancamento.objects.create(data=hoje(), tipo="saida", descricao="Gás", valor=Decimal("40"))
        self.assertEqual(services.saldo_caixa(hoje().year, hoje().month)["saldo"], Decimal("110"))

    def test_ingrediente_com_registros_nao_pode_ser_excluido(self):
        Compra.objects.create(data=hoje(), ingrediente=self.morango, quantidade=Decimal("1"), valor_total=Decimal("10"))
        with self.assertRaises(ProtectedError):
            self.morango.delete()


class Seguranca(TestCase):
    URLS = ["menu", "perda_nova", "compra_nova", "ingrediente_novo", "receitas", "receita_nova", "caixa", "resumo"]

    def setUp(self):
        self.user = User.objects.create_user("carina_teste", password="Senha-de-Teste-123")
        self.morango = Ingrediente.objects.create(nome="Morango", unidade="kg", preco_atual=Decimal("10"))

    def test_telas_exigem_login(self):  # RNF01/RNF02
        for nome in self.URLS:
            resp = self.client.get(reverse(nome))
            self.assertEqual(resp.status_code, 302, nome)
            self.assertIn(reverse("login"), resp["Location"], nome)

    def test_health_check_publica_confirma_aplicacao_e_banco(self):
        resp = self.client.get(reverse("health_check"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b"ok")

    def test_menu_exibe_controles_acessiveis_de_tamanho_do_texto(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("menu"))
        self.assertContains(resp, 'aria-label="Aumentar tamanho do texto"')
        self.assertContains(resp, 'aria-live="polite"')
        self.assertContains(resp, "data-ajuste-fonte")

    def test_login_valido_e_invalido(self):  # RNF01
        ruim = self.client.post(reverse("login"), {"username": "carina_teste", "password": "errada"})
        self.assertContains(ruim, "Usuário ou senha incorretos")
        self.assertTrue(self.client.login(username="carina_teste", password="Senha-de-Teste-123"))

    def test_senha_guardada_com_hash_pbkdf2(self):  # RNF01
        self.assertTrue(self.user.password.startswith("pbkdf2_sha256$"))
        self.assertNotIn("Senha-de-Teste-123", self.user.password)

    def test_sair_encerra_a_sessao(self):  # RNF01
        self.client.force_login(self.user)
        self.client.post(reverse("logout"))
        self.assertEqual(self.client.get(reverse("menu")).status_code, 302)

    def test_formulario_sem_csrf_e_recusado(self):  # RNF02
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.user)
        resp = cliente.post(reverse("perda_nova"), {"ingrediente": self.morango.pk, "quantidade": "1"})
        self.assertEqual(resp.status_code, 403)

    def test_quantidade_zero_e_rejeitada_no_servidor(self):  # RNF02 / RF03
        self.client.force_login(self.user)
        resp = self.client.post(reverse("perda_nova"), {"ingrediente": self.morango.pk, "quantidade": "0",
                                                         "motivo": "preparo", "data": hoje().isoformat()})
        self.assertContains(resp, "maior que zero")
        self.assertEqual(Perda.objects.count(), 0)

    def test_virgula_decimal_e_aceita_e_valor_e_calculado(self):  # RF03
        self.client.force_login(self.user)
        resp = self.client.post(reverse("perda_nova"), {"ingrediente": self.morango.pk, "quantidade": "0,5",
                                                         "motivo": "preparo", "data": hoje().isoformat()}, follow=True)
        self.assertContains(resp, "Perda registrada: R$ 5,00")

    def test_motivo_fora_da_lista_e_rejeitado(self):  # RNF02
        self.client.force_login(self.user)
        self.client.post(reverse("perda_nova"), {"ingrediente": self.morango.pk, "quantidade": "1",
                                                  "motivo": "invalido", "data": hoje().isoformat()})
        self.assertEqual(Perda.objects.count(), 0)

    def test_script_digitado_aparece_como_texto(self):  # RNF02 (XSS)
        self.client.force_login(self.user)
        Perda.objects.create(data=hoje(), ingrediente=self.morango, quantidade=Decimal("1"), motivo="outro",
                             observacao="<script>alert(1)</script>")
        resp = self.client.get(reverse("resumo"))
        self.assertContains(resp, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(resp, "<script>alert(1)</script>")
