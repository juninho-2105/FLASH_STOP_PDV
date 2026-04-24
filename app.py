import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop PDV", layout="wide", initial_sidebar_state="collapsed")

# 1. HEARTBEAT (Mantém a conexão ativa a cada 5 minutos)
st_autorefresh(interval=5 * 60 * 1000, key="heartbeat_flashstop")

# 2. CONEXÃO COM GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dinamico(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df is not None and not df.empty:
            df.columns = [c.lower().strip() for c in df.columns]
        return df
    except:
        return pd.DataFrame()

# ==================== GESTÃO DE ACESSOS (URL + SENHAS) ====================
# Dicionário onde a senha define automaticamente a unidade
ACESSOS = {
    "flash01": "Flash Stop 01",
    "flash02": "Flash Stop 02",
    "admin2026": "Administrador Geral"
}
TOKEN_MESTRE = "flash2026" # Token para o link automático via URL

if "logado" not in st.session_state:
    st.session_state["logado"] = False

# --- FLUXO 1: LOGIN AUTOMÁTICO VIA URL ---
query_params = st.query_params
if "pdv" in query_params and "token" in query_params:
    if query_params["token"] == TOKEN_MESTRE:
        st.session_state["logado"] = True
        st.session_state["unidade_atual"] = query_params["pdv"]

# --- FLUXO 2: LOGIN MANUAL (Sem seletor de unidade, apenas senha) ---
if not st.session_state["logado"]:
    st.markdown("<h1 style='text-align: center; color: #32CD32;'>⚡ flash stop</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            senha_dig = st.text_input("Senha da Unidade", type="password")
            if st.form_submit_button("Acessar PDV", use_container_width=True):
                if senha_dig in ACESSOS:
                    st.session_state["logado"] = True
                    st.session_state["unidade_atual"] = ACESSOS[senha_dig]
                    st.rerun()
                else:
                    st.error("Senha inválida.")
    st.stop()

# ==================== MENU LATERAL ====================
with st.sidebar:
    st.write(f"📍 **{st.session_state['unidade_atual']}**")
    menu = st.radio("Navegação", ["🛒 Checkout", "📦 Inventário", "📊 Dashboard"])
    if st.button("Sair"):
        st.session_state["logado"] = False
        st.rerun()

# ==================== ABA: INVENTÁRIO (SÓ VÊ O SEU) ====================
if menu == "📦 Inventário":
    st.header(f"📦 Inventário - {st.session_state['unidade_atual']}")
    
    df_geral = carregar_dinamico("produtos")
    df_estoque = carregar_dinamico("estoque_pdv")

    # Filtro rígido: se não for Admin, só vê a própria unidade
    unidade_ativa = st.session_state["unidade_atual"]
    if unidade_ativa == "Administrador Geral":
        unidade_ativa = st.selectbox("Ver unidade:", df_estoque['unidade'].unique() if not df_estoque.empty else ["Flash Stop 01"])

    aba_geral, aba_unidade = st.tabs(["🌎 Catálogo Geral", "📍 Estoque Local"])

    with aba_geral:
        if not df_geral.empty:
            st.dataframe(df_geral[["nome", "preco_venda", "categoria"]], use_container_width=True, hide_index=True)

    with aba_unidade:
        df_local = df_estoque[df_estoque['unidade'] == unidade_ativa] if not df_estoque.empty else pd.DataFrame()
        
        # Sincronização automática de novos produtos
        if not df_geral.empty:
            faltantes = [p for p in df_geral['nome'].tolist() if p not in df_local['nome'].tolist()]
            if faltantes and st.button(f"📥 Sincronizar Itens"):
                novos = pd.DataFrame([{"unidade": unidade_ativa, "nome": p, "quantidade": 0, "validade": "A definir", "minimo_alerta": 5} for p in faltantes])
                df_estoque = pd.concat([df_estoque, novos], ignore_index=True)
                conn.update(worksheet="estoque_pdv", data=df_estoque)
                st.rerun()

        if not df_local.empty:
            # Exibição Exata: Nome, Quantidade e Validade
            st.dataframe(df_local[["nome", "quantidade", "validade", "minimo_alerta"]], use_container_width=True, hide_index=True)

            with st.form("edit_estoque"):
                p_edit = st.selectbox("Produto", df_local['nome'].tolist())
                c1, c2, c3 = st.columns(3)
                n_qtd = c1.number_input("Qtd Existente", value=0)
                n_val = c2.text_input("Validade (DD/MM/AAAA)")
                n_min = c3.number_input("Mínimo Alerta", value=5)
                if st.form_submit_button("Salvar Alterações"):
                    idx = df_estoque[(df_estoque['unidade'] == unidade_ativa) & (df_estoque['nome'] == p_edit)].index[0]
                    df_estoque.at[idx, 'quantidade'] = n_qtd
                    df_estoque.at[idx, 'validade'] = n_val
                    df_estoque.at[idx, 'minimo_alerta'] = n_min
                    conn.update(worksheet="estoque_pdv", data=df_estoque)
                    st.success("Atualizado!")
                    st.rerun()

# ==================== ABA: DASHBOARD (ALERTAS CORRIGIDOS) ====================
elif menu == "📊 Dashboard":
    st.header(f"📊 Dashboard - {st.session_state['unidade_atual']}")
    
    df_v = carregar_dinamico("vendas")
    df_e = carregar_dinamico("estoque_pdv")

    # Métricas Financeiras
    if not df_v.empty:
        # Se não for admin, filtra vendas só desta unidade
        df_un = df_v if st.session_state['unidade_atual'] == "Administrador Geral" else df_v[df_v['unidade'] == st.session_state['unidade_atual']]
        bruto = pd.to_numeric(df_un['valor_bruto'], errors='coerce').sum()
        st.metric("Faturamento Unidade", f"R$ {bruto:,.2f}")

    st.divider()
    st.subheader("🚨 Alertas desta Unidade")
    
    if not df_e.empty:
        # Filtro de alertas específico para a unidade logada
        df_e_un = df_e[df_e['unidade'] == st.session_state['unidade_atual']]
        
        c1, c2 = st.columns(2)
        with c1:
            df_e_un['quantidade'] = pd.to_numeric(df_e_un['quantidade'], errors='coerce').fillna(0)
            baixo = df_e_un[df_e_un['quantidade'] <= pd.to_numeric(df_e_un['minimo_alerta'], errors='coerce').fillna(5)]
            if not baixo.empty:
                for _, r in baixo.iterrows(): st.error(f"**{r['nome']}** baixo estoque!")
            else: st.success("Estoque OK")
            
        with c2:
            df_e_un['dt'] = pd.to_datetime(df_e_un['validade'], dayfirst=True, errors='coerce')
            vencendo = df_e_un[(df_e_un['dt'].notnull()) & (df_e_un['dt'] <= datetime.now() + timedelta(days=7))]
            if not vencendo.empty:
                for _, r in vencendo.iterrows(): st.warning(f"**{r['nome']}** vencendo!")
            else: st.success("Validades OK")

elif menu == "🛒 Checkout":
    st.title("🛒 Área de Checkout")
    st.write(f"PDV: {st.session_state['unidade_atual']}")
