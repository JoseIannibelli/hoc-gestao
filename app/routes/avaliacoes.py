from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.avaliacao import (CicloAvaliacao, Avaliacao, Meta,
                                   STATUS_CICLO, TIPOS_AVALIACAO,
                                   STATUS_META, TIPOS_META, CRITERIOS)
from app.models.colaborador import Colaborador
from app.utils.acesso import requer_gestor, requer_lider_ou_gestor
from datetime import datetime

avaliacoes_bp = Blueprint('avaliacoes', __name__, url_prefix='/avaliacoes')


# ── Ciclos ─────────────────────────────────────────────────────────────────────

@avaliacoes_bp.route('/')
@login_required
def lista_ciclos():
    ciclos = CicloAvaliacao.query.order_by(CicloAvaliacao.created_at.desc()).all()
    return render_template('avaliacoes/lista_ciclos.html',
                           ciclos=ciclos, status_ciclo=STATUS_CICLO)


@avaliacoes_bp.route('/ciclo/novo', methods=['GET', 'POST'])
@login_required
@requer_gestor
def novo_ciclo():
    if request.method == 'POST':
        ciclo = CicloAvaliacao(
            nome=request.form.get('nome', '').strip(),
            descricao=request.form.get('descricao', '').strip(),
            status=request.form.get('status', 'aberto'),
            created_by=current_user.id,
        )
        di = request.form.get('data_inicio')
        df = request.form.get('data_fim')
        ciclo.data_inicio = datetime.strptime(di, '%Y-%m-%d').date() if di else None
        ciclo.data_fim    = datetime.strptime(df, '%Y-%m-%d').date() if df else None

        db.session.add(ciclo)
        db.session.commit()
        flash(f'Ciclo "{ciclo.nome}" criado!', 'success')
        return redirect(url_for('avaliacoes.detalhe_ciclo', id=ciclo.id))

    return render_template('avaliacoes/form_ciclo.html',
                           ciclo=None, status_ciclo=STATUS_CICLO)


@avaliacoes_bp.route('/ciclo/<int:id>')
@login_required
def detalhe_ciclo(id):
    ciclo = CicloAvaliacao.query.get_or_404(id)
    colaboradores = Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all()

    # Avaliações do ciclo
    avaliacoes = ciclo.avaliacoes.all()

    # Se for técnico, filtra só as suas
    if current_user.role == 'tecnico' and current_user.colaborador_id:
        avaliacoes = [a for a in avaliacoes
                      if a.avaliado_id == current_user.colaborador_id
                      or a.avaliador_id == current_user.id]

    return render_template('avaliacoes/detalhe_ciclo.html',
                           ciclo=ciclo,
                           avaliacoes=avaliacoes,
                           colaboradores=colaboradores,
                           tipos=TIPOS_AVALIACAO,
                           status_ciclo=STATUS_CICLO)


@avaliacoes_bp.route('/ciclo/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_gestor
def editar_ciclo(id):
    ciclo = CicloAvaliacao.query.get_or_404(id)

    if request.method == 'POST':
        ciclo.nome      = request.form.get('nome', '').strip()
        ciclo.descricao = request.form.get('descricao', '').strip()
        ciclo.status    = request.form.get('status', ciclo.status)
        di = request.form.get('data_inicio')
        df = request.form.get('data_fim')
        ciclo.data_inicio = datetime.strptime(di, '%Y-%m-%d').date() if di else None
        ciclo.data_fim    = datetime.strptime(df, '%Y-%m-%d').date() if df else None
        db.session.commit()
        flash('Ciclo atualizado!', 'success')
        return redirect(url_for('avaliacoes.detalhe_ciclo', id=ciclo.id))

    return render_template('avaliacoes/form_ciclo.html',
                           ciclo=ciclo, status_ciclo=STATUS_CICLO)


# ── Avaliações ─────────────────────────────────────────────────────────────────

@avaliacoes_bp.route('/ciclo/<int:ciclo_id>/criar', methods=['POST'])
@login_required
@requer_lider_ou_gestor
def criar_avaliacao(ciclo_id):
    ciclo = CicloAvaliacao.query.get_or_404(ciclo_id)
    avaliado_id = request.form.get('avaliado_id')
    tipo        = request.form.get('tipo', 'hetero')

    if not avaliado_id:
        flash('Selecione o colaborador a ser avaliado.', 'danger')
        return redirect(url_for('avaliacoes.detalhe_ciclo', id=ciclo_id))

    existente = Avaliacao.query.filter_by(
        ciclo_id=ciclo_id, avaliado_id=int(avaliado_id),
        avaliador_id=current_user.id, tipo=tipo
    ).first()

    if existente:
        flash('Avaliação já existe para este colaborador neste ciclo.', 'warning')
        return redirect(url_for('avaliacoes.detalhe_ciclo', id=ciclo_id))

    avaliacao = Avaliacao(
        ciclo_id=ciclo_id,
        avaliado_id=int(avaliado_id),
        avaliador_id=current_user.id,
        tipo=tipo,
        status='pendente',
    )
    db.session.add(avaliacao)
    db.session.commit()
    flash('Avaliação criada! Preencha agora.', 'success')
    return redirect(url_for('avaliacoes.preencher', id=avaliacao.id))


@avaliacoes_bp.route('/autoavaliar', methods=['POST'])
@login_required
def autoavaliar():
    """Colaborador inicia a própria autoavaliação."""
    if not current_user.colaborador_id:
        flash('Seu usuário não está vinculado a um colaborador.', 'warning')
        return redirect(url_for('avaliacoes.lista_ciclos'))

    ciclo_id = request.form.get('ciclo_id')
    if not ciclo_id:
        flash('Selecione o ciclo.', 'danger')
        return redirect(url_for('avaliacoes.lista_ciclos'))

    existente = Avaliacao.query.filter_by(
        ciclo_id=int(ciclo_id),
        avaliado_id=current_user.colaborador_id,
        avaliador_id=current_user.id,
        tipo='auto'
    ).first()

    if existente:
        return redirect(url_for('avaliacoes.preencher', id=existente.id))

    avaliacao = Avaliacao(
        ciclo_id=int(ciclo_id),
        avaliado_id=current_user.colaborador_id,
        avaliador_id=current_user.id,
        tipo='auto',
        status='pendente',
    )
    db.session.add(avaliacao)
    db.session.commit()
    return redirect(url_for('avaliacoes.preencher', id=avaliacao.id))


@avaliacoes_bp.route('/<int:id>/preencher', methods=['GET', 'POST'])
@login_required
def preencher(id):
    avaliacao = Avaliacao.query.get_or_404(id)

    # Permissão
    if avaliacao.avaliador_id != current_user.id and not current_user.is_gestor():
        flash('Sem permissão para preencher esta avaliação.', 'warning')
        return redirect(url_for('avaliacoes.lista_ciclos'))

    if avaliacao.status == 'enviada' and not current_user.is_gestor():
        flash('Esta avaliação já foi enviada e não pode ser editada.', 'info')
        return redirect(url_for('avaliacoes.ver', id=id))

    if request.method == 'POST':
        avaliacao.tecnico         = int(request.form.get('tecnico', 0) or 0)
        avaliacao.comunicacao     = int(request.form.get('comunicacao', 0) or 0)
        avaliacao.trabalho_equipe = int(request.form.get('trabalho_equipe', 0) or 0)
        avaliacao.proatividade    = int(request.form.get('proatividade', 0) or 0)
        avaliacao.entrega_prazo   = int(request.form.get('entrega_prazo', 0) or 0)
        avaliacao.pontos_fortes   = request.form.get('pontos_fortes', '').strip()
        avaliacao.pontos_melhoria = request.form.get('pontos_melhoria', '').strip()
        avaliacao.comentarios     = request.form.get('comentarios', '').strip()
        avaliacao.updated_at      = datetime.utcnow()

        acao = request.form.get('acao', 'rascunho')
        avaliacao.status = 'enviada' if acao == 'enviar' else 'rascunho'

        db.session.commit()
        msg = 'Avaliação enviada com sucesso!' if avaliacao.status == 'enviada' else 'Rascunho salvo.'
        flash(msg, 'success')
        return redirect(url_for('avaliacoes.detalhe_ciclo', id=avaliacao.ciclo_id))

    return render_template('avaliacoes/preencher.html',
                           avaliacao=avaliacao,
                           criterios=CRITERIOS)


@avaliacoes_bp.route('/<int:id>/ver')
@login_required
def ver(id):
    avaliacao = Avaliacao.query.get_or_404(id)

    # Somente avaliador, avaliado (se vinculado) ou gestor
    pode_ver = (
        current_user.is_gestor() or
        avaliacao.avaliador_id == current_user.id or
        (current_user.colaborador_id == avaliacao.avaliado_id and avaliacao.status == 'enviada')
    )
    if not pode_ver:
        flash('Sem permissão para visualizar esta avaliação.', 'warning')
        return redirect(url_for('avaliacoes.lista_ciclos'))

    return render_template('avaliacoes/ver.html',
                           avaliacao=avaliacao, criterios=CRITERIOS)


# ── Metas e PDI ────────────────────────────────────────────────────────────────

@avaliacoes_bp.route('/metas/<int:colab_id>')
@login_required
def metas_colaborador(colab_id):
    colaborador = Colaborador.query.get_or_404(colab_id)

    # Permissão
    if (current_user.role == 'tecnico'
            and current_user.colaborador_id != colab_id):
        flash('Sem permissão.', 'warning')
        return redirect(url_for('main.index'))

    metas = Meta.query.filter_by(colaborador_id=colab_id).order_by(Meta.created_at.desc()).all()
    ciclos = CicloAvaliacao.query.filter_by(status='aberto').all()

    return render_template('avaliacoes/metas.html',
                           colaborador=colaborador,
                           metas=metas,
                           ciclos=ciclos,
                           status_meta=STATUS_META,
                           tipos_meta=TIPOS_META)


@avaliacoes_bp.route('/metas/<int:colab_id>/nova', methods=['POST'])
@login_required
def nova_meta(colab_id):
    Colaborador.query.get_or_404(colab_id)

    prazo_str = request.form.get('prazo')
    ciclo_id  = request.form.get('ciclo_id') or None

    meta = Meta(
        colaborador_id=colab_id,
        titulo=request.form.get('titulo', '').strip(),
        descricao=request.form.get('descricao', '').strip(),
        tipo=request.form.get('tipo', 'meta'),
        prazo=datetime.strptime(prazo_str, '%Y-%m-%d').date() if prazo_str else None,
        ciclo_id=int(ciclo_id) if ciclo_id else None,
    )
    db.session.add(meta)
    db.session.commit()
    flash('Meta adicionada!', 'success')
    return redirect(url_for('avaliacoes.metas_colaborador', colab_id=colab_id))


@avaliacoes_bp.route('/metas/meta/<int:meta_id>/status', methods=['POST'])
@login_required
def atualizar_status_meta(meta_id):
    meta = Meta.query.get_or_404(meta_id)
    meta.status = request.form.get('status', meta.status)
    db.session.commit()
    flash('Status da meta atualizado!', 'success')
    return redirect(url_for('avaliacoes.metas_colaborador', colab_id=meta.colaborador_id))


@avaliacoes_bp.route('/metas/meta/<int:meta_id>/excluir', methods=['POST'])
@login_required
@requer_lider_ou_gestor
def excluir_meta(meta_id):
    meta = Meta.query.get_or_404(meta_id)
    colab_id = meta.colaborador_id
    db.session.delete(meta)
    db.session.commit()
    flash('Meta removida.', 'info')
    return redirect(url_for('avaliacoes.metas_colaborador', colab_id=colab_id))
