"""
Script de migração — adiciona colunas e tabelas novas ao banco existente.
Execute sempre que houver mudanças no modelo: python3 migrar_db.py
"""
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), 'hoc.db')

def col_existe(cur, tabela, coluna):
    cur.execute(f"PRAGMA table_info({tabela})")
    return any(row[1] == coluna for row in cur.fetchall())

def tabela_existe(cur, tabela):
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabela,))
    return cur.fetchone() is not None

conn = sqlite3.connect(DB_PATH)
cur  = conn.cursor()

# ── Novas colunas em tabelas existentes ────────────────────────────────────────
novas_colunas = [
    ("colaboradores", "regime",          "VARCHAR(20)"),
    ("colaboradores", "cidade",          "VARCHAR(100)"),
    ("colaboradores", "estado",          "VARCHAR(2)"),
    ("users",         "colaborador_id",  "INTEGER REFERENCES colaboradores(id)"),
    ("users",         "ultimo_acesso",   "DATETIME"),
    ("users",         "reset_token",     "VARCHAR(256)"),
    ("users",         "reset_token_exp", "DATETIME"),
    ("projetos",      "gestor_id",       "INTEGER REFERENCES users(id)"),
]

print("── Colunas ──────────────────────────")
for tabela, coluna, tipo in novas_colunas:
    if tabela_existe(cur, tabela) and not col_existe(cur, tabela, coluna):
        cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
        print(f"  + {tabela}.{coluna}")
    else:
        print(f"  ✓ {tabela}.{coluna}")

# ── Novas tabelas ──────────────────────────────────────────────────────────────
novas_tabelas = {
    "skills": """
        CREATE TABLE IF NOT EXISTS skills (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nome       VARCHAR(100) NOT NULL UNIQUE,
            categoria  VARCHAR(30),
            descricao  TEXT,
            ativo      BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    "colaborador_skills": """
        CREATE TABLE IF NOT EXISTS colaborador_skills (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id   INTEGER NOT NULL REFERENCES colaboradores(id),
            skill_id         INTEGER NOT NULL REFERENCES skills(id),
            nivel            VARCHAR(20) DEFAULT 'basico',
            anos_experiencia REAL DEFAULT 0,
            principal        BOOLEAN DEFAULT 0,
            created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(colaborador_id, skill_id)
        )""",
    "certificacoes": """
        CREATE TABLE IF NOT EXISTS certificacoes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER NOT NULL REFERENCES colaboradores(id),
            nome           VARCHAR(150) NOT NULL,
            instituicao    VARCHAR(150),
            data_obtencao  DATE,
            data_expiracao DATE,
            url            VARCHAR(300),
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    "projetos": """
        CREATE TABLE IF NOT EXISTS projetos (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            nome              VARCHAR(150) NOT NULL,
            cliente           VARCHAR(150),
            descricao         TEXT,
            status            VARCHAR(20) DEFAULT 'planejamento',
            data_inicio       DATE,
            data_fim_prevista DATE,
            data_fim_real     DATE,
            lider_id          INTEGER REFERENCES colaboradores(id),
            created_by        INTEGER REFERENCES users(id),
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    "alocacoes": """
        CREATE TABLE IF NOT EXISTS alocacoes (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            projeto_id     INTEGER NOT NULL REFERENCES projetos(id),
            colaborador_id INTEGER NOT NULL REFERENCES colaboradores(id),
            papel          VARCHAR(30) DEFAULT 'desenvolvedor',
            percentual     INTEGER DEFAULT 100,
            data_inicio    DATE,
            data_fim       DATE,
            ativo          BOOLEAN DEFAULT 1,
            observacao     TEXT,
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(projeto_id, colaborador_id)
        )""",
    "ciclos_avaliacao": """
        CREATE TABLE IF NOT EXISTS ciclos_avaliacao (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            nome        VARCHAR(100) NOT NULL,
            descricao   TEXT,
            data_inicio DATE,
            data_fim    DATE,
            status      VARCHAR(20) DEFAULT 'aberto',
            created_by  INTEGER REFERENCES users(id),
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    "avaliacoes": """
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            ciclo_id        INTEGER NOT NULL REFERENCES ciclos_avaliacao(id),
            avaliado_id     INTEGER NOT NULL REFERENCES colaboradores(id),
            avaliador_id    INTEGER NOT NULL REFERENCES users(id),
            tipo            VARCHAR(10) DEFAULT 'auto',
            tecnico         INTEGER,
            comunicacao     INTEGER,
            trabalho_equipe INTEGER,
            proatividade    INTEGER,
            entrega_prazo   INTEGER,
            pontos_fortes   TEXT,
            pontos_melhoria TEXT,
            comentarios     TEXT,
            status          VARCHAR(15) DEFAULT 'pendente',
            created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    "metas": """
        CREATE TABLE IF NOT EXISTS metas (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER NOT NULL REFERENCES colaboradores(id),
            ciclo_id       INTEGER REFERENCES ciclos_avaliacao(id),
            titulo         VARCHAR(200) NOT NULL,
            descricao      TEXT,
            tipo           VARCHAR(10) DEFAULT 'meta',
            prazo          DATE,
            status         VARCHAR(20) DEFAULT 'pendente',
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    "registros_ponto": """
        CREATE TABLE IF NOT EXISTS registros_ponto (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id INTEGER NOT NULL REFERENCES colaboradores(id),
            data           DATE NOT NULL,
            entrada        TIME,
            inicio_almoco  TIME,
            retorno_almoco TIME,
            saida          TIME,
            tipo           VARCHAR(20) DEFAULT 'normal',
            observacao     TEXT,
            justificativa  TEXT,
            created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(colaborador_id, data)
        )""",
    "fechamentos_ponto": """
        CREATE TABLE IF NOT EXISTS fechamentos_ponto (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id    INTEGER NOT NULL REFERENCES colaboradores(id),
            ano               INTEGER NOT NULL,
            mes               INTEGER NOT NULL,
            status            VARCHAR(15) DEFAULT 'aberto',
            total_dias_uteis  INTEGER DEFAULT 0,
            total_horas_trab  REAL DEFAULT 0.0,
            total_faltas      INTEGER DEFAULT 0,
            saldo_banco_horas REAL DEFAULT 0.0,
            observacao_colab  TEXT,
            observacao_gestor TEXT,
            submetido_em      DATETIME,
            aprovado_em       DATETIME,
            aprovado_por      INTEGER REFERENCES users(id),
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(colaborador_id, ano, mes)
        )""",
    "solicitacoes_correcao": """
        CREATE TABLE IF NOT EXISTS solicitacoes_correcao (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            colaborador_id      INTEGER NOT NULL REFERENCES colaboradores(id),
            data_registro       DATE NOT NULL,
            entrada_orig        TIME,
            inicio_almoco_orig  TIME,
            retorno_almoco_orig TIME,
            saida_orig          TIME,
            tipo_orig           VARCHAR(20),
            entrada_novo        TIME,
            inicio_almoco_novo  TIME,
            retorno_almoco_novo TIME,
            saida_novo          TIME,
            tipo_novo           VARCHAR(20),
            motivo              TEXT NOT NULL,
            status              VARCHAR(15) DEFAULT 'pendente',
            observacao_gestor   TEXT,
            aprovado_em         DATETIME,
            aprovado_por        INTEGER REFERENCES users(id),
            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    "equipamentos": """
        CREATE TABLE IF NOT EXISTS equipamentos (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo              VARCHAR(30) NOT NULL DEFAULT 'outros',
            marca             VARCHAR(100),
            modelo            VARCHAR(100),
            numero_serie      VARCHAR(150),
            numero_patrimonio VARCHAR(100),
            descricao         TEXT,
            status            VARCHAR(20) NOT NULL DEFAULT 'disponivel',
            valor             REAL,
            data_aquisicao    DATE,
            created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
    "alocacoes_equipamento": """
        CREATE TABLE IF NOT EXISTS alocacoes_equipamento (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            equipamento_id          INTEGER NOT NULL REFERENCES equipamentos(id),
            colaborador_id          INTEGER NOT NULL REFERENCES colaboradores(id),
            data_entrega            DATE NOT NULL,
            data_prevista_devolucao DATE,
            data_devolucao          DATE,
            estado_entrega          VARCHAR(20) DEFAULT 'bom',
            estado_devolucao        VARCHAR(20),
            observacoes             TEXT,
            ativo                   BOOLEAN NOT NULL DEFAULT 1,
            created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP
        )""",
}

print("\n── Tabelas ──────────────────────────")
for nome, ddl in novas_tabelas.items():
    if not tabela_existe(cur, nome):
        cur.execute(ddl)
        print(f"  + tabela '{nome}' criada")
    else:
        print(f"  ✓ tabela '{nome}' já existe")

# ── Renomear role colaborador → tecnico ───────────────────────────────────────
print("\n── Roles ────────────────────────────")
cur.execute("SELECT COUNT(*) FROM users WHERE role = 'colaborador'")
n = cur.fetchone()[0]
if n > 0:
    cur.execute("UPDATE users SET role = 'tecnico' WHERE role = 'colaborador'")
    print(f"  + {n} usuário(s) com role='colaborador' renomeado(s) para 'tecnico'")
else:
    print("  ✓ nenhum usuário com role='colaborador' (já migrado)")

conn.commit()
conn.close()
print("\nMigração concluída!")
