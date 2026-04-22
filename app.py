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
    "pontos": ["nome", "senha"]
}

@st.cache_data(ttl=300) # Cache de 5 min para velocidade
def carregar_estatico(aba):
    try:
        df = conn.read(worksheet=aba, ttl=0)
        return df.dropna(how='all') if df is not None else pd.DataFrame(columns=COLS.get(aba, []))
    except:
        return pd.DataFrame(columns=COLS.get(aba, []))

def carregar_dinamico(aba): # Sem cache para dados em tempo real
    try:
        df = conn.read(worksheet=aba, ttl=0)
        return df.dropna(how='all') if df is not None else pd.DataFrame(columns=COLS.get(aba, []))
    except:
        return pd.DataFrame(columns=COLS.get(aba, []))

def render_logo(size="42px"):
    st.markdown(f'<h1 style="text-align:center;font-family:sans-serif;font-size:{size};color:#000;margin-bottom:0;">FLASH <span style="color:#7CFC00;font-style:italic;">STOP</span></h1>', unsafe_allow_html=True)

# ==================== 2. CONTROLE DE ACESSO ====================
if "auth" not in st.session_state: 
    st.session_state.auth, st.session_state.perfil, st.session_state.pdv_atual = False, None, None

if not st.session_state.auth:
    render_logo("55px")
    df_pts = carregar_estatico("pontos")
    col_l1, col_l2, col_l3 = st.columns([1,1.5,1])
    with col_l2:
        with st.form("login_form"):
            u = st.text_input("Usuário ou Nome do PDV")
            s = st.text_input("Senha", type="password")
            if st.form_submit_button("Acessar", use_container_width=True):
                if u == "admin" and s == "flash123":
                    st.session_state.auth, st.session_state.perfil = True, "admin"
                    st.rerun()
                elif not df_pts.empty and u in df_pts['nome'].values:
                    if s == str(df_pts[df_pts['nome'] == u].iloc[0]['senha']):
                        st.session_state.auth, st.session_state.perfil, st.session_state.pdv_atual = True, "cliente", u
                        st.rerun()
                st.error("Credenciais inválidas.")
    st.stop()

# ==================== 3. NAVEGAÇÃO ====================
with st.sidebar:
    render_logo("30px")
    menu = "🛍️ Self-Checkout" if st.session_state.perfil == "cliente" else st.radio("Menu", ["📊 Dashboard", "🛍️ Self-Checkout", "📈 Custos Fixos", "💰 Entrada Mercadoria", "📦 Inventário", "📂 Contabilidade", "📟 Configurações"])
    st.divider()
    if st.button("🚪 Sair"):
        st.session_state.auth = False
        st.rerun()

# ==================== 4. DASHBOARD (VERSÃO COMPLETA COM ALERTAS) ====================
if menu == "📊 Dashboard":
    st.header("📊 Performance Flash Stop")
    df_v, df_d, df_p = carregar_dinamico("vendas"), carregar_dinamico("despesas"), carregar_dinamico("produtos")
    
    # --- CÁLCULOS FINANCEIROS ---
    bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
    liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
    gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
    cashback = bruto * 0.02
    res = liq - gastos - cashback

    # --- MÉTRICAS PRINCIPAIS ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Bruto Total", f"R$ {bruto:,.2f}")
    c2.metric("Líquido", f"R$ {liq:,.2f}")
    c3.metric("Custos Fixos", f"R$ {gastos:,.2f}")
    c4.metric("Cashback (2%)", f"R$ {cashback:,.2f}", delta=f"-{cashback:,.2f}", delta_color="inverse")
    c5.metric("Lucro Real", f"R$ {res:,.2f}")

    st.divider()

    # --- GRÁFICO DE EVOLUÇÃO ---
    st.subheader("📈 Evolução de Vendas por Dia")
    if not df_v.empty:
        df_v['data_dt'] = pd.to_datetime(df_v['data'], format="%d/%m/%Y %H:%M", errors='coerce')
        vendas_dia = df_v.groupby(df_v['data_dt'].dt.date)['valor_bruto'].sum()
        st.bar_chart(vendas_dia, color="#7CFC00")
    else:
        st.info("Aguardando vendas para gerar o gráfico.")

    st.divider()

    # --- ALERTAS CRÍTICOS ---
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🚨 Alerta de Estoque Baixo")
        # Comparação entre estoque atual e estoque mínimo definido no inventário
        estoque_critico = df_p[pd.to_numeric(df_p['estoque']) <= pd.to_numeric(df_p['estoque_minimo'])]
        if not estoque_critico.empty:
            st.warning(f"Atenção: {len(estoque_critico)} itens em nível crítico.")
            st.dataframe(estoque_critico[['nome', 'estoque', 'estoque_minimo']], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Estoque em dia!")

    with col_b:
        st.subheader("📅 Alerta de Validade")
        vencendo = []
        hoje = datetime.now()
        margem = hoje + timedelta(days=15) # Alerta com 15 dias de antecedência

        for _, item in df_p.iterrows():
            try:
                dt_val = datetime.strptime(str(item['validade']), "%d/%m/%Y")
                if dt_val <= margem:
                    vencendo.append({
                        "Produto": item['nome'], 
                        "Vencimento": item['validade'], 
                        "Status": "VENCIDO" if dt_val < hoje else "Crítico"
                    })
            except: continue
        
        if vencendo:
            st.error(f"Validade Crítica: {len(vencendo)} itens.")
            st.table(vencendo)
        else:
            st.success("✅ Nenhuma validade próxima!")

# ==================== 5. SELF-CHECKOUT (OTIMIZADO) ====================
elif menu == "🛍️ Self-Checkout":
    h = datetime.now().hour
    saudacao = "Bom dia! ☕" if h < 12 else "Boa tarde! ☀️" if h < 18 else "Boa noite! 🌙"
    st.markdown(f"<h3 style='text-align: center; color: #555;'>{saudacao}</h3>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align: center; margin-top: -15px;'>Bem-vindo à Flash Stop</h2>", unsafe_allow_html=True)
    
    df_p = carregar_estatico("produtos")
    df_m = carregar_estatico("maquinas")
    df_pts = carregar_estatico("pontos")
    
    v_pdv = st.session_state.pdv_atual if st.session_state.perfil == "cliente" else st.selectbox("PDV:", df_pts['nome'].tolist())

    col_v1, col_v2, col_v3 = st.columns([0.5, 2, 0.5])
    with col_v2:
        with st.container(border=True):
            v_prod = st.selectbox("Selecione o Produto:", [""] + df_p['nome'].tolist(), key="sb_final")
            v_qtd = st.number_input("Quantidade:", min_value=1, step=1, value=1)
            
            if v_prod != "":
                p_unit = float(df_p[df_p['nome'] == v_prod].iloc[0]['preco'])
                total = p_unit * v_qtd
                
                st.markdown(f"""
                    <div style="background-color: #000; padding: 20px; border-radius: 15px; text-align: center; margin: 15px 0; border-left: 10px solid #7CFC00;">
                        <p style="color: #FFF; margin: 0; font-size: 18px;">VALOR TOTAL</p>
                        <h1 style="color: #7CFC00; margin: 0; font-size: 55px;">R$ {total:,.2f}</h1>
                    </div>
                """, unsafe_allow_html=True)
                
                v_forma = st.radio("Pagamento:", ["Pix", "Débito", "Crédito"], horizontal=True)
                
                if st.button("✅ FINALIZAR COMPRA", use_container_width=True, type="primary"):
                    with st.spinner("Gravando..."):
                        maqs = df_m[df_m['pdv_vinculado'] == v_pdv]['nome_maquina'].tolist()
                        m_n = maqs[0] if maqs else "Dinheiro"
                        taxa = 0.0
                        if m_n != "Dinheiro":
                            md = df_m[df_m['nome_maquina'] == m_n].iloc[0]
                            taxa = md['taxa_pix'] if v_forma == "Pix" else md['taxa_debito'] if v_forma == "Débito" else md['taxa_credito']
                        
                        v_liq = total * (1 - (taxa/100))
                        df_p_real = carregar_dinamico("produtos")
                        idx = df_p_real[df_p_real['nome'] == v_prod].index[0]
                        df_p_real.at[idx, 'estoque'] -= v_qtd
                        
                        venda = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": v_pdv, "maquina": m_n, "produto": v_prod, "valor_bruto": total, "valor_liquido": v_liq, "forma": v_forma}])
                        
                        conn.update(worksheet="vendas", data=pd.concat([carregar_dinamico("vendas"), venda], ignore_index=True))
                        conn.update(worksheet="produtos", data=df_p_real)
                        st.balloons(); st.success("Sucesso!"); time.sleep(1.5); st.rerun()

# ==================== 6. CUSTOS FIXOS ====================
elif menu == "📈 Custos Fixos":
    st.header("📈 Despesas Operacionais")
    df_d, df_pts = carregar_dinamico("despesas"), carregar_estatico("pontos")
    with st.form("f_d"):
        p, d, v = st.selectbox("PDV", df_pts['nome'].tolist()), st.text_input("Descrição"), st.number_input("Valor", min_value=0.0)
        if st.form_submit_button("Lançar"):
            nova = pd.DataFrame([{"pdv": p, "descricao": d, "valor": v, "vencimento": datetime.now().strftime("%d/%m/%Y")}])
            conn.update(worksheet="despesas", data=pd.concat([df_d, nova], ignore_index=True)); st.rerun()
    st.dataframe(df_d, use_container_width=True)

# ==================== 7. ENTRADA MERCADORIA ====================
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Gestão de Entrada")
    df_p = carregar_dinamico("produtos")
    sel = st.selectbox("Produto:", ["NOVO"] + df_p['nome'].tolist())
    with st.form("f_e"):
        n = st.text_input("Nome") if sel == "NOVO" else sel
        c_ent, m_ent = st.columns(2)
        custo = c_ent.number_input("Custo Unit.", min_value=0.0)
        margem = m_ent.slider("Margem %", 10, 200, 50)
        qtd = st.number_input("Quantidade", min_value=1)
        val = st.date_input("Validade")
        if st.form_submit_button("Gravar"):
            pv = custo * (1 + margem/100)
            if sel == "NOVO":
                n_df = pd.DataFrame([{"nome": n, "estoque": qtd, "preco": pv, "validade": val.strftime("%d/%m/%Y"), "estoque_minimo": 5}])
                df_p = pd.concat([df_p, n_df], ignore_index=True)
            else:
                idx = df_p[df_p['nome'] == sel].index[0]
                df_p.at[idx, 'estoque'] += qtd
                df_p.at[idx, 'preco'], df_p.at[idx, 'validade'] = pv, val.strftime("%d/%m/%Y")
            conn.update(worksheet="produtos", data=df_p); st.rerun()

# ==================== 8. INVENTÁRIO ====================
elif menu == "📦 Inventário":
    st.header("📦 Controle de Estoque")
    df_p = carregar_dinamico("produtos")
    st.dataframe(df_p, use_container_width=True)
    with st.form("f_inv"):
        p_sel = st.selectbox("Ajustar Mínimo de:", df_p['nome'].tolist())
        min_n = st.number_input("Novo Alerta Mínimo", min_value=0)
        if st.form_submit_button("Salvar Alerta"):
            idx = df_p[df_p['nome'] == p_sel].index[0]
            df_p.at[idx, 'estoque_minimo'] = min_n
            conn.update(worksheet="produtos", data=df_p); st.rerun()

# ==================== 9. CONTABILIDADE ====================
elif menu == "📂 Contabilidade":
    st.header("📂 Relatório Contábil")
    df_v, df_pts = carregar_dinamico("vendas"), carregar_estatico("pontos")
    if not df_v.empty:
        f_pdv = st.selectbox("Filtrar por Unidade:", ["Todos"] + df_pts['nome'].tolist())
        df_f = df_v if f_pdv == "Todos" else df_v[df_v['pdv'] == f_pdv]
        st.dataframe(df_f, use_container_width=True)
        st.download_button("📥 Exportar para Contador", data=df_f.to_csv(index=False).encode('utf-8-sig'), file_name=f"contabilidade_{f_pdv}.csv")

# ==================== 10. CONFIGURAÇÕES ====================
elif menu == "📟 Configurações":
    st.header("📟 Gerenciar Unidades")
    df_pts, df_m = carregar_dinamico("pontos"), carregar_dinamico("maquinas")
    t1, t2 = st.tabs(["PDVs", "Máquinas"])
    with t1:
        with st.form("f_pts"):
            n_p, s_p = st.text_input("Nome PDV"), st.text_input("Senha")
            if st.form_submit_button("Add PDV"):
                conn.update(worksheet="pontos", data=pd.concat([df_pts, pd.DataFrame([{"nome": n_p, "senha": s_p}])], ignore_index=True)); st.rerun()
        st.table(df_pts)
    with t2:
        with st.form("f_m"):
            mn, mv = st.text_input("Nome Máquina"), st.selectbox("Vincular", df_pts['nome'].tolist())
            c1, c2, c3 = st.columns(3)
            txp, txd, txc = c1.number_input("Pix %"), c2.number_input("Débito %"), c3.number_input("Crédito %")
            if st.form_submit_button("Add Máquina"):
                n_m = pd.DataFrame([{"nome_maquina": mn, "pdv_vinculado": mv, "taxa_debito": txd, "taxa_credito": txc, "taxa_pix": txp}])
                conn.update(worksheet="maquinas", data=pd.concat([df_m, n_m], ignore_index=True)); st.rerun()
        st.table(df_m)
