CREATE TABLE IF NOT EXISTS public.rbac_papeis (
    codigo text PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS public.rbac_permissoes (
    codigo text PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS public.rbac_papel_permissoes (
    papel text NOT NULL REFERENCES public.rbac_papeis (codigo),
    permissao text NOT NULL REFERENCES public.rbac_permissoes (codigo),
    PRIMARY KEY (papel, permissao)
);

CREATE TABLE IF NOT EXISTS public.rbac_usuario_permissoes (
    id_usuario integer NOT NULL REFERENCES public.usuarios (id),
    permissao text NOT NULL REFERENCES public.rbac_permissoes (codigo),
    permitido boolean NOT NULL,
    PRIMARY KEY (id_usuario, permissao)
);

INSERT INTO public.rbac_papeis (codigo)
VALUES ('admin'), ('professor'), ('aluno')
ON CONFLICT DO NOTHING;

WITH padroes(papel, permissao) AS (
    VALUES
    ('admin', 'admin.admin_painel.read'),
    ('admin', 'admin.admin_check_vinculos.read'),
    ('admin', 'admin.admin_gestao_cursos.read'),
    ('admin', 'admin.admin_gestao_projetos.read'),
    ('admin', 'admin.admin_gestao_usuarios.read'),
    ('admin', 'admin.admin_novo_usuario.read'),
    ('admin', 'admin.editar_usuario.read'),
    ('admin', 'admin.admin_permissoes_usuario.read'),
    ('admin', 'admin.admin_importar.read'),
    ('admin', 'admin.admin_configuracoes.read'),
    ('admin', 'admin.exportar_presencas.read'),
    ('admin', 'admin.desativar_projeto.write'),
    ('admin', 'admin.admin_gestao_cursos.write'),
    ('admin', 'admin.admin_toggle_curso.write'),
    ('admin', 'admin.admin_gestao_projetos.write'),
    ('admin', 'admin.admin_toggle_projeto.write'),
    ('admin', 'admin.admin_novo_usuario.write'),
    ('admin', 'admin.editar_usuario.write'),
    ('admin', 'admin.admin_permissoes_usuario.write'),
    ('admin', 'admin.admin_toggle_usuario.write'),
    ('admin', 'admin.admin_importar.write'),
    ('admin', 'admin.admin_configuracoes.write'),
    ('aluno', 'aluno.aluno_dashboard.read'),
    ('aluno', 'aluno.aluno_historico.read'),
    ('aluno', 'aluno.credencial.read'),
    ('aluno', 'aluno.aluno_inscrever_manual.write'),
    ('aluno', 'aluno.aluno_cancelar_inscricao.write'),
    ('professor', 'professor.professor_dashboard.read'),
    ('professor', 'professor.professor_projeto.read'),
    ('professor', 'professor.professor_scanner.read'),
    ('professor', 'professor.professor_exportar_csv.read'),
    ('professor', 'professor.professor_exportar_geral.read'),
    ('professor', 'professor.registrar_presenca.write')
), catalogo AS (
    INSERT INTO public.rbac_permissoes (codigo)
    SELECT DISTINCT permissao FROM padroes
    ON CONFLICT DO NOTHING
    RETURNING codigo
)
INSERT INTO public.rbac_papel_permissoes (papel, permissao)
SELECT papel, permissao FROM padroes JOIN catalogo ON codigo = permissao
ON CONFLICT DO NOTHING;

ALTER TABLE public.rbac_papeis ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rbac_permissoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rbac_papel_permissoes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rbac_usuario_permissoes ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.rbac_papeis, public.rbac_permissoes,
    public.rbac_papel_permissoes, public.rbac_usuario_permissoes FROM PUBLIC;
DO $$
DECLARE papel_api text;
BEGIN
    FOR papel_api IN SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')
    LOOP
        EXECUTE format('REVOKE ALL ON public.rbac_papeis, public.rbac_permissoes, public.rbac_papel_permissoes, public.rbac_usuario_permissoes FROM %I', papel_api);
    END LOOP;
END;
$$;
