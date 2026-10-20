"""Documentos para o SEI: o SGPP monta o texto com os dados do projeto e entrega em texto, HTML e PDF.

O texto-base de cada modelo vem dos documentos que a DPLAN e as unidades executoras já emitem no SEI. Quem
emite cada um depende do lado: a Planejamento (Escritório de Projetos) ou a unidade que elabora e executa o projeto.

Número, bloco de assinatura e rodapé do processo são do SEI e nunca entram no texto copiável. O PDF existe como
minuta de conferência e, se o SEI aceitar, como documento externo (modo "externo", com linha de assinatura).

Só texto e regras, sem Streamlit, para poder ser testado sozinho. As telas ficam em app.py.
"""
import html
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

import guia
import projetos

CIDADE_PADRAO = "Manaus"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro",
         "dezembro"]

ATO_POLITICA = "Ato nº 021/2025/PGJ"
ATO_REGIMENTO_CGP = "Ato nº 269/2026/PGJ"
POLITICA = f"Política Institucional de Projetos ({ATO_POLITICA})"
FECHO_ESTILO = "Atenciosamente,"
CIENCIA = "colocamo-nos à disposição para eventuais esclarecimentos adicionais que se façam necessários."


@dataclass
class Documento:
    """Um documento já montado. As telas editam os blocos antes de gerar a saída."""
    tipo: str
    tipo_sei: str
    titulo: str
    destinatario: list = field(default_factory=list)
    assunto: str = ""
    vocativo: str = ""
    # ("paragrafo", texto) | ("titulo", texto) | ("lista", [textos]) | ("campo", rótulo, valor). Campos seguidos saem juntos.
    blocos: list = field(default_factory=list)
    fecho: str = ""
    assinante: list = field(default_factory=list)
    assinatura_no_corpo: bool = False
    data: date = None


# ------------------------------------------------------------------ campos de cada modelo

def _campo(chave, rotulo, ajuda="", tipo="texto", opcoes=None):
    return {"chave": chave, "rotulo": rotulo, "ajuda": ajuda, "tipo": tipo, "opcoes": opcoes or []}


_DESTINATARIO = [
    _campo("tratamento", "Tratamento", "Ex.: Ilustríssimo(a) Senhor(a)"),
    _campo("destinatario_nome", "Nome do destinatário", "Pode ficar em branco."),
    _campo("destinatario_cargo", "Cargo do destinatário"),
    _campo("vocativo", "Vocativo", "Ex.: Senhor(a) Coordenador(a),"),
]
_ASSINANTE = [
    _campo("assinante_nome", "Quem assina (nome)", "Sai no corpo do Memorando; nas Certidões só entra no PDF para documento externo."),
    _campo("assinante_cargo", "Cargo e unidade de quem assina"),
]

def _lista_em_portugues(itens):
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + " e " + itens[-1]


_PARTES_COM_CAMPO = _lista_em_portugues([p["numero"] for p in guia.ESCOPO_ATO_PGJ if p["no_sgpp"]])

AVISO_DADOS_PESSOAIS = ("Esta Certidão trata de ações institucionais do projeto (reunião, oficina, visita, divulgação, capacitação). "
                        "Não digite nome, iniciais, CPF, número de processo ou outros dados pessoais de participantes: o SGPP "
                        "acompanha projetos, não atendimentos individuais.")

# Ordem: primeiro os documentos da Planejamento (na ordem do ciclo), depois os do lado do projeto.
TIPOS_DOCUMENTO = {
    "memorando_devolucao": {
        "titulo": "Memorando de devolução para ajustes", "tipo_sei": "Memorando", "lado": "dplan", "arquivo": "Memorando_devolucao",
        "momento": "Ao devolver o projeto para ajustes, na Revisão.",
        "campos": _DESTINATARIO + [_campo("referencia", "Em atenção ao (opcional)", "Ex.: Despacho Nº 10.2026.CGP-MPAM.2208269")] + _ASSINANTE,
    },
    "parecer_tecnico": {
        "titulo": "Parecer Técnico", "tipo_sei": "Parecer", "lado": "dplan", "arquivo": "Parecer_tecnico",
        "momento": "Ao concluir a revisão, antes de encaminhar ao Comitê.",
        "aviso": "Os trechos marcados com (a preencher: ...) pedem a análise de quem assina o Parecer. Substitua cada um antes de usar o documento.",
        "campos": [_campo("interessado", "Interessado", "Por padrão, a unidade do projeto."),
                   _campo("conclusao", "Conclusão", tipo="escolha", opcoes=projetos.CONCLUSOES_PARECER)] + _ASSINANTE,
    },
    "memorando_comite": {
        "titulo": "Memorando de encaminhamento do Parecer ao Comitê", "tipo_sei": "Memorando", "lado": "dplan", "arquivo": "Memorando_comite",
        "momento": "Depois de emitir o Parecer Técnico, ao concluir a revisão.",
        "campos": _DESTINATARIO + [
            _campo("referencia_despacho", "Despacho do Comitê (opcional)", "Ex.: Despacho Nº 10.2026.CGP-MPAM.2208269"),
            _campo("referencia_parecer", "Parecer Técnico (opcional)", "Ex.: Parecer Nº 5.2026.ESCRITÓRIO DE PROJETOS.2241387")] + _ASSINANTE,
    },
    "certidao_inclusao_portfolio": {
        "titulo": "Certidão de inclusão no Portfólio", "tipo_sei": "Certidão", "lado": "dplan", "arquivo": "Certidao_inclusao",
        "momento": "Com a revisão concluída e o projeto na base da Planejamento, ou depois do Ato PGJ.",
        "campos": [_campo("ato_pgj", "Ato PGJ (opcional)", "Com o Ato, a Certidão fala da atualização após a publicação.")] + _ASSINANTE,
    },
    "memorando_reenvio": {
        "titulo": "Memorando de resposta e reenvio", "tipo_sei": "Memorando", "lado": "projeto", "arquivo": "Memorando_reenvio",
        "momento": "Depois de ajustar o projeto devolvido e reenviá-lo.",
        "campos": [_campo("destino", "Para quem", tipo="escolha", opcoes=["DPLAN", "PGJ"])] + _DESTINATARIO + [
            _campo("referencia", "Em atenção ao (opcional)", "Ex.: Memorando Nº 11.2026.ESCRITÓRIO DE PROJETOS.2213965")] + _ASSINANTE,
    },
    "certidao_atividade": {
        "titulo": "Certidão de atividade", "tipo_sei": "Certidão", "lado": "projeto", "arquivo": "Certidao_atividade",
        "momento": "A cada atividade registrada como atualização no Acompanhamento.",
        "aviso": AVISO_DADOS_PESSOAIS,
        "campos": [_campo("atualizacao_id", "Atividade (atualização registrada)", tipo="atualizacao"),
                   _campo("horario", "Horário (opcional)", "Ex.: 9h às 10h"),
                   _campo("local", "Local (opcional)")] + _ASSINANTE,
    },
    "escopo_projeto": {
        "titulo": "Escopo do projeto", "tipo_sei": "Projeto", "lado": "projeto", "arquivo": "Projeto_escopo",
        "momento": "Durante a Elaboração, antes de enviar, e a cada nova versão do projeto.",
        "aviso": f"O Escopo segue as 17 partes do Modelo de Escopo de Projeto (Ato nº 269/2026/PGJ). O formulário de Elaboração ainda "
                 f"cobre só as partes {_PARTES_COM_CAMPO}; as demais saem marcadas com (a preencher: ...). A orientação de cada parte está "
                 "no Guia, em Escopo do projeto (Ato PGJ).",
        "campos": list(_ASSINANTE),
    },
    "relatorio_atuacao": {
        "titulo": "Relatório de atuação", "tipo_sei": "Relatório", "lado": "projeto", "arquivo": "Relatorio_atuacao",
        "momento": "No fim de um período ou do ano, com as atualizações registradas no Acompanhamento.",
        "aviso": "A seção 5 vem das atualizações do período. As demais, marcadas com (a preencher: ...), pedem o seu texto. "
                 "Não cite nome nem dado pessoal de participantes.",
        "campos": [_campo("inicio", "Início do período", tipo="data"), _campo("termino", "Fim do período", tipo="data")] + _ASSINANTE,
    },
}


# ------------------------------------------------------------------ quem vê o quê

def tipos_para(nivel):
    dplan = projetos.pode("documentos_dplan", nivel)
    do_projeto = projetos.pode("documentos_projeto", nivel)
    return [t for t, m in TIPOS_DOCUMENTO.items() if (m["lado"] == "dplan" and dplan) or (m["lado"] == "projeto" and do_projeto)]


def sugerido(projeto, nivel):
    """O documento que mais provavelmente se quer agora, pelo estado da revisão do projeto e pelo perfil."""
    disponiveis = tipos_para(nivel)
    if not disponiveis:
        return None
    revisao = projetos.texto(projeto.get("REVISAO"))
    if projetos.pode("documentos_dplan", nivel):
        if revisao == projetos.REVISAO_DEVOLVIDO:
            return "memorando_devolucao"
        if revisao == projetos.REVISAO_CONCLUIDA:
            return "parecer_tecnico"
        return disponiveis[0]
    if revisao in (projetos.REVISAO_DEVOLVIDO, projetos.REVISAO_REENVIADO):
        return "memorando_reenvio"
    return "certidao_atividade"


# ------------------------------------------------------------------ apoio aos modelos

def _t(valor):
    return projetos.texto(valor)


_PADRAO_A_PREENCHER = re.compile(r"\(a preencher:[^)]*\)")


def _a_preencher(orientacao):
    """Trecho que só a pessoa pode escrever. A tela conta quantos ainda restam antes de liberar o documento."""
    return f"(a preencher: {orientacao})"


def trechos_a_preencher(doc):
    """Quantos trechos marcados com '(a preencher: ...)' ainda restam no documento."""
    textos = [doc.assunto, doc.vocativo, doc.fecho] + [bloco_para_texto(b) for b in doc.blocos]
    return sum(len(_PADRAO_A_PREENCHER.findall(t)) for t in textos)


def _nome(projeto):
    return _t(projeto.get("Nome da Iniciativa")) or "(projeto sem nome)"


def _unidade_entre_parenteses(projeto):
    unidade = _t(projeto.get("Unidade"))
    return f" ({unidade})" if unidade else ""


def _ultimo_comentario(abas, n, tipo):
    achados = [c["texto"] for c in projetos.comentarios_do_projeto(abas, n) if c["tipo"] == tipo]
    return achados[-1] if achados else ""


def _campos_alterados_desde_a_devolucao(abas, n):
    """Campos que o gestor mudou depois da devolução mais recente (ou desde sempre, se nunca foi devolvido), sem repetir."""
    eventos = projetos.linha_do_tempo(abas, n)
    ultimo = max((i for i, e in enumerate(eventos) if e["evento"] == "devolvido"), default=-1)
    campos = []
    for e in eventos[ultimo + 1:]:
        if e["evento"] != "editado":
            continue
        detalhe = _t(e["detalhe"])
        itens = detalhe[len("Campos: "):].split(", ") if detalhe.startswith("Campos: ") else [detalhe]
        for item in (i.strip() for i in itens):
            if item and item not in campos:
                campos.append(item)
    return campos


def _atualizacoes_recentes_primeiro(abas, n):
    """Atualizações do projeto, da data de referência mais recente para a mais antiga (empate: a registrada por último)."""
    linhas = list(projetos.do_projeto(abas, "Atualizacoes", n).itertuples())  # já vem da última registrada para a primeira
    return sorted(linhas, key=lambda r: projetos.parse_data(r.data_referencia) or date.min, reverse=True)


def opcoes_atualizacoes(abas, n):
    """Atualizações do projeto para escolher: {id: 'dd/mm/aaaa: começo do texto'}, a mais recente primeiro."""
    opcoes = {}
    for r in _atualizacoes_recentes_primeiro(abas, n):
        quando = projetos.parse_data(r.data_referencia)
        texto = _t(r.texto)
        opcoes[r.id] = f"{quando.strftime('%d/%m/%Y') if quando else r.data_referencia}: {texto[:70]}{'...' if len(texto) > 70 else ''}"
    return opcoes


def _rotulo_do_ato(valor):
    valor = _t(valor)
    return valor if re.match(r"(?i)^\s*ato\b", valor) else f"Ato PGJ nº {valor}"


def _data_extenso(d):
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def _linhas(*itens):
    return [i for i in itens if i]


def _destinatario(c):
    tratamento = _t(c.get("tratamento"))
    return _linhas(f"Ao(À) {tratamento}" if tratamento else "", _t(c.get("destinatario_nome")), _t(c.get("destinatario_cargo")))


def _assinante(c):
    return _linhas(_t(c.get("assinante_nome")), _t(c.get("assinante_cargo")))


def _em_atencao(referencia, complemento=""):
    return f", em atenção ao {referencia}{complemento}" if referencia else ""


# ------------------------------------------------------------------ padrões dos campos

def _cargo_do_projeto(projeto):
    unidade = _t(projeto.get("Unidade"))
    return f"Coordenação do projeto, {unidade}" if unidade else "Coordenação do projeto"


_CARGO_ESCRITORIO = "Escritório de Projetos, Diretoria de Planejamento (DPLAN)"


def _padroes_memorando_devolucao(p, abas, autor, hoje, escolhidos):
    return {"tratamento": "Ilustríssimo(a) Senhor(a)", "destinatario_nome": _t(p.get("Gestor")),
            "destinatario_cargo": "Coordenação do projeto", "vocativo": "Senhor(a) Coordenador(a),", "referencia": "",
            "assinante_nome": autor, "assinante_cargo": _CARGO_ESCRITORIO}


def _padroes_memorando_comite(p, abas, autor, hoje, escolhidos):
    return {"tratamento": "Ilustríssimo(a) Senhor(a)", "destinatario_nome": "",
            "destinatario_cargo": "Presidente do Comitê de Governança de Projetos", "vocativo": "Senhor(a) Presidente,",
            "referencia_despacho": "", "referencia_parecer": "", "assinante_nome": autor, "assinante_cargo": _CARGO_ESCRITORIO}


def _padroes_certidao_inclusao(p, abas, autor, hoje, escolhidos):
    return {"ato_pgj": _t(p.get("Ato PGJ")), "assinante_nome": autor, "assinante_cargo": "Diretoria de Planejamento (DPLAN)"}


def _padroes_memorando_reenvio(p, abas, autor, hoje, escolhidos):
    pgj = _t(escolhidos.get("destino")).upper() == "PGJ"
    return {"destino": "PGJ" if pgj else "DPLAN",
            "tratamento": "Excelentíssimo(a) Senhor(a)" if pgj else "Ilustríssimo(a) Senhor(a)",
            "destinatario_nome": "",
            "destinatario_cargo": "Procurador(a)-Geral de Justiça" if pgj else "Diretor(a) de Planejamento, DPLAN/MPAM",
            "vocativo": "Excelentíssimo(a) Senhor(a) Procurador(a)-Geral de Justiça," if pgj else "Senhor(a) Diretor(a),",
            "referencia": "", "assinante_nome": autor, "assinante_cargo": _cargo_do_projeto(p)}


def _padroes_certidao_atividade(p, abas, autor, hoje, escolhidos):
    recentes = _atualizacoes_recentes_primeiro(abas, projetos.chave(p))
    return {"atualizacao_id": recentes[0].id if recentes else "", "horario": "", "local": "",
            "assinante_nome": autor, "assinante_cargo": _cargo_do_projeto(p)}


def _parecer_registrado(abas, n):
    """O parecer mais recente já registrado no Acompanhamento: (conclusão, texto), ou ('', '')."""
    registrados = projetos.do_projeto(abas, "Pareceres", n)
    if registrados.empty:
        return "", ""
    ultimo = registrados.iloc[0]
    return _t(ultimo["conclusao"]), _t(ultimo["texto"])


def _padroes_parecer_tecnico(p, abas, autor, hoje, escolhidos):
    conclusao, _ = _parecer_registrado(abas, projetos.chave(p))
    return {"interessado": _t(p.get("Unidade")), "conclusao": conclusao if conclusao in projetos.CONCLUSOES_PARECER else "Favorável",
            "assinante_nome": autor, "assinante_cargo": _CARGO_ESCRITORIO}


def _primeiro_dia_do_ano(hoje):
    return date(hoje.year, 1, 1)


def _padroes_relatorio_atuacao(p, abas, autor, hoje, escolhidos):
    return {"inicio": _primeiro_dia_do_ano(hoje).isoformat(), "termino": hoje.isoformat(),
            "assinante_nome": autor, "assinante_cargo": _cargo_do_projeto(p)}


def _padroes_escopo_projeto(p, abas, autor, hoje, escolhidos):
    return {"assinante_nome": autor, "assinante_cargo": _cargo_do_projeto(p)}


_PADROES = {
    "memorando_devolucao": _padroes_memorando_devolucao,
    "parecer_tecnico": _padroes_parecer_tecnico,
    "memorando_comite": _padroes_memorando_comite,
    "certidao_inclusao_portfolio": _padroes_certidao_inclusao,
    "memorando_reenvio": _padroes_memorando_reenvio,
    "certidao_atividade": _padroes_certidao_atividade,
    "escopo_projeto": _padroes_escopo_projeto,
    "relatorio_atuacao": _padroes_relatorio_atuacao,
}


def campos_padrao(tipo, projeto, abas, autor_nome="", hoje=None, escolhidos=None):
    """Valor inicial de cada campo do modelo. `escolhidos` traz o que a pessoa já escolheu e muda os outros padrões
    (o destino do Memorando de reenvio, por exemplo, troca o destinatário)."""
    padroes = _PADROES[tipo](projeto, abas, _t(autor_nome), hoje or date.today(), escolhidos or {})
    return {c["chave"]: padroes.get(c["chave"], "") for c in TIPOS_DOCUMENTO[tipo]["campos"]}


# ------------------------------------------------------------------ os modelos

def _montar_memorando_devolucao(p, abas, c, hoje):
    nome = _nome(p)
    ajustes = [linha.strip() for linha in _ultimo_comentario(abas, projetos.chave(p), "devolucao").splitlines() if linha.strip()]
    return Documento(
        tipo="memorando_devolucao", tipo_sei="Memorando", titulo=TIPOS_DOCUMENTO["memorando_devolucao"]["titulo"],
        destinatario=_destinatario(c), vocativo=_t(c.get("vocativo")),
        assunto=f'Encaminha autos para fins de diligência e eventuais ajustes no Projeto "{nome}" quanto à sua '
                f"conformidade com os requisitos previstos na Política Institucional de Projetos.",
        blocos=[
            ("paragrafo", f"Com os cumprimentos de estilo{_em_atencao(_t(c.get('referencia')))}, vimos, por meio do presente, "
                          f'encaminhar os autos do Projeto "{nome}"{_unidade_entre_parenteses(p)} para fins de diligência e eventuais ajustes.'),
            ("paragrafo", "No exercício das competências desta Diretoria, na qualidade de Escritório de Projetos, procedeu-se à análise "
                          "da documentação constante dos autos, ocasião em que se verificou a necessidade de complementação e "
                          "aprimoramento de informações, a fim de assegurar o pleno atendimento às diretrizes estabelecidas na "
                          f"{POLITICA}."),
            ("paragrafo", "Os ajustes necessários são os seguintes:"),
            ("lista", ajustes or [_a_preencher("descreva os ajustes necessários")]),
            ("paragrafo", CIENCIA[0].upper() + CIENCIA[1:]),
        ],
        fecho=FECHO_ESTILO, assinante=_assinante(c), assinatura_no_corpo=True, data=hoje)


def _montar_memorando_comite(p, abas, c, hoje):
    nome = _nome(p)
    despacho, parecer = _t(c.get("referencia_despacho")), _t(c.get("referencia_parecer")) or "Parecer Técnico anexo aos autos"
    requisitos = (f"requisitos previstos na {POLITICA} e no Regimento Interno do Comitê de Governança de Projetos ({ATO_REGIMENTO_CGP})")
    if despacho:
        abertura = (f"Com os cumprimentos de estilo, em atenção ao {despacho}, por meio do qual se solicita a emissão de Parecer Técnico "
                    f'por este Escritório de Projetos acerca do Projeto "{nome}", especialmente quanto à sua conformidade com os '
                    f"{requisitos}, vimos, por meio do presente, encaminhar à apreciação desse Comitê o {parecer}.")
    else:
        abertura = (f"Com os cumprimentos de estilo, vimos, por meio do presente, encaminhar à apreciação desse Comitê o {parecer} "
                    f'acerca do Projeto "{nome}", elaborado quanto à sua conformidade com os {requisitos}.')
    blocos = [("paragrafo", abertura),
              ("paragrafo", "Informamos que o documento foi elaborado após análise da documentação encaminhada e de diligências "
                            "realizadas junto à equipe de gestão do projeto supracitado.")]
    if _t(p.get("Status")) == "Em execução":
        blocos.append(("paragrafo", "Ressaltamos que, embora o projeto já se encontre em execução, tal circunstância não afasta a "
                                    "necessidade de sua submissão à apreciação deste Comitê, para fins de verificação de conformidade "
                                    "com a Política Institucional de Projetos e de sua eventual institucionalização e inclusão no "
                                    "Portfólio Institucional de Projetos do MPAM."))
    blocos.append(("paragrafo", "Por fim, " + CIENCIA))
    return Documento(
        tipo="memorando_comite", tipo_sei="Memorando", titulo=TIPOS_DOCUMENTO["memorando_comite"]["titulo"],
        destinatario=_destinatario(c), vocativo=_t(c.get("vocativo")), assunto=f'Encaminha parecer técnico acerca do Projeto "{nome}".',
        blocos=blocos, fecho=FECHO_ESTILO, assinante=_assinante(c), assinatura_no_corpo=True, data=hoje)


def _montar_certidao_inclusao(p, abas, c, hoje):
    nome, ato = _nome(p), _t(c.get("ato_pgj"))
    if ato:
        certifico = (f"Certifico, para todos os fins, que as informações referentes ao {_rotulo_do_ato(ato)} foram inseridas na planilha "
                     f'de acompanhamento de projetos desta Diretoria de Planejamento, relativas ao Projeto "{nome}".')
    else:
        certifico = (f'Certifico, para fins de conclusão do processo na unidade, que o Projeto "{nome}" foi incluído na Planilha de '
                     "Controle de Projetos desta Diretoria de Planejamento/Escritório de Projetos, que servirá de base para a "
                     "construção do Portfólio de Projetos desta instituição.")
    return Documento(
        tipo="certidao_inclusao_portfolio", tipo_sei="Certidão", titulo=TIPOS_DOCUMENTO["certidao_inclusao_portfolio"]["titulo"],
        blocos=[("paragrafo", certifico), ("paragrafo", "É o que me cumpre certificar.")],
        assinante=_assinante(c), assinatura_no_corpo=False, data=hoje)


def _montar_memorando_reenvio(p, abas, c, hoje):
    nome, n = _nome(p), projetos.chave(p)
    alterados = _campos_alterados_desde_a_devolucao(abas, n)
    referencia, sei, unidade = _t(c.get("referencia")), _t(p.get("SEI")), _t(p.get("Unidade"))
    if _t(c.get("destino")).upper() == "PGJ":
        if referencia:
            processo = f", proferido nos autos do Processo SEI nº {sei}" if sei else ""
            abertura = (f"Cumprimentando cordialmente, em atenção ao {referencia}{processo}, que trata da institucionalização do "
                        f'Projeto "{nome}", encaminha-se a versão atualizada do referido Projeto, com as adequações pertinentes.')
        else:
            abertura = f'Cumprimentando cordialmente, encaminha-se a versão atualizada do Projeto "{nome}", com as adequações pertinentes.'
        blocos = [("paragrafo", abertura)]
        if alterados:
            blocos += [("paragrafo", "As alterações realizadas contemplam, especialmente, a atualização dos seguintes campos do projeto:"),
                       ("lista", alterados)]
        else:
            blocos.append(("paragrafo", "As alterações realizadas contemplam a atualização do documento do projeto."))
        quem = f"a unidade {unidade} encaminha" if unidade else "encaminha-se"
        blocos += [("paragrafo", f"Dessa forma, {quem} o Projeto atualizado, para fins de continuidade do trâmite de institucionalização, "
                                 "por meio da publicação de Ato e demais providências que se entenderem cabíveis."),
                   ("paragrafo", "Sem mais para o momento, renovo protestos de elevada estima e distinta consideração.")]
        assunto = f'Encaminha Projeto "{nome}" atualizado para continuidade do trâmite de institucionalização.'
    else:
        complemento = ", bem como às orientações técnicas expedidas por esse Escritório de Projetos"
        blocos = [("paragrafo", f"Cumprimentando cordialmente{_em_atencao(referencia, complemento)}, informo que foram realizadas as "
                                f'correções, adequações e atualizações no Projeto "{nome}", em conformidade com os parâmetros da '
                                "Política Institucional de Projetos.")]
        if alterados:
            blocos += [("paragrafo", "As providências adotadas contemplaram a revisão dos seguintes campos do projeto:"), ("lista", alterados)]
        else:
            blocos.append(("paragrafo", "As providências adotadas contemplaram a revisão do documento do projeto, com os devidos "
                                        "ajustes de conteúdo, organização e detalhamento técnico."))
        blocos.append(("paragrafo", "Dessa forma, encaminha-se a versão atualizada do projeto, para conhecimento e prosseguimento da "
                                    "tramitação, colocando esta Coordenação à disposição para quaisquer esclarecimentos adicionais "
                                    "que se façam necessários."))
        assunto = f'Projeto "{nome}": ajustes realizados.'
    return Documento(
        tipo="memorando_reenvio", tipo_sei="Memorando", titulo=TIPOS_DOCUMENTO["memorando_reenvio"]["titulo"],
        destinatario=_destinatario(c), vocativo=_t(c.get("vocativo")), assunto=assunto, blocos=blocos, fecho=FECHO_ESTILO,
        assinante=_assinante(c), assinatura_no_corpo=True, data=hoje)


def _montar_certidao_atividade(p, abas, c, hoje):
    nome, n = _nome(p), projetos.chave(p)
    recentes = _atualizacoes_recentes_primeiro(abas, n)
    escolhida = next((r for r in recentes if r.id == _t(c.get("atualizacao_id"))), recentes[0] if recentes else None)
    dia = (projetos.parse_data(escolhida.data_referencia) if escolhida else None) or hoje
    horario, local = _t(c.get("horario")), _t(c.get("local"))
    abertura = (f"Certifico, para os devidos fins, que no dia {dia.strftime('%d/%m/%Y')}"
                f"{f', no horário de {horario}' if horario else ''}, no âmbito do Projeto \"{nome}\"{_unidade_entre_parenteses(p)}, "
                "foi registrada a seguinte atividade:")
    blocos = [("paragrafo", abertura),
              ("paragrafo", _t(escolhida.texto) if escolhida else _a_preencher("descreva a atividade realizada"))]
    if local:
        blocos.append(("paragrafo", f"Local: {local}."))
    blocos.append(("paragrafo", "É o que me cumpre certificar."))
    return Documento(
        tipo="certidao_atividade", tipo_sei="Certidão", titulo=TIPOS_DOCUMENTO["certidao_atividade"]["titulo"],
        blocos=blocos, assinante=_assinante(c), assinatura_no_corpo=False, data=hoje)


def _data_br(valor):
    d = projetos.parse_data(valor)
    return d.strftime("%d/%m/%Y") if d else ""


def _montar_parecer_tecnico(p, abas, c, hoje):
    nome, n = _nome(p), projetos.chave(p)
    unidade = _t(c.get("interessado")) or _t(p.get("Unidade"))
    ementa, gestor = _t(p.get("Ementa (Objetivo)")), _t(p.get("Gestor"))
    alinhamento, pen = _t(p.get("Alinhamento Estratégico")), _t(p.get("Alinhamento ao PEN"))
    inicio, termino = _data_br(p.get("INICIO_PREVISTO")), _data_br(p.get("TERMINO_PREVISTO"))
    conclusao = _t(c.get("conclusao")) or "Favorável"
    _, texto_registrado = _parecer_registrado(abas, n)

    def analise(dados, orientacao):
        return f"{dados} {_a_preencher(orientacao)}" if dados else _a_preencher(orientacao)

    declarado = " ".join(_linhas(f"Alinhamento estratégico declarado: {alinhamento}." if alinhamento else "",
                                 f"Alinhamento ao PEN: {pen}." if pen else ""))
    prazo = " ".join(_linhas(f"Início previsto: {inicio}." if inicio else "", f"Término previsto: {termino}." if termino else ""))
    governanca = " ".join(_linhas(f"Unidade responsável: {unidade}." if unidade else "", f"Gestor responsável: {gestor}." if gestor else ""))
    blocos = [
        ("campo", "Processo SEI nº", _t(p.get("SEI")) or _a_preencher("informe o nº do processo")),
        ("campo", "Interessado", unidade or _a_preencher("informe a unidade")),
        ("campo", "Iniciativa", nome),
        ("titulo", "EMENTA"),
        ("paragrafo", f'Análise técnica do Projeto "{nome}", quanto à sua conformidade com os requisitos previstos na {POLITICA} '
                      f"e no Regimento Interno do Comitê de Governança de Projetos ({ATO_REGIMENTO_CGP})."),
        ("titulo", "RELATÓRIO"),
        ("paragrafo", f'Trata-se do Projeto "{nome}"{f", submetido pela unidade {unidade}" if unidade else ""}.'),
    ]
    if ementa:
        blocos.append(("paragrafo", f"Ementa (objetivo): {ementa}"))
    blocos += [
        ("paragrafo", "É o relatório."),
        ("titulo", "ANÁLISE TÉCNICA"),
        ("titulo", "1. Alinhamento Estratégico"),
        ("paragrafo", analise(declarado, "analise a aderência ao PEI-MPAM, ao PEN-CNMP e aos ODS")),
        ("titulo", "2. Relevância Institucional"),
        ("paragrafo", _a_preencher("analise a relevância do projeto para a instituição e para o público atendido")),
        ("titulo", "3. Viabilidade Técnica"),
        ("paragrafo", _a_preencher("analise a coerência da metodologia, da equipe e dos recursos tecnológicos com os objetivos")),
        ("titulo", "4. Viabilidade Econômica"),
        ("paragrafo", _a_preencher("analise os recursos necessários, a origem deles e a compatibilidade com a realidade orçamentária")),
        ("titulo", "5. Impacto e Benefícios"),
        ("paragrafo", _a_preencher("descreva os benefícios esperados e o impacto para o público atendido e para a instituição")),
        ("titulo", "6. Riscos"),
        ("paragrafo", _a_preencher("analise a identificação dos riscos, sua probabilidade e impacto, e as respostas previstas")),
        ("titulo", "7. Capacidade de Execução"),
        ("paragrafo", _a_preencher("analise a capacidade da equipe e da unidade de executar o projeto")),
        ("titulo", "8. Indicadores"),
        ("paragrafo", _a_preencher("analise se os indicadores contemplam métricas de esforço, resultado e resolutividade")),
        ("titulo", "9. Cronograma"),
        ("paragrafo", analise(prazo, "analise a compatibilidade das atividades previstas com os prazos")),
        ("titulo", "10. Demais Requisitos da Política Institucional"),
        ("titulo", "10.1 Governança"),
        ("paragrafo", analise(governanca, "analise a estrutura de governança: coordenação, equipe e parceiros")),
        ("titulo", "10.2 Requisitos Tecnológicos"),
        ("paragrafo", _a_preencher("informe se há demandas tecnológicas relevantes para a execução")),
        ("titulo", "10.3 Proteção de Dados e Segurança da Informação"),
        ("paragrafo", _a_preencher("analise o tratamento de dados pessoais conforme a Lei nº 13.709/2018 (LGPD) e as diretrizes de segurança da informação")),
        ("titulo", "CONCLUSÃO"),
    ]
    if conclusao == "Favorável":
        conclusao_texto = (f'À luz da análise realizada, conclui-se pela recomendação favorável ao Projeto "{nome}", considerando o alinhamento '
                           "estratégico, a relevância institucional e a adequação dos aspectos técnicos, econômicos e de governança, com a "
                           "consequente inclusão no Portfólio Institucional de Projetos.")
    elif conclusao == "Favorável com ressalvas":
        conclusao_texto = (f'À luz da análise realizada, conclui-se pela recomendação favorável com ressalvas ao Projeto "{nome}", '
                           f"condicionada aos seguintes ajustes: {_a_preencher('liste as ressalvas')}")
    else:
        conclusao_texto = (f'À luz da análise realizada, conclui-se pela recomendação desfavorável ao Projeto "{nome}", pelos seguintes '
                           f"fundamentos: {_a_preencher('indique os fundamentos')}")
    blocos.append(("paragrafo", conclusao_texto))
    if texto_registrado:
        blocos.append(("paragrafo", texto_registrado))
    return Documento(
        tipo="parecer_tecnico", tipo_sei="Parecer", titulo=TIPOS_DOCUMENTO["parecer_tecnico"]["titulo"],
        blocos=blocos, assinante=_assinante(c), assinatura_no_corpo=False, data=hoje)


def _montar_relatorio_atuacao(p, abas, c, hoje):
    nome, n = _nome(p), projetos.chave(p)
    inicio = projetos.parse_data(c.get("inicio")) or _primeiro_dia_do_ano(hoje)
    fim = projetos.parse_data(c.get("termino")) or hoje
    if inicio > fim:
        inicio, fim = fim, inicio
    atuacoes = [r for r in reversed(_atualizacoes_recentes_primeiro(abas, n))
                if inicio <= (projetos.parse_data(r.data_referencia) or date.min) <= fim]
    itens = [f"{projetos.parse_data(r.data_referencia).strftime('%d/%m/%Y')} ({_t(r.situacao)}): {_t(r.texto)}" for r in atuacoes]
    ementa = _t(p.get("Ementa (Objetivo)"))
    alinhamento = " ".join(_linhas(_t(p.get("Alinhamento Estratégico")), _t(p.get("Alinhamento ao PEN"))))
    blocos = [
        ("titulo", "RELATÓRIO DE ATUAÇÃO"),
        ("titulo", f"PROJETO {nome.upper()}"),
        ("titulo", "1. INTRODUÇÃO"),
        ("paragrafo", f'O presente Relatório objetiva apresentar a atuação do Projeto "{nome}" durante o período de '
                      f"{inicio.strftime('%d/%m/%Y')} a {fim.strftime('%d/%m/%Y')}."),
        ("titulo", "2. DADOS DO PROJETO"),
        ("titulo", "2.1 Objetivo Geral"),
        ("paragrafo", ementa or _a_preencher("descreva o objetivo geral do projeto")),
        ("titulo", "2.2 Objetivos Específicos"),
        ("paragrafo", _a_preencher("liste os objetivos específicos")),
        ("titulo", "2.3 Alinhamento Estratégico"),
        ("paragrafo", alinhamento or _a_preencher("informe o alinhamento estratégico")),
        ("titulo", "3. IMPACTOS"),
        ("paragrafo", _a_preencher("descreva os impactos observados no período")),
        ("titulo", "4. DESAFIOS"),
        ("paragrafo", _a_preencher("descreva os desafios enfrentados no período")),
        ("titulo", "5. ATUAÇÃO"),
        ("lista", itens) if itens else ("paragrafo", _a_preencher("nenhuma atualização registrada no período; descreva a atuação")),
        ("titulo", "6. RESULTADOS OBTIDOS"),
        ("paragrafo", _a_preencher("descreva os resultados obtidos no período")),
    ]
    return Documento(
        tipo="relatorio_atuacao", tipo_sei="Relatório", titulo=TIPOS_DOCUMENTO["relatorio_atuacao"]["titulo"],
        blocos=blocos, assinante=_assinante(c), assinatura_no_corpo=False, data=hoje)


def _campo_ou_pendente(rotulo, valor, orientacao):
    return ("campo", rotulo, valor or _a_preencher(orientacao))


def _escopo_i(p):
    return [_campo_ou_pendente("Título do projeto", _t(p.get("Nome da Iniciativa")), "informe o nome do projeto"),
            _campo_ou_pendente("Unidade demandante", _t(p.get("Unidade")), "informe a unidade"),
            _campo_ou_pendente("Gerente ou coordenador", _t(p.get("Gestor")), "informe nome e cargo"),
            ("paragrafo", _a_preencher("sigla do projeto, e-mail e telefone do gerente, equipe do projeto e patrocinador"))]


def _escopo_ii(p):
    return [("paragrafo", _t(p.get("Ementa (Objetivo)")) or _a_preencher("descreva a iniciativa de forma sucinta"))]


def _escopo_viii(p):
    dados = [("campo", rotulo, valor) for rotulo, valor in (("Alinhamento estratégico", _t(p.get("Alinhamento Estratégico"))),
                                                           ("Alinhamento ao PEN", _t(p.get("Alinhamento ao PEN")))) if valor]
    return dados + [("paragrafo", _a_preencher("indique o objetivo, o programa e a ação estratégicos e os ODS"))]


def _escopo_xii(p):
    return [_campo_ou_pendente("Início previsto", _data_br(p.get("INICIO_PREVISTO")), "informe o mês e o ano de início"),
            _campo_ou_pendente("Término previsto", _data_br(p.get("TERMINO_PREVISTO")), "informe o mês e o ano de término"),
            _campo_ou_pendente("Fase atual do projeto", _t(p.get("Status")), "informe a fase atual"),
            ("paragrafo", _a_preencher("informe a duração em meses e a estimativa de custo em reais"))]


def _escopo_sem_campo(p):
    return [("paragrafo", _a_preencher("esta parte ainda não tem campo no SGPP; escreva aqui"))]


# As partes do Escopo que o formulário de Elaboração já cobre. Quando uma parte ganhar campo no formulário, entra aqui.
PARTES_PREENCHIDAS = {"I": _escopo_i, "II": _escopo_ii, "VIII": _escopo_viii, "XII": _escopo_xii}


def _montar_escopo_projeto(p, abas, c, hoje):
    nome = _nome(p)
    blocos = [("titulo", "ESCOPO DE PROJETO"), ("titulo", f"PROJETO {nome.upper()}")]
    for parte in guia.ESCOPO_ATO_PGJ:
        blocos.append(("titulo", f"{parte['numero']}. {parte['titulo']}"))
        blocos += PARTES_PREENCHIDAS.get(parte["numero"], _escopo_sem_campo)(p)
    return Documento(
        tipo="escopo_projeto", tipo_sei="Projeto", titulo=TIPOS_DOCUMENTO["escopo_projeto"]["titulo"],
        blocos=blocos, assinante=_assinante(c), assinatura_no_corpo=False, data=hoje)


def projeto_do_rascunho(rascunho, gestor):
    """O rascunho com os nomes de coluna do projeto, para gerar o Escopo antes de o projeto ser enviado."""
    return {"Nome da Iniciativa": rascunho.get("nome"), "Unidade": rascunho.get("unidade"), "Gestor": gestor,
            "Ementa (Objetivo)": rascunho.get("ementa"), "Alinhamento Estratégico": rascunho.get("alinhamento_est"),
            "Alinhamento ao PEN": rascunho.get("alinhamento_pen"), "INICIO_PREVISTO": rascunho.get("inicio_previsto"),
            "TERMINO_PREVISTO": rascunho.get("termino_previsto"), "Status": rascunho.get("status"), "SEI": rascunho.get("sei"),
            "ID_PROJETO": "rascunho"}


_MONTADORES = {
    "memorando_devolucao": _montar_memorando_devolucao,
    "parecer_tecnico": _montar_parecer_tecnico,
    "memorando_comite": _montar_memorando_comite,
    "certidao_inclusao_portfolio": _montar_certidao_inclusao,
    "memorando_reenvio": _montar_memorando_reenvio,
    "certidao_atividade": _montar_certidao_atividade,
    "escopo_projeto": _montar_escopo_projeto,
    "relatorio_atuacao": _montar_relatorio_atuacao,
}


def montar(tipo, projeto, abas, campos=None, hoje=None):
    """Monta o documento. `campos` pode trazer só alguns campos; o resto vem dos padrões."""
    if tipo not in TIPOS_DOCUMENTO:
        raise ValueError(f"documento desconhecido: {tipo}")
    hoje = hoje or date.today()
    campos = {k: v for k, v in (campos or {}).items()}
    completos = {**campos_padrao(tipo, projeto, abas, "", hoje, escolhidos=campos), **campos}
    return _MONTADORES[tipo](projeto, abas, completos, hoje)


# ------------------------------------------------------------------ edição dos blocos pela tela

def bloco_para_texto(bloco):
    """O bloco como texto de uma caixa de edição: a lista vira uma linha por item e o campo mostra só o valor."""
    if bloco[0] == "lista":
        return "\n".join(bloco[1])
    return bloco[2] if bloco[0] == "campo" else bloco[1]


def texto_para_bloco(bloco, texto):
    """Devolve o bloco com o texto editado. Item de lista vazio some."""
    if bloco[0] == "lista":
        return ("lista", [linha.strip() for linha in texto.splitlines() if linha.strip()])
    if bloco[0] == "campo":
        return ("campo", bloco[1], texto.strip())
    return (bloco[0], texto.strip())


def _agrupar_campos(blocos):
    """Campos seguidos (Processo, Interessado, Iniciativa) saem juntos, sem linha em branco entre eles."""
    saida = []
    for bloco in blocos:
        if bloco[0] != "campo":
            saida.append(bloco)
        elif saida and saida[-1][0] == "campos":
            saida[-1][1].append((bloco[1], bloco[2]))
        else:
            saida.append(("campos", [(bloco[1], bloco[2])]))
    return saida


# ------------------------------------------------------------------ dados pessoais

_PADROES_PESSOAIS = [
    ("CPF", re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b")),
    ("número de processo judicial", re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")),
    ("e-mail", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("telefone", re.compile(r"\(\d{2}\)\s?9?\d{4}-?\d{4}|\b9\d{4}-\d{4}\b")),
]


def alertas_dados_pessoais(texto):
    """O que parece dado pessoal no texto: CPF, número de processo judicial, e-mail e telefone. Nome não dá para detectar."""
    return [rotulo for rotulo, padrao in _PADROES_PESSOAIS if padrao.search(texto or "")]


# ------------------------------------------------------------------ saída: texto e HTML

def _partes_do_texto(doc):
    partes = []
    if doc.destinatario:
        partes.append("\n".join(doc.destinatario))
    if doc.assunto:
        partes.append(f"Assunto: {doc.assunto}")
    if doc.vocativo:
        partes.append(doc.vocativo)
    for bloco in _agrupar_campos(doc.blocos):
        if bloco[0] == "lista":
            partes.append("\n".join(f"- {item}" for item in bloco[1]))
        elif bloco[0] == "campos":
            partes.append("\n".join(f"{rotulo}: {valor}" for rotulo, valor in bloco[1]))
        else:
            partes.append(bloco[1])
    if doc.fecho:
        partes.append(doc.fecho)
    if doc.assinatura_no_corpo and doc.assinante:
        partes.append("\n".join(doc.assinante))
    return [p for p in partes if p]


def para_texto(doc):
    """O corpo do documento para colar no editor do SEI: sem número e sem o bloco de assinatura, que são do SEI."""
    return "\n\n".join(_partes_do_texto(doc)) + "\n"


def _h(texto):
    return html.escape(texto, quote=True).replace("\n", "<br>")


def para_html(doc):
    """O mesmo corpo em HTML simples, para colar no editor do SEI (ou numa extensão que insere HTML)."""
    saida = []
    if doc.destinatario:
        saida.append(f"<p>{'<br>'.join(_h(l) for l in doc.destinatario)}</p>")
    if doc.assunto:
        saida.append(f"<p><strong>Assunto:</strong> {_h(doc.assunto)}</p>")
    if doc.vocativo:
        saida.append(f"<p>{_h(doc.vocativo)}</p>")
    for bloco in _agrupar_campos(doc.blocos):
        if bloco[0] == "lista":
            saida.append("<ul>" + "".join(f"<li>{_h(item)}</li>" for item in bloco[1]) + "</ul>")
        elif bloco[0] == "campos":
            saida.append("<p>" + "<br>".join(f"<strong>{_h(rotulo)}:</strong> {_h(valor)}" for rotulo, valor in bloco[1]) + "</p>")
        elif bloco[0] == "titulo":
            saida.append(f"<p><strong>{_h(bloco[1])}</strong></p>")
        else:
            saida.append(f'<p style="text-align:justify">{_h(bloco[1])}</p>')
    if doc.fecho:
        saida.append(f"<p>{_h(doc.fecho)}</p>")
    if doc.assinatura_no_corpo and doc.assinante:
        saida.append(f'<p style="text-align:center">{"<br>".join(_h(l) for l in doc.assinante)}</p>')
    return "\n".join(saida) + "\n"


# ------------------------------------------------------------------ saída: PDF

_TROCAS_LATIN1 = {"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "–": "-", "—": "-",
                  "…": "...", "•": "-", " ": " ", " ": " ", "​": ""}


def para_latin1(texto):
    """As fontes nativas do PDF só escrevem Latin-1 (cobre o português). Aspas curvas, travessão e reticências viram os
    equivalentes simples; o que não cabe vira '?'."""
    for velho, novo in _TROCAS_LATIN1.items():
        texto = texto.replace(velho, novo)
    return texto.encode("latin-1", "replace").decode("latin-1")


def para_pdf(doc, modo="minuta", comprimir=True):
    """O documento em PDF (A4, Times 12). Modo "minuta": título, texto e rodapé, sem número nem linha de assinatura.
    Modo "externo": acrescenta local, data e linha de assinatura, para incluir no SEI como documento externo."""
    from fpdf import FPDF

    quando = doc.data or date.today()
    rodape = (f"Documento gerado pelo SGPP em {quando.strftime('%d/%m/%Y')}." if modo == "externo" else
              f"Minuta gerada pelo SGPP em {quando.strftime('%d/%m/%Y')}. Número e assinatura eletrônica são atribuídos pelo SEI.")

    class _Pdf(FPDF):
        def footer(self):
            self.set_y(-18)
            self.set_font("Times", "I", 9)
            self.cell(0, 5, para_latin1(rodape), align="C", new_x="LMARGIN", new_y="NEXT")
            self.cell(0, 5, f"Página {self.page_no()}/{{nb}}", align="C")

    pdf = _Pdf(format="A4", unit="mm")
    pdf.set_compression(comprimir)
    pdf.set_margins(30, 25, 20)
    pdf.set_auto_page_break(True, margin=25)
    pdf.set_title(para_latin1(doc.titulo))
    pdf.set_author("SGPP")
    pdf.set_creator("SGPP")
    pdf.alias_nb_pages()
    pdf.add_page()

    def paragrafo(texto, estilo="", alinhamento="J", recuo=0):
        pdf.set_font("Times", estilo, 12)
        pdf.set_x(pdf.l_margin + recuo)
        pdf.multi_cell(0, 6, para_latin1(texto), align=alinhamento, new_x="LMARGIN", new_y="NEXT")

    paragrafo(doc.tipo_sei.upper(), "B", "C")
    pdf.ln(4)
    if doc.destinatario:
        for linha in doc.destinatario:
            paragrafo(linha, alinhamento="L")
        pdf.ln(4)
    if doc.assunto:
        pdf.set_font("Times", "B", 12)
        pdf.write(6, "Assunto: ")
        pdf.set_font("Times", "", 12)
        pdf.write(6, para_latin1(doc.assunto))
        pdf.ln(10)
    if doc.vocativo:
        paragrafo(doc.vocativo, alinhamento="L")
        pdf.ln(3)
    for bloco in _agrupar_campos(doc.blocos):
        if bloco[0] == "lista":
            for item in bloco[1]:
                paragrafo(f"- {item}", recuo=8)
            pdf.ln(3)
        elif bloco[0] == "campos":
            for rotulo, valor in bloco[1]:
                pdf.set_font("Times", "B", 12)
                pdf.write(6, para_latin1(f"{rotulo}: "))
                pdf.set_font("Times", "", 12)
                pdf.write(6, para_latin1(valor))
                pdf.ln(6)
            pdf.ln(3)
        elif bloco[0] == "titulo":
            paragrafo(bloco[1], "B", "L")
            pdf.ln(2)
        else:
            paragrafo(bloco[1])
            pdf.ln(3)
    if doc.fecho:
        paragrafo(doc.fecho, alinhamento="L")
        pdf.ln(3)
    if modo == "externo":
        pdf.ln(4)
        paragrafo(f"{CIDADE_PADRAO}, {_data_extenso(quando)}.", alinhamento="R")
        pdf.ln(12)
        paragrafo("_" * 40, alinhamento="C")
        for linha in doc.assinante:
            paragrafo(linha, alinhamento="C")
    elif doc.assinatura_no_corpo and doc.assinante:
        pdf.ln(8)
        for linha in doc.assinante:
            paragrafo(linha, alinhamento="C")
    return bytes(pdf.output())


# ------------------------------------------------------------------ nome do arquivo

def _slug(texto):
    ascii_ = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9-]+", "_", ascii_).strip("_")


def nome_do_arquivo(doc, projeto, extensao):
    """Ex.: Certidao_inclusao_2026-0007_Escola_em_Paz.pdf (sem acento nem espaço)."""
    partes = [TIPOS_DOCUMENTO[doc.tipo]["arquivo"], _slug(_t(projeto.get("CODIGO")) or projetos.chave(projeto)), _slug(_nome(projeto))]
    return "_".join(p for p in partes if p) + f".{extensao}"
