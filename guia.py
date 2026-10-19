"""Conteúdo do guia do SGPP: o que cada tela faz e o passo a passo, filtrado pelo nível de acesso.

Só texto e regras de visibilidade, sem Streamlit, para poder ser testado sem abrir o app. A tela que
mostra o guia fica em app.py.
"""

# Quem cria e edita projetos
_AUTORES = ("administrador", "planejamento", "comite", "gestor_unidade", "gestor_projeto")
_PLANEJAMENTO = ("administrador", "planejamento")
_VE_PENDENCIAS = ("administrador", "planejamento", "comite")

TEXTO_INICIAL = "Escolha uma seção para ver o passo a passo. O guia mostra só o que o seu nível de acesso permite."

SECOES = [
    {
        "id": "comecar", "titulo": "Primeiros passos", "icone": ":material/rocket_launch:",
        "resumo": "Conheça o menu e o seu nível de acesso.",
        "niveis": None,
        "passos": [
            "O menu à esquerda mostra só as telas que o seu nível permite.",
            "O **Dashboard** e o **Quadro** mostram o portfólio inteiro do MPAM. **Meus Projetos** mostra os projetos em que você é o gestor.",
            "Em **Atalhos**, copie o nº do SEI de um projeto e abra o portal do SEI-MPAM.",
            "Este guia fica sempre à mão: o botão **Guia**, no menu, abre de novo a qualquer momento.",
        ],
    },
    {
        "id": "elaborar", "titulo": "Elaborar um projeto", "icone": ":material/edit_note:",
        "resumo": "Preencha o rascunho no seu tempo e envie para a Planejamento.",
        "niveis": _AUTORES,
        "passos": [
            "Abra **Elaboração** e preencha os dados do projeto. O rascunho pode ser salvo e retomado depois, quantas vezes você quiser.",
            "Ao salvar o rascunho, nada é exigido. Os campos obrigatórios só são conferidos no envio, e o app avisa o que falta.",
            "Clique em **Enviar para a Planejamento**. O projeto entra no portfólio com um código no formato AAAA-NNNN e fica travado para edição.",
            "Para mudar algo depois do envio, use **Solicitar liberação** em **Meus Projetos** e explique o motivo.",
        ],
    },
    {
        "id": "acompanhar", "titulo": "Acompanhar e atualizar", "icone": ":material/timeline:",
        "resumo": "Registre o andamento e consulte o histórico do projeto.",
        "niveis": None,
        "passos": [
            "Abra **Acompanhamento** e escolha o projeto. As abas reúnem as atualizações, os pareceres, os comentários, os dados completos e a linha do tempo.",
            "Quem é gestor do projeto registra atualizações a qualquer momento, sem precisar liberar a edição. O histórico nunca é apagado.",
            "No **Quadro**, mova um cartão para mudar o status (Em elaboração, Em execução, Concluído, Paralisado). Com o projeto travado, peça a liberação antes.",
            "O Leitor só consulta. O Comitê consulta o quadro, mas não move cartões.",
        ],
    },
    {
        "id": "retorno", "titulo": "Retorno da Planejamento", "icone": ":material/forum:",
        "resumo": "Veja o que a Planejamento comentou ou devolveu e responda.",
        "niveis": _AUTORES,
        "passos": [
            "Depois do envio, o projeto fica **Aguardando revisão**. Em **Meus Projetos**, um bloco mostra o que a Planejamento comentou.",
            "Se o projeto voltar como **Devolvido para ajustes**, a edição é liberada. Leia a orientação, faça os ajustes e salve.",
            "Responda no bloco de comentários e salve os ajustes em **Meus Projetos**. Ao salvar, o projeto volta para a fila da Planejamento como **Ajustes reenviados**.",
            "A revisão termina quando a Planejamento marca **Revisão concluída**.",
        ],
    },
    {
        "id": "revisao", "titulo": "Revisar projetos", "icone": ":material/rate_review:",
        "resumo": "Para a Planejamento: leia o projeto inteiro, comente e devolva ou conclua.",
        "niveis": _PLANEJAMENTO,
        "passos": [
            "Em **Revisão**, a aba **Para revisar** lista os projetos enviados e os ajustes reenviados. Abra **Ver o projeto inteiro** para ler tudo antes de decidir.",
            "Escreva a orientação e clique em **Devolver para ajustes**. O gestor recebe o comentário e a edição é liberada.",
            "Quando estiver tudo certo, clique em **Concluir revisão**.",
            "A aba **Com o gestor** mostra os projetos devolvidos e as respostas. **Pedidos de liberação** traz quem pediu para editar um projeto travado.",
            "Projetos que saíram do portfólio vão para a aba **Arquivo**, com o histórico preservado.",
        ],
    },
    {
        "id": "portfolio", "titulo": "Portfólio e planilha", "icone": ":material/dashboard:",
        "resumo": "Dashboard, quadro, planilha central e exportação.",
        "niveis": None,
        "passos": [
            "O **Dashboard** resume o portfólio e aceita filtros por área, status e município.",
            "A **Planilha Central** mostra de onde vêm os dados, a versão lida e permite recarregar a base.",
            "Em **Exportar**, baixe os dados em planilha.",
        ],
    },
    {
        "id": "pendencias", "titulo": "Pendências", "icone": ":material/checklist:",
        "resumo": "O que falta preencher nos projetos, por gravidade.",
        "niveis": _VE_PENDENCIAS,
        "passos": [
            "A tela **Pendências** lista, por projeto, os campos que faltam. A gravidade vai de **Obrigatório** a **Atenção** e **Recomendado**.",
            "Filtre por gravidade, por tipo de pendência ou busque por projeto, gestor ou unidade.",
            "Baixe a lista em .csv para cobrar os responsáveis.",
        ],
    },
    {
        "id": "niveis", "titulo": "Níveis de acesso", "icone": ":material/shield_person:",
        "resumo": "Quem pode o quê no SGPP.",
        "niveis": None,
        "passos": [
            "**Administrador:** tudo, inclusive conceder qualquer nível.",
            "**Planejamento:** painel de gestão da DPLAN, revisão, pareceres, arquivo e aprovação de cadastros.",
            "**Comitê:** aprova cadastros (até Gestor de unidade) e acompanha as pendências.",
            "**Gestor de unidade** e **Gestor de projeto:** elaboram e atualizam os próprios projetos e consultam o portfólio.",
            "**Leitor:** só consulta o portfólio.",
        ],
    },
]


def secoes_para(nivel):
    """Seções do guia que fazem sentido para o nível, na ordem de leitura, numeradas pela posição para quem lê
    (01, 02, 03...) sem lacunas. Nível desconhecido vê só o que é de todos."""
    visiveis = [s for s in SECOES if s["niveis"] is None or nivel in s["niveis"]]
    return [{**s, "numero": f"{i:02d}"} for i, s in enumerate(visiveis, 1)]
