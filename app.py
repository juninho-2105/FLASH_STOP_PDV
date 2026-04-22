import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES E CONEXÃO ====================
st.set_page_config(page_title="Flash Stop - Gestão Total", layout="wide", page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)

COLS = {
    "produtos": ["nome", "estoque", "validade", "preco", "estoque_minimo"],
    "vendas": ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"],
    "despesas": ["pdv", "descricao", "valor", "vencimento"],
    "maquinas": ["nome_maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"],
    "pontos": ["nome", "senha"],
    "fornecedores": ["nome_fantasia", "cnpj_cpf"]
}

@st.cache_data(ttl=2)
def carregar(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLS.get(aba, []))
        df = df.dropna(how='all')
        num_cols = ["estoque", "preco", "valor", "valor_bruto", "valor_liquido", "taxa_debito", "taxa_credito", "taxa_pix", "estoque_minimo"]
        for col in num_cols:
            if col in df.columns: 
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame(columns=COLS.get(aba, []))

def render_logo(size="42px"):
    st.markdown(f'<h1 style="text-align:center;font-family:sans-serif;font-size:{size};color:#000;margin-bottom:0;">FLASH <span style="color:#7CFC00;font-style:italic;">STOP</span></h1>', unsafe_allow_html=True)

# ==================== 2. CONTROLE DE ACESSO ====================
if "auth" not in st.session_state: 
    st.session_state.auth = False
    st.session_state.perfil = None
    st.session_state.pdv_atual = None

if not st.session_state.auth:
    render_logo("55px")
    df_pts = carregar("pontos")
    col_l1, col_l2, col_l3 = st.columns([1,1.5,1])
    with col_l2:
        with st.form("login_form"):
            u = st.text_input("Usuário ou Nome do PDV")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar", use_container_width=True):
                if u == "admin" and s == "flash123":
                    st.session_state.auth = True
                    st.session_state.perfil = "admin"
                    st.rerun()
                elif not df_pts.empty and u in df_pts['nome'].values:
                    senha_correta = str(df_pts[df_pts['nome'] == u].iloc[0]['senha'])
                    if s == senha_correta:
                        st.session_state.auth = True
                        st.session_state.perfil = "cliente"
                        st.session_state.pdv_atual = u
                        st.rerun()
                st.error("Credenciais inválidas ou PDV não cadastrado.")
    st.stop()

# ==================== 3. NAVEGAÇÃO ====================
with st.sidebar:
    render_logo("30px")
    if st.session_state.perfil == "cliente":
        st.success(f"📍 Local: {st.session_state.pdv_atual}")
        menu = "🛍️ Self-Checkout"
    else:
        menu = st.radio("Menu", ["📊 Dashboard", "🛍️ Self-Checkout", "📈 Custos Fixos", "💰 Entrada Mercadoria", "📦 Inventário", "📂 Contabilidade", "📟 Configurações"])
    
    st.divider()
    if st.button("🚪 Sair do Sistema"):
        st.session_state.auth = False
        st.rerun()

# ==================== 4. DASHBOARD ====================
if menu == "📊 Dashboard":
    st.header("📊 Performance Flash Stop")
    df_v, df_d = carregar("vendas"), carregar("despesas")
    bruto = df_v['valor_bruto'].sum()
    liq = df_v['valor_liquido'].sum()
    gastos = df_d['valor'].sum()
    cashback = bruto * 0.02
    resultado = liq - gastos - cashback

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido", f"R$ {liq:,.2f}")
    c3.metric("Custos Fixos", f"R$ {gastos:,.2f}")
    c4.metric("Cashback (2%)", f"R$ {cashback:,.2f}")
    c5.metric("Lucro Real", f"R$ {resultado:,.2f}")

# ==================== 5. SELF-CHECKOUT ====================
elif menu == "🛍️ Self-Checkout":
    st.markdown(f"<h2 style='text-align: center;'>🛒 Checkout - {st.session_state.pdv_atual if st.session_state.pdv_atual else 'Modo Admin'}</h2>", unsafe_allow_html=True)
    df_p, df_m, df_pts = carregar("produtos"), carregar("maquinas"), carregar("pontos")
    v_pdv = st.session_state.pdv_atual if st.session_state.perfil == "cliente" else st.selectbox("Selecione PDV para teste:", df_pts['nome'].tolist())

    col_c1, col_c2, col_c3 = st.columns([1, 2, 1])
    with col_c2:
        with st.container(border=True):
            v_prod = st.selectbox("Escolha o Produto:", [""] + df_p['nome'].tolist())
            v_qtd = st.number_input("Qtd:", min_value=1, step=1)
            if v_prod != "":
                p_u = float(df_p[df_p['nome'] == v_prod].iloc[0]['preco'])
                total = p_u * v_qtd
                st.markdown(f"<h1 style='text-align:center; color:#7CFC00;'>R$ {total:,.2f}</h1>", unsafe_allow_html=True)
                v_forma = st.radio("Pagamento:", ["Pix", "Débito", "Crédito"], horizontal=True)
                if st.button("✅ FINALIZAR VENDA", use_container_width=True, type="primary"):
                    maqs = df_m[df_m['pdv_vinculado'] == v_pdv]['nome_maquina'].tolist()
                    m_n = maqs[0] if maqs else "Dinheiro"
                    idx = df_p[df_p['nome'] == v_prod].index[0]
                    taxa = 0.0
                    if m_n != "Dinheiro":
                        md = df_m[df_m['nome_maquina'] == m_n].iloc[0]
                        taxa = md['taxa_pix'] if v_forma == "Pix" else md['taxa_debito'] if v_forma == "Débito" else md['taxa_credito']
                    v_liq = total * (1 - (taxa/100))
                    df_p.at[idx, 'estoque'] -= v_qtd
                    venda = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": v_pdv, "maquina": m_n, "produto": v_prod, "valor_bruto": total, "valor_liquido": v_liq, "forma": v_forma}])
                    conn.update(worksheet="vendas", data=pd.concat([carregar("vendas"), venda], ignore_index=True))
                    conn.update(worksheet="produtos", data=df_p)
                    st.balloons(); st.success("Compra finalizada com sucesso!"); time.sleep(1); st.rerun()

# ==================== 6. CUSTOS FIXOS ====================
elif menu == "📈 Custos Fixos":
    st.header("📈 Registro de Despesas")
    df_d, df_pts = carregar("despesas"), carregar("pontos")
    with st.form("form_despesa"):
        p_escolhido = st.selectbox("Unidade:", df_pts['nome'].tolist())
        desc_d = st.text_input("Descrição do Gasto:")
        val_d = st.number_input("Valor R$:", min_value=0.0)
        if st.form_submit_button("Lançar Despesa"):
            nova_d = pd.DataFrame([{"pdv": p_escolhido, "descricao": desc_d, "valor": val_d, "vencimento": datetime.now().strftime("%d/%m/%Y")}])
            conn.update(worksheet="despesas", data=pd.concat([df_d, nova_d], ignore_index=True))
            st.success("Despesa salva com sucesso!"); st.rerun()
    st.dataframe(df_d, use_container_width=True)

# ==================== 7. ENTRADA MERCADORIA ====================
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Entrada de Estoque e Preços")
    df_p = carregar("produtos")
    sel_item = st.selectbox("Item:", ["NOVO"] + df_p['nome'].tolist())
    with st.form("form_entrada"):
        nome_p = st.text_input("Nome do Produto:") if sel_item == "NOVO" else sel_item
        c_ent, m_ent = st.columns(2)
        custo_p = c_ent.number_input("Custo Unitário:", min_value=0.0)
        margem_p = m_ent.slider("Margem de Lucro %:", 10, 200, 50)
        qtd_p = st.number_input("Quantidade:", min_value=1)
        validade_p = st.date_input("Validade:", format="DD/MM/YYYY")
        if st.form_submit_button("Confirmar Entrada"):
            preco_final = custo_p * (1 + margem_p/100)
            if sel_item == "NOVO":
                novo_p = pd.DataFrame([{"nome": nome_p, "estoque": qtd_p, "preco": preco_final, "validade": validade_p.strftime("%d/%m/%Y"), "estoque_minimo": 5}])
                df_p = pd.concat([df_p, novo_p], ignore_index=True)
            else:
                idx_p = df_p[df_p['nome'] == sel_item].index[0]
                df_p.at[idx_p, 'estoque'] += qtd_p
                df_p.at[idx_p, 'preco'] = preco_final
                df_p.at[idx_p, 'validade'] = validade_p.strftime("%d/%m/%Y")
            conn.update(worksheet="produtos", data=df_p); st.success("Estoque atualizado!"); st.rerun()

# ==================== 8. INVENTÁRIO (CORRIGIDO) ====================
elif menu == "📦 Inventário":
    st.header("📦 Gestão de Estoque")
    df_prod = carregar("produtos")
    st.dataframe(df_prod, use_container_width=True)
    with st.form("form_limite"):
        p_ajuste = st.selectbox("Produto para ajustar alerta:", df_prod['nome'].tolist())
        limite_n = st.number_input("Mínimo para Alerta:", min_value=0) # Linha que estava cortada
        if st.form_submit_button("Atualizar Alerta"):
            idx_a = df_prod[df_prod['nome'] == p_ajuste].index[0]
            df_prod.at[idx_a, 'estoque_minimo'] = limite_n
            conn.update(worksheet="produtos", data=df_prod)
            st.success("Limite salvo!"); st.rerun()

# ==================== 9. CONTABILIDADE (REVISADO) ====================
elif menu == "📂 Contabilidade":
    st.header("📂 Histórico de Vendas")
    df_vendas = carregar("vendas")
    if not df_vendas.empty:
        st.dataframe(df_vendas, use_container_width=True)
        csv_data = df_vendas.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Baixar Relatório CSV",
            data=csv_data,
            file_name="vendas_flash_stop.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhuma venda registrada até o momento.")

# ==================== 10. CONFIGURAÇÕES (REVISADO) ====================
elif menu == "📟 Configurações":
    st.header("📟 Unidades e Máquinas")
    df_pts, df_maqs = carregar("pontos"), carregar("maquinas")
    tab_unidade, tab_maquina = st.tabs(["PDVs", "Maquininhas"])
    
    with tab_unidade:
        with st.form("form_pdv"):
            nome_pdv = st.text_input("Nome da Unidade:")
            senha_pdv = st.text_input("Senha do Tablet:", type="password")
            if st.form_submit_button("Cadastrar PDV"):
                if nome_pdv and senha_pdv:
                    novo_p = pd.DataFrame([{"nome": nome_pdv, "senha": senha_pdv}])
                    conn.update(worksheet="pontos", data=pd.concat([df_pts, novo_p], ignore_index=True))
                    st.success("PDV Criado com sucesso!"); st.rerun()
                else:
                    st.warning("Preencha todos os campos.")
        st.subheader("PDVs Ativos")
        st.dataframe(df_pts, use_container_width=True, hide_index=True)
        
    with tab_maquina:
        with st.form("form_maq"):
            m_nome_cad = st.text_input("Identificação da Máquina (Ex: Moderninha 01):")
            m_vinculo = st.selectbox("Vincular ao PDV:", df_pts['nome'].tolist() if not df_pts.empty else ["Nenhum"])
            c_tx1, c_tx2, c_tx3 = st.columns(3)
            tx_p = c_tx1.number_input("Pix %", min_value=0.0, step=0.01)
            tx_d = c_tx2.number_input("Débito %", min_value=0.0, step=0.01)
            tx_c = c_tx3.number_input("Crédito %", min_value=0.0, step=0.01)
            if st.form_submit_button("Cadastrar Máquina"):
                if m_nome_cad:
                    nova_m = pd.DataFrame([{
                        "nome_maquina": m_nome_cad, 
                        "pdv_vinculado": m_vinculo, 
                        "taxa_debito": tx_d, 
                        "taxa_credito": tx_c, 
                        "taxa_pix": tx_p
                    }])
                    conn.update(worksheet="maquinas", data=pd.concat([df_maqs, nova_m], ignore_index=True))
                    st.success("Máquina vinculada!"); st.rerun()
        st.subheader("Máquinas Configuradas")
        st.dataframe(df_maqs, use_container_width=True, hide_index=True)
