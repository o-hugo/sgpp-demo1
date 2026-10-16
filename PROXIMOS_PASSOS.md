# Próximos passos

Anotações para as próximas conversas. Nada daqui está implementado ainda.

## Anotado em 16/10/2026

**Pendências: a Planejamento comenta cada pendência com o responsável.** Na aba Pendências, a Planejamento deve poder mandar um comentário sobre uma pendência (por exemplo, "município em branco") ao gestor do projeto, sem sair da lista. A ideia é reaproveitar o fio de comentários que já existe em cada projeto: o comentário aparece em Retornos da Planejamento, em Meus Projetos, e o gestor pode responder. A decidir: comentar uma pendência de cada vez ou várias de um mesmo projeto; e se projetos sem gestor (18 na planilha real) vão para a Planejamento corrigir direto no Painel de Gestão.

## Já combinados e pendentes

- **Etapa 4, guia flutuante** que destaca os campos que explica, para ajudar na elaboração do projeto. Falta a referência do SIS/PaS (link ou print do guia que se quer imitar).
- **Demo online:** colocar esta versão num segundo app do Streamlit Community Cloud, separado do app atual.
- **Acesso ao SharePoint:** depende de a DTI conceder o consentimento de administrador para `Sites.Selected` ao app registrado no Entra ID. Enquanto isso, o app usa a planilha local.
- **Planilha interna no SharePoint:** criar o arquivo, descobrir o `item_id` com `descobrir_ids.py` e preencher `item_id_interno` nos Secrets. Sem isso, rascunhos, comentários e histórico ficam num arquivo temporário do servidor.
- **Aviso na tela inicial** quando houver respostas ou pedidos novos para a Planejamento (hoje ela precisa abrir a aba Revisão).
- **Power BI:** avisar quem mantém o relatório sobre as colunas novas da planilha (`CODIGO`, `INICIO_PREVISTO`, `TERMINO_PREVISTO`, `EDICAO`, `ENVIADO_POR`, `ENVIADO_EM`, `ID_RASCUNHO`, `PEDIDO_LIBERACAO`, `REVISAO`, `ID_PROJETO`) e sobre o valor `Arquivado`.
- **Nº repetido:** a DPLAN decide se corrige os Nº repetidos da planilha (25 a 41 aparecem duas vezes).
