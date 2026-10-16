import ast

import pytest

import contas
import usuarios_codigo
from apoio import SENHA, abrir_app, entrar, textos_visiveis
from conftest import ADMIN, SEGREDOS_CODIGO
from test_app import MENU, ir_para


def entrada(login="ana.souza", nome="Ana Souza Lima", nivel="planejamento", senha=SENHA, **extra):
    texto, erro = contas.linha_usuario_codigo(login, nome, nivel, senha, **extra)
    assert erro is None, erro
    return ast.literal_eval("{" + texto + "}")


# ------------------------------------------------------------ regras (contas.py)

def test_entrada_gerada_vale_como_codigo_python_e_autentica():
    usuarios = entrada(unidade="DPLAN")
    assert usuarios["ana.souza"]["senha_hash"].startswith("$argon2id$")
    assert SENHA not in str(usuarios)
    df = contas.usuarios_do_codigo(usuarios)
    assert contas.autenticar(df, "ana.souza", SENHA).ok
    assert contas.buscar_conta(df, "ana.souza")["unidade"] == "DPLAN"
    assert not contas.autenticar(df, "ana.souza", "errada-errada-1").ok


def test_entrada_gerada_escapa_aspas_no_nome():
    usuarios = entrada(nome='Ana "Aninha" Souza')
    assert usuarios["ana.souza"]["nome"] == 'Ana "Aninha" Souza'


@pytest.mark.parametrize("campos", [
    {"login": "ab"}, {"login": "Ana Souza"}, {"nivel": "chefe"}, {"nome": " "}, {"senha": "curta"},
])
def test_gerador_recusa_dados_invalidos(campos):
    base = {"login": "ana.souza", "nome": "Ana Souza Lima", "nivel": "leitor", "senha": SENHA}
    texto, erro = contas.linha_usuario_codigo(**{**base, **campos})
    assert texto is None and erro


def test_usuarios_do_codigo_vazio_e_valido():
    assert contas.usuarios_do_codigo({}).empty
    assert list(contas.usuarios_do_codigo({}).columns) == contas.COLUNAS_USUARIOS


@pytest.mark.parametrize("usuarios,trecho", [
    ({"ab": {"nome": "Ana Souza", "nivel": "leitor"}}, "login"),
    ({"ana.souza": {"nome": "Ana Souza", "nivel": "chefe"}}, "nível"),
    ({"ana.souza": {"nome": " ", "nivel": "leitor"}}, "nome"),
    ({"ana.souza": {"nome": "Ana", "nivel": "leitor"}, "ANA.SOUZA": {"nome": "Ana", "nivel": "leitor"}}, "mais de uma vez"),
])
def test_usuarios_do_codigo_aponta_o_erro_de_configuracao(usuarios, trecho):
    with pytest.raises(ValueError, match=trecho):
        contas.usuarios_do_codigo(usuarios)


def test_entrada_sem_hash_nunca_autentica():
    df = contas.usuarios_do_codigo({"ana.souza": {"nome": "Ana Souza Lima", "nivel": "administrador"}})
    assert not contas.autenticar(df, "ana.souza", "").ok
    assert not contas.autenticar(df, "ana.souza", SENHA).ok


# ------------------------------------------------------------ telas (modo padrão)

def abrir_codigo():
    return abrir_app(SEGREDOS_CODIGO)


def test_login_do_modo_codigo_nao_tem_cadastro_nem_senhas_expostas(pasta):
    at = abrir_codigo()
    assert not at.tabs
    tela = textos_visiveis(at)
    assert "Solicitar cadastro" not in tela
    assert "Planejamento" in tela  # orienta a procurar a Planejamento


def test_usuario_do_codigo_entra_com_o_nivel_definido(pasta, monkeypatch):
    monkeypatch.setattr(usuarios_codigo, "USUARIOS", {
        **entrada("paula.plan", "Paula Planejamento Dias", "planejamento"),
        **entrada("membro.um", "Membro 1", "gestor_projeto"),
    })
    at = entrar(abrir_codigo(), "paula.plan", SENHA)
    assert at.session_state["autenticado"] and at.session_state["nivel"] == "planejamento"
    assert at.session_state["perfil"] == "Gestor_Geral"
    assert MENU["painel"] in at.sidebar.radio[0].options
    assert not at.exception

    at = entrar(abrir_codigo(), "membro.um", SENHA)
    assert at.session_state["nivel"] == "gestor_projeto" and at.session_state["perfil"] == "Usuario"
    assert MENU["painel"] not in at.sidebar.radio[0].options
    assert not at.session_state["conta_na_planilha"]


def test_modo_codigo_nao_mostra_gestao_de_usuarios_nem_troca_de_senha(pasta, monkeypatch):
    monkeypatch.setattr(usuarios_codigo, "USUARIOS", entrada("paula.plan", "Paula Planejamento Dias", "administrador"))
    at = entrar(abrir_codigo(), "paula.plan", SENHA)
    assert MENU["usuarios"] not in at.sidebar.radio[0].options
    assert not any("Alterar minha senha" in str(e.label) for e in at.sidebar.expander)
    # e não cria o arquivo da planilha interna
    import os
    assert not os.path.exists("DADOS_INTERNOS - SGPP.xlsx")


def test_senha_errada_e_usuario_inexistente_sao_recusados(pasta, monkeypatch):
    monkeypatch.setattr(usuarios_codigo, "USUARIOS", entrada("paula.plan", "Paula Planejamento Dias", "planejamento"))
    for login, senha in [("paula.plan", "errada-errada-1"), ("fulano", SENHA), ("admin", "123")]:
        assert not entrar(abrir_codigo(), login, senha).session_state["autenticado"]


def test_administrador_de_emergencia_continua_valendo_no_modo_codigo(pasta):
    at = entrar(abrir_codigo(), *ADMIN)
    assert at.session_state["autenticado"] and at.session_state["nivel"] == "administrador"
    assert not at.exception


def test_configuracao_invalida_nos_usuarios_do_codigo_mostra_o_que_corrigir(pasta, monkeypatch):
    monkeypatch.setattr(usuarios_codigo, "USUARIOS", {"ana.souza": {"nome": "Ana Souza", "nivel": "chefe", "senha_hash": ""}})
    at = entrar(abrir_codigo(), "ana.souza", SENHA)
    assert not at.session_state["autenticado"]
    assert any("Configuração de usuários inválida" in e.value and "chefe" in e.value for e in at.error)
    assert not at.exception


# ------------------------------------------------------------ cabeçalho do login

def test_cabecalho_do_login_tem_brasao_nome_reflexo_e_respeita_movimento_reduzido(pasta):
    at = abrir_codigo()
    pagina = "\n".join(m.value for m in at.markdown)
    assert "hero-mpam" in pagina and "data:image/png;base64," in pagina
    assert "MINISTÉRIO PÚBLICO" in pagina and "DO ESTADO DO AMAZONAS" in pagina
    assert "reflexo-caixa" in pagina
    assert "prefers-reduced-motion" in pagina
    assert ">SGPP</h1>" in pagina


def test_telas_internas_seguem_funcionando_no_modo_codigo(pasta):
    at = entrar(abrir_codigo(), *ADMIN)
    for pagina in ("elaboracao", "acompanhamento", "dashboard", "meus", "planilha", "exportar", "revisao", "painel"):
        at = ir_para(at, pagina)
        assert not at.exception, pagina
