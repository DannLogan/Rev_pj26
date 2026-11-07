BEGIN;
SET LOCAL lock_timeout = '2s';
CREATE TABLE IF NOT EXISTS public.supervisores_projeto_curso (
    id_professor INTEGER NOT NULL REFERENCES public.professores (id_usuario),
    id_projeto INTEGER NOT NULL REFERENCES public.projetos (id),
    id_curso INTEGER NOT NULL REFERENCES public.cursos (id),
    PRIMARY KEY (id_professor, id_projeto, id_curso)
);
REVOKE ALL ON public.supervisores_projeto_curso FROM PUBLIC;
ALTER TABLE public.supervisores_projeto_curso ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.supervisores_projeto_curso FROM anon, authenticated;
COMMIT;
