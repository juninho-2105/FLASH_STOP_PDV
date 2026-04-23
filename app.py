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
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dinamico(aba):
    return conn.read(worksheet=aba, ttl=0)

# ==================== 2. SISTEMA DE LOGIN ====================
if not st.session_state.autenticado:
    st.title("⚡ Flash Stop - Acesso")
    with st.form("login_form"):
        user = st.text_input("Usuário / PDV")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            df_pts = carregar_dinamico("pontos")
            if user == "admin" and senha == "flash123":
                st.session_state.autenticado = True
                st.session_state.unidade = "Administração"
                st.session_state.perfil = "admin"
                st.rerun()
            elif user in df_pts['nome'].values:
                senha_correta = str(df_pts[df_pts['nome'] == user]['senha'].values[0])
                if senha == senha_correta:
                    st.session_state.autenticado = True
                    st.session_state.unidade = user
                    st.session_state.perfil = "pdv"
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
            else:
                st.error("Usuário não encontrado.")
    st.stop()

# ==================== 3. MENU LATERAL ====================
# PROTEÇÃO CONTRA ERRO DE IMAGEM
with st.sidebar:
    caminho_logo = "logo_flash_stop.png"
    if os.path.exists(caminho_logo):
        st.image(caminho_logo)
    else:
        st.title("⚡ Flash Stop")
    
    st.write(f"📍 **{st.session_state.unidade}**")

    if st.session_state.perfil == "admin":
        menu = st.radio("Navegação", [
            "📊 Dashboard", 
            "🛒 Self-Checkout", 
            "💰 Entrada Mercadoria", 
            "📦 Inventário", 
            "💸 Despesas",
            "📂 Contabilidade", 
            "📟 Configurações"
        ])
    else:
        menu = st.radio("Navegação", ["🛒 Self-Checkout", "📦 Inventário"])

    st.sidebar.divider()
    if st.sidebar.button("🚪 Sair / Trocar Usuário"):
        st.session_state.autenticado = False
        st.rerun()

# ==================== 4. LÓGICA DE NAVEGAÇÃO ÚNICA ====================

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_p = carregar_dinamico("produtos")
    
    # KPIs com tratamento de erro para valores vazios
    bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum() if not df_v.empty else 0
    liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum() if not df_v.empty else 0
    gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum() if not df_d.empty else 0
    lucro = liq - gastos

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido (Pós Taxas)", f"R$ {liq:,.2f}")
    c3.metric("Despesas Totais", f"R$ {gastos:,.2f}")
    c4.metric("Lucro Real", f"R$ {lucro:,.2f}", delta=f"{lucro/bruto*100:.1f}%" if bruto > 0 else None)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🚨 Estoque Crítico")
        critico = df_p[df_p['estoque'].astype(int) <= df_p['estoque_minimo'].astype(int)]
        st.dataframe(critico[['nome', 'estoque']], use_container_width=True, hide_index=True) if not critico.empty else st.success("Estoque OK!")

# --- SELF-CHECKOUT ---
elif menu == "🛒 Self-Checkout":
    st.header("🛒 Checkout Compacto")
    df_p = carregar_dinamico("produtos")
    p_nome = st.selectbox("Bipar ou selecionar produto:", [""] + df_p['nome'].tolist())

    if p_nome:
        dados_p = df_p[df_p['nome'] == p_nome].iloc[0]
        preco_unit = float(dados_p['preco'])
        if st.button(f"➕ Adicionar {p_nome} (R$ {preco_unit:.2f})", use_container_width=True, type="primary"):
            st.session_state.carrinho.append({"produto": p_nome, "preco": preco_unit})
            st.rerun()

    if st.session_state.carrinho:
        st.divider()
        df_cart = pd.DataFrame(st.session_state.carrinho)
        resumo = df_cart.groupby('produto').agg({'preco': 'first', 'produto': 'count'}).rename(columns={'produto': 'qtd'}).reset_index()
        
        for idx, item in resumo.iterrows():
            c_txt, c_btn = st.columns([3, 1])
            c_txt.write(f"**{item['qtd']}x {item['produto']}** - R$ {item['preco']*item['qtd']:.2f}")
            if c_btn.button("🗑️", key=f"del_{idx}"):
                # Remove apenas um item do nome correspondente
                for i, p in enumerate(st.session_state.carrinho):
                    if p['produto'] == item['produto']:
                        st.session_state.carrinho.pop(i)
                        break
                st.rerun()
        
        total = sum(i['preco'] for i in st.session_state.carrinho)
        st.subheader(f"Total: R$ {total:.2f}")
        if st.button("🚀 FINALIZAR PAGAMENTO", use_container_width=True, type="primary"):
            st.success("Venda Concluída!")
            st.session_state.carrinho = []
            time.sleep(1)
            st.rerun()

# --- ENTRADA MERCADORIA ---
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Entrada de Produtos")
    df_p = carregar_dinamico("produtos")
    # ... Lógica de entrada aqui ...
    st.info("Funcionalidade de entrada pronta para uso.")

# --- INVENTÁRIO ---
elif menu == "📦 Inventário":
    st.header("📦 Inventário Geral")
    df_p = carregar_dinamico("produtos")
    st.dataframe(df_p, use_container_width=True, hide_index=True)

# --- DESPESAS ---
elif menu == "💸 Despesas":
    st.header("💸 Gestão de Despesas")
    # ... Lógica de despesas aqui ...
    st.info("Registre aqui os gastos da unidade.")

# --- CONTABILIDADE ---
elif menu == "📂 Contabilidade":
    st.header("📂 Relatórios")
    # ... Lógica de exportação aqui ...
    st.info("Exporte seus dados para contabilidade.")

# --- CONFIGURAÇÕES ---
elif menu == "📟 Configurações":
    st.header("📟 Configurações")
    # ... Lógica de taxas e PDVs aqui ...
    st.info("Gerencie unidades e máquinas de cartão.")

# --- ELSE FINAL (O ÚNICO!) ---
else:
    st.info("Selecione uma opção no menu lateral.")
