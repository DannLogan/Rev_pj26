import csv
import io
import re
import uuid
import math
from io import StringIO
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, make_response
from werkzeug.security import generate_password_hash
from utils.decorators import requer_autenticacao, requer_perfil
from repositories import admin_repository, auth_repository
from db import obter_configuracao_global

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/painel')
@requer_autenticacao
@requer_perfil('admin')
def admin_painel():
    return render_template('painel_admin.html')

@admin_bp.route('/admin/projeto/<int:projeto_id>/desativar')
@requer_autenticacao
@requer_perfil('admin')
def desativar_projeto(projeto_id):
    id_edicao = obter_configuracao_global('edicao_ativa')
    
    # 1. Validação de segurança em backend que criamos
    if admin_repository.verificar_vinculos_projeto(projeto_id, id_edicao):
        flash("Ação negada! Este projeto possui vínculos ativos com alunos ou professores.", "erro")
        return redirect(url_for('admin.admin_gestao_projetos'))
        
    # 2. Mudado para o nome real do seu repositório
    admin_repository.alternar_status_projeto(projeto_id, ativo=0)
    
    flash("Projeto desativado com sucesso.", "sucesso")
    return redirect(url_for('admin.admin_gestao_projetos'))

@admin_bp.route('/check-vinculos/<string:tipo>/<int:id>')
@requer_autenticacao
@requer_perfil('admin')
def admin_check_vinculos(tipo, id):
    vinculos = admin_repository.verificar_vinculos_alunos(tipo, id)
    return {"alunos": vinculos}

@admin_bp.route('/cursos', methods=['GET', 'POST'])
@requer_autenticacao
@requer_perfil('admin')
def admin_gestao_cursos():
    if request.method == 'POST':
        nome = request.form.get('nome_curso', '').strip()
        curso_id = request.form.get('curso_id') or None
        admin_repository.salvar_curso(nome, Size=curso_id)
        flash("Curso processado com sucesso!", "sucesso")

    cursos = admin_repository.listar_todos_cursos()
    return render_template('admin_cursos.html', cursos=cursos)

@admin_bp.route('/cursos/toggle/<int:id>')
@requer_autenticacao
@requer_perfil('admin')
def admin_toggle_curso(id):
    nome_curso = admin_repository.alternar_status_curso(id)
    if nome_curso:
        flash(f"Status do curso '{nome_curso}' modificado!", "sucesso")
    return redirect(url_for('admin.admin_gestao_cursos'))

@admin_bp.route('/projetos', methods=['GET', 'POST'])
@requer_autenticacao
@requer_perfil('admin')
def admin_gestao_projetos():
    id_edicao = obter_configuracao_global('edicao_ativa')

    if request.method == 'POST':
        nome = request.form.get('nome_projeto', '').strip()
        projeto_id = request.form.get('projeto_id') or None
        admin_repository.salvar_projeto(nome, projeto_id)
        flash("Projeto processado com sucesso!", "sucesso")

    projetos_cru = admin_repository.listar_todos_projetos()
    
    projetos = []
    for p in projetos_cru:
        proj_dict = dict(p) # Garante que aceita novas chaves
        proj_dict['possui_vinculos'] = admin_repository.verificar_vinculos_projeto(proj_dict['id'], id_edicao)
        projetos.append(proj_dict)

    return render_template('admin_projetos.html', projetos=projetos)

@admin_bp.route('/projetos/toggle/<int:id>')
@requer_autenticacao
@requer_perfil('admin')
def admin_toggle_projeto(id):
    id_edicao = obter_configuracao_global('edicao_ativa')
    
    with admin_repository.obter_conexao() as cursor:
        cursor.execute("SELECT ativo FROM projetos WHERE id = %s", (id,))
        proj = cursor.fetchone()
        
    if proj:
        if proj['ativo'] == 1:
            if admin_repository.verificar_vinculos_projeto(id, id_edicao):
                flash("Operação negada! Este projeto possui alunos inscritos ou professores vinculados.", "erro")
                return redirect(url_for('admin.admin_gestao_projetos'))
                
        nome_proj = admin_repository.alternar_status_projeto(id)
        if nome_proj:
            flash(f"Status do projeto '{nome_proj}' modificado!", "sucesso")
            
    return redirect(url_for('admin.admin_gestao_projetos'))

@admin_bp.route('/usuarios', methods=['GET'])
@requer_autenticacao
@requer_perfil('admin')
def admin_gestao_usuarios():
    tipo_filtro = request.args.get('tipo', '')
    letra_filtro = request.args.get('letra', '')
    busca_matricula = request.args.get('busca_matricula', '').strip()
    
    try:
        page = int(request.args.get('page', 1))
    except ValueError:
        page = 1
        
    limite_por_pagina = 50
    
    usuarios, total_resultados = admin_repository.listar_usuarios_painel_paginado(
        busca_matricula, tipo_filtro, letra_filtro, page, limite_por_pagina
    )
    
    total_paginas = math.ceil(total_resultados / limite_por_pagina)
    
    page_obj = {
        'page': page,
        'pages': total_paginas,
        'has_prev': page > 1,
        'prev_num': page - 1,
        'has_next': page < total_paginas,
        'next_num': page + 1
    }
    
    alfabeto = [chr(i) for i in range(65, 91)]
    return render_template(
        'admin_usuarios.html', 
        usuarios=usuarios, 
        tipo_filtro=tipo_filtro, 
        letra_filtro=letra_filtro, 
        busca_matricula=busca_matricula, 
        alfabeto=alfabeto,
        total_resultados=total_resultados,
        page_obj=page_obj
    )
    
@admin_bp.route('/usuarios/novo', methods=['GET', 'POST'])
@requer_autenticacao
@requer_perfil('admin')
def admin_novo_usuario():
    id_edicao = obter_configuracao_global('edicao_ativa')
    
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        tipo = request.form.get('tipo')
        matricula = request.form.get('identificador', '').strip()
        
        if not re.match(r'^[A-Za-zÀ-ÿ\s\d.-]+$', nome) or not matricula:
            flash("Erro de validação nos dados informados.", "erro")
        elif tipo == 'aluno' and (not matricula.isdigit() or len(matricula) != 10):
            flash("Para alunos, a matrícula deve conter exatamente 10 dígitos numéricos.", "erro")
        else:
            try:
                with admin_repository.obter_conexao() as cursor:
                    cursor.execute("SELECT id FROM usuarios WHERE login = %s", (matricula.lower(),))
                    existe_usuario = cursor.fetchone()

                if existe_usuario:
                    flash("Esta credencial/Login já existe no sistema.", "erro")
                else:
                    admin_repository.cadastrar_usuario_manual(
                        nome, matricula, tipo, generate_password_hash(matricula), str(uuid.uuid4()),
                        request.form.getlist('cursos_ids'), request.form.getlist('projetos_ids'),
                        request.form.getlist('inscricoes_ids'), id_edicao
                    )
                    flash(f"Usuário {nome} cadastrado com sucesso!", "sucesso")
                    return redirect(url_for('admin.admin_gestao_usuarios'))
            except Exception as e:
                flash(f"Erro ao salvar: {e}", "erro")
                
    cursos = admin_repository.listar_todos_cursos()
    projetos_filtrados = admin_repository.listar_projetos_ativos_por_edicao(id_edicao)
    
    return render_template('admin_form_usuario.html', cursos=cursos, projetos=projetos_filtrados, form_data=request.form, acao="Novo")

@admin_bp.route('/usuario/editar/<int:id_usuario>', methods=['GET', 'POST'])
@requer_autenticacao
@requer_perfil('admin')
def editar_usuario(id_usuario):
    id_edicao = obter_configuracao_global('edicao_ativa')
    form_data = {}
    
    with admin_repository.obter_conexao() as cursor:
        cursor.execute("""
            SELECT id, nome, login, email_institucional, tipo, status_conta 
            FROM usuarios 
            WHERE id = %s
        """, (id_usuario,))
        usuario = cursor.fetchone()

    if not usuario:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for('admin.admin_gestao_usuarios'))

    identificador_valor = ""
    with admin_repository.obter_conexao() as cursor:
        if usuario['tipo'] == 'aluno':
            cursor.execute("SELECT matricula FROM alunos WHERE id_usuario = %s", (id_usuario,))
            res = cursor.fetchone()
            if res:
                identificador_valor = res['matricula']
        else:
            cursor.execute("SELECT id_corporativo FROM professores WHERE id_usuario = %s", (id_usuario,))
            res = cursor.fetchone()
            if res:
                identificador_valor = res['id_corporativo']

    if request.method == 'POST':
        form_data = request.form
        
        try:
            id_curso_selecionado = form_data.get('curso_id')
            curso_final = int(id_curso_selecionado) if id_curso_selecionado else None

            admin_repository.atualizar_usuario_admin(
                id_usuario=id_usuario,
                nome=form_data.get('nome', '').strip(),
                tipo=usuario['tipo'],
                cursos_ids=curso_final,
                projetos_ids=form_data.getlist('projetos_ids'),
                inscricoes_ids=form_data.getlist('inscricoes_ids'),
                id_edicao=id_edicao,
                reset_senha=form_data.get('reset_senha', 'nao'),
                identificador=identificador_valor
            )
            flash("Usuário updated com sucesso!", "sucesso")
            return redirect(url_for('admin.admin_gestao_usuarios'))
        except Exception as e:
            flash(f"Erro ao atualizar usuário: {e}", "erro")

    cursos = admin_repository.listar_todos_cursos()
    projetos_filtrados = admin_repository.listar_projetos_ativos_por_edicao(id_edicao)

    lista_cursos_ids = admin_repository.obter_cursos_ids_do_usuario(id_usuario)       
    lista_inscricoes_ids = admin_repository.obter_inscricoes_ids_do_usuario(id_usuario) 
    lista_projetos_ids = admin_repository.obter_projetos_ids_do_usuario(id_usuario)     

    return render_template(
        'admin_form_usuario.html', 
        acao='Editar', 
        usuario=usuario, 
        identificador=identificador_valor,
        cursos=cursos,
        projetos=projetos_filtrados,
        lista_cursos_ids=lista_cursos_ids,
        lista_inscricoes_ids=lista_inscricoes_ids,
        lista_projetos_ids=lista_projetos_ids,
        form_data=form_data
    )

@admin_bp.route('/usuarios/toggle/<int:id>')
@requer_autenticacao
@requer_perfil('admin')
def admin_toggle_usuario(id):
    res = admin_repository.alternar_status_usuario(id)
    if res:
        status_txt = "Reativado" if res['novo_estado'] == 1 else "Ocultado"
        flash(f"Usuário {res['nome']} modificado para: {status_txt}.", "sucesso")
    return redirect(url_for('admin.admin_gestao_usuarios'))

@admin_bp.route('/importar', methods=['GET', 'POST'])
@requer_autenticacao
@requer_perfil('admin')
def admin_importar():
    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash('Nenhum arquivo enviado.', 'erro')
            return redirect(request.url)
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            flash('Nenhum arquivo selecionado.', 'erro')
            return redirect(request.url)

        try:
            conteudo = arquivo.read()
            try: 
                texto = conteudo.decode('utf-8-sig')
            except UnicodeDecodeError: 
                texto = conteudo.decode('latin-1')

            leitor = csv.reader(io.StringIO(texto), delimiter=';')
            linhas = list(leitor)
            if not linhas:
                flash('O arquivo está vazio.', 'erro')
                return redirect(request.url)

            if 'nome' in str(linhas[0]).lower() or 'matricula' in str(linhas[0]).lower() or 'ra' in str(linhas[0]).lower():
                linhas.pop(0)

            id_edicao = obter_configuracao_global('edicao_ativa')
            sucessos, erros = admin_repository.processar_importacao_csv(linhas, id_edicao)
            
            flash(f"Importação executada! Sucessos: {sucessos} | Duplicados ou Inválidos: {erros}", "sucesso" if sucessos > 0 else "info")
            return redirect(url_for('admin.admin_gestao_usuarios'))
        except Exception as e:
            flash(f"Falha de processamento: {e}", "erro")

    return render_template('admin_importar.html')

@admin_bp.route('/configuracoes', methods=['GET', 'POST'])
@requer_autenticacao
@requer_perfil('admin')
def admin_configuracoes():
    if request.method == 'POST':
        nova_edicao = request.form.get('nova_edicao', '').strip()
        
        if not nova_edicao:
            flash("Por favor, informe uma identificação de ciclo válida.", "erro")
            return redirect(url_for('admin.admin_configuracoes'))
            
        resultado = admin_repository.atualizar_edicao_ativa(nova_edicao)
        
        if resultado == 'sucesso':
            flash(f"Sucesso! Nova edição iniciada e configurada para: {nova_edicao}.", "sucesso")
        elif resultado == 'ja_ativa':
            flash(f"Atenção: O ciclo '{nova_edicao}' já é a edição corrente ativa no sistema.", "info")
        elif resultado == 'ja_existe':
            flash(f"Operação negada: A edição '{nova_edicao}' já foi utilizada anteriormente e não pode ser reativada.", "erro")
            
        return redirect(url_for('admin.admin_configuracoes'))
        
    id_edicao = obter_configuracao_global('edicao_ativa')
    texto_edicao = "Não configurado"
    
    if id_edicao:
        id_edicao_str = str(id_edicao).strip()
        with admin_repository.obter_conexao() as cursor:
            if id_edicao_str.isdigit():
                cursor.execute("SELECT nome_edicao FROM edicoes WHERE id = %s", (int(id_edicao_str),))
            else:
                cursor.execute("SELECT nome_edicao FROM edicoes WHERE nome_edicao = %s", (id_edicao_str,))
                
            resultado = cursor.fetchone()
            if resultado:
                texto_edicao = resultado['nome_edicao']
                
    return render_template('admin_configuracoes.html', edicao=texto_edicao)

@admin_bp.route('/exportar_presencas')
@requer_autenticacao
@requer_perfil('admin')
def exportar_presencas():
    id_edicao = obter_configuracao_global('edicao_ativa')
    relatorio = admin_repository.obter_relatorio_geral_presencas(id_edicao)

    nome_edicao_real = admin_repository.obter_nome_edicao_ativa()
    nome_edicao_texto = nome_edicao_real.replace(" ", "_").replace(".", "_")

    saida = StringIO(newline='')
    escritor = csv.writer(saida, delimiter=';')
    
    escritor.writerow(['Nome do Aluno', 'Matrícula', 'Curso', 'Projeto', 'Edição', 'Status'])

    for l in relatorio:
        escritor.writerow([
            l['nome'], 
            l['matricula'], 
            l['nome_curso'] if l.get('nome_curso') else "Não Informado", 
            l['nome_projeto'], 
            l['nome_edicao'], 
            l['status']
        ])

    resposta = make_response('\ufeff' + saida.getvalue())
    
    resposta.headers["Content-Disposition"] = f"attachment; filename=relatorio_geral_{nome_edicao_texto}.csv"
    resposta.headers["Content-Type"] = "text/csv; charset=utf-8"
    return resposta