from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, current_app)
from flask_login import login_user, logout_user, login_required, current_user
from app import db, mail
from app.models.user import User
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ── Login / Logout ────────────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(email=email).first()

        if user and user.ativo and user.check_password(password):
            login_user(user, remember=remember)
            user.ultimo_acesso = datetime.utcnow()
            db.session.commit()
            next_page = request.args.get('next')
            flash(f'Bem-vindo(a), {user.nome}!', 'success')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('E-mail ou senha inválidos.', 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada com sucesso.', 'info')
    return redirect(url_for('auth.login'))


# ── Esqueci minha senha ───────────────────────────────────────────────────────

@auth_bp.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user  = User.query.filter_by(email=email, ativo=True).first()

        # Sempre exibe a mesma mensagem — não revela se o e-mail existe
        msg_ok = ('Se este e-mail estiver cadastrado no sistema, você receberá '
                  'as instruções de recuperação em breve.')

        if user:
            token     = user.gerar_token_reset()
            db.session.commit()

            link = url_for('auth.redefinir_senha', token=token, _external=True)
            _enviar_email_reset(user, link)

        flash(msg_ok, 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/esqueci_senha.html')


def _enviar_email_reset(user, link):
    """
    Envia o e-mail de reset (ou imprime no console em modo dev).
    """
    app = current_app._get_current_object()

    if not app.config.get('MAIL_ENABLED'):
        # ── MODO DESENVOLVIMENTO — imprime link no console ────────────────
        separador = '─' * 60
        print(f'\n{separador}')
        print(f'  🔑  RESET DE SENHA — MODO DESENVOLVIMENTO')
        print(f'  Usuário : {user.nome} <{user.email}>')
        print(f'  Link    : {link}')
        print(f'  Expira  : 1 hora')
        print(f'{separador}\n')
        return

    # ── MODO PRODUÇÃO — envia e-mail real via Outlook ─────────────────────
    try:
        from flask_mail import Message
        corpo_html = render_template('auth/email_reset_senha.html',
                                     user=user, link=link)
        corpo_txt  = (
            f'Olá, {user.nome}!\n\n'
            f'Recebemos uma solicitação para redefinir a senha da sua conta HOC Gestão.\n\n'
            f'Clique no link abaixo para criar uma nova senha (válido por 1 hora):\n\n'
            f'{link}\n\n'
            f'Se você não fez essa solicitação, ignore este e-mail.\n\n'
            f'Equipe HOC Gestão'
        )
        msg = Message(
            subject='HOC Gestão — Redefinição de senha',
            recipients=[user.email],
            body=corpo_txt,
            html=corpo_html,
        )
        mail.send(msg)
    except Exception as e:
        app.logger.error(f'Erro ao enviar e-mail de reset para {user.email}: {e}')


# ── Redefinir senha via token ─────────────────────────────────────────────────

@auth_bp.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    # Busca o usuário pelo hash do token
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    user = User.query.filter_by(reset_token=token_hash).first()

    if not user or not user.verificar_token_reset(token):
        flash('Link de redefinição inválido ou expirado. Solicite um novo.', 'danger')
        return redirect(url_for('auth.esqueci_senha'))

    if request.method == 'POST':
        senha     = request.form.get('senha', '')
        confirma  = request.form.get('confirma', '')

        if len(senha) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'danger')
            return render_template('auth/redefinir_senha.html', token=token)

        if senha != confirma:
            flash('As senhas não conferem.', 'danger')
            return render_template('auth/redefinir_senha.html', token=token)

        user.set_password(senha)
        user.limpar_token_reset()
        db.session.commit()

        flash('Senha redefinida com sucesso! Faça login com a nova senha.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/redefinir_senha.html', token=token, user=user)
