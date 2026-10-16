"""A planilha real tem Nº repetido (projetos diferentes com o mesmo número). Nada pode atingir o projeto errado."""
import openpyxl
import pandas as pd
import pytest

import projetos
from apoio import botao, entrar_codigo, semear_codigo
from conftest import PLANILHA_EXEMPLO
from test_app import ir_para
from test_etapa2 import ANA, PAULA, internos
from test_etapa3 import STATUS_INDICE, alterar_planilha, colunas_do_quadro


@pytest.fixture
def repetidos(pasta, monkeypatch):
    """Nos projetos 2 e 3 do exemplo, o Nº passa a ser o mesmo (2): duas iniciativas diferentes com o mesmo número."""
    semear_codigo(monkeypatch, ANA, PAULA)
    alterar_planilha({3: {"Nº": 2}})


def lido():
    return pd.read_excel(PLANILHA_EXEMPLO, dtype=str).fillna("")


def duas_linhas():
    df = lido()
    return df[df["Nº"] == "2"].reset_index(drop=True)


def test_todas_as_telas_abrem_com_numero_repetido(repetidos):
    at = entrar_codigo(PAULA[0])
    for pagina in ("dashboard", "quadro", "meus", "elaboracao", "acompanhamento", "planilha", "exportar", "pendencias", "revisao", "painel"):
        at = ir_para(at, pagina)
        assert not at.exception, (pagina, [e.value for e in at.exception])


def test_quadro_mostra_os_dois_projetos_e_move_so_o_escolhido(repetidos):
    at = ir_para(entrar_codigo(PAULA[0]), "quadro")
    total = len(pd.read_excel(PLANILHA_EXEMPLO))
    assert sum(colunas_do_quadro(at).values()) == total  # nenhum cartão some por causa do Nº repetido
    chaves = {b.key for b in at.button if b.key and b.key.startswith("mv_2-")}
    assert {c.split("_")[1] for c in chaves} == {"2-1", "2-2"}

    antes = duas_linhas()["Status"].tolist()
    destino = "Paralisado"
    at = at.button(key=f"mv_2-2_{STATUS_INDICE[destino]}").click().run()
    assert not at.exception
    depois = duas_linhas()
    assert depois["Status"].tolist() == [antes[0], destino]  # só o segundo mudou
    assert depois["ID_PROJETO"].tolist() == ["2-1", "2-2"]  # os IDs ficaram gravados na planilha
    assert internos()["Historico"].iloc[-1]["projeto_n"] == "2-2"


def test_excluir_um_dos_repetidos_nao_exclui_o_outro(repetidos):
    at = ir_para(entrar_codigo(PAULA[0]), "painel")
    at.selectbox(key="sel_del_admin").set_value("2-1")
    at.text_input(key="mot_del_admin").set_value("Cadastro em duplicidade")
    at = botao(at, "Executar Exclusão").click().run()
    assert not at.exception
    assert duas_linhas()["SITUACAO_REGISTRO"].tolist() == ["Excluído", "Ativo"]
    at.selectbox(key="sel_rest_admin").set_value("2-1")
    at = at.run()
    at = at.button(key="restaurar_projeto").click().run()
    assert duas_linhas()["SITUACAO_REGISTRO"].tolist() == ["Ativo", "Ativo"]


def test_comentarios_ficam_no_projeto_certo(repetidos):
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at.selectbox(key="revisao_alvo").set_value("2-2")
    at = at.run()
    at.text_area(key="rev_texto_proj_2-2").set_value("Comentário só para o segundo projeto de Nº 2.")
    at.button(key="so_comentar_proj_2-2").click().run()
    comentarios = internos()["Comentarios"]
    assert comentarios["projeto_n"].tolist() == ["2-2"]
    assert projetos.comentarios_do_projeto(internos(), "2-1") == []


def test_pendencias_apontam_o_numero_repetido(repetidos):
    at = ir_para(entrar_codigo(PAULA[0]), "pendencias")
    at.multiselect(key="pend_gravidade").set_value(["Atenção"])
    at.multiselect(key="pend_categoria").set_value(["Nº repetido na planilha"])
    at = at.run()
    legenda = " ".join(c.value for c in at.caption)
    assert "2 projeto(s) e 2 pendência(s)" in legenda


def alterar_celula(linha_excel, coluna, valor):
    """Altera uma célula pela linha da planilha (a 2 é o primeiro projeto), já que o Nº não identifica a linha."""
    livro = openpyxl.load_workbook(PLANILHA_EXEMPLO)
    folha = livro.active
    folha.cell(row=linha_excel, column=[c.value for c in folha[1]].index(coluna) + 1).value = valor
    livro.save(PLANILHA_EXEMPLO)


def test_gestor_so_move_o_cartao_dele_mesmo_com_o_numero_repetido(repetidos):
    # o projeto da linha 4 (antes Nº 3, agora Nº 2 também) passa a ser da Ana; o da linha 3 segue com outra pessoa
    alterar_celula(4, "Gestor", ANA[1])
    at = ir_para(entrar_codigo(ANA[0]), "quadro")
    meus = {b.key.split("_")[1] for b in at.button if b.key and b.key.startswith("mv_")}
    assert meus == {"2-2"}  # só o dela, apesar de dividir o Nº com outro projeto
    destino = "Paralisado"
    at = at.button(key=f"mv_2-2_{STATUS_INDICE[destino]}").click().run()
    assert not at.exception and duas_linhas()["Status"].tolist()[1] == destino
    assert duas_linhas()["Status"].tolist()[0] != destino
