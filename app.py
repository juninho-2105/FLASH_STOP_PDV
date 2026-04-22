import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v4.5", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- COLUNAS PADRÃO ---
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

# ==================== LOGIN (Simplificado) ====================
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
    menu = st.radio("Navegação", [
        "📊 Dashboard", "🛍️ Venda (PDV)", "💰 Lançamento de Custos", 
        "📦 Estoque", "📟 Máquinas & PDVs", "🚚 Fornecedores"
    ])
    if st.button("🔄 Sincronizar"):
        st.cache_data.clear()
        st.rerun()

# ==================== 1. DASHBOARD ====================
if menu == "📊 Dashboard":
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    c1, c2 = st.columns(2)
    bruto = pd.to_numeric(vendas['valor_bruto'], errors='coerce').sum()
    liquido = pd.to_numeric(vendas['valor_liquido'], errors='coerce').sum()
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Faturamento Líquido (Pós Taxas)", f"R$ {liquido:,.2f}")
    st.dataframe(vendas, use_container_width=True)

# ==================== 2. VENDA (PDV) AUTOMATIZADA ====================
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ Frente de Caixa Inteligente")
    pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)
    maquinas = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    
    with st.form("venda_form"):
        p_sel = st.selectbox("📍 PDV", pdvs['nome'].tolist()) if not pdvs.empty else None
        maqs_disponiveis = maquinas[maquinas['pdv_vinculado'] == p_sel]
        maq_sel = st.selectbox("📟 Máquina", maqs_disponiveis['nome_maquina'].tolist() if not maqs_disponiveis.empty else ["N/A"])
        
        prod_sel = st.selectbox("📦 Produto", prods['nome'].tolist()) if not prods.empty else None
        qtd = st.number_input("Qtd", min_value=1, value=1)
        forma = st.selectbox("Pagamento", ["Cartão Débito", "Cartão Crédito", "Pix", "Dinheiro"])
        
        if st.form_submit_button("FINALIZAR VENDA"):
            idx_p = prods[prods['nome'] == prod_sel].index[0]
            preco_un = float(prods.at[idx_p, 'preco'])
            bruto = preco_un * qtd
            
            # Lógica Automática de Taxas
            taxa = 0.0
            if not maqs_disponiveis.empty and maq_sel != "N/A":
                info_maq = maqs_disponiveis[maqs_disponiveis['nome_maquina'] == maq_sel].iloc[0]
                if "Débito" in forma: taxa = float(info_maq['taxa_debito'])
                elif "Crédito" in forma: taxa = float(info_maq['taxa_credito'])
            
            liquido = bruto * (1 - (taxa/100))
            
            nova_venda = pd.DataFrame([{
                "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "pdv": p_sel, "maquina": maq_sel, "produto": prod_sel,
                "valor_bruto": bruto, "valor_liquido": liquido, "forma": forma
            }])
            
            # Atualiza estoque e salva
            prods.at[idx_p, 'estoque'] = int(pd.to_numeric(prods.at[idx_p, 'estoque'])) - qtd
            conn.update(worksheet="vendas", data=pd.concat([carregar_dados("vendas", COLUNAS_VENDAS), nova_venda], ignore_index=True))
            conn.update(worksheet="produtos", data=prods)
            st.cache_data.clear()
            st.success(f"Venda concluída! Líquido: R$ {liquido:.2f}")
            st.rerun()

# ==================== 3. CUSTOS COM PRECIFICAÇÃO ====================
elif menu == "💰 Lançamento de Custos":
    st.header("💰 Compra e Precificação")
    df_f = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    
    with st.form("custo_p"):
        prod_c = st.selectbox("Produto", df_p['nome'].tolist()) if not df_p.empty else []
        custo_un = st.number_input("Preço de Custo Unitário", min_value=0.01)
        margem = st.slider("Margem de Lucro Desejada (%)", 10, 200, 50)
        
        preco_sug = custo_un * (1 + margem/100)
        st.write(f"💡 Sugestão de Venda: **R$ {preco_sug:.2f}**")
        preco_final = st.number_input("Preço de Venda Final", value=float(preco_sug))
        qtd_c = st.number_input("Qtd Comprada", min_value=1)
        
        if st.form_submit_button("Gravar Compra e Atualizar Preço de Venda"):
            idx = df_p[df_p['nome'] == prod_c].index[0]
            df_p.at[idx, 'estoque'] = int(pd.to_numeric(df_p.at[idx, 'estoque'])) + qtd_c
            df_p.at[idx, 'preco'] = preco_final
            
            # Salva no Sheets
            conn.update(worksheet="produtos", data=df_p)
            st.cache_data.clear()
            st.success("Estoque e Preço de Venda atualizados!")
            st.rerun()

# ==================== 4. MÁQUINAS COM TAXAS ====================
elif menu == "📟 Máquinas & PDVs":
    st.header("📟 Configuração de Terminais")
    col1, col2 = st.columns(2)
    df_pdv = carregar_dados("pontos", COLUNAS_PONTOS)
    
    with col1:
        st.subheader("Nova Máquina")
        with st.form("maq_taxas"):
            nome_m = st.text_input("Nome da Máquina")
            vinc = st.selectbox("PDV", df_pdv['nome'].tolist()) if not df_pdv.empty else []
            t_deb = st.number_input("Taxa Débito (%)", min_value=0.0, step=0.01)
            t_cre = st.number_input("Taxa Crédito (%)", min_value=0.0, step=0.01)
            if st.form_submit_button("Salvar Máquina"):
                df_m = carregar_dados("maquinas", COLUNAS_MAQUINAS)
                nova = pd.DataFrame([{"nome_maquina": nome_m, "pdv_vinculado": vinc, "taxa_debito": t_deb, "taxa_credito": t_cre}])
                conn.update(worksheet="maquinas", data=pd.concat([df_m, nova], ignore_index=True))
                st.cache_data.clear()
                st.rerun()

    st.dataframe(carregar_dados("maquinas", COLUNAS_MAQUINAS), use_container_width=True)

# ... (Módulos de Estoque e Fornecedores permanecem os mesmos)
