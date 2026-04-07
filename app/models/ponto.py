from app import db
from datetime import datetime, date, timedelta

TIPOS_OCORRENCIA = [
    ('normal',       'Dia normal'),
    ('falta',        'Falta'),
    ('falta_just',   'Falta justificada'),
    ('feriado',      'Feriado'),
    ('ferias',       'Férias'),
    ('afastamento',  'Afastamento médico'),
    ('folga',        'Folga compensatória'),
    ('meio_periodo', 'Meio período'),
]

STATUS_FECHAMENTO = [
    ('aberto',       'Em aberto',          '#dbeafe', '#1d4ed8'),
    ('fechado_auto', 'Fechado (automático)','#fef3c7', '#92400e'),
    ('submetido',    'Submetido',           '#fef9c3', '#854d0e'),
    ('aprovado',     'Aprovado',            '#d1fae5', '#065f46'),
    ('rejeitado',    'Rejeitado',           '#fee2e2', '#991b1b'),
]

STATUS_CORRECAO = [
    ('pendente',  'Pendente',  '#fef9c3', '#854d0e'),
    ('aprovada',  'Aprovada',  '#d1fae5', '#065f46'),
    ('rejeitada', 'Rejeitada', '#fee2e2', '#991b1b'),
]

CARGA_HORARIA_PADRAO = 8.0  # horas por dia


class RegistroPonto(db.Model):
    """Registro diário de ponto de um colaborador."""
    __tablename__ = 'registros_ponto'

    id             = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    data           = db.Column(db.Date, nullable=False)

    # 4 marcações do dia
    entrada        = db.Column(db.Time)
    inicio_almoco  = db.Column(db.Time)
    retorno_almoco = db.Column(db.Time)
    saida          = db.Column(db.Time)

    # Ocorrência / tipo do dia
    tipo           = db.Column(db.String(20), default='normal')
    observacao     = db.Column(db.Text)
    justificativa  = db.Column(db.Text)

    created_at     = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at     = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    colaborador = db.relationship('Colaborador', backref='registros_ponto')

    __table_args__ = (
        db.UniqueConstraint('colaborador_id', 'data', name='uq_ponto_colab_data'),
    )

    @property
    def horas_trabalhadas(self):
        if not self.entrada or not self.saida:
            return None
        entrada = datetime.combine(self.data, self.entrada)
        saida   = datetime.combine(self.data, self.saida)
        total   = saida - entrada
        if self.inicio_almoco and self.retorno_almoco:
            ini_alm = datetime.combine(self.data, self.inicio_almoco)
            ret_alm = datetime.combine(self.data, self.retorno_almoco)
            total  -= (ret_alm - ini_alm)
        return max(total, timedelta(0))

    @property
    def horas_trabalhadas_decimal(self):
        ht = self.horas_trabalhadas
        if ht is None:
            return 0.0
        return round(ht.total_seconds() / 3600, 2)

    @property
    def saldo_horas(self):
        if self.tipo in ('feriado', 'ferias', 'folga'):
            return 0.0
        if self.tipo in ('falta', 'falta_just', 'afastamento'):
            return -CARGA_HORARIA_PADRAO
        return round(self.horas_trabalhadas_decimal - CARGA_HORARIA_PADRAO, 2)

    @property
    def tipo_display(self):
        return dict([(t[0], t[1]) for t in TIPOS_OCORRENCIA]).get(self.tipo, self.tipo)

    @property
    def completo(self):
        return all([self.entrada, self.inicio_almoco, self.retorno_almoco, self.saida])

    def fmt_time(self, t):
        return t.strftime('%H:%M') if t else '—'


class FechamentoPonto(db.Model):
    """Fechamento mensal da folha de ponto."""
    __tablename__ = 'fechamentos_ponto'

    id             = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    ano            = db.Column(db.Integer, nullable=False)
    mes            = db.Column(db.Integer, nullable=False)
    status         = db.Column(db.String(15), default='aberto')

    total_dias_uteis  = db.Column(db.Integer, default=0)
    total_horas_trab  = db.Column(db.Float, default=0.0)
    total_faltas      = db.Column(db.Integer, default=0)
    saldo_banco_horas = db.Column(db.Float, default=0.0)

    observacao_colab  = db.Column(db.Text)
    observacao_gestor = db.Column(db.Text)

    submetido_em  = db.Column(db.DateTime)
    aprovado_em   = db.Column(db.DateTime)
    aprovado_por  = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at    = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    colaborador  = db.relationship('Colaborador', backref='fechamentos_ponto')
    aprovador    = db.relationship('User', foreign_keys=[aprovado_por])

    __table_args__ = (
        db.UniqueConstraint('colaborador_id', 'ano', 'mes', name='uq_fechamento_mes'),
    )

    @property
    def mes_nome(self):
        nomes = ['', 'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                 'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        return nomes[self.mes]

    @property
    def status_info(self):
        for s in STATUS_FECHAMENTO:
            if s[0] == self.status:
                return {'label': s[1], 'bg': s[2], 'color': s[3]}
        return {'label': self.status, 'bg': '#f1f5f9', 'color': '#475569'}

    @property
    def bloqueado(self):
        """Mês não pode ser editado diretamente (só via solicitação de correção)."""
        return self.status in ('fechado_auto', 'submetido', 'aprovado')

    @property
    def saldo_formatado(self):
        s = self.saldo_banco_horas
        h = int(abs(s))
        m = int((abs(s) - h) * 60)
        return f"{'+'  if s >= 0 else '-'}{h:02d}:{m:02d}"


class SolicitacaoCorrecao(db.Model):
    """Solicitação de correção retroativa de registro de ponto."""
    __tablename__ = 'solicitacoes_correcao'

    id             = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    data_registro  = db.Column(db.Date, nullable=False)   # Dia a ser corrigido

    # Valores originais (snapshot)
    entrada_orig        = db.Column(db.Time)
    inicio_almoco_orig  = db.Column(db.Time)
    retorno_almoco_orig = db.Column(db.Time)
    saida_orig          = db.Column(db.Time)
    tipo_orig           = db.Column(db.String(20))

    # Valores solicitados (correção)
    entrada_novo        = db.Column(db.Time)
    inicio_almoco_novo  = db.Column(db.Time)
    retorno_almoco_novo = db.Column(db.Time)
    saida_novo          = db.Column(db.Time)
    tipo_novo           = db.Column(db.String(20))

    motivo             = db.Column(db.Text, nullable=False)

    status             = db.Column(db.String(15), default='pendente')
    observacao_gestor  = db.Column(db.Text)

    aprovado_em        = db.Column(db.DateTime)
    aprovado_por       = db.Column(db.Integer, db.ForeignKey('users.id'))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    colaborador = db.relationship('Colaborador', backref='solicitacoes_correcao')
    aprovador   = db.relationship('User', foreign_keys=[aprovado_por])

    def fmt_time(self, t):
        return t.strftime('%H:%M') if t else '—'

    @property
    def status_info(self):
        for s in STATUS_CORRECAO:
            if s[0] == self.status:
                return {'label': s[1], 'bg': s[2], 'color': s[3]}
        return {'label': self.status, 'bg': '#f1f5f9', 'color': '#475569'}

    @property
    def tipo_novo_display(self):
        return dict([(t[0], t[1]) for t in TIPOS_OCORRENCIA]).get(self.tipo_novo or '', '—')

    @property
    def tipo_orig_display(self):
        return dict([(t[0], t[1]) for t in TIPOS_OCORRENCIA]).get(self.tipo_orig or '', '—')
