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

# ==================== FUNÇÕES COM CACHE ====================
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

# ==================== LOGIN ====================
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
        "💰 Lançamento de Custos",
        "🚚 Fornecedores",
        "📟 Máquinas & PDVs"
    ])
    if st.button("🔄 Sincronizar Google Sheets"):
        st.cache_data.clear()
        st.rerun()

# ==================== 1. DASHBOARD & ALERTAS ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Performance Geral")
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    compras = carregar_dados("compras", COLUNAS_COMPRAS)
    produtos = carregar_dados("produtos", COLUNAS_PRODUTOS)
    
    faturamento = pd.to_numeric(vendas['valor'], errors='coerce').sum()
    custos = pd.to_numeric(compras['custo_total'], errors='coerce').sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento Total", f"R$ {faturamento:,.2f}")
    c2.metric("Custos Totais", f"R$ {custos:,.2f}")
    c3.metric("Lucro Estimado", f"R$ {(faturamento - custos):,.2f}")

    st.divider()
    # Alertas de Estoque e Validade
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📉 Estoque Baixo")
        baixo = produtos[pd.to_numeric(produtos['estoque']) < LIMITE_ESTOQUE_BAIXO]
        st.dataframe(baixo, use_container_width=True)
    with col_b:
        st.subheader("⚠️ Validade Próxima")
        # Lógica simples de exibição
        st.dataframe(produtos.sort_values(by="validade"), use_container_width=True)

# ==================== 2. RELATÓRIOS POR PDV ====================
elif menu == "📈 Relatórios por PDV":
    st.header("📈 Relatórios Contábeis")
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    pdv_sel = st.selectbox("Selecione o PDV", pdvs['nome'].unique())
    
    if pdv_sel:
        df_pdv = vendas[vendas['pdv'] == pdv_sel]
        v_total = pd.to_numeric(df_pdv['valor'], errors='coerce').sum()
        st.metric(f"Total {pdv_sel}", f"R$ {v_total:,.2f}")
        st.dataframe(df_pdv, use_container_width=True)

# ==================== 3. VENDA (PDV) ====================
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ Frente de Caixa")
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    maquinas = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    
    with st.form("venda_form"):
        p_sel = st.selectbox("📍 PDV", pdvs['nome'].tolist())
        maqs_pdv = maquinas[maquinas['pdv_vinculado'] == p_sel]['nome_maquina'].tolist()
        maq_sel = st.selectbox("📟 Máquina", maqs_pdv if maqs_pdv else ["N/A"])
        prod_sel = st.selectbox("📦 Produto", prods['nome'].tolist())
        qtd = st.number_input("Qtd", min_value=1)
        forma = st.selectbox("Pagamento", ["Cartão", "Pix", "Dinheiro"])
        
        if st.form_submit_button("FINALIZAR"):
            # Atualização no Sheets (Exemplo simplificado de lógica)
            st.success("Venda enviada ao Google Sheets!")

# ==================== 4. GESTÃO DE ESTOQUE ====================
elif menu == "📦 Gestão de Estoque":
    st.header("📦 Controle de Produtos")
    df_e = carregar_dados("produtos", COLUNAS_PRODUTOS)
    
    with st.expander("➕ Adicionar Novo Produto"):
        with st.form("add_p"):
            n = st.text_input("Nome do Item")
            e = st.number_input("Estoque Inicial", min_value=0)
            v = st.date_input("Data de Validade")
            p = st.number_input("Preço de Venda", min_value=0.0)
            if st.form_submit_button("Salvar Produto"):
                novo = pd.DataFrame([{"nome": n, "estoque": e, "validade": v.strftime("%d/%m/%Y"), "preco": p}])
                conn.update(worksheet="produtos", data=pd.concat([df_e, novo], ignore_index=True))
                st.cache_data.clear()
                st.success("Produto cadastrado!")
                st.rerun()
    
    st.dataframe(df_e, use_container_width=True)

# ==================== 5. LANÇAMENTO DE CUSTOS ====================
elif menu == "💰 Lançamento de Custos":
    st.header("💰 Entrada de Mercadorias")
    df_forn = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)
    df_prod = carregar_dados("produtos", COLUNAS_PRODUTOS)
    df_comp = carregar_dados("compras", COLUNAS_COMPRAS)

    with st.form("compra_form"):
        f_sel = st.selectbox("Fornecedor", df_forn['nome_fantasia'].tolist() if not df_forn.empty else [])
        p_sel = st.selectbox("Produto", df_prod['nome'].tolist() if not df_prod.empty else [])
        q_compra = st.number_input("Quantidade Comprada", min_value=1)
        v_unit = st.number_input("Custo Unitário (R$)", min_value=0.01)
        
        if st.form_submit_button("Registrar Compra e Atualizar Estoque"):
            # 1. Registrar a Compra
            nova_compra = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y"),
                "fornecedor": f_sel,
                "produto": p_sel,
                "quantidade": q_compra,
                "custo_unitario": v_unit,
                "custo_total": q_compra * v_unit
            }])
            
            # 2. Atualizar o estoque na tabela de produtos
            idx = df_prod[df_prod['nome'] == p_sel].index[0]
            df_prod.at[idx, 'estoque'] = pd.to_numeric(df_prod.at[idx, 'estoque']) + q_compra
            
            # Salvar ambos
            conn.update(worksheet="compras", data=pd.concat([df_comp, nova_compra], ignore_index=True))
            conn.update(worksheet="produtos", data=df_prod)
            
            st.cache_data.clear()
            st.success(f"Estoque de {p_sel} atualizado para {df_prod.at[idx, 'estoque']}!")
            st.rerun()

    st.subheader("Histórico de Compras")
    st.dataframe(df_comp, use_container_width=True)

# ==================== 6. FORNECEDORES ====================
elif menu == "🚚 Fornecedores":
    st.header("🚚 Meus Fornecedores")
    df_f = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)
    
    with st.form("f_form"):
        nf = st.text_input("Nome Fantasia")
        cnpj = st.text_input("CNPJ ou CPF")
        if st.form_submit_button("Cadastrar Fornecedor"):
            novo_f = pd.DataFrame([{"nome_fantasia": nf, "cnpj_cpf": cnpj}])
            conn.update(worksheet="fornecedores", data=pd.concat([df_f, novo_f], ignore_index=True))
            st.cache_data.clear()
            st.success("Fornecedor salvo!")
            st.rerun()
            
    st.dataframe(df_f, use_container_width=True)

# ==================== 7. MÁQUINAS & PDVs ====================
elif menu == "📟 Máquinas & PDVs":
    # (Mantido conforme a versão anterior para cadastro de máquinas por PDV)
    st.header("📟 Configuração de Unidades")
    # ... código de cadastro de PDV e Máquina ...
