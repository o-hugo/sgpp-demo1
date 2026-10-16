import contas
import dados_internos
from armazenamento import ArmazenamentoLocal, ConflitoDeVersao


def test_arquivo_inexistente_vira_abas_vazias_e_grava_ida_e_volta(tmp_path):
    arm = ArmazenamentoLocal(str(tmp_path / "interno.xlsx"))
    abas, etag = dados_internos.ler_internos(arm)
    assert set(abas) >= {"Usuarios", "Registro"}
    assert list(abas["Usuarios"].columns) == contas.COLUNAS_USUARIOS
    assert abas["Usuarios"].empty

    abas["Usuarios"], erro = contas.solicitar_cadastro(
        abas["Usuarios"], "ana.souza", "Ana Souza Lima", "ana.souza@mpam.mp.br", "PJ", "uma-senha-longa-1")
    assert erro is None
    abas = dados_internos.acrescentar_registro(abas, contas.linha_registro("ana.souza", "cadastro_solicitado", "ana.souza"))
    dados_internos.gravar_internos(arm, abas, etag)

    lidas, _ = dados_internos.ler_internos(arm)
    conta = contas.buscar_conta(lidas["Usuarios"], "ana.souza")
    assert conta["situacao"] == "pendente" and conta["trocar_senha"] == ""
    assert contas.autenticar(lidas["Usuarios"], "ana.souza", "uma-senha-longa-1").motivo == "pendente"
    assert len(lidas["Registro"]) == 1


def test_gravar_com_versao_antiga_da_conflito(tmp_path):
    arm = ArmazenamentoLocal(str(tmp_path / "interno.xlsx"))
    abas, etag = dados_internos.ler_internos(arm)
    dados_internos.gravar_internos(arm, abas, etag)  # cria o arquivo
    abas, etag = dados_internos.ler_internos(arm)
    outra, etag_outra = dados_internos.ler_internos(arm)
    dados_internos.gravar_internos(arm, outra, etag_outra)  # outra pessoa grava primeiro
    try:
        dados_internos.gravar_internos(arm, abas, etag)
    except ConflitoDeVersao:
        return
    raise AssertionError("a gravação com versão antiga deveria dar conflito")


def test_abas_e_colunas_novas_sao_completadas_ao_ler(tmp_path):
    import pandas as pd

    caminho = tmp_path / "interno.xlsx"
    with pd.ExcelWriter(caminho) as escritor:
        pd.DataFrame({"login": ["a"], "nome": ["A B"]}).to_excel(escritor, sheet_name="Usuarios", index=False)
    abas, _ = dados_internos.ler_internos(ArmazenamentoLocal(str(caminho)))
    assert list(abas["Usuarios"].columns) == contas.COLUNAS_USUARIOS
    assert abas["Usuarios"].at[0, "login"] == "a"
    assert abas["Usuarios"].at[0, "senha_hash"] == ""
    assert "Registro" in abas
