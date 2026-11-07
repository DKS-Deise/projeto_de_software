# Delícias da Lu · Controle de desperdício (MVP)

MVP em Django para registrar **compras, receitas e perdas de ingredientes** e medir a **taxa de desperdício** de um pequeno negócio de confeitaria da Vila Formosa (São Paulo). Projeto da Experiência Prática de Projeto de Software.

## Problema e público
- **Problema:** hoje as compras e as perdas (por exemplo, a calda do morango do amor que não deu certo) são anotadas em caderno, sem valor nem motivo. O desperdício não é medido.
- **Usuária direta:** Carina, que registra tudo pelo celular, na cozinha e na garagem de atendimento, com pouco tempo.
- **Beneficiados:** Lourdes (dona), clientes do bairro e a comunidade.
- **ODS 12** (meta 12.3): reduzir perdas de alimentos, ao tornar o desperdício visível e mensurável.

## Funcionalidades
| Requisito | Tela | Rota |
|---|---|---|
| RF01 Registrar compra (atualiza o preço atual do ingrediente) | Registrar compra | `/compras/nova/` |
| RF02 Cadastrar receita e ver o custo | Receitas | `/receitas/`, `/receitas/nova/` |
| RF03 Registrar perda com motivo (grava o valor perdido) | Registrar perda | `/perdas/nova/` |
| RF04 Resumo do mês: taxa de desperdício e motivo mais frequente | Resumo do mês | `/resumo/` |
| RF05 (desejável) Vendas, gastos e saldo | Caixa | `/caixa/` |

## Arquitetura e tecnologias
Monolito em três camadas dentro de uma aplicação web responsiva:
- **Apresentação:** `views.py` e `templates/` (Bootstrap 5.3.3 via CDN).
- **Regras de negócio:** `models.py` (entidades e regras) e `services.py` (taxa de desperdício, saldo).
- **Dados:** ORM do Django; PostgreSQL gerenciado em produção, SQLite só em desenvolvimento.

Python 3.12 · Django 5.2 LTS · Bootstrap 5.3 · psycopg 3.

Entidades: `Ingrediente`, `Compra`, `Receita`, `ItemReceita`, `Perda`, `Lancamento`.

## Como executar
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DJANGO_DEBUG=1                                # Windows (PowerShell): $env:DJANGO_DEBUG="1"
python manage.py migrate
python manage.py createsuperuser                     # cria a conta de acesso (use dados fictícios em demonstração)
python manage.py runserver
```
Abra `http://127.0.0.1:8000/`. Cadastre ingredientes em "Registrar compra" → "Cadastrar novo ingrediente".

Para produção, defina as variáveis de `.env.example` no serviço de hospedagem (chave secreta, hosts, banco e HTTPS) e rode `python manage.py migrate`.

## Testes
```bash
DJANGO_DEBUG=1 python manage.py test
```
Os 16 testes cobrem os cálculos (RF01–RF05) e os controles de segurança: telas exigem login, senha com hash PBKDF2, CSRF obrigatório, validação no servidor, motivo restrito à lista e script digitado exibido como texto.

O GitHub Actions executa essa suíte automaticamente em cada pull request para `main` e em cada push para `main`. O resultado aparece na aba **Actions** e nos checks do pull request.

## Segurança (RNF01/RNF02)
Login obrigatório em todas as telas, senhas com PBKDF2 (nativo do Django, mínimo de 8 caracteres), sessão de 8 h com cookies `HttpOnly`/`Secure`, token CSRF, consultas pelo ORM, saída escapada nos templates, `DEBUG` desligado por padrão, segredos em variáveis de ambiente e mensagem genérica no erro de login.

## Limites conhecidos
- Não há bloqueio automático após tentativas de login repetidas (exigiria biblioteca extra ou código próprio).
- A meta de carregamento de 3 s e a nota do Lighthouse ainda precisam ser medidas após a publicação.
- Contas são criadas pela desenvolvedora (sem cadastro público).

## Protótipo e validação
A pasta `docs/` traz o protótipo clicável usado na validação com a usuária e as capturas das três telas. Todos os dados são fictícios.
