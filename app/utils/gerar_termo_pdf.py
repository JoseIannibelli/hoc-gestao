"""
Geração do Termo de Responsabilidade de Equipamento em PDF.
Usa ReportLab (Platypus) para layout profissional, pronto para impressão e assinatura.
"""
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, HRFlowable, KeepTogether)


# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL_ESCURO  = colors.HexColor('#1E3A5F')
AZUL_MEDIO   = colors.HexColor('#2D6A9F')
AZUL_CLARO   = colors.HexColor('#DBEAFE')
CINZA_CLARO  = colors.HexColor('#F8FAFC')
CINZA_BORDA  = colors.HexColor('#CBD5E1')
TEXTO_ESCURO = colors.HexColor('#1E293B')
TEXTO_MUTED  = colors.HexColor('#64748B')


def _estilos():
    base = getSampleStyleSheet()
    estilos = {
        'titulo_empresa': ParagraphStyle(
            'titulo_empresa', parent=base['Normal'],
            fontSize=16, fontName='Helvetica-Bold',
            textColor=AZUL_ESCURO, alignment=TA_CENTER, spaceAfter=2,
        ),
        'subtitulo_empresa': ParagraphStyle(
            'subtitulo_empresa', parent=base['Normal'],
            fontSize=9, fontName='Helvetica',
            textColor=TEXTO_MUTED, alignment=TA_CENTER, spaceAfter=0,
        ),
        'titulo_doc': ParagraphStyle(
            'titulo_doc', parent=base['Normal'],
            fontSize=13, fontName='Helvetica-Bold',
            textColor=AZUL_ESCURO, alignment=TA_CENTER,
            spaceBefore=14, spaceAfter=4,
        ),
        'subtitulo_doc': ParagraphStyle(
            'subtitulo_doc', parent=base['Normal'],
            fontSize=9, fontName='Helvetica',
            textColor=TEXTO_MUTED, alignment=TA_CENTER, spaceAfter=0,
        ),
        'secao': ParagraphStyle(
            'secao', parent=base['Normal'],
            fontSize=9, fontName='Helvetica-Bold',
            textColor=colors.white, alignment=TA_LEFT,
        ),
        'campo_label': ParagraphStyle(
            'campo_label', parent=base['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold',
            textColor=TEXTO_MUTED, alignment=TA_LEFT, spaceAfter=1,
        ),
        'campo_valor': ParagraphStyle(
            'campo_valor', parent=base['Normal'],
            fontSize=9.5, fontName='Helvetica',
            textColor=TEXTO_ESCURO, alignment=TA_LEFT,
        ),
        'clausula_num': ParagraphStyle(
            'clausula_num', parent=base['Normal'],
            fontSize=9, fontName='Helvetica-Bold',
            textColor=AZUL_ESCURO, alignment=TA_LEFT,
            spaceBefore=6, spaceAfter=1,
        ),
        'clausula_txt': ParagraphStyle(
            'clausula_txt', parent=base['Normal'],
            fontSize=8.5, fontName='Helvetica',
            textColor=TEXTO_ESCURO, alignment=TA_JUSTIFY,
            leading=13, leftIndent=14,
        ),
        'rodape': ParagraphStyle(
            'rodape', parent=base['Normal'],
            fontSize=7, fontName='Helvetica',
            textColor=TEXTO_MUTED, alignment=TA_CENTER,
        ),
        'assinatura_label': ParagraphStyle(
            'assinatura_label', parent=base['Normal'],
            fontSize=7.5, fontName='Helvetica-Bold',
            textColor=TEXTO_MUTED, alignment=TA_CENTER,
        ),
        'assinatura_nome': ParagraphStyle(
            'assinatura_nome', parent=base['Normal'],
            fontSize=9, fontName='Helvetica',
            textColor=TEXTO_ESCURO, alignment=TA_CENTER,
        ),
    }
    return estilos


def _cabecalho_secao(titulo, story, E):
    """Barra azul com título de seção."""
    t = Table([[Paragraph(f'  {titulo}', E['secao'])]], colWidths=[17 * cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), AZUL_MEDIO),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [AZUL_MEDIO]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))


def _linha_campo(label, valor, E):
    """Retorna um par (label, valor) para tabela de campos."""
    return [Paragraph(label, E['campo_label']), Paragraph(str(valor or '—'), E['campo_valor'])]


def _tabela_campos(linhas, colWidths=None):
    """Cria tabela de 2 colunas (label + valor) ou 4 colunas (2 pares)."""
    if colWidths is None:
        colWidths = [4 * cm, 13 * cm]
    t = Table(linhas, colWidths=colWidths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CINZA_CLARO),
        ('BOX', (0, 0), (-1, -1), 0.5, CINZA_BORDA),
        ('INNERGRID', (0, 0), (-1, -1), 0.3, CINZA_BORDA),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def gerar_termo_pdf(alocacao):
    """
    Gera o Termo de Responsabilidade como bytes PDF.
    Recebe uma instância de AlocacaoEquipamento com relacionamentos carregados.
    """
    buffer = io.BytesIO()
    eq  = alocacao.equipamento
    col = alocacao.colaborador
    E   = _estilos()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm,  bottomMargin=2.5 * cm,
        title='Termo de Responsabilidade de Equipamento',
        author='HOC Gestão',
    )

    story = []

    # ── Cabeçalho da empresa ──────────────────────────────────────────────────
    cabecalho = Table([
        [
            Paragraph('⬡  HOC Gestão', E['titulo_empresa']),
        ],
        [Paragraph('Consultoria em Tecnologia da Informação', E['subtitulo_empresa'])],
    ], colWidths=[17 * cm])
    cabecalho.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), AZUL_CLARO),
        ('BOX', (0, 0), (-1, -1), 1, AZUL_MEDIO),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(cabecalho)

    # ── Título do documento ───────────────────────────────────────────────────
    story.append(Paragraph('TERMO DE RESPONSABILIDADE DE USO DE EQUIPAMENTO', E['titulo_doc']))
    story.append(Paragraph(
        f'Nº {alocacao.id:04d}  ·  Gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}',
        E['subtitulo_doc']
    ))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width='100%', thickness=1, color=AZUL_MEDIO))
    story.append(Spacer(1, 12))

    # ── Dados do Colaborador ──────────────────────────────────────────────────
    _cabecalho_secao('1. DADOS DO COLABORADOR', story, E)

    area    = col.area_display    if hasattr(col, 'area_display')    else (col.area or '—')
    regime  = col.regime_display  if hasattr(col, 'regime_display')  else (col.regime or '—')
    senioridade = col.senioridade_display if hasattr(col, 'senioridade_display') else (col.senioridade or '—')

    campos_col = [
        _linha_campo('Nome completo', col.nome, E),
        _linha_campo('E-mail', col.email, E),
        _linha_campo('Cargo', col.cargo, E),
        _linha_campo('Área / Departamento', area, E),
        _linha_campo('Senioridade', senioridade, E),
        _linha_campo('Regime de trabalho', regime, E),
        _linha_campo('CPF', col.cpf or '—', E),
    ]
    story.append(_tabela_campos(campos_col))
    story.append(Spacer(1, 12))

    # ── Dados do Equipamento ──────────────────────────────────────────────────
    _cabecalho_secao('2. DADOS DO EQUIPAMENTO', story, E)

    valor_fmt = f'R$ {eq.valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.') \
        if eq.valor else '—'
    data_aq = eq.data_aquisicao.strftime('%d/%m/%Y') if eq.data_aquisicao else '—'

    campos_eq = [
        _linha_campo('Tipo de equipamento', eq.tipo_display, E),
        _linha_campo('Marca',   eq.marca  or '—', E),
        _linha_campo('Modelo',  eq.modelo or '—', E),
        _linha_campo('Número de série',     eq.numero_serie      or '—', E),
        _linha_campo('Número de patrimônio', eq.numero_patrimonio or '—', E),
        _linha_campo('Valor de aquisição',  valor_fmt, E),
        _linha_campo('Data de aquisição',   data_aq,   E),
        _linha_campo('Estado na entrega',
                     dict([(e[0], e[1]) for e in
                           [('novo','Novo'),('bom','Bom'),('regular','Regular'),('ruim','Ruim')]
                           ]).get(alocacao.estado_entrega, alocacao.estado_entrega), E),
    ]
    if eq.descricao:
        campos_eq.append(_linha_campo('Descrição / Acessórios', eq.descricao, E))

    story.append(_tabela_campos(campos_eq))
    story.append(Spacer(1, 12))

    # ── Dados da Alocação ─────────────────────────────────────────────────────
    _cabecalho_secao('3. DADOS DA ALOCAÇÃO', story, E)

    data_ent = alocacao.data_entrega.strftime('%d/%m/%Y')
    data_prev = alocacao.data_prevista_devolucao.strftime('%d/%m/%Y') \
        if alocacao.data_prevista_devolucao else 'Indeterminado'

    campos_aloc = [
        _linha_campo('Data de entrega',           data_ent,  E),
        _linha_campo('Previsão de devolução',      data_prev, E),
        _linha_campo('Observações da alocação',    alocacao.observacoes or '—', E),
    ]
    story.append(_tabela_campos(campos_aloc))
    story.append(Spacer(1, 14))

    # ── Cláusulas ─────────────────────────────────────────────────────────────
    _cabecalho_secao('4. CLÁUSULAS E CONDIÇÕES DE USO', story, E)
    story.append(Spacer(1, 4))

    clausulas = [
        ('Cláusula 1 — Finalidade',
         'O equipamento descrito neste termo é cedido exclusivamente para uso '
         'profissional em atividades relacionadas às funções exercidas pelo '
         'COLABORADOR na empresa HOC Gestão, sendo vedada sua utilização para '
         'fins pessoais ou por terceiros.'),
        ('Cláusula 2 — Responsabilidade e Conservação',
         'O COLABORADOR declara ter recebido o equipamento em perfeitas condições '
         'de uso (conforme estado registrado na Cláusula 3) e compromete-se a '
         'zelar pela sua guarda, conservação e uso adequado, respondendo por '
         'danos causados por uso indevido, descuido ou negligência.'),
        ('Cláusula 3 — Segurança da Informação',
         'É expressamente proibida a instalação de softwares não homologados, '
         'o acesso a sistemas não autorizados e o compartilhamento de credenciais '
         'de acesso. O COLABORADOR deve adotar as políticas de segurança '
         'da informação vigentes na empresa.'),
        ('Cláusula 4 — Perda, Roubo ou Dano',
         'Em caso de perda, roubo, furto ou dano ao equipamento, o COLABORADOR '
         'deverá comunicar imediatamente ao departamento de RH e/ou TI, '
         'colaborando com as providências necessárias. Em caso de dano por '
         'culpa comprovada, a empresa poderá apurar responsabilidade civil.'),
        ('Cláusula 5 — Devolução',
         'O equipamento deverá ser devolvido ao término do contrato de trabalho, '
         'em caso de mudança de função que não justifique sua utilização, ou '
         'mediante solicitação da empresa, no prazo máximo de 2 (dois) dias úteis '
         'após a notificação, nas mesmas condições em que foi entregue, '
         'salvo desgaste natural decorrente do uso adequado.'),
        ('Cláusula 6 — Aceite',
         'Ao assinar este Termo, o COLABORADOR declara ter lido, entendido e '
         'concordado com todas as condições aqui estabelecidas, estando ciente '
         'de suas responsabilidades quanto ao equipamento cedido.'),
    ]

    for num, (titulo, texto) in enumerate(clausulas, 1):
        story.append(Paragraph(titulo, E['clausula_num']))
        story.append(Paragraph(texto, E['clausula_txt']))

    story.append(Spacer(1, 16))

    # ── Área de assinaturas ───────────────────────────────────────────────────
    _cabecalho_secao('5. ASSINATURAS', story, E)
    story.append(Spacer(1, 20))

    linha_assin = '_' * 45
    _meses = {
        "January": "janeiro", "February": "fevereiro", "March": "março",
        "April": "abril", "May": "maio", "June": "junho",
        "July": "julho", "August": "agosto", "September": "setembro",
        "October": "outubro", "November": "novembro", "December": "dezembro",
    }
    _data_br = datetime.now().strftime("%d de %B de %Y")
    for _en, _pt in _meses.items():
        _data_br = _data_br.replace(_en, _pt)
    cidade_data = f'{col.cidade or "____________"}, {_data_br}'

    # Local e data centralizado
    story.append(Paragraph(cidade_data, ParagraphStyle(
        'local_data', parent=getSampleStyleSheet()['Normal'],
        fontSize=9, alignment=TA_CENTER, textColor=TEXTO_ESCURO, spaceAfter=24,
    )))

    assinaturas = Table([
        [
            Paragraph(linha_assin, E['assinatura_nome']),
            Spacer(1, 1),
            Paragraph(linha_assin, E['assinatura_nome']),
        ],
        [
            Paragraph(col.nome, E['assinatura_nome']),
            Spacer(1, 1),
            Paragraph('Responsável — HOC Gestão / RH', E['assinatura_nome']),
        ],
        [
            Paragraph('COLABORADOR', E['assinatura_label']),
            Spacer(1, 1),
            Paragraph('EMPRESA', E['assinatura_label']),
        ],
    ], colWidths=[7.5 * cm, 2 * cm, 7.5 * cm])

    assinaturas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(assinaturas)
    story.append(Spacer(1, 24))

    # ── Rodapé ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width='100%', thickness=0.5, color=CINZA_BORDA))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f'HOC Gestão — Consultoria em TI  ·  Termo nº {alocacao.id:04d}  ·  '
        f'Gerado automaticamente pelo sistema HOC Gestão em '
        f'{datetime.now().strftime("%d/%m/%Y às %H:%M")}',
        E['rodape']
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer
