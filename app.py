import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop - Gestão", layout="wide", page_icon="⚡")

# Inicialização de Estados de Sessão
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'unidade' not in st.session_state:
    st.session_state.unidade = ""
if 'perfil' not in st.session_state:
    st.session_state.perfil = ""

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dinamico(aba):
    return conn.read(worksheet=aba, ttl=0)

# ==================== 2. SISTEMA DE LOGIN OTIMIZADO ====================
if not st.session_state.autenticado:
    st.title("⚡ Flash Stop - Acesso Restrito")
    
    with st.container():
        user = st.text_input("Usuário", placeholder="Digite seu usuário")
        senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
        
        if st.button("Entrar", use_container_width=True):
            # 1. Verificação para Admin (Exemplo manual)
            if user == "admin" and senha == "1234": # Altere para sua senha real
                st.session_state.autenticado = True
                st.session_state.unidade = "Central"
                st.session_state.perfil = "admin"
                st.success("Login realizado com sucesso!")
                time.sleep(0.5)
                st.rerun()  # <--- ESSENCIAL PARA O BOTÃO FUNCIONAR
            
            # 2. Verificação via Planilha (Para PDVs)
            else:
                try:
                    df_pts = carregar_dinamico("pontos")
                    if user in df_pts['nome'].values:
                        senha_correta = str(df_pts[df_pts['nome'] == user]['senha'].values[0])
                        if senha == senha_correta:
                            st.session_state.autenticado = True
                            st.session_state.unidade = user
                            st.session_state.perfil = "pdv"
                            st.success(f"Bem-vindo, {user}!")
                            time.sleep(0.5)
                            st.rerun() # <--- ESSENCIAL PARA O BOTÃO FUNCIONAR
                        else:
                            st.error("Senha incorreta.")
                    else:
                        st.error("Usuário não encontrado.")
                except Exception as e:
                    st.error(f"Erro ao conectar com a base de dados: {e}")
    
    st.stop() # Interrompe o código aqui enquanto não estiver logado

# ==================== 3. DEFINIÇÃO DO MENU ====================
st.sidebar.title("⚡ Flash Stop")
st.sidebar.write(f"📍 **{st.session_state.unidade}**")

opcoes_admin = [
    "📊 Dashboard", "🛒 Self-Checkout", "📱 Pedidos Online", 
    "💰 Entrada Mercadoria", "📦 Inventário", "💸 Despesas",
    "📂 Contabilidade", "📟 Configurações"
]
opcoes_pdv = ["🛒 Self-Checkout", "📱 Pedidos Online", "📦 Inventário"]

if st.session_state.perfil == "admin":
    menu = st.sidebar.radio("Navegação", opcoes_admin)
else:
    menu = st.sidebar.radio("Navegação", opcoes_pdv)

# CSS Customizado (Global)
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    .stButton>button { background-color: #76D72B; color: #000000; border-radius: 8px; font-weight: bold; border: none; }
    .stButton>button:hover { background-color: #5eb022; color: #FFFFFF; }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div { background-color: #1E1E1E; color: #FFFFFF; }
    </style>
""", unsafe_allow_html=True)

# ==================== 4. LÓGICA DE NAVEGAÇÃO (IF/ELIF ÚNICO) ====================

if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_p = carregar_dinamico("produtos")
    
    bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
    liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
    gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
    lucro = liq - gastos

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido", f"R$ {liq:,.2f}")
    c3.metric("Despesas", f"R$ {gastos:,.2f}")
    c4.metric("Lucro Real", f"R$ {lucro:,.2f}")

elif menu == "🛒 Self-Checkout":
    st.subheader("🛒 Carrinho de Compras")
    df_p = carregar_dinamico("produtos")
    p_nome = st.selectbox("Bipar produto...", [""] + df_p['nome'].tolist())
    # ... lógica do carrinho ...
    if not st.session_state.carrinho:
        st.info("Carrinho vazio")

elif menu == "📱 Pedidos Online":
    st.header("📱 Pedidos Recebidos Online")
    df_vendas = carregar_dinamico("vendas")
    pedidos_online = df_vendas[(df_vendas['pdv'] == st.session_state.unidade) & (df_vendas['status'] == 'Pendente')]
    if not pedidos_online.empty:
        st.dataframe(pedidos_online)
    else:
        st.info("Nenhum pedido pendente.")

elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Gestão de Estoque e Preços")
    # ... lógica de entrada ...

elif menu == "📦 Inventário":
    st.header("📦 Gestão de Itens")
    # ... lógica de inventário ...

elif menu == "💸 Despesas":
    st.header("💸 Registro de Custos e Despesas")
    try:
        df_d = carregar_dinamico("despesas")
        col_cadastro, col_historico = st.columns([1, 1.5])
        with col_cadastro:
            with st.form("form_despesa", clear_on_submit=True):
                desc = st.text_input("Descrição")
                val = st.number_input("Valor", min_value=0.0)
                if st.form_submit_button("SALVAR"):
                    st.success("Salvo!")
        with col_historico:
            st.dataframe(df_d)
    except Exception as e:
        st.error(f"Erro: {e}")

elif menu == "📂 Contabilidade":
    st.header("📂 Relatórios Contábeis")
    # ... lógica contábil ...

elif menu == "📟 Configurações":
    st.header("📟 Gestão Operacional")
    # ... lógica de configurações ...

else:
    st.info("Selecione uma opção no menu lateral para começar.")
