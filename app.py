import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop - Gestão Inteligente", layout="wide", page_icon="⚡")

# Estilo para esconder o menu padrão do Streamlit (deixa mais profissional)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# Inicialização Robusta dos Estados de Sessão
if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
if 'unidade' not in st.session_state:
    st.session_state.unidade = ""
if 'perfil' not in st.session_state:
    st.session_state.perfil = ""

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dinamico(aba):
    # ttl=0 garante que ele busque dados novos da planilha toda vez
    return conn.read(worksheet=aba, ttl=0)

# ==================== 2. SISTEMA DE LOGIN ====================
if not st.session_state.autenticado:
    st.title("⚡ Flash Stop - Acesso")
    
    with st.container():
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.form("login_form"):
                user = st.text_input("Usuário / PDV")
                senha = st.text_input("Senha", type="password")
                btn_login = st.form_submit_button("Entrar", use_container_width=True)
                
                if btn_login:
                    df_pts = carregar_dinamico("pontos")
                    
                    # Login Admin
                    if user == "admin" and senha == "flash123":
                        st.session_state.autenticado = True
                        st.session_state.unidade = "Administração"
                        st.session_state.perfil = "admin"
                        st.rerun()
                    
                    # Login por Unidade (PDV)
                    elif user in df_pts['nome'].values:
                        senha_correta = str(df_pts[df_pts['nome'] == user]['senha'].values[0])
                        if senha == senha_correta:
                            st.session_state.autenticado = True
                            st.session_state.unidade = user
                            st.session_state.perfil = "pdv"
                            st.rerun()
                        else:
                            st.error("Senha incorreta.")
                    else:
                        st.error("Usuário não encontrado.")
    st.stop()

# ==================== 3. BARRA LATERAL (MENU) ====================
st.sidebar.title(f"⚡ Flash Stop")
st.sidebar.write(f"📍 **{st.session_state.unidade}**")
st.sidebar.divider()

if st.session_state.perfil == "admin":
    menu = st.sidebar.radio("Navegação", [
        "📊 Dashboard", "🛒 Self-Checkout", "💰 Entrada Mercadoria", 
        "📦 Inventário", "📂 Contabilidade", "📟 Configurações"
    ])
else:
    # Apenas o essencial para o tablet do condomínio
    menu = st.sidebar.radio("Navegação", ["🛒 Self-Checkout", "📦 Inventário"])

st.sidebar.divider()
if st.sidebar.button("Logoff"):
    st.session_state.autenticado = False
    st.session_state.carrinho = []
    st.rerun()

# ==================== 4. DASHBOARD (SOMENTE ADMIN) ====================
if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    try:
        df_v = carregar_dinamico("vendas")
        df_d = carregar_dinamico("despesas")
        df_p = carregar_dinamico("produtos")
        
        # Conversão segura de valores para numérico
        bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
        liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
        gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
        lucro = liq - gastos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Bruto Total", f"R$ {bruto:,.2f}")
        c2.metric("Líquido", f"R$ {liq:,.2f}")
        c3.metric("Despesas", f"R$ {gastos:,.2f}")
        c4.metric("Lucro Real", f"R$ {lucro:,.2f}", delta=f"{lucro/bruto*100:.1f}%" if bruto > 0 else None)

        st.divider()
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("🚨 Reposição Necessária")
            critico = df_p[df_p['estoque'].astype(int) <= df_p['estoque_minimo'].astype(int)]
            st.dataframe(critico[['nome', 'estoque', 'estoque_minimo']], hide_index=True, use_container_width=True)

        with col_b:
            st.subheader("📅 Próximos Vencimentos")
            vencendo = []
            hoje = datetime.now()
            for _, r in df_p.iterrows():
                try:
                    dt = datetime.strptime(str(r['validade']), "%d/%m/%Y")
                    if dt <= hoje + timedelta(days=15):
                        vencendo.append({"Produto": r['nome'], "Qtd": r['estoque'], "Data": r['validade']})
                except: continue
            if vencendo:
                st.dataframe(pd.DataFrame(vencendo), hide_index=True, use_container_width=True)
            else:
                st.success("Tudo dentro do prazo de validade!")
    except Exception as e:
        st.error(f"Erro ao carregar Dashboard: {e}")

# ==================== 5. SELF-CHECKOUT (MULTICARRINHO) ====================
elif menu == "🛒 Self-Checkout":
    st.header("🛒 Checkout Automático")
    try:
        df_p = carregar_dinamico("produtos")
        
        col_esq, col_dir = st.columns([1.5, 1])

        with col_esq:
            st.subheader("Selecione os Produtos")
            prods_ativos = df_p[df_p['estoque'].astype(int) > 0]
            lista_nomes = [""] + prods_ativos['nome'].tolist()
            
            sel = st.selectbox("Busque o produto:", lista_nomes, key="sel_prod")
            
            if sel:
                d = df_p[df_p['nome'] == sel].iloc[0]
                st.markdown(f"### Preço: R$ {float(d['preco']):.2f}")
                qtd = st.number_input("Quantidade:", min_value=1, max_value=int(d['estoque']), value=1)
                
                if st.button("➕ ADICIONAR AO CARRINHO", use_container_width=True):
                    st.session_state.carrinho.append({
                        "item": sel, "qtd": qtd, "preco": float(d['preco']), "total": float(d['preco']) * qtd
                    })
                    st.toast(f"{sel} adicionado!")
                    time.sleep(0.5)
                    st.rerun()

        with col_dir:
            st.subheader("🛍️ Seu Carrinho")
            # --- LINHA 168 (Onde estava o erro) ---
            if st.session_state.carrinho:
                v_total = 0
                for item in st.session_state.carrinho:
                    v_total += item['total']
                    st.write(f"**{item['qtd']}x** {item['item']} — R$ {item['total']:.2f}")
                
                st.markdown(f"## TOTAL: R$ {v_total:.2f}")
                
                if st.button("🗑️ Limpar Tudo"):
                    st.session_state.carrinho = []
                    st.rerun()

                st.divider()
                forma = st.radio("Pagamento na Maquininha:", ["Pix", "Débito", "Crédito"], horizontal=True)
                
                if st.button("✅ FINALIZAR E PAGAR", type="primary", use_container_width=True):
                    with st.spinner("Salvando venda..."):
                        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                        v_novas = []
                        for it in st.session_state.carrinho:
                            v_liq = it['total'] * 0.97
                            v_novas.append({
                                "data": agora, "pdv": st.session_state.unidade, "produto": it['item'],
                                "valor_bruto": it['total'], "valor_liquido": v_liq, "forma": forma
                            })
                            idx = df_p[df_p['nome'] == it['item']].index[0]
                            df_p.at[idx, 'estoque'] = int(df_p.at[idx, 'estoque']) - it['qtd']
                        
                        df_v_atual = carregar_dinamico("vendas")
                        conn.update(worksheet="vendas", data=pd.concat([df_v_atual, pd.DataFrame(v_novas)], ignore_index=True))
                        conn.update(worksheet="produtos", data=df_p)
                        
                        st.session_state.carrinho = []
                        st.success("Venda registrada!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
            else:
                st.info("Carrinho vazio. Selecione um item ao lado.")
    except Exception as e:
        st.error(f"Erro no Checkout: {e}")
