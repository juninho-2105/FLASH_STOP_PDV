import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v3.8", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- REGRAS DE NEGÓCIO ---
DIAS_ALERTA_VENCIMENTO = 10  # Configurado para 10 dias conforme solicitado

# --- DEFINIÇÃO DE COLUNAS (Ordem exata do Google Sheets) ---
COLUNAS_PRODUTOS = ["nome", "estoque", "validade", "preco"]
COLUNAS_VENDAS = ["data", "pdv", "maquina", "produto", "valor", "forma"]
COLUNAS_MAQUINAS = ["nome", "tid", "pdv_vinculado"]
COLUNAS_PONTOS = ["nome"]
COLUNAS_FORNECEDORES = ["nome_fantasia", "cnpj_cpf", "contato", "categoria"]
COLUNAS_COMPRAS = ["data", "fornecedor", "produto", "quantidade", "custo_unitario", "custo_total"]

# ==================== FUNÇÕES UTILITÁRIAS ====================
def render_flash_stop_logo(font_size="42px"):
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-family: 'Arial Black', sans-serif; font-size: {font_size}; color: #000000; letter-spacing: -2px; margin-bottom: 0;">
                FLASH <span style="color: #7CFC00; font-style: italic;">STOP</span>
            </h1>
            <p style="font-family: sans-serif; font-size: 12px; color: #666; margin-top: -10px; font-weight: bold;">
                CONVENIÊNCIA INTELIGENTE
            </p>
        </div>
    """, unsafe_allow_html=True)

def carregar_aba(nome_aba, colunas_padrao):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        df = df.dropna(how='all')
        if df.empty:
            return pd.DataFrame(columns=colunas_padrao)
        return df
    except:
        return pd.DataFrame(columns=colunas_padrao)

# ==================== SISTEMA DE LOGIN ====================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        render_flash_stop_logo(font_size="55px")
        st.subheader("Acesso ao Sistema")
        with st.form("login"):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                try:
                    adm_u = st.secrets["auth"]["admin_user"]
                    adm_s = st.secrets["auth"]["admin_password"]
                except:
                    adm_u, adm_s = "admin", "flash123"

                if u == adm_u and s == adm_s:
                    st.session_state.autenticado = True
                    st.rerun()
                else: st.error("Credenciais inválidas")
    st.stop()

# ==================== MENU LATERAL ====================
with st.sidebar:
    render_flash_stop_logo(font_size="30px")
    st.divider()
    menu = st.radio("Navegação", [
        "📊 Dashboard & Alertas", 
        "🛍️ Venda (PDV)", 
        "💰 Lançamento de Custos",
        "📦 Gestão de Estoque", 
        "🚚 Fornecedores",
        "📍 Cadastrar PDV", 
        "📟 Máquinas (Automação)"
    ])
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

# ==================== 1. DASHBOARD & ALERTAS ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Performance e Alertas Críticos")
    
    vendas = carregar_aba("vendas", COLUNAS_VENDAS)
    compras = carregar_aba("compras", COLUNAS_COMPRAS)
    produtos = carregar_aba("produtos", COLUNAS_PRODUTOS)
    
    # Cálculos Financeiros
    faturamento = pd.to_numeric(vendas['valor'], errors='coerce').sum()
    custos_totais = pd.to_numeric(compras['custo_total'], errors='coerce').sum()
    lucro = faturamento - custos_totais
    margem = (lucro / faturamento * 100) if faturamento > 0 else 0

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faturamento", f"R$ {faturamento:,.2f}")
    c2.metric("Custos", f"R$ {custos_totais:,.2f}")
    c3.metric("Lucro Est.", f"R$ {lucro:,.2f}")
    c4.metric("Margem", f"{margem:.1f}%")

    st.divider()
    
    # --- LÓGICA DE ALERTAS ---
    hoje = datetime.now()
    produtos['validade_dt'] = pd.to_datetime(produtos['validade'], dayfirst=True, errors='coerce')
    produtos['estoque'] = pd.to_numeric(produtos['estoque'], errors='coerce').fillna(0)
    
    limite_vencimento = hoje + timedelta(days=DIAS_ALERTA_VENCIMENTO)
    
    vencidos = produtos[produtos['validade_dt'] < hoje]
    proximo_vencer = produtos[(produtos['validade_dt'] >= hoje) & (produtos['validade_dt'] <= limite_vencimento)]
    baixo_estoque = produtos[produtos['estoque'] < 5]

    col_a1, col_a2, col_a3 = st.columns(3)
    
    with col_
