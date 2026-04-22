import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES INICIAIS ====================
st.set_page_config(page_title="Flash Stop Ultimate v6.4", layout="wide", page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)

# Mapa de colunas para garantir que o sistema não quebre se a planilha estiver vazia
COLS = {
    "produtos": ["nome", "estoque", "validade", "preco", "estoque_minimo"],
    "vendas": ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"],
    "despesas": ["pdv", "descricao", "valor", "vencimento"],
    "maquinas": ["nome_maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"],
    "pontos": ["nome"],
    "fornecedores": ["nome_fantasia", "cnpj_cpf"]
}

@st.cache_data(ttl=2)
def carregar(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLS.get(aba, []))
        df = df.dropna(how='all')
        # Padronização numérica para cálculos
        num_cols = ["estoque", "preco", "valor", "valor_bruto", "valor_liquido", "taxa_debito", "taxa_credito", "taxa_pix", "estoque_minimo"]
        for col in num_cols:
            if col in df.columns: 
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame(columns=COLS.get(aba, []))

def render_logo(size="42px"):
    st.markdown(f'<h1 style="text-align:center;font-family:sans-serif;font-size:{size};color:#000;">FLASH <span style="color:#7CFC00;font-style:italic;">STOP</span></h1>', unsafe_allow_html=True)

# ==================== 2. CONTROLE DE ACESSO ====================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    render_logo("55px")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar Painel"):
            if u == "admin" and s == "flash123":
                st.session_state.auth = True
                st.rerun()
    st.stop()

# ==================== 3. MENU LATERAL ====================
with st.sidebar:
    render_logo("30px")
    st.divider()
    menu = st.radio("Menu de Navegação", [
        "📊 Dashboard & Performance", 
        "🛍️ Frente de Caixa (PDV)", 
        "📈 Custos Fixos", 
        "💰 Entrada de Mercadoria", 
        "📦 Inventário Geral", 
        "🚚 Fornecedores", 
        "📟 Configurações"
    ])
    if st.button("🔄 Atualizar Banco de Dados"):
        st.cache_data.clear()
        st.rerun()

# ==================== 4. DASHBOARD & PERFORMANCE ====================
if menu == "📊 Dashboard & Performance":
    st.header("📊 Performance da Flash Stop")
    df_v, df_d, df_p = carregar("vendas"), carregar("despesas"), carregar("produtos")
    
    # Cálculos Financeiros
    bruto = df_v['valor_bruto'].sum()
    liq = df_v['valor_liquido'].sum()
    gastos = df_d['valor'].sum()
    cashback = bruto * 0.02
    resultado = liq - gastos - cashback

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido (Pós-Taxas)", f"R$ {liq:,.2f}")
    c3.metric("Custos Fixos", f"R$ {gastos:,.2f}")
    c4.metric("Resultado Final", f"R$ {resultado:,.2f}", delta=float(resultado))

    st.divider()
    
    # Gráfico de Evolução Mensal
    if not df_v.empty:
        st.subheader("📈 Crescimento Mensal")
        df_v['data_dt'] = pd.to_datetime(df_v['data'], dayfirst=True, errors='coerce')
        df_chart = df_v.dropna(subset=['data_dt']).set_index('data_dt').resample('M')['valor_bruto'].sum().reset_index()
        df_chart['Mês'] = df_chart['data_dt'].dt.strftime('%m/%Y')
        st.area_chart(df_chart.set_index('Mês')['valor_bruto'])

    # Alertas de Validade (15 dias) e Estoque
    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🚨 Reposição de Estoque")
        baixo = df_p[df_p['estoque'] <= df_p['estoque_minimo']]
        if not baixo.empty: st.warning(f"{len(baixo)} itens críticos"); st.table(baixo[['nome', 'estoque']])
        else: st.success("Estoque abastecido!")
    
    with col_b:
        st.subheader("📅 Validade (Próximos 15 dias)")
        hoje = datetime.now()
        vencendo = []
        for _, r in df_p.iterrows():
            try:
                dv = datetime.strptime(str(r['validade']), "%d/%m/%Y")
                if dv <= hoje + timedelta(days=15):
                    vencendo.append({"Produto": r['nome'], "Data": r['validade']})
            except: continue
        if vencendo: st.error(f"{len(vencendo)} itens vencendo"); st.table(vencendo)
        else: st.success("Validades OK!")

# ==================== 5. FRENTE DE CAIXA ====================
elif menu == "🛍️ Frente de Caixa (PDV)":
    st.header("🛍️ Registro de Venda")
    df_p, df_m, df_pts = carregar("produtos"), carregar("maquinas"), carregar("pontos")
    
    with st.form("venda_form"):
        v_pdv = st.selectbox("Selecione o Ponto", df_pts['nome'].tolist())
        v_prod = st.selectbox("
