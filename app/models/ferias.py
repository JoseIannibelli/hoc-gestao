from app import db
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

STATUS_PERIODO = [
    ('em_aquisicao', 'Em Aquisição'),
    ('disponivel',   'Disponível'),
    ('parcial',      'Parcialmente Gozado'),
    ('gozado',       'Gozado'),
    ('vencido',      'Vencido'),
]

STATUS_SOLICITACAO = [
    ('pendente',  'Pendente'),
    ('aprovada',  'Aprovada'),
    ('recusada',  'Recusada'),
    ('cancelada', 'Cancelada'),
    ('gozada',    'Gozada'),
]


class PeriodoAquisitivo(db.Model):
    """Período de 12 meses em que o colaborador adquire direito a férias."""
    __tablename__ = 'periodos_aquisitivos'

    id             = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    data_inicio    = db.Column(db.Date, nullable=False)   # data de admissão ou aniversário
    data_fim       = db.Column(db.Date, nullable=False)   # data_inicio + 12 meses - 1 dia
    # Período concessivo: até 12 meses após o fim do aquisitivo
    data_limite    = db.Column(db.Date, nullable=False)   # data_fim + 12 meses
    dias_direito   = db.Column(db.Integer, default=30)    # normalmente 30
    dias_gozados   = db.Column(db.Integer, default=0)
    status         = db.Column(db.String(20), default='em_aquisicao')
    observacao     = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow)

    colaborador    = db.relationship('Colaborador', backref='periodos_aquisitivos')
    solicitacoes   = db.relationship('SolicitacaoFerias', backref='periodo',
                                     lazy='dynamic', cascade='all, delete-orphan')

    @property
    def dias_saldo(self):
        return self.dias_direito - self.dias_gozados

    @property
    def status_display(self):
        return dict(STATUS_PERIODO).get(self.status, self.status)

    @property
    def esta_disponivel(self):
        """True se o período aquisitivo já completou e ainda há saldo."""
        return (self.status in ('disponivel', 'parcial')
                and self.dias_saldo > 0
                and date.today() >= self.data_fim)

    @property
    def esta_vencendo(self):
        """True se faltam 60 dias ou menos para vencer o período concessivo."""
        if self.data_limite:
            delta = (self.data_limite - date.today()).days
            return 0 < delta <= 60
        return False


class SolicitacaoFerias(db.Model):
    """Solicitação de gozo de férias feita pelo colaborador."""
    __tablename__ = 'solicitacoes_ferias'

    id                 = db.Column(db.Integer, primary_key=True)
    colaborador_id     = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    periodo_id         = db.Column(db.Integer, db.ForeignKey('periodos_aquisitivos.id'), nullable=False)
    data_inicio        = db.Column(db.Date, nullable=False)
    data_fim           = db.Column(db.Date, nullable=False)
    dias_solicitados   = db.Column(db.Integer, nullable=False)
    abono_pecuniario   = db.Column(db.Boolean, default=False)  # vender até 10 dias
    dias_abono         = db.Column(db.Integer, default=0)
    observacao         = db.Column(db.Text)
    status             = db.Column(db.String(20), default='pendente')
    observacao_gestor  = db.Column(db.Text)
    aprovado_por       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    aprovado_em        = db.Column(db.DateTime, nullable=True)
    created_at         = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at         = db.Column(db.DateTime, default=datetime.utcnow)

    colaborador        = db.relationship('Colaborador', backref='solicitacoes_ferias')
    aprovador          = db.relationship('User', foreign_keys=[aprovado_por])

    @property
    def status_display(self):
        return dict(STATUS_SOLICITACAO).get(self.status, self.status)

    @property
    def total_dias(self):
        if self.data_inicio and self.data_fim:
            return (self.data_fim - self.data_inicio).days + 1
        return self.dias_solicitados
