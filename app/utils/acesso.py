"""
Decoradores de controle de acesso por perfil.
Uso:
    @requer_gestor
    @requer_lider_ou_gestor
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user


def requer_gestor(f):
    """Gestor / RH ou Administrador do sistema."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_gestor():
            flash('Acesso restrito a gestores.', 'warning')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def requer_admin(f):
    """Apenas Administrador do sistema."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Acesso restrito ao administrador do sistema.', 'warning')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def requer_lider_ou_gestor(f):
    """Gestor, Líder de Projeto ou Administrador."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_lider():
            flash('Acesso restrito a líderes e gestores.', 'warning')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated


def requer_proprio_ou_gestor(id_colaborador):
    """Verifica se o usuário é o próprio colaborador, um gestor ou admin."""
    if current_user.is_gestor():
        return True
    if hasattr(current_user, 'colaborador_id') and current_user.colaborador_id == id_colaborador:
        return True
    return False
