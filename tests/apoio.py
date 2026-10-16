"""Funções de apoio para dirigir o app nos testes de tela."""
from streamlit.testing.v1 import AppTest

import contas
import dados_internos
from armazenamento import ArmazenamentoLocal
from conftest import RAIZ, SEGREDOS

SENHA = "uma-senha-longa-1"
CAMINHO_INTERNO = "DADOS_INTERNOS - SGPP.xlsx"


def abrir_app(segredos=SEGREDOS):
    at = AppTest.from_file(str(RAIZ / "app.py"), default_timeout=90)
    for secao, valores in segredos.items():
        at.secrets[secao] = valores
    return at.run()


def campo(at, rotulo):
    return next(t for t in at.text_input if t.label == rotulo)


def botao(at, rotulo):
    return next(b for b in at.button if rotulo in b.label)


def entrar(at, login, senha):
    campo(at, "Login institucional").set_value(login)
    campo(at, "Senha").set_value(senha)
    return botao(at, "Entrar").click().run()


def semear_usuarios(*contas_novas):
    """Cria contas já ativas direto na planilha interna. Cada item: (login, nome, nivel[, trocar_senha])."""
    armazenamento = ArmazenamentoLocal(CAMINHO_INTERNO)
    abas, etag = dados_internos.ler_internos(armazenamento)
    for item in contas_novas:
        login, nome, nivel = item[:3]
        abas["Usuarios"], erro = contas.solicitar_cadastro(
            abas["Usuarios"], login, nome, f"{login}@mpam.mp.br", "DPLAN", SENHA)
        assert erro is None, erro
        abas["Usuarios"], erro = contas.aprovar(abas["Usuarios"], "semente", "administrador", login, nivel)
        assert erro is None, erro
        if len(item) > 3 and item[3]:
            abas["Usuarios"], erro = contas.redefinir_senha(abas["Usuarios"], "semente", "administrador", login, SENHA)
            assert erro is None, erro
    dados_internos.gravar_internos(armazenamento, abas, etag)


def semear_codigo(monkeypatch, *contas_novas):
    """Define, só para o teste, os usuários que ficam em usuarios_codigo.py. Cada item: (login, nome, nivel)."""
    import ast

    import usuarios_codigo

    usuarios = {}
    for login, nome, nivel in contas_novas:
        texto, erro = contas.linha_usuario_codigo(login, nome, nivel, SENHA)
        assert erro is None, erro
        usuarios.update(ast.literal_eval("{" + texto + "}"))
    monkeypatch.setattr(usuarios_codigo, "USUARIOS", usuarios)


def entrar_codigo(login, senha=SENHA):
    from conftest import SEGREDOS_CODIGO

    return entrar(abrir_app(SEGREDOS_CODIGO), login, senha)


def preencher_rascunho(at, nome="Escola em Paz", unidade="NUPA", ementa="Mediação de conflitos nas escolas.", chave="novo"):
    at.text_input(key=f"r_nome_{chave}").set_value(nome)
    at.text_input(key=f"r_unid_{chave}").set_value(unidade)
    at.text_area(key=f"r_ementa_{chave}").set_value(ementa)
    return at


def textos_visiveis(at):
    """Tudo o que a pessoa lê na tela, para procurar palavras proibidas."""
    partes = [e.value for e in at.markdown] + [e.value for e in at.caption] + [e.value for e in at.error]
    partes += [e.value for e in at.warning] + [e.value for e in at.info] + [e.value for e in at.success]
    partes += [b.label for b in at.button] + [r.label for r in at.radio] + [s.label for s in at.selectbox]
    partes += [o for r in at.radio for o in r.options]
    return "\n".join(str(p) for p in partes)
