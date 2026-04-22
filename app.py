import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# ==================== CONFIGURAÇÃO ====================
st.set_page_config(page_title="Flash Stop Pro v5.6", layout="wide", page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)

# Colunas que o sistema EXIGE
COLS = {
    "produtos": ["nome", "estoque", "validade", "preco", "estoque_minimo"],
    "vendas": ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"],
    "despesas": ["pdv", "descricao", "valor", "vencimento"],
    "maquinas": ["nome_maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"],
    "pontos": ["nome"],
    "fornecedores": ["nome_fantasia", "cnpj_cpf"]
}

@st.cache_data(ttl=10)
def carregar_dados(aba, colunas_esperadas):
    try:
        df = conn.read(worksheet=aba, ttl=0).dropna(how='all')
        # PROTEÇÃO: Se faltar coluna no Sheets, ele cria aqui para não dar erro
        for col in colunas_esperadas:
            if col not in df.columns:
                df[col] = 0
        return df
    except:
        return pd.DataFrame(columns=colunas_esperadas)

def render_logo(size="42px"):
    st.markdown(f'<h1 style="text-align:center;font-family:Arial Black;font-size:{size};">FLASH <span style="color:#7CFC00;font-style:italic;">STOP</span></h1>', unsafe_allow_html=True)

# ==================== LOGIN ====================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    render_logo("55px")
    with st.form("l"):
        if st.form_submit_button("Entrar como Admin"): # Simplificado para teste
            st.session_state.auth = True
            st.rerun()
    st.stop()

# ==================== NAVEGAÇÃO ====================
menu = st.sidebar.radio("Menu", ["📊 Dashboard", "💰 Entradas", "🛍️ Vendas", "📟 Configurações"])

# --- 1. DASHBOARD ---
if menu == "📊 Dashboard":
    vendas = carregar_dados("vendas", COLS["vendas"])
    desp = carregar_dados("despesas", COLS["despesas"])
    
    bruto = pd.to_numeric(vendas['valor_bruto']).sum()
    liq = pd.to_numeric(vendas['valor_liquido']).sum()
    gastos = pd.to_numeric(desp['valor']).sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Cashback (2%)", f"R$ {bruto*0.02:,.2f}")
    c3.metric("Lucro Real (Líquido - Despesas)", f"R$ {liq - gastos:,.2f}")

# --- 2. ENTRADAS (CUSTOS + ESTOQUE) ---
elif menu == "💰 Entradas":
    st.header("💰 Entrada de Mercadoria")
    df_p = carregar_dados("produtos", COLS["produtos"])
    
    with st.form("e"):
        nome = st.text_input("Produto")
        qtd = st.number_input("Quantidade", min_value=1)
        custo = st.number_input("Custo Unitário", min_value=0.0)
        margem = st.slider("Margem %", 0, 200, 50)
        preco_venda = custo * (1 + margem/100)
        st.write(f"Preço Sugerido: R$ {preco_venda:.2f}")
        
        if st.form_submit_button("Gravar no Estoque"):
            if nome in df_p['nome'].tolist():
                df_p.loc[df_p['nome'] == nome, ['estoque', 'preco']] = [df_p.loc[df_p['nome'] == nome, 'estoque'].values[0] + qtd, preco_venda]
            else:
                novo = pd.DataFrame([{"nome": nome, "estoque": qtd, "preco": preco_venda, "validade": "-", "estoque_minimo": 5}])
                df_p = pd.concat([df_p, novo], ignore_index=True)
            
            conn.update(worksheet="produtos", data=df_p)
            st.success("Estoque Atualizado!")
            st.rerun()

# --- 3. VENDAS (PDV) ---
elif menu == "🛍️ Vendas":
    st.header("🛍️ Registro de Venda")
    df_p = carregar_dados("produtos", COLS["produtos"])
    df_m = carregar_dados("maquinas", COLS["maquinas"])
    df_pts = carregar_dados("pontos", COLS["pontos"])

    with st.form("v"):
        pdv = st.selectbox("PDV", df_pts['nome'].tolist() if not df_pts.empty else ["-"])
        prod = st.selectbox("Produto", df_p['nome'].tolist() if not df_p.empty else ["-"])
        forma = st.selectbox("Forma", ["Débito", "Crédito", "Pix", "Dinheiro"])
        maq = st.selectbox("Máquina", df_m[df_m['pdv_vinculado'] == pdv]['nome_maquina'].tolist() if not df_m.empty else ["Nenhum"])
        qtd_v = st.number_input("Qtd", min_value=1)

        if st.form_submit_button("Vender"):
            # Lógica de taxas
            taxa = 0
            if maq != "Nenhum":
                m_info = df_m[df_m['nome_maquina'] == maq].iloc[0]
                if forma == "Débito": taxa = m_info['taxa_debito']
                elif forma == "Crédito": taxa = m_info['taxa_credito']
                elif forma == "Pix": taxa = m_info['taxa_pix']
            
            p_idx = df_p[df_p['nome'] == prod].index[0]
            v_bruto = df_p.at[p_idx, 'preco'] * qtd_v
            v_liq = v_bruto * (1 - (float(taxa)/100))
            
            # Atualiza estoque e registra venda
            df_p.at[p_idx, 'estoque'] -= qtd_v
            vendas_velhas = carregar_dados("vendas", COLS["vendas"])
            nova_v = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "pdv": pdv, "maquina": maq, "produto": prod, "valor_bruto": v_bruto, "valor_liquido": v_liq, "forma": forma}])
            
            conn.update(worksheet="vendas", data=pd.concat([vendas_velhas, nova_v]))
            conn.update(worksheet="produtos", data=df_p)
            st.success("Venda realizada!")
            st.rerun()

# --- 4. CONFIGURAÇÕES ---
elif menu == "📟 Configurações":
    st.subheader("Cadastro de Máquinas e Taxas")
    df_m = carregar_dados("maquinas", COLS["maquinas"])
    df_pts = carregar_dados("pontos", COLS["pontos"])
    
    with st.form("m"):
        nome_m = st.text_input("Nome da Máquina")
        p_vinc = st.selectbox("PDV", df_pts['nome'].tolist() if not df_pts.empty else ["-"])
        t_deb = st.number_input("Taxa Débito %")
        t_cre = st.number_input("Taxa Crédito %")
        t_pix = st.number_input("Taxa Pix %")
        
        if st.form_submit_button("Salvar Máquina"):
            nova_m = pd.DataFrame([{"nome_maquina": nome_m, "pdv_vinculado": p_vinc, "taxa_debito": t_deb, "taxa_credito": t_cre, "taxa_pix": t_pix}])
            conn.update(worksheet="maquinas", data=pd.concat([df_m, nova_m], ignore_index=True))
            st.success("Máquina Salva!")
            st.rerun()
    st.dataframe(df_m)
