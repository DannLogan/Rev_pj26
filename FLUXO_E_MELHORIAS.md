# Rev_pj26 — fluxo e reestruturação

O Rev_pj26 registra frequência por projeto e edição. A aplicação é um monólito Flask com páginas Jinja e persistência PostgreSQL. Blueprints recebem requisições, aplicam sessão e CSRF e renderizam ou redirecionam. O serviço de frequência coordena a leitura do QR e o repositório executa o SQL. A separação de responsabilidades, a gestão de segredos e as verificações de CI seguem a referência técnica da HellowTech, com operação independente.

## Fluxo do sistema

1. **Administração.** O administrador mantém cursos, projetos, usuários e vínculos de supervisão. Abre a edição ativa e importa alunos por CSV quando necessário. A troca de ciclo continua removendo os vínculos anteriores, conforme o comportamento existente.
2. **Acesso.** O usuário entra pelo identificador reconhecido pelo sistema. Contas pendentes usam uma credencial provisória gerada pela administração e passam pela conclusão de cadastro. Em caso de perda de acesso, a administração verifica a identidade e emite uma nova credencial. O aluno consulta o dashboard e o histórico e pode criar ou cancelar uma inscrição pendente.
3. **Credencial.** O aluno abre seu QR no dashboard. A aplicação consulta o token persistente da própria conta e renderiza a imagem SVG no servidor. A resposta é privada e sem cache.
4. **Frequência.** O professor abre um projeto ativo que supervisiona e usa o scanner. O formulário envia o token e a edição exibida no scanner no corpo de um POST protegido por CSRF. Se o ciclo mudou desde que a página foi aberta, o professor deve reabrir o scanner. A aplicação confere o vínculo, encontra o aluno ativo e revalida o projeto e a supervisão na mesma transação que atualiza a inscrição. Se a inscrição já estiver confirmada, a leitura informa esse estado. Se ela não existir, a leitura não cria inscrição.
5. **Relatórios.** O professor exporta a lista dos projetos autorizados. O administrador exporta o relatório geral da edição. Cabeçalhos, delimitador, codificação e formato existentes foram preservados.

## Mudanças implementadas

| Frente | Mudança |
|---|---|
| Autorização | Detalhe, scanner, confirmação e exportação exigem supervisão sobre projeto ativo. Recursos indisponíveis retornam 404. |
| QR | Geração local do SVG com o token existente. O scanner usa POST e mantém o QR fora da URL. A versão da biblioteca do scanner foi fixada. |
| Concorrência | A atualização condicional com RETURNING identifica quem confirmou a presença. A remoção administrativa verifica novamente se a inscrição está pendente no momento da exclusão. |
| Importação | Cada linha fica isolada por savepoint para falhas de integridade. Falhas inesperadas abortam a operação. A importação tem limites de tamanho e volume. |
| Autenticação | POST de login limitado a 15 tentativas por minuto e por IP. A recuperação por pergunta de segurança foi desativada. A sessão expira por inatividade e é invalidada quando a conta é desativada ou a senha muda. O URI configurado é entregue ao Flask-Limiter. A execução direta do Flask desativa o debug. |
| Bootstrap | Criação de administrador exige BOOTSTRAP_ADMIN_PASSWORD com pelo menos 20 caracteres. Nova execução preserva a edição ativa já configurada. Erros passam a interromper o comando. |

A inscrição manual valida o projeto ativo e lê a edição vigente dentro da mesma transação. Reenvios da mesma inscrição são tratados pela chave composta existente. A troca de edição bloqueia a linha de configuração durante a operação e pode inicializá-la se estiver ausente. Duas tentativas simultâneas de abrir a mesma edição resultam em uma criação. A limpeza de supervisores ao mudar o ciclo continua fazendo parte do fluxo. Presença e cancelamento também bloqueiam a configuração na transação e rejeitam a edição anterior se uma troca de ciclo já ocorreu.

## Compatibilidade e configuração

- O DDL, os nomes e tipos de colunas, as chaves e os dados históricos foram preservados. As credenciais QR já emitidas mantêm o valor.
- Atualize scanner e aplicação no mesmo deploy. O endpoint legado de registro por GET foi retirado. Se houver scanner externo, adapte-o para o POST autenticado e protegido por CSRF antes da troca. O formulário envia `qr_token` e `edicao`, obtida ao abrir o scanner.
- Para banco novo, forneça DATABASE_URL ou as variáveis DB existentes e defina BOOTSTRAP_ADMIN_PASSWORD por meio do ambiente seguro antes de rodar init_db.py. A criação de senha nova não altera uma conta admin que já existe.
- Configure SECRET_KEY e SESSION_COOKIE_SECURE=true para deploy HTTPS. O rate limiter aceita RATELIMIT_STORAGE_URI e mantém QR_RATE_LIMIT_STORAGE_URI como fallback. O padrão em memória é por processo. Para múltiplos workers, use um backend compartilhado com o driver correspondente e confira o endereço de origem recebido através do proxy.
- Valide os fluxos em ambiente isolado com PostgreSQL antes do deploy. Para rollback, publique o artefato anterior junto com seu scanner correspondente.

## Validação e próximos passos

Os testes locais de serviço e contrato passaram. Os testes HTTP cobrem acesso a projetos alheios, POST e CSRF. Execute a suíte completa com as dependências de requirements.txt e Docker disponíveis. O teste de integração usa PostgreSQL 16 descartável, aplica o esquema real e confere que duas conexões concorrentes produzem uma confirmação e uma resposta de presença já registrada. Ele também verifica a rejeição de um ator sem vínculo.

## Transição das credenciais e sessões

- Após o deploy, as sessões antigas exigem novo login. Sessões novas têm limite de inatividade de uma hora para aluno e professor e oito horas para admin.
- Antes de publicar, confira que há um administrador ativo com senha forte. A senha legada do bootstrap e as senhas previsíveis de contas pendentes deixam de funcionar. Emita credenciais novas para essas contas via administração.
- O cadastro manual, o reset e a importação exibem as credenciais provisórias na resposta administrativa com `Cache-Control: private, no-store`. Entregue cada credencial diretamente ao titular por canal institucional. O banco armazena o hash. A credencial vale até a troca no primeiro acesso ou até novo reset.
- Para validar o rollout, confirme que um reset derruba a sessão anterior, que a senha nova permite concluir o cadastro e que um usuário desativado perde acesso. Verifique também que o HTML do resultado não é armazenado por proxy ou registrado por ferramentas de inspeção.

## Medição e operação

A recuperação automática exigiria um canal institucional verificado. A recuperação atual é assistida. Verifique a origem de IP no proxy e o compartilhamento dos contadores entre workers antes de usar os limites em produção. O cenário Locust faz login de professor e usa dashboard, scanner, registro e exportação. Execute apenas em ambiente isolado com projeto ativo, professor vinculado e aluno inscrito. Instale Locust separadamente e forneça LOAD_TEST_ALLOW_WRITES=1, LOAD_TEST_PROJECT_ID, LOAD_TEST_QR_TOKEN, LOAD_TEST_LOGIN e LOAD_TEST_PASSWORD pelo ambiente. Execute `locust -f locustfile.py --host <url-de-teste>`. Reinicie a inscrição entre rodadas que precisam medir a primeira escrita. Com o mesmo QR, as demais leituras exercitam a confirmação idempotente. Compare p95, taxa de erros e saturação antes de decidir sobre pooling e índices.

- `GET /health` verifica o processo. `GET /ready` consulta o banco e retorna 503 se ele estiver indisponível. Configure o health check conforme a finalidade.
- A aplicação retorna `X-Request-ID` e emite um log JSON por requisição com rota parametrizada, método, status e duração. O formato omite corpo, parâmetros, URL bruta e texto de exceções. Configure a coleta e revise também logs do proxy e do servidor HTTP.
- A conexão PostgreSQL tem timeout de abertura de cinco segundos. A carga e os planos SQL ainda devem ser medidos em homologação.


## Publicação e rollback

1. No PR, aguarde instalação, checagem de dependências e suíte completa com PostgreSQL descartável. A branch só deve seguir para homologação depois de passar pelo CI.
2. Em homologação, rode o aplicativo com `gunicorn 'app:create_app()'` em Linux e valide `/health` e `/ready`. Confira configuração de HTTPS, contadores do limitador e logs do proxy.
3. Faça a validação funcional com um professor vinculado, um professor sem acesso, um aluno inscrito e um administrador. Teste a leitura duplicada, a troca de edição com scanner aberto, a redefinição de senha, o CSV e a exportação.
4. Registre a linha de base do teste de carga. O resolvedor central de edição passou a fazer uma única consulta, inclusive no fallback por nome. A decisão sobre pooling e índices depende dos resultados reais.
5. Publique aplicativo e templates juntos. Para rollback, restaure o artefato anterior completo e verifique saúde, login e scanner. A implantação deste lote dispensa migração do banco.

## Fechamento da revisão

- O primeiro acesso depende de provisionamento administrativo. A página pública orienta o usuário e não cria contas. O retorno da edição de perfil é escolhido no servidor.
- O login rejeita identificadores ambíguos. O provisionamento e a atualização de perfil verificam colisões entre identificadores existentes. Em homologação, identifique e corrija colisões antigas antes da publicação.
- As alterações de vínculos administrativos validam a edição exibida no formulário. Desativação e vinculação de projetos usam bloqueios compatíveis no PostgreSQL. A listagem administrativa consulta os vínculos em lote.
- Os botões de exportação solicitam o modo planilha, que trata prefixos de fórmulas. O endpoint sem o parâmetro preserva o CSV legado. Ao importar em planilha, selecione texto para a coluna de matrícula para preservar zeros à esquerda.
- O aplicativo limita a requisição a 3 MiB e o arquivo CSV a 2 MiB e 5.000 registros. O cabeçalho é reconhecido pelo primeiro campo. No ambiente com FLASK_ENV=production, o cookie de sessão usa Secure.
- O Locust verifica a confirmação após seguir o redirecionamento. A execução com dados representativos continua necessária antes de dimensionar índices ou pooling.
