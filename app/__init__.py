from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from config import config

db = SQLAlchemy()
mail = Mail()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'warning'


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)

    # Blueprints
    from app.routes.main         import main_bp
    from app.routes.auth         import auth_bp
    from app.routes.colaboradores import colaboradores_bp
    from app.routes.usuarios     import usuarios_bp
    from app.routes.skills       import skills_bp
    from app.routes.projetos     import projetos_bp
    from app.routes.avaliacoes   import avaliacoes_bp
    from app.routes.ponto        import ponto_bp
    from app.routes.equipamentos import equipamentos_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(colaboradores_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(skills_bp)
    app.register_blueprint(projetos_bp)
    app.register_blueprint(avaliacoes_bp)
    app.register_blueprint(ponto_bp)
    app.register_blueprint(equipamentos_bp)

    with app.app_context():
        from app.models import User, Colaborador  # noqa
        from app.models.skill       import Skill, ColaboradorSkill, Certificacao              # noqa
        from app.models.projeto     import Projeto, Alocacao                                  # noqa
        from app.models.avaliacao   import CicloAvaliacao, Avaliacao, Meta                   # noqa
        from app.models.ponto       import RegistroPonto, FechamentoPonto, SolicitacaoCorrecao  # noqa
        from app.models.equipamento import Equipamento, AlocacaoEquipamento                  # noqa
        db.create_all()

        # Bootstrap: cria admin automaticamente se não existir nenhum usuário
        import os
        if User.query.count() == 0:
            email = os.environ.get('ADMIN_EMAIL', 'admin@hoc.com.br')
            senha = os.environ.get('ADMIN_PASSWORD', 'hoc@2024')
            admin = User(nome='Administrador', email=email, role='admin')
            admin.set_password(senha)
            db.session.add(admin)
            db.session.commit()

    @app.cli.command('criar-admin')
    def criar_admin():
        """Cria o usuário administrador padrão (use apenas no primeiro deploy)."""
        from app.models.user import User
        import os
        email = os.environ.get('ADMIN_EMAIL', 'admin@hoc.com.br')
        senha = os.environ.get('ADMIN_PASSWORD', 'hoc@2024')
        if User.query.filter_by(email=email).first():
            print(f'Usuário {email} já existe.')
            return
        admin = User(nome='Administrador', email=email, role='admin')
        admin.set_password(senha)
        db.session.add(admin)
        db.session.commit()
        print(f'Admin criado: {email}')

    return app
