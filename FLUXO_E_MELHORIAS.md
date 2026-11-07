# Rev_pj26 — fluxo e reestruturação

O Rev_pj26 registra frequência por projeto e edição. A aplicação é um monólito Flask com páginas Jinja e persistência PostgreSQL. Blueprints recebem requisições, aplicam sessão e CSRF e renderizam ou redirecionam. O serviço de frequência coordena a leitura do QR e o repositório executa o SQL. A separação de responsabilidades, a gestão de segredos e as verificações de CI seguem a referência técnica da HellowTech, com operação independente.

## Fluxo do sistema

1. **Administração.** O administrador mantém cursos, projetos, usuários e vínculos de supervisão. Abre a edição ativa e importa alunos por CSV quando necessário. A troca de ciclo continua removendo os vínculos anteriores, conforme o comportamento existente.
2. **Acesso.** O usuário entra pelo identificador reconhecido pelo sistema. Contas pendentes passam pela conclusão de cadastro. O aluno consulta o dashboard e o histórico e pode criar ou cancelar uma inscrição pendente.
3. **Credencial.** O aluno abre seu QR no dashboard. A aplicação consulta o token persistente da própria conta e renderiza a imagem SVG no servidor. A resposta é privada e sem cache.
4. **Frequência.** O professor abre um projeto ativo que supervisiona e usa o scanner. O formulário envia o token no corpo de um POST protegido por CSRF. A aplicação confere o vínculo, encontra o aluno ativo e revalida o projeto e a supervisão na mesma transação que atualiza a inscrição. Se a inscrição já estiver confirmada, a leitura informa esse estado. Se ela não existir, a leitura não cria inscrição.
5. **Relatórios.** O professor exporta a lista dos projetos autorizados. O administrador exporta o relatório geral da edição. Cabeçalhos, delimitador, codificação e formato existentes foram preservados.

## Mudanças implementadas

| Frente | Mudança |
|---|---|
| Autorização | Detalhe, scanner, confirmação e exportação exigem supervisão sobre projeto ativo. Recursos indisponíveis retornam 404. |
| QR | Geração local do SVG com o token existente. O scanner usa POST e mantém o QR fora da URL. A versão da biblioteca do scanner foi fixada. |
| Concorrência | A atualização condicional com RETURNING identifica quem confirmou a presença. A remoção administrativa verifica novamente se a inscrição está pendente no momento da exclusão. |
| Importação | Cada linha fica isolada por savepoint para falhas de integridade. Falhas inesperadas abortam a operação. |
| Autenticação | POST de login e recuperação limitado a 15 tentativas por minuto e por IP. O URI configurado é entregue ao Flask-Limiter. A execução direta do Flask desativa o debug. |
| Bootstrap | Criação de administrador exige BOOTSTRAP_ADMIN_PASSWORD com pelo menos 20 caracteres. Nova execução preserva a edição ativa já configurada. Erros passam a interromper o comando. |

## Compatibilidade e configuração

- O DDL, os nomes e tipos de colunas, as chaves e os dados históricos foram preservados. As credenciais QR já emitidas mantêm o valor.
- Atualize scanner e aplicação no mesmo deploy. O endpoint legado de registro por GET foi retirado. Se houver scanner externo, adapte-o para o POST autenticado e protegido por CSRF antes da troca.
- Para banco novo, forneça DATABASE_URL ou as variáveis DB existentes e defina BOOTSTRAP_ADMIN_PASSWORD por meio do ambiente seguro antes de rodar init_db.py. A criação de senha nova não altera uma conta admin que já existe.
- Configure SECRET_KEY e SESSION_COOKIE_SECURE=true para deploy HTTPS. O rate limiter aceita RATELIMIT_STORAGE_URI e mantém QR_RATE_LIMIT_STORAGE_URI como fallback. O padrão em memória é por processo. Para múltiplos workers, use um backend compartilhado com o driver correspondente e confira o endereço de origem recebido através do proxy.
- Valide os fluxos em ambiente isolado com PostgreSQL antes do deploy. Para rollback, publique o artefato anterior junto com seu scanner correspondente.

## Validação e próximos passos

Os testes locais de serviço e contrato passaram. Os testes HTTP cobrem acesso a projetos alheios, POST e CSRF. Execute a suíte completa com as dependências de requirements.txt e Docker disponíveis. O teste de integração PostgreSQL atual verifica conectividade. A concorrência precisa de um teste com duas conexões reais e o esquema da aplicação.

A próxima etapa de segurança é substituir senhas provisórias derivadas dos identificadores no cadastro, importação e reset e revisar contas já provisionadas. Também faltam recuperação por canal verificado, revogação de sessões abertas, limites distribuídos por conta e origem e a auditoria do proxy de produção. O teste de carga existente precisa usar rotas reais. Use métricas de latência, conexões e consultas para decidir sobre pooling e índices.
