from app import db
from datetime import datetime

STATUS_PROJETO = [
    ('planejamento',  'Planejamento',  '#dbeafe', '#1d4ed8'),
    ('em_andamento',  'Em andamento',  '#d1fae5', '#065f46'),
    ('pausado',       'Pausado',       '#fef9c3', '#854d0e'),
    ('concluido',     'Concluído',     '#ede9fe', '#6d28d9'),
    ('cancelado',     'Cancelado',     '#fee2e2', '#991b1b'),
]

PAPEIS_ALOCACAO = [
    ('desenvolvedor',  'Desenvolvedor(a)'),
    ('lider_tecnico',  'Líder Técnico'),
    ('arquiteto',      'Arquiteto(a)'),
    ('qa',             'QA / Tester'),
    ('devops',         'DevOps'),
    ('analista',       'Analista'),
    ('consultor',      'Consultor(a)'),
    ('pm',             'Gerente de Projeto'),
    ('scrum_master',   'Scrum Master'),
    ('po',             'Product Owner'),
    ('outro',          'Outro'),
]


class Projeto(db.Model):
    __tablename__ = 'projetos'

    id               = db.Column(db.Integer, primary_key=True)
    nome             = db.Column(db.String(150), nullable=False)
    cliente          = db.Column(db.String(150))
    descricao        = db.Column(db.Text)
    status           = db.Column(db.String(20), default='planejamento')
    data_inicio      = db.Column(db.Date)
    data_fim_prevista = db.Column(db.Date)
    data_fim_real    = db.Column(db.Date)
    gestor_id        = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    lider_id         = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=True)
    created_by       = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at       = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    gestor     = db.relationship('User', foreign_keys=[gestor_id], backref='projetos_gerenciados')
    lider      = db.relationship('Colaborador', foreign_keys=[lider_id], backref='projetos_liderados')
    alocacoes  = db.relationship('Alocacao', backref='projeto', lazy='dynamic', cascade='all, delete-orphan')
    criador    = db.relationship('User', foreign_keys=[created_by])

    @property
    def status_info(self):
        for s in STATUS_PROJETO:
            if s[0] == self.status:
                return {'label': s[1], 'bg': s[2], 'color': s[3]}
        return {'label': self.status, 'bg': '#f1f5f9', 'color': '#475569'}

    @property
    def tem_lider(self):
        return self.lider_id is not None

    @property
    def responsavel_nome(self):
        """Retorna o líder; se não houver, indica que o gestor assume."""
        if self.lider:
            return self.lider.nome
        if self.gestor:
            return f'{self.gestor.nome} (Gestor)'
        return '—'

    @property
    def total_colaboradores(self):
        return self.alocacoes.filter_by(ativo=True).count()

    @property
    def percentual_medio(self):
        ativas = self.alocacoes.filter_by(ativo=True).all()
        if not ativas:
            return 0
        return round(sum(a.percentual for a in ativas) / len(ativas))

    def __repr__(self):
        return f'<Projeto {self.nome}>'


class Alocacao(db.Model):
    __tablename__ = 'alocacoes'

    id             = db.Column(db.Integer, primary_key=True)
    projeto_id     = db.Column(db.Integer, db.ForeignKey('projetos.id'), nullable=False)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    papel          = db.Column(db.String(30), default='desenvolvedor')
    percentual     = db.Column(db.Integer, default=100)   # 0-100
    data_inicio    = db.Column(db.Date)
    data_fim       = db.Column(db.Date)
    ativo          = db.Column(db.Boolean, default=True)
    observacao     = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    colaborador = db.relationship('Colaborador', backref='alocacoes')

    @property
    def papel_display(self):
        return dict(PAPEIS_ALOCACAO).get(self.papel, self.papel or '—')

    __table_args__ = (
        db.UniqueConstraint('projeto_id', 'colaborador_id', name='uq_projeto_colaborador'),
    )
