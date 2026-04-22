import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v5.8", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- DEFINIÇÃO DE COLUNAS ---
COLUNAS_PRODUTOS = ["nome", "estoque", "validade", "preco", "estoque_minimo"]
COLUNAS_VENDAS = ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"]
COLUNAS_DESPESAS = ["pdv", "descricao", "valor", "vencimento"]
COLUNAS_MAQUINAS = ["nome_maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"]
COLUNAS_PONTOS = ["nome"]

# ==================== FUNÇÕES MOTORAS ====================
@st.cache_data(ttl=60)
def carregar_dados(nome_aba, colunas):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        df = df.dropna(how='all')
        if df.empty: return pd.DataFrame(columns=colunas)
        for col in colunas:
            if col not in df.columns: df[col] = 0
        num_cols = ["estoque", "preco", "valor", "valor_bruto", "valor_liquido", "taxa_debito", "taxa_credito", "taxa_pix", "estoque_minimo"]
        for col in num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=colunas)

def render_logo(font_size="42px"):
    st.markdown(f'<div style="text-align:center;"><h1 style="font-family:Arial Black; font-size:{font_size}; color:#000;">FLASH <span style="color:#7CFC00; font-style:italic;">STOP</span></h1></div>', unsafe_allow_html=True)

# ==================== CONTROLE DE ACESSO ====================
if "autenticado" not in st.session_state: st.session_state.autenticado = False
if not st.session_state.autenticado:
    render_logo("55px")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if u == "admin" and s == "flash123":
                st.session_state.autenticado = True
                st.rerun()
    st.stop()

# ==================== MENU LATERAL ====================
with st.sidebar:
    render_logo("30px")
    menu = st.radio("Navegação Principal", [
        "📊 Dashboard & Alertas",
        "📂 Relatórios Contábeis",
        "💰 Entrada de Mercadoria",
        "📈 Despesas Fixas",
        "🛍️ Frente de Caixa (PDV)",
        "📦 Inventário de Estoque",
        "📟 Configurações"
    ])
    if st.button("🔄 Sincronizar Agora"):
        st.cache_data.clear()
        st.rerun()

# ==================== 1. DASHBOARD & ALERTAS (REVISADO) ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Painel de Controle e Alertas Críticos")
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🚨 Alerta de Estoque Baixo")
        baixo = prods[prods['estoque'] <= prods['estoque_minimo']]
        if not baixo.empty:
            st.warning(f"Existem {len(baixo)} produtos precisando de reposição.")
            st.dataframe(baixo[['nome', 'estoque', 'estoque_minimo']], use_container_width=True, hide_index=True)
        else: st.success("Estoque em níveis normais.")

    with c2:
        st.subheader("📅 Alerta de Vencimento (30 dias)")
        hoje = datetime.now()
        vencendo = []
        for _, r in prods.iterrows():
            try:
                dt_venc = datetime.strptime(r['validade'], "%d/%m/%Y")
                if dt_venc <= hoje + timedelta(days=30):
                    vencendo.append({"Produto": r['nome'], "Vencimento": r['validade'], "Dias Restantes": (dt_venc - hoje).days})
            except: continue
        
        if vencendo:
            st.error(f"{len(vencendo)} produtos próximos ao vencimento!")
            st.dataframe(pd.DataFrame(vencendo), use_container_width=True, hide_index=True)
        else: st.success("Nenhum produto vencendo em breve.")

# ==================== 2. RELATÓRIOS CONTÁBEIS (NOVO) ====================
elif menu == "📂 Relatórios Contábeis":
    st.header("📂 Relatórios de Fechamento por PDV")
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    despesas = carregar_dados("despesas", COLUNAS_DESPESAS)
    
    pdv_sel = st.selectbox("Selecione o Ponto de Venda para Análise", ["Todos"] + list(vendas['pdv'].unique()))
    
    df_v = vendas if pdv_sel == "Todos" else vendas[vendas['pdv'] == pdv_sel]
    df_d = despesas if pdv_sel == "Todos" else despesas[despesas['pdv'] == pdv_sel]
    
    col_res1, col_res2, col_res3 = st.columns(3)
    bruto = df_v['valor_bruto'].sum()
    liquido = df_v['valor_liquido'].sum()
    gastos = df_d['valor'].sum()
    
    col_res1.metric("Vendas Brutas", f"R$ {bruto:,.2f}")
    col_res2.metric("Líquido (Pós-Taxas)", f"R$ {liquido:,.2f}")
    col_res3.metric("Resultado Final", f"R$ {liquido - gastos:,.2f}", delta=float(liquido - gastos))

    st.subheader("Detalhamento de Vendas")
    st.dataframe(df_v, use_container_width=True, hide_index=True)
    
    st.subheader("Detalhamento de Custos Fixos")
    st.dataframe(df_d, use_container_width=True, hide_index=True)

# ==================== 3. ENTRADA DE MERCADORIA ====================
elif menu == "💰 Entrada de Mercadoria":
    st.header("💰 Entrada e Precificação")
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    with st.form("entrada"):
        sel = st.selectbox("Produto", ["+ NOVO"] + df_p['nome'].tolist())
        nome = st.text_input("Nome do Produto") if sel == "+ NOVO" else sel
        c1, c2, c3 = st.columns(3)
        qtd = c1.number_input("Quantidade", min_value=1)
        custo = c2.number_input("Custo Unitário", min_value=0.0)
        margem = c3.slider("Margem %", 10, 200, 50)
        venc = st.date_input("Data de Validade")
        
        if st.form_submit_button("Confirmar Entrada"):
            preco_final = custo * (1 + margem/100)
            if sel in df_p['nome'].tolist():
                idx = df_p[df_p['nome'] == sel].index[0]
                df_p.at[idx, 'estoque'] += qtd
                df_p.at[idx, 'preco'] = preco_final
                df_p.at[idx, 'validade'] = venc.strftime("%d/%m/%Y")
            else:
                novo = pd.DataFrame([{"nome": nome, "estoque": qtd, "validade": venc.strftime("%d/%m/%Y"), "preco": preco_final, "estoque_minimo": 5}])
                df_p = pd.concat([df_p, novo], ignore_index=True)
            conn
