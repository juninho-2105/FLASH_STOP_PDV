import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh

# ==================== 1. CONFIGURAÇÕES DA PÁGINA & DESIGN PREMIUM ====================
st.set_page_config(
    page_title="Flash Stop - Gestão Pro", 
    layout="wide", 
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# Heartbeat para manter o app ativo (Anti-hibernação)
st_autorefresh(interval=5 * 60 * 1000, key="heartbeat_flashstop")

# --- CSS MASTER DESIGN (DARK PREMIUM) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    * { font-family: 'Inter', sans-serif; }

    .stApp { background-color: #0E1117; color: #FFFFFF; }

    section[data-testid="stSidebar"] {
        background-color: #161B22 !important;
        border-right: 1px solid #30363D;
    }
    
    div[data-testid="metric-container"] {
        background-color: #161B22;
        border: 1px solid #30363D;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stButton>button {
        background-color: #76D72B !important;
        color: #000000 !important;
        font-weight: 800 !important;
        border-radius: 10px !important;
        border: none !important;
        height: 45px !important;
        width: 100% !important;
        text-transform: uppercase;
        transition: all 0.3s ease !important;
    }
    .stButton>button:hover {
        background-color: #5eb022 !important;
        box-shadow: 0 0 15px rgba(118, 215, 43, 0.4) !important;
        transform: scale(1.02);
    }

    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background-color: #0D1117 !important;
        border: 1px solid #30363D !important;
        color: white !important;
    }

    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Inicialização de Estados
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'carrinho' not in st.session_state: st.session_state.carrinho = []
if 'unidade' not in st.session_state: st.session_state.unidade = ""
if 'perfil' not in st.session_state: st.session_state.perfil = ""

# Conexão Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dinamico(aba):
    try: return conn.read(worksheet=aba, ttl=0)
    except: return pd.DataFrame()

# ==================== 2. SISTEMA DE LOGIN ====================
query_params = st.query_params
if not st.session_state.autenticado:
    if "pdv" in query_params and "token" in query_params:
        if query_params["token"] == "flash2026":
            st.session_state.update({"autenticado": True, "unidade": query_params["pdv"], "perfil": "pdv"})
            st.rerun()

if not st.session_state.autenticado:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div style='text-align: center; background: #161B22; padding: 40px; border-radius: 20px; border: 1px solid #30363D;'>
                <h1 style='color: #76D72B; font-size: 60px; margin-bottom: 0;'>⚡</h1>
                <h2 style='margin-top: 0; color: white;'>FLASH STOP</h2>
                <p style='color: #8B949E;'>Acesso ao Terminal de Gestão</p>
            </div>
        """, unsafe_allow_html=True)
        with st.form("login_form"):
            user = st.text_input("Usuário / PDV")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("ACESSAR SISTEMA"):
                df_pts = carregar_dinamico("pontos")
                if user == "admin" and senha == "flash123":
                    st.session_state.update({"autenticado": True, "unidade": "Administração", "perfil": "admin"})
                    st.rerun()
                elif not df_pts.empty and user in df_pts['nome'].values:
                    if senha == str(df_pts[df_pts['nome'] == user]['senha'].values[0]):
                        st.session_state.update({"autenticado": True, "unidade": user, "perfil": "pdv"})
                        st.rerun()
                    else: st.error("Senha incorreta.")
                else: st.error("Usuário não encontrado.")
    st.stop()

# ==================== 3. MENU LATERAL ====================
with st.sidebar:
    st.markdown("<div style='text-align: center; padding: 20px 0;'><span style='font-size: 40px;'>⚡</span><h3 style='margin: 0; color: #76D72B;'>FLASH STOP</h3></div>", unsafe_allow_html=True)
    st.markdown(f"<div style='background: #0D1117; padding: 10px; border-radius: 8px; text-align: center; border: 1px solid #30363D;'>📍 <b>{st.session_state.unidade}</b></div>", unsafe_allow_html=True)
    opcoes = ["📊 Dashboard", "🛒 Self-Checkout", "📱 Pedidos Online", "💰 Entrada Mercadoria", "📦 Inventário", "💸 Despesas", "📂 Contabilidade", "📟 Configurações"] if st.session_state.perfil == "admin" else ["🛒 Self-Checkout", "📱 Pedidos Online", "📦 Inventário"]
    menu = st.radio("Navegação Principal", opcoes)
    if st.button("🚪 ENCERRAR SESSÃO"):
        st.session_state.autenticado = False
        st.rerun()

# ==================== 4. TELAS ====================

if menu == "📊 Dashboard":
    st.title("📊 Painel de Controle")
    df_v = carregar_dinamico("vendas")
    if not df_v.empty:
        bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
        liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento", f"R<LaTex>$ {bruto:,.2f}")
        m2.metric("Líquido", f"R$</LaTex> {liq:,.2f}")
        m3.metric("Vendas", len(df_v))
        st.area_chart(df_v.groupby(pd.to_datetime(df_v['data'], errors='coerce', dayfirst=True).dt.date)['valor_bruto'].sum(), color="#76D72B")

elif menu == "🛒 Self-Checkout":
    st.markdown("<div style='text-align: center; padding: 20px; background: #161B22; border-radius: 15px; border-bottom: 4px solid #76D72B;'><h1 style='margin:0; color: #76D72B;'>⚡ flash<span style='color: white;'>stop</span></h1></div>", unsafe_allow_html=True)
    df_p = carregar_dinamico("produtos")
    if not df_p.empty:
        p_nome = st.selectbox("🔍 SELECIONE O PRODUTO", [""] + df_p['nome'].tolist())
        if p_nome:
            dados_p = df_p[df_p['nome'] == p_nome].iloc[0]
            preco = float(str(dados_p['preco_venda']).replace('R$', '').replace(',', '.'))
            if st.button("ADICIONAR AO CARRINHO"):
                st.session_state.carrinho.append({"produto": p_nome, "preco": preco})
                st.toast("Adicionado!")
                st.rerun()
    if st.session_state.carrinho:
        total = sum(i['preco'] for i in st.session_state.carrinho)
        st.markdown(f"<h2 style='text-align: right; color: #76D72B;'>TOTAL: R$ {total:.2f}</h2>", unsafe_allow_html=True)
        if st.button("🚀 FINALIZAR"):
            st.success("Venda Concluída!")
            st.session_state.carrinho = []
            st.rerun()

elif menu == "📱 Pedidos Online":
    st.title("📱 Pedidos Online")
    df_v = carregar_dinamico("vendas")
    pedidos = df_v[(df_v['pdv'] == st.session_state.unidade) & (df_v['status'] == 'Pendente')] if not df_v.empty and 'status' in df_v.columns else pd.DataFrame()
    if not pedidos.empty:
        st.dataframe(pedidos, use_container_width=True)
        id_p = st.selectbox("ID do Pedido", pedidos.index)
        if st.button("CONFIRMAR ENTREGA"):
            df_v.at[id_p, 'status'] = 'Concluído'
            conn.update(worksheet="vendas", data=df_v)
            st.cache_data.clear()
            st.rerun()
    else: st.info("Sem pedidos pendentes.")

else:
    st.title(menu)
    st.info("Funcionalidade operacional mantida.")
