from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, send_file)
from flask_login import login_required, current_user
from app import db
from app.models.equipamento import (Equipamento, AlocacaoEquipamento,
                                     TIPOS_EQUIPAMENTO, STATUS_EQUIPAMENTO,
                                     ESTADOS_CONSERVACAO)
from app.models.colaborador import Colaborador
from app.utils.acesso import requer_gestor
from app.utils.gerar_termo_pdf import gerar_termo_pdf
from datetime import datetime, date

equipamentos_bp = Blueprint('equipamentos', __name__, url_prefix='/equipamentos')


def _parse_date(val):
    if val and val.strip():
        try:
            return datetime.strptime(val.strip(), '%Y-%m-%d').date()
        except ValueError:
            return None
    return None


# ── Lista geral ────────────────────────────────────────────────────────────────

@equipamentos_bp.route('/')
@login_required
def lista():
    # Colaborador comum → redireciona para "meus equipamentos"
    if not current_user.is_gestor() and not current_user.is_lider():
        return redirect(url_for('equipamentos.meus'))

    filtro_status = request.args.get('status', '')
    filtro_tipo   = request.args.get('tipo', '')
    q             = request.args.get('q', '').strip()

    query = Equipamento.query
    if filtro_status:
        query = query.filter_by(status=filtro_status)
    if filtro_tipo:
        query = query.filter_by(tipo=filtro_tipo)
    if q:
        like = f'%{q}%'
        query = query.filter(
            db.or_(
                Equipamento.marca.ilike(like),
                Equipamento.modelo.ilike(like),
                Equipamento.numero_serie.ilike(like),
                Equipamento.numero_patrimonio.ilike(like),
            )
        )

    equipamentos = query.order_by(Equipamento.tipo, Equipamento.marca).all()

    # Contadores para cards de resumo
    contadores = {s[0]: Equipamento.query.filter_by(status=s[0]).count()
                  for s in STATUS_EQUIPAMENTO}

    return render_template('equipamentos/lista.html',
                           equipamentos=equipamentos,
                           contadores=contadores,
                           filtro_status=filtro_status,
                           filtro_tipo=filtro_tipo,
                           q=q,
                           tipos=TIPOS_EQUIPAMENTO,
                           status_list=STATUS_EQUIPAMENTO)


# ── Meus equipamentos (colaborador) ───────────────────────────────────────────

@equipamentos_bp.route('/meus')
@login_required
def meus():
    colaborador_id = current_user.colaborador_id
    if not colaborador_id:
        flash('Seu usuário não está vinculado a um colaborador.', 'warning')
        return redirect(url_for('main.index'))

    alocacoes_ativas = AlocacaoEquipamento.query.filter_by(
        colaborador_id=colaborador_id, ativo=True
    ).all()
    historico = AlocacaoEquipamento.query.filter_by(
        colaborador_id=colaborador_id, ativo=False
    ).order_by(AlocacaoEquipamento.data_devolucao.desc()).all()

    return render_template('equipamentos/meus.html',
                           alocacoes_ativas=alocacoes_ativas,
                           historico=historico)


# ── Criar ──────────────────────────────────────────────────────────────────────

@equipamentos_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@requer_gestor
def novo():
    if request.method == 'POST':
        eq = Equipamento(
            tipo              = request.form.get('tipo', 'outros'),
            marca             = request.form.get('marca', '').strip() or None,
            modelo            = request.form.get('modelo', '').strip() or None,
            numero_serie      = request.form.get('numero_serie', '').strip() or None,
            numero_patrimonio = request.form.get('numero_patrimonio', '').strip() or None,
            descricao         = request.form.get('descricao', '').strip() or None,
            status            = 'disponivel',
            data_aquisicao    = _parse_date(request.form.get('data_aquisicao')),
        )
        valor_str = request.form.get('valor', '').strip().replace(',', '.')
        if valor_str:
            try:
                eq.valor = float(valor_str)
            except ValueError:
                pass

        db.session.add(eq)
        db.session.commit()
        flash(f'Equipamento "{eq.nome_completo}" cadastrado com sucesso!', 'success')
        return redirect(url_for('equipamentos.detalhe', id=eq.id))

    return render_template('equipamentos/form.html',
                           equipamento=None,
                           tipos=TIPOS_EQUIPAMENTO,
                           titulo='Novo Equipamento')


# ── Editar ─────────────────────────────────────────────────────────────────────

@equipamentos_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_gestor
def editar(id):
    eq = Equipamento.query.get_or_404(id)

    if request.method == 'POST':
        eq.tipo              = request.form.get('tipo', eq.tipo)
        eq.marca             = request.form.get('marca', '').strip() or None
        eq.modelo            = request.form.get('modelo', '').strip() or None
        eq.numero_serie      = request.form.get('numero_serie', '').strip() or None
        eq.numero_patrimonio = request.form.get('numero_patrimonio', '').strip() or None
        eq.descricao         = request.form.get('descricao', '').strip() or None
        eq.status            = request.form.get('status', eq.status)
        eq.data_aquisicao    = _parse_date(request.form.get('data_aquisicao'))

        valor_str = request.form.get('valor', '').strip().replace(',', '.')
        eq.valor  = float(valor_str) if valor_str else None

        eq.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Equipamento atualizado com sucesso!', 'success')
        return redirect(url_for('equipamentos.detalhe', id=eq.id))

    return render_template('equipamentos/form.html',
                           equipamento=eq,
                           tipos=TIPOS_EQUIPAMENTO,
                           status_list=STATUS_EQUIPAMENTO,
                           titulo='Editar Equipamento')


# ── Detalhe ────────────────────────────────────────────────────────────────────

@equipamentos_bp.route('/<int:id>')
@login_required
def detalhe(id):
    if not current_user.is_gestor() and not current_user.is_lider():
        flash('Acesso restrito.', 'warning')
        return redirect(url_for('equipamentos.meus'))

    eq = Equipamento.query.get_or_404(id)
    colaboradores = Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all()
    historico = eq.alocacoes.all()

    return render_template('equipamentos/detalhe.html',
                           eq=eq,
                           colaboradores=colaboradores,
                           historico=historico,
                           hoje=date.today(),
                           estados=ESTADOS_CONSERVACAO)


# ── Alocar ─────────────────────────────────────────────────────────────────────

@equipamentos_bp.route('/<int:id>/alocar', methods=['POST'])
@login_required
@requer_gestor
def alocar(id):
    eq = Equipamento.query.get_or_404(id)

    if eq.status == 'alocado':
        flash('Equipamento já está alocado. Registre a devolução antes de realocar.', 'warning')
        return redirect(url_for('equipamentos.detalhe', id=id))

    if eq.status in ('manutencao', 'descartado'):
        flash(f'Equipamento com status "{eq.status_info["label"]}" não pode ser alocado.', 'warning')
        return redirect(url_for('equipamentos.detalhe', id=id))

    colaborador_id = request.form.get('colaborador_id', type=int)
    data_entrega   = _parse_date(request.form.get('data_entrega'))
    data_prev_dev  = _parse_date(request.form.get('data_prevista_devolucao'))
    estado_entrega = request.form.get('estado_entrega', 'bom')
    observacoes    = request.form.get('observacoes', '').strip() or None

    if not colaborador_id or not data_entrega:
        flash('Colaborador e data de entrega são obrigatórios.', 'danger')
        return redirect(url_for('equipamentos.detalhe', id=id))

    colaborador = Colaborador.query.get_or_404(colaborador_id)

    aloc = AlocacaoEquipamento(
        equipamento_id          = eq.id,
        colaborador_id          = colaborador.id,
        data_entrega            = data_entrega,
        data_prevista_devolucao = data_prev_dev,
        estado_entrega          = estado_entrega,
        observacoes             = observacoes,
        ativo                   = True,
    )
    eq.status = 'alocado'
    eq.updated_at = datetime.utcnow()

    db.session.add(aloc)
    db.session.commit()

    flash(f'Equipamento alocado para {colaborador.nome} com sucesso!', 'success')
    return redirect(url_for('equipamentos.detalhe', id=id))


# ── Devolver ───────────────────────────────────────────────────────────────────

@equipamentos_bp.route('/devolucao/<int:aloc_id>', methods=['POST'])
@login_required
@requer_gestor
def devolver(aloc_id):
    aloc = AlocacaoEquipamento.query.get_or_404(aloc_id)
    eq   = aloc.equipamento

    data_dev         = _parse_date(request.form.get('data_devolucao')) or date.today()
    estado_devolucao = request.form.get('estado_devolucao', 'bom')
    obs_dev          = request.form.get('observacoes_dev', '').strip()

    aloc.data_devolucao    = data_dev
    aloc.estado_devolucao  = estado_devolucao
    aloc.ativo             = False
    if obs_dev:
        aloc.observacoes = (aloc.observacoes or '') + f'\n[Devolução] {obs_dev}'
    aloc.updated_at = datetime.utcnow()

    eq.status     = 'disponivel'
    eq.updated_at = datetime.utcnow()

    db.session.commit()
    flash(f'Devolução de {aloc.colaborador.nome} registrada. '
          f'Equipamento disponível novamente.', 'success')
    return redirect(url_for('equipamentos.detalhe', id=eq.id))


# ── Gerar Termo PDF ────────────────────────────────────────────────────────────

@equipamentos_bp.route('/termo/<int:aloc_id>.pdf')
@login_required
def termo_pdf(aloc_id):
    aloc = AlocacaoEquipamento.query.get_or_404(aloc_id)

    # Colaborador só acessa o próprio termo
    if not current_user.is_gestor() and not current_user.is_lider():
        if current_user.colaborador_id != aloc.colaborador_id:
            flash('Acesso não autorizado.', 'danger')
            return redirect(url_for('equipamentos.meus'))

    buffer = gerar_termo_pdf(aloc)
    nome_arquivo = (f'Termo_Responsabilidade_{aloc.colaborador.nome.replace(" ", "_")}'
                    f'_{aloc.equipamento.tipo}_{aloc.id:04d}.pdf')

    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=False,          # abre no browser para visualizar/imprimir
        download_name=nome_arquivo,
    )
