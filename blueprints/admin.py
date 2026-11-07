from services.supervision_service import parse_supervision_pairs
import csv
from utils.csv_export import linha_para_planilha
import io
import re
import uuid
import secrets
import math
from io import StringIO
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, make_response, current_app
from werkzeug.security import generate_password_hash
from utils.decorators import requer_autenticacao, requer_perfil
from repositories import admin_repository, auth_repository
from db import obter_configuracao_global

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def mostrar_credenciais(credenciais, erros=0):
    resposta = make_response(render_template(
        'admin_credenciais.html', credenciais=credenciais, erros=erros
    ))
    resposta.headers['Cache-Control'] = 'private, no-store'
    return resposta

@admin_bp.route('/painel')
@requer_autenticacao
@requer_perfil('admin')
def admin_painel():
    return render_template('painel_admin.html')

@admin_bp.route('/admin/projeto/<int:projeto_id>/desativar', methods=['POST'])
@requer_autenticacao
@requer_perfil('admin')
def desativar_projeto(projeto_id):
    return modificar_status_projeto(projeto_id, desativar=True)


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

        admin_repository.salvar_curso(nome, curso_id=curso_id)
        flash("Curso processado com sucesso!", "sucesso")
        
        return redirect(url_for('admin.admin_gestao_cursos'))

    cursos = admin_repository.listar_todos_cursos()
    return render_template('admin_cursos.html', cursos=cursos)

@admin_bp.route('/cursos/toggle/<int:id>', methods=['POST'])
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

    projetos = admin_repository.listar_projetos_com_vinculos(id_edicao)
    return render_template('admin_projetos.html', projetos=projetos)

@admin_bp.route('/projetos/toggle/<int:id>', methods=['POST'])
@requer_autenticacao
@requer_perfil('admin')
def admin_toggle_projeto(id):
    return modificar_status_projeto(id)


def modificar_status_projeto(id_projeto, *, desativar=False):
    resultado = admin_repository.alternar_status_projeto(id_projeto, desativar=desativar)
    if resultado == 'vinculado':
        flash("Operação negada. O projeto possui inscrições ou supervisores.", "erro")
    elif resultado == 'sucesso':
        flash("Status do projeto atualizado.", "sucesso")
    else:
        flash("Projeto não encontrado.", "erro")
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
        
        if tipo != 'aluno':
            matricula = ""

        if tipo not in {'aluno', 'professor', 'admin'}:
            flash("Perfil inválido.", "erro")
        elif not re.match(r'^[A-Za-zÀ-ÿ\s\d.-]+$', nome):
            flash("Erro de validação: O nome contém caracteres inválidos.", "erro")
        elif tipo == 'aluno' and (not matricula.isdigit() or len(matricula) != 10):
            flash("Para alunos, a matrícula deve conter exatamente 10 dígitos numéricos.", "erro")
        else:
            try:
                existe_usuario = False
                if tipo == 'aluno':
                    existe_usuario = admin_repository.buscar_usuario_por_login(matricula.lower())

                if existe_usuario:
                    flash("Esta credencial/Login já existe no sistema.", "erro")
                else:
                    senha_provisoria = secrets.token_urlsafe(18)
                    login_gerado = admin_repository.cadastrar_usuario_manual(
                        nome, matricula, tipo, generate_password_hash(senha_provisoria), str(uuid.uuid4()),
                        request.form.getlist('cursos_ids'), parse_supervision_pairs(request.form.getlist('supervisoes')) if tipo == 'professor' else [],
                        request.form.getlist('inscricoes_ids'), request.form.get('edicao') or None
                    )
                    
                    return mostrar_credenciais([(login_gerado, senha_provisoria)])
            except ValueError as erro:
                flash(str(erro), "erro")
                return redirect(request.path)
            except Exception:
                current_app.logger.exception("Erro ao salvar")
                flash("Não foi possível salvar o usuário.", "erro")
                
    cursos = admin_repository.listar_todos_cursos()
    
    # 🚀 CORREÇÃO AQUI: Removeu o id_edicao dos parênteses para bater com o repositório global
    projetos_filtrados = admin_repository.listar_projetos_ativos_por_edicao()
    
    # 🚀 CORREÇÃO DUPLA: Passa tanto projetos quanto projects para blindar o Jinja2 do HTML
    return render_template('admin_form_usuario.html', cursos=cursos, projetos=projetos_filtrados, projects=projetos_filtrados, form_data=request.form, acao="Novo", id_edicao=id_edicao)

@admin_bp.route('/usuario/editar/<int:id_usuario>', methods=['GET', 'POST'])
@requer_autenticacao
@requer_perfil('admin')
def editar_usuario(id_usuario):
    id_edicao = obter_configuracao_global('edicao_ativa')
        
    form_data = {}
    
    usuario = admin_repository.obter_usuario_admin(id_usuario)

    if not usuario:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for('admin.admin_gestao_usuarios'))

    identificador_valor = admin_repository.obter_identificador_usuario(id_usuario, usuario['tipo'])

    if request.method == 'POST':
        form_data = request.form
        
        try:
            id_curso_selecionado = form_data.get('curso_id')
            curso_final = int(id_curso_selecionado) if id_curso_selecionado else None

            senha_provisoria = secrets.token_urlsafe(18) if form_data.get('reset_senha') == 'sim' else None
            admin_repository.atualizar_usuario_admin(
                id_usuario=id_usuario,
                nome=form_data.get('nome', '').strip(),
                tipo=usuario['tipo'],
                cursos_ids=curso_final,
                supervisoes=parse_supervision_pairs(form_data.getlist('supervisoes')) if usuario['tipo'] == 'professor' else [],
                inscricoes_ids=form_data.getlist('inscricoes_ids'),
                id_edicao=form_data.get('edicao') or None,
                senha_provisoria_hash=generate_password_hash(senha_provisoria) if senha_provisoria else None,
                identificador=identificador_valor
            )
            if senha_provisoria:
                return mostrar_credenciais([(identificador_valor, senha_provisoria)])
            flash("Usuário updated com sucesso!", "sucesso")
            return redirect(url_for('admin.admin_gestao_usuarios'))
        except ValueError as erro:
            flash(str(erro), "erro")
            return redirect(request.path)
        except Exception:
            current_app.logger.exception("Erro ao atualizar usuário")
            flash("Não foi possível atualizar o usuário.", "erro")

    cursos = admin_repository.listar_todos_cursos()
    
    # 🚀 CORREÇÃO AQUI: Removeu o id_edicao dos parênteses
    projetos_filtrados = admin_repository.listar_projetos_ativos_por_edicao()

    lista_cursos_ids = admin_repository.obter_cursos_ids_do_usuario(id_usuario)      
    lista_inscricoes_ids = admin_repository.obter_lista_inscricoes_aluno(id_usuario, id_edicao)
    supervisoes_atuais = admin_repository.obter_supervisoes_do_usuario(id_usuario)

    return render_template(
        'admin_form_usuario.html', 
        acao='Editar', 
        usuario=usuario, 
        identificador=identificador_valor,
        cursos=cursos,
        projetos=projetos_filtrados,
        projects=projetos_filtrados,
        lista_cursos_ids=lista_cursos_ids,
        lista_inscricoes_ids=lista_inscricoes_ids,
        supervisoes_atuais=supervisoes_atuais,
        id_edicao=id_edicao,
        form_data=form_data
    )
        
@admin_bp.route('/usuarios/toggle/<int:id>', methods=['POST'])
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
            conteudo = arquivo.read(2 * 1024 * 1024 + 1)
            if len(conteudo) > 2 * 1024 * 1024:
                flash("O CSV deve ter no máximo 2 MiB.", "erro")
                return redirect(request.url)
            try: 
                texto = conteudo.decode('utf-8-sig')
            except UnicodeDecodeError: 
                texto = conteudo.decode('latin-1')

            leitor = csv.reader(io.StringIO(texto), delimiter=';')
            linhas = list(leitor)
            if not linhas:
                flash('O arquivo está vazio.', 'erro')
                return redirect(request.url)

            if linhas[0] and linhas[0][0].strip().casefold() in {'matricula', 'matrícula', 'ra'}:
                linhas.pop(0)
            if len(linhas) > 5000:
                flash("O CSV deve ter no máximo 5.000 registros.", "erro")
                return redirect(request.url)

            id_edicao = obter_configuracao_global('edicao_ativa')
            credenciais, erros = admin_repository.processar_importacao_csv(linhas, id_edicao)
            return mostrar_credenciais(credenciais, erros)
        except Exception as e:
            current_app.logger.exception("Falha de processamento")
            flash("Não foi possível processar o arquivo.", "erro")

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
        texto_edicao = admin_repository.obter_nome_edicao(id_edicao_str)
                
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
        linha = [
            l['nome'], 
            l['matricula'], 
            l['nome_curso'] if l.get('nome_curso') else "Não Informado", 
            l['nome_projeto'], 
            l['nome_edicao'], 
            l['status']
        ]
        escritor.writerow(linha_para_planilha(linha) if request.args.get("formato") == "planilha" else linha)

    resposta = make_response('\ufeff' + saida.getvalue())
    
    resposta.headers["Content-Disposition"] = f"attachment; filename=relatorio_geral_{nome_edicao_texto}.csv"
    resposta.headers["Content-Type"] = "text/csv; charset=utf-8"
    return resposta
