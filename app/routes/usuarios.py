from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models.user import User, ROLES
from app.models.colaborador import Colaborador
from app.models.projeto import Projeto
from app.utils.acesso import requer_admin
from datetime import datetime

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios')


# ── lista ──────────────────────────────────────────────────────────────────────

@usuarios_bp.route('/')
@login_required
@requer_admin
def lista():
    busca  = request.args.get('busca', '').strip()
    role   = request.args.get('role', '')
    status = request.args.get('status', 'ativo')

    query = User.query
    if status == 'ativo':
        query = query.filter_by(ativo=True)
    elif status == 'inativo':
        query = query.filter_by(ativo=False)
    if busca:
        query = query.filter(
            db.or_(User.nome.ilike(f'%{busca}%'),
                   User.email.ilike(f'%{busca}%'))
        )
    if role:
        query = query.filter_by(role=role)

    usuarios = query.order_by(User.nome).all()
    return render_template('usuarios/lista.html',
                           usuarios=usuarios, roles=ROLES,
                           busca=busca, role_sel=role, status_sel=status)


# ── novo ───────────────────────────────────────────────────────────────────────

@usuarios_bp.route('/novo', methods=['GET', 'POST'])
@login_required
@requer_admin
def novo():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        nome  = request.form.get('nome', '').strip()
        role  = request.form.get('role', 'tecnico')
        senha = request.form.get('senha', '').strip()

        erro = None
        if not nome:
            erro = 'O nome é obrigatório.'
        elif not email:
            erro = 'O e-mail é obrigatório.'
        elif User.query.filter_by(email=email).first():
            erro = 'Já existe um usuário com este e-mail.'
        elif len(senha) < 6:
            erro = 'A senha deve ter pelo menos 6 caracteres.'

        if erro:
            flash(erro, 'danger')
        else:
            user = User(nome=nome, email=email, role=role)
            user.set_password(senha)

            # Cria registro mínimo de colaborador para não-admin
            # (perfil completo será preenchido pelo gestor em Equipe/Perfis)
            if role != 'admin':
                colab = Colaborador.query.filter_by(email=email).first()
                if not colab:
                    colab = Colaborador(nome=nome, email=email, ativo=True)
                    db.session.add(colab)
                    db.session.flush()
                user.colaborador_id = colab.id

            db.session.add(user)
            db.session.commit()
            flash(f'Usuário {nome} criado com sucesso!', 'success')
            return redirect(url_for('usuarios.lista'))

    return render_template('usuarios/form.html', usuario=None, roles=ROLES)


# ── editar ─────────────────────────────────────────────────────────────────────

@usuarios_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
@requer_admin
def editar(id):
    usuario = User.query.get_or_404(id)

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        role = request.form.get('role', 'tecnico')

        # Admin não pode se rebaixar
        if usuario.id == current_user.id and role != 'admin':
            role = 'admin'
            flash('Você não pode alterar o próprio perfil.', 'warning')

        usuario.nome = nome
        usuario.role = role

        nova_senha = request.form.get('senha', '').strip()
        if nova_senha:
            if len(nova_senha) < 6:
                flash('A nova senha deve ter pelo menos 6 caracteres.', 'danger')
                return render_template('usuarios/form.html', usuario=usuario, roles=ROLES)
            usuario.set_password(nova_senha)

        # Sincroniza nome no colaborador se existir
        if usuario.colaborador:
            usuario.colaborador.nome = nome
        elif role != 'admin':
            # Cria registro mínimo se não existir
            colab = Colaborador.query.filter_by(email=usuario.email).first()
            if not colab:
                colab = Colaborador(nome=nome, email=usuario.email, ativo=True)
                db.session.add(colab)
                db.session.flush()
            usuario.colaborador_id = colab.id

        if role == 'admin':
            usuario.colaborador_id = None

        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('usuarios.lista'))

    return render_template('usuarios/form.html', usuario=usuario, roles=ROLES)


# ── toggle ativo ──────────────────────────────────────────────────────────────

@usuarios_bp.route('/<int:id>/toggle-ativo', methods=['POST'])
@login_required
@requer_admin
def toggle_ativo(id):
    usuario = User.query.get_or_404(id)
    if usuario.id == current_user.id:
        flash('Você não pode desativar seu próprio usuário.', 'warning')
        return redirect(url_for('usuarios.lista'))

    usuario.ativo = not usuario.ativo
    # Sincroniza com o perfil de colaborador
    if usuario.colaborador:
        usuario.colaborador.ativo = usuario.ativo

    db.session.commit()
    status = 'ativado' if usuario.ativo else 'desativado'
    flash(f'Usuário {usuario.nome} {status}.', 'info')
    return redirect(url_for('usuarios.lista'))


# ── resetar senha ─────────────────────────────────────────────────────────────

@usuarios_bp.route('/<int:id>/resetar-senha', methods=['POST'])
@login_required
@requer_admin
def resetar_senha(id):
    usuario = User.query.get_or_404(id)
    nova = request.form.get('nova_senha', '').strip()
    if len(nova) < 6:
        flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
    else:
        usuario.set_password(nova)
        db.session.commit()
        flash(f'Senha de {usuario.nome} redefinida com sucesso.', 'success')
    return redirect(url_for('usuarios.lista'))


# ── excluir ───────────────────────────────────────────────────────────────────

@usuarios_bp.route('/<int:id>/excluir', methods=['POST'])
@login_required
@requer_admin
def excluir(id):
    usuario = User.query.get_or_404(id)

    # Não pode excluir a si mesmo
    if usuario.id == current_user.id:
        flash('Você não pode excluir seu próprio usuário.', 'warning')
        return redirect(url_for('usuarios.lista'))

    # Não pode excluir o último admin
    if usuario.role == 'admin':
        qtd_admins = User.query.filter_by(role='admin', ativo=True).count()
        if qtd_admins <= 1:
            flash('Não é possível excluir o último administrador do sistema.', 'danger')
            return redirect(url_for('usuarios.lista'))

    # Bloqueia exclusão se houver qualquer histórico de atividade.
    # Usuários com rastro de auditoria devem ser apenas desativados,
    # para preservar a integridade dos registros históricos.
    motivos = []

    projetos_gestor  = Projeto.query.filter_by(gestor_id=usuario.id).count()
    projetos_criador = Projeto.query.filter_by(created_by=usuario.id).count()
    if projetos_gestor:
        motivos.append(f'{projetos_gestor} projeto(s) como gestor')
    if projetos_criador:
        motivos.append(f'{projetos_criador} projeto(s) criado(s)')

    if usuario.colaborador_id:
        from app.models.colaborador import Colaborador as Col
        from app.models.projeto import Alocacao
        proj_lider = Projeto.query.filter_by(lider_id=usuario.colaborador_id).count()
        alocacoes  = Alocacao.query.filter_by(colaborador_id=usuario.colaborador_id).count()
        if proj_lider:
            motivos.append(f'líder em {proj_lider} projeto(s)')
        if alocacoes:
            motivos.append(f'{alocacoes} alocação(ões) em projetos')

        # Registros de ponto
        from app.models.ponto import RegistroPonto
        registros_ponto = RegistroPonto.query.filter_by(colaborador_id=usuario.colaborador_id).count()
        if registros_ponto:
            motivos.append(f'{registros_ponto} registro(s) de ponto')

    if motivos:
        lista = ', '.join(motivos)
        flash(
            f'Não é possível excluir {usuario.nome} — há histórico vinculado: {lista}. '
            f'Use a opção "Desativar" para bloquear o acesso preservando o histórico.',
            'danger'
        )
        return redirect(url_for('usuarios.lista'))

    nome = usuario.nome
    db.session.delete(usuario)
    db.session.commit()
    flash(f'Usuário {nome} excluído com sucesso.', 'success')
    return redirect(url_for('usuarios.lista'))
