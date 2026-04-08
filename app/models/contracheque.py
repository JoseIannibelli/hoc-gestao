from app import db
from datetime import datetime

MESES = [
    (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
    (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
    (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro'),
]


class Contracheque(db.Model):
    __tablename__ = 'contracheques'

    id             = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    ano            = db.Column(db.Integer, nullable=False)
    mes            = db.Column(db.Integer, nullable=False)
    arquivo        = db.Column(db.String(200), nullable=False)   # nome do arquivo PDF
    uploaded_by    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    observacao     = db.Column(db.Text)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    colaborador    = db.relationship('Colaborador', backref='contracheques')
    uploader       = db.relationship('User', foreign_keys=[uploaded_by])

    __table_args__ = (
        db.UniqueConstraint('colaborador_id', 'ano', 'mes', name='uq_contracheque_colab_anomes'),
    )

    @property
    def mes_display(self):
        return dict(MESES).get(self.mes, str(self.mes))

    @property
    def periodo_display(self):
        return f'{self.mes_display}/{self.ano}'

    @property
    def arquivo_url(self):
        return f'/static/uploads/contracheques/{self.arquivo}'
