# Refatoração para Services e CI com PostgreSQL em Testcontainers

## Objetivo

Refatorar o monólito Flask atual para concentrar regras de negócio em uma camada `services`, mantendo os repositories responsáveis por persistência e os blueprints responsáveis por HTTP, sessão e apresentação.

## Regras confirmadas

- O aluno não pode registrar a própria presença.
- O QR code do aluno é permanente e não expira.
- A presença é registrada pelo professor, por aluno, projeto e edição.
- A CI deve validar a aplicação contra PostgreSQL executado em Docker através de Testcontainers.
- A refatoração deve preservar os demais comportamentos atuais, salvo os dois ajustes explicitamente confirmados acima.

## Arquitetura alvo

```text
Blueprints (HTTP/sessão/mensagens)
        ↓
Services (regras de negócio e casos de uso)
        ↓
Repositories (SQL e persistência)
        ↓
PostgreSQL
```

Os services receberão dependências de persistência quando isso simplificar testes. Os repositories não deverão conter decisões de fluxo HTTP, e os blueprints não deverão executar SQL diretamente.

## Fluxos críticos

### QR code

O QR code é gerado uma vez no cadastro/criação do aluno, armazenado em `alunos.qr_token` e reutilizado. A validação consulta o token persistente e o aluno ativo; não haverá expiração temporal.

### Registro de presença

O professor acessa o scanner, o token identifica o aluno e o service valida:

1. aluno existente e ativo;
2. projeto/edição aplicáveis;
3. inscrição do aluno no projeto e edição;
4. estado atual da presença.

O resultado mantém os estados atuais: sucesso, já presente ou não inscrito. O fluxo de auto-presença do aluno será removido/desabilitado.

### Consulta de frequência

Dashboards, histórico e exportações continuarão consultando os repositories através de services, sem alteração do formato esperado pelas telas.

## Testes

O teste superficial atual será removido. A suíte será organizada em `tests/` e cobrirá os fluxos críticos com PostgreSQL real em container, incluindo criação do schema de teste e isolamento entre testes.

Casos mínimos:

- QR code persistente após leituras repetidas;
- professor registra presença de aluno inscrito;
- segunda leitura não duplica a presença;
- aluno não inscrito não recebe presença;
- aluno não consegue registrar a própria presença;
- consulta retorna presentes e pendentes corretamente;
- autenticação e autorização de perfil nas rotas principais.

## CI

O GitHub Actions deverá:

1. instalar Python e dependências;
2. disponibilizar Docker;
3. executar a suíte com Testcontainers;
4. falhar o job quando testes, lint básico ou verificação de importação falharem.

## Fora do escopo

- Alterar o modelo de domínio além das regras confirmadas.
- Adicionar expiração, rotação ou regeneração automática de QR code.
- Introduzir novos patterns sem necessidade concreta.
- Alterar a hospedagem de produção.

## Sugestões de segurança para decisão posterior

Estas sugestões não serão aplicadas automaticamente nesta refatoração:

1. Remover credenciais do Supabase do código e exigir `DATABASE_URL`/segredos de ambiente.
2. Rotacionar imediatamente a senha atualmente exposta no repositório.
3. Exigir `SECRET_KEY` em produção, sem fallback previsível.
4. Proteger mutações com CSRF, especialmente as rotas administrativas e de inscrição.
5. Trocar ações destrutivas/alterações de estado via `GET` por `POST` com confirmação.
6. Aplicar rate limiting em login, recuperação de senha e leitura de QR code.
7. Evitar retornar detalhes internos de exceções nas mensagens exibidas ao usuário.
8. Registrar auditoria de presença: professor, aluno, projeto, edição, horário e origem.
9. Validar autorização do professor no próprio service antes de registrar presença, não apenas pela interface.
10. Usar cookies de sessão `Secure`, `HttpOnly` e `SameSite` em produção.
