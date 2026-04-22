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

# ==================== 4. DASHBOARD (FINANCEIRO E ALERTAS) ====================
if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    
    # Carregamento de dados
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_p = carregar_dinamico("produtos")
    
    # --- BLOCO DE KPIs ---
    bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
    liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
    gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
    lucro = liq - gastos

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
    c2.metric("Líquido (Pós Taxas)", f"R$ {liq:,.2f}")
    c3.metric("Despesas Totais", f"R$ {gastos:,.2f}")
    c4.metric("Lucro Real", f"R$ {lucro:,.2f}", delta=f"{lucro/bruto*100:.1f}%" if bruto > 0 else None)

    st.divider()

    # --- GRÁFICO DE VENDAS ---
    st.subheader("📈 Evolução de Vendas")
    if not df_v.empty:
        try:
            # Converte a data para gráfico
            df_v['data_dt'] = pd.to_datetime(df_v['data'], format="%d/%m/%Y %H:%M", errors='coerce')
            vendas_dia = df_v.groupby(df_v['data_dt'].dt.date)['valor_bruto'].sum()
            st.area_chart(vendas_dia)
        except:
            st.info("Aguardando mais dados para gerar o gráfico.")

    st.divider()

    # --- BLOCO DE ALERTAS ---
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("🚨 Reposição (Estoque Crítico)")
        # Filtra produtos onde estoque atual é menor ou igual ao mínimo
        critico = df_p[df_p['estoque'].astype(int) <= df_p['estoque_minimo'].astype(int)]
        if not critico.empty:
            st.dataframe(critico[['nome', 'estoque', 'estoque_minimo']], 
                         hide_index=True, use_container_width=True)
        else:
            st.success("Estoque abastecido em todas as unidades!")

    with col_b:
        st.subheader("📅 Alertas de Validade (15 dias)")
        vencendo = []
        hoje = datetime.now()
        for _, r in df_p.iterrows():
            try:
                # Converte a data da planilha para comparar
                dt_val = datetime.strptime(str(r['validade']), "%d/%m/%Y")
                if dt_val <= hoje + timedelta(days=15):
                    status = "VENCIDO" if dt_val < hoje else "Vence em breve"
                    vencendo.append({
                        "Produto": r['nome'], 
                        "Qtd": r['estoque'], 
                        "Data": r['validade'],
                        "Status": status
                    })
            except:
                continue
        
        if vencendo:
            st.dataframe(pd.DataFrame(vencendo), hide_index=True, use_container_width=True)
        else:
            st.success("Nenhum produto próximo ao vencimento!")

# ==================== 5. SELF-CHECKOUT (BIPOU-ENTROU + AJUSTE DE QTD) ====================
elif menu == "🛒 Self-Checkout":
    # Saudação por horário
    hora_atual = datetime.now().hour
    if hora_atual < 12: saudacao = "Bom dia"
    elif hora_atual < 18: saudacao = "Boa tarde"
    else: saudacao = "Boa noite"

    st.header(f"🛒 {saudacao}! Bem-vindo à Flash Stop")
    
    try:
        df_p = carregar_dinamico("produtos")
        col_esq, col_dir = st.columns([1.2, 1.3])

        with col_esq:
            st.subheader("Escaneie o Produto")
            prods_ativos = df_p[df_p['estoque'].astype(int) > 0]
            lista_nomes = [""] + prods_ativos['nome'].tolist()
            
            # Campo de entrada para o leitor de código de barras
            sel = st.selectbox("Aponte o leitor para o código:", lista_nomes, key="leitor_ba")
            
            if sel:
                d = df_p[df_p['nome'] == sel].iloc[0]
                preco_unit = float(d['preco'])
                
                # Verifica se o item já está no carrinho para apenas somar a quantidade
                item_no_carrinho = False
                for idx, item in enumerate(st.session_state.carrinho):
                    if item['item'] == sel:
                        st.session_state.carrinho[idx]['qtd'] += 1
                        st.session_state.carrinho[idx]['total'] = st.session_state.carrinho[idx]['qtd'] * preco_unit
                        item_no_carrinho = True
                        break
                
                if not item_no_carrinho:
                    st.session_state.carrinho.append({
                        "item": sel, "qtd": 1, "preco": preco_unit, "total": preco_unit
                    })
                
                st.toast(f"✅ {sel} adicionado!")
                time.sleep(0.3)
                st.rerun()

        with col_dir:
            st.subheader("🛍️ Seu Carrinho")
            if st.session_state.carrinho:
                v_total_compra = 0
                
                # Exibe cada item com botões de controle
                for i, item in enumerate(st.session_state.carrinho):
                    v_total_compra += item['total']
                    c_nome, c_menos, c_qtd, c_mais = st.columns([3, 1, 1, 1])
                    
                    c_nome.write(f"**{item['item']}**\n(R$ {item['preco']:.2f})")
                    
                    if c_menos.button("➖", key=f"min_{i}"):
                        if item['qtd'] > 1:
                            st.session_state.carrinho[i]['qtd'] -= 1
                            st.session_state.carrinho[i]['total'] = st.session_state.carrinho[i]['qtd'] * item['preco']
                        else:
                            st.session_state.carrinho.pop(i)
                        st.rerun()
                        
                    c_qtd.write(f"**{item['qtd']}**")
                    
                    if c_mais.button("➕", key=f"add_{i}"):
                        # Verifica estoque antes de somar
                        estoque_disponivel = int(df_p[df_p['nome'] == item['item']].iloc[0]['estoque'])
                        if item['qtd'] < estoque_disponivel:
                            st.session_state.carrinho[i]['qtd'] += 1
                            st.session_state.carrinho[i]['total'] = st.session_state.carrinho[i]['qtd'] * item['preco']
                            st.rerun()
                        else:
                            st.error("Limite de estoque atingido.")

                st.divider()
                st.markdown(f"## TOTAL: R$ {v_total_compra:.2f}")

                # --- PAGAMENTO E CANCELAMENTO ---
                st.subheader("💳 Pagamento")
                forma = st.radio("Escolha a forma:", ["Pix", "Débito", "Crédito"], horizontal=True)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("❌ CANCELAR", use_container_width=True):
                        st.session_state.carrinho = []
                        st.rerun()
                with col_btn2:
                    if st.button("✅ FINALIZAR", type="primary", use_container_width=True):
                        with st.spinner("Finalizando..."):
                            # Lógica de salvamento idêntica à anterior
                            agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                            v_novas = []
                            for it in st.session_state.carrinho:
                                v_liq = it['total'] * 0.97
                                v_novas.append({
                                    "data": agora, "pdv": st.session_state.unidade, "produto": it['item'],
                                    "valor_bruto": it['total'], "valor_liquido": v_liq, "forma": forma
                                })
                                idx_estoque = df_p[df_p['nome'] == it['item']].index[0]
                                df_p.at[idx_estoque, 'estoque'] = int(df_p.at[idx_estoque, 'estoque']) - it['qtd']
                            
                            df_v_atual = carregar_dinamico("vendas")
                            conn.update(worksheet="vendas", data=pd.concat([df_v_atual, pd.DataFrame(v_novas)], ignore_index=True))
                            conn.update(worksheet="produtos", data=df_p)
                            
                            st.session_state.carrinho = []
                            st.success("Obrigado! Tenha um excelente dia.")
                            st.balloons()
                            time.sleep(3)
                            st.rerun()
            else:
                st.info("Passe o produto no leitor para começar.")
        
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
