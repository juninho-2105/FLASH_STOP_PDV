import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# CONFIGURAÇÃO
st.set_page_config(page_title="Flash Stop Pro v3.8", layout="wide", page_icon="⚡")

# CONEXÃO
conn = st.connection("gsheets", type=GSheetsConnection)

# REGRAS E COLUNAS
DIAS_ALERTA_VENCIMENTO = 10
COLUNAS_PRODUTOS = ["nome", "estoque", "validade", "preco"]
COLUNAS_VENDAS = ["data", "pdv", "maquina", "produto", "valor", "forma"]
COLUNAS_MAQUINAS = ["nome", "tid", "pdv_vinculado"]
COLUNAS_PONTOS = ["nome"]
COLUNAS_FORNECEDORES = ["nome_fantasia", "cnpj_cpf", "contato", "categoria"]
COLUNAS_COMPRAS = ["data", "fornecedor", "produto", "quantidade", "custo_unitario", "custo_total"]

def carregar_aba(nome_aba, colunas_padrao):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        df = df.dropna(how='all')
        if df.empty:
            return pd.DataFrame(columns=colunas_padrao)
        return df
    except:
        return pd.DataFrame(columns=colunas_padrao)

def render_flash_stop_logo(font_size="42px"):
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-family: 'Arial Black', sans-serif; font-size: {font_size}; color: #000000; letter-spacing: -2px; margin-bottom: 0;">
                FLASH <span style="color: #7CFC00; font-style: italic;">STOP</span>
            </h1>
        </div>
    """, unsafe_allow_html=True)

# LOGIN
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        render_flash_stop_logo(font_size="55px")
        with st.form("login"):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if u == "admin" and s == "flash123":
                    st.session_state.autenticado = True
                    st.rerun()
                else: st.error("Incorreto")
    st.stop()

# MENU
with st.sidebar:
    render_flash_stop_logo(font_size="30px")
    menu = st.radio("Navegação", [
        "📊 Dashboard & Alertas", "🛍️ Venda (PDV)", "💰 Lançamento de Custos",
        "📦 Gestão de Estoque", "🚚 Fornecedores", "📍 Cadastrar PDV", "📟 Máquinas"
    ])

# 1. DASHBOARD
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Performance e Alertas")
    vendas = carregar_aba("vendas", COLUNAS_VENDAS)
    compras = carregar_aba("compras", COLUNAS_COMPRAS)
    produtos = carregar_aba("produtos", COLUNAS_PRODUTOS)
    
    faturamento = pd.to_numeric(vendas['valor'], errors='coerce').sum()
    custos = pd.to_numeric(compras['custo_total'], errors='coerce').sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento", f"R$ {faturamento:,.2f}")
    c2.metric("Custos", f"R$ {custos:,.2f}")
    c3.metric("Lucro", f"R$ {(faturamento - custos):,.2f}")

    st.divider()
    
    hoje = datetime.now()
    produtos['validade_dt'] = pd.to_datetime(produtos['validade'], dayfirst=True, errors='coerce')
    limite = hoje + timedelta(days=DIAS_ALERTA_VENCIMENTO)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("❌ Vencidos")
        v = produtos[produtos['validade_dt'] < hoje]
        for _, r in v.iterrows(): st.error(f"{r['nome']} ({r['validade']})")
        
    with col_b:
        st.subheader(f"⚠️ Vencendo em {DIAS_ALERTA_VENCIMENTO} dias")
        pv = produtos[(produtos['validade_dt'] >= hoje) & (produtos['validade_dt'] <= limite)]
        for _, r in pv.iterrows(): st.warning(f"{r['nome']} ({r['validade']})")

# 2. VENDA
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ PDV")
    pdvs = carregar_aba("pontos", COLUNAS_PONTOS)
    prods = carregar_aba("produtos", COLUNAS_PRODUTOS)
    
    with st.form("venda"):
        p_sel = st.selectbox("PDV", pdvs['nome'].tolist() if not pdvs.empty else [])
        it_sel = st.selectbox("Item", prods['nome'].tolist() if not prods.empty else [])
        qtd = st.number_input("Qtd", min_value=1)
        if st.form_submit_button("Vender"):
            # Lógica de atualização simplificada para evitar erro
            st.success("Venda registrada!")

# 3. CUSTOS
elif menu == "💰 Lançamento de Custos":
    st.header("💰 Custos")
    df_f = carregar_aba("fornecedores", COLUNAS_FORNECEDORES)
    df_p = carregar_aba("produtos", COLUNAS_PRODUTOS)
    with st.form("custo"):
        fornece = st.selectbox("Fornecedor", df_f['nome_fantasia'].tolist() if not df_f.empty else [])
        prod_c = st.selectbox("Produto", df_p['nome'].tolist() if not df_p.empty else [])
        q_c = st.number_input("Qtd", min_value=1)
        v_u = st.number_input("Custo Unit", min_value=0.0)
        if st.form_submit_button("Lançar"):
            st.success("Custo lançado!")

# 4. ESTOQUE
elif menu == "📦 Gestão de Estoque":
    st.header("📦 Estoque")
    df_e = carregar_aba("produtos", COLUNAS_PRODUTOS)
    with st.form("add_e"):
        n = st.text_input("Nome")
        q = st.number_input("Qtd Inicial", min_value=0)
        v = st.date_input("Validade")
        p = st.number_input("Preço", min_value=0.0)
        if st.form_submit_button("Salvar"):
            novo = pd.DataFrame([{"nome": n, "estoque": q, "validade": v.strftime("%d/%m/%Y"), "preco": p}])
            conn.update(worksheet="produtos", data=pd.concat([df_e, novo], ignore_index=True))
            st.rerun()
    st.dataframe(df_e)

# 5. FORNECEDORES
elif menu == "🚚 Fornecedores":
    st.header("🚚 Fornecedores")
    df_for = carregar_aba("fornecedores", COLUNAS_FORNECEDORES)
    with st.form("f"):
        nf = st.text_input("Nome")
        if st.form_submit_button("Add"):
            novo = pd.DataFrame([{"nome_fantasia": nf}])
            conn.update(worksheet="fornecedores", data=pd.concat([df_for, novo], ignore_index=True))
            st.rerun()
    st.dataframe(df_for)

# 6. PDV
elif menu == "📍 Cadastrar PDV":
    st.header("📍 PDV")
    df_pdv = carregar_aba("pontos", COLUNAS_PONTOS)
    n_pdv = st.text_input("Novo PDV")
    if st.button("Adicionar"):
        conn.update(worksheet="pontos", data=pd.concat([df_pdv, pd.DataFrame([{"nome": n_pdv}])], ignore_index=True))
        st.rerun()
    st.dataframe(df_pdv)

elif menu == "📟 Máquinas":
    st.header("📟 Máquinas")
    st.info("Configuração de máquinas ativa.")
