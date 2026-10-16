"""Usuários do SGPP definidos no próprio código (solução provisória).

Para adicionar alguém: rode `python gerar_usuario.py`, responda às perguntas e cole a entrada
que ele imprimir dentro do dicionário abaixo. Para remover, apague a entrada.

A senha NUNCA é escrita aqui em texto: só o hash Argon2id, que não permite descobrir a senha.
Para trocar a senha de alguém, gere a entrada de novo e substitua a antiga.

Campos de cada usuário:
    nome        nome completo, igual ao que consta como Gestor nos projetos (é por ele que
                "Meus Projetos" encontra os projetos da pessoa)
    nivel       administrador, planejamento, comite, gestor_unidade, gestor_projeto ou leitor
    senha_hash  gerado pelo script
    unidade     opcional

Mudanças neste arquivo valem depois que o app é reiniciado (no Streamlit Cloud, a cada novo commit).
Além destes usuários, existe a conta de emergência definida nos Secrets ([login] administrador).
"""

USUARIOS = {
    # Exemplo (apague o # e troque pelos dados gerados por gerar_usuario.py):
    # "nome.sobrenome": {
    #     "nome": "Nome Completo da Pessoa",
    #     "nivel": "planejamento",
    #     "senha_hash": "$argon2id$v=19$m=65536,t=3,p=4$...",
    # },
}
