# Estoque Veloz

Sistema web para controle mensal de estoque de um restaurante. O backend Django concentra as regras de reposição e disponibiliza uma API; o frontend React oferece uma interface responsiva para cadastro, fechamento mensal, histórico e geração da lista de compras.

## Funcionalidades principais

- cadastro, edição, desativação e reativação de ingredientes;
- acompanhamento do estoque e da validade dos produtos;
- alertas para produtos vencidos ou próximos do vencimento;
- fechamento mensal com rascunho, revisão, finalização e cancelamento;
- atualização da meta com margem de 20% quando há falta antecipada;
- histórico dos fechamentos;
- lista de compras no navegador, em TXT, CSV e no terminal.

Formato obrigatório da lista:

```text
Comprar: <quantidade> <unidade> de <ingrediente>
```

Itens com quantidade calculada igual ou inferior a zero não são incluídos.

## Tecnologias

- Python e Django 5.2;
- Django REST Framework;
- React 19 e Vite;
- SQLite para execução local sem configuração;
- PostgreSQL/Supabase quando `DATABASE_URL` é informada.

## Pré-requisitos

- Git;
- Python 3.10 ou superior;
- Node.js 22 ou superior.

## Instalação

Clone o repositório e entre na pasta:

```bash
git clone https://github.com/FabioFeitosa7/Projeto-veloz.git
cd Projeto-veloz
```

### Backend — Windows/PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe backend/manage.py migrate
.\.venv\Scripts\python.exe backend/manage.py runserver
```

### Backend — Linux/macOS

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r backend/requirements.txt
./.venv/bin/python backend/manage.py migrate
./.venv/bin/python backend/manage.py runserver
```

O backend ficará disponível em `http://127.0.0.1:8000/`.

### Frontend

Mantenha o backend rodando. Em outro terminal, execute:

```bash
cd frontend
npm install
npm run dev
```

No PowerShell, caso `npm` seja bloqueado pela política de scripts, use:

```powershell
npm.cmd install
npm.cmd run dev
```

Acesse `http://localhost:5173/`.

## Dados para demonstração

Para preencher um banco vazio com dados que demonstram as principais regras:

```powershell
.\.venv\Scripts\python.exe backend/manage.py carregar_dados_demonstracao
```

No Linux/macOS:

```bash
./.venv/bin/python backend/manage.py carregar_dados_demonstracao
```

Execute esse comando antes de iniciar o fechamento pelo navegador. Ele recusa bancos que já possuem dados.

## Lista de compras no terminal

Depois de finalizar um fechamento no sistema, informe o mês no formato `AAAA-MM`:

```powershell
.\.venv\Scripts\python.exe backend/manage.py gerar_lista_compras --mes 2026-09
```

No Linux/macOS:

```bash
./.venv/bin/python backend/manage.py gerar_lista_compras --mes 2026-09
```

Exemplo:

```text
Comprar: 14 Kg de Farinha
Comprar: 20 Litros de Leite
Comprar: 52 Unidades de Ovos
```

## Testes e verificações

Backend:

```powershell
.\.venv\Scripts\python.exe backend/manage.py test estoque --settings=config.settings_test
```

Linux/macOS:

```bash
./.venv/bin/python backend/manage.py test estoque --settings=config.settings_test
```

Frontend:

```bash
cd frontend
npm run lint
npm run test
npm run build
```

Os testes do backend usam um SQLite temporário e não alteram o Supabase.

## Configuração opcional do PostgreSQL

Sem um arquivo `.env`, o backend utiliza SQLite. Para usar PostgreSQL/Supabase, copie `.env.example` para `.env` e preencha `DATABASE_URL`:

```powershell
Copy-Item .env.example .env
```

```env
DATABASE_URL=postgresql://usuario:senha@servidor:6543/postgres
```

O `.env` é ignorado pelo Git. Nunca publique senhas ou URLs reais do banco.

Para apontar o React para outro endereço do backend, copie `frontend/.env.example` para `frontend/.env` e defina:

```env
VITE_API_URL=https://endereco-do-backend/api
```

## Estrutura

```text
backend/     aplicação Django, API, regras de negócio e testes
frontend/    aplicação React, estilos e testes da interface
```

## Regras de negócio resumidas

- reposição normal: `meta mensal - estoque aproveitável`;
- em caso de falta: `nova meta = consumo mensal × 1,20`;
- estoque vencido é desconsiderado;
- unidades indivisíveis são arredondadas para cima;
- quilogramas e litros podem possuir casas decimais;
- fechamentos finalizados não podem ser alterados;
- fechamentos cancelados continuam disponíveis no histórico.

