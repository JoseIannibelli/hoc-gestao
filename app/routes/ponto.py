from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.ponto import (RegistroPonto, FechamentoPonto, SolicitacaoCorrecao,
                               TIPOS_OCORRENCIA, STATUS_FECHAMENTO,
                               CARGA_HORARIA_PADRAO)
from app.models.colaborador import Colaborador
from app.utils.acesso import requer_gestor
from datetime import datetime, date
import calendar

ponto_bp = Blueprint('ponto', __name__, url_prefix='/ponto')


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_colaborador_atual():
    if current_user.colaborador_id:
        return Colaborador.query.get(current_user.colaborador_id)
    return None


def dias_uteis_mes(ano, mes):
    _, total_dias = calendar.monthrange(ano, mes)
    return [date(ano, mes, d) for d in range(1, total_dias + 1)
            if date(ano, mes, d).weekday() < 5]


def calcular_totais(colaborador_id, ano, mes):
    uteis = dias_uteis_mes(ano, mes)
    registros = {r.data: r for r in RegistroPonto.query.filter_by(
        colaborador_id=colaborador_id
    ).filter(
        RegistroPonto.data >= date(ano, mes, 1),
        RegistroPonto.data <= date(ano, mes, calendar.monthrange(ano, mes)[1])
    ).all()}

    total_horas = 0.0
    total_faltas = 0
    saldo = 0.0

    for d in uteis:
        reg = registros.get(d)
        if reg:
            total_horas  += reg.horas_trabalhadas_decimal
            saldo        += reg.saldo_horas
            if reg.tipo in ('falta', 'falta_just'):
                total_faltas += 1
        else:
            if d < date.today():
                total_faltas += 1
                saldo -= CARGA_HORARIA_PADRAO

    return {
        'total_dias_uteis':  len(uteis),
        'total_horas_trab':  round(total_horas, 2),
        'total_faltas':      total_faltas,
        'saldo_banco_horas': round(saldo, 2),
    }


def mes_nome(mes):
    nomes = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    return nomes[mes]


def parse_time(val):
    if val and val.strip():
        try:
            return datetime.strptime(val.strip(), '%H:%M').time()
        except ValueError:
            return None
    return None


def nav_mes(ano, mes):
    """Retorna dicts de navegação para mês anterior e próximo."""
    m_ant = mes - 1 if mes > 1 else 12
    a_ant = ano if mes > 1 else ano - 1
    m_prx = mes + 1 if mes < 12 else 1
    a_prx = ano if mes < 12 else ano + 1
    return m_ant, a_ant, m_prx, a_prx


def verificar_auto_fechamento(colaborador_id):
    """
    Auto-fecha qualquer mês passado que ainda esteja com status 'aberto'.
    Chamado nas rotas sempre que um colaborador acessa o módulo.
    """
    hoje = date.today()
    abertos = FechamentoPonto.query.filter_by(
        colaborador_id=colaborador_id, status='aberto'
    ).filter(
        db.or_(
            FechamentoPonto.ano < hoje.year,
            db.and_(
                FechamentoPonto.ano == hoje.year,
                FechamentoPonto.mes < hoje.month
            )
        )
    ).all()

    for f in abertos:
        totais = calcular_totais(colaborador_id, f.ano, f.mes)
        f.status = 'fechado_auto'
        f.total_dias_uteis  = totais['total_dias_uteis']
        f.total_horas_trab  = totais['total_horas_trab']
        f.total_faltas      = totais['total_faltas']
        f.saldo_banco_horas = totais['saldo_banco_horas']
        f.updated_at        = datetime.utcnow()

    if abertos:
        db.session.commit()


def get_ou_criar_fechamento(colaborador_id, ano, mes):
    """Retorna o fechamento do mês, criando-o se necessário."""
    f = FechamentoPonto.query.filter_by(
        colaborador_id=colaborador_id, ano=ano, mes=mes
    ).first()
    if not f:
        f = FechamentoPonto(colaborador_id=colaborador_id, ano=ano, mes=mes)
        db.session.add(f)
        db.session.flush()
    return f


def mes_bloqueado(colaborador_id, ano, mes):
    """
    Retorna True se o mês não pode ser editado diretamente.
    Meses anteriores ao atual são sempre bloqueados (auto-fechamento).
    """
    hoje = date.today()
    if ano < hoje.year or (ano == hoje.year and mes < hoje.month):
        return True
    f = FechamentoPonto.query.filter_by(
        colaborador_id=colaborador_id, ano=ano, mes=mes
    ).first()
    return f is not None and f.bloqueado


# ── Rota raiz — redireciona conforme perfil ────────────────────────────────────

@ponto_bp.route('/')
@login_required
def meu_ponto():
    if current_user.is_gestor() and not current_user.colaborador_id:
        return redirect(url_for('ponto.visao_geral'))
    return redirect(url_for('ponto.registrar_hoje'))


# ── 1. Registrar Ponto — somente hoje ─────────────────────────────────────────

@ponto_bp.route('/hoje', methods=['GET', 'POST'])
@login_required
def registrar_hoje():
    colaborador = get_colaborador_atual()
    if not colaborador:
        flash('Seu usuário não está vinculado a um colaborador.', 'warning')
        return redirect(url_for('main.index'))

    verificar_auto_fechamento(colaborador.id)

    hoje = date.today()

    # Verifica se o mês atual está bloqueado (ex: gestor fechou manualmente)
    fechamento = FechamentoPonto.query.filter_by(
        colaborador_id=colaborador.id, ano=hoje.year, mes=hoje.month
    ).first()
    bloqueado = fechamento is not None and fechamento.bloqueado

    registro = RegistroPonto.query.filter_by(
        colaborador_id=colaborador.id, data=hoje
    ).first()

    if request.method == 'POST':
        if bloqueado:
            flash('A folha deste mês está bloqueada. Use "Solicitar Correção" para ajustes.', 'warning')
            return redirect(url_for('ponto.registrar_hoje'))

        if not registro:
            registro = RegistroPonto(colaborador_id=colaborador.id, data=hoje)
            db.session.add(registro)

        registro.entrada        = parse_time(request.form.get('entrada'))
        registro.inicio_almoco  = parse_time(request.form.get('inicio_almoco'))
        registro.retorno_almoco = parse_time(request.form.get('retorno_almoco'))
        registro.saida          = parse_time(request.form.get('saida'))
        registro.tipo           = request.form.get('tipo', 'normal')
        registro.observacao     = request.form.get('observacao', '').strip()
        registro.updated_at     = datetime.utcnow()
        db.session.commit()
        flash('Ponto registrado com sucesso!', 'success')
        return redirect(url_for('ponto.registrar_hoje'))

    return render_template('ponto/registrar_hoje.html',
                           colaborador=colaborador,
                           hoje=hoje,
                           registro=registro,
                           bloqueado=bloqueado,
                           fechamento=fechamento,
                           tipos_ocorrencia=TIPOS_OCORRENCIA,
                           mes_nome_atual=mes_nome(hoje.month))


# ── 2. Consultar Folha — visão mensal read-only ────────────────────────────────

@ponto_bp.route('/consultar')
@login_required
def consultar():
    colaborador = get_colaborador_atual()
    if not colaborador and not current_user.is_gestor():
        flash('Seu usuário não está vinculado a um colaborador.', 'warning')
        return redirect(url_for('main.index'))
    if not colaborador:
        return redirect(url_for('ponto.visao_geral'))

    verificar_auto_fechamento(colaborador.id)

    hoje = date.today()
    ano  = int(request.args.get('ano', hoje.year))
    mes  = int(request.args.get('mes', hoje.month))

    _, total_dias = calendar.monthrange(ano, mes)
    registros_dict = {r.data: r for r in RegistroPonto.query.filter_by(
        colaborador_id=colaborador.id
    ).filter(
        RegistroPonto.data >= date(ano, mes, 1),
        RegistroPonto.data <= date(ano, mes, total_dias)
    ).all()}

    uteis = set(dias_uteis_mes(ano, mes))
    dias  = []
    for d in range(1, total_dias + 1):
        dt = date(ano, mes, d)
        dias.append({
            'data':     dt,
            'util':     dt in uteis,
            'registro': registros_dict.get(dt),
            'hoje':     dt == hoje,
            'futuro':   dt > hoje,
        })

    totais = calcular_totais(colaborador.id, ano, mes)
    fechamento = FechamentoPonto.query.filter_by(
        colaborador_id=colaborador.id, ano=ano, mes=mes
    ).first()

    m_ant, a_ant, m_prx, a_prx = nav_mes(ano, mes)

    # Contagem de correções pendentes neste mês
    correcoes_pendentes = SolicitacaoCorrecao.query.filter_by(
        colaborador_id=colaborador.id, status='pendente'
    ).filter(
        SolicitacaoCorrecao.data_registro >= date(ano, mes, 1),
        SolicitacaoCorrecao.data_registro <= date(ano, mes, total_dias)
    ).count()

    return render_template('ponto/consultar.html',
                           colaborador=colaborador,
                           dias=dias, ano=ano, mes=mes,
                           totais=totais,
                           fechamento=fechamento,
                           mes_ant=m_ant, ano_ant=a_ant,
                           mes_prx=m_prx, ano_prx=a_prx,
                           hoje=hoje,
                           mes_nome=mes_nome(mes),
                           correcoes_pendentes=correcoes_pendentes,
                           tipos_ocorrencia=TIPOS_OCORRENCIA)


@ponto_bp.route('/fechar-mes', methods=['POST'])
@login_required
def fechar_mes():
    colaborador = get_colaborador_atual()
    if not colaborador:
        flash('Usuário não vinculado a colaborador.', 'danger')
        return redirect(url_for('ponto.consultar'))

    ano = int(request.form.get('ano'))
    mes = int(request.form.get('mes'))

    # Não permite fechar mês futuro
    hoje = date.today()
    if ano > hoje.year or (ano == hoje.year and mes > hoje.month):
        flash('Não é possível fechar um mês futuro.', 'warning')
        return redirect(url_for('ponto.consultar', ano=ano, mes=mes))

    fechamento = get_ou_criar_fechamento(colaborador.id, ano, mes)

    if fechamento.status == 'aprovado':
        flash('Este mês já foi aprovado.', 'info')
        return redirect(url_for('ponto.consultar', ano=ano, mes=mes))

    if fechamento.status == 'fechado_auto':
        flash('Este mês foi fechado automaticamente. Para alterar use "Solicitar Correção".', 'warning')
        return redirect(url_for('ponto.consultar', ano=ano, mes=mes))

    totais = calcular_totais(colaborador.id, ano, mes)
    fechamento.total_dias_uteis  = totais['total_dias_uteis']
    fechamento.total_horas_trab  = totais['total_horas_trab']
    fechamento.total_faltas      = totais['total_faltas']
    fechamento.saldo_banco_horas = totais['saldo_banco_horas']
    fechamento.observacao_colab  = request.form.get('observacao_colab', '').strip()
    fechamento.status            = 'submetido'
    fechamento.submetido_em      = datetime.utcnow()
    fechamento.updated_at        = datetime.utcnow()
    db.session.commit()

    flash(f'Folha de {mes_nome(mes)}/{ano} submetida para aprovação!', 'success')
    return redirect(url_for('ponto.consultar', ano=ano, mes=mes))


# ── 3. Solicitar Correção ──────────────────────────────────────────────────────

@ponto_bp.route('/correcoes', methods=['GET'])
@login_required
def correcoes():
    colaborador = get_colaborador_atual()
    if not colaborador:
        flash('Seu usuário não está vinculado a um colaborador.', 'warning')
        return redirect(url_for('main.index'))

    verificar_auto_fechamento(colaborador.id)

    # Lista de solicitações anteriores
    historico = SolicitacaoCorrecao.query.filter_by(
        colaborador_id=colaborador.id
    ).order_by(SolicitacaoCorrecao.created_at.desc()).limit(50).all()

    hoje = date.today()
    # Pré-seleciona data da query string (vindo de "Consultar Folha")
    data_str = request.args.get('data', '')
    registro_atual = None
    if data_str:
        try:
            data_pre = datetime.strptime(data_str, '%Y-%m-%d').date()
            registro_atual = RegistroPonto.query.filter_by(
                colaborador_id=colaborador.id, data=data_pre
            ).first()
        except ValueError:
            data_pre = None
    else:
        data_pre = None

    return render_template('ponto/correcoes.html',
                           colaborador=colaborador,
                           historico=historico,
                           hoje=hoje,
                           data_pre=data_pre,
                           registro_atual=registro_atual,
                           tipos_ocorrencia=TIPOS_OCORRENCIA)


@ponto_bp.route('/correcoes/nova', methods=['POST'])
@login_required
def nova_correcao():
    colaborador = get_colaborador_atual()
    if not colaborador:
        flash('Usuário não vinculado a colaborador.', 'danger')
        return redirect(url_for('ponto.correcoes'))

    data_str = request.form.get('data_registro', '').strip()
    motivo   = request.form.get('motivo', '').strip()

    if not data_str or not motivo:
        flash('Data e motivo são obrigatórios.', 'danger')
        return redirect(url_for('ponto.correcoes'))

    try:
        data_reg = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Data inválida.', 'danger')
        return redirect(url_for('ponto.correcoes'))

    hoje = date.today()
    if data_reg >= hoje:
        flash('Só é possível solicitar correção de dias passados.', 'warning')
        return redirect(url_for('ponto.correcoes'))

    # Captura registro atual (snapshot)
    reg_atual = RegistroPonto.query.filter_by(
        colaborador_id=colaborador.id, data=data_reg
    ).first()

    solicitacao = SolicitacaoCorrecao(
        colaborador_id=colaborador.id,
        data_registro=data_reg,
        motivo=motivo,
        # snapshot original
        entrada_orig        = reg_atual.entrada        if reg_atual else None,
        inicio_almoco_orig  = reg_atual.inicio_almoco  if reg_atual else None,
        retorno_almoco_orig = reg_atual.retorno_almoco if reg_atual else None,
        saida_orig          = reg_atual.saida          if reg_atual else None,
        tipo_orig           = reg_atual.tipo           if reg_atual else None,
        # valores solicitados
        entrada_novo        = parse_time(request.form.get('entrada_novo')),
        inicio_almoco_novo  = parse_time(request.form.get('inicio_almoco_novo')),
        retorno_almoco_novo = parse_time(request.form.get('retorno_almoco_novo')),
        saida_novo          = parse_time(request.form.get('saida_novo')),
        tipo_novo           = request.form.get('tipo_novo', 'normal'),
        status              = 'pendente',
    )
    db.session.add(solicitacao)
    db.session.commit()
    flash('Solicitação de correção enviada! Aguarde aprovação do gestor.', 'success')
    return redirect(url_for('ponto.correcoes'))


# ── Visão Geral — Gestor ───────────────────────────────────────────────────────

@ponto_bp.route('/visao-geral')
@login_required
def visao_geral():
    if not current_user.is_gestor() and not current_user.is_lider():
        flash('Acesso restrito.', 'warning')
        return redirect(url_for('ponto.registrar_hoje'))

    hoje = date.today()
    ano  = int(request.args.get('ano', hoje.year))
    mes  = int(request.args.get('mes', hoje.month))

    colaboradores = Colaborador.query.filter_by(ativo=True).order_by(Colaborador.nome).all()
    situacao = []
    for c in colaboradores:
        verificar_auto_fechamento(c.id)
        fechamento = FechamentoPonto.query.filter_by(
            colaborador_id=c.id, ano=ano, mes=mes
        ).first()
        totais = calcular_totais(c.id, ano, mes)
        situacao.append({'colaborador': c, 'fechamento': fechamento, 'totais': totais})

    pendentes = FechamentoPonto.query.filter_by(
        status='submetido', ano=ano, mes=mes
    ).all()

    # Correções pendentes (qualquer mês)
    total_correcoes = SolicitacaoCorrecao.query.filter_by(status='pendente').count()

    m_ant, a_ant, m_prx, a_prx = nav_mes(ano, mes)

    return render_template('ponto/visao_geral.html',
                           situacao=situacao,
                           pendentes=pendentes,
                           ano=ano, mes=mes,
                           mes_ant=m_ant, ano_ant=a_ant,
                           mes_prx=m_prx, ano_prx=a_prx,
                           mes_nome=mes_nome(mes),
                           total_correcoes=total_correcoes)


@ponto_bp.route('/aprovar/<int:fechamento_id>', methods=['POST'])
@login_required
@requer_gestor
def aprovar(fechamento_id):
    fechamento = FechamentoPonto.query.get_or_404(fechamento_id)
    acao = request.form.get('acao', 'aprovar')

    if acao == 'aprovar':
        fechamento.status        = 'aprovado'
        fechamento.aprovado_em   = datetime.utcnow()
        fechamento.aprovado_por  = current_user.id
        fechamento.observacao_gestor = request.form.get('observacao_gestor', '').strip()
        flash(f'Folha de {fechamento.colaborador.nome} — {mes_nome(fechamento.mes)}/{fechamento.ano} aprovada!', 'success')
    else:
        fechamento.status = 'rejeitado'
        fechamento.observacao_gestor = request.form.get('observacao_gestor', '').strip()
        flash('Folha rejeitada. O colaborador poderá corrigir e reenviar.', 'warning')

    fechamento.updated_at = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('ponto.visao_geral', ano=fechamento.ano, mes=fechamento.mes))


@ponto_bp.route('/detalhe/<int:colaborador_id>')
@login_required
def detalhe_colaborador(colaborador_id):
    if not current_user.is_gestor() and not current_user.is_lider():
        flash('Acesso restrito.', 'warning')
        return redirect(url_for('ponto.registrar_hoje'))

    colaborador = Colaborador.query.get_or_404(colaborador_id)
    hoje = date.today()
    ano  = int(request.args.get('ano', hoje.year))
    mes  = int(request.args.get('mes', hoje.month))

    _, total_dias = calendar.monthrange(ano, mes)
    registros_dict = {r.data: r for r in RegistroPonto.query.filter_by(
        colaborador_id=colaborador_id
    ).filter(
        RegistroPonto.data >= date(ano, mes, 1),
        RegistroPonto.data <= date(ano, mes, total_dias)
    ).all()}

    uteis = set(dias_uteis_mes(ano, mes))
    dias  = [{'data': date(ano, mes, d), 'util': date(ano, mes, d) in uteis,
               'registro': registros_dict.get(date(ano, mes, d))}
             for d in range(1, total_dias + 1)]

    totais     = calcular_totais(colaborador_id, ano, mes)
    fechamento = FechamentoPonto.query.filter_by(
        colaborador_id=colaborador_id, ano=ano, mes=mes
    ).first()

    m_ant, a_ant, m_prx, a_prx = nav_mes(ano, mes)

    return render_template('ponto/detalhe_colaborador.html',
                           colaborador=colaborador,
                           dias=dias, ano=ano, mes=mes,
                           totais=totais, fechamento=fechamento,
                           mes_ant=m_ant, ano_ant=a_ant,
                           mes_prx=m_prx, ano_prx=a_prx,
                           mes_nome=mes_nome(mes))


# ── Gerenciar Correções — Gestor ───────────────────────────────────────────────

@ponto_bp.route('/gestor/correcoes')
@login_required
@requer_gestor
def gerenciar_correcoes():
    filtro = request.args.get('filtro', 'pendente')
    query = SolicitacaoCorrecao.query
    if filtro in ('pendente', 'aprovada', 'rejeitada'):
        query = query.filter_by(status=filtro)
    correcoes = query.order_by(SolicitacaoCorrecao.created_at.desc()).all()

    contagens = {
        'pendente':  SolicitacaoCorrecao.query.filter_by(status='pendente').count(),
        'aprovada':  SolicitacaoCorrecao.query.filter_by(status='aprovada').count(),
        'rejeitada': SolicitacaoCorrecao.query.filter_by(status='rejeitada').count(),
    }
    return render_template('ponto/gerenciar_correcoes.html',
                           correcoes=correcoes,
                           filtro=filtro,
                           contagens=contagens)


@ponto_bp.route('/api/registro')
@login_required
def api_registro():
    """Retorna o registro de ponto de um dia específico (para o colaborador logado)."""
    colaborador = get_colaborador_atual()
    if not colaborador:
        return jsonify({'encontrado': False})
    data_str = request.args.get('data', '')
    try:
        data_req = datetime.strptime(data_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'encontrado': False})

    reg = RegistroPonto.query.filter_by(
        colaborador_id=colaborador.id, data=data_req
    ).first()
    if not reg:
        return jsonify({'encontrado': False})

    def fmt(t):
        return t.strftime('%H:%M') if t else ''

    return jsonify({
        'encontrado':    True,
        'tipo':          reg.tipo,
        'tipo_display':  reg.tipo_display,
        'entrada':       fmt(reg.entrada),
        'inicio_almoco': fmt(reg.inicio_almoco),
        'retorno_almoco':fmt(reg.retorno_almoco),
        'saida':         fmt(reg.saida),
        'observacao':    reg.observacao or '',
    })


@ponto_bp.route('/gestor/correcoes/<int:correcao_id>', methods=['POST'])
@login_required
@requer_gestor
def resolver_correcao(correcao_id):
    sol = SolicitacaoCorrecao.query.get_or_404(correcao_id)
    acao = request.form.get('acao', 'aprovar')

    if acao == 'aprovar':
        # Aplica a correção ao RegistroPonto
        reg = RegistroPonto.query.filter_by(
            colaborador_id=sol.colaborador_id,
            data=sol.data_registro
        ).first()
        if not reg:
            reg = RegistroPonto(
                colaborador_id=sol.colaborador_id,
                data=sol.data_registro
            )
            db.session.add(reg)

        reg.entrada        = sol.entrada_novo
        reg.inicio_almoco  = sol.inicio_almoco_novo
        reg.retorno_almoco = sol.retorno_almoco_novo
        reg.saida          = sol.saida_novo
        reg.tipo           = sol.tipo_novo or 'normal'
        reg.justificativa  = f'Correção aprovada em {datetime.utcnow().strftime("%d/%m/%Y")}'
        reg.updated_at     = datetime.utcnow()

        # Recalcula o fechamento do mês correspondente
        f = FechamentoPonto.query.filter_by(
            colaborador_id=sol.colaborador_id,
            ano=sol.data_registro.year,
            mes=sol.data_registro.month
        ).first()
        if f:
            totais = calcular_totais(sol.colaborador_id,
                                     sol.data_registro.year,
                                     sol.data_registro.month)
            f.total_dias_uteis  = totais['total_dias_uteis']
            f.total_horas_trab  = totais['total_horas_trab']
            f.total_faltas      = totais['total_faltas']
            f.saldo_banco_horas = totais['saldo_banco_horas']
            f.updated_at        = datetime.utcnow()

        sol.status            = 'aprovada'
        sol.aprovado_em       = datetime.utcnow()
        sol.aprovado_por      = current_user.id
        sol.observacao_gestor = request.form.get('observacao_gestor', '').strip()
        db.session.commit()
        flash(f'Correção de {sol.colaborador.nome} em {sol.data_registro.strftime("%d/%m/%Y")} aprovada e aplicada!', 'success')
    else:
        sol.status            = 'rejeitada'
        sol.observacao_gestor = request.form.get('observacao_gestor', '').strip()
        sol.updated_at        = datetime.utcnow()
        db.session.commit()
        flash('Solicitação de correção rejeitada.', 'warning')

    return redirect(url_for('ponto.gerenciar_correcoes'))
