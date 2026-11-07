BEGIN;
SET LOCAL lock_timeout = '2s';
SET LOCAL statement_timeout = '30s';

-- Preserve os registros existentes e impeça exclusões que apagariam histórico por cascata.
ALTER TABLE public.alunos
    ADD CONSTRAINT alunos_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios (id),
    ADD CONSTRAINT alunos_matricula_key UNIQUE (matricula),
    ADD CONSTRAINT alunos_qr_token_key UNIQUE (qr_token);

ALTER TABLE public.professores
    ADD CONSTRAINT professores_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuarios (id),
    ADD CONSTRAINT professores_id_corporativo_key UNIQUE (id_corporativo);

ALTER TABLE public.usuarios
    ADD CONSTRAINT usuarios_login_key UNIQUE (login);

ALTER TABLE public.usuarios_cursos
    ADD CONSTRAINT usuarios_cursos_id_aluno_fkey FOREIGN KEY (id_aluno) REFERENCES public.usuarios (id),
    ADD CONSTRAINT usuarios_cursos_id_curso_fkey FOREIGN KEY (id_curso) REFERENCES public.cursos (id);

ALTER TABLE public.supervisores_projeto
    ADD CONSTRAINT supervisores_projeto_id_professor_fkey FOREIGN KEY (id_professor) REFERENCES public.usuarios (id),
    ADD CONSTRAINT supervisores_projeto_id_projeto_fkey FOREIGN KEY (id_projeto) REFERENCES public.projetos (id);

ALTER TABLE public.inscricoes
    ADD CONSTRAINT inscricoes_id_aluno_fkey FOREIGN KEY (id_aluno) REFERENCES public.usuarios (id),
    ADD CONSTRAINT inscricoes_id_projeto_fkey FOREIGN KEY (id_projeto) REFERENCES public.projetos (id),
    ADD CONSTRAINT inscricoes_id_edicao_fkey FOREIGN KEY (id_edicao) REFERENCES public.edicoes (id),
    ADD CONSTRAINT inscricoes_presenca_check CHECK (presenca IN (0, 1));

COMMIT;
