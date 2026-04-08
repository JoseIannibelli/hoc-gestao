from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app import db
from app.models.colaborador import Colaborador
from app.models.projeto import Projeto, Alocacao
from app.models.comunicado import Comunicado
from app.models.ferias import SolicitacaoFerias
from datetime import date
from sqlalchemy import extract

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    hoje = date.today()

    # ── Comunicados vigentes ──────────────────────────────────────────────────
    comunicados = (Comunicado.query
                   .filter(Comunicado.ativo == True)
                   .order_by(Comunicado.fixado.desc(), Comunicado.created_at.desc())
                   .all())
    # Filtra os expirados em Python (evita SQL de comparação de datas nula)
    comunicados = [c for c in comunicados if c.esta_vigente]

    # ── Meus Projetos (somente para usuários com perfil técnico vinculado) ────
    meus_projetos = []
    if current_user.colaborador_id:
        meus_projetos = (
            Alocacao.query
            .filter_by(colaborador_id=current_user.colaborador_id)
            .join(Projeto)
            .filter(Projeto.status.in_(['planejamento', 'em_andamento']))
            .order_by(Projeto.nome)
            .all()
        )

    # ── Aniversariantes do mês ────────────────────────────────────────────────
    aniversariantes = (
        Colaborador.query
        .filter(
            Colaborador.ativo == True,
            Colaborador.data_nascimento.isnot(None),
            extract('month', Colaborador.data_nascimento) == hoje.month,
        )
        .order_by(extract('day', Colaborador.data_nascimento))
        .all()
    )

    # ── Próximas férias aprovadas ─────────────────────────────────────────────
    from app.models.user import User

    if current_user.is_gestor():
        # Gestor vê toda a equipe
        ids_equipe = db.session.query(User.colaborador_id).filter(
            User.role.in_(['tecnico', 'lider']),
            User.ativo == True,
            User.colaborador_id.isnot(None)
        )
        ferias = (SolicitacaoFerias.query
                  .filter(
                      SolicitacaoFerias.status == 'aprovada',
                      SolicitacaoFerias.data_fim >= hoje,
                      SolicitacaoFerias.colaborador_id.in_(ids_equipe),
                  )
                  .join(Colaborador)
                  .order_by(SolicitacaoFerias.data_inicio)
                  .limit(10).all())
    elif current_user.colaborador_id:
        # Colaborador vê apenas as próprias
        ferias = (SolicitacaoFerias.query
                  .filter(
                      SolicitacaoFerias.status == 'aprovada',
                      SolicitacaoFerias.data_fim >= hoje,
                      SolicitacaoFerias.colaborador_id == current_user.colaborador_id,
                  )
                  .order_by(SolicitacaoFerias.data_inicio)
                  .all())
    else:
        ferias = []

    # ── Atalhos rápidos (por perfil) ──────────────────────────────────────────
    atalhos = _atalhos_por_perfil()

    return render_template('home.html',
                           comunicados=comunicados,
                           meus_projetos=meus_projetos,
                           aniversariantes=aniversariantes,
                           ferias=ferias,
                           atalhos=atalhos,
                           hoje=hoje)


def _atalhos_por_perfil():
    """Retorna lista de dicts {label, url, icon, cor} conforme o perfil logado."""
    from flask import url_for

    comuns = []
    if current_user.colaborador_id:
        comuns = [
            {'label': 'Registrar Ponto',   'url': url_for('ponto.registrar_hoje'),
             'icon': 'bi-clock',            'cor': '#f59e0b'},
            {'label': 'Folha de Ponto',    'url': url_for('ponto.consultar'),
             'icon': 'bi-calendar3',        'cor': '#f59e0b'},
            {'label': 'Minhas Férias',     'url': url_for('meu_rh.ferias'),
             'icon': 'bi-umbrella',         'cor': '#10B981'},
            {'label': 'Contracheque',      'url': url_for('meu_rh.contracheque'),
             'icon': 'bi-file-earmark-text','cor': '#10B981'},
            {'label': 'Dados Cadastrais',  'url': url_for('meu_rh.dados_cadastrais'),
             'icon': 'bi-person-vcard',     'cor': '#3B82F6'},
        ]

    if current_user.is_gestor():
        return [
            {'label': 'Equipe / Perfis',    'url': url_for('colaboradores.lista'),
             'icon': 'bi-people-fill',       'cor': '#3B82F6'},
            {'label': 'Projetos',           'url': url_for('projetos.lista'),
             'icon': 'bi-kanban',            'cor': '#8B5CF6'},
            {'label': 'Ponto — Visão Geral','url': url_for('ponto.visao_geral'),
             'icon': 'bi-grid-3x3-gap',      'cor': '#f59e0b'},
            {'label': 'Aprovar Correções',  'url': url_for('ponto.gerenciar_correcoes'),
             'icon': 'bi-check2-square',     'cor': '#f59e0b'},
            {'label': 'Publicar Contracheque','url': url_for('meu_rh.contracheque_upload'),
             'icon': 'bi-upload',            'cor': '#10B981'},
            {'label': 'Gestão de Férias',   'url': url_for('meu_rh.ferias_gestao'),
             'icon': 'bi-umbrella',          'cor': '#10B981'},
        ]

    if current_user.role == 'lider':
        return [
            {'label': 'Projetos',        'url': url_for('projetos.lista'),
             'icon': 'bi-kanban',         'cor': '#8B5CF6'},
            {'label': 'Ponto da Equipe', 'url': url_for('ponto.visao_geral'),
             'icon': 'bi-grid-3x3-gap',   'cor': '#f59e0b'},
        ] + comuns

    if current_user.is_admin():
        return [
            {'label': 'Usuários e Acessos','url': url_for('usuarios.lista'),
             'icon': 'bi-shield-lock',      'cor': '#EF4444'},
            {'label': 'Equipe / Perfis',   'url': url_for('colaboradores.lista'),
             'icon': 'bi-people-fill',      'cor': '#3B82F6'},
            {'label': 'Projetos',          'url': url_for('projetos.lista'),
             'icon': 'bi-kanban',           'cor': '#8B5CF6'},
            {'label': 'Comunicados',       'url': url_for('comunicados.lista'),
             'icon': 'bi-megaphone-fill',   'cor': '#f59e0b'},
        ]

    return comuns
