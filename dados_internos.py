"""Planilha interna do SGPP: usuários, registro de alterações e (nas próximas etapas) rascunhos,
pareceres e histórico. É um arquivo à parte da planilha de projetos que o Power BI lê.

Todas as abas são lidas e gravadas como texto. A gravação usa o mesmo controle de versão
(etag) da planilha de projetos: se outra pessoa gravou antes, nada é sobrescrito.
"""
import io

import pandas as pd

from contas import COLUNAS_USUARIOS
from projetos import ABAS_PROJETOS

COLUNAS_REGISTRO = ["data_hora", "ator", "acao", "alvo", "detalhe"]

ABAS = {
    "Usuarios": COLUNAS_USUARIOS,
    "Registro": COLUNAS_REGISTRO,
    **ABAS_PROJETOS,
}


def _aba_vazia(colunas):
    return pd.DataFrame({c: pd.Series(dtype="object") for c in colunas})


def ler_internos(armazenamento):
    """Devolve ({nome_da_aba: DataFrame}, etag). Abas ou colunas que faltam são criadas vazias."""
    conteudo, etag = armazenamento.ler()
    abas = {}
    if conteudo is not None:
        lidas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None, dtype=str)
        abas = {nome: df.fillna("") for nome, df in lidas.items()}
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
