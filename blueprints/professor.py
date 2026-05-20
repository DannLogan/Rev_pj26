import csv
from io import StringIO
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, make_response
from utils.decorators import requer_autenticacao, requer_perfil
from repositories import professor_repository
from db import obter_configuracao_global

professor_bp = Blueprint('professor', __name__, url_prefix='/professor')

@professor_bp.route('/dashboard')
@requer_autenticacao
@requer_perfil('professor')
def professor_dashboard():
    # Coleta o ciclo como string pura (ex: '2026.2')
    id_edicao = obter_configuracao_global('edicao_ativa')
    projetos = professor_repository.obter_projetos_supervisor(session['usuario_id'], id_edicao)
    return render_template('dashboard_professor.html', projetos=projetos, edicao=id_edicao)

@professor_bp.route('/projeto/<int:projeto_id>')
@requer_autenticacao
@requer_perfil('professor')
def professor_projeto(projeto_id):
    projeto = professor_repository.obter_projeto_por_id(projeto_id)
    if not projeto:
        flash("Projeto não encontrado ou inexistente.", "erro")
        return redirect(url_for('professor.professor_dashboard'))
        
    id_edicao = obter_configuracao_global('edicao_ativa')
    alunos = professor_repository.listar_alunos_inscritos_no_projeto(projeto_id, id_edicao)
    return render_template('professor_projeto.html', projeto=projeto, alunos=alunos)

@professor_bp.route('/projeto/<int:projeto_id>/scanner')
@requer_autenticacao
@requer_perfil('professor')
def professor_scanner(projeto_id):
    projeto = professor_repository.obter_projeto_por_id(projeto_id)
    if not projeto:
        flash("Projeto inválido.", "erro")
        return redirect(url_for('professor.professor_dashboard'))
    return render_template('professor_scanner.html', projeto=projeto, projeto_id=projeto_id)

@professor_bp.route('/projeto/<int:projeto_id>/registrar/<string:token_qrcode>')
@requer_autenticacao
@requer_perfil('professor')
def registrar_presenca(projeto_id, token_qrcode):
    try:
        id_edicao = obter_configuracao_global('edicao_ativa')
        aluno = professor_repository.buscar_aluno_por_qr_token(token_qrcode)
        
        if not aluno:
            flash("QR Code inválido, expirado ou não pertence a um aluno ativo.", "erro")
            return redirect(url_for('professor.professor_projeto', projeto_id=projeto_id))
            
        # Executa a validação baseada nos três estados do repositório atualizado
        resultado = professor_repository.registrar_presenca_aluno(aluno['id'], projeto_id, id_edicao)
        
        if resultado == 'sucesso':
            flash(f"Presença de {aluno['nome']} computada com sucesso!", "sucesso")
        elif resultado == 'ja_presente':
            flash(f"Aviso: A presença de {aluno['nome']} já havia sido registrada anteriormente.", "info")
        else:
            flash(f"Atenção: {aluno['nome']} não possui inscrição ativa nesta atividade.", "erro")
            
    except Exception as e:
        flash(f"Falha operacional ao registrar: {e}", "erro")
        
    return redirect(url_for('professor.professor_projeto', projeto_id=projeto_id))

@professor_bp.route('/projeto/<int:projeto_id>/exportar')
@requer_autenticacao
@requer_perfil('professor')
def professor_exportar_csv(projeto_id):
    projeto = professor_repository.obter_projeto_por_id(projeto_id)
    if not projeto:
        flash("Operação inválida.", "erro")
        return redirect(url_for('professor.professor_dashboard'))
        
    id_edicao = obter_configuracao_global('edicao_ativa')
    alunos = professor_repository.listar_alunos_inscritos_no_projeto(projeto_id, id_edicao)

    saida = StringIO(newline='')
    escritor = csv.writer(saida, delimiter=';')
    escritor.writerow(['Matrícula / RA', 'Nome do Aluno', 'Status da Presença'])

    for a in alunos:
        status = 'Presente' if a['presenca'] == 1 else 'Pendente'
        escritor.writerow([a['matricula'], a['nome'], status])

    resposta = make_response('\ufeff' + saida.getvalue())
    nome_arquivo = f"chamada_{str(projeto['nome_projeto']).lower().replace(' ', '_')}.csv"
    
    resposta.headers["Content-Disposition"] = f"attachment; filename={nome_arquivo}"
    resposta.headers["Content-Type"] = "text/csv; charset=utf-8"
    return resposta