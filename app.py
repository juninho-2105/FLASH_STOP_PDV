import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection

# ==================== 1. CONFIGURAÇÃO DA PÁGINA & CSS ====================
st.set_page_config(page_title="Flash Stop - PDV", layout="wide", initial_sidebar_state="expanded")

# CSS para esconder a barra superior e ajustar o layout profissional
st.markdown("""
    <style>
    /* Esconder barra superior (Share, GitHub, etc) */
    header[data-testid="stHeader"] { visibility: hidden; height: 0%; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Ajuste de Margens e Largura Total */
    .block-container { 
        padding-top: 1rem !important; 
        max-width: 100% !important; 
        padding-left: 2rem !important; 
        padding-right: 2rem !important; 
    }
    
    /* Título Centralizado */
    .main-title {
        text-align: center; color: #2e7d32; font-size: 32px; 
        font-weight: bold; margin-bottom: 20px; width: 100%;
    }

    /* Cards de Produto no Carrinho */
    .product-card {
        background-color: #ffffff; border-left: 6px solid #2e7d32;
        padding: 15px; border-radius: 10px; box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }

    /* Botões de Ação Grandes (Mobile First) */
    .stButton button {
        width: 100% !important; max-width: 450px; display: block;
        margin: 10px auto !important; height: 3.5rem;
        font-size: 18px; font-weight: bold; border-radius: 12px;
    }
    
    /* Centralizar Radios de Pagamento */
    div[role="radiogroup"] { justify-content: center !important; gap: 20px; }
    </style>
""", unsafe_allow_html=True)

# ==================== 2. CONEXÃO E FUNÇÕES (EVITA NAMEERROR) ====================
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=60)
def carregar_dinamico(aba):
    try:
        return conn.read(worksheet=aba)
    except Exception as e:
        return pd.DataFrame()

# Inicializar carrinho se não existir
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []

# ==================== 3. NAVEGAÇÃO LATERAL ====================
with st.sidebar:
    st.title("⚡ Flash Stop")
    menu = st.radio("Navegação", ["🛒 Self-Checkout", "📟 Configurações", "📊 Dashboard"])
    st.divider()
    if st.button("Sair / Trocar Usuário"):
        st.session_state.clear()
        st.rerun()

# ==================== 4. MENU: SELF-CHECKOUT ====================
if menu == "🛒 Self-Checkout":
    st.markdown('<div class="main-title">FLASH STOP</div>', unsafe_allow_html=True)

    df_p = carregar_dinamico("produtos")
    
    # Busca e Seleção (Para Bip ou Manual)
    c_input, c_add = st.columns([3, 1])
    with c_input:
        p_selecionado = st.selectbox(
            "Bipe ou Selecione:",
            options=[""] + df_p['nome'].tolist() if not df_p.empty else [""],
            format_func=lambda x: "Aguardando bip ou seleção..." if x == "" else x,
            label_visibility="collapsed"
        )

    with c_add:
        if st.button("➕ ADD", type="primary", key="add_p"):
            if p_selecionado:
                dados_p = df_p[df_p['nome'] == p_selecionado].iloc[0]
                preco_v = float(dados_p['preco_venda'] if 'preco_venda' in df_p.columns else dados_p['preco'])
                st.session_state.carrinho.append({
                    "id": time.time(), 
                    "produto": p_selecionado, 
                    "preco": preco_v
                })
                st.rerun()

    st.divider()

    # Listagem do Carrinho
    if st.session_state.carrinho:
        df_cart = pd.DataFrame(st.session_state.carrinho)
        resumo = df_cart.groupby('produto').agg({'preco': 'first', 'id': 'count'}).rename(columns={'id': 'qtd'}).reset_index()

        for idx, item in resumo.iterrows():
            st.markdown(f"""
                <div class="product-card">
                    <div style='font-size: 18px;'><b>{item['produto']}</b></div>
                    <div style='color: #555;'>{item['qtd']}x R$ {item['preco']:.2f} = <b>R$ {item['preco']*item['qtd']:.2f}</b></div>
                </div>
            """, unsafe_allow_html=True)
            
            q1, q2, q3, qe = st.columns([1, 1, 1, 4])
            if q1.button("—", key=f"min_{idx}"):
                for i, p in enumerate(st.session_state.carrinho):
                    if p['produto'] == item['produto']:
                        st.session_state.carrinho.pop(i)
                        break
                st.rerun()
            q2.markdown(f"<p style='text-align:center; font-size:20px; font-weight:bold;'>{item['qtd']}</p>", unsafe_allow_html=True)
            if q3.button("＋", key=f"plus_{idx}"):
                st.session_state.carrinho.append({"id": time.time(), "produto": item['produto'], "preco": item['preco']})
                st.rerun()

        # Rodapé de Pagamento
        st.divider()
        total_geral = df_cart['preco'].sum()
        st.markdown(f"<h1 style='text-align:center;'>Total: R$ {total_geral:.2f}</h1>", unsafe_allow_html=True)
        
        st.markdown("<p style='text-align:center;'>Forma de Pagamento:</p>", unsafe_allow_html=True)
        forma = st.radio("Pgto", ["Pix", "Débito", "Crédito"], horizontal=True, label_visibility="collapsed")
        
        if st.button("🚀 FINALIZAR COMPRA", type="primary"):
            st.balloons()
            st.success(f"Venda confirmada no {forma}!")
            st.session_state.carrinho = []
            time.sleep(2)
            st.rerun()
            
        if st.button("❌ CANCELAR"):
            st.session_state.carrinho = []
            st.rerun()
    else:
        st.info("🛒 Carrinho vazio. Comece a bipar os produtos!")

# ==================== 5. MENU: CONFIGURAÇÕES (PDVs) ====================
elif menu == "📟 Configurações":
    st.header("📟 Gestão de Unidades")
    df_pts = carregar_dinamico("pontos")
    
    with st.form("novo_pdv"):
        n = st.text_input("Nome da Unidade")
        s = st.text_input("Senha")
        if st.form_submit_button("Cadastrar"):
            if n and s:
                novo = pd.DataFrame([{"nome": n, "senha": s}])
                conn.update(worksheet="pontos", data=pd.concat([df_pts, novo]))
                st.cache_data.clear()
                st.rerun()

    st.write("### Unidades Ativas")
    for idx, row in df_pts.iterrows():
        c1, c2, c3 = st.columns([3, 2, 1])
