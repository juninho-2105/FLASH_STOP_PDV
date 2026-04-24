import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(
    page_title="Flash Stop PDV", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 1. HEARTBEAT: Atualiza silenciosamente a cada 5 minutos para manter a sessão viva
st_autorefresh(interval=5 * 60 * 1000, key="heartbeat_flashstop")

# 2. CONEXÃO COM GOOGLE SHEETS
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dinamico(aba):
    """Lê os dados da planilha e normaliza os cabeçalhos para minúsculo"""
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df is not None and not df.empty:
            df.columns = [c.lower().strip() for c in df.columns]
        return df
    except Exception as e:
        return pd.DataFrame()

# ==================== GESTÃO DE ACESSOS (CONFIGURAÇÃO) ====================
# Dicionário de Senhas: A senha digitada define automaticamente a unidade
ACESSOS = {
    "flash01": "Flash Stop 01",
    "flash02": "Flash Stop 02",
    "admin2026": "Administrador Geral"
}
TOKEN_MESTRE = "flash2026" # Usado para o login automático via URL

if "logado" not in st.session_state:
    st.session_state["logado"] = False

# --- FLUXO 1: LOGIN AUTOMÁTICO VIA URL (?pdv=Nome&token=flash2026) ---
query_params = st.query_params
if "pdv" in query_params and "token" in query_params:
    if query_params["token"] == TOKEN_MESTRE:
        st.session_state["logado"] = True
        st.session_state["unidade_atual"] = query_params["pdv"]

# --- FLUXO 2: INTERFACE DE LOGIN MANUAL ---
if not st.session_state["logado"]:
    st.markdown("<h1 style='text-align: center; color: #32CD32;'>⚡ flash stop</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            st.write("### Identificação do Totem")
            senha_digitada = st.text_input("Digite a Senha da Unidade", type="password")
            btn_entrar = st.form_submit_button("Acessar PDV", use_container_width=True)
            
            if btn_entrar:
                if senha_digitada in ACESSOS:
                    st.session_state["logado"] = True
                    st.session_state["unidade_atual"] = ACESSOS[senha_digitada]
                    st.success(f"Conectado com sucesso!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Senha incorreta. Verifique os dados da unidade.")
    st.stop()

# ==================== MENU DE NAVEGAÇÃO ====================
with st.sidebar:
    st.markdown("## ⚡ flash stop")
    st.info(f"📍 **Unidade:** {st.session_state['unidade_atual']}")
    menu = st.radio("Navegação", ["🛒 Checkout", "📦 Inventário", "📊 Dashboard", "💰 Despesas"])
    
    st.divider()
    if st.button("Sair / Trocar de Unidade"):
        st.session_state["logado"] = False
        st.rerun()

# ==================== ABA: DASHBOARD (MÉTRICAS + ALERTAS) ====================
if menu == "📊 Dashboard":
    st.header(f"📊 Painel de Controle - {st.session_state['unidade_atual']}")
    
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_estoque_local = carregar_dinamico("estoque_pdv")

    # --- MÉTRICAS FINANCEIRAS ---
    st.subheader("💰 Resumo Financeiro")
    if not df_v.empty:
        # Garante que os valores sejam numéricos
        df_v['valor_bruto'] = pd.to_numeric(df_v['valor_bruto'], errors='coerce').fillna(0)
        df_v['valor_liquido'] = pd.to_numeric(df_v['valor_liquido'], errors='coerce').fillna(0)
        
        # Filtra vendas apenas desta unidade (ou todas se for Admin)
        if st.session_state["unidade_atual"] != "Administrador Geral":
            df_v = df_v[df_v['unidade'] == st.session_state['unidade_atual']]
        
        bruto = df_v['valor_bruto'].sum()
        liquido = df_v['valor_liquido'].sum()
        cashback = bruto * 0.02
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
        m2.metric("Líquido Cartão", f"R$ {liquido:,.2f}")
        m3.metric("Cashback Acumulado (2%)", f"R$ {cashback:,.2f}")

    # --- ALERTAS OPERACIONAIS ---
    st.divider()
    st.subheader("🚨 Alertas de Operação")
    if not df_estoque_local.empty:
        col_estoque, col_validade = st.columns(2)

        with col_estoque:
            st.markdown("#### ⚠️ Estoque Crítico")
            df_estoque_local['quantidade'] = pd.to_numeric(df_estoque_local['quantidade'], errors='coerce').fillna(0)
            df_estoque_local['minimo_alerta'] = pd.to_numeric(df_estoque_local['minimo_alerta'], errors='coerce').fillna(5)
            
            # Filtro por unidade logada
            baixo = df_estoque_local[
                (df_estoque_local['unidade'] == st.session_state['unidade_atual']) & 
                (df_estoque_local['quantidade'] <= df_estoque_local['minimo_alerta'])
            ] if st.session_state["unidade_atual"] != "Administrador Geral" else df_estoque_local[df_estoque_local['quantidade'] <= df_estoque_local['minimo_alerta']]

            if not baixo.empty:
                for _, r in baixo.iterrows():
                    st.error(f"**{r['nome']}**: Restam apenas {int(r['quantidade'])} un.")
            else:
                st.success("Estoque em dia.")

        with col_validade:
            st.markdown("#### 📅 Próximos do Vencimento")
            df_estoque_local['validade_dt'] = pd.to_datetime(df_estoque_local['validade'], dayfirst=True, errors='coerce')
            hoje = datetime.now()
            
            vencendo = df_estoque_local[
                (df_estoque_local['unidade'] == st.session_state['unidade_atual']) &
                (df_estoque_local['validade_dt'].notnull()) & 
                (df_estoque_local['validade_dt'] <= hoje + timedelta(days=7))
            ] if st.session_state["unidade_atual"] != "Administrador Geral" else df_estoque_local[(df_estoque_local['validade_dt'].notnull()) & (df_estoque_local['validade_dt'] <= hoje + timedelta(days=7))]

            if not vencendo.empty:
                for _, r in vencendo.iterrows():
                    st.warning(f"**{r['nome']}** vence em: {r['validade']}")
            else:
                st.success("Validades verificadas.")

# ==================== ABA: INVENTÁRIO (MULTI-PDV) ====================
elif menu == "📦 Inventário":
    st.header("📦 Gestão de Estoque Local")
    
    df_geral = carregar_dinamico("produtos")
    df_estoque = carregar_dinamico("estoque_pdv")

    # Seleção de
