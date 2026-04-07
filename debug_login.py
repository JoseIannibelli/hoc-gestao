from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    db.create_all()
    
    # Verifica usuários existentes
    users = User.query.all()
    print(f"Total de usuários no banco: {len(users)}")
    for u in users:
        print(f"  - ID:{u.id} | Email:{u.email} | Role:{u.role} | Ativo:{u.ativo}")
    
    # Testa a senha diretamente
    admin = User.query.filter_by(email='admin@hoc.com').first()
    if admin:
        ok = admin.check_password('hoc@2024')
        print(f"\nTeste de senha 'hoc@2024': {'✓ CORRETA' if ok else '✗ ERRADA'}")
        print(f"Hash armazenado: {admin.password_hash[:40]}...")
    else:
        print("\nUsuário admin NÃO encontrado — criando agora...")
        admin = User(nome='Administrador', email='admin@hoc.com', role='gestor', ativo=True)
        admin.set_password('hoc@2024')
        db.session.add(admin)
        db.session.commit()
        ok = admin.check_password('hoc@2024')
        print(f"Admin criado. Teste de senha: {'✓ OK' if ok else '✗ FALHOU'}")
