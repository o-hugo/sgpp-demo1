"""Gera a entrada de um usuário para colar em usuarios_codigo.py.

Uso:
    python gerar_usuario.py

A senha é digitada sem aparecer na tela e nunca é gravada: só o hash entra na entrada gerada.
"""
import getpass
import sys

import contas


def main():
    print("Níveis disponíveis:")
    for nivel, rotulo in contas.ROTULOS_NIVEL.items():
        print(f"  {nivel:<16} {rotulo}")
    print()
    login = input("Login (ex.: nome.sobrenome): ").strip()
    nome = input("Nome completo (igual ao campo Gestor dos projetos): ").strip()
    nivel = input("Nível: ").strip()
    unidade = input("Unidade (opcional): ").strip()
    senha = getpass.getpass(f"Senha (mínimo de {contas.TAMANHO_MINIMO_SENHA} caracteres): ")
    if senha != getpass.getpass("Repita a senha: "):
        sys.exit("As senhas não são iguais.")

    texto, erro = contas.linha_usuario_codigo(login, nome, nivel, senha, unidade)
    if erro:
        sys.exit(erro)
    print("\nCole dentro de USUARIOS, em usuarios_codigo.py:\n")
    print(texto)


if __name__ == "__main__":
    main()
