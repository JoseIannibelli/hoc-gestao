from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import hashlib

ROLES = [
    ('admin',   'Administrador',      'Owner do sistema — acesso total, sem vínculo com projetos ou equipes'),
    ('gestor',  'Gestor',             'Define e gerencia projetos — responsável pela equipe e entregas'),
    ('lider',   'Líder de Projeto',   'Lidera a equipe técnica dentro de um projeto'),
    ('tecnico', 'Equipe Técnica',     'Profissional alocado nos projetos da empresa'),
]


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='tecnico')
    ativo = db.Column(db.Boolean, default=True)
    colaborador_id   = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=True)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acesso    = db.Column(db.DateTime, nullable=True)

    # Reset de senha
    reset_token      = db.Column(db.String(256), nullable=True)   # hash do token
    reset_token_exp  = db.Column(db.DateTime, nullable=True)       # expiração (1h)

    # Relacionamento com Colaborador
    colaborador = db.relationship('Colaborador', backref='usuario', uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ── Reset de senha ────────────────────────────────────────────────────────

    def gerar_token_reset(self):
        """Gera um token seguro, armazena o hash e retorna o token bruto."""
        token = secrets.token_urlsafe(32)
        self.reset_token     = hashlib.sha256(token.encode()).hexdigest()
        self.reset_token_exp = datetime.utcnow() + timedelta(hours=1)
        return token

    def verificar_token_reset(self, token):
        """Verifica se o token é válido e não expirou."""
        if not self.reset_token or not self.reset_token_exp:
            return False
        if datetime.utcnow() > self.reset_token_exp:
            return False
        return self.reset_token == hashlib.sha256(token.encode()).hexdigest()

    def limpar_token_reset(self):
        """Invalida o token após uso."""
        self.reset_token     = None
        self.reset_token_exp = None

    def is_admin(self):
        return self.role == 'admin'

    def is_gestor(self):
        """Admin tem todos os poderes de gestor."""
        return self.role in ('gestor', 'admin')

    def is_lider(self):
        return self.role in ('gestor', 'lider', 'admin')

    def is_tecnico(self):
        return self.role == 'tecnico'

    @property
    def role_display(self):
        return {r[0]: r[1] for r in ROLES}.get(self.role, self.role)

    @property
    def role_descricao(self):
        return {r[0]: r[2] for r in ROLES}.get(self.role, '')

    def __repr__(self):
        return f'<User {self.email}>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
