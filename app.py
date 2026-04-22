import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES E CONEXÃO ====================
st.set_page_config(page_title="Flash Stop - Gestão Total", layout="wide", page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)

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

# ==================== 2. CONTROLE DE ACESSO ====================
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
            if st.form_submit_button("Acessar", use_container_width=True):
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
                st.error("Credenciais inválidas.")
    st.stop()

# ==================== 3. NAVEGAÇÃO ====================
with st.sidebar:
    render_logo("30px")
    if st.session_state.perfil == "cliente":
        st.success(f"📍 Local: {st.session_state.pdv_atual}")
        menu = "🛍️ Self-Checkout"
    else:
        menu = st.radio("Menu", ["📊 Dashboard", "🛍️ Self-Checkout", "📈 Custos Fixos", "💰 Entrada Mercadoria", "📦 Inventário", "📂 Contabilidade", "📟 Configurações"])
    
    st.divider()
    if st.button("🚪 Sair"):
        st.session_state.auth = False
        st.rerun()

# ==================== 4. DASHBOARD ====================
if menu == "📊 Dashboard":
    st.header("📊 Performance Flash Stop")
    df_v, df_d, df_p = carregar("vendas"), carregar("despesas"), carregar("produtos")
    
    bruto = df_v['valor_bruto'].sum()
    liq = df_v['valor_liquido'].sum()
    gastos = df_d['valor'].sum()
    cashback = bruto * 0.02
    resultado = liq - gastos - cashback

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido", f"R$ {liq:,.2f}")
    c3.metric("Custos Fixos", f"R$ {gastos:,.2f}")
    c4.metric("Cashback (2%)", f"R$ {cashback:,.2f}")
    c5.metric("Lucro Real", f"R$ {resultado:,.2f}")

# ==================== 5. SELF-CHECKOUT ====================
elif menu == "🛍️ Self-Checkout":
    st.markdown(f"<h2 style='text-align: center;'>🛒 Checkout - {st.session_state.pdv_atual if st.session_state.pdv_atual else 'Admin'}</h2>", unsafe_allow_html=True)
    df_p, df_m, df_pts = carregar("produtos"), carregar("maquinas"), carregar("pontos")
    v_pdv = st.session_state.pdv_atual if st.session_state.perfil == "cliente" else st.selectbox("PDV:", df_pts['nome'].tolist())

    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    with col_c2:
        with st.container(border=True):
            v_prod = st.selectbox("Produto:", [""] + df_p['nome'].tolist())
            v_qtd = st.number_input("Quantidade:", min_value=1, step=1)
            if v_prod != "":
                p_u = float(df_p[df_p['nome'] == v_prod].iloc[0]['preco'])
                total = p_u * v_qtd
                st.markdown(f"<h1 style='text-align:center; color:#7CFC00;'>R$ {total:,.2f}</h1>", unsafe_allow_html=True)
                v_forma = st.radio("Pagamento:", ["Pix", "Débito", "Crédito"], horizontal=True)
                if st.button("✅ FINALIZAR", use_container_width=True, type="primary"):
                    maqs = df_m[df_m['pdv_vinculado'] == v_pdv]['nome_maquina'].tolist()
                    m_n = maqs[0] if maqs else "Dinheiro"
                    idx = df_p[df_p['nome'] == v_prod].index[0]
                    taxa = 0.0
                    if m_n != "Dinheiro":
                        md = df_m[df_m['nome_maquina'] == m_n].iloc[0]
                        taxa = md['taxa_pix'] if v_forma == "Pix" else md['taxa_debito'] if v_forma == "Débito" else md['taxa_credito']
                    v_liq = total * (1 - (taxa/100))
                    df_p.at[idx, 'estoque'] -= v_qtd
                    venda = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": v_pdv, "maquina": m_n, "produto": v_prod, "valor_bruto": total, "valor_liquido": v_liq, "forma": v_forma}])
                    conn.update(worksheet="vendas", data=pd.concat([carregar("vendas"), venda], ignore_index=True))
                    conn.update(worksheet="produtos", data=df_p)
                    st.balloons(); st.success("Sucesso!"); time.sleep(1); st.rerun()

# ==================== 6. CUSTOS FIXOS ====================
elif menu == "📈 Custos Fixos":
    st.header("📈 Despesas")
    df_d, df_pts = carregar("despesas"), carregar("pontos")
    with st.form("f_d"):
        p = st.selectbox("PDV", df_pts['nome'].tolist())
        d = st.text_input("Descrição")
        v = st.number_input("Valor", min_value=0.0)
        if st.form_submit_button("Salvar"):
            nova = pd.DataFrame([{"pdv": p, "descricao": d, "valor": v, "vencimento": datetime.now().strftime("%d/%m/%Y")}])
            conn.update(worksheet="despesas", data=pd.concat([df_d, nova], ignore_index=True))
            st.success("Sal
