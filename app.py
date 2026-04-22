import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v5.5", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# --- DEFINIÇÃO DE COLUNAS ---
COLUNAS_PRODUTOS = ["nome", "estoque", "validade", "preco", "estoque_minimo"]
COLUNAS_VENDAS = ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"]
COLUNAS_DESPESAS = ["pdv", "descricao", "valor", "vencimento"]
COLUNAS_MAQUINAS = ["nome_maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"]
COLUNAS_PONTOS = ["nome"]
COLUNAS_FORNECEDORES = ["nome_fantasia", "cnpj_cpf"]

# ==================== FUNÇÕES MOTORAS ====================
@st.cache_data(ttl=60)
def carregar_dados(nome_aba, colunas):
    try:
        df = conn.read(worksheet=nome_aba, ttl=0)
        df = df.dropna(how='all')
        if df.empty: return pd.DataFrame(columns=colunas)
        # Tratamento numérico para evitar erros de cálculo
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
    st.divider()
    menu = st.radio("Navegação Principal", [
        "📊 Dashboard & Alertas",
        "💰 Entrada de Mercadoria (Custos)",
        "📈 Financeiro (Despesas Fixas)",
        "🛍️ Frente de Caixa (PDV)",
        "📦 Inventário (Estoque)",
        "🚚 Fornecedores",
        "📟 Configurações (Taxas/PDVs)"
    ])
    if st.button("🔄 Sincronizar Agora"):
        st.cache_data.clear()
        st.rerun()

# ==================== 1. DASHBOARD & ALERTAS ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Resultado Operacional")
    vendas = carregar_dados("vendas", COLUNAS_VENDAS)
    despesas = carregar_dados("despesas", COLUNAS_DESPESAS)
    prods = carregar_dados("produtos", COLUNAS_PRODUTOS)

    # Cards de Métricas
    bruto = vendas['valor_bruto'].sum()
    liq_vendas = vendas['valor_liquido'].sum()
    fixo = despesas['valor'].sum()
    cashback = bruto * 0.02
    lucro_real = liq_vendas - fixo

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Bruto Total", f"R$ {bruto:,.2f}")
    m2.metric("Cashback (2%)", f"R$ {cashback:,.2f}")
    m3.metric("Despesas Fixas", f"R$ {fixo:,.2f}", delta_color="inverse")
    m4.metric("Lucro Real", f"R$ {lucro_real:,.2f}")

    # Alertas
    st.divider()
    c_alt1, c_alt2 = st.columns(2)
    with c_alt1:
        baixo = prods[prods['estoque'] <= prods['estoque_minimo']]
        if not baixo.empty:
            st.error(f"🚨 Estoque Baixo ({len(baixo)} itens)")
            st.dataframe(baixo[['nome', 'estoque']], use_container_width=True, hide_index=True)
    with c_alt2:
        st.success("✅ Sistema Operacional")

# ==================== 2. ENTRADA DE MERCADORIA (CUSTOS + ESTOQUE) ====================
elif menu == "💰 Entrada de Mercadoria (Custos)":
    st.header("💰 Entrada e Precificação Automática")
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    df_f = carregar_dados("fornecedores", COLUNAS_FORNECEDORES)

    with st.form("entrada_unificada"):
        col1, col2 = st.columns(2)
        with col1:
            selecao = st.selectbox("Produto", ["+ NOVO PRODUTO"] + df_p['nome'].tolist())
            nome_p = st.text_input("Nome") if selecao == "+ NOVO PRODUTO" else selecao
            qtd_in = st.number_input("Qtd Entrada", min_value=1)
            val_in = st.date_input("Validade")
        with col2:
            custo_un = st.number_input("Custo Unitário (R$)", min_value=0.0)
            margem = st.slider("Margem (%)", 10, 300, 50)
            sugestao = custo_un * (1 + margem/100)
            venda_in = st.number_input("Venda Final (R$)", value=float(sugestao))
            min_in = st.number_input("Estoque Mínimo", value=5)

        if st.form_submit_button("SALVAR E ATUALIZAR ESTOQUE"):
            if not nome_p: st.error("Nome obrigatório")
            else:
                if selecao in df_p['nome'].tolist():
                    idx = df_p[df_p['nome'] == selecao].index[0]
                    df_p.at[idx, 'estoque'] += qtd_in
                    df_p.at[idx, 'preco'] = venda_in
                    df_p.at[idx, 'validade'] = val_in.strftime("%d/%m/%Y")
                    df_p.at[idx, 'estoque_minimo'] = min_in
                else:
                    novo = pd.DataFrame([{"nome": nome_p, "estoque": qtd_in, "validade": val_in.strftime("%d/%m/%Y"), "preco": venda_in, "estoque_minimo": min_in}])
                    df_p = pd.concat([df_p, novo], ignore_index=True)
                
                conn.update(worksheet="produtos", data=df_p)
                st.cache_data.clear()
                st.success("Estoque Atualizado!")
                st.rerun()

# ==================== 3. FINANCEIRO (DESPESAS) ====================
elif menu == "📈 Financeiro (Despesas Fixas)":
    st.header("📈 Despesas Fixas (Mensais)")
    df_pdvs = carregar_dados("pontos", COLUNAS_PONTOS)
    df_desp = carregar_dados("despesas", COLUNAS_DESPESAS)
    with st.form("f_desp"):
        p_v = st.selectbox("PDV", df_pdvs['nome'].tolist()) if not df_pdvs.empty else ["-"]
        d_v = st.text_input("Descrição")
        v_v = st.number_input("Valor", min_value=0.0)
        if st.form_submit_button("Lançar"):
            nova = pd.DataFrame([{"pdv": p_v, "descricao": d_v, "valor": v_v, "vencimento": datetime.now().strftime("%d/%m/%Y")}])
            conn.update(worksheet="despesas", data=pd.concat([df_desp, nova], ignore_index=True))
            st.cache_data.clear()
            st.rerun()
    st.dataframe(df_desp, use_container_width=True)

# ==================== 4. FRENTE DE CAIXA (VENDA COM TAXA PIX) ====================
elif menu == "🛍️ Frente de Caixa (PDV)":
    st.header("🛍️ Registro de Venda")
    df_p = carregar_dados("produtos", COLUNAS_PRODUTOS)
    df_m = carregar_dados("maquinas", COLUNAS_MAQUINAS)
    df_pts = carregar_dados("pontos", COLUNAS_PONTOS)

    with st.form("pdv"):
        f_pdv = st.selectbox("PDV", df_pts['nome'].tolist()) if not df_pts.empty else ["-"]
        f_maq = st.selectbox("Máquina", df_m[df_m['pdv_vinculado'] == f_pdv]['nome_maquina'].tolist() if not df_m.empty else ["Dinheiro"])
        f_prod = st.selectbox("Produto", df_p['nome'].tolist()) if not df_p.empty else ["-"]
        f_qtd = st.number_input("Qtd", min_value=1)
        f_forma = st.selectbox("Forma", ["Débito", "Crédito", "Pix", "Dinheiro"])

        if st.form_submit_button("FINALIZAR VENDA"):
            idx = df_p[df_p['nome'] == f_prod].index[0]
            bruto = df_p.at[idx, 'preco'] * f_qtd
            
            # Cálculo de Taxa (Incluindo Pix)
            taxa = 0.0
            if f_maq != "Dinheiro":
                m_info = df_m[df_m['nome_maquina'] == f_maq].iloc[0]
                if f_forma == "Débito": taxa = m_info['taxa_debito']
                elif f_forma == "Crédito": taxa = m_info['taxa_credito']
                elif f_forma == "Pix": taxa = m_info['taxa_pix']
            
            liq = bruto * (1 - (tax
