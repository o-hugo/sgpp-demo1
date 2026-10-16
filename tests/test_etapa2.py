"""Fluxo completo da etapa 2 pela interface: rascunho, envio, trava, pedido de liberação, atualização,
parecer, arquivamento e linha do tempo. Usuários definidos no código, como no modo padrão."""
import pandas as pd
import pytest

import dados_internos
import projetos
from apoio import (
    CAMINHO_INTERNO, botao, entrar_codigo, preencher_rascunho, semear_codigo, textos_visiveis,
)
from armazenamento import ArmazenamentoLocal
from conftest import PLANILHA_EXEMPLO
from test_app import MENU, ir_para

ANA = ("ana.souza", "Ana Souza Lima", "gestor_projeto")
PAULA = ("paula.plan", "Paula Planejamento Dias", "planejamento")
CARLOS = ("carlos.comite", "Carlos Comitê Silva", "comite")
LEITORA = ("leitora.um", "Leitora Um Silva", "leitor")


@pytest.fixture
def equipe(pasta, monkeypatch):
    semear_codigo(monkeypatch, ANA, PAULA, CARLOS, LEITORA)


def internos():
    abas, _ = dados_internos.ler_internos(ArmazenamentoLocal(CAMINHO_INTERNO))
    return abas


def projetos_na_planilha():
    """Planilha de projetos como o app a lê (com os nomes de coluna do app)."""
    return pd.read_excel(PLANILHA_EXEMPLO, dtype=str).fillna("").rename(columns={"Iniciativa.1": "Nome da Iniciativa"})


def projeto_novo():
    df = projetos_na_planilha()
    return df[df["ID_RASCUNHO"] != ""].iloc[-1]


def enviar_projeto(login=ANA[0], **campos):
    """Faz o caminho completo na tela: abre a Elaboração, preenche e envia. Devolve a sessão."""
    at = ir_para(entrar_codigo(login), "elaboracao")
    assert not at.exception
    preencher_rascunho(at, **campos)
    at = botao(at, "Enviar para a Planejamento").click().run()
    assert not at.exception
    return at


# ------------------------------------------------------------------ rascunho e envio

def test_rascunho_salvo_e_privado_e_nao_entra_na_planilha_de_projetos(equipe):
    linhas = len(projetos_na_planilha())
    at = ir_para(entrar_codigo(ANA[0]), "elaboracao")
    at = botao(preencher_rascunho(at, nome="Rascunho secreto"), "Salvar rascunho").click().run()
    assert not at.exception and any("Rascunho salvo" in s.value for s in at.success)

    abas = internos()
    assert abas["Rascunhos"].iloc[0][["autor_login", "situacao", "nome"]].tolist() == ["ana.souza", "aberto", "Rascunho secreto"]
    assert len(projetos_na_planilha()) == linhas  # a Planejamento não vê nada na planilha

    # depois de salvar, o app abre o rascunho salvo, com os valores guardados
    assert at.text_input(key=f"r_nome_{abas['Rascunhos'].iloc[0]['id']}").value == "Rascunho secreto"

    # outra pessoa, mesmo da Planejamento, não enxerga o rascunho
    outra = ir_para(entrar_codigo(PAULA[0]), "elaboracao")
    assert outra.selectbox(key="rascunho_sel").options == ["Novo rascunho"]


def test_envio_cria_o_projeto_travado_com_codigo_e_registra_no_historico(equipe):
    linhas = len(projetos_na_planilha())
    at = enviar_projeto(nome="Escola em Paz")
    assert any("Projeto enviado à Planejamento" in s.value for s in at.success)

    df = projetos_na_planilha()
    assert len(df) == linhas + 1
    novo = projeto_novo()
    assert novo["Nome da Iniciativa"] == "Escola em Paz" and novo["Gestor"] == "Ana Souza Lima"
    assert novo["EDICAO"] == "Travada" and novo["SITUACAO_REGISTRO"] == "Ativo"
    assert novo["CODIGO"].startswith(f"{pd.Timestamp.now().year}-") and novo["ENVIADO_POR"] == "ana.souza"

    abas = internos()
    assert abas["Rascunhos"].iloc[0]["situacao"] == "enviado" and abas["Rascunhos"].iloc[0]["projeto_n"] == str(int(float(novo["Nº"])))
    evento = abas["Historico"].iloc[0]
    assert evento["evento"] == "enviado" and evento["ator_login"] == "ana.souza" and novo["CODIGO"] in evento["detalhe"]

    # o rascunho enviado sai da lista de abertos
    assert at.selectbox(key="rascunho_sel").options == ["Novo rascunho"]


def test_envio_incompleto_e_recusado_sem_criar_projeto(equipe):
    linhas = len(projetos_na_planilha())
    at = ir_para(entrar_codigo(ANA[0]), "elaboracao")
    at = botao(preencher_rascunho(at, ementa=""), "Enviar para a Planejamento").click().run()
    assert any("Ementa" in e.value for e in at.error)
    assert len(projetos_na_planilha()) == linhas
    assert internos()["Rascunhos"].empty  # nada foi salvo junto com o erro


def test_descartar_rascunho(equipe):
    at = ir_para(entrar_codigo(ANA[0]), "elaboracao")
    at = botao(preencher_rascunho(at), "Salvar rascunho").click().run()
    chave = internos()["Rascunhos"].iloc[0]["id"]
    assert at.button(key="perigo_descartar_rascunho").disabled
    at.checkbox(key=f"descartar_ok_{chave}").set_value(True)
    at = at.run()
    at = at.button(key="perigo_descartar_rascunho").click().run()
    assert any("descartado" in s.value for s in at.success)
    assert internos()["Rascunhos"].iloc[0]["situacao"] == "descartado" and at.selectbox(key="rascunho_sel").options == ["Novo rascunho"]


def test_leitor_nao_cria_projetos_e_nao_ve_meus_projetos_nem_elaboracao(equipe):
    at = entrar_codigo(LEITORA[0])
    opcoes = at.sidebar.radio[0].options
    assert MENU["elaboracao"] not in opcoes and MENU["meus"] not in opcoes
    assert MENU["acompanhamento"] in opcoes and MENU["revisao"] not in opcoes


def test_comite_cria_projetos_mas_nao_ve_a_revisao(equipe):
    opcoes = entrar_codigo(CARLOS[0]).sidebar.radio[0].options
    assert MENU["elaboracao"] in opcoes and MENU["revisao"] not in opcoes


# ------------------------------------------------------------------ trava, pedido e liberação

def test_pedido_de_liberacao_liberacao_pela_planejamento_e_volta_a_travar(equipe):
    enviar_projeto()
    n = str(int(float(projeto_novo()["Nº"])))

    # a gestora pede a liberação
    at = ir_para(entrar_codigo(ANA[0]), "meus")
    assert not at.exception and at.selectbox(key="sel_pedido")  # projeto travado: só dá para pedir
    at.text_area(key="motivo_pedido").set_value("Corrigir o município e a ementa do projeto")
    at = at.button(key="solicitar_liberacao").click().run()
    assert any("Pedido enviado" in s.value for s in at.success)
    assert projetos.parse_pedido(projeto_novo()["PEDIDO_LIBERACAO"])["login"] == "ana.souza"
    assert internos()["Historico"].iloc[-1]["evento"] == "liberacao_solicitada"

    # a Planejamento vê o pedido e libera
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    assert not at.exception and any("Pedidos de liberação (1)" in t.label for t in at.tabs)
    at = at.button(key=f"liberar_{n}").click().run()
    assert any("liberada" in s.value for s in at.success)
    novo = projeto_novo()
    assert novo["EDICAO"] == "Liberada" and novo["PEDIDO_LIBERACAO"] == ""
    assert internos()["Historico"].iloc[-1]["evento"] == "edicao_liberada"

    # com a edição liberada, o projeto passa para a tabela editável da gestora
    at = ir_para(entrar_codigo(ANA[0]), "meus")
    assert not at.exception and not [s for s in at.selectbox if s.key == "sel_pedido"]
    assert any("Edição livre ou liberada" in m.value for m in at.markdown)


def test_planejamento_pode_negar_o_pedido_e_o_projeto_continua_travado(equipe):
    enviar_projeto()
    n = str(int(float(projeto_novo()["Nº"])))
    at = ir_para(entrar_codigo(ANA[0]), "meus")
    at.text_area(key="motivo_pedido").set_value("Corrigir o município e a ementa do projeto")
    at.button(key="solicitar_liberacao").click().run()

    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at = at.button(key=f"negar_{n}").click().run()  # sem explicar, não nega
    assert any("Explique o motivo" in e.value for e in at.error) and projeto_novo()["PEDIDO_LIBERACAO"] != ""
    at.text_input(key=f"cm_ped_{n}").set_value("O projeto ainda está em revisão; envie as correções por comentário.")
    at = at.button(key=f"negar_{n}").click().run()
    assert any("negado" in s.value for s in at.success)
    novo = projeto_novo()
    assert novo["EDICAO"] == "Travada" and novo["PEDIDO_LIBERACAO"] == ""
    assert internos()["Historico"].iloc[-1]["evento"] == "liberacao_negada"


def test_planejamento_trava_e_libera_sem_pedido(equipe):
    enviar_projeto()
    n = str(int(float(projeto_novo()["Nº"])))
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at.selectbox(key="revisao_alvo").set_value(n)
    at = at.run()
    at = at.button(key="liberar_direto").click().run()
    assert projeto_novo()["EDICAO"] == "Liberada"
    at = ir_para(at, "revisao")
    at.selectbox(key="revisao_alvo").set_value(n)
    at = at.run()
    at = at.button(key="travar_direto").click().run()
    assert projeto_novo()["EDICAO"] == "Travada"
    assert [e for e in internos()["Historico"]["evento"]][-3:] == ["enviado", "edicao_liberada", "travado"]


def test_projeto_travado_nao_pode_ser_excluido_pelo_proprio_gestor(equipe):
    enviar_projeto()
    at = ir_para(entrar_codigo(ANA[0]), "meus")
    assert not at.exception
    assert not [b for b in at.button if b.key == "perigo_excluir_meu"]
    assert any("travados" in i.value for i in at.info)


# ------------------------------------------------------------------ acompanhamento

def test_gestora_registra_atualizacao_e_ela_aparece_na_linha_do_tempo(equipe):
    enviar_projeto()
    n = str(int(float(projeto_novo()["Nº"])))
    at = ir_para(entrar_codigo(ANA[0]), "acompanhamento")
    assert not at.exception and at.selectbox(key="acomp_projeto").value == n
    campo = next(t for t in at.text_area if "O que aconteceu" in t.label)
    campo.set_value("Reunião com a rede de proteção realizada.")
    at = botao(at, "Registrar atualização").click().run()
    assert any("Atualização registrada" in s.value for s in at.success)

    abas = internos()
    linha = abas["Atualizacoes"].iloc[0]
    assert linha["projeto_n"] == n and linha["situacao"] == "Em dia" and linha["autor_login"] == "ana.souza"
    assert abas["Historico"].iloc[-1]["evento"] == "atualizacao"
    assert "Reunião com a rede de proteção realizada." in "\n".join(m.value for m in at.markdown)  # na lista de atualizações


def test_atualizacao_curta_demais_e_recusada(equipe):
    enviar_projeto()
    at = ir_para(entrar_codigo(ANA[0]), "acompanhamento")
    next(t for t in at.text_area if "O que aconteceu" in t.label).set_value("ok")
    at = botao(at, "Registrar atualização").click().run()
    assert any("mínimo de 10" in e.value for e in at.error)
    assert internos()["Atualizacoes"].empty


def test_so_a_planejamento_emite_parecer_e_o_gestor_do_projeto_o_le(equipe):
    enviar_projeto()
    n = str(int(float(projeto_novo()["Nº"])))

    # a gestora não emite parecer
    at = ir_para(entrar_codigo(ANA[0]), "acompanhamento")
    assert not [b for b in at.button if "parecer" in b.label.lower()]

    # a Planejamento emite
    at = ir_para(entrar_codigo(PAULA[0]), "acompanhamento")
    at.radio(key="acomp_escopo").set_value("Todo o portfólio")
    at = at.run()
    at.selectbox(key="acomp_projeto").set_value(n)
    at = at.run()
    next(t for t in at.text_area if t.label == "Parecer").set_value("Projeto bem estruturado, com ressalva no cronograma.")
    at = botao(at, "Registrar parecer").click().run()
    assert any("Parecer registrado" in s.value for s in at.success)
    assert internos()["Pareceres"].iloc[0]["autor_login"] == "paula.plan"

    # a gestora lê o parecer sobre o próprio projeto
    at = ir_para(entrar_codigo(ANA[0]), "acompanhamento")
    assert "Projeto bem estruturado, com ressalva no cronograma." in "\n".join(m.value for m in at.markdown)

    # a leitora não vê o parecer
    leitora = ir_para(entrar_codigo(LEITORA[0]), "acompanhamento")
    leitora.selectbox(key="acomp_projeto").set_value(n)
    leitora = leitora.run()
    assert "Projeto bem estruturado" not in "\n".join(m.value for m in leitora.markdown)
    assert not [t for t in leitora.text_area]  # e não registra atualização nem parecer


# ------------------------------------------------------------------ arquivo e linha do tempo

def test_arquivar_tira_do_portfolio_registra_motivo_e_permite_reativar(equipe):
    enviar_projeto()
    n = str(int(float(projeto_novo()["Nº"])))
    ativos_antes = ir_para(entrar_codigo(PAULA[0]), "dashboard").metric[0].value

    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at.selectbox(key="arquivar_alvo").set_value(n)
    at.text_input(key="arquivar_motivo").set_value("Projeto encerrado pela unidade")
    at = at.run()
    at = at.button(key="arquivar_projeto").click().run()
    assert any("arquivado" in s.value.lower() for s in at.success)
    assert projeto_novo()["SITUACAO_REGISTRO"] == "Arquivado"
    evento = internos()["Historico"].iloc[-1]
    assert evento["evento"] == "arquivado" and evento["detalhe"] == "Projeto encerrado pela unidade"

    # sai do dashboard (que mostra só ativos) e aparece no arquivo, com a linha do tempo completa
    assert int(ir_para(entrar_codigo(PAULA[0]), "dashboard").metric[0].value) == int(ativos_antes) - 1
    arquivo = ir_para(entrar_codigo(PAULA[0]), "revisao")
    assert any("Arquivo (1)" in t.label for t in arquivo.tabs)
    pagina = "\n".join(m.value for m in arquivo.markdown)
    assert "Enviado à Planejamento" in pagina and "Arquivado" in pagina and "Projeto encerrado pela unidade" in pagina

    # arquivado não recebe novas atualizações
    acomp = ir_para(entrar_codigo(ANA[0]), "acompanhamento")
    assert any("arquivado" in i.value.lower() for i in acomp.info)

    # reativar traz de volta
    arquivo = arquivo.button(key="reativar_projeto").click().run()
    assert projeto_novo()["SITUACAO_REGISTRO"] == "Ativo"
    assert internos()["Historico"].iloc[-1]["evento"] == "reativado"


def test_historico_de_exclusao_e_restauracao_entra_na_linha_do_tempo(equipe):
    enviar_projeto()
    n = str(int(float(projeto_novo()["Nº"])))
    at = ir_para(entrar_codigo(PAULA[0]), "painel")
    selecao = at.selectbox(key="sel_del_admin")
    selecao.set_value(n)  # o valor da lista é o ID do projeto (igual ao Nº nos projetos novos)
    at.text_input(key="mot_del_admin").set_value("Cadastro em duplicidade")
    at = botao(at, "Executar Exclusão").click().run()
    assert projeto_novo()["SITUACAO_REGISTRO"] == "Excluído"
    assert internos()["Historico"].iloc[-1]["evento"] == "excluido"
    selecao = at.selectbox(key="sel_rest_admin")
    selecao.set_value(n)  # o valor da lista é o ID do projeto (igual ao Nº nos projetos novos)
    at = at.button(key="restaurar_projeto").click().run()
    assert projeto_novo()["SITUACAO_REGISTRO"] == "Ativo" and internos()["Historico"].iloc[-1]["evento"] == "restaurado"


def test_projetos_antigos_recebem_codigo_e_continuam_com_edicao_livre(equipe):
    at = ir_para(entrar_codigo(PAULA[0]), "painel")
    assert not at.exception
    assert "CODIGO" not in projetos_na_planilha().columns  # só olhar as telas não altera o arquivo
    # a primeira gravação (aqui, o envio de um projeto) persiste os códigos de todos
    enviar_projeto()
    df = projetos_na_planilha()
    comcodigo = df[df["CODIGO"] != ""]
    assert len(comcodigo) >= 20 and comcodigo["CODIGO"].str.match(r"^\d{4}-\d{4}$").all()
    legados = df[df["ID_RASCUNHO"] == ""]
    assert (legados["EDICAO"] == "").all()  # projetos antigos não ficam travados


def test_nenhuma_pagina_da_etapa_2_tem_emoji_nem_a_palavra_auditoria(equipe):
    import re

    emoji = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿️⃣]")
    enviar_projeto()
    at = entrar_codigo(PAULA[0])
    for pagina in ("elaboracao", "acompanhamento", "revisao", "meus"):
        at = ir_para(at, pagina)
        assert not at.exception, pagina
        texto = textos_visiveis(at)
        assert not emoji.search(texto) and "audit" not in texto.lower(), pagina
