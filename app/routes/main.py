from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app import db
from app.models.colaborador import Colaborador
from app.models.projeto import Projeto
from app.models.avaliacao import CicloAvaliacao
from app.models.skill import Skill

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    total_colaboradores = Colaborador.query.filter_by(ativo=True).count()
    total_skills        = Skill.query.filter_by(ativo=True).count()
    total_projetos      = Projeto.query.filter(Projeto.status.in_(['planejamento', 'em_andamento'])).count()
    total_ciclos        = CicloAvaliacao.query.filter(CicloAvaliacao.status != 'fechado').count()

    colaboradores_recentes = (
        Colaborador.query.filter_by(ativo=True)
        .order_by(Colaborador.created_at.desc())
        .limit(5).all()
    )
    projetos_ativos = (
        Projeto.query.filter(Projeto.status.in_(['planejamento', 'em_andamento']))
        .order_by(Projeto.created_at.desc())
        .limit(4).all()
    )

    return render_template('index.html',
                           total_colaboradores=total_colaboradores,
                           total_skills=total_skills,
                           total_projetos=total_projetos,
                           total_ciclos=total_ciclos,
                           colaboradores_recentes=colaboradores_recentes,
                           projetos_ativos=projetos_ativos)
