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

# ==================== 5. SELF-CHECKOUT (COM SAUDAÇÃO E CANCELAR) ====================
elif menu == "🛒 Self-Checkout":
    # --- LÓGICA DE SAUDAÇÃO POR HORÁRIO ---
    hora_atual = datetime.now().hour
    if hora_atual < 12:
        saudacao = "Bom dia"
    elif hora_atual < 18:
        saudacao = "Boa tarde"
    else:
        saudacao = "Boa noite"

    st.header(f"🛒 {saudacao}! Bem-vindo à Flash Stop")
    st.info(f"📍 Unidade: {st.session_state.unidade}")

    try:
        df_p = carregar_dinamico("produtos")
        
        col_esq, col_dir = st.columns([1.5, 1])

        with col_esq:
            st.subheader("Selecione os Produtos")
            prods_ativos = df_p[df_p['estoque'].astype(int) > 0]
            lista_nomes = [""] + prods_ativos['nome'].tolist()
            
            sel = st.selectbox("Busque o produto ou bipe o código:", lista_nomes, key="sel_prod")
            
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
            if st.session_state.carrinho:
                v_total = 0
                for item in st.session_state.carrinho:
                    v_total += item['total']
                    st.write(f"**{item['qtd']}x** {item['item']} — R$ {item['total']:.2f}")
                
                st.markdown(f"## TOTAL: R$ {v_total:.2f}")
                
                # --- OPÇÕES DE CANCELAR OU FINALIZAR ---
                c1, c2 = st.columns(2)
                
                with c1:
                    if st.button("❌ CANCELAR COMPRA", use_container_width=True):
                        st.session_state.carrinho = []
                        st.warning("Compra cancelada e carrinho limpo.")
                        time.sleep(1)
                        st.rerun()
                
                with c2:
                    # O botão de finalizar fica em destaque (primary)
                    finalizar = st.button("✅ IR PARA PAGAMENTO", type="primary", use_container_width=True)

                if finalizar:
                    st.divider()
                    forma = st.radio("Escolha a forma de pagamento na maquininha:", ["Pix", "Débito", "Crédito"], horizontal=True)
                    
                    if st.button("CONFIRMAR PAGAMENTO", use_container_width=True):
                        with st.spinner("Finalizando sua compra..."):
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
                            st.success(f"Obrigado pela compra! Tenha um ótimo dia.")
                            st.balloons()
                            time.sleep(3)
                            st.rerun()
            else:
                st.info("Seu carrinho está vazio. Comece selecionando um produto ao lado.")
    except Exception as e:
        st.error(f"Erro no Checkout: {e}")

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
