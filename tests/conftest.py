"""Fixtures dos testes de tela: cada teste roda numa pasta temporária, com a planilha de exemplo
e uma planilha interna própria, sem tocar nos arquivos do repositório."""
import shutil
from pathlib import Path

import pytest
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
PLANILHA_EXEMPLO = "PROJETOS - Teste 1.xlsx"
ADMIN = ("chefe.geral", "senha-do-admin-1")
# Os testes de cadastro e aprovação ligam o modo planilha; o modo padrão (usuários no código) tem testes próprios
SEGREDOS = {"login": {"administrador": ADMIN[0], "senha_administrador": ADMIN[1], "origem_usuarios": "planilha"}}
SEGREDOS_CODIGO = {"login": {"administrador": ADMIN[0], "senha_administrador": ADMIN[1]}}


@pytest.fixture
def pasta(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    shutil.copy(RAIZ / PLANILHA_EXEMPLO, tmp_path / PLANILHA_EXEMPLO)
    # st.cache_* vive no processo todo: sem isto, o limitador de tentativas e os caches vazariam entre testes
    st.cache_resource.clear()
    st.cache_data.clear()
    return tmp_path
