import pytest

import contas

SENHA = "uma-senha-longa-1"


def cadastrar(df, login="ana.souza", nome="Ana Souza Lima", email="ana.souza@mpam.mp.br", unidade="1ª PJ Parintins", senha=SENHA):
    return contas.solicitar_cadastro(df, login, nome, email, unidade, senha)


def conta_ativa(df, login="ana.souza", nivel="gestor_projeto", **kw):
    df, erro = cadastrar(df, login=login, email=f"{login}@mpam.mp.br", **kw)
    assert erro is None
    df, erro = contas.aprovar(df, "chefe", "planejamento", login, nivel)
    assert erro is None
    return df


def test_cadastro_fica_pendente_e_guarda_hash_argon2():
    df, erro = cadastrar(contas.usuarios_vazio())
    assert erro is None
    conta = contas.buscar_conta(df, "ana.souza")
    assert conta["situacao"] == "pendente"
    assert conta["nivel"] == ""
    assert conta["senha_hash"].startswith("$argon2id$")
    assert SENHA not in conta["senha_hash"]


@pytest.mark.parametrize("campo,valor", [
    ("login", "ab"),
    ("login", "Ana Souza"),
    ("nome", "Ana"),
    ("email", "ana@gmail.com"),
    ("email", "ana@mpam.mp.br.evil.com"),
    ("unidade", "  "),
    ("senha", "curta"),
    ("senha", "ana.souza"),
])
def test_cadastro_recusa_dados_invalidos(campo, valor):
    df, erro = cadastrar(contas.usuarios_vazio(), **{campo: valor})
    assert erro
    assert df.empty


def test_cadastro_recusa_login_ou_email_repetido_e_login_reservado():
    df, _ = cadastrar(contas.usuarios_vazio())
    _, erro = cadastrar(df, nome="Outra Pessoa Silva", email="outra@mpam.mp.br")
    assert erro and "login" in erro.lower()
    _, erro = cadastrar(df, login="outra.pessoa")
    assert erro and "e-mail" in erro.lower()
    _, erro = contas.solicitar_cadastro(contas.usuarios_vazio(), "ADMIN", "Admin Geral Um", "admin@mpam.mp.br", "DPLAN", SENHA, ["admin"])
    assert erro


def test_login_aceita_sufixo_do_email_e_ignora_maiusculas():
    df, erro = contas.solicitar_cadastro(contas.usuarios_vazio(), " Ana.Souza@MPAM.mp.br ", "Ana Souza Lima", "ana.souza@mpam.mp.br", "PJ", SENHA)
    assert erro is None
    assert contas.buscar_conta(df, "ana.souza")


def test_pendente_so_entra_depois_de_aprovado_e_so_com_senha_certa():
    df, _ = cadastrar(contas.usuarios_vazio())
    resultado = contas.autenticar(df, "ana.souza", SENHA)
    assert not resultado.ok and resultado.motivo == "pendente"
    # com senha errada, não revela nem que o cadastro existe
    assert contas.autenticar(df, "ana.souza", "errada-errada-1").motivo == "invalido"
    assert contas.autenticar(df, "ninguem", SENHA).motivo == "invalido"

    df, erro = contas.aprovar(df, "chefe", "planejamento", "ana.souza", "gestor_projeto")
    assert erro is None
    resultado = contas.autenticar(df, "ana.souza", SENHA)
    assert resultado.ok and resultado.conta["nivel"] == "gestor_projeto"


def test_recusado_e_desativado_nao_entram_e_podem_ser_reativados():
    df, _ = cadastrar(contas.usuarios_vazio())
    df, _ = contas.recusar(df, "chefe", "planejamento", "ana.souza")
    assert contas.autenticar(df, "ana.souza", SENHA).motivo == "recusado"
    df, erro = contas.aprovar(df, "chefe", "planejamento", "ana.souza", "leitor")
    assert erro is None

    df, erro = contas.mudar_situacao(df, "chefe", "planejamento", "ana.souza", ativar=False)
    assert erro is None
    assert contas.autenticar(df, "ana.souza", SENHA).motivo == "desativado"
    df, erro = contas.mudar_situacao(df, "chefe", "planejamento", "ana.souza", ativar=True)
    assert erro is None
    assert contas.autenticar(df, "ana.souza", SENHA).ok


@pytest.mark.parametrize("ator,nivel,permitido", [
    ("administrador", "administrador", True),
    ("administrador", "planejamento", True),
    ("planejamento", "administrador", False),
    ("planejamento", "comite", True),
    ("comite", "gestor_unidade", True),
    ("comite", "planejamento", False),
    ("comite", "comite", False),
    ("gestor_unidade", "leitor", False),
    ("leitor", "leitor", False),
])
def test_quem_pode_conceder_cada_nivel(ator, nivel, permitido):
    df, _ = cadastrar(contas.usuarios_vazio())
    _, erro = contas.aprovar(df, "chefe", ator, "ana.souza", nivel)
    assert (erro is None) == permitido


def test_comite_nao_mexe_em_conta_de_nivel_superior():
    df = conta_ativa(contas.usuarios_vazio(), nivel="planejamento")
    _, erro = contas.alterar_nivel(df, "membro.comite", "comite", "ana.souza", "leitor")
    assert erro
    _, erro = contas.mudar_situacao(df, "membro.comite", "comite", "ana.souza", ativar=False)
    assert erro
    _, erro = contas.redefinir_senha(df, "membro.comite", "comite", "ana.souza", "outra-senha-longa")
    assert erro


def test_ninguem_altera_a_propria_conta():
    df = conta_ativa(contas.usuarios_vazio(), nivel="planejamento")
    _, erro = contas.alterar_nivel(df, "ana.souza", "planejamento", "ana.souza", "leitor")
    assert erro
    _, erro = contas.mudar_situacao(df, "ana.souza", "planejamento", "ana.souza", ativar=False)
    assert erro


def test_alterar_nivel_de_conta_ativa():
    df = conta_ativa(contas.usuarios_vazio())
    df, erro = contas.alterar_nivel(df, "chefe", "planejamento", "ana.souza", "comite")
    assert erro is None
    assert contas.buscar_conta(df, "ana.souza")["nivel"] == "comite"
    assert contas.buscar_conta(df, "ana.souza")["decidido_por"] == "chefe"


def test_redefinir_senha_obriga_troca_no_proximo_acesso():
    df = conta_ativa(contas.usuarios_vazio())
    df, erro = contas.redefinir_senha(df, "chefe", "planejamento", "ana.souza", "senha-temporaria-9")
    assert erro is None
    assert not contas.autenticar(df, "ana.souza", SENHA).ok
    resultado = contas.autenticar(df, "ana.souza", "senha-temporaria-9")
    assert resultado.ok and resultado.conta["trocar_senha"] == "sim"

    df, erro = contas.trocar_propria_senha(df, "ana.souza", "senha-temporaria-9", "minha-nova-senha-7")
    assert erro is None
    resultado = contas.autenticar(df, "ana.souza", "minha-nova-senha-7")
    assert resultado.ok and resultado.conta["trocar_senha"] == ""


def test_trocar_propria_senha_exige_senha_atual_e_senha_nova_diferente_e_forte():
    df = conta_ativa(contas.usuarios_vazio())
    assert contas.trocar_propria_senha(df, "ana.souza", "errada-errada-1", "minha-nova-senha-7")[1]
    assert contas.trocar_propria_senha(df, "ana.souza", SENHA, SENHA)[1]
    assert contas.trocar_propria_senha(df, "ana.souza", SENHA, "curta")[1]


def test_corrigir_nome_e_unidade_respeita_as_regras_de_nivel():
    df = conta_ativa(contas.usuarios_vazio())
    df, erro = contas.corrigir_dados(df, "chefe", "planejamento", "ana.souza", "Ana Souza de Lima", "NUPA")
    assert erro is None
    conta = contas.buscar_conta(df, "ana.souza")
    assert conta["nome"] == "Ana Souza de Lima" and conta["unidade"] == "NUPA"
    assert contas.corrigir_dados(df, "chefe", "planejamento", "ana.souza", "Ana", "NUPA")[1]
    assert contas.corrigir_dados(df, "chefe", "planejamento", "ana.souza", "Ana Souza de Lima", " ")[1]
    assert contas.corrigir_dados(df, "chefe", "leitor", "ana.souza", "Ana Souza de Lima", "NUPA")[1]


def test_decidir_sobre_cadastro_inexistente_ou_ja_decidido():
    df = conta_ativa(contas.usuarios_vazio())
    assert contas.aprovar(df, "chefe", "planejamento", "ninguem", "leitor")[1]
    assert contas.aprovar(df, "chefe", "planejamento", "ana.souza", "leitor")[1]
    assert contas.recusar(df, "chefe", "planejamento", "ana.souza")[1]


def test_administrador_inicial_vem_dos_secrets():
    config = {"administrador": "Admin", "senha_administrador": "senha-do-admin-1"}
    conta = contas.autenticar_administrador_inicial(config, "admin", "senha-do-admin-1")
    assert conta and conta["nivel"] == "administrador"
    assert contas.autenticar_administrador_inicial(config, "admin", "errada") is None
    assert contas.autenticar_administrador_inicial(config, "outro", "senha-do-admin-1") is None
    # sem configuração, ninguém entra por este caminho, nem com senha vazia
    assert contas.autenticar_administrador_inicial({}, "", "") is None
    assert contas.autenticar_administrador_inicial({"administrador": "admin"}, "admin", "") is None


def test_limitador_bloqueia_apos_falhas_seguidas_e_libera_com_sucesso():
    limitador = contas.LimitadorTentativas(maximo=3, janela_segundos=60)
    for _ in range(2):
        limitador.registrar_falha("ana")
    assert limitador.segundos_bloqueado("ana") == 0
    limitador.registrar_falha("ana")
    assert 0 < limitador.segundos_bloqueado("ana") <= 61
    assert limitador.segundos_bloqueado("outra") == 0
    limitador.limpar("ana")
    assert limitador.segundos_bloqueado("ana") == 0


def test_limitador_esquece_falhas_antigas():
    limitador = contas.LimitadorTentativas(maximo=1, janela_segundos=0)
    limitador.registrar_falha("ana")
    assert limitador.segundos_bloqueado("ana") == 0
