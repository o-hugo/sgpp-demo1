"""Conteúdo do guia do SGPP: o que cada tela faz e o passo a passo, filtrado pelo nível de acesso.

Só texto e regras de visibilidade, sem Streamlit, para poder ser testado sem abrir o app. A tela que
mostra o guia fica em app.py.
"""

# Quem cria e edita projetos
_AUTORES = ("administrador", "planejamento", "comite", "gestor_unidade", "gestor_projeto")
_PLANEJAMENTO = ("administrador", "planejamento")
_VE_PENDENCIAS = ("administrador", "planejamento", "comite")

TEXTO_INICIAL = "Escolha uma seção para ver o passo a passo. O guia mostra só o que o seu nível de acesso permite."

# O Modelo de Escopo de Projeto, anexo único do Regimento Interno (Ato nº 269/2026/PGJ). A ordem e os títulos são os do modelo.
# `orientacao` resume o que o modelo pede em cada parte. `no_sgpp` lista os campos do formulário de Elaboração que já
# correspondem à parte (um teste confere que esses rótulos existem no app).
ESCOPO_ATO_PGJ = [
    {"numero": "I", "titulo": "Identificação do Projeto", "no_sgpp": ["Nome da iniciativa", "Unidade / Promotoria"],
     "orientacao": "Título do projeto e sigla (nome reduzido); unidade demandante (o órgão do MPAM ao qual o projeto se vincula, "
                   "de onde sai o gerente, que é membro ou servidor dessa unidade); gerente ou coordenador (nome e cargo) e seu "
                   "e-mail e telefone; equipe do projeto (nome, cargo, unidade, ramal e e-mail, com a indicação do gerente "
                   "substituto); e patrocinador, a autoridade que defende o projeto, viabiliza recursos e intervém nos conflitos "
                   "de maior relevância (escolha só uma, por exemplo Procurador-Geral de Justiça, Corregedor-Geral, Ouvidor-Geral, "
                   "Secretário-Geral, Coordenador de CAO, SUBADM ou SUBJUR)."},
    {"numero": "II", "titulo": "Descrição (Ementa)", "no_sgpp": ["Ementa (objetivo)"],
     "orientacao": "Descrição sucinta da iniciativa, um resumo claro, conciso e objetivo do que vai ser executado. Apresente a "
                   "ideia central, a finalidade, os procedimentos e a metodologia para chegar ao resultado, com metas possíveis "
                   "de alcançar com os recursos disponíveis."},
    {"numero": "III", "titulo": "Justificativas", "no_sgpp": [],
     "orientacao": "O problema ou a oportunidade que justifica o desenvolvimento do projeto."},
    {"numero": "IV", "titulo": "Objetivos do projeto", "no_sgpp": [],
     "orientacao": "O que se pretende realizar para resolver o problema central ou explorar a oportunidade identificada. "
                   "Especifique o objetivo geral e os objetivos específicos."},
    {"numero": "V", "titulo": "Unidades e órgãos envolvidos", "no_sgpp": [],
     "orientacao": "As unidades encarregadas de desenvolver uma atividade ou de fornecer produto ou serviço essencial à execução "
                   "do projeto. Considere também as instituições externas ao MPAM."},
    {"numero": "VI", "titulo": "Público alvo", "no_sgpp": [],
     "orientacao": "O público de acordo com a estratégia, para atingir as pessoas certas na hora certa e impactar quem realmente "
                   "fará a diferença para a iniciativa."},
    {"numero": "VII", "titulo": "Tipo de iniciativa", "no_sgpp": [],
     "orientacao": "Informe se o projeto é original (algo novo, sem precedentes na instituição) ou vinculado a outros projetos "
                   "concluídos, em andamento ou em estudo com os quais se relaciona."},
    {"numero": "VIII", "titulo": "Alinhamento estratégico e aos ODS", "no_sgpp": ["Alinhamento estratégico", "Alinhamento ao PEN"],
     "orientacao": "Alinhamento ao Planejamento Estratégico institucional (PEI-MPAM 2026-2029), ao Planejamento Estratégico "
                   "Nacional (PEN-MP 2020-2029) e aos Objetivos de Desenvolvimento Sustentável (ODS). Indique o objetivo "
                   "estratégico, o programa estratégico, a ação estratégica (do PEI-MPAM, do PEN-MP ou do Plano de Atuação "
                   "Setorial) e os ODS, que podem ser um só ou vários."},
    {"numero": "IX", "titulo": "Valores institucionais", "no_sgpp": [],
     "orientacao": "Justificativa em relação aos valores institucionais: resolutividade, transparência, proatividade, inovação "
                   "e cooperação."},
    {"numero": "X", "titulo": "Governança em Tecnologia da Informação", "no_sgpp": [],
     "orientacao": "Detalhe os recursos tecnológicos, se aplicável."},
    {"numero": "XI", "titulo": "Proteção de Dados e Segurança da Informação", "no_sgpp": [],
     "orientacao": "Informe, no que for aplicável, a Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018) e as políticas "
                   "institucionais de segurança da informação e confidencialidade, especialmente quanto ao armazenamento, ao "
                   "tratamento, ao compartilhamento e ao acesso às informações dos participantes."},
    {"numero": "XII", "titulo": "Detalhamento do Projeto", "no_sgpp": ["Início previsto", "Término previsto"],
     "orientacao": "Previsão de duração (em meses), de início e de conclusão (mês e ano); fase atual da iniciativa (a fase de "
                   "implementação, se parcial ou total); e estimativa de custo em reais."},
    {"numero": "XIII", "titulo": "Escopo e etapas do projeto", "no_sgpp": [],
     "orientacao": "Detalhe as etapas do trabalho a ser executado, as principais fases."},
    {"numero": "XIV", "titulo": "Quadro de Indicadores e Metas", "no_sgpp": [],
     "orientacao": "Os indicadores e as metas que mostram se os resultados planejados foram alcançados. Para cada indicador: "
                   "nome; tipo (esforço, resultado ou resolutividade); o que mede; data e valor da medição (absoluto ou "
                   "percentual); meta (a expectativa do novo valor com a implantação do projeto); e prazo (a previsão de "
                   "alcance da meta, em mês e ano)."},
    {"numero": "XV", "titulo": "Estimativa de Recursos Necessários", "no_sgpp": [],
     "orientacao": "Os tipos de recursos necessários à execução, com descrição, quantidade, custo em reais nos anos 1, 2 e 3 e "
                   "custo total. O modelo sugere despesas de pessoal, materiais de consumo, materiais permanentes (equipamentos), "
                   "aquisição de softwares, obras e serviços de engenharia, passagens e diárias, contratação de consultoria, "
                   "capacitação, serviços de comunicação ou pesquisa e outros, e aceita ajustes."},
    {"numero": "XVI", "titulo": "Identificação e Análise de Riscos", "no_sgpp": [],
     "orientacao": "Relacione os eventos negativos, avalie a probabilidade e o impacto e defina a resposta. Cada risco tem: se "
                   "(a causa ou a fonte), então (a consequência), probabilidade e impacto (de 1 a 4), severidade (probabilidade "
                   "vezes impacto: 1 a 3 baixo risco, 4 a 5 médio, 6 a 9 alto, 10 a 16 altíssimo), resposta (eliminar, mitigar, "
                   "transferir ou aceitar), ação (as medidas planejadas caso o risco aconteça) e responsável (quem monitora o "
                   "risco e gerencia a ação)."},
    {"numero": "XVII", "titulo": "Cronograma", "no_sgpp": [],
     "orientacao": "Data de início e de término das principais etapas ou eventos importantes do projeto, mês a mês. O modelo "
                   "sugere as etapas de planejamento, ações, melhorias e encerramento, e aceita linhas e colunas a mais ou a menos."},
]

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
            "O roteiro do que o projeto deve conter está na seção seguinte deste guia, o Modelo de Escopo do Ato nº 269/2026/PGJ.",
        ],
    },
    {
        "id": "escopo", "titulo": "Escopo do projeto (Ato PGJ)", "icone": ":material/assignment:",
        "resumo": "As 17 partes do modelo de Escopo do Projeto, o roteiro que o projeto precisa seguir.",
        "niveis": _AUTORES,
        "intro": "Este é o Modelo de Escopo de Projeto, anexo do Ato nº 269/2026/PGJ. A ordem e os títulos são os do modelo. "
                 "Onde aparece \"No SGPP\", o campo já existe em Elaboração.",
        "passos": [],
        "partes": ESCOPO_ATO_PGJ,
    },
    {
        "id": "acompanhar", "titulo": "Acompanhar e atualizar", "icone": ":material/timeline:",
        "resumo": "Registre o andamento e consulte o histórico do projeto.",
        "niveis": None,
        "passos": [
            "Abra **Acompanhamento** e escolha o projeto. As abas reúnem as atualizações, os pareceres, os comentários, os dados completos e a linha do tempo.",
            "Quem é gestor do projeto registra atualizações a qualquer momento, sem precisar liberar a edição. O histórico nunca é apagado.",
            "Para ver tudo sobre um projeto, use **Ver ficha** num cartão do **Quadro** ou marque a caixa no início da linha na tabela do **Dashboard**. A ficha reúne os dados completos, as atualizações, os pareceres, os comentários e a linha do tempo, e leva ao **Acompanhamento** para você agir.",
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
