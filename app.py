import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v4.5", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- COLUNAS PADRÃO (O Sheets deve seguir esta ordem) ---
COLUNAS_PRODUTOS = ["nome", "estoque", "validade", "preco"]
COLUNAS_VENDAS = ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"]
COLUNAS_MAQUINAS = ["nome_maquina", "tid", "pdv_vinculado", "taxa_debito", "taxa_credito"]
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
            else: st.error("Credenciais inválidas")
    st.stop()

# ==================== MENU LATERAL ====================
with st.sidebar:
    render_logo("30px")
    st.divider()
    menu = st.radio("Navegação", [
        "📊 Dashboard", 
        "🛍️ Venda (PDV)", 
        "💰 Lançamento de Custos", 
        "📦 Gestão de Estoque", 
        "🚚 Fornecedores",
        "📟 Máquinas & PDVs"
    ])
    if st.button("🔄 Sincronizar Google Sheets"):
        st.cache_data.clear()
        st.rerun()

# ==================== 1. DASHBOARD ====================
if menu == "📊 Dashboard":
    st.header("📊 Resumo de Operações")
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    bruto = pd.to_numeric(vendas['valor_bruto'], errors='coerce').sum()
    liquido = pd.to_numeric(vendas['valor_liquido'], errors='coerce').sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido (Pós Taxas)", f"R$ {liquido:,.2f}")
    c3.metric("Total de Vendas", len(vendas))
    
    st.subheader("Histórico Recente")
    st.dataframe(vendas.tail(10), use_container_width=True)

# ==================== 2. VENDA (PDV) ====================
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ Frente de Caixa")
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    maquinas = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    
    with st.form("venda_form"):
        p_sel = st.selectbox("📍 Unidade PDV", pdvs['nome'].tolist()) if not pdvs.empty else None
        maqs_pdv = maquinas[maquinas['pdv_vinculado'] == p_sel]
        maq_sel = st.selectbox("📟 Máquina de Cartão", maqs_pdv['nome_maquina'].tolist() if not maqs_pdv.empty else ["N/A"])
        prod_sel = st.selectbox("📦 Item", prods['nome'].tolist()) if not prods.empty else None
        qtd = st.number_input("Quantidade", min_value=1, value=1)
        forma = st.selectbox("Forma", ["Cartão Débito", "Cartão Crédito", "Pix", "Dinheiro"])
        
        if st.form_submit_button("FINALIZAR VENDA"):
            if not prods.empty and p_sel:
                idx_p = prods[prods['nome'] == prod_sel].index[0]
                preco_un = float(prods.at[idx_p, 'preco'])
                valor_bruto = preco_un * qtd
                
                # Cálculo de Taxa Automático
                taxa = 0.0
                if not maqs_pdv.empty and maq_sel != "N/A":
                    info_maq = maqs_pdv[maqs_pdv['nome_maquina'] == maq_sel].iloc[0]
                    taxa = float(info_maq['taxa_debito']) if "Débito" in forma else float(info_maq['taxa_credito']) if "Crédito" in forma else 0.0
                
                valor_liquido = valor_bruto * (1 - (taxa/100))
                
                nova_venda = pd.DataFrame([{
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "pdv": p_sel, "maquina": maq_sel, "produto": prod_sel,
                    "valor_bruto": valor_bruto, "valor_liquido": valor_liquido, "forma": forma
                }])
                
                # Baixa no Estoque
                prods.at[idx_p, 'estoque'] = int(pd.to_numeric(prods.at[idx_p, 'estoque'])) - qtd
                conn.update(worksheet="vendas", data=pd.concat([carregar_dados("vendas", COLUNAS_VENDAS), nova_venda], ignore_index=True))
                conn.update(worksheet="produtos", data=prods)
                st.cache_data.clear()
                st.success("Venda registrada!")
                st.rerun()

# ==================== 3. LANÇAMENTO DE CUSTOS & PRECIFICAÇÃO ====================
elif menu == "💰 Lançamento de Custos":
    st.header("💰 Entrada e Formação de Preço")
    df_f = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    df_c = carregar_dados("compras", COLUNAS_COMPRAS)

    with st.form("compra_form"):
        forn_sel = st.selectbox("Fornecedor", df_f['nome_fantasia'].tolist()) if not df_f.empty else []
        prod_sel = st.selectbox("Produto", df_p['nome'].tolist()) if not df_p.empty else []
        custo_un = st.number_input("Custo Unitário (R$)", min_value=0.01)
        margem = st.slider("Margem de Lucro (%)", 10, 200, 50)
        
        sugestao = custo_un * (1 + margem/100)
        st.info(f"💡 Sugestão de Venda: R$ {sugestao:.2f}")
        venda_final = st.number_input("Definir Preço de Venda Final", value=float(sugestao))
        qtd_entrada = st.number_input("Qtd Comprada", min_value=1)
        
        if st.form_submit_button("Registrar Entrada"):
            # Atualiza Tabela de Produtos (Estoque + Preço)
            idx = df_p[df_p['nome'] == prod_sel].index[0]
            df_p.at[idx, 'estoque'] = int(pd.to_numeric(df_p.at[idx, 'estoque'])) + qtd_entrada
            df_p.at[idx, 'preco'] = venda_final
            
            # Registro de Compra
            nova_compra = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y"), "fornecedor": forn_sel, "produto": prod_sel, "quantidade": qtd_entrada, "custo_unitario": custo_un, "custo_total": qtd_entrada * custo_un}])
            
            conn.update(worksheet="compras", data=pd.concat([df_c, nova_compra], ignore_index=True))
            conn.update(worksheet="produtos", data=df_p)
            st.cache_data.clear()
            st.success("Estoque e Preços atualizados!")
            st.rerun()

# ==================== 4. GESTÃO DE ESTOQUE ====================
elif menu == "📦 Gestão de Estoque":
    st.header("📦 Inventário de Produtos")
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    
    with st.expander("➕ Cadastrar Novo Item"):
        with st.form("novo_p"):
            n = st.text_input("Nome do Produto")
            e = st.number_input("Estoque Inicial", min_value=0)
            v = st.date_input("Validade")
            p = st.number_input("Preço de Venda", min_value=0.0)
            if st.form_submit_button("Salvar Novo Produto"):
                novo = pd.DataFrame([{"nome": n, "estoque": e, "validade": v.strftime("%d/%m/%Y"), "preco": p}])
                conn.update(worksheet="produtos", data=pd.concat([df_p, novo], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
    
    st.dataframe(df_p, use_container_width=True)

# ==================== 5. FORNECEDORES ====================
elif menu == "🚚 Fornecedores":
    st.header("🚚 Gestão de Fornecedores")
    df_f = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)
    with st.form("novo_f"):
        nf = st.text_input("Nome Fantasia")
        cnpj = st.text_input("CNPJ/CPF")
        if st.form_submit_button("Cadastrar Fornecedor"):
            conn.update(worksheet="fornecedores", data=pd.concat([df_f, pd.DataFrame([{"nome_fantasia": nf, "cnpj_cpf": cnpj}])], ignore_index=True))
            st.cache_data.clear()
            st.success("Fornecedor Salvo!")
            st.rerun()
    st.dataframe(df_f, use_container_width=True)

# ==================== 6. MÁQUINAS & PDVs ====================
elif menu == "📟 Máquinas & PDVs":
    st.header("📟 Configuração de Unidades e Taxas")
    c1, c2 = st.columns(2)
    df_pdv = carregar_dados("pontos", COLUNAS_PONTOS)
    df_maq = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    
    with c1:
        st.subheader("📍 Unidades (PDVs)")
        novo_pdv = st.text_input("Nome do Novo PDV")
        if st.button("Cadastrar PDV"):
            conn.update(worksheet="pontos", data=pd.concat([df_pdv, pd.DataFrame([{"nome": novo_pdv}])], ignore_index=True))
            st.cache_data.clear()
            st.rerun()
        st.table(df_pdv)

    with c2:
        st.subheader("📟 Máquinas e Taxas")
        with st.form("form_maq"):
            m_nome = st.text_input("Nome da Máquina")
            m_vinc = st.selectbox("Vincular ao PDV", df_pdv['nome'].tolist()) if not df_pdv.empty else []
            t_deb = st.number_input("Taxa Débito (%)", step=0.01)
            t_cre = st.number_input("Taxa Crédito (%)", step=0.01)
            if st.form_submit_button("Salvar Máquina"):
                nova_m = pd.DataFrame([{"nome_maquina": m_nome, "tid": "N/A", "pdv_vinculado": m_vinc, "taxa_debito": t_deb, "taxa_credito": t_cre}])
                conn.update(worksheet="maquinas", data=pd.concat([df_maq, nova_m], ignore_index=True))
                st.cache_data.clear()
                st.rerun()
        st.dataframe(df_maq, use_container_width=True)
