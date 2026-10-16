import os
import re
from pathlib import Path

import usuarios_codigo
from apoio import SENHA, abrir_app, entrar
from conftest import ADMIN, PLANILHA_EXEMPLO, RAIZ, SEGREDOS_CODIGO
from test_app import MENU, ir_para
from test_usuarios_codigo import entrada

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⬀-⯿️⃣]")


def entrar_codigo(login, senha):
    return entrar(abrir_app(SEGREDOS_CODIGO), login, senha)


def test_codigo_e_estilos_nao_usam_emoji_como_icone():
    for nome in ("app.py", "contas.py", "dados_internos.py", "armazenamento.py", "assets/estilos.css"):
        texto = (RAIZ / nome).read_text(encoding="utf-8")
        achados = sorted(set(EMOJI.findall(texto)))
        assert not achados, f"{nome} tem emoji: {achados}"


def test_menu_usa_icones_material_e_nenhuma_pagina_mostra_emoji(pasta):
    at = entrar_codigo(*ADMIN)
    for opcao in at.sidebar.radio[0].options:
        assert opcao.startswith(":material/"), opcao
    for pagina in MENU:
        if MENU[pagina] not in at.sidebar.radio[0].options:
            continue
        at = ir_para(at, pagina)
        assert not at.exception, pagina
        textos = [m.value for m in at.markdown] + [b.label for b in at.button] + [e.value for e in at.error]
        assert not EMOJI.search("\n".join(map(str, textos))), pagina


def test_planilha_central_e_uma_pagina_do_menu_e_sai_da_barra_lateral(pasta):
    at = entrar_codigo(*ADMIN)
    assert MENU["planilha"] in at.sidebar.radio[0].options
    assert not any(b.label == "Recarregar planilha agora" for b in at.sidebar.button)  # saiu da barra lateral

    at = ir_para(at, "planilha")
    assert not at.exception
    valores = [m.value for m in at.metric]
    assert len(valores) == 4 and valores[0] == "21"  # registros, ativos, arquivados, excluídos da planilha de exemplo
    assert at.button(key="recarregar_planilha")
    # gestor, em modo local, vê a substituição da base, que fica desabilitada até haver arquivo e confirmação
    assert at.button(key="perigo_substituir_base").disabled


def test_planilha_central_para_nivel_comum_mostra_estado_mas_nao_a_substituicao(pasta, monkeypatch):
    monkeypatch.setattr(usuarios_codigo, "USUARIOS", entrada("membro.um", "Membro 1", "gestor_projeto"))
    at = ir_para(entrar_codigo("membro.um", SENHA), "planilha")
    assert not at.exception
    assert len(at.metric) == 4 and at.button(key="recarregar_planilha")
    assert not [b for b in at.button if b.key == "perigo_substituir_base"]
    assert not [c for c in at.checkbox if c.key == "confirma_substituir"]


def test_base_vazia_deixa_so_a_planilha_central_para_resolver(pasta):
    os.remove(PLANILHA_EXEMPLO)
    at = entrar_codigo(*ADMIN)
    assert not at.exception
    assert at.sidebar.radio[0].options == [MENU["planilha"]]
    assert any("ainda não foi iniciada" in w.value for w in at.warning)
    assert at.button(key="perigo_substituir_base").disabled


def test_hierarquia_dos_botoes_primario_para_salvar_e_perigo_para_excluir(pasta):
    at = ir_para(entrar_codigo(*ADMIN), "painel")
    assert not at.exception
    assert at.button(key="salvar_painel").proto.type == "primary"
    perigo = at.button(key="perigo_excluir_dplan")
    assert perigo.proto.type == "secondary"  # contorno vermelho vem do CSS, pela chave "perigo*"
    assert "perigo" in perigo.key

    at = ir_para(at, "elaboracao")
    assert any(b.proto.type == "primary" for b in at.button)  # o envio do formulário é a ação principal


def _luminancia(cor):
    canais = [int(cor.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contraste(a, b):
    claro, escuro = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


def test_pares_de_cores_de_texto_do_css_tem_contraste_minimo_de_4_5():
    css = Path(RAIZ / "assets" / "estilos.css").read_text(encoding="utf-8")
    cores = dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", css))
    pares = [
        ("texto", "creme"), ("texto-suave", "creme"), ("texto-suave", "creme-linha"), ("ouro-texto", "creme"),
        ("vinho", "creme"), ("vinho", "creme-linha"), ("perigo", "creme"), ("areia", "vinho"),
    ]
    for texto, fundo in pares:
        assert _contraste(cores[texto], cores[fundo]) >= 4.5, (texto, fundo)
    assert _contraste("#FFFFFF", cores["vinho"]) >= 4.5 and _contraste("#FFFFFF", cores["vinho-claro"]) >= 4.5
    # o texto dourado do cabeçalho do login (app.py) segue a mesma cor escurecida
    assert cores["ouro-texto"].lower() in (RAIZ / "app.py").read_text(encoding="utf-8").lower()


def test_cada_pagina_tem_um_h1_e_secoes_em_h2(pasta):
    at = entrar_codigo(*ADMIN)
    for pagina in ("elaboracao", "acompanhamento", "dashboard", "meus", "planilha", "exportar", "revisao", "painel"):
        at = ir_para(at, pagina)
        html_da_pagina = "\n".join(str(m.value) for m in at.markdown)
        assert html_da_pagina.count("<h1") == 1, pagina
        # seções são h2 ("## "); h3 só aparece como subseção dentro de uma seção
        assert not re.search(r"^###\s", html_da_pagina, re.MULTILINE), pagina
    markdown_planilha = "\n".join(str(m.value) for m in ir_para(at, "planilha").markdown)
    assert re.search(r"^##\s", markdown_planilha, re.MULTILINE)


def test_login_tem_um_unico_h1(pasta):
    html_login = "\n".join(str(m.value) for m in abrir_app(SEGREDOS_CODIGO).markdown)
    assert html_login.count("<h1") == 1


def test_estilos_definem_os_tres_niveis_de_botao_e_a_escala():
    css = Path(RAIZ / "assets" / "estilos.css").read_text(encoding="utf-8")
    for trecho in ("stBaseButton-primary", "stBaseButton-secondary", 'st-key-perigo', "--e1: 4px", "--e5: 24px", "--t-lg: 1.25rem",
                   ":focus-visible"):
        assert trecho in css, trecho
