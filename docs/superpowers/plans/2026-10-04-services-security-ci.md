# Services, Security and CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refatorar a aplicação para services, reforçar segurança HTTP/sessão e validar tudo em CI com PostgreSQL real em Testcontainers.

**Architecture:** Blueprints cuidarão de HTTP e apresentação; services concentrarão casos de uso; repositories cuidarão de SQL. A configuração virá do ambiente, com PostgreSQL de teste executado por Testcontainers.

**Tech Stack:** Flask, PostgreSQL, pytest, Testcontainers, Flask-WTF, Flask-Limiter, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-10-04-arquitetura-services-design.md`

## Global Constraints

- O aluno não registra a própria presença.
- QR codes são permanentes.
- Presença é por aluno, projeto e edição.
- Exceções internas não são exibidas ao usuário.
- Mutations usam verbos HTTP apropriados.
- Sessões comuns duram 1 hora; painel administrativo dura 8 horas.

## Review Focus

- Repetição do mesmo QR code não cria presença duplicada — teste do service de presença.
- Aluno não inscrito não recebe presença — teste do service.
- Aluno não acessa endpoint de registro — teste de autorização.
- Token de dispositivo diferente possui bucket de rate limit independente — teste do limitador.
- Aplicação sem `SECRET_KEY` de produção falha explicitamente — teste de configuração.

### Task 1: Configuration and security foundation

**Files:** `.env`, `.env.example`, `.gitignore`, `requirements.txt`, `config.py`, `app.py`, `utils/security.py`, `utils/logging.py`, tests.

- [ ] Add environment-backed configuration and safe local `.env`; never commit secrets.
- [ ] Add CSRF, session cookie settings, device identifier and logging.
- [ ] Add rate limiting for QR validation based on signed device cookie.
- [ ] Add tests for configuration, cookies and device isolation.

### Task 2: Domain services and tests

**Files:** `services/`, `repositories/`, `tests/services/`.

- [ ] Create services for authentication, student enrollment/presence, professor attendance and frequency queries.
- [ ] Move rules out of routes without changing repository behavior beyond confirmed requirements.
- [ ] Add tests for persistent QR, attendance success, duplicate attendance, non-enrolled student and self-attendance rejection.

### Task 3: Route migration and HTTP semantics

**Files:** `blueprints/*.py`, templates, `utils/decorators.py`, tests.

- [ ] Replace direct SQL from blueprints with service calls.
- [ ] Remove student self-presence route and update templates.
- [ ] Convert state-changing GET routes to POST and add CSRF fields to forms.
- [ ] Return generic user-facing errors and log internal exceptions.

### Task 4: Testcontainers and CI

**Files:** `tests/`, `testcontainers/`, `.github/workflows/ci.yml`, `pytest.ini`.

- [ ] Build isolated PostgreSQL fixtures from `init_db.py` schema.
- [ ] Remove `teste_sistema.py` and replace it with real route/service tests.
- [ ] Configure CI to install dependencies and run tests against Testcontainers.
- [ ] Run the complete suite and import checks.
