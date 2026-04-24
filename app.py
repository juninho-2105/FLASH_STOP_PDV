import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop - PDV Autônomo", layout="wide", initial_sidebar_state="collapsed")

# 1. HEARTBEAT (Manter sessão ativa a cada 5 minutos)
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

# ==================== LÓGICA DE ACESSO (URL + SESSION STATE) ====================
TOKEN_MESTRE = "flash2026"
query_params = st.query_params

if "logado" not in st.session_state:
    st.session_state["logado"] = False

# Verificação automática via URL (Ex: ?pdv=Flash%20Stop%2001&token=flash2026)
if "pdv" in query_params and "token" in query_params:
    if query_params["token"] == TOKEN_MESTRE:
        st.session_state["logado"] = True
        st.session_state["unidade_atual"] = query_params["pdv"]

# ==================== INTERFACE DE LOGIN (Se não estiver logado) ====================
if not st.session_state["logado"]:
    st.title("⚡ flash stop")
    with st.form("login_manual"):
        user = st.text_input("Usuário")
        pw = st.text_input("Senha", type="password")
        unidade_login = st.selectbox("Selecione a Unidade", ["Flash Stop 01", "Flash Stop 02"])
        if st.form_submit_button("Entrar"):
            if pw == TOKEN_MESTRE: # Simplificado para o exemplo
                st.session_state["logado"] = True
                st.session_state["unidade_atual"] = unidade_login
                st.rerun()
    st.stop()

# ==================== BARRA LATERAL (MENU) ====================
with st.sidebar:
    st.write(f"📍 **Unidade:** {st.session_state['unidade_atual']}")
    menu = st.radio("Navegação", ["🛒 Checkout", "📦 Inventário", "📊 Dashboard", "💰 Despesas"])
    if st.button("Sair"):
        st.session_state["logado"] = False
        st.rerun()

# ==================== ABA: DASHBOARD (MÉTRICAS + ALERTAS) ====================
if menu == "📊 Dashboard":
    st.header(f"📊 Painel de Controle - {st.session_state['unidade_atual']}")

    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_estoque_local = carregar_dinamico("estoque_pdv")

    # --- PARTE A: FINANCEIRO ---
    st.subheader("💰 Resumo Financeiro (Geral)")
    if not df_v.empty:
        df_v['valor_bruto'] = pd.to_numeric(df_v['valor_bruto'], errors='coerce').fillna(0)
        df_v['valor_liquido'] = pd.to_numeric(df_v['valor_liquido'], errors='coerce').fillna(0)
        
        bruto_total = df_v['valor_bruto'].sum()
        liquido_cartao = df_v['valor_liquido'].sum()
        cashback_total = bruto_total * 0.02
        
        gastos = 0.0
        if not df_d.empty and 'valor' in df_d.columns:
            df_d['valor'] = pd.to_numeric(df_d['valor'], errors='coerce').fillna(0)
            gastos = df_d['valor'].sum()

        lucro_final = liquido_cartao - gastos - cashback_total

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Fat. Bruto", f"R$ {bruto_total:.2f}")
        m2.metric("Despesas", f"R$ {gastos:.2f}")
        m3.metric("Cashback (2%)", f"R$ {cashback_total:.2f}")
        m4.metric("Líq. Cartão", f"R$ {liquido_cartao:.2f}")
        m5.metric("Lucro Real", f"R$ {lucro_final:.2f}")

    # --- PARTE B: ALERTAS OPERACIONAIS (POR UNIDADE) ---
    st.divider()
    st.subheader("🚨 Alertas de Operação")
    
    if not df_estoque_local.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### ⚠️ Estoque Crítico")
            df_estoque_local['quantidade'] = pd.to_numeric(df_estoque_local['quantidade'], errors='coerce').fillna(0)
            df_estoque_local['minimo_alerta'] = pd.to_numeric(df_estoque_local['minimo_alerta'], errors='coerce').fillna(5)
            baixo = df_estoque_local[df_estoque_local['quantidade'] <= df_estoque_local['minimo_alerta']]
            
            if not baixo.empty:
                for _, r in baixo.iterrows():
                    st.error(f"📍 **{r['unidade']}** | **{r['nome']}**: {int(r['quantidade'])} un")
            else:
                st.success("✅ Estoque em dia.")

        with c2:
            st.markdown("#### 📅 Validades")
            df_estoque_local['validade_dt'] = pd.to_datetime(df_estoque_local['validade'], dayfirst=True, errors='coerce')
            hoje = datetime.now()
            vencendo = df_estoque_local[(df_estoque_local['validade_dt'].notnull()) & (df_estoque_local['validade_dt'] <= hoje + timedelta(days=7))]
            
            if not vencendo.empty:
                for _, r in vencendo.iterrows():
                    st.warning(f"📍 **{r['unidade']}** | **{r['nome']}** ({r['validade']})")
            else:
                st.success("✅ Tudo na validade.")

# ==================== ABA: INVENTÁRIO (MULTI-PDV) ====================
elif menu == "📦 Inventário":
    st.header("📦 Gestão de Estoque Multi-PDV")
    
    df_geral = carregar_dinamico("produtos")
    df_estoque = carregar_dinamico("estoque_pdv")
    df_vendas = carregar_dinamico("vendas")

    # Busca dinâmica de PDVs
    u_vendas = df_vendas['unidade'].unique().tolist() if not df_vendas.empty and 'unidade' in df_vendas.columns else []
    u_estoque = df_estoque['unidade'].unique().tolist() if not df_estoque.empty and 'unidade' in df_estoque.columns else []
    unidades_cadastradas = sorted(list(set(u_vendas + u_estoque + [st.session_state["unidade_atual"]])))

    aba_geral, aba_unidade = st.tabs(["🌎 Catálogo Geral", "📍 Estoque por PDV"])

    with aba_geral:
        if not df_geral.empty:
            st.dataframe(df_geral[["nome", "preco_venda", "categoria"]], use_container_width=True, hide_index=True)

    with aba_unidade:
        unidade_sel = st.selectbox("Gerenciar Unidade:", unidades_cadastradas)
        df_local = df_estoque[df_estoque['unidade'] == unidade_sel] if not df_estoque.empty else pd.DataFrame()
        
        # Sincronização automática
        if not df_geral.empty:
            faltantes = [p for p in df_geral['nome'].tolist() if p not in df_local['nome'].tolist()]
            if faltantes and st.button(f"📥 Importar {len(faltantes)} Itens"):
                novos = pd.DataFrame([{"unidade": unidade_sel, "nome": p, "quantidade": 0, "validade": "A definir", "minimo_alerta": 5} for p in faltantes])
                df_estoque = pd.concat([df_estoque, novos], ignore_index=True)
                conn.update(worksheet="estoque_pdv", data=df_estoque)
                st.rerun()

        if not df_local.empty:
            st.dataframe(df_local[["nome", "quantidade", "validade", "minimo_alerta"]], use_container_width=True, hide_index=True)
            
            with st.form("edit_estoque"):
                p_edit = st.selectbox("Editar Produto", df_local['nome'].tolist())
                c1, c2, c3 = st.columns(3)
                n_qtd = c1.number_input("Qtd Existente", value=0)
                n_val = c2.text_input("Validade (DD/MM/AAAA)")
                n_min = c3.number_input("Mínimo Alerta", value=5)
                if st.form_submit_button("Salvar Alterações"):
                    idx = df_estoque[(df_estoque['unidade'] == unidade_sel) & (df_estoque['nome'] == p_edit)].index[0]
                    df_estoque.at[idx, 'quantidade'] = n_qtd
                    df_estoque.at[idx, 'validade'] = n_val
                    df_estoque.at[idx, 'minimo_alerta'] = n_min
                    conn.update(worksheet="estoque_pdv", data=df_estoque)
                    st.success("Atualizado!")
                    st.rerun()

# ==================== ABA: CHECKOUT (SIMPLIFICADA) ====================
elif menu == "🛒 Checkout":
    st.subheader(f"🛒 Totem de Vendas - {st.session_state['unidade_atual']}")
    st.write("Interface de vendas para o cliente final...")
    # Aqui entraria o seu código de leitura de código de barras e finalização
