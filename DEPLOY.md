# Deploy — HOC Gestão no Railway

## Pré-requisitos

- Conta no [GitHub](https://github.com) (gratuita)
- Registrado em: jiannibelli@hoc.com.br (Hoctec@01)
- Conta no [Railway](https://railway.app) (gratuita — login com GitHub)
- OK

---

## Passo 1 — Subir o código no GitHub

Abra o terminal na pasta do projeto e execute:

```bash
git init
git add .
git commit -m "primeiro deploy"
```

Acesse github.com → **New repository** → nomeie como `hoc-gestao` → **Create repository**.

Em seguida, conecte e envie:

```bash
git remote add origin https://github.com/JoseIannibelli/hoc-gestao.git
git branch -M main
git push -u origin main
```

---

## Passo 2 — Criar o projeto no Railway

1. Acesse [railway.app](https://railway.app) e faça login com sua conta GitHub
2. Clique em **New Project → Deploy from GitHub repo**
3. Selecione o repositório `hoc-gestao`
4. O Railway detectará automaticamente que é uma aplicação Python e iniciará o build

---

## Passo 3 — Configurar as variáveis de ambiente

No painel do Railway, vá em **Variables** e adicione:

| Variável | Valor |
|---|---|
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | *(gere com: `python -c "import secrets; print(secrets.token_hex(32))"`)* |
| `ADMIN_EMAIL` | seu e-mail de administrador |
| `ADMIN_PASSWORD` | senha forte para o primeiro acesso |

> As demais variáveis de e-mail são opcionais neste momento — o sistema funciona sem elas.

---

## Passo 4 — Adicionar volume para o banco de dados

O Railway usa containers que resetam a cada deploy. Para o banco SQLite não perder dados, é necessário um **Volume**:

1. No painel do projeto, clique em **+ New → Volume**
2. Monte o volume no caminho: `/app/data`
3. Volte em **Variables** e adicione:

| Variável | Valor |
|---|---|
| `DATABASE_URL` | `sqlite:////app/data/hoc.db` |

Isso garante que o banco fica em disco persistente independente de redeploys.

---

## Passo 5 — Criar o usuário administrador (primeiro acesso)

Após o deploy estar online, abra o terminal do Railway (**Settings → Deploy → Open Terminal**) e execute:

```bash
flask criar-admin
```

Isso criará o usuário com o e-mail e senha definidos nas variáveis `ADMIN_EMAIL` e `ADMIN_PASSWORD`.

---

## Passo 6 — Gerar a URL pública

No painel do Railway, vá em **Settings → Networking → Generate Domain**.

O Railway fornecerá uma URL pública no formato `hoc-gestao-production.up.railway.app`.

---

## Atualizações futuras

Para publicar qualquer atualização, basta fazer commit e push:

```bash
git add .
git commit -m "descrição da mudança"
git push
```

O Railway detecta o push e faz o redeploy automaticamente em ~1 minuto.

---

## Sobre o banco de dados

Para esta fase de MVP, o SQLite com volume persistente é suficiente.
Quando o sistema evoluir para produção real com múltiplos usuários simultâneos,
a migração para PostgreSQL (também oferecido gratuitamente pelo Railway) é simples:
basta adicionar o serviço PostgreSQL no Railway e ele preencherá a variável `DATABASE_URL` automaticamente.

---

## Limites do plano gratuito do Railway

- 500 horas de execução por mês (suficiente para uso interno contínuo)
- 1 GB de RAM, 1 GB de disco no volume
- Sem limite de deploys

Para uso da equipe inteira em MVP, esses limites são mais que suficientes.
