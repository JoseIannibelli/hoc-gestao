from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.projeto import Projeto, Alocacao, STATUS_PROJETO, PAPEIS_ALOCACAO
from app.models.colaborador import Colaborador
from app.models.user import User
from app.utils.acesso import requer_lider_ou_gestor
from datetime import datetime

projetos_bp = Blueprint('projetos', __name__, url_prefix='/projetos')


@projetos_bp.route('/')
@login_required
def lista():
    status_sel = request.args.get('status', '')
    busca      = request.args.get('busca', '').strip()

    query = Projeto.query
    if status_sel:
        query = query.filter_by(status=status_sel)
    if busca:
        query = query.filter(
            db.or_(Projeto.nome.ilike(f'%{busca}%'),
                   Projeto.cliente.ilike(f'%{busca}%'))
        )

    # Equipe técnica só vê projetos em que está alocada
    if current_user.role == 'tecnico' and current_user.colaborador_id:
        ids_projetos = db.session.query(Alocacao.projeto_id).filter_by(
            colaborador_id=current_user.colaborador_id, ativo=True
        )
        query = query.filter(Projeto.id.in_(ids_projetos))

    projetos = query.order_by(Projeto.created_at.desc()).all()

    # Contadores por status
    contadores = {s[0]: Projeto.query.filter_by(status=s[0]).count() for s in STATUS_PROJETO}

    return render_template('projetos/lista.html',
                           projetos=projetos,
                           status_projeto=STATUS_PROJETO,
                           status_sel=status_sel,
                           busca=busca,
                           contadores=contadores)


@projetos_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@requer_lider_ou_gestor
def novo():
    gestores = User.query.filter(User.role == 'gestor', User.ativo == True).order_by(User.nome).all()
    # Líder: usuários com role 'lider' que tenham perfil de equipe vinculado
    ids_lideres = db.session.query(User.colaborador_id).filter(
        User.role == 'lider', User.ativo == True, User.colaborador_id.isnot(None)
    )
    colaboradores = Colaborador.query.filter(
        Colaborador.ativo == True, Colaborador.id.in_(ids_lideres)
    ).order_by(Colaborador.nome).all()

    if request.method == 'POST':
        projeto = Projeto(
            nome=request.form.get('nome', '').strip(),
            cliente=request.form.get('cliente', '').strip(),
            descricao=request.form.get('descricao', '').strip(),
            status=request.form.get('status', 'planejamento'),
            gestor_id=request.form.get('gestor_id') or None,
            lider_id=request.form.get('lider_id') or None,
            created_by=current_user.id,
        )

        di = request.form.get('data_inicio')
        df = request.form.get('data_fim_prevista')
        projeto.data_inicio       = datetime.strptime(di, '%Y-%m-%d').date() if di else None
        projeto.data_fim_prevista = datetime.strptime(df, '%Y-%m-%d').date() if df else None

        db.session.add(projeto)
        db.session.commit()
        flash(f'Projeto "{projeto.nome}" criado!', 'success')
        return redirect(url_for('projetos.detalhe', id=projeto.id))

    return render_template('projetos/form.html',
                           projeto=None,
                           colaboradores=colaboradores,
                           gestores=gestores,
                           status_projeto=STATUS_PROJETO)


@projetos_bp.route('/<int:id>')
@login_required
def detalhe(id):
    projeto = Projeto.query.get_or_404(id)
    alocacoes_ativas = projeto.alocacoes.filter_by(ativo=True).all()

    # Colaboradores disponíveis para alocar:
    # apenas usuários com role 'tecnico' ou 'lider' que tenham perfil vinculado
    ids_alocados = [a.colaborador_id for a in alocacoes_ativas]
    ids_equipe = db.session.query(User.colaborador_id).filter(
        User.role.in_(['tecnico', 'lider']),
        User.ativo == True,
        User.colaborador_id.isnot(None)
    )
    disponiveis = Colaborador.query.filter(
        Colaborador.ativo == True,
        Colaborador.id.in_(ids_equipe),
        ~Colaborador.id.in_(ids_alocados)
    ).order_by(Colaborador.nome).all()

    return render_template('projetos/detalhe.html',
                           projeto=projeto,
                           alocacoes=alocacoes_ativas,
                           disponiveis=disponiveis,
                           papeis=PAPEIS_ALOCACAO,
                           status_projeto=STATUS_PROJETO)


@projetos_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_lider_ou_gestor
def editar(id):
    projeto = Projeto.query.get_or_404(id)
    gestores = User.query.filter(User.role == 'gestor', User.ativo == True).order_by(User.nome).all()
    ids_lideres = db.session.query(User.colaborador_id).filter(
        User.role == 'lider', User.ativo == True, User.colaborador_id.isnot(None)
    )
    colaboradores = Colaborador.query.filter(
        Colaborador.ativo == True, Colaborador.id.in_(ids_lideres)
    ).order_by(Colaborador.nome).all()

    if request.method == 'POST':
        projeto.nome      = request.form.get('nome', '').strip()
        projeto.cliente   = request.form.get('cliente', '').strip()
        projeto.descricao = request.form.get('descricao', '').strip()
        projeto.status    = request.form.get('status', projeto.status)
        projeto.gestor_id = request.form.get('gestor_id') or None
        projeto.lider_id  = request.form.get('lider_id') or None
        projeto.updated_at = datetime.utcnow()

        di = request.form.get('data_inicio')
        df = request.form.get('data_fim_prevista')
        dfr = request.form.get('data_fim_real')
        projeto.data_inicio        = datetime.strptime(di,  '%Y-%m-%d').date() if di  else None
        projeto.data_fim_prevista  = datetime.strptime(df,  '%Y-%m-%d').date() if df  else None
        projeto.data_fim_real      = datetime.strptime(dfr, '%Y-%m-%d').date() if dfr else None

        db.session.commit()
        flash('Projeto atualizado!', 'success')
        return redirect(url_for('projetos.detalhe', id=projeto.id))

    return render_template('projetos/form.html',
                           projeto=projeto,
                           colaboradores=colaboradores,
                           gestores=gestores,
                           status_projeto=STATUS_PROJETO)


@projetos_bp.route('/<int:id>/alocar', methods=['POST'])
@login_required
@requer_lider_ou_gestor
def alocar(id):
    projeto = Projeto.query.get_or_404(id)
    colab_id   = request.form.get('colaborador_id')
    papel      = request.form.get('papel', 'desenvolvedor')
    percentual = int(request.form.get('percentual', 100))
    di = request.form.get('data_inicio')
    df = request.form.get('data_fim')

    if not colab_id:
        flash('Selecione um colaborador.', 'danger')
        return redirect(url_for('projetos.detalhe', id=id))

    existente = Alocacao.query.filter_by(
        projeto_id=id, colaborador_id=int(colab_id)
    ).first()

    if existente:
        existente.ativo      = True
        existente.papel      = papel
        existente.percentual = percentual
        existente.data_inicio = datetime.strptime(di, '%Y-%m-%d').date() if di else None
        existente.data_fim    = datetime.strptime(df, '%Y-%m-%d').date() if df else None
    else:
        alocacao = Alocacao(
            projeto_id=id,
            colaborador_id=int(colab_id),
            papel=papel,
            percentual=percentual,
            data_inicio=datetime.strptime(di, '%Y-%m-%d').date() if di else None,
            data_fim=datetime.strptime(df, '%Y-%m-%d').date() if df else None,
        )
        db.session.add(alocacao)

    db.session.commit()
    flash('Colaborador alocado ao projeto!', 'success')
    return redirect(url_for('projetos.detalhe', id=id))


@projetos_bp.route('/alocacao/<int:aloc_id>/editar', methods=['POST'])
@login_required
@requer_lider_ou_gestor
def editar_alocacao(aloc_id):
    alocacao = Alocacao.query.get_or_404(aloc_id)

    alocacao.papel      = request.form.get('papel', alocacao.papel)
    alocacao.percentual = int(request.form.get('percentual', alocacao.percentual))
    alocacao.observacao = request.form.get('observacao', '').strip() or None

    di = request.form.get('data_inicio')
    df = request.form.get('data_fim')
    alocacao.data_inicio = datetime.strptime(di, '%Y-%m-%d').date() if di else None
    alocacao.data_fim    = datetime.strptime(df, '%Y-%m-%d').date() if df else None

    db.session.commit()
    flash(f'Alocação de {alocacao.colaborador.nome} atualizada.', 'success')
    return redirect(url_for('projetos.detalhe', id=alocacao.projeto_id))


@projetos_bp.route('/alocacao/<int:aloc_id>/remover', methods=['POST'])
@login_required
@requer_lider_ou_gestor
def desalocar(aloc_id):
    alocacao = Alocacao.query.get_or_404(aloc_id)
    projeto_id = alocacao.projeto_id
    alocacao.ativo = False
    db.session.commit()
    flash('Membro removido da equipe do projeto.', 'info')
    return redirect(url_for('projetos.detalhe', id=projeto_id))
