import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time

# ==================== CONFIGURAÇÃO ====================
st.set_page_config(page_title="Flash Stop Pro v3.7", layout="wide", page_icon="⚡")

conn = st.connection("gsheets", type=GSheetsConnection)

# Função para renderizar o nome FLASH STOP estilizado
def render_flash_stop_logo(font_size="42px"):
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="font-family: 'Arial Black', sans-serif; font-size: {font_size}; color: #000000; letter-spacing: -2px; margin-bottom: 0;">
                FLASH <span style="color: #7CFC00; font-style: italic;">STOP</span>
            </h1>
            <p style="font-family: sans-serif; font-size: 12px; color: #666; margin-top: -10px; font-weight: bold;">
                CONVENIÊNCIA INTELIGENTE
            </p>
        </div>
    """, unsafe_allow_html=True)

def carregar_aba(nome_aba):
    try:
        df = conn.read(worksheet=nome_aba)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

# --- LOGIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    col_l1, col_l2, col_l3 = st.columns([1,2,1])
    with col_l2:
        render_flash_stop_logo(font_size="55px")
        st.subheader("Acesso ao Sistema")
        with st.form("login"):
            u = st.text_input("Usuário")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar"):
                if u == "admin" and s == "flash123":
                    st.session_state.autenticado = True
                    st.session_state.nome_usuario = u
                    st.rerun()
                else: st.error("Credenciais inválidas")
    st.stop()

# ==================== MENU LATERAL ====================
with st.sidebar:
    render_flash_stop_logo(font_size="30px")
    st.divider()
    menu = st.radio("Navegação", 
        ["📊 Dashboard & Alertas", "🛍️ Venda (PDV)", "📋 Relatórios Contábeis", "📦 Gestão de Estoque", "📍 Cadastrar PDV", "📟 Máquinas (Automação)"])

# ==================== 1. DASHBOARD & ALERTAS ====================
if menu == "📊 Dashboard & Alertas":
    st.header("📊 Painel de Controle")
    produtos = carregar_aba("produtos")
    
    if produtos.empty:
        st.info("💡 Cadastre produtos na aba 'Gestão de Estoque' para ver os alertas.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⚠️ Estoque Baixo")
            produtos['estoque'] = pd.to_numeric(produtos['estoque'], errors='coerce').fillna(0)
            baixo = produtos[produtos['estoque'] < 5]
            if not baixo.empty:
                for _, r in baixo.iterrows(): st.error(f"**Repor:** {r['nome']} ({int(r['estoque'])} un)")
            else: st.success("Estoque em dia!")

        with col2:
            st.subheader("📅 Validades")
            produtos['validade_dt'] = pd.to_datetime(produtos['validade'], dayfirst=True, errors='coerce')
            vencidos = produtos[produtos['validade_dt'] < datetime.now()]
            if not vencidos.empty:
                for _, r in vencidos.iterrows(): st.error(f"**VENCIDO:** {r['nome']} ({r['validade']})")
            else: st.success("Validades em dia!")

# ==================== 2. GESTÃO DE ESTOQUE ====================
elif menu == "📦 Gestão de Estoque":
    st.header("📦 Gestão de Estoque")
    df_estoque = carregar_aba("produtos")

    with st.expander("➕ Adicionar Novo Produto"):
        with st.form("novo_p"):
            n = st.text_input("Nome do Produto")
            e = st.number_input("Quantidade Inicial", min_value=0)
            v = st.text_input("Validade (DD/MM/AAAA)")
            p = st.number_input("Preço de Venda")
            if st.form_submit_button("Salvar Produto"):
                novo = pd.DataFrame([{"nome": n, "estoque": e, "validade": v, "preco": p}])
                conn.update(worksheet="produtos", data=pd.concat([df_estoque, novo], ignore_index=True))
                st.success("Produto cadastrado!")
                st.rerun()

    st.subheader("📋 Estoque Atual")
    st.dataframe(df_estoque, use_container_width=True)

    if not df_estoque.empty:
        with st.expander("🗑️ Excluir Produto"):
            prod_del = st.selectbox("Selecione para remover", df_estoque['nome'].tolist())
            if st.button("Confirmar Exclusão"):
                conn.update(worksheet="produtos", data=df_estoque[df_estoque['nome'] != prod_del])
                st.warning(f"{prod_del} removido.")
                st.rerun()

# ==================== 3. MÁQUINAS (COM VÍNCULO AO PDV) ====================
elif menu == "📟 Máquinas (Automação)":
    st.header("📟 Máquinas de Cartão")
    df_maqs = carregar_aba("maquinas")
    df_pdvs = carregar_aba("pontos")

    if df_pdvs.empty:
        st.warning("⚠️ Cadastre um PDV antes de adicionar máquinas.")
    else:
        with st.expander("➕ Vincular Nova Máquina"):
            with st.form("nova_m"):
                n = st.text_input("Nome da Máquina")
                tid = st.text_input("Serial (TID)")
                pdv_v = st.selectbox("Vincular ao PDV:", df_pdvs['nome'].tolist())
                if st.form_submit_button("Cadastrar e Vincular"):
                    nova = pd.DataFrame([{"nome": n, "tid": tid, "pdv_vinculado": pdv_v}])
                    conn.update(worksheet="maquinas", data=pd.concat([df_maqs, nova], ignore_index=True))
                    st.success(f"Máquina {n} ligada ao {pdv_v}!")
                    st.rerun()

    st.subheader("📋 Máquinas Ativas")
    st.dataframe(df_maqs, use_container_width=True)

    if not df_maqs.empty:
        with st.expander("🗑️ Remover Máquina"):
            maq_del = st.selectbox("Remover Máquina", df_maqs['nome'].tolist())
            if st.button("Confirmar Remoção"):
                conn.update(worksheet="maquinas", data=df_maqs[df_maqs['nome'] != maq_del])
                st.warning("Máquina removida.")
                st.rerun()

# ==================== 4. VENDA PDV ====================
elif menu == "🛍️ Venda (PDV)":
    st.header("🛍️ Frente de Caixa")
    pdvs = carregar_aba("pontos")
    prods = carregar_aba("produtos")
    maqs = carregar_aba("maquinas")
    
    if pdvs.empty or prods.empty:
        st.warning("⚠️ Configure PDVs e Estoque antes de vender!")
    else:
        with st.form("venda_f"):
            pdv_sel = st.selectbox("📍 Selecione o PDV", pdvs['nome'].tolist())
            maqs_pdv = maqs[maqs['pdv_vinculado'] == pdv_sel]['nome'].tolist()
            maq_sel = st.selectbox("📟 Máquina de Cartão", maqs_pdv if maqs_pdv else ["Nenhuma máquina vinculada"])
            prod_sel = st.selectbox("📦 Item", prods['nome'].tolist())
            qtd = st.number_input("Quantidade", min_value=1, value=1)
            forma = st.selectbox("Forma de Pagto", ["Cartão", "Pix", "Dinheiro"])
            
            if st.form_submit_button("FINALIZAR VENDA"):
                idx = prods[prods['nome'] == prod_sel].index[0]
                if int(prods.at[idx, 'estoque']) >= qtd:
                    v_df = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": pdv_sel, "maquina": maq_sel, "produto": prod_sel, "valor": float(prods.at[idx, 'preco']) * qtd, "forma": forma}])
                    conn.update(worksheet="vendas", data=pd.concat([carregar_aba("vendas"), v_df], ignore_index=True))
                    prods.at[idx, 'estoque'] = int(prods.at[idx, 'estoque']) - qtd
                    conn.update(worksheet="produtos", data=prods)
                    st.success("Venda processada!")
                    st.balloons()
                else: st.error("Estoque insuficiente!")

# ==================== 5. RELATÓRIOS E PDV ====================
elif menu == "📋 Relatórios Contábeis":
    st.header("📋 Relatórios")
    vendas = carregar_aba("vendas")
    if not vendas.empty:
        pdv_f = st.selectbox("Filtrar Unidade", ["Todos"] + vendas['pdv'].unique().tolist())
        df = vendas if pdv_f == "Todos" else vendas[vendas['pdv'] == pdv_f]
        st.metric("Total Bruto", f"R$ {pd.to_numeric(df['valor']).sum():.2f}")
        st.dataframe(df)
    else: st.info("Sem vendas.")

elif menu == "📍 Cadastrar PDV":
    st.header("📍 Gestão de Pontos")
    df_pdvs = carregar_aba("pontos")
    with st.form("p"):
        n = st.text_input("Nome do PDV")
        if st.form_submit_button("Salvar PDV"):
            conn.update(worksheet="pontos", data=pd.concat([df_pdvs, pd.DataFrame([{"nome": n}])], ignore_index=True))
            st.success("Cadastrado!")
            st.rerun()
    st.dataframe(df_pdvs)
