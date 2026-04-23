import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time
import os

# ==================== 1. CONFIGURAÇÕES ====================
st.set_page_config(page_title="Flash Stop - Gestão", layout="wide", page_icon="⚡")

if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'carrinho' not in st.session_state: st.session_state.carrinho = []
if 'unidade' not in st.session_state: st.session_state.unidade = ""
if 'perfil' not in st.session_state: st.session_state.perfil = ""

# Conexão com Google Sheets
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro na conexão com Google Sheets. Verifique seu arquivo secrets.")
    st.stop()

def carregar_dinamico(aba):
    try:
        return conn.read(worksheet=aba, ttl=0)
    except:
        return pd.DataFrame()

# ==================== 2. LOGIN ====================
if not st.session_state.autenticado:
    st.title("⚡ Flash Stop - Acesso")
    with st.form("login"):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            df_pts = carregar_dinamico("pontos")
            if u == "admin" and s == "flash123":
                st.session_state.update({"autenticado": True, "unidade": "Adm", "perfil": "admin"})
                st.rerun()
            elif not df_pts.empty and u in df_pts['nome'].values:
                if s == str(df_pts[df_pts['nome'] == u]['senha'].values[0]):
                    st.session_state.update({"autenticado": True, "unidade": u, "perfil": "pdv"})
                    st.rerun()
                else:
                    st.error("Senha incorreta.")
            else:
                st.error("Usuário não encontrado.")
    st.stop()

# ==================== 3. MENU LATERAL ====================
with st.sidebar:
    if os.path.exists("logo_flash_stop.png"):
        st.image("logo_flash_stop.png")
    else:
        st.title("⚡ FLASH STOP")
    
    st.write(f"📍 Unidade: **{st.session_state.unidade}**")
    
    opcoes_admin = ["📊 Dashboard", "🛒 Checkout", "💰 Entrada Mercadoria", "📦 Inventário", "💸 Despesas", "📂 Contabilidade", "📟 Configurações"]
    opcoes_pdv = ["🛒 Checkout", "📦 Inventário"]
    
    menu = st.radio("Navegação", opcoes_admin if st.session_state.perfil == "admin" else opcoes_pdv)
    
    st.divider()
    if st.button("🚪 Sair"):
        st.session_state.autenticado = False
        st.rerun()

# ==================== 4. TELAS DO SISTEMA ====================

if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_p = carregar_dinamico("produtos")

    if not df_v.empty:
        bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
        liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
        gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum() if not df_d.empty else 0
        lucro = liq - gastos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
        c2.metric("Líquido (Pós Taxas)", f"R$ {liq:,.2f}")
        c3.metric("Despesas Totais", f"R$ {gastos:,.2f}")
        c4.metric("Lucro Real", f"R$ {lucro:,.2f}")
        
        # Gráfico Simples
        df_v['data_dt'] = pd.to_datetime(df_v['data'], format="%d/%m/%Y %H:%M", errors='coerce')
        vendas_dia = df_v.groupby(df_v['data_dt'].dt.date)['valor_bruto'].sum()
        st.area_chart(vendas_dia)
    else:
        st.info("Sem dados de vendas para o dashboard.")

elif menu == "🛒 Checkout":
    st.header("🛒 Self-Checkout")
    df_p = carregar_dinamico("produtos")
    
    p_nome = st.selectbox("Bipe ou selecione o item:", [""] + df_p['nome'].tolist())
    if p_nome:
        dados_p = df_p[df_p['nome'] == p_nome].iloc[0]
        preco = float(dados_p['preco'])
        if st.button(f"Adicionar {p_nome} - R$ {preco:.2f}", use_container_width=True):
            st.session_state.carrinho.append({"produto": p_nome, "preco": preco})
            st.toast("Adicionado!")
            st.rerun()

    if st.session_state.carrinho:
        st.divider()
        total = sum(item['preco'] for item in st.session_state.carrinho)
        st.subheader(f"Total Carrinho: R$ {total:.2f}")
        if st.button("🚀 FINALIZAR PAGAMENTO", type="primary"):
            st.success("Venda registrada!")
            st.session_state.carrinho = []
            time.sleep(1)
            st.rerun()

elif menu == "📦 Inventário":
    st.header("📦 Gestão de Estoque")
    df_p = carregar_dinamico("produtos")
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True, hide_index=True)
        
        # Alerta de estoque baixo
        critico = df_p[df_p['estoque'].astype(int) <= df_p['estoque_minimo'].astype(int)]
        if not critico.empty:
            st.warning("⚠️ Itens abaixo do estoque mínimo!")
            st.table(critico[['nome', 'estoque']])

elif menu == "💸 Despesas":
    st.header("💸 Registro de Despesas")
    try:
        df_d = carregar_dinamico("despesas")
        with st.form("nova_despesa"):
            desc = st.text_input("Descrição")
            val = st.number_input("Valor", min_value=0.0)
            if st.form_submit_button("Salvar"):
                nova = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "descricao": desc, "valor": val}])
                df_atualizado = pd.concat([df_d, nova], ignore_index=True)
                conn.update(worksheet="despesas", data=df_atualizado)
                st.success("Salvo!")
                st.rerun()
    except Exception as e:
        st.error(f"Erro na aba despesas: {e}")

elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Entrada de Produtos")
    st.write("Funcionalidade para cadastro e reposição.")

elif menu == "📂 Contabilidade":
    st.header("📂 Relatórios")
    st.write("Área de exportação de dados.")

elif menu == "📟 Configurações":
    st.header("📟 Configuração do Sistema")
    st.write("Gestão de PDVs e Taxas.")
