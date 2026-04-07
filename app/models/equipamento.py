from app import db
from datetime import datetime

TIPOS_EQUIPAMENTO = [
    ('notebook',    'Notebook'),
    ('desktop',     'Desktop / Workstation'),
    ('monitor',     'Monitor'),
    ('teclado',     'Teclado'),
    ('mouse',       'Mouse'),
    ('headset',     'Headset / Fone'),
    ('celular',     'Celular / Smartphone'),
    ('tablet',      'Tablet'),
    ('impressora',  'Impressora'),
    ('nobreak',     'Nobreak / UPS'),
    ('roteador',    'Roteador / Switch'),
    ('outros',      'Outros'),
]

STATUS_EQUIPAMENTO = [
    ('disponivel',    'Disponível',      '#d1fae5', '#065f46'),
    ('alocado',       'Alocado',         '#dbeafe', '#1d4ed8'),
    ('manutencao',    'Em manutenção',   '#fef9c3', '#854d0e'),
    ('descartado',    'Descartado',      '#f1f5f9', '#64748b'),
]

ESTADOS_CONSERVACAO = [
    ('novo',     'Novo'),
    ('bom',      'Bom'),
    ('regular',  'Regular'),
    ('ruim',     'Ruim'),
]


class Equipamento(db.Model):
    __tablename__ = 'equipamentos'

    id                = db.Column(db.Integer, primary_key=True)
    tipo              = db.Column(db.String(30), nullable=False)
    marca             = db.Column(db.String(100))
    modelo            = db.Column(db.String(150))
    numero_serie      = db.Column(db.String(100), unique=True)
    numero_patrimonio = db.Column(db.String(100), unique=True)
    descricao         = db.Column(db.Text)
    status            = db.Column(db.String(20), default='disponivel')
    valor             = db.Column(db.Float)           # valor de aquisição (R$)
    data_aquisicao    = db.Column(db.Date)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at        = db.Column(db.DateTime, default=datetime.utcnow,
                                  onupdate=datetime.utcnow)

    alocacoes = db.relationship('AlocacaoEquipamento',
                                backref='equipamento',
                                lazy='dynamic',
                                order_by='AlocacaoEquipamento.data_entrega.desc()')

    @property
    def tipo_display(self):
        return dict(TIPOS_EQUIPAMENTO).get(self.tipo, self.tipo)

    @property
    def status_info(self):
        for s in STATUS_EQUIPAMENTO:
            if s[0] == self.status:
                return {'label': s[1], 'bg': s[2], 'color': s[3]}
        return {'label': self.status, 'bg': '#f1f5f9', 'color': '#64748b'}

    @property
    def alocacao_ativa(self):
        return self.alocacoes.filter_by(ativo=True).first()

    @property
    def nome_completo(self):
        partes = [self.tipo_display]
        if self.marca:
            partes.append(self.marca)
        if self.modelo:
            partes.append(self.modelo)
        return ' — '.join(partes)


class AlocacaoEquipamento(db.Model):
    __tablename__ = 'alocacoes_equipamento'

    id                      = db.Column(db.Integer, primary_key=True)
    equipamento_id          = db.Column(db.Integer, db.ForeignKey('equipamentos.id'),
                                        nullable=False)
    colaborador_id          = db.Column(db.Integer, db.ForeignKey('colaboradores.id'),
                                        nullable=False)
    data_entrega            = db.Column(db.Date, nullable=False)
    data_prevista_devolucao = db.Column(db.Date)
    data_devolucao          = db.Column(db.Date)
    estado_entrega          = db.Column(db.String(20), default='bom')
    estado_devolucao        = db.Column(db.String(20))
    observacoes             = db.Column(db.Text)
    ativo                   = db.Column(db.Boolean, default=True)  # alocação vigente
    created_at              = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at              = db.Column(db.DateTime, default=datetime.utcnow,
                                        onupdate=datetime.utcnow)

    colaborador = db.relationship('Colaborador', backref='alocacoes_equipamento')

    @property
    def estado_entrega_display(self):
        return dict(ESTADOS_CONSERVACAO).get(self.estado_entrega, self.estado_entrega)

    @property
    def estado_devolucao_display(self):
        return dict(ESTADOS_CONSERVACAO).get(self.estado_devolucao or '', '—')

    @property
    def dias_com_colaborador(self):
        fim = self.data_devolucao or datetime.utcnow().date()
        return (fim - self.data_entrega).days
