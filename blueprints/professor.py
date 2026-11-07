import csv
from flask import abort
from io import StringIO
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, make_response, current_app
from utils.decorators import requer_autenticacao, requer_perfil
from repositories import professor_repository
from db import obter_configuracao_global
from services.attendance_service import AttendanceService
from extensions import limiter

professor_bp = Blueprint('professor', __name__, url_prefix='/professor')


def projeto_supervisionado(projeto_id):
    projeto = professor_repository.obter_projeto_por_id_e_professor(
        projeto_id, session['usuario_id']
    )
    if projeto is None:
        abort(404)
    return projeto

@professor_bp.route('/dashboard')
@requer_autenticacao
@requer_perfil('professor')
def professor_dashboard():
    id_edicao = obter_configuracao_global('edicao_ativa')
    
    nome_exibicao_edicao = professor_repository.obter_nome_edicao(id_edicao) if id_edicao else "Não configurado"

    projetos = professor_repository.obter_projetos_supervisor(session['usuario_id'], id_edicao)
    return render_template('dashboard_professor.html', projetos=projetos, edicao=nome_exibicao_edicao)

@professor_bp.route('/projeto/<int:projeto_id>')
@requer_autenticacao
@requer_perfil('professor')
def professor_projeto(projeto_id):
    projeto = projeto_supervisionado(projeto_id)
        
    id_edicao = obter_configuracao_global('edicao_ativa')
    alunos = professor_repository.listar_alunos_inscritos_no_projeto(projeto_id, id_edicao)
    return render_template('professor_projeto.html', projeto=projeto, alunos=alunos)

@professor_bp.route('/projeto/<int:projeto_id>/scanner')
@requer_autenticacao
@requer_perfil('professor')
def professor_scanner(projeto_id):
    projeto = projeto_supervisionado(projeto_id)
    return render_template('professor_scanner.html', projeto=projeto, projeto_id=projeto_id)

@professor_bp.route('/projeto/<int:projeto_id>/registrar', methods=['POST'])
@limiter.limit(lambda: __import__('flask').current_app.config['QR_RATE_LIMIT'])
@requer_autenticacao
@requer_perfil('professor')
def registrar_presenca(projeto_id):
    projeto_supervisionado(projeto_id)
    token_qrcode = request.form.get('qr_token', '')
    if not token_qrcode or len(token_qrcode) > 255:
        abort(400)
    try:
        id_edicao = obter_configuracao_global('edicao_ativa')
        resultado = AttendanceService(professor_repository).register_from_qr(
            token_qrcode, projeto_id, id_edicao, session['usuario_id']
        )
        
        if resultado['status'] == 'sucesso':
            flash(f"Presença de {resultado['student']['nome']} computada com sucesso!", "sucesso")
        elif resultado['status'] == 'ja_presente':
            flash(f"Aviso: A presença de {resultado['student']['nome']} já havia sido registrada anteriormente.", "info")
        else:
            flash(f"Atenção: {resultado['student']['nome']} não possui inscrição ativa nesta atividade.", "erro")
    except PermissionError:
        abort(404)
    except ValueError:
        flash("QR Code inválido ou não pertence a um aluno ativo.", "erro")
    
    except Exception as e:
        current_app.logger.exception("Falha ao registrar presença", exc_info=e)
        flash("Não foi possível registrar a presença. Tente novamente.", "erro")
        
    return redirect(url_for('professor.professor_projeto', projeto_id=projeto_id))

@professor_bp.route('/projeto/<int:projeto_id>/exportar')
@requer_autenticacao
@requer_perfil('professor')
def professor_exportar_csv(projeto_id):
    projeto = projeto_supervisionado(projeto_id)
        
    id_edicao = obter_configuracao_global('edicao_ativa')
    alunos = professor_repository.listar_alunos_inscritos_no_projeto(projeto_id, id_edicao)

    saida = StringIO(newline='')
    escritor = csv.writer(saida, delimiter=';')
    
    escritor.writerow(['Matrícula / RA', 'Nome do Aluno', 'Curso', 'Edição', 'Status da Presença'])

    for a in alunos:
        status = 'Presente' if a['presenca'] == 1 else 'Pendente'
        escritor.writerow([
            a['matricula'], 
            a['nome'], 
            a.get('nome_curso', 'Não Informado'), 
            a.get('nome_edicao', 'Não Informada'), 
            status
        ])

    resposta = make_response('\ufeff' + saida.getvalue())
    nome_arquivo = f"chamada_{str(projeto['nome_projeto']).lower().replace(' ', '_')}.csv"
    
    resposta.headers["Content-Disposition"] = f"attachment; filename={nome_arquivo}"
    resposta.headers["Content-Type"] = "text/csv; charset=utf-8"
    return resposta
