BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '15s';
SET LOCAL lock_timeout = '2s';

SELECT schemaname, relname, n_live_tup AS linhas_estimadas
FROM pg_stat_user_tables ORDER BY 1, 2;

SELECT n.nspname AS esquema, c.relname AS objeto, c.relkind,
       c.relrowsecurity AS rls, c.relforcerowsecurity AS rls_forcado,
       has_table_privilege('anon', c.oid, 'SELECT') AS anon_leitura,
       has_table_privilege('authenticated', c.oid, 'SELECT') AS autenticado_leitura
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind IN ('r','p','v','m','f')
ORDER BY 1, 2;

SELECT 'presenca_invalida' AS verificacao, count(*) AS ocorrencias
FROM public.inscricoes WHERE presenca NOT IN (0, 1)
UNION ALL
SELECT 'presenca_nula', count(*) FROM public.inscricoes WHERE presenca IS NULL
UNION ALL
SELECT 'perfis_invalidos', count(*) FROM public.usuarios
WHERE tipo NOT IN ('aluno','professor','admin')
UNION ALL
SELECT 'qr_duplicado_grupos', count(*) FROM (
    SELECT qr_token FROM public.alunos WHERE qr_token IS NOT NULL
    GROUP BY qr_token HAVING count(*) > 1
) AS duplicados
UNION ALL
SELECT 'inscricao_sem_subtipo_aluno', count(*)
FROM public.inscricoes i LEFT JOIN public.alunos a ON a.id_usuario = i.id_aluno
WHERE a.id_usuario IS NULL
UNION ALL
SELECT 'supervisao_sem_subtipo_professor', count(*)
FROM public.supervisores_projeto s
LEFT JOIN public.professores p ON p.id_usuario = s.id_professor
WHERE p.id_usuario IS NULL;

ROLLBACK;
