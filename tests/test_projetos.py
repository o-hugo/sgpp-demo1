from datetime import date, timedelta

import pandas as pd
import pytest

import dados_internos
import projetos
from armazenamento import ArmazenamentoLocal


@pytest.fixture
def abas(tmp_path):
    abas, _ = dados_internos.ler_internos(ArmazenamentoLocal(str(tmp_path / "interno.xlsx")))
    return abas


def planilha(*linhas):
    """Planilha de projetos mínima, como a que o app lê: cada linha é (Nº, ano de criação, código)."""
    base = [{"Iniciativa": n, "Nº": n, "Nome da Iniciativa": f"Projeto {n}", "Ano de criação": ano, "CODIGO": codigo,
             "Gestor": "Ana Souza Lima", "Status": "Em execução", "SITUACAO_REGISTRO": "Ativo"} for n, ano, codigo in linhas]
    return projetos.garantir_colunas(pd.DataFrame(base))


def dados(**extra):
    base = {**projetos.dados_vazios(), "nome": "Escola em Paz", "area": "Infância e Juventude", "unidade": "NUPA",
            "ementa": "Mediação de conflitos nas escolas.", "ano": 2026}
    return {**base, **extra}


def rascunho_pronto(abas, login="ana.souza", nome="Ana Souza Lima", **extra):
    id_, erro = projetos.criar_rascunho(abas, login, nome, dados(**extra))
    assert erro is None, erro
    return projetos.buscar_rascunho(abas, id_, login)


# ------------------------------------------------------------------ código AAAA-NNNN

def test_codigos_sao_preenchidos_por_ano_em_ordem_de_numero_e_sao_estaveis():
    df = projetos.preencher_codigos(planilha((3, 2024, ""), (1, 2024, ""), (2, 2025, ""), (4, 2024, "2024-0007")))
    assert dict(zip(df["Nº"], df["CODIGO"])) == {1: "2024-0008", 2: "2025-0001", 3: "2024-0009", 4: "2024-0007"}
    assert projetos.preencher_codigos(df)["CODIGO"].tolist() == df["CODIGO"].tolist()  # estável


def test_projeto_sem_ano_valido_fica_sem_codigo():
    df = projetos.preencher_codigos(planilha((1, None, ""), (2, 1850, ""), (3, 2024, "")))
    assert df["CODIGO"].tolist() == ["", "", "2024-0001"]


def test_proximo_codigo_continua_depois_do_maior_do_ano():
    df = planilha((1, 2026, "2026-0004"), (2, 2025, "2025-0009"))
    assert projetos.proximo_codigo(df, 2026) == "2026-0005"
    assert projetos.proximo_codigo(df, 2030) == "2030-0001"


# ------------------------------------------------------------------ identificador do projeto (Nº repetido na planilha real)

def test_id_e_o_proprio_numero_quando_ele_e_unico_e_nao_muda_depois():
    df = projetos.atribuir_ids(planilha((1, 2026, ""), (2, 2026, ""), (3, 2026, "")))
    assert df["ID_PROJETO"].tolist() == ["1", "2", "3"]
    outra = projetos.atribuir_ids(df.assign(**{"Nº": [9, 8, 7]}))  # IDs já gravados nunca mudam, mesmo se o Nº mudar
    assert outra["ID_PROJETO"].tolist() == ["1", "2", "3"]


def test_numero_repetido_ou_ausente_ganha_sufixo_pela_ordem_das_linhas():
    df = projetos.atribuir_ids(planilha((7, 2026, ""), (28, 2026, ""), (28, 2025, ""), (9, 2026, ""), (28, 2024, "")))
    assert df["ID_PROJETO"].tolist() == ["7", "28-1", "28-2", "9", "28-3"]
    sem_numero = planilha((1, 2026, ""), (2, 2026, ""))
    sem_numero["Nº"] = [None, None]
    assert projetos.atribuir_ids(sem_numero)["ID_PROJETO"].tolist() == ["sem-n-1", "sem-n-2"]


def test_projeto_novo_entra_sem_colidir_com_ids_existentes():
    df = projetos.atribuir_ids(planilha((1, 2026, ""), (5, 2026, ""), (5, 2025, "")))
    assert df["ID_PROJETO"].tolist() == ["1", "5-1", "5-2"]
    assert projetos.atribuir_ids(df)["ID_PROJETO"].tolist() == ["1", "5-1", "5-2"]  # idempotente
    novo = df.copy()
    novo.loc[len(novo)] = {c: "" for c in novo.columns}
    novo.at[len(novo) - 1, "Nº"] = 6
    assert projetos.atribuir_ids(novo)["ID_PROJETO"].iloc[-1] == "6"


def test_acoes_atingem_so_o_projeto_escolhido_quando_o_numero_se_repete():
    df = projetos.atribuir_ids(planilha((28, 2026, ""), (28, 2025, "")))
    df["Gestor"] = ["Ana Souza Lima", "Beto Souza Lima"]
    novo, anterior, _, _, erro = projetos.mover_status(df, "28-2", "Concluído", "planejamento", "Paula")
    assert erro is None and anterior == "Em execução"
    assert novo["Status"].tolist() == ["Em execução", "Concluído"]
    # trava, liberação e arquivamento seguem a mesma regra
    travado, _ = projetos.travar_projeto(df, "28-1")
    assert travado["EDICAO"].tolist() == ["Travada", ""]
    arquivado, _ = projetos.arquivar_projeto(df, "28-2", "Encerrado pela unidade")
    assert arquivado["SITUACAO_REGISTRO"].tolist() == ["Ativo", "Arquivado"]
    # o Nº sozinho, que é ambíguo, ainda serve de reserva para planilhas sem ID
    assert projetos._indice(planilha((1, 2026, "")), 1) == 0


def test_pendencia_de_numero_repetido_aparece_nos_dois_projetos():
    df = projetos.atribuir_ids(planilha((28, 2026, "2026-0001"), (28, 2025, "2025-0001"), (30, 2026, "2026-0002")))
    detalhe = projetos.pendencias_detalhadas(df, HOJE)
    repetidos = detalhe[detalhe["categoria"] == "Nº repetido na planilha"]
    assert repetidos["n"].tolist() == ["28-1", "28-2"] and set(repetidos["gravidade"]) == {"Atenção"}
    resumo = projetos.resumo_pendencias(df, HOJE)
    assert resumo[resumo["categoria"] == "Nº repetido na planilha"]["projetos"].tolist() == [2]
    assert "28-1" in projetos.relatorio_pendencias(df, HOJE)["n"].tolist()


# ------------------------------------------------------------------ rascunhos

def test_rascunho_pode_ser_salvo_incompleto_mas_precisa_de_nome(abas):
    assert projetos.criar_rascunho(abas, "ana", "Ana S", {**projetos.dados_vazios(), "nome": "ab"})[1]
    id_, erro = projetos.criar_rascunho(abas, "ana", "Ana Souza", {**projetos.dados_vazios(), "nome": "Meu projeto"})
    assert erro is None and id_
    assert projetos.buscar_rascunho(abas, id_, "ana")["situacao"] == "aberto"


def test_so_o_autor_enxerga_e_altera_o_rascunho(abas):
    r = rascunho_pronto(abas)
    assert projetos.buscar_rascunho(abas, r["id"], "outra.pessoa") is None
    assert projetos.atualizar_rascunho(abas, r["id"], "outra.pessoa", dados())
    assert projetos.descartar_rascunho(abas, r["id"], "outra.pessoa")
    assert projetos.rascunhos_abertos(abas, "outra.pessoa").empty
    assert len(projetos.rascunhos_abertos(abas, "ana.souza")) == 1


def test_atualizar_e_descartar_rascunho(abas):
    r = rascunho_pronto(abas)
    assert projetos.atualizar_rascunho(abas, r["id"], "ana.souza", dados(nome="Escola em Paz 2")) is None
    assert projetos.buscar_rascunho(abas, r["id"], "ana.souza")["nome"] == "Escola em Paz 2"
    assert projetos.descartar_rascunho(abas, r["id"], "ana.souza") is None
    assert projetos.rascunhos_abertos(abas, "ana.souza").empty
    assert projetos.atualizar_rascunho(abas, r["id"], "ana.souza", dados())  # descartado não volta


def test_datas_previstas_precisam_ser_validas_e_em_ordem():
    assert projetos.validar_dados(dados(inicio_previsto="2026-03-01", termino_previsto="2026-02-01"), False)
    assert projetos.validar_dados(dados(inicio_previsto="01/03/2026"), False)
    assert projetos.validar_dados(dados(inicio_previsto="2026-03-01", termino_previsto="2026-12-31"), False) is None


def test_envio_exige_campos_obrigatorios(abas):
    r = rascunho_pronto(abas, ementa="", unidade="")
    df, n, codigo, erro = projetos.enviar_rascunho(planilha((1, 2026, "2026-0001")), r)
    assert erro and "Unidade" in erro and "Ementa" in erro
    assert n is None and len(df) == 1


# ------------------------------------------------------------------ envio

def test_envio_cria_projeto_travado_com_codigo_gestor_e_datas(abas):
    r = rascunho_pronto(abas, inicio_previsto="2026-02-01", termino_previsto="2026-12-31", institucionalizado="Sim")
    df, n, codigo, erro = projetos.enviar_rascunho(planilha((7, 2026, "2026-0003")), r, quando="10/01/2026 09:00")
    assert erro is None and n == 8 and codigo == "2026-0004"
    novo = df[df["Nº"] == 8].iloc[0]
    assert novo["Gestor"] == "Ana Souza Lima" and novo["EDICAO"] == "Travada" and novo["SITUACAO_REGISTRO"] == "Ativo"
    assert novo["ENVIADO_POR"] == "ana.souza" and novo["ENVIADO_EM"] == "10/01/2026 09:00"
    assert novo["INICIO_PREVISTO"] == "2026-02-01" and novo["TERMINO_PREVISTO"] == "2026-12-31"
    assert novo["ID_RASCUNHO"] == r["id"] and novo["Ato PGJ"] == "Institucionalizado"
    assert projetos.esta_travado(df, 8)


def test_envio_repetido_nao_duplica_o_projeto(abas):
    r = rascunho_pronto(abas)
    df, n1, c1, _ = projetos.enviar_rascunho(planilha((1, 2026, "2026-0001")), r)
    df2, n2, c2, erro = projetos.enviar_rascunho(df, r)
    assert erro is None and (n1, c1) == (n2, c2) and len(df2) == len(df) == 2


def test_rascunho_ja_presente_na_planilha_some_da_lista_de_abertos(abas):
    r = rascunho_pronto(abas)
    df, *_ = projetos.enviar_rascunho(planilha((1, 2026, "2026-0001")), r)
    assert len(projetos.rascunhos_abertos(abas, "ana.souza")) == 1
    assert projetos.rascunhos_abertos(abas, "ana.souza", df).empty
    projetos.marcar_rascunho_enviado(abas, r["id"], 2)
    assert projetos.rascunhos_abertos(abas, "ana.souza").empty
    assert projetos.buscar_rascunho(abas, r["id"], "ana.souza")["situacao"] == "enviado"


# ------------------------------------------------------------------ trava e liberação

def projeto_travado(abas):
    df, n, _, _ = projetos.enviar_rascunho(planilha((1, 2026, "2026-0001")), rascunho_pronto(abas))
    return df, n


def test_pedido_de_liberacao_exige_projeto_travado_motivo_e_so_um_pendente(abas):
    df, n = projeto_travado(abas)
    assert projetos.solicitar_liberacao(df, n, "ana.souza", "curto")[1]
    df, erro = projetos.solicitar_liberacao(df, n, "ana.souza", "Corrigir o município e a ementa", quando="11/01/2026 10:00")
    assert erro is None
    pedido = projetos.parse_pedido(df[df["Nº"] == n].iloc[0]["PEDIDO_LIBERACAO"])
    assert pedido == {"quando": "11/01/2026 10:00", "login": "ana.souza", "motivo": "Corrigir o município e a ementa"}
    assert projetos.solicitar_liberacao(df, n, "ana.souza", "Outro pedido qualquer aqui")[1]
    assert len(projetos.pedidos_pendentes(df)) == 1
    # projeto livre não precisa de pedido
    livre = planilha((1, 2026, "2026-0001"))
    assert projetos.solicitar_liberacao(livre, 1, "ana.souza", "Quero editar este projeto")[1]


def test_motivo_com_separador_nao_quebra_a_leitura_do_pedido(abas):
    df, n = projeto_travado(abas)
    df, _ = projetos.solicitar_liberacao(df, n, "ana.souza", "Trocar A | B por outro valor aqui")
    assert projetos.parse_pedido(df[df["Nº"] == n].iloc[0]["PEDIDO_LIBERACAO"])["motivo"] == "Trocar A - B por outro valor aqui"


def test_liberar_encerra_o_pedido_e_depois_de_salvar_volta_a_travar(abas):
    df, n = projeto_travado(abas)
    df, _ = projetos.solicitar_liberacao(df, n, "ana.souza", "Corrigir o município da iniciativa")
    df, erro = projetos.liberar_edicao(df, n)
    assert erro is None and projetos.edicao_do_projeto(df, n) == "Liberada" and projetos.pedidos_pendentes(df).empty
    assert projetos.liberar_edicao(df, n)[1]  # já liberada
    df, travados = projetos.retravar_apos_edicao(df, [n])
    assert travados == [n] and projetos.esta_travado(df, n)


def test_retravar_so_afeta_projetos_liberados():
    livre = planilha((1, 2026, "2026-0001"))
    df, travados = projetos.retravar_apos_edicao(livre, [1])
    assert travados == [] and projetos.edicao_do_projeto(df, 1) == ""


def test_negar_liberacao_limpa_o_pedido_e_mantem_a_trava(abas):
    df, n = projeto_travado(abas)
    assert projetos.negar_liberacao(df, n)[1]  # sem pedido
    df, _ = projetos.solicitar_liberacao(df, n, "ana.souza", "Corrigir o município da iniciativa")
    df, erro = projetos.negar_liberacao(df, n)
    assert erro is None and projetos.esta_travado(df, n) and projetos.pedidos_pendentes(df).empty


def test_travar_manualmente_um_projeto_livre():
    df, erro = projetos.travar_projeto(planilha((1, 2026, "2026-0001")), 1)
    assert erro is None and projetos.esta_travado(df, 1)
    assert projetos.travar_projeto(df, 1)[1]


def test_campos_alterados_compara_so_o_que_o_gestor_pode_editar():
    antes = {"Status": "Em execução", "Unidade": "NUPA", "Gestor": "Ana"}
    depois = {"Status": "Concluído", "Unidade": "NUPA", "Gestor": "Outra"}
    assert projetos.campos_alterados(antes, depois) == ["Status"]
    assert projetos.validar_datas_previstas("2026-05-01", "2026-04-01")
    assert projetos.validar_datas_previstas("", "") is None


def editar(df, n, **mudancas):
    """Simula o editor: devolve (origem, editado) para o projeto n com as mudanças aplicadas."""
    origem = df[df["Nº"] == n].copy()
    editado = origem.copy()
    for coluna, valor in mudancas.items():
        editado[coluna] = valor
    return origem, editado


def test_aplicar_edicoes_registra_campos_e_so_trava_o_que_estava_liberado(abas):
    df, n = projeto_travado(abas)
    df, _ = projetos.liberar_edicao(df, n)
    origem, editado = editar(df, n, Status="Concluído", Unidade="NUPA - Capital")
    novo, alterados, travados, reenviados, erro = projetos.aplicar_edicoes(df, origem, editado)
    assert erro is None
    assert alterados == {str(n): ["Unidade", "Status"]}  # na ordem das colunas editáveis
    assert travados == [str(n)]
    linha = novo[novo["Nº"] == n].iloc[0]
    assert linha["Status"] == "Concluído" and linha["EDICAO"] == "Travada"


def test_aplicar_edicoes_em_projeto_livre_nao_trava_e_sem_mudanca_nao_faz_nada():
    df = planilha((1, 2026, "2026-0001"))
    origem, editado = editar(df, 1, Status="Paralisado")
    novo, alterados, travados, reenviados, erro = projetos.aplicar_edicoes(df, origem, editado)
    assert erro is None and list(alterados) == ["1"] and travados == []
    assert novo.iloc[0]["Status"] == "Paralisado" and novo.iloc[0]["EDICAO"] == ""
    origem, editado = editar(df, 1)
    novo, alterados, travados, reenviados, erro = projetos.aplicar_edicoes(df, origem, editado)
    assert (alterados, travados, erro) == ({}, [], None) and novo is df


def test_aplicar_edicoes_recusa_datas_invalidas_sem_alterar_a_planilha():
    df = planilha((1, 2026, "2026-0001"))
    origem, editado = editar(df, 1, INICIO_PREVISTO="2026-06-01", TERMINO_PREVISTO="2026-01-01")
    novo, alterados, travados, reenviados, erro = projetos.aplicar_edicoes(df, origem, editado)
    assert erro == "Projeto Nº 1: O término previsto não pode ser anterior ao início previsto."
    assert alterados == {} and novo is df
    origem, editado = editar(df, 1, INICIO_PREVISTO="amanhã")
    assert projetos.aplicar_edicoes(df, origem, editado)[4]


# ------------------------------------------------------------------ revisão e comentários

def projeto_em_revisao(abas):
    df, n = projeto_travado(abas)
    return df, n


def test_projeto_enviado_entra_na_fila_de_revisao(abas):
    df, n = projeto_em_revisao(abas)
    assert df[df["Nº"] == n].iloc[0]["REVISAO"] == "Aguardando revisão"
    assert projetos.para_revisar(df)["Nº"].tolist() == [n]
    legado = planilha((1, 2026, "2026-0001"))
    assert projetos.para_revisar(legado).empty  # projeto antigo não entra na fila sozinho


def test_devolver_libera_a_edicao_e_tira_da_fila(abas):
    df, n = projeto_em_revisao(abas)
    df, _ = projetos.solicitar_liberacao(df, n, "ana.souza", "Corrigir o município da iniciativa")
    df, erro = projetos.devolver_para_ajustes(df, n)
    assert erro is None
    linha = df[df["Nº"] == n].iloc[0]
    assert (linha["REVISAO"], linha["EDICAO"], linha["PEDIDO_LIBERACAO"]) == ("Devolvido para ajustes", "Liberada", "")
    assert projetos.para_revisar(df).empty
    assert projetos.devolver_para_ajustes(df, n)[1] == "O projeto já está com o gestor para ajustes."


def test_gestor_salva_ajustes_e_o_projeto_volta_para_a_fila_travado(abas):
    df, n = projeto_em_revisao(abas)
    df, _ = projetos.devolver_para_ajustes(df, n)
    origem, editado = editar(df, n, Município="Parintins")
    novo, alterados, travados, reenviados, erro = projetos.aplicar_edicoes(df, origem, editado)
    assert erro is None and travados == [str(n)] and reenviados == [str(n)]
    linha = novo[novo["Nº"] == n].iloc[0]
    assert (linha["REVISAO"], linha["EDICAO"]) == ("Ajustes reenviados", "Travada")
    assert projetos.para_revisar(novo)["Nº"].tolist() == [n]


def test_mover_cartao_de_projeto_devolvido_tambem_conta_como_reenvio(abas):
    df, n = projeto_em_revisao(abas)
    df, _ = projetos.devolver_para_ajustes(df, n)
    nome = df[df["Nº"] == n].iloc[0]["Gestor"]
    novo, _, voltou, reenviado, erro = projetos.mover_status(df, n, "Concluído", "gestor_projeto", nome)
    assert erro is None and voltou and reenviado and novo[novo["Nº"] == n].iloc[0]["REVISAO"] == "Ajustes reenviados"
    # a Planejamento mover o cartão não reenvia nada
    novo, _, _, reenviado, _ = projetos.mover_status(df, n, "Concluído", "planejamento", "Paula")
    assert not reenviado and novo[novo["Nº"] == n].iloc[0]["REVISAO"] == "Devolvido para ajustes"


def test_concluir_revisao_so_depois_que_o_gestor_reenviar(abas):
    df, n = projeto_em_revisao(abas)
    devolvido, _ = projetos.devolver_para_ajustes(df, n)
    assert projetos.concluir_revisao(devolvido, n)[1] == "O projeto está com o gestor para ajustes. Aguarde o reenvio."
    df2, erro = projetos.concluir_revisao(df, n)  # a partir de "Aguardando revisão"
    assert erro is None and df2[df2["Nº"] == n].iloc[0]["REVISAO"] == "Revisão concluída"
    assert projetos.concluir_revisao(df2, n)[1] == "A revisão deste projeto já está concluída."
    assert projetos.para_revisar(df2).empty


def test_editar_projeto_com_revisao_concluida_manda_de_volta_para_a_fila(abas):
    df, n = projeto_em_revisao(abas)
    df, _ = projetos.concluir_revisao(df, n)
    df, _ = projetos.liberar_edicao(df, n)
    origem, editado = editar(df, n, Status="Concluído")
    novo, _, _, reenviados, _ = projetos.aplicar_edicoes(df, origem, editado)
    assert reenviados == [str(n)] and novo[novo["Nº"] == n].iloc[0]["REVISAO"] == "Ajustes reenviados"


def test_comentarios_validam_tamanho_e_formam_um_fio_cronologico(abas):
    assert projetos.registrar_comentario(abas, 1, "comentario", "ok", "p", "Paula")
    assert projetos.registrar_comentario(abas, 1, "devolucao", "curto", "p", "Paula")
    assert projetos.registrar_comentario(abas, 1, "outro", "Texto longo o bastante", "p", "Paula")
    assert projetos.registrar_comentario(abas, 1, "devolucao", "Ajustar o município e a ementa", "p", "Paula", "01/02/2026 09:00") is None
    assert projetos.registrar_comentario(abas, 1, "comentario", "Ajustado, pode revisar de novo.", "a", "Ana", "02/02/2026 10:00") is None
    assert projetos.registrar_comentario(abas, "1.0", "conclusao", "", "p", "Paula", "03/02/2026 08:00") is None  # conclusão pode ir sem texto
    assert projetos.registrar_comentario(abas, 2, "comentario", "Comentário de outro projeto", "p", "Paula") is None
    fio = projetos.comentarios_do_projeto(abas, 1)
    assert [c["tipo"] for c in fio] == ["devolucao", "comentario", "conclusao"]
    assert [c["autor_nome"] for c in fio] == ["Paula", "Ana", "Paula"]
    assert fio[0]["rotulo"] == "Devolvido para ajustes" and fio[0]["quando"] == "01/02/2026 09:00"


@pytest.mark.parametrize("nivel,nome,gestor,pode", [
    ("planejamento", "Paula", "Ana Souza Lima", True), ("administrador", "Admin", "Ana Souza Lima", True),
    ("gestor_projeto", "Ana Souza Lima", "ana souza lima", True), ("gestor_projeto", "Outra Pessoa", "Ana Souza Lima", False),
    ("comite", "Carlos", "Ana Souza Lima", False), ("leitor", "Ana Souza Lima", "Ana Souza Lima", False),
    ("gestor_projeto", "", "", False),
])
def test_quem_comenta_e_le_o_fio_de_comentarios(nivel, nome, gestor, pode):
    assert projetos.pode_comentar(nivel, nome, gestor) is pode


# ------------------------------------------------------------------ arquivamento

def test_arquivar_e_reativar_exigem_o_estado_certo_e_motivo():
    df = planilha((1, 2026, "2026-0001"))
    assert projetos.arquivar_projeto(df, 1, "x")[1]
    df, erro = projetos.arquivar_projeto(df, 1, "Projeto encerrado pela unidade")
    assert erro is None and df.iloc[0]["SITUACAO_REGISTRO"] == "Arquivado"
    assert projetos.arquivar_projeto(df, 1, "Projeto encerrado pela unidade")[1]
    df, erro = projetos.reativar_projeto(df, 1)
    assert erro is None and df.iloc[0]["SITUACAO_REGISTRO"] == "Ativo"
    assert projetos.reativar_projeto(df, 1)[1]


# ------------------------------------------------------------------ quadro (kanban)

@pytest.mark.parametrize("status,coluna", [
    ("Em elaboração", "Em elaboração"), ("Em execução", "Em execução"), ("Concluído", "Concluído"), ("Paralisado", "Paralisado"),
    ("Há intenção formalizada", "Outros status"), ("Encerrado", "Outros status"), ("", "Outros status"), (None, "Outros status"),
    (float("nan"), "Outros status"),
])
def test_coluna_do_quadro(status, coluna):
    assert projetos.coluna_do_quadro(status) == coluna


def projeto_do_quadro(edicao="", gestor="Ana Souza Lima", status="Em execução"):
    df = planilha((1, 2026, "2026-0001"))
    df["EDICAO"], df["Gestor"], df["Status"] = edicao, gestor, status
    return df


@pytest.mark.parametrize("nivel,nome,edicao,pode", [
    ("planejamento", "Paula", "Travada", True),          # a Planejamento move mesmo travado
    ("administrador", "Admin", "Travada", True),
    ("gestor_projeto", "Ana Souza Lima", "", True),      # o gestor move projeto livre
    ("gestor_projeto", "ana souza lima", "Liberada", True),
    ("gestor_projeto", "Ana Souza Lima", "Travada", False),
    ("gestor_unidade", "Outra Pessoa Silva", "", False),  # de outro gestor
    ("comite", "Ana Souza Lima", "", False),
    ("leitor", "Ana Souza Lima", "", False),
])
def test_quem_pode_mover_o_cartao(nivel, nome, edicao, pode):
    df = projeto_do_quadro(edicao)
    assert projetos.pode_mover_status(df.iloc[0], nivel, nome)[0] is pode
    _, _, _, _, erro = projetos.mover_status(df, 1, "Concluído", nivel, nome)
    assert (erro is None) is pode


def test_mover_altera_o_status_e_devolve_o_anterior():
    df, anterior, voltou, _, erro = projetos.mover_status(projeto_do_quadro(), 1, "Concluído", "gestor_projeto", "Ana Souza Lima")
    assert (anterior, voltou, erro) == ("Em execução", False, None) and df.iloc[0]["Status"] == "Concluído"
    # projeto de vocabulário antigo também pode entrar numa das quatro colunas
    df, anterior, _, _, erro = projetos.mover_status(projeto_do_quadro(status="Há intenção formalizada"), 1, "Em elaboração", "planejamento", "P")
    assert erro is None and anterior == "Há intenção formalizada" and df.iloc[0]["Status"] == "Em elaboração"


def test_mover_recusa_destino_invalido_mesmo_status_e_projeto_inativo():
    df = projeto_do_quadro()
    assert projetos.mover_status(df, 1, "Outros status", "planejamento", "P")[4]
    assert projetos.mover_status(df, 1, "Em execução", "planejamento", "P")[4] == "O projeto já está nesse status."
    assert projetos.mover_status(df, 99, "Concluído", "planejamento", "P")[4] == "Projeto não encontrado."
    arquivado = df.assign(SITUACAO_REGISTRO="Arquivado")
    assert projetos.mover_status(arquivado, 1, "Concluído", "planejamento", "P")[4]


def test_gestor_com_edicao_liberada_volta_a_travar_ao_mover_mas_a_planejamento_nao_mexe_na_trava():
    df = projeto_do_quadro("Liberada")
    novo, _, voltou, _, _ = projetos.mover_status(df, 1, "Concluído", "gestor_projeto", "Ana Souza Lima")
    assert voltou and novo.iloc[0]["EDICAO"] == "Travada"
    novo, _, voltou, _, _ = projetos.mover_status(df, 1, "Concluído", "planejamento", "Paula")
    assert not voltou and novo.iloc[0]["EDICAO"] == "Liberada"
    novo, _, voltou, _, _ = projetos.mover_status(projeto_do_quadro(""), 1, "Concluído", "gestor_projeto", "Ana Souza Lima")
    assert not voltou and novo.iloc[0]["EDICAO"] == ""  # projeto livre continua livre


# ------------------------------------------------------------------ pendências

HOJE = date(2026, 6, 15)


def projeto_completo(**mudancas):
    base = {"Nome da Iniciativa": "Escola em Paz", "Projeto/Programa/Boa Prática": "Projeto", "Área de Atuação": "Educação",
            "Unidade": "NUPA", "Município": "Manaus", "Gestor": "Ana Souza Lima", "Ementa (Objetivo)": "Mediação.",
            "Status": "Em execução", "CODIGO": "2026-0001", "SEI": "123", "Institucionalizado": "Sim",
            "INICIO_PREVISTO": "", "TERMINO_PREVISTO": ""}
    return {**base, **mudancas}


def test_projeto_completo_nao_tem_pendencia():
    assert projetos.pendencias_do_projeto(projeto_completo(), HOJE) == []


@pytest.mark.parametrize("campo,rotulo", [
    ("Nome da Iniciativa", "Nome"), ("Projeto/Programa/Boa Prática", "Tipo"), ("Área de Atuação", "Área de atuação"),
    ("Unidade", "Unidade"), ("Município", "Município"), ("Gestor", "Gestor"), ("Ementa (Objetivo)", "Ementa"), ("Status", "Status"),
])
def test_cada_campo_obrigatorio_em_branco_vira_pendencia_obrigatoria(campo, rotulo):
    for vazio in ("", None, float("nan"), "   "):
        achadas = projetos.pendencias_do_projeto(projeto_completo(**{campo: vazio}), HOJE)
        assert ("Obrigatório", f"{rotulo} em branco", f"{rotulo} em branco") in achadas, (campo, vazio)


def test_recomendadas_atencao_e_status_fora_do_padrao():
    achadas = projetos.pendencias_do_projeto(projeto_completo(CODIGO="", SEI="", Institucionalizado="", Status="Encerrado"), HOJE)
    assert {(g, c) for g, c, _ in achadas} == {
        ("Recomendado", "Sem ano de criação (sem código)"), ("Recomendado", "Sem nº SEI"),
        ("Recomendado", "Institucionalizado em branco"), ("Atenção", "Status fora do padrão"),
    }
    assert "Status fora do padrão: Encerrado" in [d for _, _, d in achadas]


def test_prazo_vencido_so_vale_para_projeto_em_andamento_e_datas_incoerentes_sao_atencao():
    vencido = projetos.pendencias_do_projeto(projeto_completo(TERMINO_PREVISTO="2026-05-31"), HOJE)
    assert [(g, c) for g, c, _ in vencido] == [("Atenção", "Prazo vencido")]
    assert "31/05/2026" in vencido[0][2]
    assert projetos.pendencias_do_projeto(projeto_completo(TERMINO_PREVISTO="2026-05-31", Status="Concluído"), HOJE) == []
    assert projetos.pendencias_do_projeto(projeto_completo(TERMINO_PREVISTO="2026-12-31"), HOJE) == []
    incoerente = projetos.pendencias_do_projeto(projeto_completo(INICIO_PREVISTO="2026-09-01", TERMINO_PREVISTO="2026-03-01"), HOJE)
    assert [(g, c) for g, c, _ in incoerente] == [("Atenção", "Datas previstas incoerentes")]


def test_relatorio_lista_so_ativos_com_pendencia_do_mais_grave_ao_menos_grave():
    df = planilha((1, 2026, "2026-0001"), (2, 2026, "2026-0002"), (3, 2026, "2026-0003"), (4, 2026, "2026-0004"), (5, 2026, "2026-0005"))
    for coluna, valor in {"Projeto/Programa/Boa Prática": "Projeto", "Área de Atuação": "Educação", "Unidade": "NUPA", "Município": "Manaus",
                          "Ementa (Objetivo)": "Mediação.", "SEI": "1", "Institucionalizado": "Sim"}.items():
        df[coluna] = valor
    df.loc[df["Nº"] == 1, "Gestor"] = ""                       # obrigatório
    df.loc[df["Nº"] == 2, "SEI"] = ""                           # só recomendada
    df.loc[df["Nº"] == 3, "Status"] = "Encerrado"               # atenção
    df.loc[df["Nº"] == 4, ["Gestor", "Unidade"]] = ""           # dois obrigatórios (mais grave que o 1)
    df.loc[df["Nº"] == 5, ["Gestor", "SITUACAO_REGISTRO"]] = ["", "Arquivado"]  # arquivado não entra
    r = projetos.relatorio_pendencias(df, HOJE)
    assert r["n"].tolist() == ["4", "1", "3", "2"]
    assert r["gravidade"].tolist() == ["Obrigatório", "Obrigatório", "Atenção", "Recomendado"]
    assert r.iloc[0]["qtd"] == 2 and r.iloc[0]["pendencias"] == ["Unidade em branco", "Gestor em branco"]

    resumo = projetos.resumo_pendencias(df, HOJE)
    contagem = {(l.gravidade, l.categoria): l.projetos for l in resumo.itertuples()}
    assert contagem[("Obrigatório", "Gestor em branco")] == 2 and contagem[("Obrigatório", "Unidade em branco")] == 1
    assert resumo.iloc[0]["gravidade"] == "Obrigatório"


def test_pendencias_detalhadas_tem_uma_linha_por_problema():
    df = planilha((1, 2026, "2026-0001"), (2, 2026, "2026-0002"))
    for coluna, valor in {"Projeto/Programa/Boa Prática": "Projeto", "Área de Atuação": "Educação", "Unidade": "NUPA", "Município": "Manaus",
                          "Ementa (Objetivo)": "Mediação.", "SEI": "1", "Institucionalizado": "Sim"}.items():
        df[coluna] = valor
    df.loc[df["Nº"] == 2, ["Gestor", "SEI"]] = ["", ""]
    detalhe = projetos.pendencias_detalhadas(df, HOJE)
    assert detalhe["n"].tolist() == ["2", "2"] and set(detalhe["categoria"]) == {"Gestor em branco", "Sem nº SEI"}
    assert set(detalhe["gravidade"]) == {"Obrigatório", "Recomendado"} and set(detalhe["projeto"]) == {"Projeto 2"}
    assert list(detalhe.columns) == ["n", "codigo", "projeto", "gestor", "unidade", "gravidade", "categoria", "detalhe"]


def test_quem_ve_as_pendencias():
    assert [n for n in ("administrador", "planejamento", "comite", "gestor_unidade", "gestor_projeto", "leitor")
            if projetos.pode("ver_pendencias", n)] == ["administrador", "planejamento", "comite"]


def test_planilha_sem_pendencias_gera_relatorio_vazio():
    df = planilha((1, 2026, "2026-0001"))
    for coluna, valor in {"Projeto/Programa/Boa Prática": "Projeto", "Área de Atuação": "Educação", "Unidade": "NUPA", "Município": "Manaus",
                          "Ementa (Objetivo)": "Mediação.", "SEI": "1", "Institucionalizado": "Sim"}.items():
        df[coluna] = valor
    assert projetos.relatorio_pendencias(df, HOJE).empty and projetos.resumo_pendencias(df, HOJE).empty


# ------------------------------------------------------------------ atualizações e pareceres

def test_atualizacao_valida_data_situacao_e_texto(abas):
    ontem = (date.today() - timedelta(days=1)).isoformat()
    futuro = (date.today() + timedelta(days=2)).isoformat()
    assert projetos.registrar_atualizacao(abas, 1, futuro, "Em dia", "Reunião realizada com a rede", "a", "Ana")
    assert projetos.registrar_atualizacao(abas, 1, ontem, "Quase", "Reunião realizada com a rede", "a", "Ana")
    assert projetos.registrar_atualizacao(abas, 1, ontem, "Em dia", "curto", "a", "Ana")
    assert projetos.registrar_atualizacao(abas, 1, "", "Em dia", "Reunião realizada com a rede", "a", "Ana")
    assert projetos.registrar_atualizacao(abas, 1, ontem, "Em dia", "Reunião realizada com a rede", "a", "Ana") is None
    linhas = projetos.do_projeto(abas, "Atualizacoes", 1)
    assert len(linhas) == 1 and linhas.iloc[0]["situacao"] == "Em dia"
    assert projetos.do_projeto(abas, "Atualizacoes", 2).empty


def test_parecer_exige_texto_e_aceita_conclusao_opcional(abas):
    assert projetos.registrar_parecer(abas, 1, "Talvez", "Parecer longo o bastante aqui", "p", "Paula")
    assert projetos.registrar_parecer(abas, 1, "Favorável", "curto", "p", "Paula")
    assert projetos.registrar_parecer(abas, 1, "", "Parecer longo o bastante aqui", "p", "Paula") is None
    assert projetos.registrar_parecer(abas, 1, "Favorável com ressalvas", "Ajustar o cronograma da iniciativa", "p", "Paula") is None
    assert len(projetos.do_projeto(abas, "Pareceres", 1)) == 2


# ------------------------------------------------------------------ linha do tempo

def test_linha_do_tempo_e_cronologica_e_resume_o_arquivamento(abas):
    projetos.acrescentar_eventos(abas, [
        projetos.evento(5, "paula", "Paula", "arquivado", "Encerrado pela unidade", "20/03/2026 15:00"),
        projetos.evento(5, "ana", "Ana", "enviado", "Código 2026-0001", "10/01/2026 09:00"),
        projetos.evento(5, "ana", "Ana", "liberacao_solicitada", "Corrigir ementa", "01/02/2026 08:30"),
        projetos.evento(6, "ana", "Ana", "enviado", "Código 2026-0002", "15/01/2026 09:00"),
    ])
    itens = projetos.linha_do_tempo(abas, 5)
    assert [i["evento"] for i in itens] == ["enviado", "liberacao_solicitada", "arquivado"]
    assert itens[0]["rotulo"] == "Enviado à Planejamento"
    resumo = projetos.resumo_arquivamento(abas, 5)
    assert resumo["enviado_em"] == "10/01/2026 09:00" and resumo["arquivado_em"] == "20/03/2026 15:00"
    assert resumo["arquivado_por"] == "Paula" and resumo["motivo"] == "Encerrado pela unidade" and resumo["dias"] == 69
    assert projetos.resumo_arquivamento(abas, 99)["dias"] is None


def test_historico_so_recebe_linhas_novas_e_rejeita_evento_desconhecido(abas):
    projetos.acrescentar_eventos(abas, projetos.evento(1, "a", "A", "enviado", "x"))
    antes = abas["Historico"].copy()
    projetos.acrescentar_eventos(abas, projetos.evento(1, "a", "A", "travado", "y"))
    assert abas["Historico"].iloc[: len(antes)].equals(antes) and len(abas["Historico"]) == 2
    with pytest.raises(ValueError):
        projetos.evento(1, "a", "A", "evento-inventado")


# ------------------------------------------------------------------ permissões

@pytest.mark.parametrize("acao,permitidos", [
    ("criar_rascunho", {"administrador", "planejamento", "comite", "gestor_unidade", "gestor_projeto"}),
    ("liberar_edicao", {"administrador", "planejamento"}),
    ("emitir_parecer", {"administrador", "planejamento"}),
    ("arquivar", {"administrador", "planejamento"}),
    ("atualizar_qualquer_projeto", {"administrador", "planejamento"}),
])
def test_permissoes_por_nivel(acao, permitidos):
    for nivel in ("administrador", "planejamento", "comite", "gestor_unidade", "gestor_projeto", "leitor"):
        assert projetos.pode(acao, nivel) == (nivel in permitidos), (acao, nivel)
    assert not projetos.pode("acao_inexistente", "administrador")
