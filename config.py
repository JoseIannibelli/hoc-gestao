import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hoc-dev-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'hoc.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    APP_NAME = 'HOC Gestão'

    # ── E-mail / Flask-Mail ────────────────────────────────────────────────
    # Defina MAIL_ENABLED = True apenas no servidor de produção.
    # Em desenvolvimento o link de reset é exibido no console do servidor.
    MAIL_ENABLED       = os.environ.get('MAIL_ENABLED', 'false').lower() == 'true'

    MAIL_SERVER        = os.environ.get('MAIL_SERVER',   'smtp.office365.com')
    MAIL_PORT          = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS       = os.environ.get('MAIL_USE_TLS',  'true').lower() == 'true'
    MAIL_USE_SSL       = False
    MAIL_USERNAME      = os.environ.get('MAIL_USERNAME', '')   # ex: voce@hoc.com.br
    MAIL_PASSWORD      = os.environ.get('MAIL_PASSWORD', '')   # senha do Outlook
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'HOC Gestão <noreply@hoc.com.br>')


class DevelopmentConfig(Config):
    DEBUG = True
    # Em dev, o link de reset aparece no terminal — sem necessidade de SMTP
    MAIL_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    # Em produção, leia as variáveis de ambiente no servidor:
    #   export MAIL_ENABLED=true
    #   export MAIL_USERNAME=voce@hoc.com.br
    #   export MAIL_PASSWORD=sua_senha
    MAIL_ENABLED = os.environ.get('MAIL_ENABLED', 'false').lower() == 'true'


config = {
    'development': DevelopmentConfig,
    'production':  ProductionConfig,
    'default':     DevelopmentConfig
}
