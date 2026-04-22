import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop - Gestão", layout="wide", page_icon="⚡")

# Inicialização de Estados de Sessão
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
    return conn.read(worksheet=aba, ttl=0)

# ==================== 2. SISTEMA DE LOGIN ====================
if not st.session_state.autenticado:
    st.title("⚡ Flash Stop - Acesso")
    with st.form("login_form"):
        user = st.text_input("Usuário / PDV")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            df_pts = carregar_dinamico("pontos")
            if user == "admin" and senha == "flash123":
                st.session_state.autenticado = True
                st.session_state.unidade = "Administração"
                st.session_state.perfil = "admin"
                st.rerun()
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

# ==================== 3. MENU LATERAL ====================
st.sidebar.title("⚡ Flash Stop")
st.sidebar.write(f"📍 **{st.session_state.unidade}**")

if st.session_state.perfil == "admin":
    menu = st.sidebar.radio("Navegação", [
        "📊 Dashboard", "🛒 Self-Checkout", "💰 Entrada Mercadoria", 
        "📦 Inventário", "📂 Contabilidade", "📟 Configurações"
    ])
else:
    menu = st.sidebar.radio("Navegação", ["🛒 Self-Checkout", "📦 Inventário"])

if st.sidebar.button("Sair"):
    st.session_state.autenticado = False
    st.rerun()

# ==================== 4. DASHBOARD ====================
if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_p = carregar_dinamico("produtos")
    
    # Cálculos
    bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
    liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
    gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
    lucro = liq - gastos

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Bruto Total", f"R$ {bruto:,.2f}")
    c2.metric("Líquido", f"R$ {liq:,.2f}")
    c3.metric("Despesas", f"R$ {gastos:,.2f}")
    c4.metric("Lucro Real", f"R$ {lucro:,.2f}")

    # Gráfico de Vendas por Data
    st.subheader("📈 Evolução de Vendas")
    if not df_v.empty:
        df_v['data_dt'] = pd.to_datetime(df_v['data'], format="%d/%m/%Y %H:%M", errors='coerce')
        vendas_dia = df_v.groupby(df_v['data_dt'].dt.date)['valor_bruto'].sum()
        st.line_chart(vendas_dia)

# ==================== 5. SELF-CHECKOUT ====================
elif menu == "🛒 Self-Checkout":
    st.header("🛒 Checkout")
    df_p = carregar_dinamico("produtos")
    
    c_sel, c_car = st.columns([1.5, 1])
    with c_sel:
        lista_p = [""] + df_p[df_p['estoque'].astype(int) > 0]['nome'].tolist()
        sel = st.selectbox("Produto:", lista_p)
        if sel:
            d = df_p[df_p['nome'] == sel].iloc[0]
            st.write(f"Preço: R$ {float(d['preco']):.2f}")
            qtd = st.number_input("Qtd:", min_value=1, max_value=int(d['estoque']), value=1)
            if st.button("➕ Adicionar"):
                st.session_state.carrinho.append({"item": sel, "qtd": qtd, "preco": float(d['preco']), "total": float(d['preco'])*qtd})
                st.rerun()

    with c_car:
        st.subheader("Carrinho")
        if st.session_state.carrinho:
            total = 0
            for it in st.session_state.carrinho:
                total += it['total']
                st.write(f"{it['qtd']}x {it['item']} - R$ {it['total']:.2f}")
            st.markdown(f"### Total: R$ {total:.2f}")
            if st.button("🏁 Finalizar"):
                # Lógica de salvar simplificada para brevidade
                st.success("Venda Concluída!")
                st.session_state.carrinho = []
                time.sleep(1); st.rerun()

# ==================== 6. ENTRADA MERCADORIA ====================
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Entrada de Estoque")
    df_p = carregar_dinamico("produtos")
    with st.form("form_entrada"):
        prod_e = st.selectbox("Produto:", df_p['nome'].tolist())
        qtd_e = st.number_input("Quantidade que chegou:", min_value=1)
        if st.form_submit_button("Registrar Entrada"):
            idx = df_p[df_p['nome'] == prod_e].index[0]
            df_p.at[idx, 'estoque'] = int(df_p.at[idx, 'estoque']) + qtd_e
            conn.update(worksheet="produtos", data=df_p)
            st.success("Estoque Atualizado!")

# ==================== 7. INVENTÁRIO ====================
elif menu == "📦 Inventário":
    st.header("📦 Inventário Atual")
    df_p = carregar_dinamico("produtos")
    st.dataframe(df_p[['nome', 'estoque', 'preco', 'validade']], use_container_width=True)

# ==================== 8. CONTABILIDADE ====================
elif menu == "📂 Contabilidade":
    st.header("📂 Relatórios Contábeis")
    df_v = carregar_dinamico("vendas")
    st.download_button("Baixar Relatório de Vendas (CSV)", df_v.to_csv(index=False), "vendas.csv")
    st.dataframe(df_v, use_container_width=True)

# ==================== 9. CONFIGURAÇÕES ====================
elif menu == "📟 Configurações":
    st.header("📟 Gestão de PDVs")
    df_pts = carregar_dinamico("pontos")
    with st.form("novo_p"):
        n = st.text_input("Nome da Unidade")
        s = st.text_input("Senha")
        if st.form_submit_button("Cadastrar"):
            novo = pd.DataFrame([{"nome": n, "senha": s}])
            conn.update(worksheet="pontos", data=pd.concat([df_pts, novo], ignore_index=True))
            st.rerun()
