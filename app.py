import streamlit as st
import pandas as pd
import plotly.express as px
from PIL import Image
from datetime import datetime, timedelta, timezone
import base64
import html
import io
import math
import os
import re
import secrets
import zlib

import contas
import dados_internos
import documentos_sei
import guia
import projetos
import usuarios_codigo

from armazenamento import (
    ArmazenamentoGraph, ArmazenamentoLocal, ArmazenamentoSomenteLeitura, ArquivoBloqueado, ConflitoDeVersao,
    ErroArmazenamento, criar_armazenamento
)

# Importação segura da biblioteca LDAP para integração com Active Directory da TI/MPAM
try:
    from ldap3 import Server, Connection, ALL, NTLM, SUBTREE
    from ldap3.utils.conv import escape_filter_chars
    LDAP_DISPONIVEL = True
except ImportError:
    LDAP_DISPONIVEL = False

# Fuso horário oficial do Amazonas (UTC-4) para registro exato da Data/Hora de Exclusão
FUSO_AMAZONAS = timezone(timedelta(hours=-4))

# ==============================================================================
# 1. TEMA INSTITUCIONAL E CONFIGURAÇÕES GERAIS (CORES MPAM)
# ==============================================================================
PASTA_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
CAMINHO_LOGO = os.path.join(PASTA_ASSETS, "logo-mpam.png")      # logotipo horizontal (brasão + nome)
CAMINHO_BRASAO = os.path.join(PASTA_ASSETS, "brasao-mpam.png")  # só o brasão

st.set_page_config(
    page_title="SGPP - DPLAN/MPAM",
    page_icon=CAMINHO_BRASAO if os.path.exists(CAMINHO_BRASAO) else ":material/account_balance:",
    layout="wide",
)

# Identidade visual do painel "MP em Foco - Panorama" (tema sqlbi.json e scripts/fundo.py do pbip_panorama_dock)
VINHO = "#6F0000"
VINHO_CLARO = "#7C0E0E"
VINHO_ESCURO = "#560000"
OURO = "#D4A862"
AREIA = "#E8D1A9"
CREME = "#FBF7F0"
CREME_LINHA = "#F4EEE4"
TEXTO = "#404040"
PALETA_GRAFICOS = [VINHO, OURO, "#A1343C", "#8A1C1B", "#D64550", "#6B2328", "#1E803C", AREIA]

CAMINHO_CSS = os.path.join(PASTA_ASSETS, "estilos.css")

def carregar_css():
    with open(CAMINHO_CSS, encoding="utf-8") as arquivo:
        return arquivo.read()

st.markdown(f"<style>{carregar_css()}</style>", unsafe_allow_html=True)

# Avisos com ícone (Material Symbols) em vez de emoji no texto
def alerta_erro(mensagem):
    st.error(mensagem, icon=":material/error:")

def alerta_aviso(mensagem):
    st.warning(mensagem, icon=":material/warning:")

def alerta_ok(mensagem):
    st.success(mensagem, icon=":material/check_circle:")

def alerta_info(mensagem):
    st.info(mensagem, icon=":material/info:")

def faixa_titulo(titulo, subtitulo="", icone=""):
    """Cabeçalho de página: faixa vinho com friso dourado (do painel MP em Foco) e, opcionalmente, um ícone."""
    chip = f"<span class='icone-faixa' aria-hidden='true'>{icone}</span>" if icone else ""
    sub = f"<p class='subtitulo'>{subtitulo}</p>" if subtitulo else ""
    st.markdown(f"<div class='faixa-mpam'>{chip}<div><h1 class='titulo'>{titulo}</h1>{sub}</div></div>", unsafe_allow_html=True)

def estilizar_figura(fig):
    fig.update_layout(
        font=dict(family="Segoe UI, sans-serif", color=TEXTO, size=12),
        title_font=dict(color=VINHO, size=15),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        colorway=PALETA_GRAFICOS, margin=dict(t=50, l=10, r=10, b=10),
    )
    fig.update_xaxes(gridcolor=CREME_LINHA, zerolinecolor=AREIA)
    fig.update_yaxes(gridcolor=CREME_LINHA, zerolinecolor=AREIA)
    return fig

if os.path.exists(CAMINHO_LOGO):
    st.logo(CAMINHO_LOGO, size="large", icon_image=CAMINHO_BRASAO if os.path.exists(CAMINHO_BRASAO) else None)

CSS_HERO_LOGIN = """
<style>
.hero-mpam { --brasao: url("__BRASAO__"); display: flex; flex-direction: column; align-items: center;
    margin: 6px 0 4px; animation: hero-entrada 1s ease-out both; }
.hero-mpam .grupo { display: flex; align-items: center; justify-content: center; gap: 22px; }
.hero-mpam .brasao { position: relative; flex: none; width: __LARGURA__px; height: __ALTURA__px;
    background: var(--brasao) center / contain no-repeat;
    filter: drop-shadow(0 5px 8px rgba(111, 0, 0, .16)); animation: hero-pulso 6s ease-in-out infinite; }
/* Brilho: uma faixa de luz que atravessa só a parte opaca do brasão (a máscara é o próprio brasão) */
.hero-mpam .brasao::after { content: ""; position: absolute; inset: 0;
    -webkit-mask: var(--brasao) center / contain no-repeat; mask: var(--brasao) center / contain no-repeat;
    background: linear-gradient(105deg, transparent 38%, rgba(255, 255, 255, .9) 50%, transparent 62%);
    background-size: 300% 100%; background-position: 160% 0; animation: hero-brilho 6s ease-in-out 1s infinite; }
.hero-mpam .nome { font-family: "Palatino Linotype", "Book Antiqua", Palatino, Georgia, "Times New Roman", serif; line-height: 1.15; }
.hero-mpam .nome .l1 { color: __VINHO__; font-size: 1.85rem; font-weight: 700; letter-spacing: .06em; }
.hero-mpam .nome .l2 { color: #8A5F12; font-size: 1.2rem; font-weight: 700; letter-spacing: .1em; margin-top: 2px; }
.hero-mpam .nome .l3 { color: __TEXTO__; font-size: 1.05rem; font-style: italic; margin-top: 8px; }
/* Reflexo: cópia invertida do grupo, vista só na faixa de cima e que esmaece para baixo */
.hero-mpam .reflexo-caixa { height: 74px; overflow: hidden; margin-top: 4px; pointer-events: none;
    -webkit-mask-image: linear-gradient(to bottom, rgba(0, 0, 0, .34), transparent 88%);
    mask-image: linear-gradient(to bottom, rgba(0, 0, 0, .34), transparent 88%); }
.hero-mpam .reflexo-caixa .grupo { transform: scaleY(-1); filter: blur(.6px); }
.hero-mpam .reflexo-caixa .brasao { filter: none; animation: none; }
@keyframes hero-entrada { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
@keyframes hero-pulso { 0%, 100% { filter: drop-shadow(0 5px 8px rgba(111, 0, 0, .16)); }
    50% { filter: drop-shadow(0 6px 12px rgba(212, 168, 98, .38)); } }
@keyframes hero-brilho { 0%, 60% { background-position: 160% 0; } 100% { background-position: -60% 0; } }
@media (max-width: 720px) {
    .hero-mpam .grupo { flex-direction: column; gap: 8px; text-align: center; }
    .hero-mpam .nome .l1 { font-size: 1.35rem; } .hero-mpam .nome .l2 { font-size: 1rem; }
    .hero-mpam .reflexo-caixa { display: none; }
}
@media (prefers-reduced-motion: reduce) {
    .hero-mpam, .hero-mpam .brasao, .hero-mpam .brasao::after { animation: none; }
}
</style>
"""

@st.cache_resource
def hero_login_html():
    """Cabeçalho do login: brasão e nome do MPAM com reflexo e brilho. Vazio se o brasão não estiver na pasta assets."""
    if not os.path.exists(CAMINHO_BRASAO):
        return ""
    with open(CAMINHO_BRASAO, "rb") as arquivo:
        dados = base64.b64encode(arquivo.read()).decode("ascii")
    with Image.open(CAMINHO_BRASAO) as imagem:
        proporcao = imagem.width / imagem.height
    altura = 150
    css = (CSS_HERO_LOGIN
           .replace("__BRASAO__", f"data:image/png;base64,{dados}")
           .replace("__ALTURA__", str(altura)).replace("__LARGURA__", str(round(altura * proporcao)))
           .replace("__VINHO__", VINHO).replace("__TEXTO__", TEXTO))
    grupo = ("<div class='grupo'><div class='brasao'></div><div class='nome'>"
             "<div class='l1'>MINISTÉRIO PÚBLICO</div><div class='l2'>DO ESTADO DO AMAZONAS</div>"
             "<div class='l3'>Procuradoria-Geral de Justiça</div></div></div>")
    reflexo = f"<div class='reflexo-caixa' aria-hidden='true'>{grupo}</div>"
    return css + f"<div class='hero-mpam' role='img' aria-label='Ministério Público do Estado do Amazonas, Procuradoria-Geral de Justiça'>{grupo}{reflexo}</div>"

CAMINHO_PADRAO = '/content/drive/MyDrive/PROJETOS - Teste 1.xlsx'
CAMINHO_LOCAL_COLAB = 'PROJETOS - Teste 1.xlsx'

def obter_caminho_ativo():
    if os.path.exists('/content/drive/MyDrive'):
        return CAMINHO_PADRAO
    return CAMINHO_LOCAL_COLAB

def ler_secao_secrets(nome_secao):
    """Lê uma seção do secrets.toml (local) ou do painel Secrets do Streamlit Cloud; {} se não existir."""
    try:
        return dict(st.secrets.get(nome_secao, {}))
    except Exception:
        return {}

@st.cache_resource
def obter_armazenamento():
    # A planilha original do Power BI (no SharePoint, se a seção [onedrive] estiver preenchida; senão, o arquivo local).
    # O SGPP só a lê, uma vez, para copiar os projetos para a própria fonte de dados, e nunca a grava: este
    # armazenamento recusa qualquer gravação.
    return ArmazenamentoSomenteLeitura(criar_armazenamento(ler_secao_secrets("onedrive"), obter_caminho_ativo()))

def em_sharepoint():
    return isinstance(obter_armazenamento().envolvido, ArmazenamentoGraph)

# ==============================================================================
# 2. ÁREA EXCLUSIVA PARA A TI DO MPAM (INTEGRAÇÃO ACTIVE DIRECTORY / LDAP)
# ==============================================================================
ATIVAR_LDAP_CORPORATIVO_TI = False             # <-- TI: Mudar para True em Produção na Intranet
LDAP_SERVIDOR_URI = "ldap://10.0.0.10:389"     # <-- TI: Inserir IP ou Hostname do AD do MPAM
LDAP_DOMINIO_REDE = "MPAM"                     # <-- TI: Domínio NetBIOS (Ex: MPAM) ou FQDN (mpam.mp.br)
LDAP_BASE_DN = "DC=mpam,DC=mp,DC=br"           # <-- TI: Base DN para pesquisa de atributos/grupos
LDAP_GRUPO_DPLAN = "CN=DPLAN,OU=Grupos,DC=mpam,DC=mp,DC=br"

LOGINS_GESTORES_DPLAN = [
    "admin",
    "venilton.melo",
    "diretor.dplan",
    "analista1.dplan",
    "analista2.dplan",
    "coordenador.dplan"
]

def autenticar_via_ad_mpam(usuario_login, senha_rede):
    if not LDAP_DISPONIVEL:
        return False, "", False, "Biblioteca ldap3 não instalada no servidor."
        
    login_limpo = usuario_login.strip().lower().replace("@mpam.mp.br", "")
    # O AD pode aceitar bind sem senha como "não autenticado" e o bind() retornaria sucesso
    if not senha_rede:
        return False, "", False, "Informe a senha institucional."
    usuario_ntlm = f"{LDAP_DOMINIO_REDE}\\{login_limpo}"
    
    try:
        servidor = Server(LDAP_SERVIDOR_URI, get_info=ALL, connect_timeout=5)
        conexao = Connection(servidor, user=usuario_ntlm, password=senha_rede, authentication=NTLM)
        
        if conexao.bind():
            nome_completo = login_limpo
            pertence_dplan = login_limpo in [u.lower() for u in LOGINS_GESTORES_DPLAN]
            
            try:
                filtro_busca = f"(sAMAccountName={escape_filter_chars(login_limpo)})"
                conexao.search(LDAP_BASE_DN, filtro_busca, attributes=['displayName', 'memberOf', 'department'])
                if conexao.entries:
                    registro = conexao.entries[0]
                    if 'displayName' in registro and registro.displayName.value:
                        nome_completo = str(registro.displayName.value)
                    if 'department' in registro and 'DPLAN' in str(registro.department.value).upper():
                        pertence_dplan = True
                    if 'memberOf' in registro and any('DPLAN' in str(g).upper() for g in registro.memberOf):
                        pertence_dplan = True
            except Exception:
                pass
                
            conexao.unbind()
            return True, nome_completo, pertence_dplan, "Autenticado no Active Directory do MPAM."
        else:
            return False, "", False, "Usuário ou senha institucional incorretos no AD/MPAM."
    except Exception as erro_rede:
        return False, "", False, f"Servidor AD/LDAP inacessível a partir desta rede ({erro_rede})."

# ==============================================================================
# 3. CONTAS INDIVIDUAIS, NÍVEIS HIERÁRQUICOS E LOGIN
# ==============================================================================
# Cada pessoa tem a própria conta, guardada na planilha interna (aba "Usuarios") com senha em hash
# Argon2id. A Planejamento (ou o comitê, dentro do que lhe cabe) aprova o cadastro e define o nível.
# Conta de emergência: [login] administrador / senha_administrador nos Secrets (não fica na planilha).
CAMINHO_INTERNO = 'DADOS_INTERNOS - SGPP.xlsx'

@st.cache_resource
def obter_armazenamento_interno():
    # Mesma biblioteca do SharePoint, arquivo à parte (item_id_interno); sem ele, usa um arquivo local
    return criar_armazenamento(ler_secao_secrets("onedrive"), CAMINHO_INTERNO, chave_item="item_id_interno")

@st.cache_resource
def obter_limitador():
    return contas.LimitadorTentativas()

def usuarios_na_planilha():
    """Origem dos usuários. Padrão: o código (usuarios_codigo.py).

    Com `origem_usuarios = "planilha"` na seção [login] dos Secrets, ligam-se o cadastro por conta
    própria, a aprovação pela Planejamento e a planilha interna.
    """
    return ler_secao_secrets("login").get("origem_usuarios", "codigo") == "planilha"

def pode_gerenciar_usuarios(nivel):
    return usuarios_na_planilha() and contas.pode_aprovar(nivel)

def carregar_usuarios_para_login():
    """Tabela de usuários no formato de contas.py, vinda do código ou da planilha interna."""
    if usuarios_na_planilha():
        abas, _ = dados_internos.ler_internos(obter_armazenamento_interno())
        return abas["Usuarios"]
    return contas.usuarios_do_codigo(usuarios_codigo.USUARIOS)

def logins_reservados():
    reservado = contas.normalizar_login(ler_secao_secrets("login").get("administrador", ""))
    return [reservado] if reservado else []

def perfil_do_nivel(nivel):
    """Perfil usado pelas telas: Gestor_Geral vê tudo; os demais veem o portfólio e os próprios projetos."""
    if nivel in ("administrador", "planejamento"):
        return "Gestor_Geral"
    return "Comite" if nivel == "comite" else "Usuario"

def alterar_planilha_interna(alterar):
    """Lê a planilha interna, aplica alterar(abas) e grava. Devolve a mensagem de erro, ou None se deu certo.

    `alterar` modifica o dicionário de abas e devolve uma mensagem de erro (ou None). A gravação só
    acontece se ninguém mexeu na planilha desde a leitura.
    """
    armazenamento = obter_armazenamento_interno()
    try:
        abas, etag = dados_internos.ler_internos(armazenamento)
        erro = alterar(abas)
        if erro:
            return erro
        dados_internos.gravar_internos(armazenamento, abas, etag)
    except ConflitoDeVersao:
        return "Outra pessoa alterou os cadastros ao mesmo tempo. Nada foi gravado; tente de novo."
    except ArquivoBloqueado as erro:
        return f"{erro} Feche a planilha interna no Excel e tente de novo."
    except ErroArmazenamento as erro:
        return f"Não foi possível acessar os cadastros: {erro}"
    return None

MENSAGENS_LOGIN = {
    "invalido": "Login ou senha incorretos.",
    "sem_cadastro": "Sua conta institucional ainda não tem cadastro no SGPP. Use a aba Solicitar cadastro.",
    "pendente": "Seu cadastro ainda aguarda a aprovação da Planejamento.",
    "recusado": "Seu cadastro não foi aprovado. Procure a Planejamento (DPLAN).",
    "desativado": "Esta conta está desativada. Procure a Planejamento (DPLAN).",
}

def iniciar_sessao(conta):
    st.session_state['autenticado'] = True
    st.session_state['login_rede'] = conta['login']
    st.session_state['nome'] = conta['nome']
    st.session_state['nivel'] = conta['nivel']
    st.session_state['perfil'] = perfil_do_nivel(conta['nivel'])
    st.session_state['trocar_senha'] = conta.get('trocar_senha') == 'sim'
    # Só contas guardadas na planilha trocam a própria senha pelo app; as do código mudam em usuarios_codigo.py
    st.session_state['conta_na_planilha'] = usuarios_na_planilha() and conta.get('origem') != 'inicial'

def tentar_entrar(login_digitado, senha):
    login = contas.normalizar_login(login_digitado)
    if len(login) < 3 or not senha:
        alerta_erro("Informe o login e a senha.")
        return
    limitador = obter_limitador()
    espera = limitador.segundos_bloqueado(login)
    if espera:
        alerta_erro(f"Muitas tentativas incorretas. Tente novamente em {math.ceil(espera / 60)} minuto(s).")
        return

    conta = contas.autenticar_administrador_inicial(ler_secao_secrets("login"), login, senha)
    if conta is not None:
        conta['origem'] = 'inicial'
        limitador.limpar(login)
        iniciar_sessao(conta)
        st.rerun()
        return

    try:
        usuarios = carregar_usuarios_para_login()
    except ErroArmazenamento as erro:
        alerta_erro(f"Não foi possível consultar os cadastros: {erro}")
        return
    except ValueError as erro:
        alerta_erro(f"Configuração de usuários inválida. {erro}")
        return

    if ATIVAR_LDAP_CORPORATIVO_TI:
        # O AD confirma quem é a pessoa; o nível de acesso continua vindo do cadastro no SGPP
        ok_ad, _, _, _ = autenticar_via_ad_mpam(login, senha)
        if not ok_ad:
            conta, motivo = None, "invalido"
        else:
            conta = contas.buscar_conta(usuarios, login)
            motivo = "sem_cadastro" if conta is None else ("" if conta['situacao'] == "ativo" else conta['situacao'])
    else:
        resultado = contas.autenticar(usuarios, login, senha)
        conta, motivo = resultado.conta, ("" if resultado.ok else resultado.motivo)

    if motivo:
        if motivo == "invalido":
            limitador.registrar_falha(login)
        alerta_erro(MENSAGENS_LOGIN.get(motivo, MENSAGENS_LOGIN["invalido"]))
        return
    limitador.limpar(login)
    iniciar_sessao(conta)
    st.rerun()

def formulario_cadastro():
    with st.form("cadastro_form"):
        st.caption(
            "A Planejamento (DPLAN) analisa o seu cadastro e define o seu nível de acesso. "
            "Você poderá entrar depois da aprovação."
        )
        login = st.text_input("Login institucional (ex.: nome.sobrenome)")
        nome = st.text_input("Nome completo (igual ao que consta como Gestor nos projetos)")
        email = st.text_input(f"E-mail institucional (@{contas.DOMINIO_EMAIL})")
        unidade = st.text_input("Unidade / Promotoria")
        senha = confirma = ""
        if not ATIVAR_LDAP_CORPORATIVO_TI:
            senha = st.text_input(f"Senha (mínimo de {contas.TAMANHO_MINIMO_SENHA} caracteres)", type="password", key="cad_senha")
            confirma = st.text_input("Repita a senha", type="password", key="cad_confirma")
        enviado = st.form_submit_button("Solicitar cadastro", icon=":material/person_add:", type="primary", use_container_width=True)

    if not enviado:
        return
    if ATIVAR_LDAP_CORPORATIVO_TI:
        senha = secrets.token_urlsafe(32)  # a senha de verdade é a do AD; esta nunca é usada
    elif senha != confirma:
        alerta_erro("As senhas digitadas não são iguais.")
        return

    def alterar(abas):
        if (abas["Usuarios"]["situacao"] == "pendente").sum() >= 100:
            return "Há muitas solicitações aguardando análise. Procure a Planejamento."
        abas["Usuarios"], erro = contas.solicitar_cadastro(
            abas["Usuarios"], login, nome, email, unidade, senha, logins_reservados())
        if erro:
            return erro
        dados_internos.acrescentar_registro(
            abas, contas.linha_registro(contas.normalizar_login(login), "cadastro_solicitado", contas.normalizar_login(login)))
        return None

    erro = alterar_planilha_interna(alterar)
    if erro:
        alerta_erro(erro)
    else:
        alerta_ok("Cadastro enviado. Avise a Planejamento e aguarde a aprovação para entrar.")

def formulario_troca_senha(chave, obrigatoria=False):
    with st.form(f"troca_senha_{chave}"):
        atual = st.text_input("Senha atual" if not obrigatoria else "Senha temporária recebida", type="password", key=f"ts_atual_{chave}")
        nova = st.text_input(f"Nova senha (mínimo de {contas.TAMANHO_MINIMO_SENHA} caracteres)", type="password", key=f"ts_nova_{chave}")
        confirma = st.text_input("Repita a nova senha", type="password", key=f"ts_conf_{chave}")
        enviado = st.form_submit_button("Alterar senha", icon=":material/key:", type="primary")
    if not enviado:
        return
    if nova != confirma:
        alerta_erro("As senhas digitadas não são iguais.")
        return
    login = st.session_state['login_rede']

    def alterar(abas):
        abas["Usuarios"], erro = contas.trocar_propria_senha(abas["Usuarios"], login, atual, nova)
        if erro:
            return erro
        dados_internos.acrescentar_registro(abas, contas.linha_registro(login, "senha_alterada", login))
        return None

    erro = alterar_planilha_interna(alterar)
    if erro:
        alerta_erro(erro)
    else:
        st.session_state['trocar_senha'] = False
        alerta_ok("Senha alterada.")
        if obrigatoria:
            st.rerun()

def tela_troca_senha_obrigatoria():
    faixa_titulo("Defina uma nova senha", "A senha que você usou foi definida por outra pessoa. Troque-a para continuar.")
    formulario_troca_senha("obrigatoria", obrigatoria=True)
    if st.button("Sair", icon=":material/logout:"):
        st.session_state['autenticado'] = False
        st.rerun()

def tela_login():
    st.markdown(hero_login_html(), unsafe_allow_html=True)
    st.markdown(f"<h1 style='text-align: center; color: {VINHO}; padding-top: 6px; margin-bottom: 0;'>SGPP</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: {TEXTO}; font-size: 1.15rem; margin-top: 4px;'>Sistema Integrado de Gestão de Projetos <span style='color: {OURO};'>|</span> DPLAN</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.35, 1])
    with col2:
        def formulario_entrar():
            with st.form("login_form"):
                if ATIVAR_LDAP_CORPORATIVO_TI:
                    st.caption("Use o login e a senha institucionais da rede do Ministério Público do Estado do Amazonas.")
                elif usuarios_na_planilha():
                    st.caption("Use o login e a senha do seu cadastro no SGPP. Ainda não tem? Abra a aba Solicitar cadastro.")
                else:
                    st.caption("Use o login e a senha fornecidos pela DPLAN. Para obter acesso, procure a Planejamento.")
                usuario_input = st.text_input("Login institucional")
                senha = st.text_input("Senha", type="password")
                submit = st.form_submit_button("Entrar", icon=":material/login:", type="primary", use_container_width=True)
            if submit:
                tentar_entrar(usuario_input, senha)

        if usuarios_na_planilha():
            aba_entrar, aba_cadastro = st.tabs(["Entrar", "Solicitar cadastro"])
            with aba_entrar:
                formulario_entrar()
            with aba_cadastro:
                formulario_cadastro()
        else:
            formulario_entrar()

        with st.expander("Especificações técnicas para integração de login institucional (DTI / MPAM)"):
            st.markdown(f"""
            **Status atual do conector AD/LDAP:** `{'ATIVO (produção na intranet)' if ATIVAR_LDAP_CORPORATIVO_TI else 'DESLIGADO (cadastro com senha própria)'}`

            Este sistema já possui o motor **LDAPv3 / NTLM (`ldap3`)** codificado na Seção 2 do arquivo `app.py`.
            Com ele ligado, o AD confirma a identidade e o nível de acesso continua vindo do cadastro no SGPP.
            Para ativar, a equipe da **DTI/MPAM** precisa:
            1. Hospedar este script em uma máquina virtual/container na rede interna do MPAM com acesso à porta `389` (LDAP) ou `636` (LDAPS).
            2. Editar 4 variáveis na Seção 2 do código:
               * `ATIVAR_LDAP_CORPORATIVO_TI = True`
               * `LDAP_SERVIDOR_URI = "ldap://<IP_DO_AD_MPAM>:389"`
               * `LDAP_DOMINIO_REDE = "MPAM"`
               * `LDAP_BASE_DN = "DC=mpam,DC=mp,DC=br"`
            """)

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

# ==============================================================================
# 4. MOTOR DE DADOS, INTEGRAÇÃO SEI E REGISTRO DE EXCLUSÃO
# ==============================================================================
def _preparar_dataframe(df):
    """Prepara a aba Projetos para as telas: colunas de controle, códigos, ids e SEI. DataFrame vazio se não há projetos."""
    if df is None or df.empty:
        return pd.DataFrame()

    df = projetos.normalizar_nomes_da_original(df.copy())

    colunas_controle = [
        'OBSERVAÇÕES/CORREÇÕES', 'AVALIAÇÃO', 'AUDITOR_DPLAN',
        'SITUACAO_REGISTRO', 'EXCLUIDO_POR', 'MOTIVO_EXCLUSAO', 'DATA_EXCLUSAO'
    ]
    for col in colunas_controle:
        if col not in df.columns:
            df[col] = "Ativo" if col == 'SITUACAO_REGISTRO' else ""
        df[col] = df[col].fillna("Ativo" if col == 'SITUACAO_REGISTRO' else "").astype(str)
        
    df.loc[df['SITUACAO_REGISTRO'].str.strip().isin(["", "nan", "None"]), 'SITUACAO_REGISTRO'] = "Ativo"
    for col_limpa in ['EXCLUIDO_POR', 'MOTIVO_EXCLUSAO', 'DATA_EXCLUSAO', 'OBSERVAÇÕES/CORREÇÕES', 'AVALIAÇÃO', 'AUDITOR_DPLAN']:
        df.loc[df[col_limpa].str.strip().isin(["nan", "None"]), col_limpa] = ""
    
    # Colunas do ciclo do projeto (código, datas, trava) e código AAAA-NNNN dos projetos que ainda não têm
    df = projetos.atribuir_ids(projetos.preencher_codigos(df))

    # Formata o SEI removendo '.0' caso o Excel tenha lido como número decimal
    df['SEI'] = df['SEI'].fillna("").astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df.loc[df['SEI'].isin(["nan", "None"]), 'SEI'] = ""
    df['SEI_Limpo'] = df['SEI'].str.replace(r'\D', '', regex=True)
    df['Link_SEI'] = "https://sei.mpam.mp.br/sei"
    return df

@st.cache_data(ttl=60, show_spinner="Carregando os projetos...")
def _carregar_dados_cache():
    # Cache compartilhado entre sessões: evita baixar e reprocessar a planilha a cada clique na tela
    abas, etag = dados_internos.garantir_projetos(obter_armazenamento_interno(), obter_armazenamento())
    # versao: etag da leitura e as abas lidas, para gravar a aba Projetos sem perder as demais
    return _preparar_dataframe(abas[dados_internos.ABA_PROJETOS]), {"etag": etag, "abas": abas}

def carregar_dados(usar_cache=True):
    """Retorna (DataFrame, versao). Use usar_cache=False antes de operações de gravação."""
    if not usar_cache:
        _carregar_dados_cache.clear()
    return _carregar_dados_cache()

def salvar_dados(df_para_salvar, versao):
    """Grava os projetos na fonte de dados do SGPP se ela ainda estiver na versão lida; senão levanta ConflitoDeVersao.
    A planilha original do Power BI nunca é gravada."""
    interno = obter_armazenamento_interno()
    if not dados_internos.pode_gravar_projetos(interno, em_sharepoint()):
        raise ErroArmazenamento("a fonte de dados do SGPP está num arquivo local do servidor, que some quando ele reinicia. "
                                "Peça à DPLAN para configurar o item_id_interno nos Secrets antes de gravar projetos.")
    abas = dict(versao["abas"])
    abas[dados_internos.ABA_PROJETOS] = df_para_salvar.drop(columns=['SEI_Limpo', 'Link_SEI'], errors='ignore')
    try:
        dados_internos.gravar_internos(interno, abas, versao["etag"])
    finally:
        _carregar_dados_cache.clear()

def gravar_com_aviso(df_para_salvar, versao):
    """Chama salvar_dados e traduz falhas em mensagens na tela. Retorna True se gravou."""
    try:
        salvar_dados(df_para_salvar, versao)
        return True
    except ConflitoDeVersao:
        alerta_erro("A planilha foi alterada por outra pessoa desde que você abriu esta tela. "
                 "Nada foi gravado. A tela foi atualizada: confira os dados e refaça a alteração.")
    except ArquivoBloqueado as erro:
        alerta_erro(f"{erro} Feche a planilha no Excel e tente de novo.")
    except ErroArmazenamento as erro:
        alerta_erro(f"Não foi possível gravar a planilha: {erro}")
    return False

def executar_exclusao_logica(num_projeto, usuario_executor, motivo_texto):
    df_atual, versao = carregar_dados(usar_cache=False)
    mask = df_atual['ID_PROJETO'] == str(num_projeto).strip()
    if mask.any():
        agora_manaus = datetime.now(FUSO_AMAZONAS).strftime("%d/%m/%Y %H:%M")
        df_atual.loc[mask, 'SITUACAO_REGISTRO'] = "Excluído"
        df_atual.loc[mask, 'EXCLUIDO_POR'] = str(usuario_executor)
        df_atual.loc[mask, 'MOTIVO_EXCLUSAO'] = str(motivo_texto).strip()
        df_atual.loc[mask, 'DATA_EXCLUSAO'] = str(agora_manaus)
        gravou = gravar_com_aviso(df_atual, versao)
        if gravou:
            login, nome = ator_da_sessao()
            registrar_historico([projetos.evento(num_projeto, login, nome, "excluido", str(motivo_texto).strip())])
        return gravou
    return False

def restaurar_projeto_excluido(num_projeto):
    df_atual, versao = carregar_dados(usar_cache=False)
    mask = df_atual['ID_PROJETO'] == str(num_projeto).strip()
    if mask.any():
        df_atual.loc[mask, 'SITUACAO_REGISTRO'] = "Ativo"
        df_atual.loc[mask, 'EXCLUIDO_POR'] = ""
        df_atual.loc[mask, 'MOTIVO_EXCLUSAO'] = ""
        df_atual.loc[mask, 'DATA_EXCLUSAO'] = ""
        gravou = gravar_com_aviso(df_atual, versao)
        if gravou:
            login, nome = ator_da_sessao()
            registrar_historico([projetos.evento(num_projeto, login, nome, "restaurado")])
        return gravou
    return False

def renderizar_copiador_sei(df_alvo, chave_unica):
    """Cria uma barra expressa onde o usuário escolhe o projeto, copia o SEI em 1 clique e abre o portal SEI."""
    if df_alvo.empty or 'SEI' not in df_alvo.columns:
        return
    with st.expander("Copiar nº do SEI e abrir o portal", expanded=False, icon=":material/content_copy:"):
        st.caption("Escolha a iniciativa, copie o número com o ícone de copiar da caixa e abra o SEI para colar com `Ctrl+V` na pesquisa.")
        c_sel, c_copy, c_btn = st.columns([2.2, 1.3, 1])
        
        por_id = {r['ID_PROJETO']: r for _, r in df_alvo.iterrows()}
        escolha = c_sel.selectbox(
            "1. Escolha a iniciativa", list(por_id), key=f"sel_sei_{chave_unica}",
            format_func=lambda i: f"Nº {por_id[i]['Nº']} - {por_id[i]['Nome da Iniciativa']} (SEI: {por_id[i]['SEI'] or 'S/N'})")
        sei_valor = str(por_id[escolha]['SEI']).strip()
        
        with c_copy:
            st.markdown("**2. Copie o número com o ícone à direita**")
            if sei_valor:
                # O componente st.code gera nativamente o botão de 'Copiar para área de transferência' com 1 clique!
                st.code(sei_valor, language=None)
            else:
                alerta_info("Sem nº SEI cadastrado")
                
        with c_btn:
            st.markdown("**3. Abra o SEI e cole com `Ctrl+V`**")
            st.link_button("Abrir o SEI-MPAM", "https://sei.mpam.mp.br/sei", icon=":material/open_in_new:", use_container_width=True)

# ==============================================================================
# 5. INTERFACE PRINCIPAL E MÓDULOS DO SISTEMA
# ==============================================================================
COLUNAS_FILTRO = ['Status', 'Projeto/Programa/Boa Prática', 'Área de Atuação', 'Unidade', 'Município', 'Gestor']

def filtrar_tabela(df, chave, rotulo="Filtrar a tabela"):
    """Filtros para as tabelas: busca livre, institucionalizados e seleção por coluna. Devolve o df filtrado."""
    if df.empty:
        return df
    with st.expander(rotulo):
        busca = st.text_input("Buscar em qualquer coluna", key=f"busca_{chave}")
        apenas_inst = False
        if 'Institucionalizado' in df.columns:
            apenas_inst = st.checkbox("Mostrar apenas os institucionalizados", key=f"inst_{chave}")
        colunas = [c for c in COLUNAS_FILTRO if c in df.columns]
        escolhas = {}
        for coluna, destino in zip(colunas, st.columns(3) * 2):
            opcoes = sorted(df[coluna].dropna().astype(str).unique())
            escolhas[coluna] = destino.multiselect(coluna, opcoes, key=f"filtro_{chave}_{coluna}")

    mascara = pd.Series(True, index=df.index)
    if apenas_inst:
        mascara &= df['Institucionalizado'].astype(str).str.strip().str.lower() == 'sim'
    for coluna, valores in escolhas.items():
        if valores:
            mascara &= df[coluna].astype(str).isin(valores)
    if busca.strip():
        achou = df.astype(str).apply(lambda col: col.str.contains(busca.strip(), case=False, regex=False))
        mascara &= achou.any(axis=1)
    if not mascara.all():
        st.caption(f"Mostrando {int(mascara.sum())} de {len(df)} registros.")
    return df[mascara]

def texto_seguro(texto):
    """Escapa o markdown de textos digitados por usuários antes de exibi-los."""
    return re.sub(r'([\\`*_{}\[\]()#+\-.!|<>~$&])', r'\\\1', str(texto))

def decidir_usuario(funcao, acao, login_alvo, mensagem, detalhe="", **extra):
    """Aplica uma decisão sobre uma conta e grava no registro de alterações. Recarrega a tela se deu certo."""
    ator_login, ator_nivel = st.session_state['login_rede'], st.session_state['nivel']

    def alterar(abas):
        abas["Usuarios"], erro = funcao(abas["Usuarios"], ator_login, ator_nivel, login_alvo, **extra)
        if erro:
            return erro
        dados_internos.acrescentar_registro(abas, contas.linha_registro(ator_login, acao, login_alvo, detalhe))
        return None

    erro = alterar_planilha_interna(alterar)
    if erro:
        alerta_erro(erro)
        return
    st.session_state['aviso_usuarios'] = mensagem
    st.rerun()

def tela_usuarios(df_projetos):
    nivel_ator = st.session_state['nivel']
    concedidos = contas.niveis_que_pode_conceder(nivel_ator)
    faixa_titulo("Usuários e Níveis", "Aprovação de cadastros e definição do nível hierárquico", "group")
    st.caption("Níveis que você pode conceder: " + ", ".join(contas.ROTULOS_NIVEL[n] for n in concedidos) + ".")
    aviso = st.session_state.pop('aviso_usuarios', None)
    if aviso:
        alerta_ok(aviso)

    try:
        abas, _ = dados_internos.ler_internos(obter_armazenamento_interno())
    except ErroArmazenamento as erro:
        alerta_erro(f"Não foi possível ler os cadastros: {erro}")
        return
    usuarios = abas["Usuarios"]
    pendentes = usuarios[usuarios['situacao'] == 'pendente']
    gestores_nos_projetos = (
        df_projetos['Gestor'].astype(str).str.strip().str.lower().value_counts()
        if not df_projetos.empty and 'Gestor' in df_projetos.columns else pd.Series(dtype=int)
    )

    aba_pendentes, aba_contas, aba_registro = st.tabs(
        [f":material/hourglass_top: Aguardando aprovação ({len(pendentes)})", ":material/group: Contas", ":material/history: Registro de alterações"])

    with aba_pendentes:
        if pendentes.empty:
            alerta_info("Nenhum cadastro aguardando aprovação.")
        for _, linha in pendentes.iterrows():
            login = linha['login']
            with st.container(border=True):
                esquerda, direita = st.columns([2, 1.2])
                esquerda.markdown(f"**{texto_seguro(linha['nome'])}**  \n{texto_seguro(login)} | {texto_seguro(linha['email'])}  \n"
                                  f"{texto_seguro(linha['unidade'])} | pedido em {texto_seguro(linha['solicitado_em'])}")
                qtd = int(gestores_nos_projetos.get(str(linha['nome']).strip().lower(), 0))
                if qtd:
                    esquerda.caption(f"O nome consta como Gestor em {qtd} projeto(s).")
                else:
                    esquerda.caption("O nome não consta como Gestor em nenhum projeto (confira a grafia antes de aprovar).")
                padrao = concedidos.index("gestor_projeto") if "gestor_projeto" in concedidos else 0
                nivel = direita.selectbox("Nível", concedidos, index=padrao, key=f"nivel_pend_{login}",
                                          format_func=lambda n: contas.ROTULOS_NIVEL[n])
                b1, b2 = direita.columns(2)
                if b1.button("Aprovar", icon=":material/check:", type="primary", key=f"aprovar_{login}"):
                    decidir_usuario(contas.aprovar, "cadastro_aprovado", login, f"Cadastro de {login} aprovado.",
                                    f"nível: {contas.ROTULOS_NIVEL[nivel]}", nivel=nivel)
                if b2.button("Recusar", icon=":material/close:", key=f"perigo_recusar_{login}"):
                    decidir_usuario(contas.recusar, "cadastro_recusado", login, f"Cadastro de {login} recusado.")

    with aba_contas:
        decididas = usuarios[usuarios['situacao'] != 'pendente']
        if decididas.empty:
            alerta_info("Ainda não há contas decididas.")
        else:
            tabela = decididas.assign(
                nivel=decididas['nivel'].map(lambda n: contas.ROTULOS_NIVEL.get(n, "")),
                situacao=decididas['situacao'].map(lambda s: contas.ROTULOS_SITUACAO.get(s, s)),
            )[['login', 'nome', 'email', 'unidade', 'nivel', 'situacao', 'decidido_por', 'decidido_em']]
            st.dataframe(tabela, use_container_width=True, hide_index=True, column_config={
                'login': 'Login', 'nome': 'Nome', 'email': 'E-mail', 'unidade': 'Unidade', 'nivel': 'Nível',
                'situacao': 'Situação', 'decidido_por': 'Decidido por', 'decidido_em': 'Em'})

            st.markdown("### Alterar uma conta")
            alvo = st.selectbox(
                "Conta", decididas['login'].tolist(), key="conta_alvo",
                format_func=lambda l: f"{usuarios.loc[usuarios['login'] == l, 'nome'].iat[0]} ({l})")
            conta = contas.buscar_conta(usuarios, alvo)
            acoes = {
                'ativo': ["Alterar nível", "Corrigir nome e unidade", "Redefinir senha", "Desativar"],
                'desativado': ["Reativar", "Corrigir nome e unidade"],
                'recusado': ["Aprovar com um nível"],
            }.get(conta['situacao'], [])
            acao = st.radio("Ação", acoes, horizontal=True, key=f"acao_{alvo}")

            if acao in ("Alterar nível", "Aprovar com um nível"):
                atual = conta['nivel'] if conta['nivel'] in concedidos else concedidos[0]
                nivel = st.selectbox("Novo nível", concedidos, index=concedidos.index(atual), key=f"novo_nivel_{alvo}",
                                     format_func=lambda n: contas.ROTULOS_NIVEL[n])
                if st.button("Confirmar", type="primary", key=f"conf_nivel_{alvo}"):
                    if acao == "Alterar nível":
                        decidir_usuario(contas.alterar_nivel, "nivel_alterado", alvo, f"Nível de {alvo} alterado.",
                                        f"de {contas.ROTULOS_NIVEL.get(conta['nivel'], '-')} para {contas.ROTULOS_NIVEL[nivel]}", nivel=nivel)
                    else:
                        decidir_usuario(contas.aprovar, "cadastro_aprovado", alvo, f"Cadastro de {alvo} aprovado.",
                                        f"nível: {contas.ROTULOS_NIVEL[nivel]}", nivel=nivel)
            elif acao == "Corrigir nome e unidade":
                novo_nome = st.text_input("Nome completo", value=conta['nome'], key=f"cn_nome_{alvo}")
                nova_unidade = st.text_input("Unidade / Promotoria", value=conta['unidade'], key=f"cn_unid_{alvo}")
                if st.button("Salvar", type="primary", key=f"conf_dados_{alvo}"):
                    decidir_usuario(contas.corrigir_dados, "dados_corrigidos", alvo, f"Dados de {alvo} corrigidos.",
                                    nome=novo_nome, unidade=nova_unidade)
            elif acao == "Redefinir senha":
                st.caption("Informe uma senha temporária e repasse à pessoa por um canal seguro. No próximo acesso ela será obrigada a trocá-la.")
                temporaria = st.text_input("Senha temporária", type="password", key=f"temp_{alvo}")
                if st.button("Redefinir senha", type="primary", key=f"conf_senha_{alvo}"):
                    decidir_usuario(contas.redefinir_senha, "senha_redefinida", alvo, f"Senha de {alvo} redefinida.",
                                    senha_temporaria=temporaria)
            elif acao == "Desativar":
                if st.button("Desativar conta", icon=":material/block:", key=f"perigo_desativar_{alvo}"):
                    decidir_usuario(contas.mudar_situacao, "conta_desativada", alvo, f"Conta de {alvo} desativada.", ativar=False)
            elif acao == "Reativar":
                if st.button("Reativar conta", type="primary", key=f"conf_reativar_{alvo}"):
                    decidir_usuario(contas.mudar_situacao, "conta_reativada", alvo, f"Conta de {alvo} reativada.", ativar=True)

    with aba_registro:
        registro = abas["Registro"]
        if registro.empty:
            alerta_info("Nenhuma alteração registrada ainda.")
        else:
            st.dataframe(registro.iloc[::-1], use_container_width=True, hide_index=True, column_config={
                'data_hora': 'Data e hora', 'ator': 'Quem', 'acao': 'Ação', 'alvo': 'Conta', 'detalhe': 'Detalhe'})

PAGINAS = {
    "dashboard": ":material/dashboard: Dashboard",
    "quadro": ":material/view_kanban: Quadro",
    "meus": ":material/folder_open: Meus Projetos",
    "elaboracao": ":material/edit_note: Elaboração",
    "acompanhamento": ":material/timeline: Acompanhamento",
    "documentos": ":material/description: Documentos SEI",
    "planilha": ":material/table_view: Planilha Central",
    "exportar": ":material/download: Exportar",
    "pendencias": ":material/checklist: Pendências",
    "revisao": ":material/rate_review: Revisão",
    "painel": ":material/admin_panel_settings: Painel de Gestão",
    "usuarios": ":material/group: Usuários e Níveis",
}

def rotulo_lateral(texto):
    st.sidebar.markdown(f"<div class='rotulo-lateral'>{texto}</div>", unsafe_allow_html=True)

def tela_planilha_central(armazenamento, modo_sharepoint, df_completo, versao):
    """A fonte de dados do SGPP, a planilha original do Power BI (só leitura) e a troca da base de projetos."""
    faixa_titulo("Planilha Central", "Origem, versão e atualização dos dados do portfólio", "table_view")
    nivel = st.session_state['nivel']
    gestor_geral = st.session_state['perfil'] == 'Gestor_Geral'
    interno = obter_armazenamento_interno()

    if df_completo.empty:
        alerta_aviso("A fonte de dados do SGPP ainda não tem projetos."
                     + (" Use a seção Substituir a base de projetos para carregar uma planilha." if gestor_geral else ""))
        ativos = excluidos = arquivados = 0
    else:
        excluidos = int((df_completo['SITUACAO_REGISTRO'] == 'Excluído').sum())
        arquivados = int((df_completo['SITUACAO_REGISTRO'] == 'Arquivado').sum())
        ativos = len(df_completo) - excluidos - arquivados
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Registros na planilha", len(df_completo))
    m2.metric("Projetos ativos", ativos)
    m3.metric("Arquivados", arquivados)
    m4.metric("Excluídos", excluidos)

    st.markdown("## Fonte de dados do SGPP")
    with st.container(border=True):
        texto, acao = st.columns([3, 1], vertical_alignment="center")
        texto.markdown(f"**{interno.descricao}**")
        texto.caption("Os projetos, os rascunhos, as atualizações, os pareceres e o histórico ficam aqui, e só o SGPP grava nesta planilha. "
                      "A leitura é renovada sozinha a cada minuto, e cada gravação só vale se ninguém alterou a planilha desde que você a abriu.")
        if versao.get("etag"):
            texto.caption(f"Versão lida: {versao['etag'][:24]}")
        if acao.button("Recarregar agora", icon=":material/refresh:", key="recarregar_planilha", use_container_width=True):
            _carregar_dados_cache.clear()
            st.rerun()
        if isinstance(interno, ArmazenamentoLocal) and modo_sharepoint:
            alerta_erro("Esta fonte está num arquivo local do servidor e se perde quando ele reinicia. Por isso o SGPP não grava "
                        "projetos enquanto o item_id_interno não estiver configurado nos Secrets.")
        if usuarios_na_planilha():
            texto.caption("Os cadastros de usuários também ficam nela.")
        else:
            texto.caption("Os usuários estão definidos no código (usuarios_codigo.py). Para incluir, alterar ou remover alguém, "
                          "use gerar_usuario.py e edite o arquivo; vale a partir do próximo deploy.")

    st.markdown("## Planilha original do Power BI")
    with st.container(border=True):
        st.markdown(f"**{armazenamento.descricao}**")
        st.caption("Para o SGPP esta planilha é somente leitura. Ele a leu uma vez, para copiar os projetos para a fonte de dados própria, "
                   "e nunca a grava. Para alimentar o Power BI com os dados atuais, gere a exportação na tela Exportar.")

    if gestor_geral:
        st.markdown("## Substituir a base de projetos")
        alerta_aviso("A planilha enviada substitui todos os projetos da fonte de dados do SGPP. Use só para carregar uma nova versão completa. "
                     "A planilha original do Power BI não é alterada.")
        arquivo = st.file_uploader("Planilha (.xlsx)", type=['xlsx'], key="upload_base")
        confirmou = st.checkbox("Entendo que a base atual será substituída", key="confirma_substituir")
        if st.button("Substituir base", icon=":material/upload:", key="perigo_substituir_base",
                     disabled=arquivo is None or not confirmou):
            try:
                novos = projetos.normalizar_nomes_da_original(pd.read_excel(arquivo))
                salvar_dados(novos, versao)
                st.rerun()
            except ErroArmazenamento as erro:
                alerta_erro(f"Não foi possível substituir: {erro}")
            except ValueError as erro:
                alerta_erro(f"A planilha enviada não pôde ser lida: {erro}")

# ==============================================================================
# 6. ELABORAÇÃO, ACOMPANHAMENTO E REVISÃO (rascunho, envio, trava, parecer, arquivo)
# ==============================================================================
def esc(valor):
    return html.escape(projetos.texto(valor))

def rotulo_projeto(linha):
    codigo = projetos.texto(linha.get('CODIGO'))
    return f"{codigo or 'Nº ' + projetos.texto(linha.get('Nº'))} · {projetos.texto(linha.get('Nome da Iniciativa'))}"

def ator_da_sessao():
    return st.session_state['login_rede'], st.session_state['nome']

def aviso_planilha_interna_temporaria(modo_sharepoint):
    if modo_sharepoint and isinstance(obter_armazenamento_interno(), ArmazenamentoLocal):
        alerta_aviso("A fonte de dados do SGPP está num arquivo temporário do servidor e se perde quando ele reinicia. "
                     "Enquanto isso, o SGPP não grava projetos. Peça à DPLAN para configurar item_id_interno nos Secrets.")

def ler_abas_ou_erro():
    try:
        abas, _ = dados_internos.ler_internos(obter_armazenamento_interno())
        return abas
    except ErroArmazenamento as erro:
        alerta_erro(f"Não foi possível ler os dados internos: {erro}")
        return None

def html_linha_do_tempo(itens, ano_criacao=""):
    """Linha do tempo vertical. Todo texto vindo de usuários é escapado."""
    if not itens:
        legado = f" O projeto consta na planilha com ano de criação {esc(ano_criacao)}." if projetos.texto(ano_criacao) else ""
        return f"<p class='linha-tempo-vazia'>Ainda não há eventos registrados para este projeto.{legado}</p>"
    partes = []
    for item in itens:
        detalhe = f"<p>{esc(item['detalhe'])}</p>" if projetos.texto(item['detalhe']) else ""
        partes.append(
            f"<li class='ev ev-{esc(item['evento'])}'><span class='quando'>{esc(item['quando'])}</span>"
            f"<b>{esc(item['rotulo'])}</b><span class='quem'>{esc(item['quem'])}</span>{detalhe}</li>")
    return f"<ol class='linha-tempo'>{''.join(partes)}</ol>"

def etiqueta(texto, tom=""):
    return f"<span class='etiqueta {tom}'>{esc(texto)}</span>"

def situacao_da_edicao(linha):
    if projetos.parse_pedido(linha.get('PEDIDO_LIBERACAO')):
        return "Pedido de liberação enviado"
    return {"Travada": "Travado", "Liberada": "Edição liberada"}.get(projetos.texto(linha.get('EDICAO')), "Livre")

# ------------------------------------------------------------------ elaboração (rascunhos)

def salvar_rascunho(escolhido, dados):
    """Cria ou atualiza o rascunho do usuário. Devolve (id, erro)."""
    login, nome = ator_da_sessao()
    resultado = {}

    def alterar(abas):
        if escolhido == "novo":
            resultado['id'], erro = projetos.criar_rascunho(abas, login, nome, dados)
        else:
            resultado['id'], erro = escolhido, projetos.atualizar_rascunho(abas, escolhido, login, dados)
        return erro

    erro = alterar_planilha_interna(alterar)
    return (None, erro) if erro else (resultado['id'], None)

def enviar_para_planejamento(id_rascunho):
    """Cria o projeto na planilha central (travado) e marca o rascunho como enviado. Devolve (n, codigo) ou None."""
    login, nome = ator_da_sessao()
    abas = ler_abas_ou_erro()
    if abas is None:
        return None
    rascunho = projetos.buscar_rascunho(abas, id_rascunho, login)
    if rascunho is None:
        alerta_erro("Rascunho não encontrado.")
        return None
    df_atual, versao_atual = carregar_dados(usar_cache=False)
    df_novo, n, codigo, erro = projetos.enviar_rascunho(df_atual, rascunho)
    if erro:
        alerta_erro(erro)
        return None
    if len(df_novo) != len(df_atual) and not gravar_com_aviso(df_novo, versao_atual):
        return None

    def alterar(abas_):
        projetos.marcar_rascunho_enviado(abas_, id_rascunho, n)
        projetos.acrescentar_eventos(abas_, projetos.evento(n, login, nome, "enviado", f"Código {codigo}"))
        return None

    erro = alterar_planilha_interna(alterar)
    if erro:
        alerta_aviso(f"O projeto foi enviado (Nº {n}, código {codigo}), mas o rascunho não pôde ser marcado como enviado: {erro}")
    return n, codigo

def tela_elaboracao(df_completo, modo_sharepoint):
    faixa_titulo("Elaboração", "Monte o projeto com calma: a Planejamento só vê quando você enviar", "edit_note")
    login, nome = ator_da_sessao()
    if not projetos.pode("criar_rascunho", st.session_state['nivel']):
        alerta_info("O seu nível de acesso não permite criar projetos.")
        return
    aviso_planilha_interna_temporaria(modo_sharepoint)
    abas = ler_abas_ou_erro()
    if abas is None:
        return
    mensagem = st.session_state.pop('aviso_elaboracao', None)
    if mensagem:
        alerta_ok(mensagem)

    abertos = projetos.rascunhos_abertos(abas, login, df_completo)
    ids = ["novo"] + abertos["id"].tolist()
    rotulos = {"novo": "Novo rascunho"}
    rotulos.update({r.id: f"{projetos.texto(r.nome) or 'Sem nome'} (salvo em {r.atualizado_em})" for r in abertos.itertuples()})
    if 'rascunho_foco' in st.session_state:  # definido ao salvar; precisa ser aplicado antes de o seletor ser criado
        st.session_state['rascunho_sel'] = st.session_state.pop('rascunho_foco')
    if st.session_state.get('rascunho_sel') not in ids:
        st.session_state['rascunho_sel'] = "novo"
    escolhido = st.selectbox("Rascunho", ids, format_func=lambda i: rotulos[i], key="rascunho_sel")

    atual = projetos.buscar_rascunho(abas, escolhido, login) if escolhido != "novo" else None
    base = projetos.dados_vazios()
    if atual:
        base.update({c: atual[c] for c in projetos.CAMPOS_RASCUNHO})
    base_ano = int(float(base["ano"])) if projetos.texto(base["ano"]) else datetime.now().year
    areas = df_completo['Área de Atuação'].dropna().unique().tolist() if not df_completo.empty else []
    areas = areas or ["Autocomposição", "Infância e Juventude", "Criminal", "Meio Ambiente", "Patrimônio Público", "Gestão Administrativa"]
    if base["area"] and base["area"] not in areas:
        areas.append(base["area"])
    k = escolhido  # as chaves mudam por rascunho, para os campos recomeçarem dos valores salvos

    st.markdown("## Dados do projeto")
    with st.form(f"form_rascunho_{k}"):
        c1, c2, c3 = st.columns([2, 1, 1])
        nome_proj = c1.text_input("Nome da iniciativa *", value=base["nome"], key=f"r_nome_{k}")
        tipo = c2.selectbox("Tipo *", projetos.TIPOS, index=projetos.TIPOS.index(base["tipo"]) if base["tipo"] in projetos.TIPOS else 0, key=f"r_tipo_{k}")
        ano = c3.number_input("Ano de criação", min_value=2000, max_value=2050, value=base_ano, key=f"r_ano_{k}")

        c4, c5, c6 = st.columns(3)
        area = c4.selectbox("Área de atuação *", areas, index=areas.index(base["area"]) if base["area"] in areas else 0, key=f"r_area_{k}")
        unidade = c5.text_input("Unidade / Promotoria * (ex.: DPLAN, NUPA, 1ª PJ Parintins)", value=base["unidade"], key=f"r_unid_{k}")
        municipio = c6.text_input("Município *", value=base["municipio"], key=f"r_mun_{k}")

        c7, c8 = st.columns(2)
        alinhamento_est = c7.text_input("Alinhamento estratégico", value=base["alinhamento_est"], key=f"r_est_{k}")
        alinhamento_pen = c8.text_input("Alinhamento ao PEN", value=base["alinhamento_pen"], key=f"r_pen_{k}")

        c9, c10, c11 = st.columns(3)
        sei = c9.text_input("Processo SEI vinculado (ex.: 2026.000123)", value=base["sei"], key=f"r_sei_{k}")
        status = c10.selectbox("Status atual", projetos.STATUS, index=projetos.STATUS.index(base["status"]) if base["status"] in projetos.STATUS else 0, key=f"r_status_{k}")
        institucionalizado = c11.selectbox("Institucionalizado?", ["Não", "Sim"], index=1 if base["institucionalizado"] == "Sim" else 0, key=f"r_inst_{k}")

        c12, c13, _ = st.columns([1, 1, 2])
        inicio = c12.date_input("Início previsto", value=projetos.parse_data(base["inicio_previsto"]), format="DD/MM/YYYY", key=f"r_ini_{k}")
        termino = c13.date_input("Término previsto", value=projetos.parse_data(base["termino_previsto"]), format="DD/MM/YYYY", key=f"r_ter_{k}")
        ementa = st.text_area("Ementa (objetivo) *", value=base["ementa"], key=f"r_ementa_{k}")

        b1, b2, _ = st.columns([1.5, 1, 2])
        enviar = b1.form_submit_button("Enviar para a Planejamento", icon=":material/send:", type="primary")
        salvar = b2.form_submit_button("Salvar rascunho", icon=":material/save:")
        st.caption("Ao enviar, o projeto entra na planilha central e fica travado para edição até a Planejamento liberar.")

    if enviar or salvar:
        dados = {"nome": nome_proj, "tipo": tipo, "area": area, "unidade": unidade, "municipio": municipio,
                 "alinhamento_est": alinhamento_est, "alinhamento_pen": alinhamento_pen, "ano": ano, "sei": sei,
                 "status": status, "institucionalizado": institucionalizado, "ementa": ementa,
                 "inicio_previsto": inicio, "termino_previsto": termino}
        erro = projetos.validar_dados(dados, para_envio=enviar)
        if erro:
            alerta_erro(erro)
        else:
            id_salvo, erro = salvar_rascunho(escolhido, dados)
            if erro:
                alerta_erro(erro)
            elif salvar:
                st.session_state['rascunho_foco'] = id_salvo
                st.session_state['aviso_elaboracao'] = "Rascunho salvo. Só você o enxerga."
                st.rerun()
            else:
                enviado = enviar_para_planejamento(id_salvo)
                if enviado:
                    st.session_state['rascunho_foco'] = "novo"
                    st.session_state['aviso_elaboracao'] = f"Projeto enviado à Planejamento: Nº {enviado[0]}, código {enviado[1]}."
                    st.rerun()

    if atual:
        with st.expander("Descartar este rascunho", icon=":material/delete:"):
            alerta_aviso("O rascunho será descartado e não poderá ser recuperado.")
            confirmou = st.checkbox("Entendo que o rascunho será descartado", key=f"descartar_ok_{k}")
            if st.button("Descartar rascunho", icon=":material/delete:", key="perigo_descartar_rascunho", disabled=not confirmou):
                erro = alterar_planilha_interna(lambda abas_: projetos.descartar_rascunho(abas_, escolhido, login))
                if erro:
                    alerta_erro(erro)
                else:
                    st.session_state['rascunho_foco'] = "novo"
                    st.session_state['aviso_elaboracao'] = "Rascunho descartado."
                    st.rerun()

    if atual:
        with st.expander("Escopo do projeto para o SEI", icon=":material/description:"):
            st.caption("O Escopo (as 17 partes do Ato nº 269/2026/PGJ) montado com o que está salvo neste rascunho. Salve o rascunho antes para atualizar. As partes sem campo aqui saem marcadas com (a preencher: ...).")
            projeto_rascunho = documentos_sei.projeto_do_rascunho(atual, st.session_state['nome'])
            doc_escopo = documentos_sei.montar("escopo_projeto", projeto_rascunho, abas, campos={"assinante_nome": st.session_state['nome']})
            st.code(documentos_sei.para_texto(doc_escopo), language=None, wrap_lines=True)
            st.download_button("Baixar o Escopo em PDF", data=documentos_sei.para_pdf(doc_escopo, "minuta"), icon=":material/download:",
                               file_name=documentos_sei.nome_do_arquivo(doc_escopo, projeto_rascunho, "pdf"), mime="application/pdf",
                               key=f"escopo_pdf_{k}", on_click="ignore")

    enviados = abas["Rascunhos"]
    enviados = enviados[(enviados["autor_login"] == login) & (enviados["situacao"] == "enviado")].iloc[::-1].head(8)
    if not enviados.empty:
        st.markdown("## Enviados por você")
        codigos = dict(zip(df_completo["ID_PROJETO"], df_completo["CODIGO"])) if not df_completo.empty else {}
        tabela = pd.DataFrame({
            "Código": [codigos.get(projetos.texto(n), "") for n in enviados["projeto_n"]],
            "Projeto": enviados["nome"].tolist(), "Enviado em": enviados["enviado_em"].tolist(),
        })
        st.dataframe(tabela, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------ edição pelo gestor (Meus Projetos)

COLUNAS_OCULTAS_GESTOR = [
    "OBSERVAÇÕES/CORREÇÕES", "AVALIAÇÃO", "AUDITOR_DPLAN", "SEI_Limpo", "SITUACAO_REGISTRO", "EXCLUIDO_POR",
    "MOTIVO_EXCLUSAO", "DATA_EXCLUSAO", "EDICAO", "ENVIADO_POR", "ENVIADO_EM", "ID_RASCUNHO", "PEDIDO_LIBERACAO", "REVISAO", "ID_PROJETO",
]

def salvar_edicoes_gestor(df_completo, versao, df_origem, df_editado):
    """Grava as edições do gestor: valida datas, registra o que mudou e volta a travar o que estava liberado."""
    login, nome = ator_da_sessao()
    df_atual, alterados, travados, reenviados, erro = projetos.aplicar_edicoes(df_completo, df_origem, df_editado)
    if erro:
        alerta_erro(erro)
        return
    if not alterados:
        alerta_info("Nenhuma alteração para salvar.")
        return
    if not gravar_com_aviso(df_atual, versao):
        return
    eventos = [projetos.evento(n, login, nome, "editado", "Campos: " + ", ".join(campos)) for n, campos in alterados.items()]
    eventos += [projetos.evento(n, login, nome, "travado", "Edição travada novamente depois de salva") for n in travados]
    eventos += [projetos.evento(n, login, nome, "reenviado", "Ajustes enviados para nova revisão") for n in reenviados]
    registrar_historico(eventos)
    st.session_state['aviso_meus'] = (f"Alterações gravadas em {len(alterados)} projeto(s)."
                                      + (" Os projetos liberados voltaram a ficar travados." if travados else "")
                                      + (" Os ajustes foram reenviados à Planejamento para nova revisão." if reenviados else ""))
    if reenviados:
        st.session_state['docs_depois'] = (reenviados[0], "memorando_reenvio")
    st.rerun()

def pedir_liberacao(numero, motivo):
    login, nome = ator_da_sessao()
    df_atual, versao_atual = carregar_dados(usar_cache=False)
    df_novo, erro = projetos.solicitar_liberacao(df_atual, numero, login, motivo)
    if erro:
        alerta_erro(erro)
        return
    if gravar_com_aviso(df_novo, versao_atual):
        registrar_historico([projetos.evento(numero, login, nome, "liberacao_solicitada", motivo)])
        st.session_state['aviso_meus'] = "Pedido enviado à Planejamento. Você será avisado nesta tela quando a edição for liberada."
        st.rerun()

# ------------------------------------------------------------------ acompanhamento

def html_ficha_cabecalho(projeto):
    """Cabeçalho da ficha de um projeto: código, nome, gestor, unidade, prazo e etiquetas de situação."""
    chips = [etiqueta(projeto['Status']), etiqueta(situacao_da_edicao(projeto), "suave")]
    if projeto['SITUACAO_REGISTRO'] == projetos.SITUACAO_ARQUIVADO:
        chips.append(etiqueta("Arquivado", "alerta"))
    revisao = projetos.texto(projeto['REVISAO'])
    if revisao:
        chips.append(etiqueta(revisao, "ok" if revisao == projetos.REVISAO_CONCLUIDA else "atencao" if revisao in (projetos.REVISAO_DEVOLVIDO, projetos.REVISAO_REENVIADO) else "suave"))
    datas = " a ".join(d for d in (projetos.texto(projeto['INICIO_PREVISTO']), projetos.texto(projeto['TERMINO_PREVISTO'])) if d)
    return (f"<div class='ficha-projeto'><div class='codigo'>{esc(projeto['CODIGO']) or 'Sem código'}</div>"
            f"<div class='nome'>{esc(projeto['Nome da Iniciativa'])}</div>"
            f"<div class='meta'>{esc(projeto['Gestor'])} · {esc(projeto['Unidade'])}"
            f"{' · Previsto: ' + esc(datas) if datas else ''}</div><div>{''.join(chips)}</div></div>")

def mostrar_atualizacoes(abas, n):
    atualizacoes = projetos.do_projeto(abas, "Atualizacoes", n)
    if atualizacoes.empty:
        st.caption("Nenhuma atualização registrada.")
    for r in atualizacoes.itertuples():
        tom = {"Em dia": "ok", "Atenção": "atencao", "Atrasado": "alerta"}.get(r.situacao, "")
        data_br = projetos.parse_data(r.data_referencia)
        with st.container(border=True):
            st.markdown(f"**{data_br.strftime('%d/%m/%Y') if data_br else esc(r.data_referencia)}** {etiqueta(r.situacao, tom)}", unsafe_allow_html=True)
            st.markdown(f"<p class='texto-livre'>{esc(r.texto)}</p>", unsafe_allow_html=True)
            st.caption(f"{projetos.texto(r.autor_nome)}, registrado em {r.registrado_em}")

def mostrar_pareceres(abas, n):
    pareceres = projetos.do_projeto(abas, "Pareceres", n)
    if pareceres.empty:
        st.caption("Nenhum parecer registrado.")
    for r in pareceres.itertuples():
        with st.container(border=True):
            st.markdown(f"**{esc(r.conclusao) or 'Sem conclusão'}** {etiqueta(projetos.texto(r.autor_nome), 'suave')}", unsafe_allow_html=True)
            st.markdown(f"<p class='texto-livre'>{esc(r.texto)}</p>", unsafe_allow_html=True)
            st.caption(f"Registrado em {r.registrado_em}")

def tela_acompanhamento(df_completo, modo_sharepoint):
    faixa_titulo("Acompanhamento", "Atualizações, pareceres e linha do tempo de cada projeto", "timeline")
    nivel = st.session_state['nivel']
    login, nome = ator_da_sessao()
    visiveis = df_completo[df_completo['SITUACAO_REGISTRO'].isin([projetos.SITUACAO_ATIVO, projetos.SITUACAO_ARQUIVADO])]
    meus = visiveis[visiveis['Gestor'].astype(str).str.lower() == nome.lower()]
    mensagem = st.session_state.pop('aviso_acompanhamento', None)
    if mensagem:
        alerta_ok(mensagem)
    botao_documento_depois()
    if visiveis.empty:
        alerta_info("Não há projetos para acompanhar.")
        return
    aviso_planilha_interna_temporaria(modo_sharepoint)
    abas = ler_abas_ou_erro()
    if abas is None:
        return

    escopos = (["Meus projetos"] if not meus.empty else []) + ["Todo o portfólio"]
    escopo = st.radio("Projetos", escopos, horizontal=True, key="acomp_escopo")
    base = meus if escopo == "Meus projetos" else visiveis
    numeros = base['ID_PROJETO'].tolist()
    por_numero = {projetos.chave(r): r for _, r in base.iterrows()}
    escolhido = st.selectbox("Projeto", numeros, format_func=lambda n: rotulo_projeto(por_numero[n]), key="acomp_projeto")
    projeto = por_numero[escolhido]
    arquivado = projeto['SITUACAO_REGISTRO'] == projetos.SITUACAO_ARQUIVADO
    dono = projetos.texto(projeto['Gestor']).lower() == nome.lower()

    st.markdown(html_ficha_cabecalho(projeto), unsafe_allow_html=True)

    pode_atualizar = not arquivado and (projetos.pode("atualizar_qualquer_projeto", nivel) or (dono and nivel != "leitor"))
    pode_parecer = not arquivado and projetos.pode("emitir_parecer", nivel)
    ve_pareceres = dono or nivel in ("administrador", "planejamento", "comite")

    aba_atu, aba_par, aba_com, aba_dados, aba_tempo = st.tabs([
        ":material/update: Atualizações", ":material/rate_review: Pareceres", ":material/forum: Comentários",
        ":material/description: Dados completos", ":material/timeline: Linha do tempo"])

    with aba_atu:
        if pode_atualizar:
            with st.form(f"form_atualizacao_{escolhido}"):
                c1, c2 = st.columns([1, 1])
                data_ref = c1.date_input("Data de referência", value=datetime.now().date(), max_value=datetime.now().date(), format="DD/MM/YYYY")
                situacao = c2.selectbox("Situação do projeto", projetos.SITUACOES_ATUALIZACAO)
                texto_atu = st.text_area("O que aconteceu desde a última atualização", placeholder="Descreva o andamento, entregas e dificuldades.")
                if st.form_submit_button("Registrar atualização", icon=":material/add_task:", type="primary"):
                    def alterar(abas_):
                        erro = projetos.registrar_atualizacao(abas_, escolhido, data_ref, situacao, texto_atu, login, nome)
                        if erro:
                            return erro
                        projetos.acrescentar_eventos(abas_, projetos.evento(escolhido, login, nome, "atualizacao", f"{situacao}: {texto_atu.strip()[:140]}"))
                        return None
                    erro = alterar_planilha_interna(alterar)
                    if erro:
                        alerta_erro(erro)
                    else:
                        st.session_state['aviso_acompanhamento'] = "Atualização registrada."
                        st.session_state['docs_depois'] = (escolhido, "certidao_atividade")
                        st.rerun()
        elif arquivado:
            alerta_info("Projeto arquivado: não recebe novas atualizações.")
        mostrar_atualizacoes(abas, escolhido)

    with aba_par:
        if not ve_pareceres:
            st.caption("Os pareceres ficam visíveis ao gestor do projeto e à equipe de coordenação.")
        else:
            if pode_parecer:
                with st.form(f"form_parecer_{escolhido}"):
                    conclusao = st.selectbox("Conclusão (opcional)", [""] + projetos.CONCLUSOES_PARECER, format_func=lambda c: c or "Sem conclusão")
                    texto_par = st.text_area("Parecer")
                    if st.form_submit_button("Registrar parecer", icon=":material/rate_review:", type="primary"):
                        def alterar(abas_):
                            erro = projetos.registrar_parecer(abas_, escolhido, conclusao, texto_par, login, nome)
                            if erro:
                                return erro
                            projetos.acrescentar_eventos(abas_, projetos.evento(escolhido, login, nome, "parecer", conclusao or "Sem conclusão"))
                            return None
                        erro = alterar_planilha_interna(alterar)
                        if erro:
                            alerta_erro(erro)
                        else:
                            st.session_state['aviso_acompanhamento'] = "Parecer registrado."
                            st.rerun()
            mostrar_pareceres(abas, escolhido)

    with aba_com:
        bloco_comentarios(abas, projeto, "acomp", 'aviso_acompanhamento')

    with aba_dados:
        st.markdown(html_dados_completos(projeto, coordenacao=nivel in ("administrador", "planejamento", "comite")), unsafe_allow_html=True)

    with aba_tempo:
        st.markdown(html_linha_do_tempo(projetos.linha_do_tempo(abas, escolhido), projeto.get('Ano de criação')), unsafe_allow_html=True)

# ------------------------------------------------------------------ documentos para o SEI

LADOS_DOCUMENTO = {"dplan": "DPLAN", "projeto": "Unidade do projeto"}

def pedir_documentos(numero, tipo=None):
    """Vai para Documentos SEI já com o projeto (e o documento) escolhidos. Serve de on_click: o menu aplica no começo da execução."""
    st.session_state['navegar_docs'] = (str(numero), tipo)

def botao_documento_depois():
    """Depois de uma ação que costuma pedir um documento no SEI, oferece o atalho. Aparece uma vez, como os avisos."""
    depois = st.session_state.pop('docs_depois', None)
    if not depois:
        return
    numero, tipo = depois
    if tipo in documentos_sei.tipos_para(st.session_state['nivel']):
        st.button(f"Preparar: {documentos_sei.TIPOS_DOCUMENTO[tipo]['titulo']}", icon=":material/description:",
                  key=f"docs_depois_{tipo}", on_click=pedir_documentos, args=(numero, tipo))

def registrar_geracao_documento(numero, titulo, formato):
    """Roda ao baixar: deixa na linha do tempo quem gerou o documento, sem guardar o texto."""
    login, nome = ator_da_sessao()
    registrar_historico([projetos.evento(numero, login, nome, "documento_gerado", f"{titulo} ({formato})")])

def altura_da_caixa(texto):
    return max(68, min(400, 26 * (len(texto) // 85 + texto.count("\n") + 2)))

def tela_documentos_sei(df_completo, modo_sharepoint):
    faixa_titulo("Documentos SEI", "Textos e PDFs prontos para agregar ao processo no SEI", "description")
    nivel = st.session_state['nivel']
    login, nome = ator_da_sessao()
    tipos = documentos_sei.tipos_para(nivel)
    ativos = df_completo[df_completo['SITUACAO_REGISTRO'] == projetos.SITUACAO_ATIVO]
    base = ativos if projetos.pode("documentos_dplan", nivel) else ativos[ativos['Gestor'].astype(str).str.lower() == nome.lower()]
    if base.empty:
        alerta_info("Não há projetos ativos sob a sua responsabilidade para gerar documentos.")
        return
    aviso_planilha_interna_temporaria(modo_sharepoint)
    abas = ler_abas_ou_erro()
    if abas is None:
        return

    por_n = {projetos.chave(r): r for _, r in base.iterrows()}
    ids = list(por_n)
    if st.session_state.get('docs_projeto') not in ids:
        st.session_state.pop('docs_projeto', None)
    escolhido = st.selectbox("Projeto", ids, format_func=lambda n: rotulo_projeto(por_n[n]), key="docs_projeto")
    projeto = por_n[escolhido]
    st.markdown(html_ficha_cabecalho(projeto), unsafe_allow_html=True)

    sugerido = documentos_sei.sugerido(projeto, nivel)
    if st.session_state.get('docs_tipo') not in tipos:
        st.session_state['docs_tipo'] = sugerido
    dois_lados = len({documentos_sei.TIPOS_DOCUMENTO[t]['lado'] for t in tipos}) > 1

    def rotulo_tipo(t):
        modelo_t = documentos_sei.TIPOS_DOCUMENTO[t]
        return f"{LADOS_DOCUMENTO[modelo_t['lado']]}: {modelo_t['titulo']}" if dois_lados else modelo_t['titulo']

    tipo = st.selectbox("Documento", tipos, format_func=rotulo_tipo, key="docs_tipo")
    modelo = documentos_sei.TIPOS_DOCUMENTO[tipo]
    if sugerido and sugerido != tipo:
        st.caption(f"Sugerido para este projeto agora: {documentos_sei.TIPOS_DOCUMENTO[sugerido]['titulo']}.")
    st.caption(f"Quando usar: {modelo['momento']}")
    if modelo.get('aviso'):
        alerta_aviso(modelo['aviso'])

    padrao_inicial = documentos_sei.campos_padrao(tipo, projeto, abas, nome)
    escolhidos = {}
    for campo in modelo['campos']:
        if campo['tipo'] == 'escolha':
            inicial = padrao_inicial.get(campo['chave'])
            escolhidos[campo['chave']] = st.radio(campo['rotulo'], campo['opcoes'], horizontal=True,
                                                  index=campo['opcoes'].index(inicial) if inicial in campo['opcoes'] else 0,
                                                  key=f"docs_{escolhido}_{tipo}_{campo['chave']}")
    padrao = documentos_sei.campos_padrao(tipo, projeto, abas, nome, escolhidos=escolhidos)
    chave_base = f"docs_{escolhido}_{tipo}_" + "_".join(escolhidos.values())
    valores = dict(escolhidos)
    with st.expander("Dados do documento", icon=":material/tune:", expanded=True):
        for campo in modelo['campos']:
            if campo['tipo'] == 'escolha':
                continue
            chave_campo = f"{chave_base}_{campo['chave']}"
            if campo['tipo'] == 'atualizacao':
                opcoes = documentos_sei.opcoes_atualizacoes(abas, escolhido)
                if opcoes:
                    valores[campo['chave']] = st.selectbox(campo['rotulo'], list(opcoes), format_func=opcoes.get, key=chave_campo)
                else:
                    st.caption("Nenhuma atividade registrada no Acompanhamento. A Certidão usa a data de hoje; descreva a atividade na caixa de texto abaixo.")
            elif campo['tipo'] == 'data':
                dia = st.date_input(campo['rotulo'], value=projetos.parse_data(padrao[campo['chave']]), format="DD/MM/YYYY", key=chave_campo)
                valores[campo['chave']] = dia.isoformat() if dia else ""
            else:
                valores[campo['chave']] = st.text_input(campo['rotulo'], value=padrao[campo['chave']], help=campo['ajuda'] or None, key=chave_campo)

    doc = documentos_sei.montar(tipo, projeto, abas, campos=valores)
    digest = format(zlib.crc32(repr(sorted(valores.items())).encode("utf-8")), "08x")  # refaz as caixas quando os dados mudam
    aba_editar, aba_texto, aba_pdf = st.tabs([":material/edit: Editar o texto", ":material/content_copy: Copiar para o SEI", ":material/picture_as_pdf: PDF"])

    with aba_editar:
        st.caption("O texto vem dos dados do projeto. Ajuste o que precisar. Se mudar os dados acima, o texto é refeito a partir deles.")
        if doc.assunto:
            doc.assunto = st.text_input("Assunto", value=doc.assunto, key=f"{chave_base}_{digest}_assunto")
        novos = []
        for i, bloco in enumerate(doc.blocos):
            rotulo = (bloco[1] if bloco[0] == "campo" else "Lista (um item por linha)" if bloco[0] == "lista"
                      else "Título" if bloco[0] == "titulo" else f"Parágrafo {i + 1}")
            inicial = documentos_sei.bloco_para_texto(bloco)
            editado = st.text_area(rotulo, value=inicial, height=altura_da_caixa(inicial), key=f"{chave_base}_{digest}_b{i}")
            novos.append(documentos_sei.texto_para_bloco(bloco, editado))
        doc.blocos = novos

    texto_sei = documentos_sei.para_texto(doc)
    alertas = documentos_sei.alertas_dados_pessoais(texto_sei)
    if alertas:
        alerta_aviso(f"O texto parece conter {', '.join(alertas)}. Retire esses dados antes de usar o documento: o SGPP acompanha projetos, não pessoas.")
    faltam = documentos_sei.trechos_a_preencher(doc)
    if faltam:
        alerta_info(f"{faltam} trecho(s) ainda marcado(s) com (a preencher: ...). Escreva cada um em Editar o texto antes de usar o documento.")

    with aba_texto:
        st.caption(f"No SEI: Incluir Documento, tipo {modelo['tipo_sei']}. Cole o texto no editor. Número, assinatura e código verificador "
                   "o próprio SEI põe. Use o ícone de copiar no canto da caixa.")
        st.code(texto_sei, language=None, wrap_lines=True)
        st.download_button("Baixar em HTML", data=documentos_sei.para_html(doc).encode("utf-8"), icon=":material/code:",
                           file_name=documentos_sei.nome_do_arquivo(doc, projeto, "html"), mime="text/html", key=f"docs_html_{escolhido}_{tipo}",
                           on_click=registrar_geracao_documento, args=(escolhido, modelo['titulo'], "HTML"),
                           help="Para colar no editor do SEI ou numa extensão que insere HTML.")

    with aba_pdf:
        modos = {"minuta": "Minuta de conferência (sem número nem assinatura)",
                 "externo": "Documento externo (com local, data e linha de assinatura)"}
        modo = st.radio("Tipo de PDF", list(modos), format_func=modos.get, key="docs_modo")
        st.caption("Documento criado no SEI recebe número e assinatura do próprio SEI. O PDF serve para conferir o texto ou, no modo externo, "
                   "para incluir como documento externo. Confirme no SEI do MPAM como ele trata um PDF externo antes de adotar esse modo.")
        st.download_button("Baixar PDF", data=documentos_sei.para_pdf(doc, modo), icon=":material/download:", type="primary",
                           file_name=documentos_sei.nome_do_arquivo(doc, projeto, "pdf"), mime="application/pdf",
                           key=f"docs_pdf_{escolhido}_{tipo}", on_click=registrar_geracao_documento,
                           args=(escolhido, modelo['titulo'], "PDF"))

# ------------------------------------------------------------------ revisão (Planejamento)

GRUPOS_FICHA = [
    ("Identificação", [("CODIGO", "Código"), ("Nº", "Nº"), ("Nome da Iniciativa", "Nome"), ("Projeto/Programa/Boa Prática", "Tipo"),
                       ("Área de Atuação", "Área de atuação"), ("Unidade", "Unidade"), ("Município", "Município"), ("Gestor", "Gestor")]),
    ("Alinhamento", [("Alinhamento Estratégico", "Alinhamento estratégico"), ("Alinhamento ao PEN", "Alinhamento ao PEN"),
                     ("Institucionalizado", "Institucionalizado"), ("Ato PGJ", "Ato PGJ"), ("Ano de criação", "Ano de criação")]),
    ("Processo e prazos", [("SEI", "Nº SEI"), ("Link", "Link"), ("Status", "Status"),
                           ("INICIO_PREVISTO", "Início previsto"), ("TERMINO_PREVISTO", "Término previsto")]),
    ("Descrição", [("Ementa (Objetivo)", "Ementa (objetivo)"), ("Descrição do Projeto", "Descrição do projeto")]),
]
GRUPO_CONTROLE = ("Controle (coordenação)", [
    ("SITUACAO_REGISTRO", "Situação do registro"), ("EDICAO", "Edição"), ("REVISAO", "Revisão"), ("ENVIADO_POR", "Enviado por"),
    ("ENVIADO_EM", "Enviado em"), ("AVALIAÇÃO", "Avaliação da DPLAN"), ("OBSERVAÇÕES/CORREÇÕES", "Observações da DPLAN"),
    ("AUDITOR_DPLAN", "Avaliado por"),
])
CAMPOS_LARGOS = ("Ementa (Objetivo)", "Descrição do Projeto", "Nome da Iniciativa", "OBSERVAÇÕES/CORREÇÕES", "Alinhamento Estratégico")

def valor_da_ficha(coluna, valor):
    t = projetos.texto(valor)
    if t and coluna in ("Nº", "Ano de criação"):
        try:
            return str(int(float(t)))
        except ValueError:
            return t
    return t

def html_dados_completos(linha, coordenacao=False):
    """Todos os dados do projeto, em seções. Todo valor é escapado; campos em branco aparecem como 'não informado'."""
    grupos = GRUPOS_FICHA + ([GRUPO_CONTROLE] if coordenacao else [])
    secoes = []
    for titulo, campos in grupos:
        itens = []
        for coluna, rotulo in campos:
            if coluna not in linha.index and coluna not in ("Link", "Descrição do Projeto"):
                continue
            valor = valor_da_ficha(coluna, linha.get(coluna))
            conteudo = esc(valor) if valor else "<span class='vazio'>não informado</span>"
            largo = " largo" if coluna in CAMPOS_LARGOS else ""
            itens.append(f"<div class='campo{largo}'><dt>{esc(rotulo)}</dt><dd>{conteudo}</dd></div>")
        secoes.append(f"<section class='ficha-secao'><div class='ficha-titulo'>{esc(titulo)}</div><dl>{''.join(itens)}</dl></section>")
    return f"<div class='ficha-completa'>{''.join(secoes)}</div>"

def html_comentarios(itens, eu=None):
    if not itens:
        return "<p class='linha-tempo-vazia'>Nenhum comentário ainda.</p>"
    partes = []
    for c in itens:
        proprio = " proprio" if eu and c['autor_login'] == eu else ""
        texto_c = esc(c['texto']) or "<span class='vazio'>Sem observações adicionais.</span>"
        marca = f" {etiqueta(c['rotulo'], 'atencao' if c['tipo'] == 'devolucao' else 'ok' if c['tipo'] == 'conclusao' else 'suave')}" if c['tipo'] != "comentario" else ""
        partes.append(f"<li class='comentario{proprio}'><div class='cab'><b>{esc(c['autor_nome'])}</b>{marca}<span>{esc(c['quando'])}</span></div>"
                      f"<p class='texto-livre'>{texto_c}</p></li>")
    return f"<ol class='fio-comentarios'>{''.join(partes)}</ol>"

def erro_comentario(tipo, texto_comentario):
    """Valida o texto antes de qualquer gravação, para uma ação não ficar pela metade."""
    vazio = {"Comentarios": pd.DataFrame(columns=projetos.COLUNAS_COMENTARIOS)}
    return projetos.registrar_comentario(vazio, "0", tipo, texto_comentario, "x", "x")

def registrar_historico(eventos, comentarios=()):
    """Grava eventos (e comentários) na planilha interna. Se falhar, avisa sem desfazer a ação principal, que já foi gravada.

    `comentarios` é uma lista de (numero_do_projeto, tipo, texto) escritos em nome de quem está na sessão.
    """
    login, nome = ator_da_sessao()

    def alterar(abas):
        projetos.acrescentar_eventos(abas, eventos)
        for numero, tipo, texto_c in comentarios:
            erro = projetos.registrar_comentario(abas, numero, tipo, texto_c, login, nome)
            if erro:
                return erro
        return None

    erro = alterar_planilha_interna(alterar)
    if erro:
        alerta_aviso(f"A ação foi feita, mas o histórico e os comentários não puderam ser gravados: {erro}")

def comentar_no_projeto(numero, texto_comentario, aviso_em):
    login, nome = ator_da_sessao()
    erro = erro_comentario("comentario", texto_comentario)
    if erro:
        alerta_erro(erro)
        return
    registrar_historico([projetos.evento(numero, login, nome, "comentario", texto_comentario.strip()[:140])], [(numero, "comentario", texto_comentario)])
    st.session_state[aviso_em] = "Comentário enviado."
    st.rerun()

def bloco_comentarios(abas, linha, chave, aviso_em):
    """Fio de comentários do projeto e, para quem pode, o campo para comentar."""
    login, nome = ator_da_sessao()
    n = projetos.chave(linha)
    if not projetos.pode_comentar(st.session_state['nivel'], nome, linha['Gestor']):
        st.caption("Os comentários ficam visíveis ao gestor do projeto e à equipe de coordenação.")
        return
    st.markdown(html_comentarios(projetos.comentarios_do_projeto(abas, n), login), unsafe_allow_html=True)
    novo = st.text_area("Novo comentário", key=f"com_{chave}_{n}")
    if st.button("Enviar comentário", icon=":material/send:", key=f"comentar_{chave}_{n}"):
        comentar_no_projeto(n, novo, aviso_em)

# ------------------------------------------------------------------ revisão (Planejamento)

def decidir_edicao(funcao, numero, tipo_evento, detalhe, mensagem, comentario="", exigir_comentario=False):
    """Libera, nega ou trava a edição: grava na planilha de projetos e registra no histórico (com comentário, se houver)."""
    login, nome = ator_da_sessao()
    comentario = comentario.strip()
    if exigir_comentario or comentario:
        erro = erro_comentario("comentario", comentario)
        if erro:
            alerta_erro(("Explique o motivo ao gestor: " if exigir_comentario else "") + erro)
            return
    df_atual, versao_atual = carregar_dados(usar_cache=False)
    df_novo, erro = funcao(df_atual, numero)
    if erro:
        alerta_erro(erro)
        return
    if gravar_com_aviso(df_novo, versao_atual):
        registrar_historico([projetos.evento(numero, login, nome, tipo_evento, comentario[:140] or detalhe)],
                            [(numero, "comentario", comentario)] if comentario else [])
        st.session_state['aviso_revisao'] = mensagem
        st.rerun()

def acao_revisao(numero, acao, comentario):
    """Concluir a revisão, devolver para ajustes ou só comentar. Devolver exige explicar o que ajustar."""
    login, nome = ator_da_sessao()
    tipo = {"concluir": "conclusao", "devolver": "devolucao", "comentar": "comentario"}[acao]
    erro = erro_comentario(tipo, comentario)
    if erro:
        alerta_erro(erro)
        return
    if acao != "comentar":
        funcao = projetos.concluir_revisao if acao == "concluir" else projetos.devolver_para_ajustes
        df_atual, versao_atual = carregar_dados(usar_cache=False)
        df_novo, erro = funcao(df_atual, numero)
        if erro:
            alerta_erro(erro)
            return
        if not gravar_com_aviso(df_novo, versao_atual):
            return
    tipo_evento = {"concluir": "revisao_concluida", "devolver": "devolvido", "comentar": "comentario"}[acao]
    detalhe = comentario.strip()[:140] or ("Sem observações adicionais" if acao == "concluir" else "")
    # a conclusão sem texto também entra no fio, como 'Revisão concluída'
    registrar_historico([projetos.evento(numero, login, nome, tipo_evento, detalhe)], [(numero, tipo, comentario)])
    st.session_state['aviso_revisao'] = {"concluir": "Revisão concluída.", "devolver": "Projeto devolvido ao gestor para ajustes.",
                                         "comentar": "Comentário enviado."}[acao]
    if acao == "devolver":
        st.session_state['docs_depois'] = (numero, "memorando_devolucao")
    elif acao == "concluir":
        st.session_state['docs_depois'] = (numero, "parecer_tecnico")
    st.rerun()

def mudar_arquivamento(numero, arquivar, motivo=""):
    login, nome = ator_da_sessao()
    df_atual, versao_atual = carregar_dados(usar_cache=False)
    df_novo, erro = projetos.arquivar_projeto(df_atual, numero, motivo) if arquivar else projetos.reativar_projeto(df_atual, numero)
    if erro:
        alerta_erro(erro)
        return
    if gravar_com_aviso(df_novo, versao_atual):
        registrar_historico([projetos.evento(numero, login, nome, "arquivado" if arquivar else "reativado", motivo.strip())])
        st.session_state['aviso_revisao'] = "Projeto arquivado." if arquivar else "Projeto reativado."
        st.rerun()

def painel_revisao_projeto(linha, abas, chave):
    """Tudo o que a Planejamento precisa para revisar um projeto: dados completos, comentários e as ações."""
    n = projetos.chave(linha)
    with st.expander("Ver o projeto inteiro", icon=":material/description:"):
        st.markdown(html_dados_completos(linha, coordenacao=True), unsafe_allow_html=True)
    st.markdown("**Comentários com o gestor**")
    st.markdown(html_comentarios(projetos.comentarios_do_projeto(abas, n), st.session_state['login_rede']), unsafe_allow_html=True)
    texto_c = st.text_area("Comentário ou orientação para o gestor", key=f"rev_texto_{chave}_{n}",
                           help="Para devolver o projeto, explique o que precisa ser ajustado.")
    b1, b2, b3, _ = st.columns([1.1, 1.35, 1, 1.2])
    if b1.button("Concluir revisão", icon=":material/task_alt:", type="primary", key=f"concluir_{chave}_{n}"):
        acao_revisao(n, "concluir", texto_c)
    if b2.button("Devolver para ajustes", icon=":material/undo:", key=f"devolver_{chave}_{n}"):
        acao_revisao(n, "devolver", texto_c)
    if b3.button("Só comentar", icon=":material/comment:", key=f"so_comentar_{chave}_{n}"):
        acao_revisao(n, "comentar", texto_c)

def tela_revisao(df_completo, modo_sharepoint):
    faixa_titulo("Revisão", "Revise os projetos enviados, comente, devolva para ajustes e libere edições", "rate_review")
    mensagem = st.session_state.pop('aviso_revisao', None)
    if mensagem:
        alerta_ok(mensagem)
    botao_documento_depois()
    aviso_planilha_interna_temporaria(modo_sharepoint)
    abas = ler_abas_ou_erro()
    if abas is None:
        return
    df = projetos.garantir_colunas(df_completo)
    fila = projetos.para_revisar(df)
    pendentes = projetos.pedidos_pendentes(df)
    arquivados = df[df['SITUACAO_REGISTRO'] == projetos.SITUACAO_ARQUIVADO]
    ativos = df[df['SITUACAO_REGISTRO'] == projetos.SITUACAO_ATIVO]
    com_gestor = ativos[ativos['REVISAO'] == projetos.REVISAO_DEVOLVIDO]

    aba_fila, aba_gestor, aba_pedidos, aba_projetos, aba_arquivo = st.tabs([
        f":material/inbox: Para revisar ({len(fila)})", f":material/undo: Com o gestor ({len(com_gestor)})",
        f":material/lock_open: Pedidos de liberação ({len(pendentes)})",
        ":material/folder_open: Projetos", f":material/inventory_2: Arquivo ({len(arquivados)})"])

    with aba_gestor:
        st.caption("Projetos devolvidos para ajustes. Aqui você acompanha as respostas do gestor e pode comentar de novo.")
        if com_gestor.empty:
            st.caption("Nenhum projeto devolvido aguardando o gestor.")
        for _, linha in com_gestor.iterrows():
            with st.container(border=True):
                st.markdown(f"**{esc(rotulo_projeto(linha))}**  \n{esc(linha['Gestor'])} {etiqueta(linha['REVISAO'], 'atencao')}", unsafe_allow_html=True)
                painel_revisao_projeto(linha, abas, "gestor")

    with aba_fila:
        st.caption("Projetos recém-enviados e projetos cujos ajustes o gestor reenviou.")
        if fila.empty:
            st.caption("Nenhum projeto aguardando revisão.")
        for _, linha in fila.iterrows():
            with st.container(border=True):
                st.markdown(f"**{esc(rotulo_projeto(linha))}**  \n{esc(linha['Gestor'])} · enviado em {esc(linha['ENVIADO_EM'])} "
                            f"{etiqueta(linha['REVISAO'], 'atencao' if linha['REVISAO'] == projetos.REVISAO_REENVIADO else 'suave')}", unsafe_allow_html=True)
                painel_revisao_projeto(linha, abas, "fila")

    with aba_pedidos:
        if pendentes.empty:
            st.caption("Nenhum pedido aguardando.")
        for _, linha in pendentes.iterrows():
            pedido = projetos.parse_pedido(linha['PEDIDO_LIBERACAO'])
            n = projetos.chave(linha)
            with st.container(border=True):
                st.markdown(f"**{esc(rotulo_projeto(linha))}**  \n{esc(linha['Gestor'])} pediu em {esc(pedido['quando'])}")
                st.markdown(f"<p class='texto-livre'>{esc(pedido['motivo'])}</p>", unsafe_allow_html=True)
                with st.expander("Ver o projeto inteiro", icon=":material/description:"):
                    st.markdown(html_dados_completos(linha, coordenacao=True), unsafe_allow_html=True)
                resposta = st.text_input("Comentário para o gestor (obrigatório para negar)", key=f"cm_ped_{n}")
                b1, b2, _ = st.columns([1, 1, 3])
                if b1.button("Liberar", icon=":material/lock_open:", type="primary", key=f"liberar_{n}"):
                    decidir_edicao(projetos.liberar_edicao, n, "edicao_liberada", f"Pedido de {pedido['login']}",
                                   f"Edição de {rotulo_projeto(linha)} liberada.", resposta)
                if b2.button("Negar", icon=":material/close:", key=f"negar_{n}"):
                    decidir_edicao(projetos.negar_liberacao, n, "liberacao_negada", f"Pedido de {pedido['login']}",
                                   "Pedido negado.", resposta, exigir_comentario=True)

    with aba_projetos:
        if ativos.empty:
            st.caption("Não há projetos ativos.")
        else:
            por_n = {projetos.chave(r): r for _, r in ativos.iterrows()}
            alvo = st.selectbox("Projeto", list(por_n), key="revisao_alvo",
                                format_func=lambda n: f"{rotulo_projeto(por_n[n])} ({projetos.texto(por_n[n]['REVISAO']) or 'sem revisão'}, {situacao_da_edicao(por_n[n]).lower()})")
            painel_revisao_projeto(por_n[alvo], abas, "proj")
            st.markdown("## Edição do projeto")
            b1, b2, _ = st.columns([1, 1, 2])
            if b1.button("Liberar edição", icon=":material/lock_open:", key="liberar_direto"):
                decidir_edicao(projetos.liberar_edicao, alvo, "edicao_liberada", "Liberada pela Planejamento", "Edição liberada.")
            if b2.button("Travar edição", icon=":material/lock:", key="travar_direto"):
                decidir_edicao(projetos.travar_projeto, alvo, "travado", "Travada pela Planejamento", "Edição travada.")

    with aba_arquivo:
        st.markdown("## Arquivar um projeto")
        if ativos.empty:
            st.caption("Não há projetos ativos.")
        else:
            por_n_ativo = {projetos.chave(r): r for _, r in ativos.iterrows()}
            alvo_arq = st.selectbox("Projeto", list(por_n_ativo), format_func=lambda n: rotulo_projeto(por_n_ativo[n]), key="arquivar_alvo")
            motivo_arq = st.text_input("Motivo do arquivamento *", key="arquivar_motivo")
            if st.button("Arquivar projeto", icon=":material/inventory_2:", key="arquivar_projeto"):
                mudar_arquivamento(alvo_arq, True, motivo_arq)

        st.markdown("## Projetos arquivados")
        if arquivados.empty:
            st.caption("Nenhum projeto arquivado.")
        else:
            resumos = {projetos.chave(r): projetos.resumo_arquivamento(abas, projetos.chave(r)) for _, r in arquivados.iterrows()}
            tabela = pd.DataFrame({
                "Código": arquivados['CODIGO'].tolist(), "Projeto": arquivados['Nome da Iniciativa'].tolist(),
                "Enviado em": [resumos[n]['enviado_em'] for n in arquivados['ID_PROJETO']],
                "Arquivado em": [resumos[n]['arquivado_em'] for n in arquivados['ID_PROJETO']],
                "Por": [resumos[n]['arquivado_por'] for n in arquivados['ID_PROJETO']],
                "Dias ativo": [resumos[n]['dias'] for n in arquivados['ID_PROJETO']],
                "Motivo": [resumos[n]['motivo'] for n in arquivados['ID_PROJETO']],
            })
            st.dataframe(tabela, use_container_width=True, hide_index=True)
            por_n_arq = {projetos.chave(r): r for _, r in arquivados.iterrows()}
            ver = st.selectbox("Ver a linha do tempo de", list(por_n_arq), format_func=lambda n: rotulo_projeto(por_n_arq[n]), key="arquivo_ver")
            st.markdown(html_linha_do_tempo(projetos.linha_do_tempo(abas, ver), por_n_arq[ver].get('Ano de criação')), unsafe_allow_html=True)
            if st.button("Reativar projeto", icon=":material/unarchive:", type="primary", key="reativar_projeto"):
                mudar_arquivamento(ver, False)

# ------------------------------------------------------------------ retornos da Planejamento (Meus Projetos)

def bloco_retornos_gestor(df_meus):
    """Mostra ao gestor o que a Planejamento comentou, devolveu ou concluiu nos projetos dele, e deixa responder."""
    login, nome = ator_da_sessao()
    abas = ler_abas_ou_erro()
    if abas is None:
        return
    itens = []
    for _, linha in df_meus.iterrows():
        n = projetos.chave(linha)
        fio = projetos.comentarios_do_projeto(abas, n)
        devolvido = projetos.texto(linha['REVISAO']) == projetos.REVISAO_DEVOLVIDO
        if devolvido or any(c['autor_login'] != login for c in fio):
            itens.append((n, linha, fio, devolvido))
    if not itens:
        return
    st.markdown("## Retornos da Planejamento")
    devolvidos = [i for i in itens if i[3]]
    if devolvidos:
        alerta_aviso(f"{len(devolvidos)} projeto(s) devolvido(s) para ajustes. Altere o que foi pedido na tabela de edição abaixo e "
                     "salve: o projeto volta para a revisão da Planejamento.")
    for n, linha, fio, devolvido in itens:
        estado = projetos.texto(linha['REVISAO']) or "sem revisão"
        with st.expander(f"{rotulo_projeto(linha)} ({estado})", expanded=devolvido):
            st.markdown(html_comentarios(fio, login), unsafe_allow_html=True)
            resposta = st.text_area("Responder à Planejamento", key=f"resp_{n}")
            if st.button("Enviar resposta", icon=":material/reply:", key=f"enviar_resp_{n}"):
                comentar_no_projeto(n, resposta, 'aviso_meus')

# ------------------------------------------------------------------ quadro (kanban)

def mover_cartao(numero, destino):
    """Muda o status de um projeto pelo quadro: uma gravação com controle de versão e um evento no histórico."""
    login, nome = ator_da_sessao()
    df_atual, versao_atual = carregar_dados(usar_cache=False)
    df_novo, anterior, voltou, reenviado, erro = projetos.mover_status(df_atual, numero, destino, st.session_state['nivel'], nome)
    if erro:
        alerta_erro(erro)
        return
    if gravar_com_aviso(df_novo, versao_atual):
        eventos = [projetos.evento(numero, login, nome, "editado", f"Status: de {anterior or 'em branco'} para {destino}")]
        if voltou:
            eventos.append(projetos.evento(numero, login, nome, "travado", "Edição travada novamente depois de salva"))
        if reenviado:
            eventos.append(projetos.evento(numero, login, nome, "reenviado", "Ajustes enviados para nova revisão"))
        registrar_historico(eventos)
        st.session_state['aviso_quadro'] = f"Projeto movido para {destino}."
        st.rerun()

def prazo_vencido(linha):
    termino = projetos.parse_data(linha.get('TERMINO_PREVISTO'))
    return bool(termino and termino < datetime.now().date() and projetos.texto(linha.get('Status')) in ("Em elaboração", "Em execução"))

def tela_quadro(df_raw):
    faixa_titulo("Quadro", "Os projetos por status: veja a ficha de um cartão ou mova-o para mudar o status", "view_kanban")
    nivel = st.session_state['nivel']
    nome = st.session_state['nome']
    mensagem = st.session_state.pop('aviso_quadro', None)
    if mensagem:
        alerta_ok(mensagem)
    meus = df_raw[df_raw['Gestor'].astype(str).str.lower() == nome.lower()]
    escopos = ["Todo o portfólio"] + (["Meus projetos"] if not meus.empty else [])
    escopo = st.radio("Projetos", escopos, horizontal=True, key="quadro_escopo")
    base = filtrar_tabela(meus if escopo == "Meus projetos" else df_raw, "quadro", "Filtrar os cartões")
    if base.empty:
        alerta_info("Nenhum projeto para o filtro escolhido.")
        return
    base = base.assign(_coluna=base['Status'].map(projetos.coluna_do_quadro))
    if not any(projetos.pode_mover_status(linha, nivel, nome)[0] for _, linha in base.iterrows()):
        st.caption("Você pode consultar o quadro, mas não tem projetos que possa mover. Para mudar o status, peça ao gestor ou à Planejamento.")

    colunas = st.columns(len(projetos.COLUNAS_QUADRO), gap="small")
    for coluna_quadro, destino_ui in zip(projetos.COLUNAS_QUADRO, colunas):
        cartoes = base[base['_coluna'] == coluna_quadro]
        destino_ui.markdown(f"<div class='quadro-titulo'>{esc(coluna_quadro)}<span>{len(cartoes)}</span></div>", unsafe_allow_html=True)
        with destino_ui.container(height=620, border=False):
            if cartoes.empty:
                st.caption("Nenhum projeto.")
            for _, linha in cartoes.iterrows():
                n = projetos.chave(linha)
                status = projetos.texto(linha['Status'])
                chips = []
                if coluna_quadro == projetos.COLUNA_OUTROS:
                    chips.append(etiqueta(status, "suave") if status else etiqueta("Sem status", "atencao"))
                edicao = situacao_da_edicao(linha)
                if edicao != "Livre":
                    chips.append(etiqueta(edicao, "atencao" if edicao.startswith("Pedido") else "suave"))
                if projetos.texto(linha['REVISAO']) in (projetos.REVISAO_DEVOLVIDO, projetos.REVISAO_REENVIADO):
                    chips.append(etiqueta(linha['REVISAO'], "atencao"))
                if prazo_vencido(linha):
                    chips.append(etiqueta("Prazo vencido", "alerta"))
                with st.container(border=True):
                    st.markdown(
                        f"<div class='cartao-kanban'><div class='codigo'>{esc(linha['CODIGO']) or 'Sem código'}</div>"
                        f"<div class='nome'>{esc(linha['Nome da Iniciativa']) or 'Sem nome'}</div>"
                        f"<div class='meta'>{esc(linha['Gestor']) or 'Sem gestor'} · {esc(linha['Unidade']) or 'Sem unidade'}</div>"
                        f"<div>{''.join(chips)}</div></div>", unsafe_allow_html=True)
                    # Um embaixo do outro: o cartão é estreito e os rótulos lado a lado ficavam cortados
                    if st.button("Ver ficha", icon=":material/visibility:", key=f"ver_{n}", use_container_width=True,
                                 help="Abrir a ficha completa do projeto"):
                        abrir_ficha(n)
                    if projetos.pode_mover_status(linha, nivel, nome)[0]:
                        with st.popover("Mover para", icon=":material/swap_horiz:", use_container_width=True):
                            for i, destino in enumerate(projetos.STATUS):
                                if destino != status and st.button(destino, key=f"mv_{n}_{i}", use_container_width=True):
                                    mover_cartao(n, destino)

# ------------------------------------------------------------------ pendências

def tela_pendencias(df_completo):
    faixa_titulo("Pendências", "Projetos com dados em branco ou que pedem atenção", "checklist")
    detalhe = projetos.pendencias_detalhadas(df_completo)
    ativos = int((df_completo['SITUACAO_REGISTRO'] == projetos.SITUACAO_ATIVO).sum())
    com_obrigatoria = detalhe.loc[detalhe['gravidade'] == "Obrigatório", 'n'].nunique()
    com_alguma = detalhe['n'].nunique()
    m1, m2, m3 = st.columns(3)
    m1.metric("Projetos ativos", ativos)
    m2.metric("Com campo obrigatório em branco", com_obrigatoria)
    m3.metric("Sem nenhuma pendência", ativos - com_alguma)
    st.caption("Campos obrigatórios: nome, tipo, área de atuação, unidade, município, gestor, ementa e status. "
               "Corrija no Painel de Gestão ou peça ao gestor, em Meus Projetos.")

    if detalhe.empty:
        alerta_ok("Nenhum projeto ativo tem pendências.")
        return

    st.markdown("## Por tipo de pendência")
    resumo = projetos.resumo_pendencias(df_completo)
    st.dataframe(resumo, use_container_width=True, hide_index=True,
                 column_config={'gravidade': 'Gravidade', 'categoria': 'Pendência', 'projetos': 'Projetos'})

    st.markdown("## Projetos")
    f1, f2 = st.columns(2)
    gravidades = f1.multiselect("Gravidade", projetos.GRAVIDADES, default=["Obrigatório", "Atenção"], key="pend_gravidade")
    categorias = f2.multiselect("Tipo de pendência", sorted(detalhe['categoria'].unique()), key="pend_categoria")
    busca = st.text_input("Buscar por projeto, gestor ou unidade", key="pend_busca")
    filtrado = detalhe[detalhe['gravidade'].isin(gravidades)]
    if categorias:
        filtrado = filtrado[filtrado['categoria'].isin(categorias)]
    if busca.strip():
        alvo = (filtrado['projeto'] + " " + filtrado['gestor'] + " " + filtrado['unidade']).str.contains(busca.strip(), case=False, regex=False)
        filtrado = filtrado[alvo]
    if filtrado.empty:
        st.caption("Nenhuma pendência para o filtro escolhido.")
        return
    agrupado = (filtrado.groupby('n', sort=False)
                .agg(codigo=('codigo', 'first'), projeto=('projeto', 'first'), gestor=('gestor', 'first'), unidade=('unidade', 'first'),
                     gravidade=('gravidade', lambda g: min(g, key=projetos.GRAVIDADES.index)),
                     pendencias=('detalhe', lambda d: "; ".join(d)), qtd=('detalhe', 'size'))
                .reset_index(drop=True))
    agrupado = agrupado.assign(_g=agrupado['gravidade'].map(projetos.GRAVIDADES.index)).sort_values(['_g', 'qtd'], ascending=[True, False], kind="stable").drop(columns='_g')
    st.caption(f"{len(agrupado)} projeto(s) e {len(filtrado)} pendência(s) no filtro.")
    st.dataframe(agrupado, use_container_width=True, hide_index=True,
                 column_config={'codigo': 'Código', 'projeto': 'Projeto', 'gestor': 'Gestor', 'unidade': 'Unidade',
                                'gravidade': 'Gravidade', 'pendencias': 'Pendências', 'qtd': 'Qtd'})
    st.download_button("Baixar lista (.csv)", filtrado.drop(columns='n').to_csv(index=False).encode('utf-8'),
                       "PENDENCIAS_MPAM.csv", "text/csv", icon=":material/download:", key="baixar_pendencias")

def abrir_ficha(id_projeto):
    """Pede a abertura da ficha: quem a abre é tela_principal, na próxima execução do script."""
    st.session_state['ficha_pendente'] = str(id_projeto)
    st.rerun()

def ir_para_acompanhamento(id_projeto):
    """Vai para a tela Acompanhamento já com o projeto escolhido. Aplicado por tela_principal, antes de o menu existir."""
    st.session_state['navegar_para'] = str(id_projeto)
    st.rerun()

@st.dialog("Ficha do projeto", width="large")
def dialogo_ficha(id_projeto):
    """Tudo sobre um projeto, só para consulta: dados, atualizações, pareceres, comentários e linha do tempo.
    Quem pode agir (atualizar, comentar, emitir parecer) faz isso no Acompanhamento, que a ficha abre."""
    df_completo, _ = carregar_dados()
    achado = df_completo[df_completo['ID_PROJETO'] == str(id_projeto)] if not df_completo.empty else df_completo
    achado = achado[achado['SITUACAO_REGISTRO'].isin([projetos.SITUACAO_ATIVO, projetos.SITUACAO_ARQUIVADO])] if not achado.empty else achado
    if achado.empty:
        alerta_erro("Projeto não encontrado. Ele pode ter sido excluído.")
        return
    projeto = achado.iloc[0]
    nivel = st.session_state['nivel']
    nome = st.session_state['nome']
    n = projetos.chave(projeto)
    coordenacao = nivel in ("administrador", "planejamento", "comite")
    dono = projetos.texto(projeto['Gestor']).lower() == nome.lower()
    st.markdown(html_ficha_cabecalho(projeto), unsafe_allow_html=True)
    sei = projetos.texto(projeto['SEI'])
    if sei:
        st.caption("Nº SEI do projeto (use o ícone de copiar):")
        st.code(sei, language=None)

    abas = ler_abas_ou_erro()
    rotulos = [":material/description: Dados completos", ":material/update: Atualizações"]
    if dono or coordenacao:
        rotulos.append(":material/rate_review: Pareceres")
    if projetos.pode_comentar(nivel, nome, projeto['Gestor']):
        rotulos.append(":material/forum: Comentários")
    rotulos.append(":material/timeline: Linha do tempo")
    abas_ui = dict(zip(rotulos, st.tabs(rotulos)))

    with abas_ui[rotulos[0]]:
        st.markdown(html_dados_completos(projeto, coordenacao=coordenacao), unsafe_allow_html=True)
    for rotulo, aba in abas_ui.items():
        if rotulo == rotulos[0]:
            continue
        with aba:
            if abas is None:
                st.caption("Não foi possível ler os dados internos agora.")
            elif "Atualizações" in rotulo:
                mostrar_atualizacoes(abas, n)
            elif "Pareceres" in rotulo:
                mostrar_pareceres(abas, n)
            elif "Comentários" in rotulo:
                login = st.session_state['login_rede']
                st.markdown(html_comentarios(projetos.comentarios_do_projeto(abas, n), eu=login), unsafe_allow_html=True)
            else:
                st.markdown(html_linha_do_tempo(projetos.linha_do_tempo(abas, n), projeto.get('Ano de criação')), unsafe_allow_html=True)

    st.divider()
    pode_documentos = bool(documentos_sei.tipos_para(nivel)) and (projetos.pode("documentos_dplan", nivel) or dono)
    botoes = st.columns([1, 1, 1.4] if pode_documentos else [1, 2])
    if botoes[0].button("Abrir no Acompanhamento", icon=":material/open_in_new:", type="primary", key=f"ficha_abrir_{n}",
                        help="Para registrar atualização, comentar ou emitir parecer"):
        ir_para_acompanhamento(n)
    if pode_documentos:
        botoes[1].button("Documentos SEI", icon=":material/description:", key=f"ficha_docs_{n}", on_click=pedir_documentos, args=(n,),
                         help="Memorandos, Certidões e outros documentos prontos para o SEI")

@st.dialog("Guia do SGPP", width="large")
def dialogo_guia(boas_vindas=False):
    """Janela flutuante com o passo a passo, filtrada pelo nível. Abre no primeiro acesso e pelo botão Guia do menu."""
    nivel = st.session_state['nivel']
    secoes = guia.secoes_para(nivel)
    if boas_vindas:
        primeiro_nome = st.session_state['nome'].split()[0] if st.session_state['nome'].split() else ""
        st.markdown(f"**Bem-vindo ao SGPP{', ' + primeiro_nome if primeiro_nome else ''}.**")
    st.caption(guia.TEXTO_INICIAL)
    rotulos = {s['id']: f"{s['numero']}  {s['titulo']}" for s in secoes}
    escolhida = st.pills("Seções do guia", list(rotulos), format_func=rotulos.get, selection_mode="single",
                         default=secoes[0]['id'], key=f"guia_secao_{nivel}", label_visibility="collapsed")
    secao = next((s for s in secoes if s['id'] == escolhida), secoes[0])
    st.markdown(
        f"<div class='guia-secao'><span class='guia-numero'>{secao['numero']}</span>"
        f"<div><div class='guia-titulo'>{html.escape(secao['titulo'])}</div>"
        f"<p>{html.escape(secao['resumo'])}</p></div></div>", unsafe_allow_html=True)
    if secao.get('intro'):
        st.caption(secao['intro'])
    if secao['passos']:
        st.markdown("\n".join(f"{i}. {passo}" for i, passo in enumerate(secao['passos'], 1)))
    if secao.get('partes'):
        with st.container(height=420, border=False):  # a lista é longa: rola aqui e as abas ficam à vista
            for parte in secao['partes']:
                no_sgpp = f"\n\n:material/check_circle: No SGPP: {', '.join(parte['no_sgpp'])}" if parte['no_sgpp'] else ""
                st.markdown(f"**{parte['numero']}. {parte['titulo']}**\n\n{parte['orientacao']}{no_sgpp}")
    st.caption("Para abrir de novo, use o botão Guia do SGPP, em Atalhos, no menu.")

def tela_principal():
    armazenamento = obter_armazenamento()
    modo_sharepoint = em_sharepoint()
    try:
        df_completo, versao = carregar_dados()
    except ErroArmazenamento as erro:
        alerta_erro(f"Não foi possível ler a fonte de dados do SGPP ({obter_armazenamento_interno().descricao}): {erro}")
        if st.sidebar.button("Tentar novamente", icon=":material/refresh:"):
            _carregar_dados_cache.clear()
            st.rerun()
        if st.sidebar.button("Sair", icon=":material/logout:"):
            st.session_state['autenticado'] = False
            st.rerun()
        return

    base_vazia = df_completo.empty
    if base_vazia:
        df_raw = df_excluidos_global = df_meus = df_meus_excluidos = df_completo
    else:
        df_raw = df_completo[df_completo['SITUACAO_REGISTRO'] == projetos.SITUACAO_ATIVO].copy()
        df_excluidos_global = df_completo[df_completo['SITUACAO_REGISTRO'] == 'Excluído'].copy()
        df_meus = df_raw[df_raw['Gestor'].astype(str).str.lower() == st.session_state['nome'].lower()].copy()
        df_meus_excluidos = df_excluidos_global[df_excluidos_global['Gestor'].astype(str).str.lower() == st.session_state['nome'].lower()].copy()

    # Sem projetos na planilha, só ficam as telas que ajudam a resolver isso
    nivel_atual = st.session_state['nivel']
    opcoes_menu = []
    if not base_vazia:
        opcoes_menu += [PAGINAS["dashboard"], PAGINAS["quadro"]]
        if nivel_atual != "leitor":
            opcoes_menu += [PAGINAS["meus"], PAGINAS["elaboracao"]]
        opcoes_menu.append(PAGINAS["acompanhamento"])
        if documentos_sei.tipos_para(nivel_atual):
            opcoes_menu.append(PAGINAS["documentos"])
    opcoes_menu.append(PAGINAS["planilha"])
    if not base_vazia:
        opcoes_menu.append(PAGINAS["exportar"])
        if projetos.pode("ver_pendencias", nivel_atual):
            opcoes_menu.append(PAGINAS["pendencias"])
        if projetos.pode("liberar_edicao", nivel_atual):
            opcoes_menu.append(PAGINAS["revisao"])
        if st.session_state['perfil'] == 'Gestor_Geral':
            opcoes_menu.append(PAGINAS["painel"])
    if pode_gerenciar_usuarios(nivel_atual):
        opcoes_menu.append(PAGINAS["usuarios"])

    destino = st.session_state.pop('navegar_para', None)
    if destino and PAGINAS["acompanhamento"] in opcoes_menu:
        # Tem de ser antes de os widgets existirem nesta execução
        st.session_state['menu_principal'] = PAGINAS["acompanhamento"]
        st.session_state['acomp_escopo'] = "Todo o portfólio"
        st.session_state['acomp_projeto'] = destino
    destino_docs = st.session_state.pop('navegar_docs', None)
    if destino_docs and PAGINAS["documentos"] in opcoes_menu:
        st.session_state['menu_principal'] = PAGINAS["documentos"]
        st.session_state['docs_projeto'] = destino_docs[0]
        if destino_docs[1] in documentos_sei.tipos_para(nivel_atual):
            st.session_state['docs_tipo'] = destino_docs[1]
    rotulo_lateral("Navegação")
    menu = st.sidebar.radio("Navegação", opcoes_menu, label_visibility="collapsed", key="menu_principal")

    rotulo_lateral("Atalhos")
    pediu_guia = st.sidebar.button("Guia do SGPP", icon=":material/menu_book:", use_container_width=True, key="abrir_guia")
    primeiro_acesso = st.session_state.get('guia_visto_por') != st.session_state['login_rede']
    st.session_state['guia_visto_por'] = st.session_state['login_rede']
    ficha_pendente = st.session_state.pop('ficha_pendente', None)
    if pediu_guia or primeiro_acesso:
        dialogo_guia(boas_vindas=primeiro_acesso and not pediu_guia)
    elif ficha_pendente:
        dialogo_ficha(ficha_pendente)
    with st.sidebar.expander("Copiar nº do SEI", icon=":material/content_copy:"):
        if not df_raw.empty and 'SEI' in df_raw.columns:
            por_id_side = {r['ID_PROJETO']: r for _, r in df_raw.iterrows()}
            sel_side = st.selectbox("Projeto", list(por_id_side), key="side_sei_select",
                                    format_func=lambda i: f"Nº {por_id_side[i]['Nº']} - {str(por_id_side[i]['Nome da Iniciativa'])[:22]}...")
            sei_side = str(por_id_side[sel_side]['SEI']).strip()
            if sei_side:
                st.caption("Use o ícone de copiar no canto da caixa e cole com `Ctrl+V` no SEI:")
                st.code(sei_side, language=None)
            else:
                st.caption("Este projeto não possui nº SEI.")
        st.link_button("Abrir o portal SEI-MPAM", "https://sei.mpam.mp.br/sei", icon=":material/open_in_new:", use_container_width=True)

    rotulo_lateral("Conta")
    rotulo_nivel = contas.ROTULOS_NIVEL.get(st.session_state['nivel'], "Usuário")
    st.sidebar.markdown(f"<div class='cartao-usuario'>{html.escape(rotulo_nivel)}<b>{html.escape(st.session_state['nome'])}</b></div>", unsafe_allow_html=True)
    if st.session_state.get('conta_na_planilha') and not ATIVAR_LDAP_CORPORATIVO_TI:
        with st.sidebar.expander("Alterar minha senha", icon=":material/key:"):
            formulario_troca_senha("menu")
    if st.sidebar.button("Sair", icon=":material/logout:", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

    # --------------------------------------------------------------------------
    # PÁGINAS
    # --------------------------------------------------------------------------
    if menu == PAGINAS["usuarios"]:
        tela_usuarios(df_completo)

    elif menu == PAGINAS["planilha"]:
        tela_planilha_central(armazenamento, modo_sharepoint, df_completo, versao)

    elif menu == PAGINAS["quadro"]:
        tela_quadro(df_raw)

    elif menu == PAGINAS["pendencias"]:
        tela_pendencias(df_completo)

    elif menu == PAGINAS["elaboracao"]:
        tela_elaboracao(df_completo, modo_sharepoint)

    elif menu == PAGINAS["acompanhamento"]:
        tela_acompanhamento(df_completo, modo_sharepoint)

    elif menu == PAGINAS["documentos"]:
        tela_documentos_sei(df_completo, modo_sharepoint)

    elif menu == PAGINAS["revisao"]:
        tela_revisao(df_completo, modo_sharepoint)

    # --------------------------------------------------------------------------
    # MÓDULO 2: DASHBOARD GLOBAL
    # --------------------------------------------------------------------------
    elif menu == PAGINAS["dashboard"]:
        faixa_titulo("Dashboard", "Portfólio de projetos, programas e boas práticas do MPAM", "dashboard")
        
        escopo_dash = st.radio(
            "Escopo do dashboard",
            ["Portfólio global do MPAM (todos os projetos ativos)", f"Apenas meus projetos ({st.session_state['nome']})"],
            horizontal=True
        )
        
        df_base_dash = df_raw.copy() if escopo_dash.startswith("Portfólio") else df_meus.copy()
        
        if df_base_dash.empty:
            alerta_info("Nenhuma iniciativa ativa encontrada para o filtro selecionado.")
        else:
            with st.expander("Filtrar os dados do dashboard (área, status, município)", expanded=False, icon=":material/filter_alt:"):
                f1, f2, f3 = st.columns(3)
                areas_disp = df_base_dash['Área de Atuação'].dropna().unique().tolist()
                status_disp = df_base_dash['Status'].dropna().unique().tolist()
                mun_disp = df_base_dash['Município'].dropna().unique().tolist() if 'Município' in df_base_dash.columns else []
                
                f_area = f1.multiselect("Área de Atuação", areas_disp, default=areas_disp)
                f_status = f2.multiselect("Status", status_disp, default=status_disp)
                f_mun = f3.multiselect("Município", mun_disp, default=mun_disp) if mun_disp else []
                
            df_dash = df_base_dash[
                (df_base_dash['Área de Atuação'].isin(f_area)) &
                (df_base_dash['Status'].isin(f_status))
            ]
            if mun_disp:
                df_dash = df_dash[df_dash['Município'].isin(f_mun)]

            st.markdown("---")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Iniciativas Ativas", len(df_dash))
            k2.metric("Em Execução", len(df_dash[df_dash['Status'] == 'Em execução']))
            k3.metric("Institucionalizados", len(df_dash[df_dash['Institucionalizado'] == 'Sim']) if 'Institucionalizado' in df_dash.columns else 0)
            k4.metric("Municípios Atendidos", df_dash['Município'].nunique() if 'Município' in df_dash.columns and not df_dash.empty else 0)
            st.markdown("---")
            
            c1, c2 = st.columns(2)
            with c1:
                fig1 = px.pie(df_dash, names='Projeto/Programa/Boa Prática', title="Composição do Portfólio", hole=0.4, color_discrete_sequence=PALETA_GRAFICOS)
                fig1.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5))
                st.plotly_chart(estilizar_figura(fig1), use_container_width=True)
            with c2:
                areas = df_dash['Área de Atuação'].value_counts().reset_index()
                fig2 = px.bar(areas, x='count', y='Área de Atuação', orientation='h', title="Iniciativas por Área de Atuação", color_discrete_sequence=[VINHO], labels={'count': 'Iniciativas', 'Área de Atuação': ''})
                fig2.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(estilizar_figura(fig2), use_container_width=True)
                
            st.markdown("## Iniciativas ativas do MPAM")
            st.caption("Consulta somente leitura.")
            
            # Barra Expressa de Cópia em 1 Clique para o SEI
            renderizar_copiador_sei(df_dash, "dash")
            
            st.caption("Marque a caixa no início de uma linha para abrir a ficha completa do projeto. "
                       "Para copiar um número, clique no **Nº SEI** e use `Ctrl+C`.")
            colunas_consulta = ['CODIGO', 'Nº', 'Nome da Iniciativa', 'Projeto/Programa/Boa Prática', 'Área de Atuação', 'Unidade', 'Município', 'Gestor', 'Status', 'SEI', 'Link_SEI']
            cols_existentes = [c for c in colunas_consulta if c in df_dash.columns]
            df_tabela_dash = filtrar_tabela(df_dash, "dash")
            # A chave muda a cada abertura: a seleção zera e a mesma linha pode ser marcada de novo depois de fechar a ficha
            versao_tabela = st.session_state.get('tabela_dash_v', 0)
            marcadas = st.dataframe(
                df_tabela_dash[cols_existentes],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key=f"tabela_dash_{versao_tabela}",
                column_config={
                    "SEI": st.column_config.TextColumn("Nº SEI"),
                    "Link_SEI": st.column_config.LinkColumn("Link", display_text="Abrir SEI")
                }
            )
            if marcadas.selection.rows:
                st.session_state['tabela_dash_v'] = versao_tabela + 1
                abrir_ficha(df_tabela_dash.iloc[marcadas.selection.rows[0]]['ID_PROJETO'])

    # --------------------------------------------------------------------------
    # MÓDULO 3: AUTOGESTÃO DO USUÁRIO (COM EXCLUSÃO REGISTRADA E COPIADOR SEI)
    # --------------------------------------------------------------------------
    elif menu == PAGINAS["meus"]:
        faixa_titulo("Meus Projetos", "Autogestão das iniciativas sob sua responsabilidade", "folder_open")
        st.markdown(f"Abaixo constam as iniciativas ativas onde **{st.session_state['nome']}** é o Gestor responsável.")
        mensagem_meus = st.session_state.pop('aviso_meus', None)
        if mensagem_meus:
            alerta_ok(mensagem_meus)
        botao_documento_depois()

        if df_meus.empty:
            alerta_info(f"Não há iniciativas ativas registradas sob responsabilidade de '{st.session_state['nome']}'.")
        else:
            detalhe_meus = projetos.pendencias_detalhadas(df_meus)
            obrigatorias = detalhe_meus[detalhe_meus['gravidade'] == "Obrigatório"]
            if not obrigatorias.empty:
                faltam = obrigatorias.groupby('n', sort=False).agg(
                    codigo=('codigo', 'first'), campos=('categoria', lambda c: ", ".join(x.replace(" em branco", "").lower() for x in c)))
                lista = "; ".join(f"{linha.codigo or 'Nº ' + n}: {linha.campos}" for n, linha in faltam.iterrows())
                alerta_aviso(f"{len(faltam)} dos seus projetos têm campos obrigatórios em branco. Complete-os na tabela abaixo ou "
                             f"peça à Planejamento. Faltam: {lista}.")
            renderizar_copiador_sei(df_meus, "meus")
            bloco_retornos_gestor(df_meus)
            livres = df_meus[df_meus['EDICAO'] != projetos.EDICAO_TRAVADA]
            travados = df_meus[df_meus['EDICAO'] == projetos.EDICAO_TRAVADA]

            if not livres.empty:
                st.markdown("## Edição livre ou liberada")
                st.caption("Projetos que você pode editar agora. Depois de salvar uma alteração em um projeto cuja edição a Planejamento liberou, ele volta a ficar travado.")
                livres_filtrado = filtrar_tabela(livres, "meus")
                visiveis = livres_filtrado.drop(columns=COLUNAS_OCULTAS_GESTOR, errors='ignore')
                visiveis = visiveis[['CODIGO'] + [c for c in visiveis.columns if c != 'CODIGO']]
                df_editado_user = st.data_editor(
                    visiveis,
                    use_container_width=True, num_rows="fixed", height=400,
                    disabled=['Nº', 'Iniciativa', 'CODIGO'],
                    column_config={
                        "CODIGO": st.column_config.TextColumn("Código"),
                        "SEI": st.column_config.TextColumn("Nº SEI"),
                        "Status": st.column_config.SelectboxColumn("Status", options=projetos.STATUS),
                        "INICIO_PREVISTO": st.column_config.TextColumn("Início previsto", help="AAAA-MM-DD"),
                        "TERMINO_PREVISTO": st.column_config.TextColumn("Término previsto", help="AAAA-MM-DD"),
                        "Link_SEI": st.column_config.LinkColumn("Link", display_text="Abrir SEI")
                    },
                    hide_index=True
                )
                if st.button("Salvar Alterações", icon=":material/save:", type="primary", key="salvar_meus"):
                    # Grava sobre a mesma versão que o usuário viu: se alguém alterou a planilha depois, dá conflito
                    salvar_edicoes_gestor(df_completo, versao, livres_filtrado, df_editado_user)

            if not travados.empty:
                st.markdown("## Enviados à Planejamento")
                st.caption("Estes projetos estão travados para edição. Para alterar algum, peça a liberação.")
                tabela_travados = travados.assign(Edição=travados.apply(situacao_da_edicao, axis=1))
                st.dataframe(
                    tabela_travados[['CODIGO', 'Nome da Iniciativa', 'Status', 'ENVIADO_EM', 'REVISAO', 'Edição']],
                    use_container_width=True, hide_index=True,
                    column_config={'CODIGO': 'Código', 'Nome da Iniciativa': 'Projeto', 'ENVIADO_EM': 'Enviado em', 'REVISAO': 'Revisão'}
                )
                sem_pedido = travados[travados['PEDIDO_LIBERACAO'] == ""]
                if sem_pedido.empty:
                    st.caption("Todos os projetos travados já têm um pedido de liberação aguardando a Planejamento.")
                else:
                    with st.container(border=True):
                        st.markdown("**Precisa alterar um projeto enviado?**")
                        por_numero = {projetos.chave(r): r for _, r in sem_pedido.iterrows()}
                        escolhido_pedido = st.selectbox("Projeto", list(por_numero), format_func=lambda n: rotulo_projeto(por_numero[n]), key="sel_pedido")
                        motivo_pedido = st.text_area("O que precisa ser alterado e por quê", key="motivo_pedido")
                        if st.button("Solicitar liberação", icon=":material/lock_open:", key="solicitar_liberacao"):
                            pedir_liberacao(escolhido_pedido, motivo_pedido)

            # BLOCO DE EXCLUSÃO DE PROJETO PELO PRÓPRIO USUÁRIO (só projetos com edição livre ou liberada)
            st.markdown("---")
            with st.expander("Excluir uma das minhas iniciativas (exige justificativa)", icon=":material/delete:"):
                if livres.empty:
                    alerta_info("Seus projetos enviados estão travados. Para excluir um deles, peça à Planejamento.")
                else:
                    alerta_aviso("Atenção: A iniciativa excluída sairá do Portfólio Ativo e ficará registrada no histórico com seu nome, motivo e data.")
                    por_id_meus = {r['ID_PROJETO']: r for _, r in livres.iterrows()}
                    proj_selecionado_user = st.selectbox("Selecione a Iniciativa que deseja excluir:", list(por_id_meus), key="sel_del_user",
                                                         format_func=lambda i: f"Nº {por_id_meus[i]['Nº']} - {por_id_meus[i]['Nome da Iniciativa']}")
                    motivo_user = st.text_input("Motivo sucinto da exclusão * (Ex: Cadastro em duplicidade, projeto cancelado):", key="mot_del_user")

                    if st.button("Confirmar Exclusão", icon=":material/delete:", key="perigo_excluir_meu"):
                        if len(motivo_user.strip()) < 5:
                            alerta_erro("Informe um motivo sucinto válido (mínimo de 5 caracteres) para registrar a exclusão.")
                        else:
                            num_id = proj_selecionado_user
                            if executar_exclusao_logica(num_id, f"{st.session_state['nome']} (Autogestão)", motivo_user):
                                alerta_ok(f"Iniciativa Nº {num_id} excluída com sucesso! Registro da exclusão gravado.")
                                st.rerun()

        if not df_meus_excluidos.empty:
            st.markdown("---")
            with st.expander(f"Meu histórico de iniciativas excluídas ({len(df_meus_excluidos)})", expanded=True, icon=":material/history:"):
                cols_hist_user = ['Nº', 'Nome da Iniciativa', 'EXCLUIDO_POR', 'MOTIVO_EXCLUSAO', 'DATA_EXCLUSAO', 'Unidade']
                st.dataframe(
                    df_meus_excluidos[[c for c in cols_hist_user if c in df_meus_excluidos.columns]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "EXCLUIDO_POR": st.column_config.TextColumn("Quem Excluiu"),
                        "MOTIVO_EXCLUSAO": st.column_config.TextColumn("MOTIVO_EXCLUSAO"),
                        "DATA_EXCLUSAO": st.column_config.TextColumn("DATA_EXCLUSAO")
                    }
                )

    # --------------------------------------------------------------------------
    # MÓDULO 4: CENTRAL DE EXPORTAÇÃO
    # --------------------------------------------------------------------------
    elif menu == PAGINAS["exportar"]:
        faixa_titulo("Exportar", "Baixe o portfólio em Excel ou CSV", "download")
        opcoes_export = ["Portfólio global ativo do MPAM", "Apenas meus projetos ativos"]
        if st.session_state['perfil'] == 'Gestor_Geral':
            opcoes_export.append("Base completa com registros de acompanhamento (incluindo excluídos)")
            opcoes_export.append("Para o Power BI (formato da planilha original)")
            
        escopo_exp = st.radio("Selecione o conteúdo para download:", opcoes_export, horizontal=True)
        
        if escopo_exp.startswith("Para o Power BI"):
            # Exportação à parte: a planilha original do Power BI não é gravada pelo SGPP
            para_bi = projetos.para_power_bi(df_completo)
            buffer_bi = io.BytesIO()
            with pd.ExcelWriter(buffer_bi, engine='openpyxl') as writer:
                para_bi.to_excel(writer, index=False, sheet_name='Projetos')
            st.caption(f"{len(para_bi)} projeto(s) ativo(s), só com as colunas da planilha original e na mesma ordem. "
                       "Projetos excluídos ou arquivados e as colunas do SGPP ficam de fora, e a planilha original não é alterada.")
            c1, _ = st.columns([1.5, 2.5])
            c1.download_button("Baixar para o Power BI (.xlsx)", buffer_bi.getvalue(), "PROJETOS - SGPP (formato Power BI).xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/download:",
                               type="primary", use_container_width=True)
            st.stop()

        if escopo_exp.startswith("Portfólio"):
            df_exp = df_raw.copy()
        elif escopo_exp.startswith("Apenas"):
            df_exp = df_meus.copy()
        else:
            df_exp = df_completo.copy()
        
        if st.session_state['perfil'] != 'Gestor_Geral':
            df_exp = df_exp.drop(columns=["OBSERVAÇÕES/CORREÇÕES", "AVALIAÇÃO", "AUDITOR_DPLAN", "PEDIDO_LIBERACAO", "ID_RASCUNHO", "ENVIADO_POR"], errors='ignore')
            
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_exp.drop(columns=['SEI_Limpo', 'Link_SEI'], errors='ignore').to_excel(writer, index=False)
        
        # Ação principal à esquerda e apoio ao lado, com largura de botão (e não da página inteira)
        c1, c2, _ = st.columns([1, 1, 1.4])
        c1.download_button("Baixar Excel (.xlsx)", buffer.getvalue(), "PROJETOS - Teste 1.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", icon=":material/download:", type="primary", use_container_width=True)
        c2.download_button("Baixar CSV (.csv)", df_exp.drop(columns=['SEI_Limpo', 'Link_SEI'], errors='ignore').to_csv(index=False).encode('utf-8'), "PROJETOS_MPAM.csv", "text/csv", icon=":material/download:", use_container_width=True)

    # --------------------------------------------------------------------------
    # MÓDULO 5: PAINEL DE ACOMPANHAMENTO GLOBAL E EXCLUSÃO (DPLAN)
    # --------------------------------------------------------------------------
    elif menu == PAGINAS["painel"]:
        faixa_titulo("Painel de Gestão", "Governança e acompanhamento, DPLAN/MPAM", "admin_panel_settings")
        st.markdown(f"Gestor DPLAN conectado: **{st.session_state['nome']}** | Acesso irrestrito a toda a base (Capital e Interior).")
        
        renderizar_copiador_sei(df_completo, "admin")
        
        filtro_visao_dplan = st.radio(
            "Registros exibidos",
            ["Exibir Todos os Registros (ativos, arquivados e excluídos)", "Exibir Apenas Projetos Ativos"],
            horizontal=True
        )
        
        df_tabela_admin = df_completo.copy() if filtro_visao_dplan.startswith("Exibir Todos") else df_raw.copy()
        df_tabela_admin = filtrar_tabela(df_tabela_admin, "admin")
        
        cols_finais_auditoria = [
            'OBSERVAÇÕES/CORREÇÕES', 'AVALIAÇÃO', 'AUDITOR_DPLAN',
            'SITUACAO_REGISTRO', 'EXCLUIDO_POR', 'MOTIVO_EXCLUSAO', 'DATA_EXCLUSAO'
        ]
        cols_iniciais = [c for c in df_tabela_admin.columns if c not in cols_finais_auditoria and c != 'SEI_Limpo']
        ordem_colunas_admin = cols_iniciais + [c for c in cols_finais_auditoria if c in df_tabela_admin.columns]
        
        df_editado_admin = st.data_editor(
            df_tabela_admin[ordem_colunas_admin],
            use_container_width=True, num_rows="fixed", height=480,
            disabled=['Nº', 'Iniciativa', 'CODIGO', 'EDICAO', 'ENVIADO_POR', 'ENVIADO_EM', 'ID_RASCUNHO', 'PEDIDO_LIBERACAO', 'REVISAO', 'ID_PROJETO'],
            column_config={
                "SEI": st.column_config.TextColumn("Nº SEI"),
                "Status": st.column_config.SelectboxColumn("Status", options=["Em execução", "Concluído", "Paralisado", "Em elaboração"]),
                "Link_SEI": st.column_config.LinkColumn("Link", display_text="Abrir SEI"),
                "AVALIAÇÃO": st.column_config.SelectboxColumn("Avaliação DPLAN", options=["", "Excelente", "Bom", "Regular", "Atrasado", "Crítico", "Revisar"]),
                "OBSERVAÇÕES/CORREÇÕES": st.column_config.TextColumn("Observações / Correções DPLAN", max_chars=1000),
                "AUDITOR_DPLAN": st.column_config.TextColumn("Avaliado por (DPLAN)"),
                "SITUACAO_REGISTRO": st.column_config.SelectboxColumn("Situação", options=["Ativo", "Arquivado", "Excluído"]),
                "EXCLUIDO_POR": st.column_config.TextColumn("EXCLUIDO_POR"),
                "MOTIVO_EXCLUSAO": st.column_config.TextColumn("MOTIVO_EXCLUSAO"),
                "DATA_EXCLUSAO": st.column_config.TextColumn("DATA_EXCLUSAO")
            },
            hide_index=True
        )
        if st.button("Gravar Avaliações", icon=":material/save:", type="primary", key="salvar_painel"):
            # Grava sobre a mesma versão que o gestor viu: se alguém alterou a planilha depois, dá conflito
            df_atual = df_completo.copy()
            mask_avaliado = (df_editado_admin['AVALIAÇÃO'].astype(str).str.strip() != "") & (df_editado_admin['AUDITOR_DPLAN'].astype(str).str.strip() == "")
            df_editado_admin.loc[mask_avaliado, 'AUDITOR_DPLAN'] = st.session_state['nome']
            
            agora_manaus = datetime.now(FUSO_AMAZONAS).strftime("%d/%m/%Y %H:%M")
            mask_excluido_manual = (df_editado_admin['SITUACAO_REGISTRO'] == 'Excluído') & (df_editado_admin['DATA_EXCLUSAO'].astype(str).str.strip() == "")
            df_editado_admin.loc[mask_excluido_manual, 'DATA_EXCLUSAO'] = agora_manaus
            df_editado_admin.loc[mask_excluido_manual & (df_editado_admin['EXCLUIDO_POR'].astype(str).str.strip() == ""), 'EXCLUIDO_POR'] = f"{st.session_state['nome']} (DPLAN)"
            
            df_atual.update(df_editado_admin)
            if gravar_com_aviso(df_atual, versao):
                alerta_ok(f"Base Global atualizada e homologada por {st.session_state['nome']}!")
                st.rerun()

        # BLOCO DE EXCLUSÃO E RESTAURAÇÃO PELO GESTOR GLOBAL (DPLAN)
        st.markdown("---")
        col_del, col_rest = st.columns(2)
        
        with col_del:
            with st.expander("Excluir projeto do portfólio", expanded=False, icon=":material/delete:"):
                if df_raw.empty:
                    alerta_info("Não há projetos ativos para excluir.")
                else:
                    por_id_global = {r['ID_PROJETO']: r for _, r in df_raw.iterrows()}
                    proj_sel_admin = st.selectbox("Selecione o Projeto para excluir:", list(por_id_global), key="sel_del_admin",
                                                  format_func=lambda i: f"Nº {por_id_global[i]['Nº']} - {por_id_global[i]['Nome da Iniciativa']} ({por_id_global[i]['Gestor']})")
                    motivo_admin = st.text_input("Motivo sucinto da exclusão (DPLAN) *:", key="mot_del_admin")
                    
                    if st.button("Executar Exclusão", icon=":material/delete:", key="perigo_excluir_dplan"):
                        if len(motivo_admin.strip()) < 5:
                            alerta_erro("Informe o motivo sucinto da exclusão (mínimo de 5 caracteres).")
                        else:
                            num_id_adm = proj_sel_admin
                            if executar_exclusao_logica(num_id_adm, f"{st.session_state['nome']} (Gestor DPLAN)", motivo_admin):
                                alerta_ok(f"Projeto Nº {num_id_adm} excluído pela DPLAN com Data e Hora registradas!")
                                st.rerun()

        with col_rest:
            with st.expander(f"Restaurar projeto excluído ({len(df_excluidos_global)} na lixeira)", expanded=False, icon=":material/restore_from_trash:"):
                if df_excluidos_global.empty:
                    alerta_info("Nenhuma iniciativa excluída no momento.")
                else:
                    por_id_rest = {r['ID_PROJETO']: r for _, r in df_excluidos_global.iterrows()}
                    proj_rest = st.selectbox("Selecione o Projeto para restaurar:", list(por_id_rest), key="sel_rest_admin",
                                             format_func=lambda i: f"Nº {por_id_rest[i]['Nº']} - {por_id_rest[i]['Nome da Iniciativa']} (Excluído por: {por_id_rest[i]['EXCLUIDO_POR']})")
                    if st.button("Restaurar Projeto", icon=":material/restore_from_trash:", key="restaurar_projeto"):
                        num_id_rest = proj_rest
                        if restaurar_projeto_excluido(num_id_rest):
                            alerta_ok(f"Projeto Nº {num_id_rest} restaurado com sucesso para o Portfólio Ativo!")
                            st.rerun()

        st.markdown("## Registro de projetos excluídos")
        if df_excluidos_global.empty:
            st.caption("Nenhum projeto foi excluído até o momento.")
        else:
            cols_auditoria = ['Nº', 'Nome da Iniciativa', 'EXCLUIDO_POR', 'MOTIVO_EXCLUSAO', 'DATA_EXCLUSAO', 'Gestor', 'Unidade', 'Município']
            st.dataframe(
                df_excluidos_global[[c for c in cols_auditoria if c in df_excluidos_global.columns]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "EXCLUIDO_POR": st.column_config.TextColumn("EXCLUIDO_POR (Quem Excluiu)"),
                    "MOTIVO_EXCLUSAO": st.column_config.TextColumn("MOTIVO_EXCLUSAO"),
                    "DATA_EXCLUSAO": st.column_config.TextColumn("DATA_EXCLUSAO (Data e Hora)")
                }
            )

if not st.session_state['autenticado']:
    tela_login()
elif st.session_state.get('trocar_senha'):
    tela_troca_senha_obrigatoria()
else:
    tela_principal()
