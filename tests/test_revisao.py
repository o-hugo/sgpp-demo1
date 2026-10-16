"""Circuito de revisão pela interface: ver o projeto inteiro, comentar, devolver para ajustes, reenviar e concluir."""
import pytest

import projetos
from apoio import entrar_codigo, semear_codigo
from test_app import ir_para
from test_etapa2 import ANA, CARLOS, LEITORA, PAULA, enviar_projeto, internos, projeto_novo
from test_etapa3 import STATUS_INDICE

DEVOLUCAO = "Ajuste o município para Parintins e inclua a data de término prevista."


@pytest.fixture
def equipe(pasta, monkeypatch):
    semear_codigo(monkeypatch, ANA, PAULA, CARLOS, LEITORA)


def numero_novo():
    return str(int(float(projeto_novo()["Nº"])))


def pagina(at):
    return "\n".join(str(m.value) for m in at.markdown)


def devolver(texto=DEVOLUCAO):
    n = numero_novo()
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at.text_area(key=f"rev_texto_fila_{n}").set_value(texto)
    return at.button(key=f"devolver_fila_{n}").click().run(), n


# ------------------------------------------------------------------ ver o projeto inteiro

def test_planejamento_ve_o_projeto_inteiro_na_revisao_e_na_fila(equipe):
    enviar_projeto(nome="Escola em Paz", ementa="Mediação de conflitos nas escolas.", unidade="NUPA")
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    assert not at.exception and any("Para revisar (1)" in t.label for t in at.tabs)
    html = pagina(at)
    for esperado in ("ficha-completa", "Escola em Paz", "Mediação de conflitos nas escolas.", "NUPA", "Ana Souza Lima",
                     "Controle (coordenação)", "Aguardando revisão", "Identificação", "Alinhamento", "Processo e prazos", "Descrição"):
        assert esperado in html, esperado


def test_ficha_completa_escapa_html_digitado_pelo_usuario(equipe):
    enviar_projeto(nome="Escola <b>em</b> Paz", ementa="<script>alert(1)</script>")
    html = pagina(ir_para(entrar_codigo(PAULA[0]), "revisao"))
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert "<b>em</b>" not in html and "&lt;b&gt;em&lt;/b&gt;" in html


def test_gestor_ve_os_dados_completos_no_acompanhamento_mas_nao_o_controle_interno(equipe):
    enviar_projeto(ementa="Mediação de conflitos nas escolas.")
    html = pagina(ir_para(entrar_codigo(ANA[0]), "acompanhamento"))
    assert "Mediação de conflitos nas escolas." in html and "Identificação" in html
    assert "Controle (coordenação)" not in html
    coordenacao = pagina(ir_para(entrar_codigo(PAULA[0]), "acompanhamento"))  # na visão da Planejamento
    assert "Controle (coordenação)" in coordenacao


# ------------------------------------------------------------------ devolver e comentar

def test_devolver_exige_explicacao_libera_a_edicao_e_registra_tudo(equipe):
    enviar_projeto()
    n = numero_novo()
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at = at.button(key=f"devolver_fila_{n}").click().run()  # sem texto
    assert any("mínimo de 10" in e.value for e in at.error) and projeto_novo()["REVISAO"] == "Aguardando revisão"

    at, n = devolver()
    assert any("devolvido ao gestor" in s.value for s in at.success)
    novo = projeto_novo()
    assert (novo["REVISAO"], novo["EDICAO"]) == ("Devolvido para ajustes", "Liberada")
    abas = internos()
    comentario = abas["Comentarios"].iloc[-1]
    assert (comentario["tipo"], comentario["texto"], comentario["autor_login"]) == ("devolucao", DEVOLUCAO, "paula.plan")
    assert abas["Historico"].iloc[-1]["evento"] == "devolvido"
    assert any("Para revisar (0)" in t.label for t in at.tabs)  # saiu da fila: agora está com o gestor


def test_gestor_ve_a_devolucao_em_meus_projetos_e_o_projeto_fica_editavel(equipe):
    enviar_projeto()
    devolver()
    at = ir_para(entrar_codigo(ANA[0]), "meus")
    assert not at.exception
    assert any("devolvido(s) para ajustes" in w.value for w in at.warning)
    html = pagina(at)
    assert "Retornos da Planejamento" in html and DEVOLUCAO in html and "Devolvido para ajustes" in html
    assert "Edição livre ou liberada" in html  # a tabela de edição está disponível


def test_gestor_responde_e_a_planejamento_le_a_resposta(equipe):
    enviar_projeto()
    devolver()
    n = numero_novo()
    at = ir_para(entrar_codigo(ANA[0]), "meus")
    at.text_area(key=f"resp_{n}").set_value("Entendido, faço os ajustes ainda hoje.")
    at = at.button(key=f"enviar_resp_{n}").click().run()
    assert any("Comentário enviado" in s.value for s in at.success)
    ultimo = internos()["Comentarios"].iloc[-1]
    assert (ultimo["tipo"], ultimo["autor_login"]) == ("comentario", "ana.souza")
    assert "Entendido, faço os ajustes ainda hoje." in pagina(ir_para(entrar_codigo(PAULA[0]), "revisao"))


def test_gestor_reenvia_ao_salvar_e_a_planejamento_conclui_a_revisao(equipe):
    enviar_projeto()
    devolver()
    n = numero_novo()
    # o gestor ajusta (aqui, pelo quadro, que também conta como edição) e o projeto volta para a fila, travado
    at = ir_para(entrar_codigo(ANA[0]), "quadro")
    at.button(key=f"mv_{n}_{STATUS_INDICE['Em execução']}").click().run()
    novo = projeto_novo()
    assert (novo["REVISAO"], novo["EDICAO"], novo["Status"]) == ("Ajustes reenviados", "Travada", "Em execução")
    assert [e for e in internos()["Historico"]["evento"]][-3:] == ["editado", "travado", "reenviado"]

    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    assert any("Para revisar (1)" in t.label for t in at.tabs) and "Ajustes reenviados" in pagina(at)
    at.text_area(key=f"rev_texto_fila_{n}").set_value("Ajustes conferidos, tudo certo.")
    at = at.button(key=f"concluir_fila_{n}").click().run()
    assert any("Revisão concluída" in s.value for s in at.success)
    assert projeto_novo()["REVISAO"] == "Revisão concluída"
    ultimo = internos()["Comentarios"].iloc[-1]
    assert (ultimo["tipo"], ultimo["texto"]) == ("conclusao", "Ajustes conferidos, tudo certo.")
    assert internos()["Historico"].iloc[-1]["evento"] == "revisao_concluida"
    assert any("Para revisar (0)" in t.label for t in at.tabs)


def test_concluir_sem_comentario_e_possivel_mas_nao_enquanto_o_projeto_esta_com_o_gestor(equipe):
    enviar_projeto()
    n = numero_novo()
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at = at.button(key=f"concluir_fila_{n}").click().run()
    assert projeto_novo()["REVISAO"] == "Revisão concluída"
    assert internos()["Comentarios"].iloc[-1]["tipo"] == "conclusao"
    assert "Sem observações adicionais" in pagina(ir_para(entrar_codigo(ANA[0]), "meus"))


def test_nao_conclui_projeto_que_esta_com_o_gestor_para_ajustes(equipe):
    enviar_projeto()
    at, n = devolver()
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at.selectbox(key="revisao_alvo").set_value(n)
    at = at.run()
    at = at.button(key=f"concluir_proj_{n}").click().run()
    assert any("com o gestor para ajustes" in e.value for e in at.error)
    assert projeto_novo()["REVISAO"] == "Devolvido para ajustes"


def test_planejamento_comenta_em_qualquer_projeto_sem_mudar_o_estado(equipe):
    enviar_projeto()
    n = numero_novo()
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at.selectbox(key="revisao_alvo").set_value(n)
    at = at.run()
    at.text_area(key=f"rev_texto_proj_{n}").set_value("Lembre de informar o número do processo SEI.")
    at = at.button(key=f"so_comentar_proj_{n}").click().run()
    assert any("Comentário enviado" in s.value for s in at.success)
    assert projeto_novo()["REVISAO"] == "Aguardando revisão"
    assert "Lembre de informar o número do processo SEI." in pagina(ir_para(entrar_codigo(ANA[0]), "meus"))


def test_comentario_curto_demais_e_recusado(equipe):
    enviar_projeto()
    n = numero_novo()
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    at.text_area(key=f"rev_texto_fila_{n}").set_value("ok")
    at = at.button(key=f"so_comentar_fila_{n}").click().run()
    assert any("mínimo de 5" in e.value for e in at.error) and internos()["Comentarios"].empty


# ------------------------------------------------------------------ comentários no acompanhamento

def test_gestor_e_planejamento_conversam_no_acompanhamento(equipe):
    enviar_projeto()
    n = numero_novo()
    at = ir_para(entrar_codigo(ANA[0]), "acompanhamento")
    at.text_area(key=f"com_acomp_{n}").set_value("Posso incluir o anexo com o cronograma?")
    at = at.button(key=f"comentar_acomp_{n}").click().run()
    assert any("Comentário enviado" in s.value for s in at.success)

    at = ir_para(entrar_codigo(PAULA[0]), "acompanhamento")
    at.radio(key="acomp_escopo").set_value("Todo o portfólio")
    at = at.run()
    at.selectbox(key="acomp_projeto").set_value(n)
    at = at.run()
    assert "Posso incluir o anexo com o cronograma?" in pagina(at)
    at.text_area(key=f"com_acomp_{n}").set_value("Pode, envie pelo SEI e cite o número aqui.")
    at.button(key=f"comentar_acomp_{n}").click().run()
    assert [c["autor_login"] for c in projetos.comentarios_do_projeto(internos(), n)] == ["ana.souza", "paula.plan"]


def test_leitor_nao_le_nem_escreve_comentarios(equipe):
    enviar_projeto()
    n = numero_novo()
    at = ir_para(entrar_codigo(LEITORA[0]), "acompanhamento")
    at.selectbox(key="acomp_projeto").set_value(n)
    at = at.run()
    assert not [t for t in at.text_area]
    assert any("Os comentários ficam visíveis" in c.value for c in at.caption)


# ------------------------------------------------------------------ pedidos de liberação com comentário

def test_liberar_com_comentario_mostra_a_orientacao_ao_gestor(equipe):
    enviar_projeto()
    n = numero_novo()
    at = ir_para(entrar_codigo(ANA[0]), "meus")
    at.text_area(key="motivo_pedido").set_value("Corrigir o município e a ementa do projeto")
    at.button(key="solicitar_liberacao").click().run()
    at = ir_para(entrar_codigo(PAULA[0]), "revisao")
    assert "Ver o projeto inteiro" in " ".join(str(e.label) for e in at.expander)
    at.text_input(key=f"cm_ped_{n}").set_value("Liberado até sexta-feira; depois o projeto trava de novo.")
    at = at.button(key=f"liberar_{n}").click().run()
    assert any("liberada" in s.value for s in at.success) and projeto_novo()["EDICAO"] == "Liberada"
    assert "Liberado até sexta-feira" in pagina(ir_para(entrar_codigo(ANA[0]), "meus"))
