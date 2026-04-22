import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== CONFIGURAÇÃO INICIAL ====================
st.set_page_config(page_title="Flash Stop Ultimate v6.2", layout="wide", page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)

# --- MAPA DE COLUNAS ---
COLS = {
    "produtos": ["nome", "estoque", "validade", "preco", "estoque_minimo"],
    "vendas": ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"],
    "despesas": ["pdv", "descricao", "valor", "vencimento"],
    "maquinas": ["nome_maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"],
    "pontos": ["nome"],
    "fornecedores": ["nome_fantasia", "cnpj_cpf"]
}

# ==================== FUNÇÕES MOTORAS ====================
@st.cache_data(ttl=2)
def carregar(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=COLS.get(aba, []))
        df = df.dropna(how='all')
        # Garante colunas numéricas
        num_cols = ["estoque", "preco", "valor", "valor_bruto", "valor_liquido", "taxa_debito", "taxa_credito", "taxa_pix", "estoque_minimo"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=COLS.get(aba, []))

def render_logo(size="42px"):
    st.markdown(f'<h1 style="text-align:center;font-family:sans-serif;font-size:{size};color:#000;">FLASH <span style="color:#7CFC00;font-style:italic;">STOP</span></h1>', unsafe_allow_html=True)

# ==================== ACESSO ====================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    render_logo("55px")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if u == "admin" and s == "flash123":
                st.session_state.auth = True
                st.rerun()
    st.stop()

# ==================== MENU LATERAL ====================
with st.sidebar:
    render_logo("30px")
    st.divider()
    menu = st.radio("Navegação", [
        "📊 Dashboard & Alertas",
        "📂 Relatórios Contábeis",
        "🛍️ Frente de Caixa (PDV)",
        "💰 Entrada de Mercadoria",
        "📦 Inventário de Estoque",
        "🚚 Fornecedores",
        "📟 Configurações"
    ])
    if st.button("🔄 Sincronizar Dados"):
        st.cache_data.clear()
        st.rerun()

# ==================== 1. DASHBOARD & ALERTAS ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Resumo Operacional")
    df_v = carregar("vendas")
    df_d = carregar("despesas")
    df_p = carregar("produtos")
    
    # KPIs
    bruto = df_v['valor_bruto'].sum()
    liq = df_v['valor_liquido'].sum()
    gastos = df_d['valor'].sum()
    cashback = bruto * 0.02
    resultado = liq - gastos - cashback

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Vendas Brutas", f"R$ {bruto:,.2f}")
    c2.metric("Líquido (Pós-Taxas)", f"R$ {liq:,.2f}")
    c3.metric("Cashback (2%)", f"R$ {cashback:,.2f}")
    c4.metric("Resultado Final", f"R$ {resultado:,.2f}", delta=float(resultado))

    st.divider()
    col_alt1, col_alt2 = st.columns(2)
    
    with col_alt1:
        st.subheader("🚨 Alertas de Estoque")
        baixo = df_p[df_p['estoque'] <= df_p['estoque_minimo']]
        if not baixo.empty:
            st.warning(f"{len(baixo)} itens em nível crítico")
            st.dataframe(baixo[['nome', 'estoque']], hide_index=True)
        else: st.success("Estoque OK")

    with col_alt2:
        st.subheader("📅 Alertas de Vencimento (30 dias)")
        vencendo = []
        hoje = datetime.now()
        for _, r in df_p.iterrows():
            try:
                dv = datetime.strptime(r['validade'], "%d/%m/%Y")
                if dv <= hoje + timedelta(days=30):
                    vencendo.append({"Produto": r['nome'], "Data": r['validade']})
            except: continue
        if vencendo: st.error(f"{len(vencendo)} produtos a vencer"); st.table(vencendo)
        else: st.success("Validades OK")

# ==================== 2. RELATÓRIOS CONTÁBEIS ====================
elif menu == "📂 Relatórios Contábeis":
    st.header("📂 Fechamento por Unidade")
    df_v = carregar("vendas")
    df_pts = carregar("pontos")
    
    pdv_sel = st.selectbox("Filtrar por Condomínio", ["Todos"] + df_pts['nome'].tolist())
    dados = df_v if pdv_sel == "Todos" else df_v[df_v['pdv'] == pdv_sel]
    
    st.dataframe(dados, use_container_width=True)
    
    csv = dados.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Exportar para Contador (CSV)", csv, f"contabilidade_{pdv_sel}.csv", "text/csv")

# ==================== 3. FRENTE DE CAIXA ====================
elif menu == "🛍️ Frente de Caixa (PDV)":
    st.header("🛍️ Nova Venda")
    df_p, df_m, df_pts = carregar("produtos"), carregar("maquinas"), carregar("pontos")
    
    with st.form("venda_f"):
        v_pdv = st.selectbox("PDV", df_pts['nome'].tolist())
        v_prod = st.selectbox("Produto", df_p['nome'].tolist())
        c1, c2 = st.columns(2)
        v_forma = c1.selectbox("Pagamento", ["Pix", "Débito", "Crédito", "Dinheiro"])
        v_maq = c2.selectbox("Máquina", df_m[df_m['pdv_vinculado'] == v_pdv]['nome_maquina'].tolist() if not df_m.empty else ["Dinheiro"])
        v_qtd = st.number_input("Qtd", min_value=1)
        
        if st.form_submit_button("CONCLUIR VENDA"):
            idx = df_p[df_p['nome'] == v_prod].index[0]
            v_bruto = float(df_p.at[idx, 'preco']) * v_qtd
            taxa = 0.0
            if v_maq != "Dinheiro":
                m_info = df_m[df_m['nome_maquina'] == v_maq].iloc[0]
                if v_forma == "Pix": taxa = m_info['taxa_pix']
                elif v_forma == "Débito": taxa = m_info['taxa_debito']
                elif v_forma == "Crédito": taxa = m_info['taxa_credito']
            
            v_liq = v_bruto * (1 - (taxa/100))
            df_p.at[idx, 'estoque'] -= v_qtd
            
            nova = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": v_pdv, "maquina": v_maq, "produto": v_prod, "valor_bruto": v_bruto, "valor_liquido": v_liq, "forma": v_forma}])
            conn.update(worksheet="vendas", data=pd.concat([carregar("vendas"), nova], ignore_index=True))
            conn.update(worksheet="produtos", data=df_p)
            st.success("Venda registada com sucesso!")
            time.sleep(1); st.rerun()

# ==================== 4. ENTRADA DE MERCADORIA ====================
elif menu == "💰 Entrada de Mercadoria":
    st.header("💰 Entrada e Custos")
    df_p = carregar("produtos")
    with st.form("entrada_f"):
        sel = st.selectbox("Produto", ["NOVO"] + df_p['nome'].tolist())
        nome = st.text_input("Nome") if sel == "NOVO" else sel
        c1, c2, c3 = st.columns(3)
        custo = c1.number_input("Custo Unitário")
        margem = c2.slider("Margem %", 10, 200, 50)
        qtd_add = c3.number_input("Qtd Entrada", min_value=1)
        venda = custo * (1 + margem/100)
        val = st.date_input("Validade")
        
        if st
