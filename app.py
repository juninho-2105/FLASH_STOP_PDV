import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v3.8", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- REGRAS DE NEGÓCIO ---
DIAS_ALERTA_VENCIMENTO = 10 
LIMITE_ESTOQUE_BAIXO = 5

# --- DEFINIÇÃO DE COLUNAS (Ordem exata do Google Sheets) ---
COLUNAS_PRODUTOS = ["nome", "estoque", "validade", "preco"]
COLUNAS_VENDAS = ["data", "pdv", "maquina", "produto", "valor", "forma"]
COLUNAS_MAQUINAS = ["nome", "tid", "pdv_vinculado"]
COLUNAS_PONTOS = ["nome"]
COLUNAS_FORNECEDORES = ["nome_fantasia", "cnpj_cpf", "contato", "categoria"]
COLUNAS_COMPRAS = ["data", "fornecedor", "produto", "quantidade", "custo_unitario", "custo_total"]

# ==================== FUNÇÕES UTILITÁRIAS ====================
def render_flash_stop_logo(font_size="42px"):
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-family: 'Arial Black', sans-serif; font-size: {font_size}; color: #000000; letter-spacing: -2px; margin-bottom: 0;">
                FLASH <span style="color: #7CFC00; font-style: italic;">STOP</span>
            </h1>
            <p style="font-family: sans-serif; font-size: 12px; color: #666; margin-top: -10px; font-weight: bold;">
                CONVENIÊNCIA INTELIGENTE
            </p>
        </div>
    """, unsafe_allow_html=True)

def carregar_aba(nome_aba, colunas_padrao):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        df = df.dropna(how='all')
        if df.empty:
            return pd.DataFrame(columns=colunas_padrao)
        return df
    except:
        return pd.DataFrame(columns=colunas_padrao)

# ==================== SISTEMA DE LOGIN ====================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        render_flash_stop_logo(font_size="55px")
        st.subheader("Acesso ao Sistema")
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
    render_flash_stop_logo(font_size="30px")
    st.divider()
    menu = st.radio("Navegação", [
        "📊 Dashboard & Alertas", 
        "🛍️ Venda (PDV)", 
        "💰 Lançamento de Custos",
        "📦 Gestão de Estoque", 
        "🚚 Fornecedores",
        "📍 Cadastrar PDV", 
        "📟 Máquinas (Automação)"
    ])
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.rerun()

# ==================== 1. DASHBOARD & ALERTAS ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Performance e Alertas Críticos")
    
    vendas = carregar_aba("vendas", COLUNAS_VENDAS)
    compras = carregar_aba("compras", COLUNAS_COMPRAS)
    produtos = carregar_aba("produtos", COLUNAS_PRODUTOS)
    
    faturamento = pd.to_numeric(vendas['valor'], errors='coerce').sum()
    custos_totais = pd.to_numeric(compras['custo_total'], errors='coerce').sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento", f"R$ {faturamento:,.2f}")
    c2.metric("Custos (Compras)", f"R$ {custos_totais:,.2f}")
    c3.metric("Lucro Estimado", f"R$ {(faturamento - custos_totais):,.2f}")

    st.divider()
    
    # Lógica de Alertas
    hoje = datetime.now()
    produtos['validade_dt'] = pd.to_datetime(produtos['validade'], dayfirst=True, errors='coerce')
    produtos['estoque'] = pd.to_numeric(produtos['estoque'], errors='coerce').fillna(0)
    limite_venc = hoje + timedelta(days=DIAS_ALERTA_VENCIMENTO)
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        st.subheader("❌ Vencidos")
        v = produtos[produtos['validade_dt'] < hoje]
        if not v.empty:
            for _, r in v.iterrows(): st.error(f"**VENCIDO:** {r['nome']} ({r['validade']})")
        else: st.success("Nenhum item vencido.")

    with col_b:
        st.subheader(f"⚠️ Vence em {DIAS_ALERTA_VENCIMENTO} dias")
        pv = produtos[(produtos['validade_dt'] >= hoje) & (produtos['validade_dt'] <= limite_venc)]
        if not pv.empty:
            for _, r in pv.iterrows():
                dias = (r['validade_dt'] - hoje).days
                st.warning(f"**{r['nome']}**: {dias} dias ({r['validade']})")
        else: st.success("Sem vencimentos próximos.")

    with col_c:
        st.subheader("📉 Estoque Crítico")
        acabando = produtos[produtos['estoque'] < LIMITE_ESTOQUE_BAIXO]
        if not acabando.empty:
            for _, r in acabando.iterrows():
                st.error(f"**REPOR:** {r['nome']} ({int(r['estoque'])} un)")
        else: st.success("Estoque em dia.")

# ==================== 2. VENDA (PDV) ====================
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ Frente de Caixa")
    pdvs = carregar_aba("pontos", COLUNAS_PONTOS)
    prods = carregar_aba("produtos", COLUNAS_PRODUTOS)
    
    with st.form("venda_form"):
        p_sel = st.selectbox("📍 Selecione o PDV", pdvs['nome'].tolist() if not pdvs.empty else [])
        prod_sel = st.selectbox("📦 Item", prods['nome'].tolist() if not prods.empty else [])
        col1, col2 = st.columns(2)
        with col1:
            qtd = st.number_input("Quantidade", min_value=1, value=1)
        with col2:
            forma = st.selectbox("Pagamento", ["Cartão", "Pix", "Dinheiro"])
        
        if st.form_submit_button("FINALIZAR VENDA"):
            prods_now = carregar_aba("produtos", COLUNAS_PRODUTOS)
            idx = prods_now[prods_now['nome'] == prod_sel].index[0]
            estoque_atual = int(prods_now.at[idx, 'estoque'])

            if estoque_atual >= qtd:
                venda_df = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": p_sel, "maquina": "N/A", "produto": prod_sel, "valor": float(prods_now.at[idx, 'preco']) * qtd, "forma": forma}])
                conn.update(worksheet="vendas", data=pd.concat([carregar_aba("vendas", COLUNAS_VENDAS), venda_df], ignore_index=True))
                prods_now.at[idx, 'estoque'] = estoque_atual - qtd
                conn.update(worksheet="produtos", data=prods_now)
                st.success("Venda processada!")
                st.balloons()
                time.sleep(1)
                st.rerun()
            else: st.error(f"Estoque insuficiente! Disponível: {estoque_atual}")

# ==================== 3. LANÇAMENTO DE CUSTOS ====================
elif menu == "💰 Lançamento de Custos":
    st.header("💰 Entrada de Mercadorias")
    df_forn = carregar_aba("fornecedores", COLUNAS_FORNECEDORES)
    df_prod = carregar_aba("produtos", COLUNAS_PRODUTOS)
    df_comp = carregar_aba("compras", COLUNAS_COMPRAS)

    with st.expander("➕ Lançar Compra"):
        with st.form("compra_form"):
            f_sel = st.selectbox("Fornecedor", df_forn['nome_fantasia'].tolist() if not df_forn.empty else [])
            p_sel = st.selectbox("Produto", df_prod['nome'].tolist() if not df_prod.empty else [])
            q_compra = st.number_input("Qtd", min_value=1)
            v_unit = st.number_input("Custo Unitário", min_value=0.01)
            if st.form_submit_button("Registrar Entrada"):
                nova_compra = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "fornecedor": f_sel, "produto": p_sel, "quantidade": q_compra, "custo_unitario": v_unit, "custo_total": q_compra * v_unit}])
                conn.update(worksheet="compras", data=pd.concat([df_comp, nova_compra], ignore_index=True))
                # Atualiza Estoque
                idx = df_prod[df_prod['nome'] == p_sel].index[0]
                df_prod.at[idx, 'estoque'] = int(df_prod.at[idx, 'estoque']) + q_compra
                conn.update(worksheet="produtos", data=df_prod)
                st.success("Estoque atualizado!")
                st.rerun()
    st.dataframe(df_comp, use_container_width=True)

# ==================== 4. GESTÃO DE ESTOQUE ====================
elif menu == "📦 Gestão de Estoque":
    st.header("📦 Estoque")
    df_e = carregar_aba("produtos", COLUNAS_PRODUTOS)
    with st.expander("➕ Novo Produto"):
        with st.form("add_p"):
            n = st.text_input("Nome")
            e = st.number_input("Estoque", min_value=0)
            v = st.date_input("Validade")
            p = st.number_input("Preço Venda", min_value=0.0)
            if st.form_submit_button("Salvar"):
                novo = pd.DataFrame([{"nome": n, "estoque": e, "validade": v.strftime("%d/%m/%Y"), "preco": p}])
                conn.update(worksheet="produtos", data=pd.concat([df_e, novo], ignore_index=True))
                st.rerun()
    st.dataframe(df_e, use_container_width=True)

# ==================== 5. FORNECEDORES ====================
elif menu == "🚚 Fornecedores":
    st.header("🚚 Cadastro de Fornecedores")
    df_f = carregar_aba("fornecedores", COLUNAS_FORNECEDORES)
    with st.form("f_form"):
        nf = st.text_input("Nome Fantasia")
        cnpj = st.text_input("CNPJ/CPF")
        if st.form_submit_button("Cadastrar"):
            novo = pd.DataFrame([{"nome_fantasia": nf, "cnpj_cpf": cnpj}])
            conn.update(worksheet="fornecedores", data=pd.concat([df_f, novo], ignore_index=True))
            st.rerun()
    st.dataframe(df_f, use_container_width=True)

# ==================== 6. PDV E MÁQUINAS ====================
elif menu == "📍 Cadastrar PDV":
    st.header("📍 PDVs")
    df_p = carregar_aba("pontos", COLUNAS_PONTOS)
    n_pdv = st.text_input("Nome Unidade")
    if st.button("Adicionar"):
        conn.update(worksheet="pontos", data=pd.concat([df_p, pd.DataFrame([{"nome": n_pdv}])], ignore_index=True))
        st.rerun()
    st.dataframe(df_p)

elif menu == "📟 Máquinas (Automação)":
    st.header("📟 Máquinas")
    df_m = carregar_aba("maquinas", COLUNAS_MAQUINAS)
    st.dataframe(df_m)
