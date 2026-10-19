"""Fonte de dados do SGPP, a planilha interna: projetos, usuários, registro de alterações, rascunhos,
atualizações, pareceres, comentários e histórico. É um arquivo à parte da planilha original do Power BI, que o
SGPP só lê (uma vez, para copiar os projetos) e nunca grava.

A aba Projetos é lida com os tipos que o Excel tem (números continuam números); as demais são lidas como
texto. A gravação usa o controle de versão (etag): se outra pessoa gravou antes, nada é sobrescrito.
"""
import io

import pandas as pd

from armazenamento import ArmazenamentoLocal, ConflitoDeVersao
from contas import COLUNAS_USUARIOS
from projetos import ABAS_PROJETOS, normalizar_nomes_da_original

ABA_PROJETOS = "Projetos"

COLUNAS_REGISTRO = ["data_hora", "ator", "acao", "alvo", "detalhe"]

ABAS = {
    "Usuarios": COLUNAS_USUARIOS,
    "Registro": COLUNAS_REGISTRO,
    **ABAS_PROJETOS,
}


def _aba_vazia(colunas):
    return pd.DataFrame({c: pd.Series(dtype="object") for c in colunas})


def ler_internos(armazenamento):
    """Devolve ({nome_da_aba: DataFrame}, etag). Abas ou colunas que faltam são criadas vazias. A aba Projetos
    (sem colunas fixas, vazia se ainda não foi copiada) mantém os tipos do Excel."""
    conteudo, etag = armazenamento.ler()
    abas = {}
    if conteudo is not None:
        planilha = pd.ExcelFile(io.BytesIO(conteudo))
        for nome in planilha.sheet_names:
            abas[nome] = planilha.parse(nome) if nome == ABA_PROJETOS else planilha.parse(nome, dtype=str).fillna("")
    if ABA_PROJETOS not in abas:
        abas[ABA_PROJETOS] = pd.DataFrame()
    for nome, colunas in ABAS.items():
        df = abas.get(nome)
        if df is None:
            abas[nome] = _aba_vazia(colunas)
            continue
        for coluna in colunas:
            if coluna not in df.columns:
                df[coluna] = ""
        abas[nome] = df
    return abas, etag


def gravar_internos(armazenamento, abas, etag):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as escritor:
        for nome, df in abas.items():
            df.to_excel(escritor, index=False, sheet_name=nome)
    return armazenamento.gravar(buffer.getvalue(), etag)


def acrescentar_registro(abas, linhas):
    """Acrescenta linhas ao Registro de alterações. Só acrescenta; nunca altera nem apaga."""
    if isinstance(linhas, dict):
        linhas = [linhas]
    novo = pd.DataFrame(linhas, columns=COLUNAS_REGISTRO)
    abas["Registro"] = pd.concat([abas["Registro"], novo], ignore_index=True)
    return abas


def garantir_projetos(interno, original):
    """Lê a fonte de dados do SGPP. Na primeira vez (aba Projetos vazia), copia a planilha original, que só é lida.

    Depois da cópia, a original não é mais consultada: os projetos passam a ser do SGPP. Se outra sessão copiar
    ao mesmo tempo, vale a cópia dela. Devolve (abas, etag).
    """
    for _ in range(3):
        abas, etag = ler_internos(interno)
        if not abas[ABA_PROJETOS].empty:
            return abas, etag
        conteudo, _etag_original = original.ler()
        if conteudo is None:
            return abas, etag
        abas[ABA_PROJETOS] = normalizar_nomes_da_original(pd.read_excel(io.BytesIO(conteudo)))
        try:
            gravar_internos(interno, abas, etag)
        except ConflitoDeVersao:
            continue
        return ler_internos(interno)
    return ler_internos(interno)


def pode_gravar_projetos(interno, em_sharepoint):
    """No SharePoint, os projetos só podem ser gravados se a fonte de dados também estiver lá: um arquivo local
    do servidor some quando ele reinicia, e com ele as alterações."""
    return not (em_sharepoint and isinstance(interno, ArmazenamentoLocal))
