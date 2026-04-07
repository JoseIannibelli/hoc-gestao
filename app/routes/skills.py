from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.skill import Skill, ColaboradorSkill, Certificacao, CATEGORIAS_SKILL, NIVEIS_SKILL
from app.models.colaborador import Colaborador
from app.utils.acesso import requer_lider_ou_gestor
from datetime import datetime

skills_bp = Blueprint('skills', __name__, url_prefix='/skills')


# ── Catálogo global ────────────────────────────────────────────────────────────

@skills_bp.route('/')
@login_required
def catalogo():
    busca     = request.args.get('busca', '').strip()
    categoria = request.args.get('categoria', '')

    query = Skill.query.filter_by(ativo=True)
    if busca:
        query = query.filter(Skill.nome.ilike(f'%{busca}%'))
    if categoria:
        query = query.filter_by(categoria=categoria)

    skills = query.order_by(Skill.categoria, Skill.nome).all()

    # Agrupa por categoria
    agrupado = {}
    for s in skills:
        cat = s.categoria_display
        agrupado.setdefault(cat, []).append(s)

    return render_template('skills/catalogo.html',
                           agrupado=agrupado, skills=skills,
                           categorias=CATEGORIAS_SKILL,
                           busca=busca, categoria_sel=categoria)


@skills_bp.route('/nova', methods=['GET', 'POST'])
@login_required
@requer_lider_ou_gestor
def nova_skill():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        if Skill.query.filter(Skill.nome.ilike(nome)).first():
            flash('Já existe uma skill com este nome.', 'danger')
        else:
            skill = Skill(
                nome=nome,
                categoria=request.form.get('categoria', ''),
                descricao=request.form.get('descricao', '').strip(),
            )
            db.session.add(skill)
            db.session.commit()
            flash(f'Skill "{skill.nome}" criada com sucesso!', 'success')
            return redirect(url_for('skills.catalogo'))

    return render_template('skills/form_skill.html',
                           skill=None, categorias=CATEGORIAS_SKILL)


@skills_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_lider_ou_gestor
def editar_skill(id):
    skill = Skill.query.get_or_404(id)

    if request.method == 'POST':
        skill.nome      = request.form.get('nome', '').strip()
        skill.categoria = request.form.get('categoria', '')
        skill.descricao = request.form.get('descricao', '').strip()
        db.session.commit()
        flash('Skill atualizada!', 'success')
        return redirect(url_for('skills.catalogo'))

    return render_template('skills/form_skill.html',
                           skill=skill, categorias=CATEGORIAS_SKILL)


# ── Skills do colaborador ──────────────────────────────────────────────────────

@skills_bp.route('/colaborador/<int:colab_id>')
@login_required
def perfil_skills(colab_id):
    colaborador = Colaborador.query.get_or_404(colab_id)
    colab_skills = (ColaboradorSkill.query
                    .filter_by(colaborador_id=colab_id)
                    .join(Skill)
                    .order_by(ColaboradorSkill.principal.desc(), Skill.nome)
                    .all())

    # Skills disponíveis para adicionar
    ids_atuais = [cs.skill_id for cs in colab_skills]
    skills_disp = Skill.query.filter(
        Skill.ativo == True,
        ~Skill.id.in_(ids_atuais)
    ).order_by(Skill.nome).all()

    return render_template('skills/perfil_skills.html',
                           colaborador=colaborador,
                           colab_skills=colab_skills,
                           skills_disp=skills_disp,
                           niveis=NIVEIS_SKILL)


@skills_bp.route('/colaborador/<int:colab_id>/adicionar', methods=['POST'])
@login_required
def adicionar_skill(colab_id):
    colaborador = Colaborador.query.get_or_404(colab_id)

    # Permissão: gestor/líder ou o próprio colaborador
    from app.utils.acesso import requer_proprio_ou_gestor
    if not requer_proprio_ou_gestor(colab_id) and not current_user.is_lider():
        flash('Sem permissão.', 'warning')
        return redirect(url_for('skills.perfil_skills', colab_id=colab_id))

    skill_id = request.form.get('skill_id')
    nivel    = request.form.get('nivel', 'basico')
    anos     = request.form.get('anos_experiencia', 0)

    if not skill_id:
        flash('Selecione uma skill.', 'danger')
        return redirect(url_for('skills.perfil_skills', colab_id=colab_id))

    existente = ColaboradorSkill.query.filter_by(
        colaborador_id=colab_id, skill_id=int(skill_id)
    ).first()

    if existente:
        flash('Esta skill já está no perfil.', 'warning')
    else:
        cs = ColaboradorSkill(
            colaborador_id=colab_id,
            skill_id=int(skill_id),
            nivel=nivel,
            anos_experiencia=float(anos) if anos else 0,
        )
        db.session.add(cs)
        db.session.commit()
        flash('Skill adicionada!', 'success')

    return redirect(url_for('skills.perfil_skills', colab_id=colab_id))


@skills_bp.route('/colaborador/skill/<int:cs_id>/editar', methods=['POST'])
@login_required
def editar_colab_skill(cs_id):
    cs = ColaboradorSkill.query.get_or_404(cs_id)
    cs.nivel            = request.form.get('nivel', cs.nivel)
    cs.anos_experiencia = float(request.form.get('anos_experiencia', 0) or 0)
    cs.principal        = request.form.get('principal') == '1'
    db.session.commit()
    flash('Skill atualizada!', 'success')
    return redirect(url_for('skills.perfil_skills', colab_id=cs.colaborador_id))


@skills_bp.route('/colaborador/skill/<int:cs_id>/remover', methods=['POST'])
@login_required
def remover_skill(cs_id):
    cs = ColaboradorSkill.query.get_or_404(cs_id)
    colab_id = cs.colaborador_id
    db.session.delete(cs)
    db.session.commit()
    flash('Skill removida.', 'info')
    return redirect(url_for('skills.perfil_skills', colab_id=colab_id))


# ── Certificações ──────────────────────────────────────────────────────────────

@skills_bp.route('/colaborador/<int:colab_id>/certificacao/nova', methods=['POST'])
@login_required
def nova_certificacao(colab_id):
    Colaborador.query.get_or_404(colab_id)

    nome        = request.form.get('nome', '').strip()
    instituicao = request.form.get('instituicao', '').strip()
    data_obt    = request.form.get('data_obtencao')
    data_exp    = request.form.get('data_expiracao')
    url         = request.form.get('url', '').strip()

    cert = Certificacao(
        colaborador_id=colab_id,
        nome=nome,
        instituicao=instituicao,
        data_obtencao=datetime.strptime(data_obt, '%Y-%m-%d').date() if data_obt else None,
        data_expiracao=datetime.strptime(data_exp, '%Y-%m-%d').date() if data_exp else None,
        url=url,
    )
    db.session.add(cert)
    db.session.commit()
    flash('Certificação adicionada!', 'success')
    return redirect(url_for('skills.perfil_skills', colab_id=colab_id))


@skills_bp.route('/certificacao/<int:cert_id>/remover', methods=['POST'])
@login_required
def remover_certificacao(cert_id):
    cert = Certificacao.query.get_or_404(cert_id)
    colab_id = cert.colaborador_id
    db.session.delete(cert)
    db.session.commit()
    flash('Certificação removida.', 'info')
    return redirect(url_for('skills.perfil_skills', colab_id=colab_id))


# ── Busca por skill (API) ──────────────────────────────────────────────────────

@skills_bp.route('/busca')
@login_required
def busca_por_skill():
    skill_id     = request.args.get('skill_id', type=int)
    nivel        = request.args.get('nivel', '')
    skills_todas = Skill.query.filter_by(ativo=True).order_by(Skill.nome).all()

    resultados = []
    if skill_id:
        query = (ColaboradorSkill.query
                 .filter_by(skill_id=skill_id)
                 .join(Colaborador)
                 .filter(Colaborador.ativo == True))
        if nivel:
            query = query.filter(ColaboradorSkill.nivel == nivel)
        resultados = query.all()

    return render_template('skills/busca.html',
                           skills=skills_todas,
                           resultados=resultados,
                           skill_id_sel=skill_id,
                           nivel_sel=nivel,
                           niveis=NIVEIS_SKILL)
