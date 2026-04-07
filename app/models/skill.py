from app import db
from datetime import datetime

CATEGORIAS_SKILL = [
    ('frontend',      'Frontend'),
    ('backend',       'Backend'),
    ('fullstack',     'Full Stack'),
    ('dados',         'Dados & Analytics'),
    ('cloud',         'Cloud & DevOps'),
    ('infra',         'Infraestrutura'),
    ('seguranca',     'Segurança'),
    ('gestao',        'Gestão & Metodologias'),
    ('soft_skill',    'Soft Skills'),
    ('outro',         'Outro'),
]

NIVEIS_SKILL = [
    ('basico',        'Básico',        1),
    ('intermediario', 'Intermediário', 2),
    ('avancado',      'Avançado',      3),
    ('especialista',  'Especialista',  4),
]


class Skill(db.Model):
    """Catálogo global de habilidades."""
    __tablename__ = 'skills'

    id        = db.Column(db.Integer, primary_key=True)
    nome      = db.Column(db.String(100), nullable=False, unique=True)
    categoria = db.Column(db.String(30))
    descricao = db.Column(db.Text)
    ativo     = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    colaboradores = db.relationship('ColaboradorSkill', backref='skill', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def categoria_display(self):
        return dict([(c[0], c[1]) for c in CATEGORIAS_SKILL]).get(self.categoria, self.categoria or '—')

    @property
    def total_colaboradores(self):
        return self.colaboradores.count()

    def __repr__(self):
        return f'<Skill {self.nome}>'


class ColaboradorSkill(db.Model):
    """Habilidade de um colaborador específico."""
    __tablename__ = 'colaborador_skills'

    id              = db.Column(db.Integer, primary_key=True)
    colaborador_id  = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    skill_id        = db.Column(db.Integer, db.ForeignKey('skills.id'), nullable=False)
    nivel           = db.Column(db.String(20), default='basico')
    anos_experiencia = db.Column(db.Float, default=0)
    principal       = db.Column(db.Boolean, default=False)  # skill em destaque no perfil
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('colaborador_id', 'skill_id'),)

    @property
    def nivel_display(self):
        return {n[0]: n[1] for n in NIVEIS_SKILL}.get(self.nivel, self.nivel or '—')

    @property
    def nivel_num(self):
        return {n[0]: n[2] for n in NIVEIS_SKILL}.get(self.nivel, 1)


class Certificacao(db.Model):
    """Certificações e cursos do colaborador."""
    __tablename__ = 'certificacoes'

    id              = db.Column(db.Integer, primary_key=True)
    colaborador_id  = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    nome            = db.Column(db.String(150), nullable=False)
    instituicao     = db.Column(db.String(150))
    data_obtencao   = db.Column(db.Date)
    data_expiracao  = db.Column(db.Date)
    url             = db.Column(db.String(300))
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    colaborador = db.relationship('Colaborador', backref='certificacoes')

    @property
    def expirado(self):
        from datetime import date
        if self.data_expiracao:
            return self.data_expiracao < date.today()
        return False
