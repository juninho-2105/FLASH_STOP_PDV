import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop - Gestão", layout="wide", page_icon="⚡")

# CSS para botões ultra-compactos e ajustes de interface
st.markdown("""
    <style>
    /* Botões menores no checkout */
    .stButton>button {
        border-radius: 6px;
        padding: 2px 5px;
    }
    div[data-testid="column"] button {
        height: 32px !important;
        width: 32px !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }
    /* Esconder branding do Streamlit conforme solicitado */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
        # Cria DataFrame vazio se a aba não existir para evitar crash
        return pd.DataFrame()

# ==================== 2. SISTEMA DE LOGIN ====================
if not st.session_state.autenticado:
    st.title("⚡ Flash Stop - Acesso")
    with st.form("login_form"):
        user = st.text_input("Usuário / PDV")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
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
st.sidebar.title("⚡ Flash Stop")
st.sidebar.write(f"📍 **{st.session_state.unidade}**")

opcoes = ["📊 Dashboard", "🛒 Self-Checkout", "💰 Entrada Mercadoria", "📦 Inventário", "💸 Despesas", "📂 Contabilidade", "📟 Configurações"] if st.session_state.perfil == "admin" else ["🛒 Self-Checkout", "📦 Inventário"]
menu = st.sidebar.radio("Navegação", opcoes)

if st.sidebar.button("🚪 Sair"):
    st.session_state.autenticado = False
    st.rerun()

# ==================== 4. LÓGICA DAS TELAS ====================

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_p = carregar_dinamico("produtos")

    if not df_v.empty and not df_d.empty:
        bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
        liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
        gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
        lucro = liq - gastos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
        c2.metric("Líquido", f"R$ {liq:,.2f}")
        c3.metric("Despesas", f"R$ {gastos:,.2f}")
        c4.metric("Lucro Real", f"R$ {lucro:,.2f}")
    else:
        st.info("Dados insuficientes para o Dashboard.")

# --- SELF-CHECKOUT ---
elif menu == "🛒 Self-Checkout":
    st.header("🛒 Checkout")
    df_p = carregar_dinamico("produtos")
    
    if not df_p.empty:
        p_nome = st.selectbox("Bipar ou Selecionar Produto:", [""] + df_p['nome'].tolist())
        if p_nome:
            dados_p = df_p[df_p['nome'] == p_nome].iloc[0]
            preco_unit = float(dados_p['preco'])
            if st.button(f"Adicionar {p_nome} - R$ {preco_unit:.2f}", use_container_width=True):
                st.session_state.carrinho.append({"produto": p_nome, "preco": preco_unit})
                st.toast(f"{p_nome} adicionado!")
                time.sleep(0.3)
                st.rerun()

        st.divider()
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            resumo = df_cart.groupby('produto').agg({'preco': 'first', 'produto': 'count'}).rename(columns={'produto': 'qtd'}).reset_index()

            for idx, item in resumo.iterrows():
                col_txt, col_btns = st.columns([3, 1])
                with col_txt:
                    st.markdown(f"**{item['qtd']}x** {item['produto']} | R$ {item['preco']*item['qtd']:.2f}")
                with col_btns:
                    m1, m2 = st.columns(2)
                    if m1.button("—", key=f"sub_{idx}"):
                        for i, p in enumerate(st.session_state.carrinho):
                            if p['produto'] == item['produto']:
                                st.session_state.carrinho.pop(i)
                                break
                        st.rerun()
                    if m2.button("+", key=f"add_{idx}"):
                        st.session_state.carrinho.append({"produto": item['produto'], "preco": item['preco']})
                        st.rerun()

            total = df_cart['preco'].sum()
            st.subheader(f"Total: R$ {total:.2f}")
            forma_pgto = st.radio("Forma de Pagamento:", ["Pix", "Débito", "Crédito"], horizontal=True)
            
            c_f1, c_f2 = st.columns(2)
            if c_f1.button("❌ CANCELAR", use_container_width=True):
                st.session_state.carrinho = []
                st.rerun()
            if c_f2.button("🚀 PAGAR", use_container_width=True, type="primary"):
                st.success("Venda Finalizada!")
                st.session_state.carrinho = []
                time.sleep(1)
                st.rerun()
    else: st.warning("Nenhum produto cadastrado.")

# --- ENTRADA DE MERCADORIA ---
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Gestão de Estoque")
    df_p = carregar_dinamico("produtos")
    
    if not df_p.empty:
        prod_sel = st.selectbox("Selecione o Produto:", df_p['nome'].tolist())
        with st.form("entrada_estoque"):
            c1, c2, c3 = st.columns(3)
            qtd = c1.number_input("Quantidade Chegando:", min_value=1)
            custo = c2.number_input("Custo Unitário:", value=0.0)
            margem = c3.number_input("Margem (%)", value=40.0)
            validade = st.date_input("Data de Validade:", value=datetime.now() + timedelta(days=90))
            
            preco_sugerido = custo * (1 + (margem/100))
            preco_venda = st.number_input("Preço de Venda Final:", value=preco_sugerido)
            
            if st.form_submit_button("Atualizar Estoque"):
                idx = df_p[df_p['nome'] == prod_sel].index[0]
                df_p.at[idx, 'estoque'] = int(df_p.at[idx, 'estoque']) + qtd
                df_p.at[idx, 'preco'] = preco_venda
                df_p.at[idx, 'validade'] = validade.strftime("%d/%m/%Y")
                conn.update(worksheet="produtos", data=df_p)
                st.cache_data.clear()
                st.success("Dados salvos com sucesso!")
                time.sleep(1)
                st.rerun()

# --- INVENTÁRIO ---
elif menu == "📦 Inventário":
    st.header("📦 Gestão de Inventário")
    df_p = carregar_dinamico("produtos")
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("🗑️ Descontinuar Produto")
        p_excluir = st.selectbox("Selecione para remover:", [""] + df_p['nome'].tolist())
        if st.button("EXCLUIR PERMANENTEMENTE", type="secondary"):
            if p_excluir:
                df_p = df_p[df_p['nome'] != p_excluir]
                conn.update(worksheet="produtos", data=df_p)
                st.cache_data.clear()
                st.error(f"{p_excluir} removido.")
                time.sleep(1)
                st.rerun()

# --- CONFIGURAÇÕES ---
elif menu == "📟 Configurações":
    st.header("📟 Configurações do Sistema")
    df_pts = carregar_dinamico("pontos")
    
    tab1, tab2 = st.tabs(["📍 Pontos de Venda", "💳 Máquinas"])
    
    with tab1:
        st.dataframe(df_pts, use_container_width=True, hide_index=True)
        st.subheader("Encerrar Contrato / Excluir PDV")
        p_remover = st.selectbox("Selecione a Unidade:", [""] + df_pts['nome'].tolist())
        if st.button("⚠️ CONFIRMAR EXCLUSÃO", type="primary"):
            if p_remover:
                df_pts = df_pts[df_pts['nome'] != p_remover]
                conn.update(worksheet="pontos", data=df_pts)
                st.cache_data.clear()
                st.success("Unidade removida.")
                st.rerun()

    with tab2:
        st.info("Configuração de máquinas e taxas operacionais.")
        # Lógica de máquinas aqui conforme necessário...

else:
    st.info("Selecione uma opção válida.")
