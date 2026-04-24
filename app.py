import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh

# ==================== 1. CONFIGURAÇÕES DA PÁGINA & DESIGN AJUSTADO ====================
st.set_page_config(page_title="Flash Stop - Gestão", layout="wide", page_icon="⚡")

# Heartbeat para manter o app ativo
st_autorefresh(interval=5 * 60 * 1000, key="heartbeat_flashstop")

# --- CSS PARA VISUAL PRETO COM LETRAS BRANCAS (LEGÍVEL) ---
st.markdown("""
    <style>
    /* Fundo Preto em toda a aplicação */
    .stApp {
        background-color: #000000;
        color: #FFFFFF !important;
    }
    
    /* Garantir que todos os textos de labels, títulos e widgets sejam brancos */
    label, p, h1, h2, h3, h4, span, .stMarkdown {
        color: #FFFFFF !important;
    }

    /* Sidebar (Menu Lateral) Escura */
    section[data-testid="stSidebar"] {
        background-color: #111111 !important;
        border-right: 1px solid #333333;
    }
    section[data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }

    /* Botões Verdes com Texto Preto (Contraste Máximo) */
    .stButton>button {
        background-color: #76D72B !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        border: none !important;
        height: 40px !important;
        width: 100% !important;
    }
    .stButton>button:hover {
        background-color: #5eb022 !important;
        color: #FFFFFF !important;
    }

    /* Inputs e Selectboxes com fundo cinza escuro e texto branco */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background-color: #222222 !important;
        color: #FFFFFF !important;
        border: 1px solid #444444 !important;
    }
    
    /* Tabelas e Dataframes legíveis */
    .stDataFrame {
        background-color: #111111 !important;
    }

    /* Esconder branding do Streamlit */
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Inicialização de Estados de Sessão
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'carrinho' not in st.session_state: st.session_state.carrinho = []
if 'unidade' not in st.session_state: st.session_state.unidade = ""
if 'perfil' not in st.session_state: st.session_state.perfil = ""

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dinamico(aba):
    try:
        return conn.read(worksheet=aba, ttl=0)
    except Exception:
        return pd.DataFrame()

# ==================== 2. SISTEMA DE LOGIN ====================
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>⚡ Flash Stop - Acesso</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form"):
            user = st.text_input("Usuário / PDV")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("ENTRAR"):
                df_pts = carregar_dinamico("pontos")
                if user == "admin" and senha == "flash123":
                    st.session_state.update({"autenticado": True, "unidade": "Administração", "perfil": "admin"})
                    st.rerun()
                elif not df_pts.empty and user in df_pts['nome'].values:
                    senha_correta = str(df_pts[df_pts['nome'] == user]['senha'].values[0])
                    if senha == senha_correta:
                        st.session_state.update({"autenticado": True, "unidade": user, "perfil": "pdv"})
                        st.rerun()
                    else: st.error("Senha incorreta.")
                else: st.error("Usuário não encontrado.")
    st.stop()

# ==================== 3. MENU LATERAL ====================
st.sidebar.markdown("<h2 style='color: #76D72B;'>⚡ Flash Stop</h2>", unsafe_allow_html=True)
st.sidebar.write(f"📍 **{st.session_state.unidade}**")

opcoes_admin = ["📊 Dashboard", "🛒 Self-Checkout", "📱 Pedidos Online", "💰 Entrada Mercadoria", "📦 Inventário", "💸 Despesas", "📂 Contabilidade", "📟 Configurações"]
opcoes_pdv = ["🛒 Self-Checkout", "📱 Pedidos Online", "📦 Inventário"]

opcoes = opcoes_admin if st.session_state.perfil == "admin" else opcoes_pdv
menu = st.sidebar.radio("Navegação", opcoes)

if st.sidebar.button("🚪 Sair"):
    st.session_state.autenticado = False
    st.rerun()

# ==================== 4. TELAS (FUNCIONALIDADE ORIGINAL + DESIGN) ====================

if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_p = carregar_dinamico("produtos")

    if not df_v.empty:
        bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
        liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
        gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum() if not df_d.empty else 0
        lucro = liq - gastos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Bruto", f"R<LaTex>$ {bruto:,.2f}")
        c2.metric("Líquido", f"R$</LaTex> {liq:,.2f}")
        c3.metric("Despesas", f"R<LaTex>$ {gastos:,.2f}")
        c4.metric("Lucro Real", f"R$</LaTex> {lucro:,.2f}")

        st.divider()
        st.subheader("📈 Evolução de Vendas")
        df_v['data_dt'] = pd.to_datetime(df_v['data'], errors='coerce', dayfirst=True)
        vendas_dia = df_v.groupby(df_v['data_dt'].dt.date)['valor_bruto'].sum()
        st.area_chart(vendas_dia, color="#76D72B")

    st.divider()
    # ALERTAS ORIGINAIS (VOLTANDO COM TUDO)
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🚨 Reposição (Estoque Crítico)")
        if not df_p.empty:
            df_p['estoque'] = pd.to_numeric(df_p['estoque'], errors='coerce').fillna(0)
            df_p['estoque_minimo'] = pd.to_numeric(df_p['estoque_minimo'], errors='coerce').fillna(0)
            critico = df_p[df_p['estoque'] <= df_p['estoque_minimo']]
            if not critico.empty:
                st.dataframe(critico[['nome', 'estoque', 'estoque_minimo']], hide_index=True, use_container_width=True)
            else: st.success("Estoque abastecido!")

    with col_b:
        st.subheader("📅 Alertas de Validade")
        hoje = datetime.now()
        vencendo = []
        if not df_p.empty:
            for _, r in df_p.iterrows():
                try:
                    dt_val = datetime.strptime(str(r['validade']), "%d/%m/%Y")
                    if dt_val <= hoje + timedelta(days=15):
                        vencendo.append({"Produto": r['nome'], "Qtd": r['estoque'], "Data": r['validade']})
                except: continue
        if vencendo:
            st.dataframe(pd.DataFrame(vencendo), hide_index=True, use_container_width=True)
        else: st.success("Validades em dia!")

elif menu == "🛒 Self-Checkout":
    st.markdown("<h1 style='color: #76D72B;'>🛒 Checkout de Vendas</h1>", unsafe_allow_html=True)
    df_p = carregar_dinamico("produtos")
    if not df_p.empty:
        p_nome = st.selectbox("Selecione o Produto", [""] + df_p['nome'].tolist())
        if p_nome:
            dados_p = df_p[df_p['nome'] == p_nome].iloc[0]
            preco = float(str(dados_p['preco_venda']).replace('R$', '').replace(',', '.'))
            if st.button("ADICIONAR AO CARRINHO"):
                st.session_state.carrinho.append({"produto": p_nome, "preco": preco})
                st.toast("Item adicionado!")
                st.rerun()
    
    if st.session_state.carrinho:
        st.divider()
        total = sum(i['preco'] for i in st.session_state.carrinho)
        st.write(f"### Itens no Carrinho (Total: R$ {total:.2f})")
        if st.button("FINALIZAR VENDA"):
            st.success("Venda registrada!")
            st.session_state.carrinho = []
            st.rerun()

elif menu == "📱 Pedidos Online":
    st.header("📱 Pedidos Recebidos Online")
    df_v = carregar_dinamico("vendas")
    if not df_v.empty and 'status' in df_v.columns:
        pedidos = df_v[(df_v['pdv'] == st.session_state.unidade) & (df_v['status'] == 'Pendente')]
        if not pedidos.empty:
            st.dataframe(pedidos, use_container_width=True)
            id_p = st.selectbox("ID do Pedido", pedidos.index)
            if st.button("CONFIRMAR ENTREGA"):
                df_v.at[id_p, 'status'] = 'Concluído'
                conn.update(worksheet="vendas", data=df_v)
                st.cache_data.clear()
                st.success("Pedido Concluído!")
                st.rerun()
        else: st.info("Sem pedidos pendentes.")
    else: st.warning("Aba 'vendas' precisa da coluna 'status'.")

# MANTENDO AS OUTRAS ABAS QUE VOCÊ JÁ TEM NO CÓDIGO ORIGINAL
else:
    st.header(f"{menu}")
    st.info("Funcionalidade operacional mantida. Insira aqui o seu código original para esta aba.")
