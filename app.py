import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# Configurações Iniciais
st.set_page_config(page_title="Flash Stop Pro v6.1", layout="wide", page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)

# Mapa de Colunas
COLS = {
    "produtos": ["nome", "estoque", "validade", "preco", "estoque_minimo"],
    "vendas": ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"],
    "despesas": ["pdv", "descricao", "valor", "vencimento"],
    "maquinas": ["nome_maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"],
    "pontos": ["nome"]
}

# Funcao de Carregamento
@st.cache_data(ttl=2)
def carregar(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=COLS.get(aba, []))
        return df.dropna(how='all')
    except:
        return pd.DataFrame(columns=COLS.get(aba, []))

# Estilo da Logo
def render_logo(size="42px"):
    st.markdown(f'<h1 style="text-align:center;font-family:sans-serif;font-size:{size};">FLASH <span style="color:#7CFC00;">STOP</span></h1>', unsafe_allow_html=True)

# Login
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    render_logo("50px")
    with st.form("login"):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if u == "admin" and s == "flash123":
                st.session_state.auth = True
                st.rerun()
    st.stop()

# Menu lateral
menu = st.sidebar.radio("Navegação", ["Dashboard", "Vendas (PDV)", "Estoque", "Despesas", "Configurações"])

# 1. Dashboard
if menu == "Dashboard":
    st.header("📊 Dashboard")
    df_v = carregar("vendas")
    df_d = carregar("despesas")
    
    bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
    liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
    gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
    cashback = bruto * 0.02
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido", f"R$ {liq:,.2f}")
    c3.metric("Cashback", f"R$ {cashback:,.2f}")
    c4.metric("Resultado", f"R$ {liq - gastos - cashback:,.2f}")
    
    st.divider()
    st.subheader("📤 Exportar para Contador")
    csv = df_v.to_csv(index=False).encode('utf-8-sig')
    st.download_button("Baixar Relatório CSV", csv, "vendas_flashstop.csv", "text/csv")

# 2. Vendas
elif menu == "Vendas (PDV)":
    st.header("🛍️ Frente de Caixa")
    df_p = carregar("produtos")
    df_m = carregar("maquinas")
    df_pts = carregar("pontos")
    
    with st.form("venda"):
        pdv = st.selectbox("PDV", df_pts['nome'].tolist() if not df_pts.empty else ["-"])
        prod = st.selectbox("Produto", df_p['nome'].tolist() if not df_p.empty else ["-"])
        forma = st.selectbox("Pagamento", ["Pix", "Débito", "Crédito", "Dinheiro"])
        maquina = st.selectbox("Máquina", df_m[df_m['pdv_vinculado'] == pdv]['nome_maquina'].tolist() if not df_m.empty else ["Dinheiro"])
        qtd = st.number_input("Qtd", min_value=1)
        
        if st.form_submit_button("Finalizar"):
            p_idx = df_p[df_p['nome'] == prod].index[0]
            val_bruto = float(df_p.at[p_idx, 'preco']) * qtd
            
            taxa = 0.0
            if maquina != "Dinheiro":
                m_info = df_m[df_m['nome_maquina'] == maquina].iloc[0]
                if forma == "Pix": taxa = float(m_info['taxa_pix'])
                elif forma == "Débito": taxa = float(m_info['taxa_debito'])
                elif forma == "Crédito": taxa = float(m_info['taxa_credito'])
            
            val_liq = val_bruto * (1 - (taxa/100))
            df_p.at[p_idx, 'estoque'] = int(df_p.at[p_idx, 'estoque']) - qtd
            
            nova_v = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": pdv, "maquina": maquina, "produto": prod, "valor_bruto": val_bruto, "valor_liquido": val_liq, "forma": forma}])
            
            conn.update(worksheet="vendas", data=pd.concat([carregar("vendas"), nova_v], ignore_index=True))
            conn.update(worksheet="produtos", data=df_p)
            st.success("Venda salva!")
            time.sleep(1)
            st.rerun()

# 3. Estoque
elif menu == "Estoque":
    st.header("📦 Estoque")
    df_p = carregar("produtos")
    st.dataframe(df_p, use_container_width=True)
    with st.form("add_p"):
        n = st.text_input("Nome")
        q = st.number_input("Qtd", min_value=0)
        p = st.number_input("Preço", min_value=0.0)
        if st.form_submit_button("Adicionar/Atualizar"):
            if n in df_p['nome'].tolist():
                df_p.loc[df_p['nome'] == n, ['estoque', 'preco']] = [q, p]
            else:
                df_p = pd.concat([df_p, pd.DataFrame([{"nome": n, "estoque": q, "preco": p, "validade": "-", "estoque_minimo": 5}])])
            conn.update(worksheet="produtos", data=df_p)
            st.rerun()

# 4. Despesas
elif menu == "Despesas":
    st.header("📉 Despesas")
    df_d = carregar("despesas")
    df_pts = carregar("pontos")
    with st.form("add_d"):
        p = st.selectbox("PDV", df_pts['nome'].tolist())
        d = st.text_input("Desc")
        v = st.number_input("Valor")
        if st.form_submit_button("Salvar"):
            nova = pd.DataFrame([{"pdv": p, "descricao": d, "valor": v, "vencimento": datetime.now().strftime("%d/%m/%Y")}])
            conn.update(worksheet="despesas", data=pd.concat([df_d, nova]))
            st.rerun()
    st.dataframe(df_d)

# 5. Configurações
elif menu == "Configurações":
    st.header("📟 Configurações")
    df_pts = carregar("pontos")
    df_m = carregar("maquinas")
    
    c1, c2 = st.columns(2)
    with c1:
        new_p = st.text_input("Novo PDV")
        if st.button("Salvar PDV"):
            conn.update(worksheet="pontos", data=pd.concat([df_pts, pd.DataFrame([{"nome": new_p}])]))
            st.rerun()
    with c2:
        with st.form("m"):
            mn = st.text_input("Máquina")
            mv = st.selectbox("Vincular", df_pts['nome'].tolist())
            tp = st.number_input("Taxa Pix")
            td = st.number_input("Taxa Débito")
            tc = st.number_input("Taxa Crédito")
            if st.form_submit_button("Salvar Máquina"):
                conn.update(worksheet="maquinas", data=pd.concat([df_m, pd.DataFrame([{"nome_maquina": mn, "pdv_vinculado": mv, "taxa_debito": td, "taxa_credito": tc, "taxa_pix": tp}])]))
                st.rerun()
              
