# sgpp-mpam

Sistema de Gestão de Projetos (SGPP) da DPLAN/MPAM, em Streamlit.

O app lê e grava a planilha de projetos direto no SharePoint da DPLAN (Microsoft Graph). Sem essa configuração, usa o arquivo local `PROJETOS - Teste 1.xlsx`.

## Usuários

Cada pessoa tem a própria conta e um nível. Há dois modos, escolhidos em `origem_usuarios` na seção `[login]` dos Secrets.

### Modo padrão: usuários no código (`origem_usuarios` ausente ou `"codigo"`)

Os usuários ficam no arquivo `usuarios_codigo.py`. Para adicionar alguém:

```
python gerar_usuario.py
```

O script pergunta login, nome, nível e senha (que não aparece na tela) e imprime uma entrada para colar dentro de `USUARIOS`. Só o hash Argon2id da senha vai para o arquivo, nunca a senha. Para trocar a senha ou o nível de alguém, gere a entrada de novo e substitua a antiga; para remover, apague a entrada. As mudanças valem depois do próximo deploy (no Streamlit Cloud, a cada commit). Nesse modo não há cadastro por conta própria, aprovação nem troca de senha pelo app, e a planilha interna não é usada.

### Modo planilha (`origem_usuarios = "planilha"`)

Guardado para uma próxima etapa. Cada pessoa pede cadastro na aba **Solicitar cadastro** da tela de login, e a Planejamento (ou o comitê, dentro do que lhe cabe) aprova e define o nível em **Usuários e Níveis**. Os usuários ficam na planilha interna (ver mais abaixo).

### Níveis (nos dois modos)

| Nível | Pode |
|---|---|
| Administrador | Tudo, inclusive conceder qualquer nível |
| Planejamento | Painel de gestão da DPLAN, aprovar cadastros e conceder qualquer nível, menos Administrador |
| Comitê | Aprovar cadastros, concedendo só Gestor de unidade, Gestor de projeto ou Leitor |
| Gestor de unidade, Gestor de projeto, Leitor | Portfólio e os próprios projetos |

Regras: ninguém altera a própria conta; um nível não mexe em conta de nível superior; cinco senhas erradas bloqueiam o login por 15 minutos; a senha redefinida por um aprovador é temporária e a pessoa é obrigada a trocá-la no acesso seguinte. Toda decisão sobre contas vai para o **Registro de alterações**.

O nome da conta precisa ser igual ao que consta como Gestor nos projetos, porque é por ele que "Meus Projetos" encontra os projetos da pessoa. A tela de aprovação mostra em quantos projetos o nome aparece e permite corrigi-lo.

**Primeiro acesso:** defina a conta de emergência em `[login]` nos Secrets (`administrador` e `senha_administrador`). Ela não fica na planilha e serve para aprovar os primeiros cadastros. Sem ela, ninguém consegue aprovar o primeiro usuário.

## Ciclo do projeto

1. **Elaboração:** a pessoa monta o projeto num rascunho que **só ela enxerga** (nem a Planejamento). Dá para salvar quantas vezes quiser e voltar depois.
2. **Envio:** ao clicar em Enviar, o projeto entra na planilha central com um código `AAAA-NNNN`, fica **travado para edição** e vai para a fila **Para revisar**.
3. **Revisão (Planejamento):** na aba Revisão, a Planejamento abre o **projeto inteiro** (todos os campos, inclusive o controle interno) e escolhe:
   - **Concluir revisão**, com ou sem comentário;
   - **Devolver para ajustes**, com um comentário obrigatório dizendo o que ajustar: a edição é liberada para o gestor;
   - **Só comentar**, sem mudar o estado.
4. **Retorno ao gestor:** em Meus Projetos, a seção **Retornos da Planejamento** mostra os comentários e as devoluções, e o gestor pode **responder**. Ao salvar os ajustes, o projeto volta a ficar travado e **volta para a fila da Planejamento** ("Ajustes reenviados"). A aba **Com o gestor** da Revisão mostra os projetos devolvidos e as respostas.
5. **Pedido de liberação:** para alterar um projeto enviado que não foi devolvido, o gestor pede a liberação, com justificativa. A Planejamento libera (comentário opcional) ou nega (comentário obrigatório, para o gestor saber o motivo).
6. **Acompanhamento:** atualizações (data de referência, situação e texto), pareceres (opcionais, só a Planejamento emite), **comentários**, **dados completos** e a **linha do tempo** do projeto.
7. **Arquivo:** a Planejamento arquiva (com motivo) e reativa projetos. Os arquivados saem do portfólio, e o arquivo mostra quando foram enviados e arquivados e por quantos dias ficaram ativos.

A revisão de um projeto passa por: *Aguardando revisão*, *Devolvido para ajustes*, *Ajustes reenviados* e *Revisão concluída*. Projetos antigos (que já estavam na planilha) começam sem revisão e só entram no circuito quando a Planejamento os devolve.

| Ação | Quem pode |
|---|---|
| Criar rascunho e enviar | Todos, menos o Leitor |
| Editar projeto enviado (depois de liberado ou devolvido) | O gestor do projeto |
| Registrar atualização | O gestor do projeto, a Planejamento e o Administrador |
| Comentar e ler o fio de comentários | O gestor do projeto, a Planejamento e o Administrador |
| Concluir revisão, devolver, emitir parecer, liberar ou travar edição, arquivar | Planejamento e Administrador |
| Ver pareceres | O gestor do projeto, a Planejamento, o Comitê e o Administrador |
| Mover cartão no quadro | A Planejamento e o Administrador (qualquer projeto) e o gestor (os próprios, se não travados) |
| Ver o relatório de pendências | Planejamento, Comitê e Administrador |

Projetos que já estavam na planilha **não ficam travados**: continuam livres até a Planejamento travá-los (Revisão, aba Projetos). Eles recebem código na primeira gravação, pelo ano de criação, e os que não têm ano ficam sem código.

### Quadro

Aba **Quadro**: os projetos ativos em colunas por status (Em elaboração, Em execução, Concluído, Paralisado). Projetos com qualquer outro status, ou sem status, ficam em **Outros status**, com o texto original no cartão. Para mudar o status, o menu **Mover para** do cartão grava a mudança (com controle de versão) e registra no histórico. Mudar o status pelo quadro conta como edição: o gestor só move projeto que não esteja travado.

### Pendências

Aba **Pendências**: lista os projetos ativos com dados em branco ou que pedem atenção, por gravidade:

- **Obrigatório:** nome, tipo, área de atuação, unidade, município, gestor, ementa e status em branco;
- **Atenção:** status fora dos quatro do app, prazo vencido, datas previstas incoerentes e **Nº repetido na planilha**;
- **Recomendado:** sem ano de criação (e por isso sem código), sem nº SEI e institucionalizado em branco.

O gestor vê o aviso das pendências obrigatórias dos próprios projetos no alto de Meus Projetos. A lista pode ser filtrada e baixada em CSV.

### Colunas acrescentadas à planilha de projetos

Para que cada mudança de estado seja uma gravação só, com controle de versão, o app acrescenta ao **fim** da planilha as colunas `CODIGO`, `INICIO_PREVISTO`, `TERMINO_PREVISTO`, `EDICAO`, `ENVIADO_POR`, `ENVIADO_EM`, `ID_RASCUNHO`, `PEDIDO_LIBERACAO`, `REVISAO` e `ID_PROJETO`, e passa a usar o valor `Arquivado` em `SITUACAO_REGISTRO` (além de `Ativo` e `Excluído`). As colunas originais não mudam de nome nem de ordem. **Avise quem mantém o Power BI**: as colunas novas aparecem na tabela, e os relatórios devem filtrar `SITUACAO_REGISTRO = Ativo` para não contar arquivados e excluídos.

**Nº repetido:** a planilha real tem projetos diferentes com o mesmo Nº (por exemplo, os Nº 25 a 41 aparecem duas vezes). Por isso o app não usa o Nº como identificador: usa `ID_PROJETO`, que é igual ao Nº quando ele é único e ganha um sufixo (`28-1`, `28-2`) quando se repete. O Nº da planilha **não é alterado**. O ID é gravado na primeira gravação da planilha e nunca muda depois, mesmo se as linhas forem reordenadas ou o Nº, editado. O relatório de pendências aponta os Nº repetidos, para a DPLAN decidir se quer corrigi-los.

Rascunhos, atualizações, pareceres, comentários e o histórico ficam na **planilha interna**, que é necessária mesmo com os usuários definidos no código. No Streamlit Cloud, configure `item_id_interno` nos Secrets; sem isso o app avisa que esses dados ficam num arquivo temporário do servidor.
## Telas e identidade visual

Menu lateral: Dashboard, Quadro, Meus Projetos, Elaboração, Acompanhamento, **Planilha Central** (origem, versão e recarga dos dados; substituição da base local para gestores), Exportar, Pendências e Revisão (coordenação), Painel de Gestão e Usuários e Níveis. Cada nível só vê as telas que lhe cabem.

- Os estilos ficam em `assets/estilos.css` (cores, escala de espaçamento de 8 px, escala tipográfica de razão 1,25). Ícones são Material Symbols, nunca emoji.
- Botões em três níveis: **primário** (preenchido, a ação principal da tela, sempre à esquerda, logo abaixo do último campo), **secundário** (contorno) e **perigo** (contorno vermelho; é pedido com `key` começando em `perigo`, como `key="perigo_excluir_x"`).
- Ações da página inteira (recarregar) ficam no alto, à direita do bloco a que se referem; ações destrutivas ficam em seções separadas do salvar, com justificativa ou confirmação.
- O brasão e o logotipo estão em `assets/` (origem em `assets/LEIAME.md`).

## Planilha interna

Rascunhos, atualizações, pareceres, histórico e (no modo planilha) usuários e o registro de alterações ficam numa **segunda planilha**, à parte da que o Power BI lê, para que senhas e rascunhos nunca estejam no arquivo do relatório. No SharePoint, deixe-a numa pasta com acesso restrito à DPLAN (o app acessa pelo próprio acesso de aplicativo, então os membros não precisam abrir o arquivo). Sem `item_id_interno` nos Secrets, o app usa o arquivo local `DADOS_INTERNOS - SGPP.xlsx`, que é apagado a cada reinício no Streamlit Cloud: serve só para testes. O arquivo local está no `.gitignore`.

## Configuração

Todas as senhas e credenciais ficam em `.streamlit/secrets.toml`, que não vai para o git. Copie `.streamlit/secrets.toml.exemplo` e preencha. No Streamlit Community Cloud, cole o mesmo conteúdo em *Settings > Secrets*. Edite o arquivo salvando como UTF-8 **sem BOM**; com BOM, o Streamlit não consegue lê-lo.

- `[login]`: conta de emergência (`administrador`, `senha_administrador`).
- `[onedrive]`: credenciais do app no Microsoft Entra ID e IDs das planilhas (`item_id` e `item_id_interno`).

### Acesso ao SharePoint (uma vez)

1. O app no Entra ID tem a permissão de aplicativo `Sites.Selected` com consentimento de administrador. Essa permissão sozinha não dá acesso a nenhum site.
2. Conceda acesso ao site DPLAN pelo [Graph Explorer](https://developer.microsoft.com/graph/graph-explorer), com uma conta proprietária do site ou administradora do SharePoint:
   - `GET https://graph.microsoft.com/v1.0/sites/mpeam.sharepoint.com:/sites/DPLAN` e copie o `id`.
   - `POST https://graph.microsoft.com/v1.0/sites/{id}/permissions` com o corpo
     `{"roles":["write"],"grantedToIdentities":[{"application":{"id":"<client_id>","displayName":"SGPP-DPLAN"}}]}`.
3. Crie um client secret no portal do Entra (https://entra.microsoft.com > *App registrations* > app do SGPP > *Certificates & secrets* > *New client secret*), não no Graph Explorer. Copie o **Value** na hora, porque ele só aparece uma vez, e cole em `client_secret`. Anote a data de expiração: quando o secret vencer, o app perde o acesso à planilha.
4. Descubra os IDs de cada planilha, uma de cada vez:
   ```
   python descobrir_ids.py "<link do arquivo no SharePoint>"
   ```
   Copie o primeiro resultado para `item_id` (projetos) e o da planilha interna para `item_id_interno`. O `drive_id` é o mesmo.

## Rodar localmente

```
pip install -r requirements.txt
streamlit run app.py
```

## Testes

```
pip install -r requirements-dev.txt
python -m pytest
```

Os testes de tela rodam numa pasta temporária, com a planilha de exemplo, e não tocam nos arquivos do repositório nem no SharePoint.

## Comportamento da planilha de projetos

- A leitura fica em cache por 60 segundos (botão "Recarregar planilha agora" na barra lateral).
- Cada gravação só acontece se a planilha não foi alterada desde a leitura. Se foi, nada é gravado e o usuário recebe um aviso para refazer a alteração.
- O app regrava o arquivo inteiro: o cabeçalho original é mantido (o Power BI depende dele), mas formatação visual (cores, larguras, filtros) e outras abas se perdem. O histórico de versões do SharePoint guarda cada gravação.
- Projetos excluídos continuam na planilha com `SITUACAO_REGISTRO = Excluído`. Relatórios que leem a planilha devem filtrar por essa coluna.
- O painel considera só os projetos com Área de Atuação, Status e Município preenchidos; os demais não aparecem nos números nem nos gráficos.
