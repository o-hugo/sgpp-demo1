"""Contas de usuário, níveis hierárquicos e aprovação de cadastros.

Sem dependência do Streamlit, para poder ser testado sozinho. As funções recebem e devolvem
DataFrames da aba "Usuarios" (ver dados_internos.py) e não gravam nada.

Níveis (mesma ideia da versão Rust, com "comitê" no lugar de "auditor"):
    administrador, planejamento, comite, gestor_unidade, gestor_projeto, leitor
"""
import hmac
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

FUSO_AMAZONAS = timezone(timedelta(hours=-4))
DOMINIO_EMAIL = "mpam.mp.br"

COLUNAS_USUARIOS = [
    "login", "nome", "email", "unidade", "senha_hash", "nivel", "situacao",
    "trocar_senha", "solicitado_em", "decidido_por", "decidido_em",
]

ROTULOS_NIVEL = {
    "administrador": "Administrador",
    "planejamento": "Planejamento",
    "comite": "Comitê",
    "gestor_unidade": "Gestor de unidade",
    "gestor_projeto": "Gestor de projeto",
    "leitor": "Leitor",
}
NIVEIS = list(ROTULOS_NIVEL)

# Quais níveis cada nível pode conceder ao aprovar ou alterar uma conta. Quem não está aqui não aprova.
# O comitê aprova, mas não concede níveis acima de gestor de unidade (sem escalada de privilégio).
NIVEIS_CONCEDIDOS = {
    "administrador": list(ROTULOS_NIVEL),
    "planejamento": [n for n in ROTULOS_NIVEL if n != "administrador"],
    "comite": ["gestor_unidade", "gestor_projeto", "leitor"],
}

ROTULOS_SITUACAO = {
    "pendente": "Aguardando aprovação",
    "ativo": "Ativo",
    "recusado": "Recusado",
    "desativado": "Desativado",
}

TAMANHO_MINIMO_SENHA = 10
_PADRAO_LOGIN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")
_PADRAO_EMAIL = re.compile(r"^[a-z0-9._%+-]+@([a-z0-9.-]+)$")

_hasher = PasswordHasher()  # Argon2id
# Hash de uma senha qualquer: usado quando o login não existe, para o tempo de resposta não revelar isso
_HASH_FALSO = _hasher.hash("senha-descartavel-sem-usuario")


def agora():
    return datetime.now(FUSO_AMAZONAS).strftime("%d/%m/%Y %H:%M")


def usuarios_vazio():
    return pd.DataFrame({coluna: pd.Series(dtype="object") for coluna in COLUNAS_USUARIOS})


def normalizar_login(texto):
    texto = str(texto or "").strip().lower()
    sufixo = f"@{DOMINIO_EMAIL}"
    return texto[: -len(sufixo)] if texto.endswith(sufixo) else texto


def validar_login(login):
    if not _PADRAO_LOGIN.match(login):
        return "O login deve ter de 3 a 40 caracteres: letras minúsculas, números, ponto, hífen ou sublinhado."
    return None


def validar_senha(senha, login=""):
    if len(senha) < TAMANHO_MINIMO_SENHA:
        return f"A senha deve ter pelo menos {TAMANHO_MINIMO_SENHA} caracteres."
    if login and senha.lower() == login.lower():
        return "A senha não pode ser igual ao login."
    return None


def gerar_hash(senha):
    return _hasher.hash(senha)


def conferir_senha(hash_guardado, senha):
    try:
        return _hasher.verify(hash_guardado, senha)
    except (VerificationError, InvalidHashError):
        return False


def _linha(df, login):
    achadas = df.index[df["login"].astype(str).str.lower() == login]
    return achadas[0] if len(achadas) else None


def buscar_conta(df, login):
    """Devolve a conta como dicionário, ou None."""
    indice = _linha(df, login)
    return None if indice is None else {c: str(df.at[indice, c]) for c in COLUNAS_USUARIOS}


# ------------------------------------------------- usuários definidos no código

def usuarios_do_codigo(usuarios):
    """Converte o dicionário de usuarios_codigo.py na mesma tabela da aba "Usuarios".

    Todas as contas entram como ativas. Erros de configuração levantam ValueError com a mensagem
    do que corrigir, para não deixar o login funcionando pela metade.
    """
    linhas, vistos = [], set()
    for login_digitado, dados in usuarios.items():
        login = normalizar_login(login_digitado)
        erro = validar_login(login)
        if erro:
            raise ValueError(f"usuarios_codigo.py, login {login_digitado!r}: {erro}")
        if login in vistos:
            raise ValueError(f"usuarios_codigo.py: o login {login!r} aparece mais de uma vez.")
        vistos.add(login)
        nivel = dados.get("nivel")
        if nivel not in ROTULOS_NIVEL:
            raise ValueError(f"usuarios_codigo.py, login {login!r}: nível {nivel!r} inválido. Use um destes: {', '.join(NIVEIS)}.")
        nome = str(dados.get("nome", "")).strip()
        if not nome:
            raise ValueError(f"usuarios_codigo.py, login {login!r}: informe o nome.")
        linhas.append({
            "login": login, "nome": nome, "email": str(dados.get("email", "")), "unidade": str(dados.get("unidade", "")),
            "senha_hash": str(dados.get("senha_hash", "")), "nivel": nivel, "situacao": "ativo",
            "trocar_senha": "", "solicitado_em": "", "decidido_por": "", "decidido_em": "",
        })
    return pd.DataFrame(linhas, columns=COLUNAS_USUARIOS) if linhas else usuarios_vazio()


def linha_usuario_codigo(login, nome, nivel, senha, unidade=""):
    """Monta o texto da entrada para colar em usuarios_codigo.py. Devolve (texto, erro)."""
    login = normalizar_login(login)
    erro = validar_login(login) or validar_senha(senha, login)
    if erro:
        return None, erro
    if nivel not in ROTULOS_NIVEL:
        return None, f"Nível inválido. Use um destes: {', '.join(NIVEIS)}."
    if not str(nome).strip():
        return None, "Informe o nome."
    def literal(valor):  # aspas e barras do texto viram escapes válidos em Python
        return json.dumps(str(valor).strip(), ensure_ascii=False)

    texto = (
        f'    {literal(login)}: {{\n'
        f'        "nome": {literal(nome)},\n'
        f'        "nivel": {literal(nivel)},\n'
        + (f'        "unidade": {literal(unidade)},\n' if str(unidade).strip() else "")
        + f'        "senha_hash": {literal(gerar_hash(senha))},\n'
        f'    }},'
    )
    return texto, None


# ------------------------------------------------------------------ cadastro

def solicitar_cadastro(df, login, nome, email, unidade, senha, logins_reservados=()):
    """Acrescenta um cadastro pendente. Devolve (df, erro)."""
    login = normalizar_login(login)
    nome, unidade = str(nome).strip(), str(unidade).strip()
    email = str(email).strip().lower()

    erro = validar_login(login)
    if erro:
        return df, erro
    if len(nome) < 5 or " " not in nome:
        return df, "Informe o nome completo, igual ao que consta como Gestor nos projetos."
    parte = _PADRAO_EMAIL.match(email)
    if not parte or parte.group(1) != DOMINIO_EMAIL:
        return df, f"Informe o e-mail institucional (@{DOMINIO_EMAIL})."
    if not unidade:
        return df, "Informe a unidade ou promotoria."
    erro = validar_senha(senha, login)
    if erro:
        return df, erro
    if login in {r.lower() for r in logins_reservados} or _linha(df, login) is not None:
        return df, "Este login já está em uso. Se o cadastro é seu, procure a Planejamento."
    if (df["email"].astype(str).str.lower() == email).any():
        return df, "Já existe um cadastro com este e-mail."

    nova = pd.DataFrame([{
        "login": login, "nome": nome, "email": email, "unidade": unidade,
        "senha_hash": gerar_hash(senha), "nivel": "", "situacao": "pendente",
        "trocar_senha": "", "solicitado_em": agora(), "decidido_por": "", "decidido_em": "",
    }])
    return pd.concat([df, nova], ignore_index=True), None


# --------------------------------------------------------------- autenticação

@dataclass
class ResultadoLogin:
    ok: bool
    conta: dict | None = None
    motivo: str = ""   # invalido | pendente | recusado | desativado


def autenticar(df, login, senha):
    """Confere login e senha. O motivo de recusa só é detalhado depois de a senha estar correta."""
    login = normalizar_login(login)
    conta = buscar_conta(df, login)
    if conta is None:
        _hasher_falso_verificar(senha)
        return ResultadoLogin(False, motivo="invalido")
    if not conferir_senha(conta["senha_hash"], senha):
        return ResultadoLogin(False, motivo="invalido")
    if conta["situacao"] != "ativo":
        return ResultadoLogin(False, conta, conta["situacao"])
    return ResultadoLogin(True, conta)


def _hasher_falso_verificar(senha):
    conferir_senha(_HASH_FALSO, senha)


def autenticar_administrador_inicial(config, login, senha):
    """Conta de emergência definida nos Secrets ([login] administrador e senha_administrador).

    Não fica na planilha: serve para o primeiro acesso e para quando as demais contas não puderem entrar.
    """
    esperado_login = normalizar_login(config.get("administrador", ""))
    esperada_senha = str(config.get("senha_administrador", ""))
    if not esperado_login or not esperada_senha:
        return None
    login_ok = hmac.compare_digest(normalizar_login(login).encode(), esperado_login.encode())
    senha_ok = hmac.compare_digest(str(senha).encode(), esperada_senha.encode())
    if login_ok and senha_ok:
        return {
            "login": esperado_login, "nome": "Conta de emergência", "email": "", "unidade": "DPLAN",
            "nivel": "administrador", "situacao": "ativo", "trocar_senha": "",
        }
    return None


class LimitadorTentativas:
    """Bloqueia um login por alguns minutos depois de falhas seguidas. Fica em memória do processo."""

    def __init__(self, maximo=5, janela_segundos=900):
        self.maximo = maximo
        self.janela = janela_segundos
        self._falhas = {}

    def segundos_bloqueado(self, login):
        agora_ = time.monotonic()
        recentes = [t for t in self._falhas.get(login, []) if agora_ - t < self.janela]
        self._falhas[login] = recentes
        if len(recentes) >= self.maximo:
            return int(self.janela - (agora_ - recentes[0])) + 1
        return 0

    def registrar_falha(self, login):
        self._falhas.setdefault(login, []).append(time.monotonic())

    def limpar(self, login):
        self._falhas.pop(login, None)


# ------------------------------------------------------- decisões sobre contas

def pode_aprovar(nivel_ator):
    return nivel_ator in NIVEIS_CONCEDIDOS


def niveis_que_pode_conceder(nivel_ator):
    return NIVEIS_CONCEDIDOS.get(nivel_ator, [])


def _checar(df, ator_login, ator_nivel, login_alvo, nivel_novo=None):
    """Valida se o ator pode agir sobre a conta. Devolve (indice, erro)."""
    if not pode_aprovar(ator_nivel):
        return None, "Seu nível não permite administrar usuários."
    indice = _linha(df, login_alvo)
    if indice is None:
        return None, "Usuário não encontrado."
    if login_alvo == normalizar_login(ator_login):
        return None, "Não é possível alterar a própria conta por aqui."
    concedidos = niveis_que_pode_conceder(ator_nivel)
    nivel_atual = str(df.at[indice, "nivel"])
    if nivel_atual and nivel_atual not in concedidos:
        return None, "Seu nível não permite alterar uma conta de nível superior."
    if nivel_novo is not None and nivel_novo not in concedidos:
        return None, "Seu nível não permite conceder este nível."
    return indice, None


def aprovar(df, ator_login, ator_nivel, login_alvo, nivel):
    indice, erro = _checar(df, ator_login, ator_nivel, login_alvo, nivel)
    if erro:
        return df, erro
    # Um cadastro recusado por engano pode ser reaberto e aprovado
    if str(df.at[indice, "situacao"]) not in ("pendente", "recusado"):
        return df, "Este cadastro não está aguardando decisão."
    df = df.copy()
    df.loc[indice, ["situacao", "nivel", "decidido_por", "decidido_em"]] = ["ativo", nivel, ator_login, agora()]
    return df, None


def recusar(df, ator_login, ator_nivel, login_alvo):
    indice, erro = _checar(df, ator_login, ator_nivel, login_alvo)
    if erro:
        return df, erro
    if str(df.at[indice, "situacao"]) != "pendente":
        return df, "Este cadastro não está aguardando aprovação."
    df = df.copy()
    df.loc[indice, ["situacao", "decidido_por", "decidido_em"]] = ["recusado", ator_login, agora()]
    return df, None


def alterar_nivel(df, ator_login, ator_nivel, login_alvo, nivel):
    indice, erro = _checar(df, ator_login, ator_nivel, login_alvo, nivel)
    if erro:
        return df, erro
    if str(df.at[indice, "situacao"]) != "ativo":
        return df, "Só é possível alterar o nível de uma conta ativa."
    df = df.copy()
    df.loc[indice, ["nivel", "decidido_por", "decidido_em"]] = [nivel, ator_login, agora()]
    return df, None


def mudar_situacao(df, ator_login, ator_nivel, login_alvo, ativar):
    """Desativa uma conta ativa ou reativa uma desativada."""
    indice, erro = _checar(df, ator_login, ator_nivel, login_alvo)
    if erro:
        return df, erro
    atual = str(df.at[indice, "situacao"])
    if ativar and atual != "desativado":
        return df, "Só é possível reativar uma conta desativada."
    if not ativar and atual != "ativo":
        return df, "Só é possível desativar uma conta ativa."
    df = df.copy()
    df.loc[indice, ["situacao", "decidido_por", "decidido_em"]] = ["ativo" if ativar else "desativado", ator_login, agora()]
    return df, None


def corrigir_dados(df, ator_login, ator_nivel, login_alvo, nome, unidade):
    """Ajusta nome e unidade. O nome precisa bater com o campo Gestor dos projetos para valer em "Meus Projetos"."""
    indice, erro = _checar(df, ator_login, ator_nivel, login_alvo)
    if erro:
        return df, erro
    nome, unidade = str(nome).strip(), str(unidade).strip()
    if len(nome) < 5 or " " not in nome:
        return df, "Informe o nome completo."
    if not unidade:
        return df, "Informe a unidade ou promotoria."
    df = df.copy()
    df.loc[indice, ["nome", "unidade", "decidido_por", "decidido_em"]] = [nome, unidade, ator_login, agora()]
    return df, None


def redefinir_senha(df, ator_login, ator_nivel, login_alvo, senha_temporaria):
    """O aprovador define uma senha temporária; no próximo acesso a pessoa é obrigada a trocá-la."""
    indice, erro = _checar(df, ator_login, ator_nivel, login_alvo)
    if erro:
        return df, erro
    erro = validar_senha(senha_temporaria, login_alvo)
    if erro:
        return df, erro
    df = df.copy()
    df.loc[indice, ["senha_hash", "trocar_senha", "decidido_por", "decidido_em"]] = [
        gerar_hash(senha_temporaria), "sim", ator_login, agora()
    ]
    return df, None


def trocar_propria_senha(df, login, senha_atual, senha_nova):
    indice = _linha(df, normalizar_login(login))
    if indice is None:
        return df, "Conta não encontrada na planilha de usuários."
    if not conferir_senha(str(df.at[indice, "senha_hash"]), senha_atual):
        return df, "A senha atual não confere."
    erro = validar_senha(senha_nova, login)
    if erro:
        return df, erro
    if senha_nova == senha_atual:
        return df, "A nova senha deve ser diferente da atual."
    df = df.copy()
    df.loc[indice, ["senha_hash", "trocar_senha"]] = [gerar_hash(senha_nova), ""]
    return df, None


def linha_registro(ator, acao, alvo="", detalhe=""):
    return {"data_hora": agora(), "ator": ator, "acao": acao, "alvo": alvo, "detalhe": detalhe}
