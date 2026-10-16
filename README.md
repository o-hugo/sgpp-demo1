# SGPP MPAM: demonstração

Demonstração do Sistema de Gestão de Projetos da Diretoria de Planejamento (DPLAN) do Ministério Público do Estado do Amazonas.

**Os dados são de exemplo.** A planilha é uma amostra pequena com os nomes dos gestores anonimizados. Tudo o que for cadastrado, comentado ou alterado aqui **é apagado quando o app reinicia ou é reimplantado**.

## Como entrar

A senha de todas as contas de demonstração é `demo-mpam-2026`.

| Login | Nível | Nome |
|---|---|---|
| `paula.plan` | Planejamento | Paula Planejamento Dias |
| `carlos.comite` | Comitê | Carlos Comitê Silva |
| `membro1` | Gestor de projeto | Membro 1 |
| `membro2` | Gestor de unidade | Membro 2 |
| `leitor.demo` | Leitor | Leitor de Demonstração |

## Roteiro sugerido

1. Entre como `membro2`, abra **Elaboração**, preencha um projeto e clique em **Enviar para a Planejamento**.
2. Saia e entre como `paula.plan`. Em **Revisão**, abra **Ver o projeto inteiro**, escreva uma orientação e clique em **Devolver para ajustes**.
3. Volte como `membro2`. Em **Meus Projetos**, leia o retorno da Planejamento e responda.
4. Como `paula.plan`, veja o **Quadro** (mova um cartão), as **Pendências** e a aba **Com o gestor** da Revisão.
5. Em **Acompanhamento**, registre uma atualização e veja a linha do tempo do projeto.

## Como colocar no ar (Streamlit Community Cloud)

1. Em share.streamlit.io, entre com a conta do GitHub e clique em **Create app**.
2. Escolha este repositório, o branch `main` e o arquivo principal `app.py`.
3. Em **Advanced settings**, escolha Python 3.12. Não é preciso configurar Secrets: as contas de demonstração já estão no código.
4. O app dorme depois de cerca de 12 horas sem acesso; abra o link alguns minutos antes de usar.

Este repositório não contém dado real, segredo nem credencial do Entra ID. Para usar o app de verdade, com a planilha do SharePoint, veja o repositório principal.
