# Guia para edição por IA

## Estrutura

- `blueprints/`: entrada HTTP, sessão, redirects, flash messages e templates.
- `services/`: regras de negócio e casos de uso.
- `repositories/`: SQL e persistência; não decide fluxo HTTP.
- `utils/`: autenticação, segurança e infraestrutura transversal.
- `tests/`: testes de comportamento; prefira testar services pela interface pública.

## Regras de arquitetura

1. Rota não executa SQL diretamente.
2. Regra de negócio fica em `services/`, não em template ou blueprint.
3. Repository recebe e retorna dados; não conhece Flask, sessão ou mensagens.
4. O aluno não registra a própria presença.
5. QR codes de alunos são persistentes e não expiram.
6. Presença é única por aluno, projeto e edição.
7. Exceções internas são registradas no log e substituídas por mensagens genéricas.
8. Operações que alteram estado usam `POST`, `PUT`, `PATCH` ou `DELETE`; `GET` é somente leitura.
9. Segredos vêm do ambiente. Nunca adicionar credenciais ao código, testes ou documentação versionada.

## Segurança

- Toda mutação de formulário usa CSRF.
- Login e leitura de QR code devem ter rate limit por dispositivo.
- Sessão comum dura 1 hora; sessão administrativa dura 8 horas.
- Cookies de sessão devem ser `HttpOnly` e `SameSite=Lax`; produção usa `Secure`.

## Validação obrigatória

```bash
pytest -q
python3 -m py_compile app.py config.py
git diff --check
```

O CI deve permanecer verde antes de abrir ou aprovar um PR.

## Fluxo obrigatório de Git e Pull Request

Para toda alteração no projeto:

1. Criar uma nova branch a partir da `main`; nunca desenvolver diretamente na `main`.
2. Implementar a alteração em commits pequenos e descritivos.
3. Executar a validação obrigatória antes de publicar.
4. Enviar a branch para o GitHub (`git push -u origin <branch>`).
5. Abrir um Pull Request contra `main`.
6. Considerar o trabalho encerrado somente depois que o PR estiver aberto e a CI tiver sido executada.

Alterações adicionais durante a revisão devem ser feitas na branch do PR existente, salvo quando a revisão exigir uma nova alteração independente.
