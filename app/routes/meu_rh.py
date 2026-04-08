import os
import uuid
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app, abort, send_from_directory)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.colaborador import Colaborador, AREAS, SENIORIDADES, REGIMES, ESTADOS_BR
from app.models.contracheque import Contracheque, MESES
from app.models.ferias import PeriodoAquisitivo, SolicitacaoFerias, STATUS_SOLICITACAO
from app.utils.acesso import requer_gestor
from datetime import datetime, date

meu_rh_bp = Blueprint('meu_rh', __name__, url_prefix='/meu-rh')

ALLOWED_IMG  = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_PDF  = {'pdf'}


def _colab_do_usuario():
    """Retorna o Colaborador vinculado ao usuário logado ou None."""
    if not current_user.colaborador_id:
        return None
    return Colaborador.query.get(current_user.colaborador_id)


def _requer_colab():
    """Aborta 403 se o usuário não tiver perfil de colaborador vinculado."""
    if not current_user.colaborador_id:
        abort(403)


# ── Dados Cadastrais ──────────────────────────────────────────────────────────

@meu_rh_bp.route('/dados', methods=['GET', 'POST'])
@login_required
def dados_cadastrais():
    _requer_colab()
    colab = _colab_do_usuario()
    if not colab:
        flash('Perfil não encontrado. Solicite ao gestor.', 'warning')
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        # Campos permitidos para autoedição
        def _v(key):
            v = request.form.get(key, '') or ''
            return '' if v.strip().lower() == 'none' else v.strip()

        # Foto
        foto_file = request.files.get('foto')
        if foto_file and foto_file.filename:
            ext = foto_file.filename.rsplit('.', 1)[-1].lower()
            if ext in ALLOWED_IMG:
                fname = f"{uuid.uuid4().hex}.{ext}"
                upload_dir = os.path.join(current_app.root_path,
                                          'static', 'uploads', 'colaboradores')
                os.makedirs(upload_dir, exist_ok=True)
                foto_file.save(os.path.join(upload_dir, fname))
                colab.foto = fname

        colab.telefone  = _v('telefone')
        colab.cidade    = _v('cidade')
        colab.estado    = _v('estado')
        colab.linkedin  = _v('linkedin')
        colab.bio       = _v('bio')
        colab.updated_at = datetime.utcnow()

        # Data de nascimento (opcional, auto-editável)
        data_nasc = request.form.get('data_nascimento', '').strip()
        colab.data_nascimento = (datetime.strptime(data_nasc, '%Y-%m-%d').date()
                                 if data_nasc else colab.data_nascimento)

        try:
            db.session.commit()
            flash('Dados atualizados com sucesso!', 'success')
            return redirect(url_for('meu_rh.dados_cadastrais'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Erro ao salvar dados cadastrais: {e}')
            flash('Erro ao salvar. Tente novamente.', 'danger')

    # Limpa "None" string ao exibir
    for field in ('telefone', 'cidade', 'linkedin', 'bio'):
        val = getattr(colab, field, None)
        if val and str(val).strip().lower() == 'none':
            setattr(colab, field, '')

    return render_template('meu_rh/dados_cadastrais.html',
                           colab=colab,
                           areas=AREAS,
                           senioridades=SENIORIDADES,
                           regimes=REGIMES,
                           estados=ESTADOS_BR)


# ── Contracheque ──────────────────────────────────────────────────────────────

@meu_rh_bp.route('/contracheque')
@login_required
def contracheque():
    _requer_colab()
    colab = _colab_do_usuario()
    if not colab:
        abort(403)

    cheques = (Contracheque.query
               .filter_by(colaborador_id=colab.id)
               .order_by(Contracheque.ano.desc(), Contracheque.mes.desc())
               .all())

    return render_template('meu_rh/contracheque.html', colab=colab,
                           cheques=cheques, meses=dict(MESES))


@meu_rh_bp.route('/contracheque/<int:id>/download')
@login_required
def contracheque_download(id):
    cheque = Contracheque.query.get_or_404(id)

    # Só o próprio colaborador ou gestor/admin pode baixar
    if (cheque.colaborador_id != current_user.colaborador_id
            and not current_user.is_gestor()):
        abort(403)

    upload_dir = os.path.join(current_app.root_path,
                              'static', 'uploads', 'contracheques')
    return send_from_directory(upload_dir, cheque.arquivo,
                               as_attachment=True,
                               download_name=f'contracheque_{cheque.periodo_display}.pdf')


# ── Gestão de Férias ──────────────────────────────────────────────────────────

@meu_rh_bp.route('/ferias')
@login_required
def ferias():
    _requer_colab()
    colab = _colab_do_usuario()
    if not colab:
        abort(403)

    periodos = (PeriodoAquisitivo.query
                .filter_by(colaborador_id=colab.id)
                .order_by(PeriodoAquisitivo.data_inicio.desc())
                .all())

    solicitacoes = (SolicitacaoFerias.query
                    .filter_by(colaborador_id=colab.id)
                    .order_by(SolicitacaoFerias.created_at.desc())
                    .all())

    # Período disponível para nova solicitação
    periodo_disponivel = next(
        (p for p in periodos if p.esta_disponivel), None
    )

    return render_template('meu_rh/ferias.html',
                           colab=colab,
                           periodos=periodos,
                           solicitacoes=solicitacoes,
                           periodo_disponivel=periodo_disponivel,
                           hoje=date.today())


@meu_rh_bp.route('/ferias/solicitar', methods=['POST'])
@login_required
def ferias_solicitar():
    _requer_colab()
    colab = _colab_do_usuario()
    if not colab:
        abort(403)

    periodo_id     = request.form.get('periodo_id')
    data_inicio    = request.form.get('data_inicio', '').strip()
    data_fim       = request.form.get('data_fim', '').strip()
    abono          = request.form.get('abono_pecuniario') == '1'
    dias_abono     = int(request.form.get('dias_abono', 0) or 0)
    observacao     = request.form.get('observacao', '').strip()

    if not periodo_id or not data_inicio or not data_fim:
        flash('Preencha todos os campos obrigatórios.', 'danger')
        return redirect(url_for('meu_rh.ferias'))

    periodo = PeriodoAquisitivo.query.get_or_404(int(periodo_id))
    if periodo.colaborador_id != colab.id:
        abort(403)

    if not periodo.esta_disponivel:
        flash('Este período não está disponível para solicitação.', 'danger')
        return redirect(url_for('meu_rh.ferias'))

    d_ini = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    d_fim = datetime.strptime(data_fim,    '%Y-%m-%d').date()
    dias  = (d_fim - d_ini).days + 1

    if dias < 5:
        flash('O período mínimo de férias é de 5 dias corridos.', 'danger')
        return redirect(url_for('meu_rh.ferias'))

    if dias > periodo.dias_saldo:
        flash(f'Você tem apenas {periodo.dias_saldo} dias de saldo disponível.', 'danger')
        return redirect(url_for('meu_rh.ferias'))

    if abono and dias_abono > 10:
        flash('O abono pecuniário é limitado a 10 dias.', 'danger')
        return redirect(url_for('meu_rh.ferias'))

    solicitacao = SolicitacaoFerias(
        colaborador_id   = colab.id,
        periodo_id       = periodo.id,
        data_inicio      = d_ini,
        data_fim         = d_fim,
        dias_solicitados = dias,
        abono_pecuniario = abono,
        dias_abono       = dias_abono if abono else 0,
        observacao       = observacao,
        status           = 'pendente',
    )
    db.session.add(solicitacao)
    db.session.commit()
    flash('Solicitação enviada! Aguarde aprovação do gestor.', 'success')
    return redirect(url_for('meu_rh.ferias'))


# ── Gestão de Contracheques (gestor) ─────────────────────────────────────────

@meu_rh_bp.route('/contracheque/upload', methods=['GET', 'POST'])
@login_required
@requer_gestor
def contracheque_upload():
    from app.models.user import User

    ids_equipe = db.session.query(User.colaborador_id).filter(
        User.role.in_(['tecnico', 'lider']),
        User.ativo == True,
        User.colaborador_id.isnot(None)
    )
    equipe = (Colaborador.query
              .filter(Colaborador.ativo == True,
                      Colaborador.id.in_(ids_equipe))
              .order_by(Colaborador.nome).all())

    if request.method == 'POST':
        colab_id = request.form.get('colaborador_id')
        ano      = request.form.get('ano')
        mes      = request.form.get('mes')
        obs      = request.form.get('observacao', '').strip()
        arquivo  = request.files.get('arquivo')

        if not all([colab_id, ano, mes, arquivo and arquivo.filename]):
            flash('Preencha todos os campos e selecione o arquivo PDF.', 'danger')
        else:
            ext = arquivo.filename.rsplit('.', 1)[-1].lower()
            if ext not in ALLOWED_PDF:
                flash('Apenas arquivos PDF são permitidos.', 'danger')
            else:
                fname = f"cc_{colab_id}_{ano}_{mes}_{uuid.uuid4().hex[:8]}.pdf"
                upload_dir = os.path.join(current_app.root_path,
                                          'static', 'uploads', 'contracheques')
                os.makedirs(upload_dir, exist_ok=True)
                arquivo.save(os.path.join(upload_dir, fname))

                # Substitui se já existir para o mesmo mês
                existente = Contracheque.query.filter_by(
                    colaborador_id=int(colab_id), ano=int(ano), mes=int(mes)
                ).first()

                if existente:
                    existente.arquivo     = fname
                    existente.uploaded_by = current_user.id
                    existente.observacao  = obs
                    existente.created_at  = datetime.utcnow()
                else:
                    db.session.add(Contracheque(
                        colaborador_id = int(colab_id),
                        ano            = int(ano),
                        mes            = int(mes),
                        arquivo        = fname,
                        uploaded_by    = current_user.id,
                        observacao     = obs,
                    ))

                db.session.commit()
                flash('Contracheque enviado com sucesso!', 'success')
                return redirect(url_for('meu_rh.contracheque_upload'))

    anos = list(range(date.today().year, date.today().year - 3, -1))
    return render_template('meu_rh/contracheque_upload.html',
                           equipe=equipe, meses=MESES,
                           anos=anos,
                           ano_atual=date.today().year,
                           mes_atual=date.today().month)


# ── Gestão de Férias (gestor) ─────────────────────────────────────────────────

@meu_rh_bp.route('/ferias/gestao')
@login_required
@requer_gestor
def ferias_gestao():
    from app.models.user import User

    ids_equipe = db.session.query(User.colaborador_id).filter(
        User.role.in_(['tecnico', 'lider']),
        User.ativo == True,
        User.colaborador_id.isnot(None)
    )
    equipe = (Colaborador.query
              .filter(Colaborador.ativo == True,
                      Colaborador.id.in_(ids_equipe))
              .order_by(Colaborador.nome).all())

    pendentes = (SolicitacaoFerias.query
                 .filter_by(status='pendente')
                 .join(Colaborador)
                 .filter(Colaborador.id.in_(ids_equipe))
                 .order_by(SolicitacaoFerias.created_at)
                 .all())

    return render_template('meu_rh/ferias_gestao.html',
                           equipe=equipe,
                           pendentes=pendentes,
                           hoje=date.today())


@meu_rh_bp.route('/ferias/<int:id>/aprovar', methods=['POST'])
@login_required
@requer_gestor
def ferias_aprovar(id):
    sol = SolicitacaoFerias.query.get_or_404(id)
    acao = request.form.get('acao')
    obs  = request.form.get('observacao_gestor', '').strip()

    if acao == 'aprovar':
        sol.status = 'aprovada'
        sol.periodo.dias_gozados += sol.dias_solicitados
        if sol.periodo.dias_gozados >= sol.periodo.dias_direito:
            sol.periodo.status = 'gozado'
        else:
            sol.periodo.status = 'parcial'
        flash('Férias aprovadas.', 'success')
    elif acao == 'recusar':
        sol.status = 'recusada'
        flash('Solicitação recusada.', 'info')

    sol.observacao_gestor = obs
    sol.aprovado_por = current_user.id
    sol.aprovado_em  = datetime.utcnow()
    sol.updated_at   = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('meu_rh.ferias_gestao'))


@meu_rh_bp.route('/ferias/periodo/novo', methods=['POST'])
@login_required
@requer_gestor
def ferias_novo_periodo():
    """Gestor cadastra período aquisitivo para um colaborador."""
    colab_id    = request.form.get('colaborador_id')
    data_inicio = request.form.get('data_inicio', '').strip()

    if not colab_id or not data_inicio:
        flash('Informe o colaborador e a data de início.', 'danger')
        return redirect(url_for('meu_rh.ferias_gestao'))

    from dateutil.relativedelta import relativedelta
    d_ini   = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    d_fim   = d_ini + relativedelta(years=1) - relativedelta(days=1)
    d_limit = d_fim + relativedelta(years=1)

    periodo = PeriodoAquisitivo(
        colaborador_id = int(colab_id),
        data_inicio    = d_ini,
        data_fim       = d_fim,
        data_limite    = d_limit,
        dias_direito   = 30,
        status         = 'em_aquisicao' if d_fim > date.today() else 'disponivel',
    )
    db.session.add(periodo)
    db.session.commit()
    flash('Período aquisitivo cadastrado.', 'success')
    return redirect(url_for('meu_rh.ferias_gestao'))
