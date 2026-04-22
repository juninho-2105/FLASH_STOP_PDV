import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v4.7", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- COLUNAS ATUALIZADAS (Adicionado 'estoque_minimo') ---
COLUNAS_PRODUTOS = ["nome", "estoque", "validade", "preco", "estoque_minimo"]
COLUNAS_VENDAS = ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"]
COLUNAS_MAQUINAS = ["nome_maquina", "tid", "pdv_vinculado", "taxa_debito", "taxa_credito"]
COLUNAS_PONTOS = ["nome"]
COLUNAS_FORNECEDORES = ["nome_fantasia", "cnpj_cpf"]
COLUNAS_COMPRAS = ["data", "fornecedor", "produto", "quantidade", "custo_unitario", "custo_total"]

# ==================== FUNÇÕES DE APOIO ====================
@st.cache_data(ttl=60)
def carregar_dados(nome_aba, colunas):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        df = df.dropna(how='all')
        if df.empty: return pd.DataFrame(columns=colunas)
        return df
    except:
        return pd.DataFrame(columns=colunas)

def render_logo(font_size="42px"):
    st.markdown(f'<div style="text-align:center;"><h1 style="font-family:Arial Black; font-size:{font_size}; color:#000;">FLASH <span style="color:#7CFC00; font-style:italic;">STOP</span></h1></div>', unsafe_allow_html=True)

# ==================== LOGIN ====================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

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
    menu = st.radio("Navegação", ["📊 Dashboard & Alertas", "📈 Relatórios", "🛍️ Venda (PDV)", "💰 Custos", "📦 Estoque", "🚚 Fornecedores", "📟 Máquinas"])
    if st.button("🔄 Sincronizar Tudo"):
        st.cache_data.clear()
        st.rerun()

# ==================== 1. DASHBOARD COM ALERTAS CRÍTICOS ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Centro de Controle")
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    
    # --- LÓGICA DE ALERTAS ---
    hoje = datetime.now()
    vencendo = []
    estoque_baixo = []
    
    for _, item in prods.iterrows():
        # Alerta de Estoque Baixo (Baseado no campo estoque_minimo)
        try:
            est_min = float(item['estoque_minimo']) if 'estoque_minimo' in item else 5
            if float(item['estoque']) <= est_min:
                estoque_baixo.append(item)
        except: pass
        
        # Alerta de Vencimento (Próximos 10 dias)
        try:
            dt_venc = datetime.strptime(item['validade'], "%d/%m/%Y")
            if dt_venc <= hoje + timedelta(days=10):
                vencendo.append(item)
        except: pass

    # Exibição de Alertas Críticos
    if estoque_baixo or vencendo:
        st.warning(f"🔔 Você tem {len(estoque_baixo)} itens com estoque baixo e {len(vencendo)} produtos próximos ao vencimento!")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            if estoque_baixo:
                st.error("📉 ESTOQUE CRÍTICO")
                st.table(pd.DataFrame(estoque_baixo)[['nome', 'estoque', 'estoque_minimo']])
        with col_a2:
            if vencendo:
                st.warning("📅 VENCIMENTO PRÓXIMO")
                st.table(pd.DataFrame(vencendo)[['nome', 'validade']])
    else:
        st.success("✅ Tudo em dia! Sem alertas críticos no momento.")

    # Métricas Financeiras
    bruto = pd.to_numeric(vendas['valor_bruto'], errors='coerce').sum()
    liquido = pd.to_numeric(vendas['valor_liquido'], errors='coerce').sum()
    c1, c2 = st.columns(2)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido Real", f"R$ {liquido:,.2f}")

# ==================== 5. GESTÃO DE ESTOQUE (COM CAMPO DE MÍNIMO) ====================
elif menu == "📦 Estoque":
    st.header("📦 Gestão de Produtos")
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    
    with st.expander("➕ Cadastrar Novo Produto"):
        with st.form("form_novo_p"):
            n = st.text_input("Nome do Produto")
            e = st.number_input("Estoque Inicial", min_value=0)
            e_min = st.number_input("Avisar quando o estoque for menor que:", min_value=1, value=5)
            v = st.date_input("Validade")
            p = st.number_input("Preço de Venda", min_value=0.0)
            if st.form_submit_button("Salvar Produto"):
                novo = pd.DataFrame([{"nome": n, "estoque": e, "validade": v.strftime("%d/%m/%Y"), "preco": p, "estoque_minimo": e_min}])
                conn.update(worksheet="produtos", data=pd.concat([df_p, novo], ignore_index=True))
                st.cache_data.clear()
                st.success("Produto salvo com alerta de estoque configurado!")
                st.rerun()
    
    st.subheader("Inventário Completo")
    st.dataframe(df_p, use_container_width=True)

# ... (Mantenha as outras funções de Venda, Custos, Fornecedores e Máquinas conforme v4.6)
