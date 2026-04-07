import os
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from app.models.colaborador import Colaborador, AREAS, SENIORIDADES, REGIMES, ESTADOS_BR
from app.models.user import User
from datetime import datetime

colaboradores_bp = Blueprint('colaboradores', __name__, url_prefix='/colaboradores')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_foto(file):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'colaboradores')
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, filename))
        return filename
    return None


@colaboradores_bp.route('/')
@login_required
def lista():
    busca = request.args.get('busca', '').strip()
    area = request.args.get('area', '')
    senioridade = request.args.get('senioridade', '')
    status = request.args.get('status', 'ativo')

    # Equipe / Perfis: mostra apenas colaboradores vinculados a usuários com role='tecnico'
    ids_tecnicos = db.session.query(User.colaborador_id).filter(
        User.role == 'tecnico',
        User.colaborador_id.isnot(None)
    )
    query = Colaborador.query.filter(Colaborador.id.in_(ids_tecnicos))

    if status == 'ativo':
        query = query.filter_by(ativo=True)
    elif status == 'inativo':
        query = query.filter_by(ativo=False)

    if busca:
        query = query.filter(
            db.or_(
                Colaborador.nome.ilike(f'%{busca}%'),
                Colaborador.cargo.ilike(f'%{busca}%'),
                Colaborador.email.ilike(f'%{busca}%'),
            )
        )
    if area:
        query = query.filter_by(area=area)
    if senioridade:
        query = query.filter_by(senioridade=senioridade)

    colaboradores = query.order_by(Colaborador.nome).all()

    return render_template(
        'colaboradores/lista.html',
        colaboradores=colaboradores,
        areas=AREAS,
        senioridades=SENIORIDADES,
        busca=busca,
        area_sel=area,
        senioridade_sel=senioridade,
        status_sel=status,
    )


@colaboradores_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    # Criação unificada: toda pessoa é criada via cadastro de usuário
    flash('Para cadastrar um novo colaborador, crie o usuário do sistema.', 'info')
    return redirect(url_for('usuarios.novo'))

    if request.method == 'POST':
        foto_filename = save_foto(request.files.get('foto'))

        colaborador = Colaborador(
            nome=request.form.get('nome', '').strip(),
            email=request.form.get('email', '').strip().lower(),
            telefone=request.form.get('telefone', '').strip(),
            cpf=request.form.get('cpf', '').strip(),
            cargo=request.form.get('cargo', '').strip(),
            senioridade=request.form.get('senioridade', ''),
            area=request.form.get('area', ''),
            regime=request.form.get('regime', ''),
            cidade=request.form.get('cidade', '').strip(),
            estado=request.form.get('estado', ''),
            linkedin=request.form.get('linkedin', '').strip(),
            bio=request.form.get('bio', '').strip(),
            foto=foto_filename,
        )

        data_nasc = request.form.get('data_nascimento')
        if data_nasc:
            colaborador.data_nascimento = datetime.strptime(data_nasc, '%Y-%m-%d').date()

        data_adm = request.form.get('data_admissao')
        if data_adm:
            colaborador.data_admissao = datetime.strptime(data_adm, '%Y-%m-%d').date()

        try:
            db.session.add(colaborador)
            db.session.commit()
            flash(f'Colaborador {colaborador.nome} cadastrado com sucesso!', 'success')
            return redirect(url_for('colaboradores.detalhe', id=colaborador.id))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao cadastrar colaborador. Verifique os dados.', 'danger')

    return render_template('colaboradores/form.html', colaborador=None,
                           areas=AREAS, senioridades=SENIORIDADES,
                           regimes=REGIMES, estados=ESTADOS_BR,
                           now_date=datetime.today().strftime('%Y-%m-%d'))


@colaboradores_bp.route('/<int:id>')
@login_required
def detalhe(id):
    colaborador = Colaborador.query.get_or_404(id)
    return render_template('colaboradores/detalhe.html', colaborador=colaborador)


@colaboradores_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar(id):
    colaborador = Colaborador.query.get_or_404(id)

    if not current_user.is_gestor() and not current_user.is_lider():
        flash('Sem permissão para editar colaboradores.', 'warning')
        return redirect(url_for('colaboradores.detalhe', id=id))

    if request.method == 'POST':
        nova_foto = save_foto(request.files.get('foto'))
        if nova_foto:
            colaborador.foto = nova_foto

        colaborador.nome = request.form.get('nome', '').strip()
        colaborador.email = request.form.get('email', '').strip().lower()
        colaborador.telefone = request.form.get('telefone', '').strip()
        colaborador.cpf = request.form.get('cpf', '').strip()
        colaborador.cargo = request.form.get('cargo', '').strip()
        colaborador.senioridade = request.form.get('senioridade', '')
        colaborador.area = request.form.get('area', '')
        colaborador.regime = request.form.get('regime', '')
        colaborador.cidade = request.form.get('cidade', '').strip()
        colaborador.estado = request.form.get('estado', '')
        colaborador.linkedin = request.form.get('linkedin', '').strip()
        colaborador.bio = request.form.get('bio', '').strip()
        colaborador.updated_at = datetime.utcnow()

        data_nasc = request.form.get('data_nascimento')
        colaborador.data_nascimento = datetime.strptime(data_nasc, '%Y-%m-%d').date() if data_nasc else None

        data_adm = request.form.get('data_admissao')
        colaborador.data_admissao = datetime.strptime(data_adm, '%Y-%m-%d').date() if data_adm else None

        try:
            db.session.commit()
            flash('Dados atualizados com sucesso!', 'success')
            return redirect(url_for('colaboradores.detalhe', id=colaborador.id))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao atualizar. Verifique os dados.', 'danger')

    return render_template('colaboradores/form.html', colaborador=colaborador,
                           areas=AREAS, senioridades=SENIORIDADES,
                           regimes=REGIMES, estados=ESTADOS_BR,
                           now_date=datetime.today().strftime('%Y-%m-%d'))


@colaboradores_bp.route('/<int:id>/toggle-ativo', methods=['POST'])
@login_required
def toggle_ativo(id):
    if not current_user.is_gestor():
        flash('Acesso restrito a gestores.', 'warning')
        return redirect(url_for('colaboradores.lista'))

    colaborador = Colaborador.query.get_or_404(id)
    colaborador.ativo = not colaborador.ativo
    db.session.commit()

    status = 'ativado' if colaborador.ativo else 'desativado'
    flash(f'Colaborador {colaborador.nome} {status}.', 'info')
    return redirect(url_for('colaboradores.lista'))
