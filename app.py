import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v4.9", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÕES DE ALERTAS ---
DIAS_ANTECEDENCIA_VENCIMENTO = 10 

# --- COLUNAS PADRÃO ---
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

# ==================== 1. DASHBOARD & ALERTAS (REVISADO) ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Centro de Monitoramento")
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    
    # --- PROCESSAMENTO DE ALERTAS ---
    hoje = datetime.now()
    lista_estoque_baixo = []
    lista_vencimento = []
    
    if not prods.empty:
        for _, item in prods.iterrows():
            # Alerta Estoque Baixo
            try:
                estoque_atual = float(item['estoque'])
                minimo_def = float(item['estoque_minimo']) if 'estoque_minimo' in item else 5
                if estoque_atual <= minimo_def:
                    lista_estoque_baixo.append({"Produto": item['nome'], "Atual": estoque_atual, "Mínimo": minimo_def})
            except: pass
            
            # Alerta Vencimento
            try:
                data_venc = datetime.strptime(item['validade'], "%d/%m/%Y")
                if data_venc <= hoje + timedelta(days=DIAS_ANTECEDENCIA_VENCIMENTO):
                    dias_restantes = (data_venc - hoje).days
                    lista_vencimento.append({"Produto": item['nome'], "Data": item['validade'], "Dias": dias_restantes})
            except: pass

    # --- EXIBIÇÃO VISUAL DOS ALERTAS ---
    col_alerta1, col_alerta2 = st.columns(2)
    
    with col_alerta1:
        if lista_estoque_baixo:
            st.error(f"🚨 ESTOQUE CRÍTICO ({len(lista_estoque_baixo)} itens)")
            st.dataframe(pd.DataFrame(lista_estoque_baixo), use_container_width=True, hide_index=True)
        else:
            st.success("✅ Estoque em níveis normais.")

    with col_alerta2:
        if lista_vencimento:
            st.warning(f"📅 ATENÇÃO AO VENCIMENTO ({len(lista_vencimento)} itens)")
            df_venc = pd.DataFrame(lista_vencimento).sort_values(by="Dias")
            st.dataframe(df_venc, use_container_width=True, hide_index=True)
        else:
            st.success("✅ Sem produtos vencendo nos próximos 10 dias.")

    st.divider()
    
    # Métricas Financeiras Rápidas
    bruto = pd.to_numeric(vendas['valor_bruto'], errors='coerce').sum()
    liquido = pd.to_numeric(vendas['valor_liquido'], errors='coerce').sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido Real", f"R$ {liquido:,.2f}")
    c3.metric("Taxas Pagas", f"R$ {bruto-liquido:,.2f}", delta_color="inverse")

# ==================== 2. RELATÓRIOS CONTÁBEIS ====================
elif menu == "📈 Relatórios Contábeis":
    st.header("📈 Auditoria de Vendas")
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    
    p_filtro = st.selectbox("Filtrar Unidade", ["Geral"] + pdvs['nome'].tolist())
    df_f = vendas if p_filtro == "Geral" else vendas[vendas['pdv'] == p_filtro]
    
    st.dataframe(df_f, use_container_width=True)

# ==================== 3. VENDA (PDV) ====================
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ Registro de Venda")
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    maqs = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    
    with st.form("pdv_venda"):
        unidade = st.selectbox("Unidade", pdvs['nome'].tolist()) if not pdvs.empty else None
        maquina = st.selectbox("Máquina", maqs[maqs['pdv_vinculado'] == unidade]['nome_maquina'].tolist() if not maqs.empty else ["N/A"])
        produto = st.selectbox("Produto", prods['nome'].tolist()) if not prods.empty else None
        qtd = st.number_input("Qtd", min_value=1)
        pagamento = st.selectbox("Pagamento", ["Cartão Débito", "Cartão Crédito", "Pix", "Dinheiro"])
        
        if st.form_submit_button("Confirmar Pagamento"):
            idx = prods[prods['nome'] == produto].index[0]
            v_bruto = float(prods.at[idx, 'preco']) * qtd
            
            # Cálculo de taxa automático
            taxa = 0.0
            if maquina != "N/A":
                maq_info = maqs[maqs['nome_maquina'] == maquina].iloc[0]
                taxa = float(maq_info['taxa_debito']) if "Débito" in pagamento else float(maq_info['taxa_credito']) if "Crédito" in pagamento else 0.0
            
            v_liquido = v_bruto * (1 - (taxa/100))
            
            venda_nova = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": unidade, "maquina": maquina, "produto": produto, "valor_bruto": v_bruto, "valor_liquido": v_liquido, "forma": pagamento}])
            prods.at[idx, 'estoque'] = int(pd.to_numeric(prods.at[idx, 'estoque'])) - qtd
            
            conn.update(worksheet="vendas", data=pd.concat([carregar_dados("vendas", COLUNAS_VENDAS), venda_nova], ignore_index=True))
            conn.update(worksheet="produtos", data=prods)
            st.cache_data.clear()
            st.success("Venda salva!")
            st.rerun()

# ==================== 4. LANÇAMENTO DE CUSTOS ====================
elif menu == "💰 Lançamento de Custos":
    st.header("💰 Entrada de Estoque e Precificação")
    df_f = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    
    with st.form("entrada"):
        p_sel = st.selectbox("Produto", df_p['nome'].tolist()) if not df_p.empty else []
        custo = st.number_input("Custo Unitário", min_value=0.01)
        margem = st.slider("Margem (%)", 0, 200, 50)
        sugestao = custo * (1 + margem/100)
        st.write(f"💡 Sugerido: **R$ {sugestao:.2f}**")
        preco_venda = st.number_input("Preço de Venda Final", value=float(sugestao))
        qtd_ent = st.number_input("Qtd Comprada", min_value=1)
        
        if st.form_submit_button("Atualizar Produto"):
            idx = df_p[df_p['nome'] == p_sel].index[0]
            df_p.at[idx, 'estoque'] = int(pd.to_numeric(df_p.at[idx, 'estoque'])) + qtd_ent
            df_p.at[idx, 'preco'] = preco_venda
            conn.update(worksheet="produtos", data=df_p)
            st.cache_data.clear()
            st.success("Estoque atualizado!")
            st.rerun()

# ==================== 5. GESTÃO DE ESTOQUE ====================
elif menu == "📦 Gestão de Estoque":
    st.header("📦 Inventário")
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    with st.expander("➕ Novo Produto"):
        with st.form("add"):
            n = st.text_input("Nome")
            e = st.number_input("Estoque Inicial", min_value=0)
            e_m = st.number_input("Estoque Mínimo (Alerta)", value=5)
            v = st.date_input("Validade")
            p = st.number_input("Preço", min_value=0.0)
            if st.form_submit_button("Cadastrar"):
                novo = pd.DataFrame([{"nome": n, "estoque": e, "validade": v.strftime("%d/%m/%Y"), "preco": p, "estoque_minimo": e_m}])
                conn.update(worksheet="produtos", data=pd.concat([df_p, novo], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
    st.dataframe(df_p, use_container_width=True)

# ==================== 6. FORNECEDORES ====================
elif menu == "🚚 Fornecedores":
    st.header("🚚 Fornecedores")
    df_f = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)
    with st.form("f"):
        nf = st.text_input("Nome Fantasia")
        c = st.text_input("CNPJ/CPF")
        if st.form_submit_button("Salvar"):
            conn.update(worksheet="fornecedores", data=pd.concat([df_f, pd.DataFrame([{"nome_fantasia": nf, "cnpj_cpf": c}])], ignore_index=True))
            st.cache_data.clear()
            st.rerun()
    st.dataframe(df_f, use_container_width=True)

# ==================== 7. MÁQUINAS & PDVs ====================
elif menu == "📟 Máquinas & PDVs":
    st.header("📟 Unidades e Terminais")
    col1, col2 = st.columns(2)
    df_pdv = carregar_dados("pontos", COLUNAS_PONTOS)
    df_maq = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    
    with col1:
        st.subheader("📍 Unidades")
        novo_p = st.text_input("Nome Unidade")
        if st.button("Adicionar"):
            conn.update(worksheet="pontos", data=pd.concat([df_pdv, pd.DataFrame([{"nome": novo_p}])], ignore_index=True))
            st.cache_data.clear()
            st.rerun()
        st.table(df_pdv)

    with col2:
        st.subheader("📟 Máquinas")
        with st.form("m"):
            mn = st.text_input("Nome")
            mv = st.selectbox("PDV", df_pdv['nome'].tolist()) if not df_pdv.empty else []
            td = st.number_input("Taxa Débito (%)", step=0.01)
            tc = st.number_input("Taxa Crédito (%)", step=0.01)
            if st.form_submit_button("Salvar Máquina"):
                n_maq = pd.DataFrame([{"nome_maquina": mn, "tid": "N/A", "pdv_vinculado": mv, "taxa_debito": td, "taxa_credito": tc}])
                conn.update(worksheet="maquinas", data=pd.concat([df_maq, n_maq], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
        st.dataframe(df_maq, use_container_width=True)
