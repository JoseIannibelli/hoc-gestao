from app import db
from datetime import datetime


AREAS = [
    ('desenvolvimento', 'Desenvolvimento'),
    ('infraestrutura', 'Infraestrutura'),
    ('dados', 'Dados & Analytics'),
    ('gestao', 'Gestão de TI'),
    ('seguranca', 'Segurança da Informação'),
    ('arquitetura', 'Arquitetura de Sistemas'),
    ('qualidade', 'Qualidade / QA'),
    ('suporte', 'Suporte Técnico'),
    ('comercial', 'Comercial / Pré-venda'),
    ('outro', 'Outro'),
]

SENIORIDADES = [
    ('estagiario', 'Estagiário'),
    ('junior', 'Júnior'),
    ('pleno', 'Pleno'),
    ('senior', 'Sênior'),
    ('especialista', 'Especialista'),
    ('lider', 'Líder Técnico'),
    ('gerente', 'Gerente'),
    ('diretor', 'Diretor'),
]

REGIMES = [
    ('clt', 'CLT'),
    ('pj', 'Pessoa Jurídica (PJ)'),
    ('estagio', 'Estágio'),
    ('temporario', 'Temporário'),
    ('terceirizado', 'Terceirizado'),
]

ESTADOS_BR = [
    ('AC', 'Acre'), ('AL', 'Alagoas'), ('AP', 'Amapá'), ('AM', 'Amazonas'),
    ('BA', 'Bahia'), ('CE', 'Ceará'), ('DF', 'Distrito Federal'),
    ('ES', 'Espírito Santo'), ('GO', 'Goiás'), ('MA', 'Maranhão'),
    ('MT', 'Mato Grosso'), ('MS', 'Mato Grosso do Sul'), ('MG', 'Minas Gerais'),
    ('PA', 'Pará'), ('PB', 'Paraíba'), ('PR', 'Paraná'), ('PE', 'Pernambuco'),
    ('PI', 'Piauí'), ('RJ', 'Rio de Janeiro'), ('RN', 'Rio Grande do Norte'),
    ('RS', 'Rio Grande do Sul'), ('RO', 'Rondônia'), ('RR', 'Roraima'),
    ('SC', 'Santa Catarina'), ('SP', 'São Paulo'), ('SE', 'Sergipe'),
    ('TO', 'Tocantins'),
]


class Colaborador(db.Model):
    __tablename__ = 'colaboradores'

    id = db.Column(db.Integer, primary_key=True)

    # Dados pessoais
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    telefone = db.Column(db.String(20))
    cpf = db.Column(db.String(14), unique=True)
    data_nascimento = db.Column(db.Date)
    foto = db.Column(db.String(200))

    # Dados profissionais
    cargo = db.Column(db.String(100))
    senioridade = db.Column(db.String(20))
    area = db.Column(db.String(50))
    regime = db.Column(db.String(20))
    data_admissao = db.Column(db.Date)
    linkedin = db.Column(db.String(200))
    bio = db.Column(db.Text)

    # Localização
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))

    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Colaborador {self.nome}>'

    @property
    def senioridade_display(self):
        return dict(SENIORIDADES).get(self.senioridade, self.senioridade or '—')

    @property
    def area_display(self):
        return dict(AREAS).get(self.area, self.area or '—')

    @property
    def regime_display(self):
        return dict(REGIMES).get(self.regime, self.regime or '—')

    @property
    def estado_display(self):
        return dict(ESTADOS_BR).get(self.estado, self.estado or '—')

    @property
    def foto_url(self):
        if self.foto:
            return f'/static/uploads/colaboradores/{self.foto}'
        return '/static/img/avatar_default.png'
