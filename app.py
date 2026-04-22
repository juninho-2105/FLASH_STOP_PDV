import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v4.8", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- COLUNAS PADRÃO (O Sheets deve seguir esta estrutura) ---
COLUNAS_PRODUTOS = ["nome", "estoque", "validade", "preco", "estoque_minimo"]
COLUNAS_VENDAS = ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"]
COLUNAS_MAQUINAS = ["nome_maquina", "tid", "pdv_vinculado", "taxa_debito", "taxa_credito"]
COLUNAS_PONTOS = ["nome"]
COLUNAS_FORNECEDORES = ["nome_fantasia", "cnpj_cpf"]
COLUNAS_COMPRAS = ["data", "fornecedor", "produto", "quantidade", "custo_unitario", "custo_total"]

# ==================== FUNÇÕES DE DADOS ====================
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
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-family: 'Arial Black', sans-serif; font-size: {font_size}; color: #000000; letter-spacing: -2px; margin-bottom: 0;">
                FLASH <span style="color: #7CFC00; font-style: italic;">STOP</span>
            </h1>
        </div>
    """, unsafe_allow_html=True)

# ==================== LOGIN ====================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    render_logo("55px")
    with st.form("login"):
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar"):
            if u == "admin" and s == "flash123":
                st.session_state.autenticado = True
                st.rerun()
    st.stop()

# ==================== MENU LATERAL ====================
with st.sidebar:
    render_logo("30px")
    st.divider()
    menu = st.radio("Navegação", [
        "📊 Dashboard & Alertas",
        "📈 Relatórios Contábeis", 
        "🛍️ Venda (PDV)", 
        "💰 Lançamento de Custos", 
        "📦 Gestão de Estoque", 
        "🚚 Fornecedores",
        "📟 Máquinas & PDVs"
    ])
    if st.button("🔄 Sincronizar Tudo"):
        st.cache_data.clear()
        st.rerun()

# ==================== 1. DASHBOARD & ALERTAS ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Centro de Comando")
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    
    hoje = datetime.now()
    vencendo = []
    estoque_baixo = []
    
    for _, item in prods.iterrows():
        # Alerta Estoque Baixo
        try:
            est_min = float(item['estoque_minimo']) if 'estoque_minimo' in item else 5
            if float(item['estoque']) <= est_min:
                estoque_baixo.append(item)
        except: pass
        
        # Alerta Validade
        try:
            dt_venc = datetime.strptime(item['validade'], "%d/%m/%Y")
            if dt_venc <= hoje + timedelta(days=10):
                vencendo.append(item)
        except: pass

    if estoque_baixo or vencendo:
        col_a, col_b = st.columns(2)
        with col_a:
            if estoque_baixo:
                st.error(f"⚠️ {len(estoque_baixo)} Itens em Estoque Crítico")
                st.dataframe(pd.DataFrame(estoque_baixo)[['nome', 'estoque', 'estoque_minimo']], use_container_width=True)
        with col_b:
            if vencendo:
                st.warning(f"📅 {len(vencendo)} Itens Próximos ao Vencimento")
                st.dataframe(pd.DataFrame(vencendo)[['nome', 'validade']], use_container_width=True)

    bruto = pd.to_numeric(vendas['valor_bruto'], errors='coerce').sum()
    liquido = pd.to_numeric(vendas['valor_liquido'], errors='coerce').sum()
    c1, c2 = st.columns(2)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido Real", f"R$ {liquido:,.2f}")

# ==================== 2. RELATÓRIOS CONTÁBEIS ====================
elif menu == "📈 Relatórios Contábeis":
    st.header("📈 Auditoria e Resultados")
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    
    pdv_sel = st.selectbox("Filtrar por Unidade", ["Todos"] + pdvs['nome'].tolist())
    df_rel = vendas if pdv_sel == "Todos" else vendas[vendas['pdv'] == pdv_sel]
    
    st.metric(f"Total {pdv_sel}", f"R$ {pd.to_numeric(df_rel['valor_liquido'], errors='coerce').sum():,.2f}")
    st.dataframe(df_rel, use_container_width=True)

# ==================== 3. VENDA (PDV) ====================
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ Frente de Caixa")
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    maquinas = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    
    with st.form("venda"):
        p_sel = st.selectbox("📍 PDV", pdvs['nome'].tolist()) if not pdvs.empty else None
        maqs = maquinas[maquinas['pdv_vinculado'] == p_sel]
        maq_sel = st.selectbox("📟 Máquina", maqs['nome_maquina'].tolist() if not maqs.empty else ["N/A"])
        prod_sel = st.selectbox("📦 Produto", prods['nome'].tolist()) if not prods.empty else None
        qtd = st.number_input("Qtd", min_value=1, value=1)
        forma = st.selectbox("Pagamento", ["Cartão Débito", "Cartão Crédito", "Pix", "Dinheiro"])
        
        if st.form_submit_button("FINALIZAR"):
            idx = prods[prods['nome'] == prod_sel].index[0]
            bruto = float(prods.at[idx, 'preco']) * qtd
            
            taxa = 0.0
            if not maqs.empty and maq_sel != "N/A":
                info = maqs[maqs['nome_maquina'] == maq_sel].iloc[0]
                taxa = float(info['taxa_debito']) if "Débito" in forma else float(info['taxa_credito']) if "Crédito" in forma else 0.0
            
            liquido = bruto * (1 - (taxa/100))
            
            nova = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": p_sel, "maquina": maq_sel, "produto": prod_sel, "valor_bruto": bruto, "valor_liquido": liquido, "forma": forma}])
            prods.at[idx, 'estoque'] = int(pd.to_numeric(prods.at[idx, 'estoque'])) - qtd
            
            conn.update(worksheet="vendas", data=pd.concat([carregar_dados("vendas", COLUNAS_VENDAS), nova], ignore_index=True))
            conn.update(worksheet="produtos", data=prods)
            st.cache_data.clear()
            st.success("Venda Concluída!")
            st.rerun()

# ==================== 4. LANÇAMENTO DE CUSTOS ====================
elif menu == "💰 Lançamento de Custos":
    st.header("💰 Entrada de Mercadoria")
    df_f = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    
    with st.form("custos"):
        f_sel = st.selectbox("Fornecedor", df_f['nome_fantasia'].tolist()) if not df_f.empty else []
        p_sel = st.selectbox("Produto", df_p['nome'].tolist()) if not df_p.empty else []
        custo_un = st.number_input("Custo Unitário", min_value=0.01)
        margem = st.slider("Margem Desejada (%)", 10, 200, 50)
        sugestao = custo_un * (1 + margem/100)
        st.info(f"💡 Sugestão de Venda: R$ {sugestao:.2f}")
        venda_f = st.number_input("Preço Final", value=float(sugestao))
        qtd_c = st.number_input("Qtd Comprada", min_value=1)
        
        if st.form_submit_button("Gravar Entrada"):
            idx = df_p[df_p['nome'] == p_sel].index[0]
            df_p.at[idx, 'estoque'] = int(pd.to_numeric(df_p.at[idx, 'estoque'])) + qtd_c
            df_p.at[idx, 'preco'] = venda_f
            conn.update(worksheet="produtos", data=df_p)
            st.cache_data.clear()
            st.success("Estoque e Preço Atualizados!")
            st.rerun()

# ==================== 5. GESTÃO DE ESTOQUE ====================
elif menu == "📦 Gestão de Estoque":
    st.header("📦 Inventário")
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    with st.expander("➕ Novo Produto"):
        with st.form("novo_p"):
            n = st.text_input("Nome")
            e = st.number_input("Estoque", min_value=0)
            e_m = st.number_input("Estoque Mínimo (Alerta)", min_value=1, value=5)
            v = st.date_input("Validade")
            p = st.number_input("Preço", min_value=0.0)
            if st.form_submit_button("Salvar"):
                novo = pd.DataFrame([{"nome": n, "estoque": e, "validade": v.strftime("%d/%m/%Y"), "preco": p, "estoque_minimo": e_m}])
                conn.update(worksheet="produtos", data=pd.concat([df_p, novo], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
    st.dataframe(df_p, use_container_width=True)

# ==================== 6. FORNECEDORES ====================
elif menu == "🚚 Fornecedores":
    st.header("🚚 Cadastro de Parceiros")
    df_f = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)
    with st.form("forn"):
        nf = st.text_input("Nome Fantasia")
        c = st.text_input("CNPJ/CPF")
        if st.form_submit_button("Cadastrar"):
            conn.update(worksheet="fornecedores", data=pd.concat([df_f, pd.DataFrame([{"nome_fantasia": nf, "cnpj_cpf": c}])], ignore_index=True))
            st.cache_data.clear()
            st.rerun()
    st.dataframe(df_f, use_container_width=True)

# ==================== 7. MÁQUINAS & PDVs ====================
elif menu == "📟 Máquinas & PDVs":
    st.header("📟 Configuração")
    col1, col2 = st.columns(2)
    df_pdv = carregar_dados("pontos", COLUNAS_PONTOS)
    df_maq = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    
    with col1:
        st.subheader("📍 Unidades")
        novo_pdv = st.text_input("Nome da Unidade")
        if st.button("Salvar PDV"):
            conn.update(worksheet="pontos", data=pd.concat([df_pdv, pd.DataFrame([{"nome": novo_pdv}])], ignore_index=True))
            st.cache_data.clear()
            st.rerun()
        st.table(df_pdv)

    with col2:
        st.subheader("📟 Máquinas e Taxas")
        with st.form("maq"):
            m_n = st.text_input("Nome Máquina")
            m_v = st.selectbox("Vincular PDV", df_pdv['nome'].tolist()) if not df_pdv.empty else []
            t_d = st.number_input("Taxa Débito (%)", step=0.01)
            t_c = st.number_input("Taxa Crédito (%)", step=0.01)
            if st.form_submit_button("Salvar Máquina"):
                nova = pd.DataFrame([{"nome_maquina": m_n, "tid": "N/A", "pdv_vinculado": m_v, "taxa_debito": t_d, "taxa_credito": t_c}])
                conn.update(worksheet="maquinas", data=pd.concat([df_maq, nova], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
        st.dataframe(df_maq, use_container_width=True)
