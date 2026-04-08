from app import db
from datetime import datetime, date

TIPOS_COMUNICADO = [
    ('informativo',  'Informativo'),
    ('urgente',      'Urgente'),
    ('comemorativo', 'Comemorativo'),
    ('aviso',        'Aviso'),
]


class Comunicado(db.Model):
    """Comunicado/informe publicado pelo admin para todos os colaboradores."""
    __tablename__ = 'comunicados'

    id          = db.Column(db.Integer, primary_key=True)
    titulo      = db.Column(db.String(200), nullable=False)
    corpo       = db.Column(db.Text, nullable=False)
    tipo        = db.Column(db.String(20), default='informativo', nullable=False)
    fixado      = db.Column(db.Boolean, default=False)   # pinned no topo
    ativo       = db.Column(db.Boolean, default=True)
    expira_em   = db.Column(db.Date, nullable=True)       # None = sem expiração
    criado_por  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow)

    autor       = db.relationship('User', foreign_keys=[criado_por])

    @property
    def esta_vigente(self):
        """True se o comunicado ainda deve ser exibido (não expirou)."""
        if not self.ativo:
            return False
        if self.expira_em and self.expira_em < date.today():
            return False
        return True

    @property
    def tipo_display(self):
        return dict(TIPOS_COMUNICADO).get(self.tipo, self.tipo)

    @property
    def tipo_badge_class(self):
        return {
            'informativo':  'bg-primary',
            'urgente':      'bg-danger',
            'comemorativo': 'bg-success',
            'aviso':        'bg-warning text-dark',
        }.get(self.tipo, 'bg-secondary')

    @property
    def tipo_icon(self):
        return {
            'informativo':  'bi-info-circle-fill',
            'urgente':      'bi-exclamation-triangle-fill',
            'comemorativo': 'bi-stars',
            'aviso':        'bi-bell-fill',
        }.get(self.tipo, 'bi-megaphone-fill')
