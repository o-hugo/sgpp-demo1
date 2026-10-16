"""Descobre drive_id e item_id da planilha no SharePoint a partir do link do arquivo.

Uso (com tenant_id, client_id e client_secret já preenchidos em .streamlit/secrets.toml):
    python descobrir_ids.py "https://mpeam.sharepoint.com/sites/DPLAN/Shared%20Documents/.../arquivo.xlsx"

Também serve de teste de permissão: se imprimir os IDs, o app consegue enxergar o arquivo.
"""
import sys
import tomllib
from urllib.parse import quote, unquote, urlparse

import msal
import requests

from armazenamento import GRAPH_ESCOPO, GRAPH_URL, TIMEOUT_SEGUNDOS


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)

    with open(".streamlit/secrets.toml", "rb") as arquivo:
        config = tomllib.load(arquivo)["onedrive"]

    app = msal.ConfidentialClientApplication(
        config["client_id"],
        authority=f"https://login.microsoftonline.com/{config['tenant_id']}",
        client_credential=config["client_secret"],
    )
    token = app.acquire_token_for_client(scopes=GRAPH_ESCOPO)
    if "access_token" not in token:
        sys.exit(f"Falha no token: {token.get('error_description', token)}")
    cabecalhos = {"Authorization": f"Bearer {token['access_token']}"}

    # https://<host>/sites/<site>/<biblioteca>/<caminho dentro da biblioteca>
    url = urlparse(sys.argv[1])
    partes = unquote(url.path).strip("/").split("/")
    if len(partes) < 4 or partes[0] != "sites":
        sys.exit("Link inesperado: o formato esperado é https://<host>/sites/<site>/<biblioteca>/<caminho>.")
    site, biblioteca, caminho = partes[1], partes[2], "/".join(partes[3:])

    resposta = requests.get(f"{GRAPH_URL}/sites/{url.hostname}:/sites/{site}", headers=cabecalhos, timeout=TIMEOUT_SEGUNDOS)
    if not resposta.ok:
        sys.exit(f"Erro {resposta.status_code} ao acessar o site (concessão Sites.Selected feita?): {resposta.text[:300]}")
    site_id = resposta.json()["id"]

    # Encontra a biblioteca pelo nome que aparece na URL (ex.: "Shared Documents")
    resposta = requests.get(f"{GRAPH_URL}/sites/{site_id}/drives", headers=cabecalhos, timeout=TIMEOUT_SEGUNDOS)
    resposta.raise_for_status()
    drives = resposta.json()["value"]
    drive = next((d for d in drives if unquote(urlparse(d["webUrl"]).path).rstrip("/").endswith("/" + biblioteca)), None)
    if drive is None:
        sys.exit(f"Biblioteca '{biblioteca}' não encontrada. Disponíveis: {[d['name'] for d in drives]}")

    resposta = requests.get(
        f"{GRAPH_URL}/drives/{drive['id']}/root:/{quote(caminho)}", headers=cabecalhos, timeout=TIMEOUT_SEGUNDOS
    )
    if not resposta.ok:
        sys.exit(f"Erro {resposta.status_code} ao localizar o arquivo: {resposta.text[:300]}")
    item = resposta.json()

    print(f"Arquivo encontrado: {item['name']} ({item['size']} bytes, modificado em {item['lastModifiedDateTime']})")
    print("\nCopie para a seção [onedrive] do secrets.toml:\n")
    print(f'drive_id = "{drive["id"]}"')
    print(f'item_id = "{item["id"]}"')


if __name__ == "__main__":
    main()
