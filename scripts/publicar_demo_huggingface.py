"""Publica a demonstração do SGPP como um Space do Hugging Face, num comando só.

Antes, uma vez, entre na sua conta (o token fica guardado só no seu computador):
    pip install -U huggingface_hub
    hf auth login            # cole um token com permissão de escrita (huggingface.co/settings/tokens)

Depois, da raiz do projeto:
    python scripts/publicar_demo_huggingface.py --simular      # mostra o que faria, sem enviar nada
    python scripts/publicar_demo_huggingface.py                # cria o Space PRIVADO e envia os arquivos
    python scripts/publicar_demo_huggingface.py --publico      # cria o Space PÚBLICO (qualquer pessoa com o link abre)

Rodar de novo atualiza o mesmo Space. Os dados da demonstração são de exemplo (nomes anonimizados) e
somem quando o Space reinicia. O token nunca é lido nem gravado por este script.
"""
import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import montar_demo_huggingface as demo  # noqa: E402


def endereco_do_app(usuario, nome):
    """Endereço direto do app (sem a moldura do Hugging Face): dono-nome.hf.space, em minúsculas e com hífens."""
    parte = lambda s: re.sub(r"[^a-z0-9-]+", "-", s.lower()).strip("-")  # noqa: E731
    return f"https://{parte(usuario)}-{parte(nome)}.hf.space"


def publicar(nome="sgpp-mpam-demo", publico=False, simular=False, api=None, pasta=None, saida=print):
    """Gera o pacote e o envia. `api` e `pasta` existem para os testes; no uso normal ficam como estão."""
    pasta = demo.montar(pasta or demo.PASTA_PADRAO)
    saida(f"Pacote gerado em {pasta}")
    if simular:
        saida(f"[simulação] criaria o Space '{nome}' ({'PÚBLICO' if publico else 'privado'}, SDK Docker) e enviaria os arquivos acima.")
        saida("[simulação] nada foi enviado.")
        return None

    if api is None:
        from huggingface_hub import HfApi

        api = HfApi()  # usa o login feito com `hf auth login` ou a variável HF_TOKEN
    usuario = api.whoami()["name"]
    repo_id = f"{usuario}/{nome}"
    api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", private=not publico, exist_ok=True)
    api.upload_folder(folder_path=str(pasta), repo_id=repo_id, repo_type="space",
                      commit_message="Demonstração do SGPP (dados de exemplo)")
    saida(f"Pronto. Página do Space: https://huggingface.co/spaces/{repo_id}")
    saida(f"A primeira montagem leva alguns minutos. Depois, o app abre em {endereco_do_app(usuario, nome)}")
    saida("Visibilidade: " + ("PÚBLICA (qualquer pessoa com o link)." if publico else "privada (só você; para mostrar a outra pessoa, use --publico)."))
    saida(f"Contas de demonstração: veja o README do Space. Senha: {demo.SENHA_DEMO}")
    return repo_id


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--nome", default="sgpp-mpam-demo", help="nome do Space (padrão: sgpp-mpam-demo)")
    parser.add_argument("--publico", action="store_true", help="cria o Space público (o padrão é privado)")
    parser.add_argument("--simular", action="store_true", help="só mostra o que faria")
    argumentos = parser.parse_args()
    try:
        publicar(argumentos.nome, argumentos.publico, argumentos.simular)
    except ImportError:
        sys.exit("Falta a biblioteca do Hugging Face. Rode: pip install -U huggingface_hub")
    except Exception as erro:  # login ausente, token sem permissão de escrita, rede
        sys.exit(f"Não foi possível publicar: {erro}\nConfira se fez 'hf auth login' com um token de escrita.")


if __name__ == "__main__":
    main()
