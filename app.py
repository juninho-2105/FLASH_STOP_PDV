import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v3.8", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- DEFINIÇÃO DE COLUNAS PADRÃO (Ordem exata do Google Sheets) ---
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
                # Busca secrets ou usa padrão
                try:
                    adm_u = st.secrets["auth"]["admin_user"]
                    adm_s = st.secrets["auth"]["admin_password"]
                except:
                    adm_u, adm_s = "admin", "flash123"

                if u == adm_u and s == adm_s:
                    st.session_state.autenticado = True
                    st.rerun()
                else: st.error("Credenciais inválidas")
    st.stop()

# ==================== MENU LATERAL ====================
with st.sidebar:
    render_flash_stop_logo(font_size="30px")
    st.divider()
    menu = st.radio("Navegação", [
        "📊 Dashboard Financeiro", 
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

# ==================== 1. DASHBOARD FINANCEIRO ====================
if menu == "📊 Dashboard Financeiro":
    st.header("📊 Performance de Negócio")
    
    vendas = carregar_aba("vendas", COLUNAS_VENDAS)
    compras = carregar_aba("compras", COLUNAS_COMPRAS)
    produtos = carregar_aba("produtos", COLUNAS_PRODUTOS)
    
    # Cálculos
    faturamento = pd.to_numeric(vendas['valor'], errors='coerce').sum()
    custos = pd.to_numeric(compras['custo_total'], errors='coerce').sum()
    lucro = faturamento - custos
    margem = (lucro / faturamento * 100) if faturamento > 0 else 0

    # KPIs Visuais
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faturamento Total", f"R$ {faturamento:,.2f}")
    c2.metric("Custos Acumulados", f"R$ {custos:,.2f}")
    c3.metric("Lucro Estimado", f"R$ {lucro:,.2f}")
    c4.metric("Margem Bruta", f"{margem:.1f}%")

    st.divider()
    
    col_inf1, col_inf2 = st.columns(2)
    with col_inf1:
        st.subheader("⚠️ Alertas de Reposição")
        produtos['estoque'] = pd.to_numeric(produtos['estoque'], errors='coerce').fillna(0)
        baixo = produtos[produtos['estoque'] < 5]
        if not baixo.empty:
            for _, r in baixo.iterrows(): st.warning(f"**Baixo:** {r['nome']} ({int(r['estoque'])} un)")
        else: st.success("Estoque saudável.")

    with col_inf2:
        st.subheader("📈 Últimas Vendas")
        st.dataframe(vendas.tail(10), use_container_width=True)

# ==================== 2. VENDA (PDV) ====================
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ Frente de Caixa")
    pdvs = carregar_aba("pontos", COLUNAS_PONTOS)
    prods = carregar_aba("produtos", COLUNAS_PRODUTOS)
    maqs = carregar_aba("maquinas", COLUNAS_MAQUINAS)
    
    if pdvs.empty or prods.empty:
        st.error("⚠️ Erro: Cadastre PDVs e Produtos antes de vender.")
    else:
        with st.form("venda_form"):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                pdv_sel = st.selectbox("📍 PDV", pdvs['nome'].tolist())
                prod_sel = st.selectbox("📦 Produto", prods['nome'].tolist())
            with col_v2:
                forma = st.selectbox("💳 Pagamento", ["Cartão", "Pix", "Dinheiro"])
                qtd = st.number_input("Qtd", min_value=1, value=1)
            
            if st.form_submit_button("FINALIZAR VENDA"):
                prods_now = carregar_aba("produtos", COLUNAS_PRODUTOS)
                idx = prods_now[prods_now['nome'] == prod_sel].index[0]
                estoque_atual = int(prods_now.at[idx, 'estoque'])

                if estoque_atual >= qtd:
                    # Registrar Venda
                    nova_venda = pd.DataFrame([{
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "pdv": pdv_sel,
                        "maquina": "N/A", # Pode vincular aqui a lógica de máquinas
                        "produto": prod_sel,
                        "valor": float(prods_now.at[idx, 'preco']) * qtd,
                        "forma": forma
                    }])
                    vendas_db = carregar_aba("vendas", COLUNAS_VENDAS)
                    conn.update(worksheet="vendas", data=pd.concat([vendas_db, nova_venda], ignore_index=True))
                    
                    # Baixa Estoque
                    prods_now.at[idx, 'estoque'] = estoque_atual - qtd
                    conn.update(worksheet="produtos", data=prods_now)
                    
                    st.success("Venda Concluída!")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Estoque insuficiente ({estoque_atual} un)")

# ==================== 3. LANÇAMENTO DE CUSTOS ====================
elif menu == "💰 Lançamento de Custos":
    st.header("💰 Entrada de Mercadoria (Custos)")
    df_compras = carregar_aba("compras", COLUNAS_COMPRAS)
    df_forn = carregar_aba("fornecedores", COLUNAS_FORNECEDORES)
    df_prod = carregar_aba("produtos", COLUNAS_PRODUTOS)

    with st.expander("➕ Lançar Nota/Compra"):
        with st.form("form_compra"):
            f_sel = st.selectbox("Fornecedor", df_forn['nome_fantasia'].tolist() if not df_forn.empty else ["Cadastre um fornecedor"])
            p_sel = st.selectbox("Produto", df_prod['nome'].tolist() if not df_prod.empty else ["Cadastre um produto"])
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                q_compra = st.number_input("Quantidade", min_value=1)
            with col_c2:
                v_unit = st.number_input("Custo Unitário (R$)", min_value=0.01, format="%.2f")
            
            if st.form_submit_button("Registrar Entrada"):
                # Atualizar Compras
                nova_compra = pd.DataFrame([{
                    "data": datetime.now().strftime("%d/%m/%Y"),
                    "fornecedor": f_sel, "produto": p_sel,
                    "quantidade": q_compra, "custo_unitario": v_unit,
                    "custo_total": q_compra * v_unit
                }])
                conn.update(worksheet="compras", data=pd.concat([df_compras, nova_compra], ignore_index=True))
                
                # Somar ao estoque
                idx = df_prod[df_prod['nome'] == p_sel].index[0]
                df_prod.at[idx, 'estoque'] = int(df_prod.at[idx, 'estoque']) + q_compra
                conn.update(worksheet="produtos", data=df_prod)
                
                st.success("Estoque e Custos atualizados!")
                st.rerun()

    st.subheader("📋 Histórico de Entradas")
    st.dataframe(df_compras, use_container_width=True)

# ==================== 4. GESTÃO DE ESTOQUE ====================
elif menu == "📦 Gestão de Estoque":
    st.header("📦 Inventário")
    df_estoque = carregar_aba("produtos", COLUNAS_PRODUTOS)

    with st.expander("➕ Novo Item"):
        with st.form("novo_p"):
            n = st.text_input("Nome")
            e = st.number_input("Estoque Inicial", min_value=0)
            v = st.date_input("Validade", format="DD/MM/YYYY")
            p = st.number_input("Preço de Venda", min_value=0.0, format="%.2f")
            if st.form_submit_button("Salvar"):
                novo = pd.DataFrame([{"nome": n, "estoque": e, "validade": v.strftime("%d/%m/%Y"), "preco": p}])
                conn.update(worksheet="produtos", data=pd.concat([df_estoque, novo], ignore_index=True))
                st.rerun()
    st.dataframe(df_estoque, use_container_width=True)

# ==================== 5. FORNECEDORES ====================
elif menu == "🚚 Fornecedores":
    st.header("🚚 Fornecedores")
    df_f = carregar_aba("fornecedores", COLUNAS_FORNECEDORES)
    with st.form("f_form"):
        nf = st.text_input("Nome Fantasia")
        doc = st.text_input("CNPJ/CPF")
        ct = st.text_input("Contato (Tel/E-mail)")
        cat = st.selectbox("Categoria", ["Alimentos", "Bebidas", "Limpeza", "Outros"])
        if st.form_submit_button("Cadastrar"):
            novo = pd.DataFrame([{"nome_fantasia": nf, "cnpj_cpf": doc, "contato": ct, "categoria": cat}])
            conn.update(worksheet="fornecedores", data=pd.concat([df_f, novo], ignore_index=True))
            st.rerun()
    st.dataframe(df_f, use_container_width=True)

# ==================== 6. PDV & MÁQUINAS (CADASTRO) ====================
elif menu == "📍 Cadastrar PDV":
    st.header("📍 Unidades")
    df_p = carregar_aba("pontos", COLUNAS_PONTOS)
    with st.form("pdv_f"):
        n = st.text_input("Nome da Unidade")
        if st.form_submit_button("Salvar"):
            conn.update(worksheet="pontos", data=pd.concat([df_p, pd.DataFrame([{"nome": n}])], ignore_index=True))
            st.rerun()
    st.dataframe(df_p)

elif menu == "📟 Máquinas (Automação)":
    st.header("📟 Máquinas de Cartão")
    df_m = carregar_aba("maquinas", COLUNAS_MAQUINAS)
    pdvs = carregar_aba("pontos", COLUNAS_PONTOS)
    with st.form("maq_f"):
        n = st.text_input("Nome Máquina")
        tid = st.text_input("Serial (TID)")
        p = st.selectbox("Vincular PDV", pdvs['nome'].tolist() if not pdvs.empty else [])
        if st.form_submit_button("Cadastrar"):
            novo = pd.DataFrame([{"nome": n, "tid": tid, "pdv_vinculado": p}])
            conn.update(worksheet="maquinas", data=pd.concat([df_m, novo], ignore_index=True))
            st.rerun()
    st.dataframe(df_m)
