import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v4.0", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- REGRAS DE NEGÓCIO ---
DIAS_ALERTA_VENCIMENTO = 10 
LIMITE_ESTOQUE_BAIXO = 5

# --- COLUNAS PADRÃO ---
COLUNAS_PRODUTOS = ["nome", "estoque", "validade", "preco"]
COLUNAS_VENDAS = ["data", "pdv", "maquina", "produto", "valor", "forma"]
COLUNAS_MAQUINAS = ["nome_maquina", "tid", "pdv_vinculado"]
COLUNAS_PONTOS = ["nome"]
COLUNAS_FORNECEDORES = ["nome_fantasia", "cnpj_cpf"]
COLUNAS_COMPRAS = ["data", "fornecedor", "produto", "quantidade", "custo_unitario", "custo_total"]

# ==================== FUNÇÕES COM CACHE (VELOCIDADE) ====================
@st.cache_data(ttl=600)
def carregar_dados(nome_aba, colunas):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        df = df.dropna(how='all')
        if df.empty: return pd.DataFrame(columns=colunas)
        return df
    except:
        return pd.DataFrame(columns=colunas)

def render_logo(font_size="42px"):
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-family: 'Arial Black', sans-serif; font-size: {font_size}; color: #000000; letter-spacing: -2px; margin-bottom: 0;">
                FLASH <span style="color: #7CFC00; font-style: italic;">STOP</span>
            </h1>
            <p style="font-family: sans-serif; font-size: 12px; color: #666; margin-top: -10px; font-weight: bold;">CONVENIÊNCIA INTELIGENTE</p>
        </div>
    """, unsafe_allow_html=True)

# ==================== SISTEMA DE LOGIN ====================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        render_logo("55px")
        with st.form("login"):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if u == "admin" and s == "flash123":
                    st.session_state.autenticado = True
                    st.rerun()
                else: st.error("Credenciais inválidas")
    st.stop()

# ==================== MENU LATERAL ====================
with st.sidebar:
    render_logo("30px")
    st.divider()
    menu = st.radio("Navegação", [
        "📊 Dashboard & Alertas", 
        "📈 Relatórios por PDV",
        "🛍️ Venda (PDV)", 
        "📦 Gestão de Estoque", 
        "📟 Máquinas & PDVs",
        "💰 Custos e Fornecedores"
    ])
    if st.button("🔄 Sincronizar Google Sheets"):
        st.cache_data.clear()
        st.rerun()

# ==================== 1. DASHBOARD & ALERTAS ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Performance Geral")
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    compras = carregar_dados("compras", COLUNAS_COMPRAS)
    
    faturamento = pd.to_numeric(vendas['valor'], errors='coerce').sum()
    custos = pd.to_numeric(compras['custo_total'], errors='coerce').sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento Total", f"R$ {faturamento:,.2f}")
    c2.metric("Custos Totais", f"R$ {custos:,.2f}")
    c3.metric("Lucro Estimado", f"R$ {(faturamento - custos):,.2f}")

# ==================== 2. RELATÓRIOS CONTÁBEIS POR PDV ====================
elif menu == "📈 Relatórios por PDV":
    st.header("📈 Relatórios Contábeis")
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    
    pdv_sel = st.selectbox("Selecione o PDV para análise", pdvs['nome'].unique())
    
    if pdv_sel:
        df_pdv = vendas[vendas['pdv'] == pdv_sel]
        
        col1, col2, col3 = st.columns(3)
        venda_total_pdv = pd.to_numeric(df_pdv['valor'], errors='coerce').sum()
        qtd_vendas = len(df_pdv)
        ticket_medio = venda_total_pdv / qtd_vendas if qtd_vendas > 0 else 0
        
        col1.metric(f"Vendas em {pdv_sel}", f"R$ {venda_total_pdv:,.2f}")
        col2.metric("Qtd Transações", qtd_vendas)
        col3.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
        
        st.subheader("Extrato de Vendas")
        st.dataframe(df_pdv, use_container_width=True)

# ==================== 3. VENDA (PDV) ====================
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ Frente de Caixa")
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    maquinas = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    
    with st.form("venda_form"):
        p_sel = st.selectbox("📍 PDV", pdvs['nome'].tolist())
        # Filtra máquinas apenas do PDV selecionado
        maqs_pdv = maquinas[maquinas['pdv_vinculado'] == p_sel]['nome_maquina'].tolist()
        maq_sel = st.selectbox("📟 Máquina de Cartão", maqs_pdv if maqs_pdv else ["Sem Máquina"])
        
        prod_sel = st.selectbox("📦 Produto", prods['nome'].tolist())
        qtd = st.number_input("Quantidade", min_value=1, value=1)
        forma = st.selectbox("Forma de Pagamento", ["Cartão Crédito", "Cartão Débito", "Pix", "Dinheiro"])
        
        if st.form_submit_button("FINALIZAR VENDA"):
            # Lógica de baixa de estoque e salvamento (idêntica à anterior, mas incluindo 'maq_sel')
            st.success(f"Venda registrada em {p_sel} via {maq_sel}!")

# ==================== 4. MÁQUINAS & PDVs ====================
elif menu == "📟 Máquinas & PDVs":
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 Cadastrar Novo PDV")
        df_p = carregar_dados("pontos", COLUNAS_PONTOS)
        novo_pdv = st.text_input("Nome da Unidade (Ex: Condomínio Solar)")
        if st.button("Salvar PDV"):
            novo_df = pd.concat([df_p, pd.DataFrame([{"nome": novo_pdv}])], ignore_index=True)
            conn.update(worksheet="pontos", data=novo_df)
            st.cache_data.clear()
            st.success("PDV Cadastrado!")
            st.rerun()

    with col2:
        st.subheader("📟 Vincular Máquina")
        df_m = carregar_dados("maquinas", COLUNAS_MAQUINAS)
        nome_m = st.text_input("Nome/Modelo da Máquina")
        tid_m = st.text_input("TID / ID Único")
        pdv_vinc = st.selectbox("Vincular ao PDV", df_p['nome'].tolist() if not df_p.empty else [])
        
        if st.button("Salvar Máquina"):
            nova_maq = pd.DataFrame([{"nome_maquina": nome_m, "tid": tid_m, "pdv_vinculado": pdv_vinc}])
            conn.update(worksheet="maquinas", data=pd.concat([df_m, nova_maq], ignore_index=True))
            st.cache_data.clear()
            st.success("Máquina vinculada com sucesso!")
            st.rerun()
    
    st.divider()
    st.subheader("Máquinas Ativas por Unidade")
    st.dataframe(carregar_dados("maquinas", COLUNAS_MAQUINAS), use_container_width=True)

# ==================== 5. ESTOQUE & FORNECEDORES (RESTANTE DO CÓDIGO) ====================
# ... (Manter as funções de estoque e fornecedores que você já tinha)
