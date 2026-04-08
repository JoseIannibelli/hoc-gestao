from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request)
from flask_login import login_required, current_user
from app import db
from app.models.comunicado import Comunicado, TIPOS_COMUNICADO
from app.utils.acesso import requer_admin
from datetime import datetime

comunicados_bp = Blueprint('comunicados', __name__, url_prefix='/comunicados')


@comunicados_bp.route('/')
@login_required
@requer_admin
def lista():
    todos = (Comunicado.query
             .order_by(Comunicado.fixado.desc(), Comunicado.created_at.desc())
             .all())
    return render_template('comunicados/lista.html', comunicados=todos)


@comunicados_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@requer_admin
def novo():
    if request.method == 'POST':
        titulo    = request.form.get('titulo', '').strip()
        corpo     = request.form.get('corpo', '').strip()
        tipo      = request.form.get('tipo', 'informativo')
        fixado    = request.form.get('fixado') == '1'
        ativo     = request.form.get('ativo', '1') == '1'
        expira_em = request.form.get('expira_em', '').strip() or None

        if not titulo or not corpo:
            flash('Título e conteúdo são obrigatórios.', 'danger')
        else:
            c = Comunicado(
                titulo     = titulo,
                corpo      = corpo,
                tipo       = tipo,
                fixado     = fixado,
                ativo      = ativo,
                expira_em  = (datetime.strptime(expira_em, '%Y-%m-%d').date()
                              if expira_em else None),
                criado_por = current_user.id,
            )
            db.session.add(c)
            db.session.commit()
            flash('Comunicado publicado com sucesso!', 'success')
            return redirect(url_for('comunicados.lista'))

    return render_template('comunicados/form.html',
                           comunicado=None,
                           tipos=TIPOS_COMUNICADO,
                           titulo_pagina='Novo Comunicado')


@comunicados_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_admin
def editar(id):
    c = Comunicado.query.get_or_404(id)

    if request.method == 'POST':
        titulo    = request.form.get('titulo', '').strip()
        corpo     = request.form.get('corpo', '').strip()
        tipo      = request.form.get('tipo', 'informativo')
        fixado    = request.form.get('fixado') == '1'
        ativo     = request.form.get('ativo', '1') == '1'
        expira_em = request.form.get('expira_em', '').strip() or None

        if not titulo or not corpo:
            flash('Título e conteúdo são obrigatórios.', 'danger')
        else:
            c.titulo     = titulo
            c.corpo      = corpo
            c.tipo       = tipo
            c.fixado     = fixado
            c.ativo      = ativo
            c.expira_em  = (datetime.strptime(expira_em, '%Y-%m-%d').date()
                            if expira_em else None)
            c.updated_at = datetime.utcnow()
            db.session.commit()
            flash('Comunicado atualizado.', 'success')
            return redirect(url_for('comunicados.lista'))

    return render_template('comunicados/form.html',
                           comunicado=c,
                           tipos=TIPOS_COMUNICADO,
                           titulo_pagina='Editar Comunicado')


@comunicados_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
@requer_admin
def excluir(id):
    c = Comunicado.query.get_or_404(id)
    db.session.delete(c)
    db.session.commit()
    flash('Comunicado removido.', 'info')
    return redirect(url_for('comunicados.lista'))


@comunicados_bp.route('/<int:id>/toggle', methods=['POST'])
@login_required
@requer_admin
def toggle_ativo(id):
    c = Comunicado.query.get_or_404(id)
    c.ativo = not c.ativo
    c.updated_at = datetime.utcnow()
    db.session.commit()
    estado = 'ativado' if c.ativo else 'desativado'
    flash(f'Comunicado {estado}.', 'info')
    return redirect(url_for('comunicados.lista'))
