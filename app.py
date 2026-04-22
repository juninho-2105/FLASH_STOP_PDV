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

# ==================== 4. DASHBOARD (COM QUANTIDADE NOS ALERTAS) ====================
if menu == "📊 Dashboard":
    st.header("📊 Performance Flash Stop")
    df_v, df_d, df_p = carregar_dinamico("vendas"), carregar_dinamico("despesas"), carregar_dinamico("produtos")
    
    # --- CÁLCULOS FINANCEIROS ---
    bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
    liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
    gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
    cashback = bruto * 0.02
    res = liq - gastos - cashback

    # --- MÉTRICAS ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Bruto Total", f"R$ {bruto:,.2f}")
    c2.metric("Líquido", f"R$ {liq:,.2f}")
    c3.metric("Custos Fixos", f"R$ {gastos:,.2f}")
    c4.metric("Cashback (2%)", f"R$ {cashback:,.2f}")
    c5.metric("Lucro Real", f"R$ {res:,.2f}")

    st.divider()

    # --- GRÁFICO DE EVOLUÇÃO ---
    st.subheader("📈 Evolução de Vendas por Dia")
    if not df_v.empty:
        df_v['data_dt'] = pd.to_datetime(df_v['data'], format="%d/%m/%Y %H:%M", errors='coerce')
        vendas_dia = df_v.groupby(df_v['data_dt'].dt.date)['valor_bruto'].sum()
        st.bar_chart(vendas_dia, color="#7CFC00")

    st.divider()

    # --- ALERTAS CRÍTICOS ---
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🚨 Alerta de Estoque Baixo")
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
        margem = hoje + timedelta(days=15) 

        for _, item in df_p.iterrows():
            try:
                dt_val = datetime.strptime(str(item['validade']), "%d/%m/%Y")
                if dt_val <= margem:
                    # ADICIONADA A COLUNA 'ESTOQUE' NO ALERTA
                    vencendo.append({
                        "Produto": item['nome'], 
                        "Qtd em Estoque": int(item['estoque']), # Nova informação
                        "Vencimento": item['validade'], 
                        "Status": "VENCIDO" if dt_val < hoje else "Crítico"
                    })
            except: continue
        
        if vencendo:
            st.error(f"Validade Crítica: {len(vencendo)} itens.")
            # Exibindo a tabela com a quantidade
            st.dataframe(pd.DataFrame(vencendo), use_container_width=True, hide_index=True)
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

# ==================== 7. ENTRADA MERCADORIA (COM CÁLCULO DE MARGEM) ====================
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Gestão de Entrada e Precificação")
    df_p = carregar_dinamico("produtos")
    
    opcoes_produtos = ["✨ NOVO PRODUTO"] + df_p['nome'].tolist()
    sel_item = st.selectbox("Selecione o produto:", opcoes_produtos)
    
    with st.form("form_entrada_margem"):
        if sel_item == "✨ NOVO PRODUTO":
            nome_p = st.text_input("Nome do Novo Produto:")
            estoque_atual, preco_atual, e_min_sug, val_sug = 0, 0.0, 5, datetime.now()
        else:
            dados = df_p[df_p['nome'] == sel_item].iloc[0]
            nome_p = st.text_input("Nome do Produto:", value=dados['nome'])
            estoque_atual = int(dados['estoque'])
            preco_atual = float(dados['preco'])
            e_min_sug = int(dados['estoque_minimo'])
            try: val_sug = datetime.strptime(str(dados['validade']), "%d/%m/%Y")
            except: val_sug = datetime.now()

        c1, c2, c3 = st.columns(3)
        with c1:
            custo_un = st.number_input("Custo Unitário (R$):", min_value=0.0, step=0.01, help="Preço que você pagou pelo item.")
            qtd_nova = st.number_input("Qtd Entrada:", min_value=0, step=1, value=0)
        
        with c2:
            margem = st.slider("Margem de Lucro (%):", 0, 300, 50)
            # Cálculo automático da sugestão de preço
            sugestao_venda = custo_un * (1 + (margem / 100))
            preco_final = st.number_input("Preço de Venda Final (R$):", min_value=0.0, value=max(sugestao_venda, preco_atual), format="%.2f")
        
        with c3:
            estoque_min_p = st.number_input("Estoque Mínimo:", min_value=0, value=e_min_sug)
            validade_p = st.date_input("Data de Validade:", value=val_sug, format="DD/MM/YYYY")

        st.info(f"💡 Sugestão baseada na margem: R$ {sugestao_venda:,.2f} | Estoque Final: {estoque_atual + qtd_nova}")

        if st.form_submit_button("💾 SALVAR PRODUTO"):
            if not nome_p:
                st.error("O nome é obrigatório.")
            else:
                with st.spinner("Salvando..."):
                    if sel_item == "✨ NOVO PRODUTO":
                        novo_p = pd.DataFrame([{
                            "nome": nome_p, "estoque": qtd_nova, "preco": preco_final,
                            "validade": validade_p.strftime("%d/%m/%Y"), "estoque_minimo": estoque_min_p
                        }])
                        df_final = pd.concat([df_p, novo_p], ignore_index=True)
                    else:
                        idx = df_p[df_p['nome'] == sel_item].index[0]
                        df_p.at[idx, 'nome'] = nome_p
                        df_p.at[idx, 'estoque'] = estoque_atual + qtd_nova
                        df_p.at[idx, 'preco'] = preco_final
                        df_p.at[idx, 'validade'] = validade_p.strftime("%d/%m/%Y")
                        df_p.at[idx, 'estoque_minimo'] = estoque_min_p
                        df_final = df_p

                    conn.update(worksheet="produtos", data=df_final)
                    st.success("Dados atualizados!")
                    time.sleep(1); st.rerun()

# ==================== 8. INVENTÁRIO (COM BAIXA DE VENCIDOS) ====================
elif menu == "📦 Inventário":
    st.header("📦 Controle de Estoque e Perdas")
    df_p = carregar_dinamico("produtos")
    
    # --- VISUALIZAÇÃO GERAL ---
    st.subheader("Situação Atual do Estoque")
    st.dataframe(df_p, use_container_width=True, hide_index=True)

    st.divider()

    col_inv1, col_inv2 = st.columns(2)

    # --- AJUSTE DE ALERTA MÍNIMO ---
    with col_inv1:
        with st.container(border=True):
            st.markdown("#### ⚙️ Ajustar Alerta Mínimo")
            p_sel_min = st.selectbox("Produto para configurar alerta:", df_p['nome'].tolist(), key="sel_min")
            min_n = st.number_input("Nova quantidade mínima para alerta:", min_value=0, step=1)
            
            if st.button("Salvar Novo Limite", use_container_width=True):
                idx = df_p[df_p['nome'] == p_sel_min].index[0]
                df_p.at[idx, 'estoque_minimo'] = min_n
                conn.update(worksheet="produtos", data=df_p)
                st.success(f"Alerta de '{p_sel_min}' atualizado!")
                time.sleep(1); st.rerun()

    # --- RETIRADA DE VENCIDOS (NOVA FUNÇÃO) ---
    with col_inv2:
        with st.container(border=True):
            st.markdown("#### 🗑️ Baixa de Produtos Vencidos")
            # Filtra apenas produtos que têm estoque para retirar
            produtos_com_estoque = df_p[df_p['estoque'] > 0]['nome'].tolist()
            
            p_vencido = st.selectbox("Produto a ser descartado:", [""] + produtos_com_estoque, key="sel_venc")
            qtd_vencida = st.number_input("Quantidade vencida/danificada:", min_value=0, step=1)
            
            if st.button("Confirmar Retirada", use_container_width=True, type="secondary"):
                if p_vencido != "" and qtd_vencida > 0:
                    idx = df_p[df_p['nome'] == p_vencido].index[0]
                    estoque_atual = int(df_p.at[idx, 'estoque'])
                    
                    if qtd_vencida > estoque_atual:
                        st.error(f"Erro: Você está tentando retirar {qtd_vencida}, mas o estoque atual é de apenas {estoque_atual}.")
                    else:
                        with st.spinner("Processando baixa..."):
                            df_p.at[idx, 'estoque'] = estoque_atual - qtd_vencida
                            conn.update(worksheet="produtos", data=df_p)
                            st.warning(f"Baixa realizada: {qtd_vencida} unidade(s) de '{p_vencido}' removidas do estoque.")
                            time.sleep(1.5); st.rerun()
                else:
                    st.info("Selecione um produto e a quantidade para dar baixa.")

    st.markdown("<p style='font-size: 12px; color: gray;'>Dica: Use esta função para registrar perdas, quebras ou produtos que passaram da validade e precisam sair do inventário físico.</p>", unsafe_allow_html=True)

# ==================== 9. CONTABILIDADE (REVISADO E PERSISTENTE) ====================
elif menu == "📂 Contabilidade":
    st.header("📂 Relatório Contábil e Exportação")
    
    # Carrega os dados sempre atualizados
    df_v = carregar_dinamico("vendas")
    df_pts = carregar_estatico("pontos")

    # Seletor de Filtro (Fica sempre visível)
    lista_pdvs = ["Todos"] + df_pts['nome'].tolist()
    f_pdv = st.selectbox("Filtrar relatório por Unidade (PDV):", lista_pdvs)

    if df_v.empty:
        st.info(f"💡 A aba de vendas está vazia no Google Sheets. Realize uma venda no Self-Checkout para gerar dados.")
        
        # Opcional: Criar um botão para visualizar como seria o relatório (apenas visual)
        if st.checkbox("Visualizar exemplo de relatório"):
            exemplo = pd.DataFrame([{"data": "01/01/2026 10:00", "pdv": "Exemplo", "produto": "Item Teste", "valor_bruto": 10.0, "valor_liquido": 9.5, "forma": "Pix"}])
            st.dataframe(exemplo, use_container_width=True)
    else:
        # Aplica o filtro de PDV
        df_f = df_v if f_pdv == "Todos" else df_v[df_v['pdv'] == f_pdv]

        if df_f.empty:
            st.warning(f"Nenhum registro encontrado para a unidade: {f_pdv}")
        else:
            # Exibe Métricas do que foi filtrado
            c1, c2 = st.columns(2)
            c1.metric("Bruto (Filtrado)", f"R$ {pd.to_numeric(df_f['valor_bruto']).sum():,.2f}")
            c2.metric("Líquido (Filtrado)", f"R$ {pd.to_numeric(df_f['valor_liquido']).sum():,.2f}")

            # Tabela de Dados
            st.dataframe(df_f, use_container_width=True, hide_index=True)

            st.divider()

            # Botões de Ação
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                csv = df_f.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📤 EXPORTAR PARA CONTADOR (CSV)",
                    data=csv,
                    file_name=f"contabil_{f_pdv}_{datetime.now().strftime('%m_%Y')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col_btn2:
                if st.button("🖨️ PREPARAR PARA IMPRIMIR", use_container_width=True):
                    st.toast("Use Ctrl+P para imprimir a tela agora!", icon="🖨️")
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
