import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh  # Necessário: pip install streamlit-autorefresh

# ==================== 1. CONFIGURAÇÕES DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop - Gestão", layout="wide", page_icon="⚡")

# HEARTBEAT: Atualiza silenciosamente a cada 5 minutos para manter a sessão viva no totem
st_autorefresh(interval=5 * 60 * 1000, key="heartbeat_flashstop")

# CSS para botões ultra-compactos e ajustes de interface
st.markdown("""
    <style>
    .stButton>button { border-radius: 6px; padding: 2px 5px; }
    div[data-testid="column"] button { height: 32px !important; width: 32px !important; font-weight: bold !important; font-size: 18px !important; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Inicialização de Estados de Sessão
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'carrinho' not in st.session_state: st.session_state.carrinho = []
if 'unidade' not in st.session_state: st.session_state.unidade = ""
if 'perfil' not in st.session_state: st.session_state.perfil = ""

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dinamico(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df is not None and not df.empty:
            df.columns = [c.lower().strip() for c in df.columns]
        return df
    except Exception:
        return pd.DataFrame()

# ==================== 2. SISTEMA DE LOGIN (URL + MANUAL) ====================

# --- FLUXO A: LOGIN AUTOMÁTICO VIA URL (?pdv=NomeDaUnidade&token=flash2026) ---
TOKEN_MESTRE = "flash2026"
query_params = st.query_params
if not st.session_state.autenticado:
    if "pdv" in query_params and "token" in query_params:
        if query_params["token"] == TOKEN_MESTRE:
            st.session_state.update({
                "autenticado": True, 
                "unidade": query_params["pdv"], 
                "perfil": "pdv"
            })

# --- FLUXO B: INTERFACE DE LOGIN MANUAL ---
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center; color: #32CD32;'>⚡ flash stop</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user = st.text_input("Usuário / PDV")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", use_container_width=True):
                df_pts = carregar_dinamico("pontos")
                if user == "admin" and senha == "flash123":
                    st.session_state.update({"autenticado": True, "unidade": "Administração", "perfil": "admin"})
                    st.rerun()
                elif not df_pts.empty and user in df_pts['nome'].values:
                    senha_correta = str(df_pts[df_pts['nome'] == user]['senha'].values[0])
                    if senha == senha_correta:
                        st.session_state.update({"autenticado": True, "unidade": user, "perfil": "pdv"})
                        st.rerun()
                    else: st.error("Senha incorreta.")
                else: st.error("Usuário não encontrado.")
    st.stop()

# ==================== 3. MENU LATERAL ====================
st.sidebar.title("⚡ Flash Stop")
st.sidebar.write(f"📍 **{st.session_state.unidade}**")

opcoes = ["📊 Dashboard", "🛒 Self-Checkout", "💰 Entrada Mercadoria", "📦 Inventário", "💸 Despesas", "📂 Contabilidade", "📟 Configurações"] if st.session_state.perfil == "admin" else ["🛒 Self-Checkout", "📦 Inventário"]
menu = st.sidebar.radio("Navegação", opcoes)

if st.sidebar.button("🚪 Sair"):
    st.session_state.autenticado = False
    st.rerun()

# ==================== 4. ABA: INVENTÁRIO (SÓ VÊ O SEU) ====================
if menu == "📦 Inventário":
    st.header(f"📦 Gestão de Estoque - {st.session_state.unidade}")
    
    df_geral = carregar_dinamico("produtos")      
    df_estoque = carregar_dinamico("estoque_pdv") 

    # Se for Admin, ele escolhe qual unidade ver. Se for PDV, a escolha é travada na dele.
    if st.session_state.perfil == "admin":
        lista_pdvs = df_estoque['unidade'].unique().tolist() if not df_estoque.empty else ["Flash Stop 01"]
        unidade_ativa = st.selectbox("Selecione o PDV para gerir:", lista_pdvs)
    else:
        unidade_ativa = st.session_state.unidade
        st.info(f"Visualizando estoque local da unidade: **{unidade_ativa}**")

    aba_geral, aba_unidade = st.tabs(["🌎 Catálogo Geral", "📍 Estoque Local"])

    with aba_geral:
        st.subheader("Catálogo de Preços Global")
        if not df_geral.empty:
            st.dataframe(df_geral[["nome", "preco_venda", "categoria"]], use_container_width=True, hide_index=True)

    with aba_unidade:
        # Filtra para mostrar APENAS o que pertence àquela unidade
        df_local = df_estoque[df_estoque['unidade'] == unidade_ativa] if not df_estoque.empty else pd.DataFrame()
        
        # Botão para importar produtos novos do catálogo geral para este PDV específico
        if not df_geral.empty:
            faltantes = [p for p in df_geral['nome'].tolist() if p not in df_local['nome'].tolist()]
            if faltantes and st.button(f"📥 Sincronizar {len(faltantes)} novos itens"):
                novos = pd.DataFrame([{"unidade": unidade_ativa, "nome": p, "quantidade": 0, "validade": "A definir", "minimo_alerta": 5} for p in faltantes])
                df_estoque = pd.concat([df_estoque, novos], ignore_index=True)
                conn.update(worksheet="estoque_pdv", data=df_estoque)
                st.rerun()

        if not df_local.empty:
            st.dataframe(df_local[["nome", "quantidade", "validade", "minimo_alerta"]], use_container_width=True, hide_index=True)

            with st.expander("✏️ Editar Quantidade / Validade Local"):
                with st.form("edit_estoque_local"):
                    p_edit = st.selectbox("Produto", df_local['nome'].tolist())
                    c1, c2, c3 = st.columns(3)
                    n_qtd = c1.number_input("Qtd em Prateleira", value=0)
                    n_val = c2.text_input("Validade (DD/MM/AAAA)")
                    n_min = c3.number_input("Mínimo para Alerta", value=5)
                    if st.form_submit_button("Salvar Alterações"):
                        idx = df_estoque[(df_estoque['unidade'] == unidade_ativa) & (df_estoque['nome'] == p_edit)].index[0]
                        df_estoque.at[idx, 'quantidade'] = n_qtd
                        df_estoque.at[idx, 'validade'] = n_val
                        df_estoque.at[idx, 'minimo_alerta'] = n_min
                        conn.update(worksheet="estoque_pdv", data=df_estoque)
                        st.success("Estoque atualizado!")
                        st.rerun()

# ==================== 5. ABA: DASHBOARD (ALERTAS FILTRADOS) ====================
elif menu == "📊 Dashboard":
    st.header(f"📊 Painel - {st.session_state.unidade}")
    
    df_v = carregar_dinamico("vendas")
    df_e = carregar_dinamico("estoque_pdv")

    # Se for PDV, o dashboard só mostra os dados dele
    if st.session_state.perfil == "pdv":
        df_v = df_v[df_v['unidade'] == st.session_state.unidade] if not df_v.empty else df_v
        df_e = df_e[df_e['unidade'] == st.session_state.unidade] if not df_e.empty else df_e

    # (Aqui continua a lógica de métricas financeiras que você já tem...)
    st.write("Métricas de Faturamento e Alertas de Estoque...")
    # ... (restante do código do Dashboard que você enviou)

# ==================== 6. ABA: SELF-CHECKOUT ====================
elif menu == "🛒 Self-Checkout":
    st.markdown("<h2 style='text-align: center;'>⚡ flash stop</h2>", unsafe_allow_html=True)
    # (Aqui entra a lógica do carrinho e finalização de compra que você já tem...)
    st.info(f"PDV ATIVO: {st.session_state.unidade}")
