import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

# --- CONFIGURAÇÕES INICIAIS ---
st.set_page_config(page_title="Flash Stop PDV", layout="centered")

# Simulação de conexão (Substitua pela sua lógica de conn.update / gspread)
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# Função auxiliar para carregar dados (Exemplo)
def carregar_dinamico(aba):
    # Aqui entraria sua lógica de: return conn.read(worksheet=aba)
    # Criando DFs vazios para o código não quebrar na demonstração:
    return pd.DataFrame() 

# --- MENU LATERAL ---
with st.sidebar:
    st.image("logo_flash_stop.png") # Certifique-se de que o arquivo existe
    menu = st.radio("Navegação", [
        "🏠 Home", 
        "🛒 Self-Checkout", 
        "💰 Entrada Mercadoria", 
        "📊 Dashboard", 
        "📟 Configurações"
    ])

# ==================== 1. HOME ====================
if menu == "🏠 Home":
    st.title("Bem-vindo à Flash Stop")
    st.write("Selecione uma opção no menu lateral para começar.")

# ==================== 2. SELF-CHECKOUT (COMPACTO) ====================
elif menu == "🛒 Self-Checkout":
    st.header("🛒 Finalizar Compra")
    
    if not st.session_state.carrinho:
        st.info("Seu carrinho está vazio. Adicione produtos na aba de vendas.")
    else:
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
        st.markdown(f"### Total: R$ {total_venda:.2f}")
        
        forma_pagto = st.radio("Pagamento:", ["Pix", "Débito", "Crédito"], horizontal=True, label_visibility="collapsed")

        if st.button("✅ FINALIZAR E PAGAR", use_container_width=True, type="primary"):
            st.success("Venda realizada com sucesso!")
            st.session_state.carrinho = []
            time.sleep(2)
            st.rerun()

# ==================== 3. ENTRADA MERCADORIA (PADRÃO BR) ====================
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Gestão de Estoque")
    df_p = carregar_dinamico("produtos")
    
    tipo_acao = st.radio("Ação:", ["Repor Estoque", "Novo Cadastro"], horizontal=True)
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: qtd = st.number_input("Qtd:", min_value=1)
    with c2: custo = st.number_input("Custo:", min_value=0.0)
    with c3: margem = st.number_input("Margem %:", value=30.0)
    with c4: val = st.date_input("Validade:", format="DD/MM/YYYY")
    
    if st.button("Salvar Entrada", use_container_width=True):
        st.success("Estoque atualizado!")

# ==================== 4. CONFIGURAÇÕES (GESTÃO E EXCLUSÃO) ====================
elif menu == "📟 Configurações":
    st.header("📟 Configurações do Sistema")
    aba_pdv, aba_maq = st.tabs(["📍 PDVs", "💳 Máquinas"])
    
    with aba_pdv:
        df_pts = carregar_dinamico("pontos")
        # Interface de cadastro de PDV...
        # Loop de exclusão de PDV que você pediu:
        if not df_pts.empty:
            for idx, row in df_pts.iterrows():
                c_txt, c_del = st.columns([4, 1])
                c_txt.write(f"🏠 {row['nome']}")
                if c_del.button("🗑️", key=f"del_{idx}"):
                    # Lógica de exclusão aqui
                    st.rerun()

    with aba_maq:
        st.subheader("Vincular Máquina")
        # Formulário de máquinas com selectbox de PDV para vínculo
        st.info("Vincule as taxas ao PDV correspondente.")

# ==================== 5. ELSE (FINAL DE TUDO) ====================
else:
    st.info("Selecione uma opção válida no menu lateral.")
