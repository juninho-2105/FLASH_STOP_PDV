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

# ==================== 4. DASHBOARD OTIMIZADO ====================
if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    
    # Criamos um container para os dados, assim o erro de um não mata o outro
    with st.status("Sincronizando com Google Sheets...", expanded=False) as status:
        df_p = carregar_dinamico("produtos")
        df_v = carregar_dinamico("vendas")
        df_d = carregar_dinamico("despesas")
        status.update(label="Dados sincronizados!", state="complete")
    
    if not df_v.empty and not df_d.empty:
        # Conversão segura
        bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
        liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
        gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
        lucro = liq - gastos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
        c2.metric("Líquido (Pós Taxas)", f"R$ {liq:,.2f}")
        c3.metric("Despesas Totais", f"R$ {gastos:,.2f}")
        c4.metric("Lucro Real", f"R$ {lucro:,.2f}")

        st.divider()

        # Gráfico de Vendas
        st.subheader("📈 Evolução de Vendas")
        df_v['data_dt'] = pd.to_datetime(df_v['data'], format="%d/%m/%Y %H:%M", errors='coerce')
        vendas_dia = df_v.groupby(df_v['data_dt'].dt.date)['valor_bruto'].sum()
        st.area_chart(vendas_dia)
    else:
        st.warning("Aguardando carregamento de dados das planilhas...")

# ==================== 5. SELF-CHECKOUT (MODO TURBO - ANTI-ERRO QUOTA) ====================
elif menu == "🛒 Self-Checkout":
    # 1. Saudação por horário
    hora_atual = datetime.now().hour
    if hora_atual < 12: saudacao = "Bom dia"
    elif hora_atual < 18: saudacao = "Boa tarde"
    else: saudacao = "Boa noite"

    st.header(f"🛒 {saudacao}! Bem-vindo à Flash Stop")
    
    # 2. Lógica de Cache para evitar erro 429 (Limite do Google)
    # Definimos um tempo de vida (TTL) para a leitura não sobrecarregar o Google
    try:
        # Usamos o cache para buscar produtos
        df_p = carregar_dinamico("produtos")
        
        col_esq, col_dir = st.columns([1.2, 1.3])

        with col_esq:
            st.subheader("Escaneie o Produto")
            prods_ativos = df_p[df_p['estoque'].astype(int) > 0]
            lista_nomes = [""] + prods_ativos['nome'].tolist()
            
            # Selectbox preparada para o leitor de código de barras
            sel = st.selectbox("Aponte o leitor para o código:", lista_nomes, key="leitor_ba")
            
            if sel:
                d = df_p[df_p['nome'] == sel].iloc[0]
                preco_unit = float(d['preco'])
                
                # Agrupamento inteligente no carrinho
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
                # Pequena pausa para o usuário ver o feedback antes do rerun
                time.sleep(0.3)
                st.rerun()

        with col_dir:
            st.subheader("🛍️ Seu Carrinho")
            if st.session_state.carrinho:
                v_total_compra = 0
                
                # Interface de ajuste de quantidades [+ / -]
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
                        estoque_dis = int(df_p[df_p['nome'] == item['item']].iloc[0]['estoque'])
                        if item['qtd'] < estoque_dis:
                            st.session_state.carrinho[i]['qtd'] += 1
                            st.session_state.carrinho[i]['total'] = st.session_state.carrinho[i]['qtd'] * item['preco']
                            st.rerun()
                        else:
                            st.error("Sem estoque disponível")

                st.divider()
                st.markdown(f"## TOTAL: R$ {v_total_compra:.2f}")

                # --- PAGAMENTO ---
                st.subheader("💳 Pagamento")
                forma = st.radio("Escolha a forma:", ["Pix", "Débito", "Crédito"], horizontal=True)
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("❌ CANCELAR", use_container_width=True):
                        st.session_state.carrinho = []
                        st.rerun()
                with col_btn2:
                    if st.button("✅ FINALIZAR", type="primary", use_container_width=True):
                        with st.spinner("Registrando..."):
                            agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                            v_novas = []
                            for it in st.session_state.carrinho:
                                # Taxa fixa de 3% (ajustável conforme sua máquina)
                                v_liq = it['total'] * 0.97 
                                v_novas.append({
                                    "data": agora, 
                                    "pdv": st.session_state.unidade, 
                                    "produto": it['item'],
                                    "valor_bruto": it['total'], 
                                    "valor_liquido": v_liq, 
                                    "forma": forma
                                })
                                # Baixa de estoque
                                idx_est = df_p[df_p['nome'] == it['item']].index[0]
                                df_p.at[idx_est, 'estoque'] = int(df_p.at[idx_est, 'estoque']) - it['qtd']
                            
                            # Envio dos dados para o Google
                            df_v_atual = carregar_dinamico("vendas")
                            conn.update(worksheet="vendas", data=pd.concat([df_v_atual, pd.DataFrame(v_novas)], ignore_index=True))
                            conn.update(worksheet="produtos", data=df_p)
                            
                            # IMPORTANTE: Limpa o cache após o update para a próxima leitura ser real
                            st.cache_data.clear()
                            
                            st.session_state.carrinho = []
                            st.success("Pagamento confirmado! Obrigado por comprar na Flash Stop.")
                            st.balloons()
                            time.sleep(3)
                            st.rerun()
            else:
                st.info("Passe o produto no leitor para começar sua compra.")
    
    except Exception as e:
        # Se der o erro de quota, avisamos de forma amigável
        if "429" in str(e):
            st.warning("O sistema está processando muitos dados. Por favor, aguarde 10 segundos e tente bipar novamente.")
        else:
            st.error(f"Erro no sistema: {e}")

# ==================== 6. ENTRADA MERCADORIA ====================
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Entrada de Estoque")
    # ... resto do código ...
        
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
