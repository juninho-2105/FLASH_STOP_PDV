import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# ==================== 1. CONFIGURAÇÕES E ESTILO ====================
st.set_page_config(page_title="Flash Stop PDV", layout="centered")

# Inicialização de variáveis de sessão
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'unidade_atual' not in st.session_state:
    st.session_state.unidade_atual = "Não Identificada"

# Função para carregar dados (Substitua pela sua lógica gspread/conn)
def carregar_dinamico(aba):
    try:
        # Exemplo: return conn.read(worksheet=aba)
        return pd.DataFrame() 
    except:
        return pd.DataFrame()

# ==================== 2. MENU LATERAL COM PROTEÇÃO DE LOGO ====================
with st.sidebar:
    caminho_logo = "logo_flash_stop.png"
    if os.path.exists(caminho_logo):
        st.image(caminho_logo)
    else:
        st.title("⚡ Flash Stop")
        st.caption("Automação Comercial")
    
    st.divider()
    menu = st.radio("Navegação", [
        "🏠 Home", 
        "🛒 Self-Checkout", 
        "💰 Entrada Mercadoria", 
        "📊 Dashboard", 
        "📟 Configurações"
    ])

# ==================== 3. LÓGICA DOS MENUS ====================

# --- HOME ---
if menu == "🏠 Home":
    st.title("🏠 Painel de Controle")
    st.write(f"Unidade: **{st.session_state.unidade_atual}**")
    st.info("Utilize o menu lateral para gerenciar vendas, estoque ou configurações.")

# --- SELF-CHECKOUT (LAYOUT COMPACTO + FORMAS PAGTO) ---
elif menu == "🛒 Self-Checkout":
    st.header("🛒 Checkout")
    
    if not st.session_state.carrinho:
        st.info("O carrinho está vazio.")
    else:
        # Cabeçalho da lista
        for i, item in enumerate(st.session_state.carrinho):
            col_nome, col_controles, col_subtotal = st.columns([2, 1.5, 1])
            
            with col_nome:
                st.markdown(f"**{item['nome']}**")
                st.caption(f"R$ {item['preco']:.2f}/un")
            
            with col_controles:
                c_menos, c_qtd, c_mais = st.columns([1, 1, 1])
                with c_menos:
                    if st.button("➖", key=f"min_{i}"):
                        if st.session_state.carrinho[i]['qtd'] > 1:
                            st.session_state.carrinho[i]['qtd'] -= 1
                            st.rerun()
                        else:
                            st.session_state.carrinho.pop(i)
                            st.rerun()
                with c_qtd:
                    st.markdown(f"<div style='text-align:center; padding-top:5px'>{item['qtd']}</div>", unsafe_allow_html=True)
                with c_mais:
                    if st.button("➕", key=f"plus_{i}"):
                        st.session_state.carrinho[i]['qtd'] += 1
                        st.rerun()
            
            with col_subtotal:
                sub = item['preco'] * item['qtd']
                st.markdown(f"**R$ {sub:.2f}**")
            st.divider()

        total_venda = sum(item['preco'] * item['qtd'] for item in st.session_state.carrinho)
        st.subheader(f"Total: R$ {total_venda:.2f}")
        
        # Formas de Pagamento Horizontais
        forma_pagto = st.radio("Pagamento:", ["Pix", "Débito", "Crédito"], horizontal=True, label_visibility="collapsed")

        if st.button("✅ FINALIZAR VENDA", use_container_width=True, type="primary"):
            # Lógica para salvar venda na planilha de vendas...
            st.success(f"Venda no {forma_pagto} finalizada com sucesso!")
            st.session_state.carrinho = []
            time.sleep(1.5)
            st.rerun()

# --- ENTRADA MERCADORIA (CALENDÁRIO BR + PRECO_VENDA) ---
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Gestão de Estoque e Preços")
    df_p = carregar_dinamico("produtos")
    
    tipo_acao = st.radio("Ação:", ["Repor Estoque", "Cadastrar Novo"], horizontal=True)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: qtd = st.number_input("Qtd:", min_value=1)
    with c2: custo = st.number_input("Custo Un (R$):", min_value=0.0, format="%.2f")
    with c3: margem = st.number_input("Margem Lucro (%):", value=30.0)
    with c4: 
        # Calendário Padrão Brasileiro
        val = st.date_input("Validade:", format="DD/MM/YYYY", value=datetime.now() + timedelta(days=90))

    preco_sugerido = custo * (1 + (margem / 100))
    
    # Caixa de destaque para o preço sugerido
    st.markdown(f"""
    <div style="background-color:#f0f2f6;padding:10px;border-radius:10px;border-left:5px solid #2e7d32; margin-bottom:15px">
        Sugestão de Preço: <b>R$ {preco_sugerido:.2f}</b>
    </div>
    """, unsafe_allow_html=True)
    
    preco_final = st.number_input("Preço de Venda Final:", value=preco_sugerido, format="%.2f")

    if st.button("🚀 ATUALIZAR PLANILHA", use_container_width=True):
        # Aqui você usa df_p.at[idx, 'preco_venda'] = preco_final
        st.success("Produto atualizado na coluna 'preco_venda'!")

# --- DASHBOARD ---
elif menu == "📊 Dashboard":
    st.header("📊 Dashboard de Performance")
    st.info("Integre aqui seus gráficos de vendas e estoque baixo.")

# --- CONFIGURAÇÕES (EXCLUIR PDV E VÍNCULO DE MÁQUINA) ---
elif menu == "📟 Configurações":
    st.header("📟 Configurações do Sistema")
    aba_pdv, aba_maquina = st.tabs(["📍 Gestão de PDVs", "💳 Máquinas e Taxas"])
    
    with aba_pdv:
        st.subheader("Unidades Cadastradas")
        df_pts = carregar_dinamico("pontos")
        
        # Simulação de listagem para demonstrar a lixeira
        if not df_pts.empty:
            for idx, row in df_pts.iterrows():
                col_txt,
