import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time
import os

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
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro na conexão com o Google Sheets. Verifique o arquivo .streamlit/secrets.toml")
    st.stop()

def carregar_dinamico(aba):
    try:
        return conn.read(worksheet=aba, ttl=0)
    except:
        return pd.DataFrame()

# ==================== 2. SISTEMA DE LOGIN ====================
if not st.session_state.autenticado:
    st.title("⚡ Flash Stop - Acesso")
    with st.form("login_form"):
        user = st.text_input("Usuário / PDV")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            df_pts = carregar_dinamico("pontos")
            # Login Admin
            if user == "admin" and senha == "flash123":
                st.session_state.autenticado = True
                st.session_state.unidade = "Administração"
                st.session_state.perfil = "admin"
                st.rerun()
            # Login Unidades
            elif not df_pts.empty and user in df_pts['nome'].values:
                senha_correta = str(df_pts[df_pts['nome'] == user]['senha'].values[0])
                if senha == senha_correta:
                    st.session_state.autenticado = True
                    st.session_state.unidade = user
                    st.session_state.perfil = "pdv"
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
            else:
                st.error("Usuário não encontrado ou erro na planilha 'pontos'.")
    st.stop()

# ==================== 3. BARRA LATERAL (MENU) ====================
with st.sidebar:
    # Mostra logo ou texto (Sem dar erro!)
    if os.path.exists("logo_flash_stop.png"):
        st.image("logo_flash_stop.png")
    else:
        st.title("⚡ Flash Stop")
    
    st.write(f"📍 Unidade: **{st.session_state.unidade}**")
    st.divider()

    if st.session_state.perfil == "admin":
        opcoes = ["📊 Dashboard", "🛒 Checkout", "💰 Entrada", "📦 Inventário", "💸 Despesas", "📂 Contabilidade", "📟 Configurações"]
    else:
        opcoes = ["🛒 Checkout", "📦 Inventário"]
    
    menu = st.radio("Navegação", opcoes)
    
    st.divider()
    if st.button("🚪 Sair"):
        st.session_state.autenticado = False
        st.rerun()

# ==================== 4. TELAS DO SISTEMA ====================

if menu == "📊 Dashboard":
    st.header("📊 Painel Administrativo")
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    
    c1, c2, c3 = st.columns(3)
    bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum() if not df_v.empty else 0
    gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum() if not df_d.empty else 0
    
    c1.metric("Vendas Brutas", f"R$ {bruto:,.2f}")
    c2.metric("Total Despesas", f"R$ {gastos:,.2f}")
    c3.metric("Saldo", f"R$ {bruto - gastos:,.2f}")

elif menu == "🛒 Checkout":
    st.header("🛒 Self-Checkout")
    df_p = carregar_dinamico("produtos")
    
    if not df_p.empty:
        produto = st.selectbox("Selecione ou bipe o item:", [""] + df_p['nome'].tolist())
        if produto:
            dados = df_p[df_p['nome'] == produto].iloc[0]
            preco = float(dados['preco']) if 'preco' in dados else 0.0
            if st.button(f"Adicionar {produto} - R$ {preco:.2f}", use_container_width=True):
                st.session_state.carrinho.append({"item": produto, "preco": preco})
                st.toast("Adicionado!")
    
    if st.session_state.carrinho:
        st.write("---")
        total = sum(i['preco'] for i in st.session_state.carrinho)
        st.write(f"### Total: R$ {total:.2f}")
        if st.button("PAGAR", type="primary", use_container_width=True):
            st.success("Venda enviada!")
            st.session_state.carrinho = []
            time.sleep(1)
            st.rerun()

elif menu == "📦 Inventário":
    st.header("📦 Estoque Atual")
    st.dataframe(carregar_dinamico("produtos"), use_container_width=True)

elif menu == "💰 Entrada":
    st.header("💰 Entrada de Mercadoria")
    st.write("Funcionalidade em desenvolvimento...")

elif menu == "💸 Despesas":
    st.header("💸 Lançamento de Gastos")
    st.write("Funcionalidade em desenvolvimento...")

elif menu == "📂 Contabilidade":
    st.header("📂 Relatórios para Impressão")
    st.write("Funcionalidade em desenvolvimento...")

elif menu == "📟 Configurações":
    st.header("📟 Gestão de Unidades e Taxas")
    st.write("Funcionalidade em desenvolvimento...")

else:
    st.info("Selecione uma opção no menu lateral.")
