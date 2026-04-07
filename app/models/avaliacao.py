from app import db
from datetime import datetime

STATUS_CICLO = [
    ('aberto',       'Aberto',       '#d1fae5', '#065f46'),
    ('em_andamento', 'Em andamento', '#fef9c3', '#854d0e'),
    ('fechado',      'Fechado',      '#f1f5f9', '#475569'),
]

TIPOS_AVALIACAO = [
    ('auto',    'Autoavaliação'),
    ('hetero',  'Heteroavaliação'),
    ('gestor',  'Avaliação do Gestor'),
]

STATUS_AVALIACAO = [
    ('pendente',  'Pendente'),
    ('rascunho',  'Rascunho'),
    ('enviada',   'Enviada'),
]

STATUS_META = [
    ('pendente',     'Pendente',     '#fef9c3', '#854d0e'),
    ('em_andamento', 'Em andamento', '#dbeafe', '#1d4ed8'),
    ('concluida',    'Concluída',    '#d1fae5', '#065f46'),
    ('cancelada',    'Cancelada',    '#fee2e2', '#991b1b'),
]

TIPOS_META = [
    ('meta', 'Meta de Desempenho'),
    ('pdi',  'PDI — Plano de Desenvolvimento'),
]

CRITERIOS = [
    ('tecnico',          'Competência Técnica'),
    ('comunicacao',      'Comunicação'),
    ('trabalho_equipe',  'Trabalho em Equipe'),
    ('proatividade',     'Proatividade'),
    ('entrega_prazo',    'Entrega no Prazo'),
]


class CicloAvaliacao(db.Model):
    __tablename__ = 'ciclos_avaliacao'

    id          = db.Column(db.Integer, primary_key=True)
    nome        = db.Column(db.String(100), nullable=False)
    descricao   = db.Column(db.Text)
    data_inicio = db.Column(db.Date)
    data_fim    = db.Column(db.Date)
    status      = db.Column(db.String(20), default='aberto')
    created_by  = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    avaliacoes  = db.relationship('Avaliacao', backref='ciclo', lazy='dynamic', cascade='all, delete-orphan')
    metas       = db.relationship('Meta', backref='ciclo', lazy='dynamic')
    criador     = db.relationship('User', foreign_keys=[created_by])

    @property
    def status_info(self):
        for s in STATUS_CICLO:
            if s[0] == self.status:
                return {'label': s[1], 'bg': s[2], 'color': s[3]}
        return {'label': self.status, 'bg': '#f1f5f9', 'color': '#475569'}

    @property
    def total_avaliacoes(self):
        return self.avaliacoes.count()

    @property
    def total_enviadas(self):
        return self.avaliacoes.filter_by(status='enviada').count()


class Avaliacao(db.Model):
    __tablename__ = 'avaliacoes'

    id            = db.Column(db.Integer, primary_key=True)
    ciclo_id      = db.Column(db.Integer, db.ForeignKey('ciclos_avaliacao.id'), nullable=False)
    avaliado_id   = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    avaliador_id  = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    tipo          = db.Column(db.String(10), default='auto')

    # Critérios (1-5)
    tecnico         = db.Column(db.Integer)
    comunicacao     = db.Column(db.Integer)
    trabalho_equipe = db.Column(db.Integer)
    proatividade    = db.Column(db.Integer)
    entrega_prazo   = db.Column(db.Integer)

    pontos_fortes   = db.Column(db.Text)
    pontos_melhoria = db.Column(db.Text)
    comentarios     = db.Column(db.Text)
    status          = db.Column(db.String(15), default='pendente')

    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    avaliado    = db.relationship('Colaborador', foreign_keys=[avaliado_id], backref='avaliacoes_recebidas')
    avaliador   = db.relationship('User', foreign_keys=[avaliador_id])

    @property
    def media(self):
        notas = [self.tecnico, self.comunicacao, self.trabalho_equipe,
                 self.proatividade, self.entrega_prazo]
        notas = [n for n in notas if n is not None]
        return round(sum(notas) / len(notas), 1) if notas else None

    @property
    def tipo_display(self):
        return dict(TIPOS_AVALIACAO).get(self.tipo, self.tipo)

    @property
    def status_display(self):
        return dict(STATUS_AVALIACAO).get(self.status, self.status)


class Meta(db.Model):
    __tablename__ = 'metas'

    id             = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    ciclo_id       = db.Column(db.Integer, db.ForeignKey('ciclos_avaliacao.id'), nullable=True)
    titulo         = db.Column(db.String(200), nullable=False)
    descricao      = db.Column(db.Text)
    tipo           = db.Column(db.String(10), default='meta')
    prazo          = db.Column(db.Date)
    status         = db.Column(db.String(20), default='pendente')
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    colaborador = db.relationship('Colaborador', backref='metas')

    @property
    def status_info(self):
        for s in STATUS_META:
            if s[0] == self.status:
                return {'label': s[1], 'bg': s[2], 'color': s[3]}
        return {'label': self.status, 'bg': '#f1f5f9', 'color': '#475569'}

    @property
    def tipo_display(self):
        return dict(TIPOS_META).get(self.tipo, self.tipo)
