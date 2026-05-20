from flask import Blueprint, render_template, session, redirect, url_for, flash, request, current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from utils.decorators import requer_autenticacao, requer_perfil
from repositories import aluno_repository, professor_repository
from db import obter_configuracao_global

aluno_bp = Blueprint('aluno', __name__, url_prefix='/aluno')

def obter_serializador():
    return URLSafeTimedSerializer(current_app.secret_key)

@aluno_bp.route('/dashboard')
@requer_autenticacao
@requer_perfil('aluno')
def aluno_dashboard():
    id_edicao = (obter_configuracao_global('edicao_ativa'))
    dados = aluno_repository.obter_dashboard_aluno(session['usuario_id'], id_edicao)
    
    aluno_dados = dados.get('aluno') if dados.get('aluno') else {}
    
    return render_template(
        'dashboard_aluno.html', 
        inscricoes=dados.get('inscricoes', []), 
        projetos_disponiveis=dados.get('projetos_disponiveis', []), 
        aluno=aluno_dados 
    )

@aluno_bp.route('/historico')
@requer_autenticacao
@requer_perfil('aluno')
def aluno_historico():
    id_edicao = (obter_configuracao_global('edicao_ativa'))
    historico = aluno_repository.obter_historico_aluno(session['usuario_id'], id_edicao)
    return render_template('aluno_historico.html', historico=historico)

@aluno_bp.route('/inscrever/<int:projeto_id>/<string:token>')
@requer_autenticacao
@requer_perfil('aluno')
def aluno_auto_inscrever(projeto_id, token):
    try:
        id_confirmado = obter_serializador().loads(token, salt='assinatura-presenca', max_age=8)
        if id_confirmado != projeto_id:
            flash("Token inválido.", "erro")
            return redirect(url_for('aluno.aluno_dashboard'))
    except (SignatureExpired, BadTimeSignature):
        flash("O QR Code expirou ou assinatura é inválida.", "erro")
        return redirect(url_for('aluno.aluno_dashboard'))

    id_edicao = (obter_configuracao_global('edicao_ativa'))
    aluno_repository.registrar_auto_presenca(session['usuario_id'], projeto_id, id_edicao)
    flash("Presença e inscrição confirmadas!", "sucesso")
    return redirect(url_for('aluno.aluno_dashboard'))

@aluno_bp.route('/inscrever_manual', methods=['POST'])
@requer_autenticacao
@requer_perfil('aluno')
def aluno_inscrever_manual():
    projeto_id = request.form.get('projeto_id')
    id_edicao = (obter_configuracao_global('edicao_ativa'))
    
    if not aluno_repository.verificar_inscricao_existente(session['usuario_id'], projeto_id, id_edicao):
        aluno_repository.realizar_inscricao_manual(session['usuario_id'], projeto_id, id_edicao)
        flash("Inscrição realizada com sucesso!", "sucesso")
    else:
        flash("Você já está cadastrado nesta atividade.", "info")
    return redirect(url_for('aluno.aluno_dashboard'))

@aluno_bp.route('/cancelar_inscricao/<int:projeto_id>', methods=['POST'])
@requer_autenticacao
@requer_perfil('aluno')
def aluno_cancelar_inscricao(projeto_id):
    id_edicao = (obter_configuracao_global('edicao_ativa'))
    afetados = aluno_repository.cancelar_inscricao_pendente(session['usuario_id'], projeto_id, id_edicao)
    
    if afetados > 0:
        flash("Inscrição cancelada com sucesso.", "sucesso")
    else:
        flash("Não é possível cancelar registros com presença confirmada.", "erro")
    return redirect(url_for('aluno.aluno_dashboard'))