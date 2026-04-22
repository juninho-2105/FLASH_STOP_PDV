import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES INICIAIS ====================
st.set_page_config(page_title="Flash Stop Ultimate v6.4", layout="wide", page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)

# Mapa de colunas para garantir que o sistema não quebre se a planilha estiver vazia
COLS = {
    "produtos": ["nome", "estoque", "validade", "preco", "estoque_minimo"],
    "vendas": ["data", "pdv", "maquina", "produto", "valor_bruto", "valor_liquido", "forma"],
    "despesas": ["pdv", "descricao", "valor", "vencimento"],
    "maquinas": ["nome_maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"],
    "pontos": ["nome"],
    "fornecedores": ["nome_fantasia", "cnpj_cpf"]
}

@st.cache_data(ttl=2)
def carregar(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=COLS.get(aba, []))
        df = df.dropna(how='all')
        # Padronização numérica para cálculos
        num_cols = ["estoque", "preco", "valor", "valor_bruto", "valor_liquido", "taxa_debito", "taxa_credito", "taxa_pix", "estoque_minimo"]
        for col in num_cols:
            if col in df.columns: 
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    except: return pd.DataFrame(columns=COLS.get(aba, []))

def render_logo(size="42px"):
    st.markdown(f'<h1 style="text-align:center;font-family:sans-serif;font-size:{size};color:#000;">FLASH <span style="color:#7CFC00;font-style:italic;">STOP</span></h1>', unsafe_allow_html=True)

# ==================== 2. CONTROLE DE ACESSO ====================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    render_logo("55px")
    with st.form("login"):
        u, s = st.text_input("Usuário"), st.text_input("Senha", type="password")
        if st.form_submit_button("Acessar Painel"):
            if u == "admin" and s == "flash123":
                st.session_state.auth = True
                st.rerun()
    st.stop()

# ==================== 3. MENU LATERAL ====================
with st.sidebar:
    render_logo("30px")
    st.divider()
    menu = st.radio("Menu de Navegação", [
        "📊 Dashboard & Performance", 
        "🛍️ Frente de Caixa (PDV)", 
        "📈 Custos Fixos", 
        "💰 Entrada de Mercadoria", 
        "📦 Inventário Geral", 
        "🚚 Fornecedores", 
        "📟 Configurações"
    ])
    if st.button("🔄 Atualizar Banco de Dados"):
        st.cache_data.clear()
        st.rerun()

# ==================== 4. DASHBOARD & PERFORMANCE ====================
if menu == "📊 Dashboard & Performance":
    st.header("📊 Performance da Flash Stop")
    df_v, df_d, df_p = carregar("vendas"), carregar("despesas"), carregar("produtos")
    
    # Cálculos Financeiros
    bruto = df_v['valor_bruto'].sum()
    liq = df_v['valor_liquido'].sum() # Valor já sem as taxas das máquinas
    gastos = df_d['valor'].sum()     # Custos fixos
    cashback = bruto * 0.02          # 2% de Cashback sobre o faturamento total
    resultado = liq - gastos - cashback

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido (Pós-Taxas)", f"R$ {liq:,.2f}")
    c3.metric("Custos Fixos", f"R$ {gastos:,.2f}")
    c4.metric("Cashback (2%)", f"R$ {cashback:,.2f}", delta=f"-{cashback:,.2f}", delta_color="inverse")
    c5.metric("Resultado Final", f"R$ {resultado:,.2f}", delta=f"{resultado:,.2f}")

    st.divider()
    
    # Gráfico de Evolução Mensal
    if not df_v.empty:
        st.subheader("📈 Crescimento Mensal (Faturamento)")
        df_v['data_dt'] = pd.to_datetime(df_v['data'], dayfirst=True, errors='coerce')
        df_chart = df_v.dropna(subset=['data_dt']).set_index('data_dt').resample('M')['valor_bruto'].sum().reset_index()
        df_chart['Mês'] = df_chart['data_dt'].dt.strftime('%m/%Y')
        st.area_chart(df_chart.set_index('Mês')['valor_bruto'])

# ==================== 5. FRENTE DE CAIXA (PDV) ====================
elif menu == "🛍️ Frente de Caixa (PDV)":
    st.header("🛍️ Registro de Venda")
    df_p, df_m, df_pts = carregar("produtos"), carregar("maquinas"), carregar("pontos")
    
    with st.form("venda_form"):
        v_pdv = st.selectbox("Selecione o Ponto", df_pts['nome'].tolist() if not df_pts.empty else ["-"])
        v_prod = st.selectbox("Selecione o Produto", df_p['nome'].tolist() if not df_p.empty else ["-"])
        c1, c2 = st.columns(2)
        v_forma = c1.selectbox("Forma de Pagamento", ["Pix", "Débito", "Crédito", "Dinheiro"])
        v_maq = c2.selectbox("Máquina Utilizada", df_m[df_m['pdv_vinculado'] == v_pdv]['nome_maquina'].tolist() if not df_m.empty else ["Dinheiro"])
        v_qtd = st.number_input("Quantidade", min_value=1, step=1)
        
        if st.form_submit_button("🛒 FINALIZAR VENDA"):
            if v_prod != "-" and v_pdv != "-":
                idx = df_p[df_p['nome'] == v_prod].index[0]
                v_bruto = float(df_p.at[idx, 'preco']) * v_qtd
                taxa = 0.0
                if v_maq != "Dinheiro":
                    m_info = df_m[df_m['nome_maquina'] == v_maq].iloc[0]
                    taxa = m_info['taxa_pix'] if v_forma == "Pix" else m_info['taxa_debito'] if v_forma == "Débito" else m_info['taxa_credito'] if v_forma == "Crédito" else 0.0
                
                v_liq = v_bruto * (1 - (taxa/100))
                df_p.at[idx, 'estoque'] -= v_qtd
                
                nova_venda = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": v_pdv, "maquina": v_maq, "produto": v_prod, "valor_bruto": v_bruto, "valor_liquido": v_liq, "forma": v_forma}])
                conn.update(worksheet="vendas", data=pd.concat([carregar("vendas"), nova_venda], ignore_index=True))
                conn.update(worksheet="produtos", data=df_p)
                st.success(f"Venda de {v_prod} salva!"); time.sleep(1); st.rerun()

# ==================== 6. CUSTOS FIXOS ====================
elif menu == "📈 Custos Fixos":
    st.header("📈 Lançamento de Gastos Operacionais")
    df_d, df_pts = carregar("despesas"), carregar("pontos")
    with st.form("despesa_form"):
        p = st.selectbox("Unidade Responsável", df_pts['nome'].tolist() if not df_pts.empty else ["-"])
        d = st.text_input("Descrição (Ex: Condomínio, Luz, Sistema)")
        v = st.number_input("Valor R$", min_value=0.0)
        if st.form_submit_button("Lançar Despesa"):
            nova = pd.DataFrame([{"pdv": p, "descricao": d, "valor": v, "vencimento": datetime.now().strftime("%d/%m/%Y")}])
            conn.update(worksheet="despesas", data=pd.concat([df_d, nova], ignore_index=True))
            st.success("Despesa cadastrada!"); st.rerun()
    st.divider()
    st.subheader("📋 Histórico de Despesas")
    st.dataframe(df_d, use_container_width=True, hide_index=True)

# ==================== 7. ENTRADA DE MERCADORIA ====================
elif menu == "💰 Entrada de Mercadoria":
    st.header("💰 Entrada e Precificação")
    df_p = carregar("produtos")
    with st.form("entrada_form"):
        sel = st.selectbox("Produto", ["NOVO"] + df_p['nome'].tolist())
        nome = st.text_input("Nome") if sel == "NOVO" else sel
        c1, c2 = st.columns(2)
        custo = c1.number_input("Custo de Compra (Un)")
        margem = c2.slider("Margem Desejada (%)", 10, 200, 50)
        qtd = st.number_input("Qtd Entrada", min_value=1)
        val = st.date_input("Data de Validade")
        
        if st.form_submit_button("Confirmar Entrada"):
            preco_final = custo * (1 + margem/100)
            if sel == "NOVO":
                novo = pd.DataFrame([{"nome": nome, "estoque": qtd, "preco": preco_final, "validade": val.strftime("%d/%m/%Y"), "estoque_minimo": 5}])
                df_p = pd.concat([df_p, novo], ignore_index=True)
            else:
                idx = df_p[df_p['nome'] == sel].index[0]
                df_p.at[idx, 'estoque'] += qtd; df_p.at[idx, 'preco'] = preco_final; df_p.at[idx, 'validade'] = val.strftime("%d/%m/%Y")
            conn.update(worksheet="produtos", data=df_p); st.success("Estoque atualizado!"); st.rerun()

# ==================== 8. OUTROS MÓDULOS ====================
elif menu == "📦 Inventário Geral":
    st.header("📦 Estoque em Tempo Real")
    st.dataframe(carregar("produtos"), use_container_width=True, hide_index=True)

elif menu == "🚚 Fornecedores":
    st.header("🚚 Gestão de Parceiros")
    df_f = carregar("fornecedores")
    with st.form("f_form"):
        n = st.text_input("Nome Fantasia"); c = st.text_input("CNPJ/CPF")
        if st.form_submit_button("Salvar Fornecedor"):
            conn.update(worksheet="fornecedores", data=pd.concat([df_f, pd.DataFrame([{"nome_fantasia": n, "cnpj_cpf": c}])], ignore_index=True)); st.rerun()
    st.dataframe(df_f, use_container_width=True, hide_index=True)

elif menu == "📟 Configurações":
    st.header("📟 Unidades e Taxas")
    df_pts, df_maq = carregar("pontos"), carregar("maquinas")
    
    t1, t2 = st.tabs(["Unidades/PDV", "Máquinas de Cartão"])
    with t1:
        n_p = st.text_input("Novo PDV")
        if st.button("Cadastrar PDV"):
            conn.update(worksheet="pontos", data=pd.concat([df_pts, pd.DataFrame([{"nome": n_p}])], ignore_index=True)); st.rerun()
        st.dataframe(df_pts, use_container_width=True)
    with t2:
        with st.form("maq_f"):
            mn = st.text_input("Nome Máquina"); mv = st.selectbox("PDV Vinculado", df_pts['nome'].tolist() if not df_pts.empty else ["-"])
            c1, c2, c3 = st.columns(3); p = c1.number_input("Pix %"); d = c2.number_input("Débito %"); c = c3.number_input("Crédito %")
            if st.form_submit_button("Salvar Máquina"):
                conn.update(worksheet="maquinas", data=pd.concat([df_maq, pd.DataFrame([{"nome_maquina": mn, "pdv_vinculado": mv, "taxa_debito": d, "taxa_credito": c, "taxa_pix": p}])], ignore_index=True)); st.rerun()
        st.dataframe(df_maq, use_container_width=True) 
