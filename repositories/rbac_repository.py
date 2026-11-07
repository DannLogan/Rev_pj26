from db import obter_conexao


def listar_permissoes_do_usuario(id_usuario: int) -> list[dict]:
    with obter_conexao() as cursor:
        cursor.execute("""
            SELECT p.codigo, rp.permissao IS NOT NULL AS padrao, up.permitido AS excecao
            FROM usuarios u
            JOIN rbac_permissoes p ON split_part(p.codigo, '.', 1) = u.tipo
            LEFT JOIN rbac_papel_permissoes rp ON rp.papel = u.tipo AND rp.permissao = p.codigo
            LEFT JOIN rbac_usuario_permissoes up ON up.id_usuario = u.id AND up.permissao = p.codigo
            WHERE u.id = %s AND p.codigo NOT LIKE 'admin.admin_permissoes_usuario.%%'
            ORDER BY p.codigo
        """, (id_usuario,))
        return cursor.fetchall()


def definir_excecao(id_usuario: int, codigo: str, permitido: bool | None) -> bool:
    with obter_conexao() as cursor:
        cursor.execute("""
            SELECT 1
            FROM usuarios u
            JOIN rbac_permissoes p ON split_part(p.codigo, '.', 1) = u.tipo
            WHERE u.id = %s AND p.codigo = %s
              AND p.codigo NOT LIKE 'admin.admin_permissoes_usuario.%%'
            FOR SHARE OF u, p
        """, (id_usuario, codigo))
        if cursor.fetchone() is None:
            return False
        if permitido is None:
            cursor.execute("""
                DELETE FROM rbac_usuario_permissoes
                WHERE id_usuario = %s AND permissao = %s
            """, (id_usuario, codigo))
        else:
            cursor.execute("""
                INSERT INTO rbac_usuario_permissoes (id_usuario, permissao, permitido)
                VALUES (%s, %s, %s)
                ON CONFLICT (id_usuario, permissao) DO UPDATE SET permitido = EXCLUDED.permitido
            """, (id_usuario, codigo, permitido))
        return True
