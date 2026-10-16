"""Regras do ciclo do projeto: rascunho, envio, trava de edição, atualizações, pareceres, arquivamento
e linha do tempo. Sem dependência do Streamlit, para poder ser testado sozinho.

Onde cada coisa fica:
  * Planilha de projetos (a que o Power BI lê): o estado do projeto, em colunas acrescentadas no fim
    (CODIGO, INICIO_PREVISTO, TERMINO_PREVISTO, EDICAO, ENVIADO_POR, ENVIADO_EM, ID_RASCUNHO,
    PEDIDO_LIBERACAO) e SITUACAO_REGISTRO (Ativo, Arquivado ou Excluído). Cada mudança de estado é uma
    gravação só, com controle de versão.
  * Planilha interna (privada): Rascunhos, Atualizacoes, Pareceres e Historico.

As funções recebem e devolvem DataFrames e não gravam nada.
"""
import re
import uuid
from datetime import date, datetime

import pandas as pd

from contas import agora

# ------------------------------------------------------------------ constantes

COLUNAS_NOVAS_PROJETO = [
    "CODIGO", "INICIO_PREVISTO", "TERMINO_PREVISTO", "EDICAO",
    "ENVIADO_POR", "ENVIADO_EM", "ID_RASCUNHO", "PEDIDO_LIBERACAO", "REVISAO", "ID_PROJETO",
]
EDICAO_TRAVADA = "Travada"
EDICAO_LIBERADA = "Liberada"

# Ciclo de revisão do projeto enviado: Aguardando revisão -> (Devolvido para ajustes -> Ajustes reenviados)* -> Revisão concluída
REVISAO_AGUARDANDO = "Aguardando revisão"
REVISAO_DEVOLVIDO = "Devolvido para ajustes"
REVISAO_REENVIADO = "Ajustes reenviados"
REVISAO_CONCLUIDA = "Revisão concluída"
REVISOES = [REVISAO_AGUARDANDO, REVISAO_DEVOLVIDO, REVISAO_REENVIADO, REVISAO_CONCLUIDA]

SITUACAO_ATIVO = "Ativo"
SITUACAO_ARQUIVADO = "Arquivado"
SITUACAO_EXCLUIDO = "Excluído"

TIPOS = ["Projeto", "Programa", "Boa Prática"]
STATUS = ["Em elaboração", "Em execução", "Concluído", "Paralisado"]
SITUACOES_ATUALIZACAO = ["Em dia", "Atenção", "Atrasado"]
CONCLUSOES_PARECER = ["Favorável", "Favorável com ressalvas", "Desfavorável"]

CAMPOS_RASCUNHO = [
    "nome", "tipo", "area", "unidade", "municipio", "alinhamento_est", "alinhamento_pen", "ano",
    "sei", "status", "institucionalizado", "ementa", "inicio_previsto", "termino_previsto",
]
COLUNAS_RASCUNHOS = ["id", "autor_login", "autor_nome", "situacao", "criado_em", "atualizado_em",
                     "enviado_em", "projeto_n"] + CAMPOS_RASCUNHO
COLUNAS_ATUALIZACOES = ["id", "projeto_n", "data_referencia", "situacao", "texto", "autor_login", "autor_nome", "registrado_em"]
COLUNAS_PARECERES = ["id", "projeto_n", "conclusao", "texto", "autor_login", "autor_nome", "registrado_em"]
COLUNAS_HISTORICO = ["projeto_n", "data_hora", "ator_login", "ator_nome", "evento", "detalhe"]
COLUNAS_COMENTARIOS = ["id", "projeto_n", "tipo", "texto", "autor_login", "autor_nome", "registrado_em"]
TIPOS_COMENTARIO = {"comentario": "Comentário", "devolucao": "Devolvido para ajustes", "conclusao": "Revisão concluída"}

ABAS_PROJETOS = {
    "Rascunhos": COLUNAS_RASCUNHOS,
    "Atualizacoes": COLUNAS_ATUALIZACOES,
    "Pareceres": COLUNAS_PARECERES,
    "Comentarios": COLUNAS_COMENTARIOS,
    "Historico": COLUNAS_HISTORICO,
}

# Rótulo de cada evento da linha do tempo
EVENTOS = {
    "enviado": "Enviado à Planejamento",
    "comentario": "Comentário registrado",
    "devolvido": "Devolvido para ajustes",
    "reenviado": "Ajustes reenviados",
    "revisao_concluida": "Revisão concluída",
    "liberacao_solicitada": "Liberação de edição solicitada",
    "edicao_liberada": "Edição liberada",
    "liberacao_negada": "Liberação negada",
    "editado": "Dados alterados",
    "travado": "Edição travada",
    "atualizacao": "Atualização registrada",
    "parecer": "Parecer registrado",
    "arquivado": "Arquivado",
    "reativado": "Reativado",
    "excluido": "Excluído",
    "restaurado": "Restaurado",
}

# Quem pode o quê (níveis de contas.py). O comitê, por ora, só aprova usuários.
_PERMISSOES = {
    "criar_rascunho": {"administrador", "planejamento", "comite", "gestor_unidade", "gestor_projeto"},
    "atualizar_qualquer_projeto": {"administrador", "planejamento"},
    "emitir_parecer": {"administrador", "planejamento"},
    "liberar_edicao": {"administrador", "planejamento"},
    "arquivar": {"administrador", "planejamento"},
    "revisar": {"administrador", "planejamento"},
    "ver_pendencias": {"administrador", "planejamento", "comite"},
}


def pode(acao, nivel):
    return nivel in _PERMISSOES.get(acao, set())


# ------------------------------------------------------------------ utilitários

def texto(valor):
    """Valor de célula como texto limpo ('' para vazio ou NaN)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return ""
    t = str(valor).strip()
    return "" if t.lower() in ("nan", "none", "nat") else t


def novo_id():
    return uuid.uuid4().hex[:10]


def parse_data(valor):
    """'AAAA-MM-DD' (ou date) -> date; vazio ou inválido -> None."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    t = texto(valor)[:10]
    try:
        return datetime.strptime(t, "%Y-%m-%d").date()
    except ValueError:
        return None


def data_iso(valor):
    d = parse_data(valor)
    return d.isoformat() if d else ""


def garantir_colunas(df):
    df = df.copy()
    for coluna in COLUNAS_NOVAS_PROJETO:
        if coluna not in df.columns:
            df[coluna] = ""
        df[coluna] = df[coluna].map(texto)
    return df


def _normalizar_n(valor):
    return re.sub(r"\.0$", "", str(valor).strip())


def chave(linha):
    """Identificador do projeto: ID_PROJETO, ou o Nº quando a linha ainda não tem ID (planilhas de teste e dados antigos)."""
    return texto(linha.get("ID_PROJETO")) or _normalizar_n(linha.get("Nº"))


def _indice(df, n):
    """Linha do projeto. A chave é o ID_PROJETO; o Nº só serve de reserva, porque na planilha real há Nº repetidos."""
    procurado = _normalizar_n(n)
    if "ID_PROJETO" in df.columns:
        achados = df.index[df["ID_PROJETO"].map(texto) == procurado]
        if len(achados):
            return achados[0]
    achados = df.index[df["Nº"].map(_normalizar_n) == procurado]
    return achados[0] if len(achados) else None


def atribuir_ids(df):
    """Dá ID_PROJETO a quem não tem. É o Nº quando ele é único na planilha; se o Nº se repete (ou falta), recebe
    um sufixo pela ordem das linhas: 28-1, 28-2. IDs já existentes nunca mudam."""
    df = garantir_colunas(df)
    numeros = df["Nº"].map(_normalizar_n)
    repeticoes = numeros.map(numeros.value_counts())
    usados = {i for i in df["ID_PROJETO"] if i}
    contagem = {}
    for indice in df.index[df["ID_PROJETO"] == ""]:
        base = numeros[indice]
        if base in ("", "nan", "None"):
            base, unico = "sem-n", False
        else:
            unico = repeticoes[indice] == 1 and base not in usados
        if unico:
            novo = base
        else:
            contagem[base] = contagem.get(base, 0) + 1
            novo = f"{base}-{contagem[base]}"
            while novo in usados:
                contagem[base] += 1
                novo = f"{base}-{contagem[base]}"
        df.at[indice, "ID_PROJETO"] = novo
        usados.add(novo)
    return df


def _n_int(valor):
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ código AAAA-NNNN

_PADRAO_CODIGO = re.compile(r"^(\d{4})-(\d{4})$")


def _ano(valor):
    n = _n_int(valor)
    return f"{n:04d}" if n and 2000 <= n <= 2100 else None


def preencher_codigos(df):
    """Dá código AAAA-NNNN aos projetos que não têm, pelo ano de criação e em ordem de Nº.

    Quem não tem ano de criação válido fica sem código (aparece no relatório de pendências).
    A numeração continua depois do maior código já existente no ano, então é estável.
    """
    df = garantir_colunas(df)
    maiores = {}
    for codigo in df["CODIGO"]:
        m = _PADRAO_CODIGO.match(codigo)
        if m:
            maiores[m.group(1)] = max(maiores.get(m.group(1), 0), int(m.group(2)))
    sem_codigo = df[df["CODIGO"] == ""]
    ordem = sem_codigo.assign(_ordem=pd.to_numeric(sem_codigo["Nº"], errors="coerce")).sort_values("_ordem", na_position="last")
    for indice in ordem.index:
        ano = _ano(df.at[indice, "Ano de criação"]) if "Ano de criação" in df.columns else None
        if ano is None:
            continue
        maiores[ano] = maiores.get(ano, 0) + 1
        df.at[indice, "CODIGO"] = f"{ano}-{maiores[ano]:04d}"
    return df


def proximo_codigo(df, ano):
    ano = _ano(ano) or f"{datetime.now().year:04d}"
    maior = 0
    for codigo in df["CODIGO"] if "CODIGO" in df.columns else []:
        m = _PADRAO_CODIGO.match(texto(codigo))
        if m and m.group(1) == ano:
            maior = max(maior, int(m.group(2)))
    return f"{ano}-{maior + 1:04d}"


def proximo_numero(df):
    numeros = pd.to_numeric(df["Nº"], errors="coerce").dropna() if "Nº" in df.columns and len(df) else pd.Series(dtype=float)
    return int(numeros.max()) + 1 if len(numeros) else 1


# ------------------------------------------------------------------ rascunhos

def dados_vazios():
    return {
        "nome": "", "tipo": TIPOS[0], "area": "", "unidade": "", "municipio": "Manaus",
        "alinhamento_est": "", "alinhamento_pen": "", "ano": datetime.now().year, "sei": "",
        "status": STATUS[0], "institucionalizado": "Não", "ementa": "", "inicio_previsto": "", "termino_previsto": "",
    }


def validar_dados(dados, para_envio):
    """Devolve a mensagem de erro, ou None. Para salvar rascunho basta um nome; para enviar, os campos obrigatórios."""
    if len(texto(dados.get("nome"))) < 3:
        return "Dê ao rascunho um nome com pelo menos 3 caracteres."
    inicio, termino = texto(dados.get("inicio_previsto")), texto(dados.get("termino_previsto"))
    if inicio and parse_data(inicio) is None:
        return "Data de início prevista inválida."
    if termino and parse_data(termino) is None:
        return "Data de término prevista inválida."
    if inicio and termino and parse_data(termino) < parse_data(inicio):
        return "O término previsto não pode ser anterior ao início previsto."
    if para_envio:
        faltam = [rotulo for campo, rotulo in (("tipo", "Tipo"), ("area", "Área de atuação"), ("unidade", "Unidade"),
                                               ("municipio", "Município"), ("ementa", "Ementa")) if not texto(dados.get(campo))]
        if faltam:
            return "Preencha os campos obrigatórios antes de enviar: " + ", ".join(faltam) + "."
        if _ano(dados.get("ano")) is None:
            return "Informe um ano de criação válido."
    return None


def _limpar_dados(dados):
    limpo = {c: texto(dados.get(c)) for c in CAMPOS_RASCUNHO}
    limpo["inicio_previsto"] = data_iso(dados.get("inicio_previsto"))
    limpo["termino_previsto"] = data_iso(dados.get("termino_previsto"))
    limpo["ano"] = str(_n_int(dados.get("ano")) or "")
    return limpo


def criar_rascunho(abas, autor_login, autor_nome, dados, quando=None):
    """Acrescenta um rascunho aberto. Devolve (id, erro)."""
    erro = validar_dados(dados, para_envio=False)
    if erro:
        return None, erro
    quando = quando or agora()
    id_ = novo_id()
    linha = {"id": id_, "autor_login": autor_login, "autor_nome": autor_nome, "situacao": "aberto",
             "criado_em": quando, "atualizado_em": quando, "enviado_em": "", "projeto_n": "", **_limpar_dados(dados)}
    abas["Rascunhos"] = pd.concat([abas["Rascunhos"], pd.DataFrame([linha], columns=COLUNAS_RASCUNHOS)], ignore_index=True)
    return id_, None


def _linha_rascunho(abas, id_):
    achados = abas["Rascunhos"].index[abas["Rascunhos"]["id"] == id_]
    return achados[0] if len(achados) else None


def buscar_rascunho(abas, id_, autor_login):
    """Rascunho do autor como dicionário, ou None. Ninguém além do autor enxerga o rascunho."""
    indice = _linha_rascunho(abas, id_)
    if indice is None or abas["Rascunhos"].at[indice, "autor_login"] != autor_login:
        return None
    return {c: texto(abas["Rascunhos"].at[indice, c]) for c in COLUNAS_RASCUNHOS}


def atualizar_rascunho(abas, id_, autor_login, dados, quando=None):
    erro = validar_dados(dados, para_envio=False)
    if erro:
        return erro
    atual = buscar_rascunho(abas, id_, autor_login)
    if atual is None:
        return "Rascunho não encontrado."
    if atual["situacao"] != "aberto":
        return "Este rascunho já foi enviado ou descartado."
    indice = _linha_rascunho(abas, id_)
    for campo, valor in _limpar_dados(dados).items():
        abas["Rascunhos"].at[indice, campo] = valor
    abas["Rascunhos"].at[indice, "atualizado_em"] = quando or agora()
    return None


def descartar_rascunho(abas, id_, autor_login):
    atual = buscar_rascunho(abas, id_, autor_login)
    if atual is None:
        return "Rascunho não encontrado."
    if atual["situacao"] != "aberto":
        return "Este rascunho já foi enviado ou descartado."
    abas["Rascunhos"].at[_linha_rascunho(abas, id_), "situacao"] = "descartado"
    return None


def rascunhos_abertos(abas, autor_login, df_projetos=None):
    """Rascunhos abertos do autor, do mais recente ao mais antigo. Os já presentes na planilha de projetos
    (envio concluído mas ainda não marcado) ficam de fora."""
    r = abas["Rascunhos"]
    r = r[(r["autor_login"] == autor_login) & (r["situacao"] == "aberto")]
    if df_projetos is not None and "ID_RASCUNHO" in df_projetos.columns:
        r = r[~r["id"].isin(set(df_projetos["ID_RASCUNHO"].map(texto)))]
    return r.iloc[::-1]


def marcar_rascunho_enviado(abas, id_, projeto_n, quando=None):
    indice = _linha_rascunho(abas, id_)
    if indice is None:
        return
    abas["Rascunhos"].loc[indice, ["situacao", "enviado_em", "projeto_n"]] = ["enviado", quando or agora(), str(projeto_n)]


# ------------------------------------------------------------------ envio

def enviar_rascunho(df, rascunho, quando=None):
    """Cria o projeto na planilha a partir do rascunho. Devolve (df, numero, codigo, erro).

    Idempotente: se o rascunho já virou projeto (ID_RASCUNHO presente), devolve o projeto existente
    sem criar outro, o que torna seguro repetir o envio depois de uma falha no meio do caminho.
    """
    df = garantir_colunas(df)
    existente = df.index[df["ID_RASCUNHO"] == rascunho["id"]]
    if len(existente):
        i = existente[0]
        return df, _n_int(df.at[i, "Nº"]), df.at[i, "CODIGO"], None
    erro = validar_dados(rascunho, para_envio=True)
    if erro:
        return df, None, None, erro

    df = atribuir_ids(preencher_codigos(df))
    quando = quando or agora()
    n = proximo_numero(df)
    codigo = proximo_codigo(df, rascunho["ano"])
    inst = rascunho["institucionalizado"] == "Sim"
    linha = {
        "Iniciativa": n, "Nº": n, "Nome da Iniciativa": rascunho["nome"],
        "Projeto/Programa/Boa Prática": rascunho["tipo"], "Área de Atuação": rascunho["area"],
        "Alinhamento Estratégico": rascunho["alinhamento_est"], "Alinhamento ao PEN": rascunho["alinhamento_pen"],
        "Ano de criação": _n_int(rascunho["ano"]), "SEI": rascunho["sei"], "Unidade": rascunho["unidade"],
        "Município": rascunho["municipio"], "Gestor": rascunho["autor_nome"], "Ementa (Objetivo)": rascunho["ementa"],
        "Status": rascunho["status"], "Institucionalizado": "Sim" if inst else "Não",
        "Ato PGJ": "Institucionalizado" if inst else "",
        "OBSERVAÇÕES/CORREÇÕES": "", "AVALIAÇÃO": "", "AUDITOR_DPLAN": "",
        "SITUACAO_REGISTRO": SITUACAO_ATIVO, "EXCLUIDO_POR": "", "MOTIVO_EXCLUSAO": "", "DATA_EXCLUSAO": "",
        "CODIGO": codigo, "INICIO_PREVISTO": rascunho["inicio_previsto"], "TERMINO_PREVISTO": rascunho["termino_previsto"],
        "EDICAO": EDICAO_TRAVADA, "ENVIADO_POR": rascunho["autor_login"], "ENVIADO_EM": quando,
        "ID_RASCUNHO": rascunho["id"], "PEDIDO_LIBERACAO": "", "REVISAO": REVISAO_AGUARDANDO, "ID_PROJETO": str(n),
    }
    return pd.concat([df, pd.DataFrame([linha])], ignore_index=True), n, codigo, None


# ------------------------------------------------------------------ trava de edição

def edicao_do_projeto(df, n):
    indice = _indice(df, n)
    return "" if indice is None else texto(df.at[indice, "EDICAO"]) if "EDICAO" in df.columns else ""


def esta_travado(df, n):
    return edicao_do_projeto(df, n) == EDICAO_TRAVADA


def parse_pedido(valor):
    """'dd/mm/aaaa hh:mm | login | motivo' -> dict, ou None."""
    partes = texto(valor).split(" | ", 2)
    if len(partes) != 3:
        return None
    return {"quando": partes[0], "login": partes[1], "motivo": partes[2]}


def solicitar_liberacao(df, n, ator_login, motivo, quando=None):
    indice = _indice(df, n)
    if indice is None:
        return df, "Projeto não encontrado."
    if texto(df.at[indice, "EDICAO"]) != EDICAO_TRAVADA:
        return df, "Este projeto não está travado."
    if parse_pedido(df.at[indice, "PEDIDO_LIBERACAO"]):
        return df, "Já existe um pedido de liberação aguardando a Planejamento."
    motivo = texto(motivo).replace(" | ", " - ")
    if len(motivo) < 10:
        return df, "Explique o que precisa alterar (mínimo de 10 caracteres)."
    df = df.copy()
    df.at[indice, "PEDIDO_LIBERACAO"] = f"{quando or agora()} | {ator_login} | {motivo}"
    return df, None


def liberar_edicao(df, n):
    """Planejamento libera a edição; o pedido, se houver, é encerrado."""
    indice = _indice(df, n)
    if indice is None:
        return df, "Projeto não encontrado."
    if texto(df.at[indice, "EDICAO"]) == EDICAO_LIBERADA:
        return df, "A edição deste projeto já está liberada."
    df = df.copy()
    df.loc[indice, ["EDICAO", "PEDIDO_LIBERACAO"]] = [EDICAO_LIBERADA, ""]
    return df, None


def negar_liberacao(df, n):
    indice = _indice(df, n)
    if indice is None:
        return df, "Projeto não encontrado."
    if not parse_pedido(df.at[indice, "PEDIDO_LIBERACAO"]):
        return df, "Não há pedido de liberação para este projeto."
    df = df.copy()
    df.at[indice, "PEDIDO_LIBERACAO"] = ""
    return df, None


def travar_projeto(df, n):
    indice = _indice(df, n)
    if indice is None:
        return df, "Projeto não encontrado."
    if texto(df.at[indice, "EDICAO"]) == EDICAO_TRAVADA:
        return df, "O projeto já está travado."
    df = df.copy()
    df.at[indice, "EDICAO"] = EDICAO_TRAVADA
    return df, None


def retravar_apos_edicao(df, numeros):
    """Depois que o gestor salva, os projetos que estavam liberados voltam a ficar travados.
    Devolve (df, numeros_que_foram_travados)."""
    df = df.copy()
    travados = []
    for n in numeros:
        indice = _indice(df, n)
        if indice is not None and texto(df.at[indice, "EDICAO"]) == EDICAO_LIBERADA:
            df.at[indice, "EDICAO"] = EDICAO_TRAVADA
            travados.append(n)
    return df, travados


def pedidos_pendentes(df):
    """Projetos ativos com pedido de liberação aguardando, do mais antigo ao mais novo."""
    df = garantir_colunas(df)
    pend = df[(df["PEDIDO_LIBERACAO"] != "") & (df["SITUACAO_REGISTRO"] == SITUACAO_ATIVO)]
    return pend.reset_index(drop=True)


# ------------------------------------------------------------------ revisão e comentários

def para_revisar(df):
    """Projetos ativos que esperam a Planejamento: recém-enviados ou com ajustes reenviados."""
    df = garantir_colunas(df)
    fila = df[(df["SITUACAO_REGISTRO"] == SITUACAO_ATIVO) & df["REVISAO"].isin([REVISAO_AGUARDANDO, REVISAO_REENVIADO])]
    return fila.reset_index(drop=True)


def devolver_para_ajustes(df, n):
    """A Planejamento devolve o projeto ao gestor: a edição é liberada e ele fica 'Devolvido para ajustes'."""
    indice = _indice(df, n)
    if indice is None:
        return df, "Projeto não encontrado."
    if texto(df.at[indice, "SITUACAO_REGISTRO"]) != SITUACAO_ATIVO:
        return df, "Só é possível devolver um projeto ativo."
    if texto(df.at[indice, "REVISAO"]) == REVISAO_DEVOLVIDO:
        return df, "O projeto já está com o gestor para ajustes."
    df = df.copy()
    df.loc[indice, ["REVISAO", "EDICAO", "PEDIDO_LIBERACAO"]] = [REVISAO_DEVOLVIDO, EDICAO_LIBERADA, ""]
    return df, None


def concluir_revisao(df, n):
    indice = _indice(df, n)
    if indice is None:
        return df, "Projeto não encontrado."
    if texto(df.at[indice, "SITUACAO_REGISTRO"]) != SITUACAO_ATIVO:
        return df, "Só é possível concluir a revisão de um projeto ativo."
    atual = texto(df.at[indice, "REVISAO"])
    if atual == REVISAO_DEVOLVIDO:
        return df, "O projeto está com o gestor para ajustes. Aguarde o reenvio."
    if atual == REVISAO_CONCLUIDA:
        return df, "A revisão deste projeto já está concluída."
    df = df.copy()
    df.at[indice, "REVISAO"] = REVISAO_CONCLUIDA
    return df, None


def marcar_reenvio(df, numeros):
    """Quando o gestor salva alterações num projeto devolvido (ou de revisão já concluída), ele volta para a fila.
    Devolve (df, numeros_reenviados)."""
    df = df.copy()
    reenviados = []
    for n in numeros:
        indice = _indice(df, n)
        if indice is not None and texto(df.at[indice, "REVISAO"]) in (REVISAO_DEVOLVIDO, REVISAO_CONCLUIDA):
            df.at[indice, "REVISAO"] = REVISAO_REENVIADO
            reenviados.append(_normalizar_n(n))
    return df, reenviados


def pode_comentar(nivel, nome_usuario, gestor_do_projeto):
    """Comentam e leem o fio de comentários: a Planejamento e o Administrador, e o gestor do projeto."""
    if pode("revisar", nivel):
        return True
    return nivel != "leitor" and texto(gestor_do_projeto).lower() == texto(nome_usuario).lower() and bool(texto(nome_usuario))


def registrar_comentario(abas, n, tipo, texto_, autor_login, autor_nome, quando=None):
    """Acrescenta ao fio de comentários do projeto. Devolve a mensagem de erro, ou None."""
    if tipo not in TIPOS_COMENTARIO:
        return "Tipo de comentário inválido."
    minimo = {"comentario": 5, "devolucao": 10, "conclusao": 0}[tipo]
    if len(texto(texto_)) < minimo:
        return f"Escreva o comentário (mínimo de {minimo} caracteres)." if tipo != "devolucao" else "Explique o que precisa ser ajustado (mínimo de 10 caracteres)."
    linha = {"id": novo_id(), "projeto_n": _normalizar_n(n), "tipo": tipo, "texto": texto(texto_),
             "autor_login": autor_login, "autor_nome": autor_nome, "registrado_em": quando or agora()}
    abas["Comentarios"] = pd.concat([abas["Comentarios"], pd.DataFrame([linha], columns=COLUNAS_COMENTARIOS)], ignore_index=True)
    return None


def comentarios_do_projeto(abas, n):
    """Fio de comentários do projeto, do mais antigo ao mais novo: lista de dicts."""
    c = abas["Comentarios"]
    c = c[c["projeto_n"].map(_normalizar_n) == _normalizar_n(n)]
    return [{"tipo": r.tipo, "rotulo": TIPOS_COMENTARIO.get(r.tipo, r.tipo), "texto": texto(r.texto),
             "autor_login": r.autor_login, "autor_nome": texto(r.autor_nome) or r.autor_login, "quando": r.registrado_em}
            for r in c.itertuples()]


# ------------------------------------------------------------------ arquivamento

def arquivar_projeto(df, n, motivo):
    indice = _indice(df, n)
    if indice is None:
        return df, "Projeto não encontrado."
    if texto(df.at[indice, "SITUACAO_REGISTRO"]) != SITUACAO_ATIVO:
        return df, "Só é possível arquivar um projeto ativo."
    if len(texto(motivo)) < 5:
        return df, "Informe o motivo do arquivamento (mínimo de 5 caracteres)."
    df = df.copy()
    df.at[indice, "SITUACAO_REGISTRO"] = SITUACAO_ARQUIVADO
    return df, None


def reativar_projeto(df, n):
    indice = _indice(df, n)
    if indice is None:
        return df, "Projeto não encontrado."
    if texto(df.at[indice, "SITUACAO_REGISTRO"]) != SITUACAO_ARQUIVADO:
        return df, "Este projeto não está arquivado."
    df = df.copy()
    df.at[indice, "SITUACAO_REGISTRO"] = SITUACAO_ATIVO
    return df, None


# ------------------------------------------------------------------ edição pelo gestor

COLUNAS_EDITAVEIS_GESTOR = [
    "Nome da Iniciativa", "Projeto/Programa/Boa Prática", "Área de Atuação", "Alinhamento Estratégico",
    "Alinhamento ao PEN", "Ano de criação", "SEI", "Unidade", "Município", "Ementa (Objetivo)", "Status",
    "Institucionalizado", "INICIO_PREVISTO", "TERMINO_PREVISTO",
]


def validar_datas_previstas(inicio, termino):
    inicio, termino = texto(inicio), texto(termino)
    if inicio and parse_data(inicio) is None:
        return "Início previsto inválido (use AAAA-MM-DD)."
    if termino and parse_data(termino) is None:
        return "Término previsto inválido (use AAAA-MM-DD)."
    if inicio and termino and parse_data(termino) < parse_data(inicio):
        return "O término previsto não pode ser anterior ao início previsto."
    return None


def campos_alterados(antes, depois, colunas=COLUNAS_EDITAVEIS_GESTOR):
    """Nomes das colunas que mudaram entre duas linhas (dict ou Series)."""
    return [c for c in colunas if c in antes and c in depois and texto(antes[c]) != texto(depois[c])]


def aplicar_edicoes(df_completo, df_origem, df_editado):
    """Aplica na planilha as edições feitas por um gestor na tabela de edição.

    `df_origem` é a tabela mostrada ao gestor e `df_editado` o que voltou do editor (mesmo índice).
    Devolve (df_novo, alterados, travados, reenviados, erro): `alterados` mapeia o número do projeto aos campos que
    mudaram, `travados` lista os que estavam liberados e voltaram a ficar travados e `reenviados` os que voltaram
    para a fila de revisão da Planejamento (estavam devolvidos para ajustes ou com a revisão concluída).
    """
    alterados = {}
    for indice in df_editado.index:
        campos = campos_alterados(df_origem.loc[indice], df_editado.loc[indice])
        if not campos:
            continue
        numero = chave(df_origem.loc[indice])
        erro = validar_datas_previstas(df_editado.at[indice, "INICIO_PREVISTO"], df_editado.at[indice, "TERMINO_PREVISTO"])
        if erro:
            return df_completo, {}, [], [], f"Projeto Nº {numero}: {erro}"
        alterados[numero] = campos
    if not alterados:
        return df_completo, {}, [], [], None
    df_novo = df_completo.copy()
    df_novo.update(df_editado)
    df_novo, travados = retravar_apos_edicao(df_novo, list(alterados))
    df_novo, reenviados = marcar_reenvio(df_novo, list(alterados))
    return df_novo, alterados, travados, reenviados, None


# ------------------------------------------------------------------ quadro (kanban)

COLUNA_OUTROS = "Outros status"
COLUNAS_QUADRO = STATUS + [COLUNA_OUTROS]


def coluna_do_quadro(status):
    """Coluna do quadro de um status. O que não é um dos quatro status do app (inclusive vazio) vai para 'Outros status'."""
    s = texto(status)
    return s if s in STATUS else COLUNA_OUTROS


def pode_mover_status(linha, nivel, nome_usuario):
    """Quem move o cartão: Planejamento e Administrador, sempre; o gestor do projeto, se a edição não estiver travada.
    Devolve (pode, motivo_se_nao)."""
    if nivel in ("administrador", "planejamento"):
        return True, ""
    if nivel in ("leitor", "comite"):
        return False, "O seu nível só consulta o quadro."
    if texto(linha.get("Gestor")).lower() != texto(nome_usuario).lower():
        return False, "Só o gestor do projeto ou a Planejamento move este cartão."
    if texto(linha.get("EDICAO")) == EDICAO_TRAVADA:
        return False, "Projeto travado: peça a liberação da edição em Meus Projetos."
    return True, ""


def mover_status(df, n, destino, nivel, nome_usuario):
    """Muda o status de um projeto. Devolve (df, status_anterior, voltou_a_travar, reenviado, erro).

    Mudar o status é uma edição: se quem move é o gestor e a edição estava liberada, o projeto volta a ficar
    travado, como em qualquer outra edição. A Planejamento não altera a trava ao mover.
    """
    if destino not in STATUS:
        return df, "", False, False, "Escolha um dos status do quadro."
    indice = _indice(df, n)
    if indice is None:
        return df, "", False, False, "Projeto não encontrado."
    if texto(df.at[indice, "SITUACAO_REGISTRO"]) != SITUACAO_ATIVO:
        return df, "", False, False, "Só projetos ativos podem ser movidos."
    pode, motivo = pode_mover_status(df.loc[indice], nivel, nome_usuario)
    if not pode:
        return df, "", False, False, motivo
    anterior = texto(df.at[indice, "Status"])
    if anterior == destino:
        return df, anterior, False, False, "O projeto já está nesse status."
    df = df.copy()
    df.at[indice, "Status"] = destino
    voltou = False
    if nivel not in ("administrador", "planejamento") and texto(df.at[indice, "EDICAO"]) == EDICAO_LIBERADA:
        df.at[indice, "EDICAO"] = EDICAO_TRAVADA
        voltou = True
    reenviado = False
    if nivel not in ("administrador", "planejamento"):
        df, reenviados = marcar_reenvio(df, [n])
        reenviado = bool(reenviados)
    return df, anterior, voltou, reenviado, None


# ------------------------------------------------------------------ relatório de pendências

CAMPOS_OBRIGATORIOS = [
    ("Nome da Iniciativa", "Nome"), ("Projeto/Programa/Boa Prática", "Tipo"), ("Área de Atuação", "Área de atuação"),
    ("Unidade", "Unidade"), ("Município", "Município"), ("Gestor", "Gestor"), ("Ementa (Objetivo)", "Ementa"),
    ("Status", "Status"),
]
GRAVIDADES = ["Obrigatório", "Atenção", "Recomendado"]  # da mais para a menos importante


def pendencias_do_projeto(linha, hoje=None):
    """Pendências de um projeto: lista de (gravidade, categoria, detalhe).

    A categoria agrupa o mesmo problema em projetos diferentes; o detalhe é o texto mostrado.
    """
    hoje = hoje or datetime.now().date()
    achadas = []
    for coluna, rotulo in CAMPOS_OBRIGATORIOS:
        if not texto(linha.get(coluna)):
            achadas.append(("Obrigatório", f"{rotulo} em branco", f"{rotulo} em branco"))

    status = texto(linha.get("Status"))
    if status and status not in STATUS:
        achadas.append(("Atenção", "Status fora do padrão", f"Status fora do padrão: {status}"))
    inicio, termino = parse_data(linha.get("INICIO_PREVISTO")), parse_data(linha.get("TERMINO_PREVISTO"))
    if inicio and termino and termino < inicio:
        achadas.append(("Atenção", "Datas previstas incoerentes", "Término previsto anterior ao início previsto"))
    elif termino and termino < hoje and status in ("Em elaboração", "Em execução"):
        achadas.append(("Atenção", "Prazo vencido", f"Prazo vencido: término previsto em {termino.strftime('%d/%m/%Y')}"))

    if not texto(linha.get("CODIGO")):
        achadas.append(("Recomendado", "Sem ano de criação (sem código)", "Sem ano de criação válido, por isso sem código"))
    if not texto(linha.get("SEI")):
        achadas.append(("Recomendado", "Sem nº SEI", "Sem nº do processo SEI"))
    if not texto(linha.get("Institucionalizado")):
        achadas.append(("Recomendado", "Institucionalizado em branco", "Institucionalizado em branco"))
    return achadas


def pendencias_detalhadas(df, hoje=None):
    """Uma linha por pendência: n, codigo, projeto, gestor, unidade, gravidade, categoria, detalhe."""
    df = garantir_colunas(df)
    repetidos = df["Nº"].map(_normalizar_n)
    repetidos = repetidos.map(repetidos.value_counts())
    linhas = []
    for indice, projeto in df[df["SITUACAO_REGISTRO"] == SITUACAO_ATIVO].iterrows():
        achadas = pendencias_do_projeto(projeto, hoje)
        if repetidos[indice] > 1 and _normalizar_n(projeto["Nº"]) not in ("", "nan", "None"):
            achadas.append(("Atenção", "Nº repetido na planilha", f"O Nº {_normalizar_n(projeto['Nº'])} está em mais de um projeto"))
        for gravidade, categoria, detalhe in achadas:
            linhas.append({
                "n": chave(projeto), "codigo": texto(projeto.get("CODIGO")),
                "projeto": texto(projeto.get("Nome da Iniciativa")), "gestor": texto(projeto.get("Gestor")),
                "unidade": texto(projeto.get("Unidade")), "gravidade": gravidade, "categoria": categoria, "detalhe": detalhe,
            })
    return pd.DataFrame(linhas, columns=["n", "codigo", "projeto", "gestor", "unidade", "gravidade", "categoria", "detalhe"])


def relatorio_pendencias(df, hoje=None):
    """Uma linha por projeto ativo que tenha alguma pendência, dos mais graves aos menos graves.

    Colunas: n, codigo, projeto, gestor, unidade, gravidade (a maior do projeto), pendencias (textos),
    categorias (lista), qtd. Deriva de pendencias_detalhadas, para os totais nunca divergirem da lista.
    """
    colunas = ["n", "codigo", "projeto", "gestor", "unidade", "gravidade", "pendencias", "categorias", "qtd"]
    detalhe = pendencias_detalhadas(df, hoje)
    if detalhe.empty:
        return pd.DataFrame(columns=colunas)
    linhas = []
    for n, grupo in detalhe.groupby("n", sort=False):
        primeira = grupo.iloc[0]
        linhas.append({
            "n": n, "codigo": primeira["codigo"], "projeto": primeira["projeto"], "gestor": primeira["gestor"],
            "unidade": primeira["unidade"], "gravidade": min(grupo["gravidade"], key=GRAVIDADES.index),
            "pendencias": grupo["detalhe"].tolist(), "categorias": grupo["categoria"].tolist(), "qtd": len(grupo),
        })
    relatorio = pd.DataFrame(linhas, columns=colunas)
    ordem = relatorio["gravidade"].map(GRAVIDADES.index)
    return relatorio.assign(_g=ordem).sort_values(["_g", "qtd"], ascending=[True, False], kind="stable").drop(columns="_g").reset_index(drop=True)


def resumo_pendencias(df, hoje=None):
    """Totais por categoria: DataFrame (gravidade, categoria, projetos), mais graves primeiro."""
    detalhe = pendencias_detalhadas(df, hoje)
    if detalhe.empty:
        return pd.DataFrame(columns=["gravidade", "categoria", "projetos"])
    resumo = (detalhe.groupby(["gravidade", "categoria"], sort=False)["n"].nunique().rename("projetos").reset_index())
    return (resumo.assign(_g=resumo["gravidade"].map(GRAVIDADES.index))
            .sort_values(["_g", "projetos"], ascending=[True, False], kind="stable").drop(columns="_g").reset_index(drop=True))


# ------------------------------------------------------------------ atualizações e pareceres

def registrar_atualizacao(abas, n, data_referencia, situacao, texto_, autor_login, autor_nome, quando=None):
    data = parse_data(data_referencia)
    if data is None:
        return "Informe a data de referência."
    if data > datetime.now().date():
        return "A data de referência não pode ser futura."
    if situacao not in SITUACOES_ATUALIZACAO:
        return "Escolha a situação do projeto."
    if len(texto(texto_)) < 10:
        return "Descreva o andamento (mínimo de 10 caracteres)."
    linha = {"id": novo_id(), "projeto_n": str(n), "data_referencia": data.isoformat(), "situacao": situacao,
             "texto": texto(texto_), "autor_login": autor_login, "autor_nome": autor_nome, "registrado_em": quando or agora()}
    abas["Atualizacoes"] = pd.concat([abas["Atualizacoes"], pd.DataFrame([linha], columns=COLUNAS_ATUALIZACOES)], ignore_index=True)
    return None


def registrar_parecer(abas, n, conclusao, texto_, autor_login, autor_nome, quando=None):
    if conclusao and conclusao not in CONCLUSOES_PARECER:
        return "Conclusão inválida."
    if len(texto(texto_)) < 10:
        return "Escreva o parecer (mínimo de 10 caracteres)."
    linha = {"id": novo_id(), "projeto_n": str(n), "conclusao": conclusao or "", "texto": texto(texto_),
             "autor_login": autor_login, "autor_nome": autor_nome, "registrado_em": quando or agora()}
    abas["Pareceres"] = pd.concat([abas["Pareceres"], pd.DataFrame([linha], columns=COLUNAS_PARECERES)], ignore_index=True)
    return None


def do_projeto(abas, aba, n):
    """Linhas de uma aba (Atualizacoes ou Pareceres) do projeto, da mais recente para a mais antiga."""
    df = abas[aba]
    return df[df["projeto_n"].astype(str) == str(n)].iloc[::-1]


# ------------------------------------------------------------------ histórico e linha do tempo

def evento(n, ator_login, ator_nome, tipo, detalhe="", quando=None):
    if tipo not in EVENTOS:
        raise ValueError(f"evento desconhecido: {tipo}")
    return {"projeto_n": str(n), "data_hora": quando or agora(), "ator_login": ator_login,
            "ator_nome": ator_nome, "evento": tipo, "detalhe": detalhe}


def acrescentar_eventos(abas, eventos):
    """O histórico só recebe linhas novas; nada é alterado nem apagado."""
    if isinstance(eventos, dict):
        eventos = [eventos]
    abas["Historico"] = pd.concat([abas["Historico"], pd.DataFrame(eventos, columns=COLUNAS_HISTORICO)], ignore_index=True)


def _quando(valor):
    try:
        return datetime.strptime(texto(valor), "%d/%m/%Y %H:%M")
    except ValueError:
        return datetime.min


def linha_do_tempo(abas, n):
    """Eventos do projeto em ordem cronológica: lista de dicts (quando, quem, rotulo, detalhe)."""
    h = abas["Historico"]
    h = h[h["projeto_n"].astype(str) == str(n)]
    itens = [
        {"quando": r.data_hora, "quem": r.ator_nome or r.ator_login, "evento": r.evento,
         "rotulo": EVENTOS.get(r.evento, r.evento), "detalhe": r.detalhe}
        for r in h.itertuples()
    ]
    return sorted(itens, key=lambda i: _quando(i["quando"]))


def resumo_arquivamento(abas, n, df=None):
    """Datas do ciclo do projeto: enviado, arquivado (último), quem e por quê, e dias entre os dois."""
    itens = linha_do_tempo(abas, n)
    enviado = next((i for i in itens if i["evento"] == "enviado"), None)
    arquivado = next((i for i in reversed(itens) if i["evento"] == "arquivado"), None)
    dias = None
    if enviado and arquivado:
        dias = (_quando(arquivado["quando"]) - _quando(enviado["quando"])).days
    return {
        "enviado_em": enviado["quando"] if enviado else "",
        "arquivado_em": arquivado["quando"] if arquivado else "",
        "arquivado_por": arquivado["quem"] if arquivado else "",
        "motivo": arquivado["detalhe"] if arquivado else "",
        "dias": dias,
    }
