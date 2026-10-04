# Arquitetura de Software — Sistema de Frequência do Simpósio de Extensão

Documento de referência para a refatoração do projeto. Cada decisão aqui tem uma justificativa ligada a um requisito real do projeto, não é aplicação de "boa prática" sem contexto.

## Contexto do projeto

- Projeto de extensão universitária, sem investimento financeiro.
- Não há garantia de continuidade/manutenção após a saída da equipe atual.
- Função principal: controle de frequência de alunos em palestras via leitura de QR code único por aluno.
- Check-in é único por palestra (não por evento inteiro).
- Estimativa de carga (sem dados reais ainda): ~300 usuários simultâneos no pico de uma palestra.
- Dados de frequência costumam ser consultados em menos de uma semana após o evento.
- Equipe: 1 desenvolvedor codificando com apoio de IA + 1 pessoa revisando arquitetura/PRs.

## Decisões de arquitetura

### 1. Estilo arquitetural: Monolito comum

Decisão: **não** modularizar com fronteiras rígidas (sem monolito modular, sem microsserviços).

Justificativa:
- Sem necessidade de escalar partes do sistema de forma independente.
- Sem múltiplos times publicando em ritmos diferentes.
- Projeto sem continuidade de longo prazo — o custo de manter fronteiras rígidas não se paga.

Ainda assim, manter **separação por camadas** dentro do monolito, para legibilidade e facilidade de encontrar bugs:
- Camada de rotas/entrada (API)
- Camada de regra de negócio (services/use cases)
- Camada de acesso a dados (repositories)

### 2. Conectividade

Decisão: aplicação **online apenas**, sem suporte a funcionamento offline.

Justificativa: suporte offline (com sincronização de dados) é a parte mais complexa de implementar neste tipo de sistema, e o retorno não justifica o esforço dado o escopo e tempo do projeto.

### 3. Banco de dados

Decisão: **Supabase** (Postgres gerenciado).

Justificativa: facilita gerência do banco sem precisar manter infraestrutura própria — alinhado com "sem equipe de manutenção depois".

⚠️ **Risco conhecido e aceito**: o plano gratuito do Supabase pausa o projeto após um período de inatividade (atualmente em torno de uma semana). Como as consultas aos dados de frequência costumam acontecer em menos de uma semana após o evento, o risco é considerado baixo. **Ação**: configurar um alerta/lembrete para reativar o banco manualmente caso fique inativo por tempo prolongado.

### 4. Design patterns

Decisão: aplicar principalmente **Repository** e **Service (Use Case)**.

Justificativa:
- Repository isola o acesso a dados da regra de negócio.
- Service concentra a regra de negócio (ex: gerar QR code, validar presença).
- Padrões já conhecidos pelo desenvolvedor principal (experiência prévia em Java), reduzindo a curva de aprendizado à sintaxe Python.

Novos patterns só devem ser adicionados quando houver um problema concreto que os justifique — não adicionar por estudo/teoria.

### 5. Guia para a IA (`AGENTS.md`)

Criar um arquivo `AGENTS.md` na raiz do repositório contendo:
- Estrutura de pastas esperada (rotas / services / repositories).
- Convenções de nomenclatura.
- Limitações do que a IA não deve fazer (ex: não misturar camadas, não acessar banco direto da rota).

Este arquivo guia a IA, mas **não substitui** a validação automatizada (ver item 6) — é guideline, não trava.

### 6. Rede de segurança: testes de caracterização

Decisão: escrever testes de caracterização (com apoio de IA) para os fluxos críticos antes de refatorar:
- Geração de QR code
- Validação/registro de presença por palestra
- Consulta de frequência

Esses testes registram o comportamento **atual** do sistema (não o comportamento "correto"), servindo como rede de segurança durante a refatoração incremental.

### 7. Fluxo de trabalho / critério de aceite

Decisão:
- Todo código passa a entrar via **Pull Request** (nada direto na `main`).
- **CI** roda os testes automaticamente em cada PR — CI verde é o critério principal de aceite.
- Revisão adicional leve (assistida por IA) para identificar desvios óbvios das guidelines do `AGENTS.md`, sem revisão linha a linha.

### 8. Refatoração incremental (strangler fig)

Ordem sugerida:
1. Escrever testes de caracterização dos fluxos críticos.
2. Definir estrutura alvo no `AGENTS.md`.
3. Código novo já nasce na estrutura nova.
4. Migrar um módulo por vez, em PRs pequenos e frequentes (evitar branch de refatoração longa, que gera conflitos).
5. Combinar janelas curtas com o time para evitar dois devs mexendo no mesmo módulo em migração.

Não é necessário parar o desenvolvimento de novas features para refatorar — a migração acontece em paralelo, módulo por módulo.

### 9. ADRs (Architecture Decision Records)

Decisão: registrar decisões arquiteturais relevantes como ADRs a partir de agora, documentando contexto, alternativas consideradas e motivo da escolha. As decisões deste documento podem servir de base para os primeiros ADRs.

## Pontos em aberto

- Número real de acessos simultâneos e de palestras ocorrendo em paralelo (depende de reunião com a central de extensão).
- Local de hospedagem da aplicação (ainda não definido).
