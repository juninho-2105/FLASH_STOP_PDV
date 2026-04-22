import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES E CONEXÃO ====================
st.set_page_config(page_title="Flash Stop - PDV Inteligente", layout="wide", page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)

# Estrutura padrão de colunas
COLS = {
    "produtos": ["nome", "estoque", "validade", "preco", "estoque_minimo"],
    "vendas": ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"],
    "despesas": ["pdv", "descricao", "valor", "vencimento"],
    "maquinas": ["nome_maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"],
    "pontos": ["nome", "senha"],
    "fornecedores": ["nome_fantasia", "cnpj_cpf"]
}

@st.cache_data(ttl=2)
def carregar(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLS.get(aba, []))
        df = df.dropna(how='all')
        num_cols = ["estoque", "preco", "valor", "valor_bruto", "valor_liquido", "taxa_debito", "taxa_credito", "taxa_pix", "estoque_minimo"]
        for col in num_cols:
            if col in df.columns: 
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame(columns=COLS.get(aba, []))

def render_logo(size="42px"):
    st.markdown(f'<h1 style="text-align:center;font-family:sans-serif;font-size:{size};color:#000;margin-bottom:0;">FLASH <span style="color:#7CFC00;font-style:italic;">STOP</span></h1>', unsafe_allow_html=True)

# ==================== 2. CONTROLE DE ACESSO POR PDV ====================
if "auth" not in st.session_state: 
    st.session_state.auth = False
    st.session_state.perfil = None
    st.session_state.pdv_atual = None

if not st.session_state.auth:
    render_logo("55px")
    df_pts = carregar("pontos")
    col_l1, col_l2, col_l3 = st.columns([1,1.5,1])
    with col_l2:
        with st.form("login_form"):
            u = st.text_input("Usuário ou Nome do PDV")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar Sistema", use_container_width=True):
                if u == "admin" and s == "flash123":
                    st.session_state.auth = True
                    st.session_state.perfil = "admin"
                    st.rerun()
                elif not df_pts.empty and u in df_pts['nome'].values:
                    senha_correta = str(df_pts[df_pts['nome'] == u].iloc[0]['senha'])
                    if s == senha_correta:
                        st.session_state.auth = True
                        st.session_state.perfil = "cliente"
                        st.session_state.pdv_atual = u
                        st.rerun()
                st.error("Dados inválidos. Verifique o nome do PDV e a senha.")
    st.stop()

# ==================== 3. NAVEGAÇÃO ====================
with st.sidebar:
    render_logo("30px")
    if st.session_state.perfil == "cliente":
        st.success(f"📍 Local: {st.session_state.pdv_atual}")
        menu = "🛍️ Self-Checkout"
    else:
        menu = st.radio("Administração", ["📊 Dashboard", "🛍️ Self-Checkout", "📈 Custos Fixos", "💰 Entrada Mercadoria", "📦 Inventário", "📂 Contabilidade", "📟 Configurações"])
    
    st.divider()
    if st.button("🚪 Sair / Deslogar"):
        st.session_state.auth = False
        st.rerun()

# ==================== 4. DASHBOARD (ADMIN) ====================
if menu == "📊 Dashboard":
    st.header("📊 Performance Flash Stop")
    df_v, df_d, df_p = carregar("vendas"), carregar("despesas"), carregar("produtos")
    
    bruto = df_v['valor_bruto'].sum()
    liq = df_v['valor_liquido'].sum()
    gastos = df_d['valor'].sum()
    cashback = bruto * 0.02
    resultado = liq - gastos - cashback

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido (Pós-Taxas)", f"R$ {liq:,.2f}")
    c3.metric("Custos Fixos", f"R$ {gastos:,.2f}")
    c4.metric("Cashback (2%)", f"R$ {cashback:,.2f}", delta=f"-{cashback:,.2f}", delta_color="inverse")
    c5.metric("Lucro Final", f"R$ {resultado:,.2f}")

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🚨 Estoque em Alerta")
        baixo = df_p[df_p['estoque'] <= df_p['estoque_minimo']]
        st.table(baixo[['nome', 'estoque']]) if not baixo.empty else st.success("Estoque OK")
    with col_b:
        st.subheader("📅 Validade (15 dias)")
        vencendo = []
        for _, r in df_p.iterrows():
            try:
                dv = datetime.strptime(str(r['validade']), "%d/%m/%Y")
                if dv <= datetime.now() + timedelta(days=15): vencendo.append({"Item": r['nome'], "Vencimento": r['validade']})
            except: continue
        st.table(vencendo) if vencendo else st.success("Validades OK")

# ==================== 5. SELF-CHECKOUT (TRAVADO POR PDV) ====================
elif menu == "🛍️ Self-Checkout":
    st.markdown(f"<h2 style='text-align: center;'>🛒 Autoatendimento - {st.session_state.pdv_atual if st.session_state.pdv_atual else 'Admin'}</h2>", unsafe_allow_html=True)
    df_p, df_m, df_pts = carregar("produtos"), carregar("maquinas"), carregar("pontos")
    
    # Define o PDV da venda (automatico se for login de cliente)
    v_pdv = st.session_state.pdv_atual if st.session_state.perfil == "cliente" else st.selectbox("Simular PDV:", df_pts['nome'].tolist())

    c_s1, c_s2, c_s3 = st.columns([1, 2, 1])
    with c_s2:
        with st.container(border=True):
            v_prod = st.selectbox("Bipe o código ou busque o produto:", [""] + df_p['nome'].tolist())
            v_qtd = st.number_input("Quantidade:", min_value=1, step=1, value=1)
            
            if v_prod != "":
                p_u = float(df_p[df_p['nome'] == v_prod].iloc[0]['preco'])
                total = p_u * v_qtd
                st.markdown(f"<h1 style='text-align:center; color:#7CFC00;'>R$ {total:,.2f}</h1>", unsafe_allow_html=True)
                v_forma = st.radio("Selecione o Pagamento:", ["Pix", "Débito", "Crédito"], horizontal=True)
                
                if st.button("✅ FINALIZAR COMPRA", use_container_width=True, type="primary"):
                    # Busca automática da máquina do PDV logado
                    maqs = df_m[df_m['pdv_vinculado'] == v_pdv]['nome_maquina'].tolist()
                    m_nome = maqs[0] if maqs else "Dinheiro"
                    
                    idx = df_p[df_p['nome'] == v_prod].index[0]
                    taxa = 0.0
                    if m_nome != "Dinheiro":
                        m_d = df_m[df_m['nome_maquina'] == m_nome].iloc[0]
                        taxa = m_d['taxa_pix'] if v_forma == "Pix" else m_d['taxa_
