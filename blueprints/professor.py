import csv
from utils.csv_export import linha_para_planilha
from flask import abort
from io import StringIO
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, make_response, current_app
from utils.decorators import requer_autenticacao, requer_perfil
from repositories import professor_repository
from db import obter_configuracao_global
from services.attendance_service import AttendanceService
from extensions import limiter

professor_bp = Blueprint('professor', __name__, url_prefix='/professor')


def projeto_supervisionado(projeto_id, curso_id):
    projeto = professor_repository.obter_projeto_por_id_e_professor(
        projeto_id, session['usuario_id'], curso_id
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

@professor_bp.route('/projeto/<int:projeto_id>/curso/<int:curso_id>')
@requer_autenticacao
@requer_perfil('professor')
def professor_projeto(projeto_id, curso_id):
    projeto = projeto_supervisionado(projeto_id, curso_id)
        
    id_edicao = obter_configuracao_global('edicao_ativa')
    alunos = professor_repository.listar_chamadas_supervisor(session['usuario_id'], id_edicao, projeto_id, curso_id)
    return render_template('professor_projeto.html', projeto=projeto, alunos=alunos)

@professor_bp.route('/projeto/<int:projeto_id>/curso/<int:curso_id>/scanner')
@requer_autenticacao
@requer_perfil('professor')
def professor_scanner(projeto_id, curso_id):
    projeto = projeto_supervisionado(projeto_id, curso_id)
    id_edicao = obter_configuracao_global('edicao_ativa')
    if not id_edicao:
        abort(409)
    return render_template(
        'professor_scanner.html', projeto=projeto, projeto_id=projeto_id, curso_id=curso_id, id_edicao=id_edicao
    )

@professor_bp.route('/projeto/<int:projeto_id>/curso/<int:curso_id>/registrar', methods=['POST'])
@limiter.limit(lambda: current_app.config['QR_RATE_LIMIT'])
@limiter.limit(lambda: current_app.config['QR_RATE_LIMIT'], key_func=lambda: f"conta:{session.get('usuario_id') or request.remote_addr}")
@requer_autenticacao
@requer_perfil('professor')
def registrar_presenca(projeto_id, curso_id):
    projeto_supervisionado(projeto_id, curso_id)
    token_qrcode = request.form.get('qr_token', '')
    id_edicao = request.form.get('edicao', '')
    if not id_edicao or not token_qrcode or len(token_qrcode) > 255:
        abort(400)
    try:
        resultado = AttendanceService(professor_repository).register_from_qr(
            token_qrcode, projeto_id, id_edicao, session['usuario_id'], curso_id
        )
        
        if resultado['status'] == 'edicao_indisponivel':
            flash("A edição ativa mudou ou está indisponível. Reabra o scanner.", "erro")
        elif resultado['status'] == 'sucesso':
            flash(f"Presença de {resultado['student']['nome']} computada com sucesso!", "sucesso")
        elif resultado['status'] == 'ja_presente':
            flash(f"Aviso: A presença de {resultado['student']['nome']} já havia sido registrada anteriormente.", "info")
        elif resultado['status'] == 'fora_do_escopo':
            flash('Credencial fora do curso selecionado.', 'erro')
        else:
            flash(f"Atenção: {resultado['student']['nome']} não possui inscrição ativa nesta atividade.", "erro")
    except PermissionError:
        abort(404)
    except ValueError:
        flash("QR Code inválido ou não pertence a um aluno ativo.", "erro")
    
    except Exception as e:
        current_app.logger.exception("Falha ao registrar presença", exc_info=e)
        flash("Não foi possível registrar a presença. Tente novamente.", "erro")
        
    return redirect(url_for('professor.professor_projeto', projeto_id=projeto_id, curso_id=curso_id))

@professor_bp.route('/projeto/<int:projeto_id>/curso/<int:curso_id>/exportar')
@requer_autenticacao
@requer_perfil('professor')
def professor_exportar_csv(projeto_id, curso_id):
    projeto_supervisionado(projeto_id, curso_id)
    edicao = obter_configuracao_global('edicao_ativa')
    alunos = professor_repository.listar_chamadas_supervisor(
        session['usuario_id'], edicao, projeto_id, curso_id
    )
    return csv_chamada(alunos, f'chamada_{projeto_id}_{curso_id}.csv')


@professor_bp.route('/exportar')
@requer_autenticacao
@requer_perfil('professor')
def professor_exportar_geral():
    edicao = obter_configuracao_global('edicao_ativa')
    alunos = professor_repository.listar_chamadas_supervisor(session['usuario_id'], edicao)
    return csv_chamada(alunos, 'chamadas_supervisionadas.csv', consolidado=True)


def csv_chamada(alunos, nome_arquivo, consolidado=False):
    saida = StringIO(newline='')
    escritor = csv.writer(saida, delimiter=';')
    cabecalho = ['Matrícula / RA', 'Nome do Aluno', 'Curso', 'Edição', 'Status da Presença']
    if consolidado:
        cabecalho = ['Projeto', 'Curso', 'Matrícula / RA', 'Nome do Aluno', 'Edição', 'Status da Presença']
    escritor.writerow(cabecalho)
    for aluno in alunos:
        status = 'Presente' if aluno['presenca'] == 1 else 'Pendente'
        if consolidado:
            linha = [aluno['nome_projeto'], aluno['nome_curso'], aluno['matricula'], aluno['nome']]
        else:
            linha = [aluno['matricula'], aluno['nome'], aluno['nome_curso']]
        escritor.writerow(linha_para_planilha(linha + [aluno['nome_edicao'], status]))

    resposta = make_response('\ufeff' + saida.getvalue())
    resposta.headers["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
    resposta.headers["Content-Type"] = "text/csv; charset=utf-8"
    resposta.headers["Cache-Control"] = "private, no-store"
    return resposta
