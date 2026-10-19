"""Leitura e gravação da planilha central, local ou no SharePoint/OneDrive (Microsoft Graph).

As duas implementações têm a mesma interface:
    ler() -> (conteudo_xlsx: bytes | None, etag: str)
    gravar(conteudo_xlsx: bytes, etag: str) -> novo_etag: str

O etag identifica a versão lida. A gravação só acontece se o arquivo ainda estiver
nessa versão; caso contrário levanta ConflitoDeVersao, evitando que uma gravação
apague silenciosamente a alteração de outra pessoa.
"""
import os
import tempfile

import requests

GRAPH_URL = "https://graph.microsoft.com/v1.0"
GRAPH_ESCOPO = ["https://graph.microsoft.com/.default"]
TIMEOUT_SEGUNDOS = 30


class ErroArmazenamento(Exception):
    pass


class ConflitoDeVersao(ErroArmazenamento):
    pass


class ArquivoBloqueado(ErroArmazenamento):
    pass


class ArmazenamentoLocal:
    def __init__(self, caminho):
        self.caminho = caminho
        self.descricao = f"Arquivo local ({caminho})"

    def _etag_atual(self):
        if not os.path.exists(self.caminho):
            return ""
        info = os.stat(self.caminho)
        return f"{info.st_mtime_ns}-{info.st_size}"

    def ler(self):
        if not os.path.exists(self.caminho):
            return None, ""
        etag = self._etag_atual()
        with open(self.caminho, "rb") as arquivo:
            return arquivo.read(), etag

    def gravar(self, conteudo, etag):
        if self._etag_atual() != etag:
            raise ConflitoDeVersao("O arquivo foi alterado desde a última leitura.")
        pasta = os.path.dirname(os.path.abspath(self.caminho))
        # Grava em arquivo temporário e troca de uma vez, para não deixar a planilha pela metade
        descritor, temporario = tempfile.mkstemp(dir=pasta, suffix=".xlsx.tmp")
        try:
            with os.fdopen(descritor, "wb") as arquivo:
                arquivo.write(conteudo)
            os.replace(temporario, self.caminho)
        except PermissionError as erro:
            if os.path.exists(temporario):
                os.remove(temporario)
            raise ArquivoBloqueado("A planilha está aberta em outro programa.") from erro
        return self._etag_atual()


class ArmazenamentoGraph:
    def __init__(self, tenant_id, client_id, client_secret, drive_id, item_id):
        import msal

        self._app = msal.ConfidentialClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            client_credential=client_secret,
        )
        self._url_item = f"{GRAPH_URL}/drives/{drive_id}/items/{item_id}"
        self.descricao = "SharePoint/OneDrive (Microsoft Graph)"

    def _cabecalhos(self):
        # O msal reaproveita o token em memória até perto de expirar
        resultado = self._app.acquire_token_for_client(scopes=GRAPH_ESCOPO)
        if "access_token" not in resultado:
            raise ErroArmazenamento(
                f"Falha ao obter token do Microsoft Entra: {resultado.get('error_description', resultado.get('error'))}"
            )
        return {"Authorization": f"Bearer {resultado['access_token']}"}

    @staticmethod
    def _verificar(resposta):
        if resposta.ok:
            return
        mensagens = {
            401: "Credenciais do app recusadas (client secret vencido ou incorreto?).",
            403: "O app não tem permissão no site do SharePoint (concessão Sites.Selected pendente?).",
            404: "Planilha não encontrada (drive_id ou item_id incorretos, ou arquivo movido/excluído).",
            412: "A planilha foi alterada por outra pessoa desde a última leitura.",
            423: "A planilha está bloqueada para edição no SharePoint.",
            429: "Limite de requisições do Microsoft Graph atingido. Tente em alguns instantes.",
        }
        texto = mensagens.get(resposta.status_code, f"Erro {resposta.status_code} do Microsoft Graph: {resposta.text[:300]}")
        if resposta.status_code == 412:
            raise ConflitoDeVersao(texto)
        if resposta.status_code == 423:
            raise ArquivoBloqueado(texto)
        raise ErroArmazenamento(texto)

    def ler(self):
        try:
            resposta = requests.get(self._url_item, headers=self._cabecalhos(), timeout=TIMEOUT_SEGUNDOS)
            self._verificar(resposta)
            item = resposta.json()
            # A URL de download é pré-autenticada e de curta duração; não leva o token
            download = requests.get(item["@microsoft.graph.downloadUrl"], timeout=TIMEOUT_SEGUNDOS)
            self._verificar(download)
        except requests.RequestException as erro:
            raise ErroArmazenamento(f"Sem conexão com o Microsoft Graph: {erro}") from erro
        # Se o arquivo mudar entre as duas chamadas, o etag fica mais antigo que o conteúdo:
        # a próxima gravação dá conflito em vez de perder dados.
        return download.content, item["eTag"]

    def gravar(self, conteudo, etag):
        cabecalhos = self._cabecalhos()
        cabecalhos["If-Match"] = etag
        cabecalhos["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        try:
            resposta = requests.put(f"{self._url_item}/content", headers=cabecalhos, data=conteudo, timeout=TIMEOUT_SEGUNDOS)
        except requests.RequestException as erro:
            raise ErroArmazenamento(f"Sem conexão com o Microsoft Graph: {erro}") from erro
        self._verificar(resposta)
        return resposta.json()["eTag"]


class ArmazenamentoSomenteLeitura:
    """Envolve um armazenamento e recusa qualquer gravação.

    A planilha original do Power BI é aberta assim: o SGPP a lê (uma vez, para copiar os projetos para a
    própria fonte de dados) e nunca a grava. Mesmo que um erro de programação peça a gravação, ela falha.
    """

    def __init__(self, armazenamento):
        self.envolvido = armazenamento
        self.descricao = armazenamento.descricao

    def ler(self):
        return self.envolvido.ler()

    def gravar(self, conteudo, etag):
        raise ErroArmazenamento("A planilha original é somente leitura: o SGPP nunca grava nela.")


def criar_armazenamento(config_onedrive, caminho_local, chave_item="item_id"):
    """Usa o SharePoint se a seção [onedrive] dos secrets estiver completa; senão, o arquivo local.

    `chave_item` escolhe qual arquivo da mesma biblioteca usar: "item_id" é a planilha original do Power BI
    (só leitura para o SGPP) e "item_id_interno" é a fonte de dados do SGPP (projetos, usuários, rascunhos,
    pareceres, histórico).
    """
    comuns = ("tenant_id", "client_id", "client_secret", "drive_id")
    if config_onedrive and all(config_onedrive.get(c) for c in (*comuns, chave_item)):
        return ArmazenamentoGraph(*(config_onedrive[c] for c in comuns), config_onedrive[chave_item])
    return ArmazenamentoLocal(caminho_local)
