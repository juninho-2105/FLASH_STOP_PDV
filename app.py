import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES INICIAIS ====================
st.set_page_config(page_title="Flash Stop Ultimate v6.5", layout="wide", page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)

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
    menu = st.radio("Navegação", [
        "📊 Dashboard & Performance", 
        "🛍️ Frente de Caixa (PDV)", 
        "📈 Custos Fixos", 
        "💰 Entrada de Mercadoria", 
        "📦 Inventário Geral", 
        "🚚 Fornecedores", 
        "📟 Configurações"
    ])
    if st.button("🔄 Atualizar Dados"):
        st.cache_data.clear()
        st.rerun()

# ==================== 4. DASHBOARD & PERFORMANCE ====================
if menu == "📊 Dashboard & Performance":
    st.header("📊 Performance da Flash Stop")
    df_v, df_d, df_p = carregar("vendas"), carregar("despesas"), carregar("produtos")
    
    bruto = df_v['valor_bruto'].sum()
    liq = df_v['valor_liquido'].sum()
    gastos = df_d['valor'].sum()
    cashback = bruto * 0.02
    resultado = liq - gastos - cashback

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido (Pós-Taxas)", f"R$ {liq:,.2f}")
    c3.metric("Custos Fixos", f"R$ {gastos:,.2f}")
    c4.metric("Cashback (2%)", f"R$ {cashback:,.2f}", delta=f"-{cashback:,.2f}", delta_color="inverse")
    c5.metric("Resultado Final", f"R$ {resultado:,.2f}")

    st.divider()
    if not df_v.empty:
        st.subheader("📈 Crescimento Mensal")
        df_v['data_dt'] = pd.to_datetime(df_v['data'], dayfirst=True, errors='coerce')
        df_chart = df_v.dropna(subset=['data_dt']).set_index('data_dt').resample('M')['valor_bruto'].sum().reset_index()
        df_chart['Mês'] = df_chart['data_dt'].dt.strftime('%m/%Y')
        st.area_chart(df_chart.set_index('Mês')['valor_bruto'])

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("🚨 Reposição de Estoque")
        baixo = df_p[df_p['estoque'] <= df_p['estoque_minimo']]
        if not baixo.empty: st.warning(f"{len(baixo)} itens críticos"); st.table(baixo[['nome', 'estoque']])
        else: st.success("Estoque OK!")
    with col_b:
        st.subheader("📅 Validade (15 dias)")
        hoje = datetime.now()
        vencendo = []
        for _, r in df_p.iterrows():
            try:
                dv = datetime.strptime(str(r['validade']), "%d/%m/%Y")
                if dv <= hoje + timedelta(days=15): vencendo.append({"Produto": r['nome'], "Data": r['validade']})
            except: continue
        if vencendo: st.error(f"{len(vencendo)} itens vencendo"); st.table(vencendo)
        else: st.success("Validades OK!")

# ==================== 5. FRENTE DE CAIXA ====================
elif menu == "🛍️ Frente de Caixa (PDV)":
    st.header("🛍️ Registro de Venda")
    df_p, df_m, df_pts = carregar("produtos"), carregar("maquinas"), carregar("pontos")
    with st.form("venda_form"):
        v_pdv = st.selectbox("Ponto", df_pts['nome'].tolist() if not df_pts.empty else ["-"])
        v_prod = st.selectbox("Produto", df_p['nome'].tolist() if not df_p.empty else ["-"])
        c1, c2 = st.columns(2)
        v_forma = c1.selectbox("Pagamento", ["Pix", "Débito", "Crédito", "Dinheiro"])
        v_maq = c2.selectbox("Máquina", df_m[df_m['pdv_vinculado'] == v_pdv]['nome_maquina'].tolist() if not df_m.empty else ["Dinheiro"])
        v_qtd = st.number_input("Qtd", min_value=1, step=1)
        if st.form_submit_button("🛒 FINALIZAR"):
            if v_prod != "-" and v_pdv != "-":
                idx = df_p[df_p['nome'] == v_prod].index[0]
                v_bruto = float(df_p.at[idx, 'preco']) * v_qtd
                taxa = 0.0
                if v_maq != "Dinheiro":
                    m_i = df_m[df_m['nome_maquina'] == v_maq].iloc[0]
                    taxa = m_i['taxa_pix'] if v_forma == "Pix" else m_i['taxa_debito'] if v_forma == "Débito" else m_i['taxa_credito']
                v_liq = v_bruto * (1 - (taxa/100))
                df_p.at[idx, 'estoque'] -= v_qtd
                nova = pd.DataFrame([{"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": v_pdv, "maquina": v_maq, "produto": v_prod, "valor_bruto": v_bruto, "valor_liquido": v_liq, "forma": v_forma}])
                conn.update(worksheet="vendas", data=pd.concat([carregar("vendas"), nova], ignore_index=True))
                conn.update(worksheet="produtos", data=df_p)
                st.success("Venda salva!"); time.sleep(1); st.rerun()

# ==================== 6. CUSTOS FIXOS ====================
elif menu == "📈 Custos Fixos":
    st.header("📈 Gastos Operacionais")
    df_d, df_pts = carregar("despesas"), carregar("pontos")
    with st.form("d_f"):
        p = st.selectbox("Unidade", df_pts['nome'].tolist() if not df_pts.empty else ["-"])
        d = st.text_input("Descrição")
        v = st.number_input("Valor R$", min_value=0.0)
        if st.form_submit_button("Salvar"):
            nova = pd.DataFrame([{"pdv": p, "descricao": d, "valor": v, "vencimento": datetime.now().strftime("%d/%m/%Y")}])
            conn.update(worksheet="despesas", data=pd.concat([df_d, nova], ignore_index=True))
            st.success("Lançado!"); st.rerun()
    st.dataframe(df_d, use_container_width=True)

# ==================== 7. ENTRADA DE MERCADORIA ====================
elif menu == "💰 Entrada de Mercadoria":
    st.header("💰 Entrada e Precificação")
    df_p = carregar("produtos")
    opcoes = ["NOVO"] + df_p['nome'].tolist()
    sel = st.selectbox("Produto para editar ou NOVO:", opcoes)
    
    val_estoque_atual = 0
    if sel != "NOVO":
        d_p = df_p[df_p['nome'] == sel].iloc[0]
        val_estoque_atual = int(d_p['estoque'])
        st.info(f"Editando: {sel} | Estoque Atual: {val_estoque_atual}")

    with st.form("ent_f"):
        nome_in = st.text_input("Nome") if sel == "NOVO" else sel
        c1, c2 = st.columns(2)
        custo = c1.number_input("Custo Un.", min_value=0.0)
        margem = c2.slider("Margem %", 10, 200, 50)
        qtd_in = st.number_input("Qtd Entrada", min_value=1)
        val_in = st.date_input("Validade")
        if st.form_submit_button("CONCLUIR"):
            preco_v = custo * (1 + margem/100)
            if sel == "NOVO":
                novo = pd.DataFrame([{"nome": nome_in, "estoque": qtd_in, "preco": preco_v, "validade": val_in.strftime("%d/%m/%Y"), "estoque_minimo": 5}])
                df_p = pd.concat([df_p, novo], ignore_index=True)
            else:
                idx = df_p[df_p['nome'] == sel].index[0]
                df_p.at[idx, 'estoque'] = val_estoque_atual + qtd_in
                df_p.at[idx, 'preco'] = preco_v
                df_p.at[idx, 'validade'] = val_in.strftime("%d/%m/%Y")
            conn.update(worksheet="produtos", data=df_p); st.success("Atualizado!"); time.sleep(1); st.rerun()

# ==================== 8. INVENTÁRIO GERAL ====================
elif menu == "📦 Inventário Geral":
    st.header("📦 Gestão de Inventário")
    df_p = carregar("produtos")
    with st.form("min_f"):
        p_sel = st.selectbox("Produto:", df_p['nome'].tolist() if not df_p.empty else ["-"])
        e_m = st.number_input("Novo Estoque Mínimo:", min_value=0)
        if st.form_submit_button("Atualizar Alerta"):
            idx = df_p[df_p['nome'] == p_sel].index[0]
            df_p.at[idx, 'estoque_minimo'] = e_m
            conn.update(worksheet="produtos", data=df_p); st.success("Limite alterado!"); st.rerun()
    st.divider()
    if not df_p.empty:
        df_p['Status'] = df_p.apply(lambda x: "🚨 REPOR" if x['estoque'] <= x['estoque_minimo'] else "✅ OK", axis=1)
        st.dataframe(df_p[['Status', 'nome', 'estoque', 'estoque_minimo', 'preco', 'validade']], use_container_width=True, hide_index=True)

# ==================== 9. RELATÓRIOS CONTÁBEIS ====================
elif menu == "📂 Relatórios Contábeis":
    st.header("📂 Fechamento e Exportação Contábil")
    df_v = carregar("vendas")
    df_pts = carregar("pontos")
    
    if not df_v.empty:
        # Filtros para o Contador
        col1, col2 = st.columns(2)
        pdv_filtro = col1.selectbox("Filtrar por Unidade", ["Todos"] + df_pts['nome'].tolist())
        
        # Filtro de Data
        df_v['data_dt'] = pd.to_datetime(df_v['data'], dayfirst=True, errors='coerce')
        meses = df_v['data_dt'].dt.strftime('%m/%Y').unique().tolist()
        mes_filtro = col2.selectbox("Filtrar por Mês", ["Todos"] + meses)
        
        # Aplicação dos Filtros
        dados_filtrados = df_v.copy()
        if pdv_filtro != "Todos":
            dados_filtrados = dados_filtrados[dados_filtrados['pdv'] == pdv_filtro]
        if mes_filtro != "Todos":
            dados_filtrados = dados_filtrados[dados_filtrados['data_dt'].dt.strftime('%m/%Y') == mes_filtro]
            
        # Resumo para conferência rápida
        st.subheader(f"Resumo: {pdv_filtro} ({mes_filtro})")
        c1, c2, c3 = st.columns(3)
        bruto_f = dados_filtrados['valor_bruto'].sum()
        liq_f = dados_filtrados['valor_liquido'].sum()
        c1.metric("Faturamento Bruto", f"R$ {bruto_f:,.2f}")
        c2.metric("Líquido (Pós-Taxas)", f"R$ {liq_f:,.2f}")
        c3.metric("Total de Vendas", len(dados_filtrados))
        
        st.divider()
        
        # Tabela de Dados e Exportação
        st.write("Dados detalhados para o contador:")
        # Removemos a coluna auxiliar de data antes de mostrar/baixar
        export_df = dados_filtrados.drop(columns=['data_dt'])
        st.dataframe(export_df, use_container_width=True, hide_index=True)
        
        # Botão de Download CSV
        csv = export_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Baixar Relatório para Excel/Contabilidade",
            data=csv,
            file_name=f"contabilidade_flash_stop_{pdv_filtro}_{mes_filtro}.csv",
            mime="text/csv",
        )
    else:
        st.info("Ainda não existem vendas registradas para gerar relatórios.")
# ==================== 10. FORNECEDORES ====================
elif menu == "🚚 Fornecedores":
    st.header("🚚 Gestão de Fornecedores")
    df_f = carregar("fornecedores")
    with st.form("f_f"):
        n = st.text_input("Nome Fantasia"); c = st.text_input("CNPJ/CPF")
        if st.form_submit_button("Salvar"):
            conn.update(worksheet="fornecedores", data=pd.concat([df_f, pd.DataFrame([{"nome_fantasia": n, "cnpj_cpf": c}])], ignore_index=True))
            st.rerun()
    st.dataframe(df_f, use_container_width=True)

# ==================== 11. CONFIGURAÇÕES ====================
elif menu == "📟 Configurações":
    st.header("📟 Unidades e Taxas")
    df_pts, df_m = carregar("pontos"), carregar("maquinas")
    t1, t2 = st.tabs(["Unidades/PDV", "Máquinas de Cartão"])
    with t1:
        n_p = st.text_input("Novo PDV")
        if st.button("Cadastrar PDV"):
            conn.update(worksheet="pontos", data=pd.concat([df_pts, pd.DataFrame([{"nome": n_p}])], ignore_index=True)); st.rerun()
        st.dataframe(df_pts, use_container_width=True)
    with t2:
        with st.form("m_f"):
            mn = st.text_input("Máquina"); mv = st.selectbox("PDV", df_pts['nome'].tolist() if not df_pts.empty else ["-"])
            c1, c2, c3 = st.columns(3); p_tx = c1.number_input("Pix %"); d_tx = c2.number_input("Débito %"); c_tx = c3.number_input("Crédito %")
            if st.form_submit_button("Salvar Máquina"):
                conn.update(worksheet="maquinas", data=pd.concat([df_m, pd.DataFrame([{"nome_maquina": mn, "pdv_vinculado": mv, "taxa_debito": d_tx, "taxa_credito": c_tx, "taxa_pix": p_tx}])], ignore_index=True)); st.rerun()
        st.dataframe(df_m, use_container_width=True)
