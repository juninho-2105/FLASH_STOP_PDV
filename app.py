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

# ==================== 5. SELF-CHECKOUT (BIPOU + MANUAL) ====================
elif menu == "🛒 Self-Checkout":
    hora_atual = datetime.now().hour
    if hora_atual < 12: saudacao = "Bom dia"
    elif hora_atual < 18: saudacao = "Boa tarde"
    else: saudacao = "Boa noite"

    st.header(f"🛒 {saudacao}! Bem-vindo à Flash Stop")
    
    try:
        # Busca produtos (usando o cache para evitar erro 429)
        df_p = carregar_dinamico("produtos")
        
        col_esq, col_dir = st.columns([1.2, 1.3])

        with col_esq:
            # Criamos duas abas para o cliente escolher o modo de entrada
            aba_scan, aba_manual = st.tabs(["📟 BIPAR PRODUTO", "🔍 BUSCA MANUAL"])
            
            prods_ativos = df_p[df_p['estoque'].astype(int) > 0]
            lista_nomes = [""] + prods_ativos['nome'].tolist()

            # --- MODO 1: SCANNER (BIPOU-ENTROU) ---
            with aba_scan:
                sel_scan = st.selectbox("Aponte o leitor:", lista_nomes, key="scan_input")
                if sel_scan:
                    d = df_p[df_p['nome'] == sel_scan].iloc[0]
                    preco_unit = float(d['preco'])
                    
                    # Lógica de somar ao carrinho
                    item_existente = False
                    for idx, item in enumerate(st.session_state.carrinho):
                        if item['item'] == sel_scan:
                            st.session_state.carrinho[idx]['qtd'] += 1
                            st.session_state.carrinho[idx]['total'] = st.session_state.carrinho[idx]['qtd'] * preco_unit
                            item_existente = True
                            break
                    
                    if not item_existente:
                        st.session_state.carrinho.append({"item": sel_scan, "qtd": 1, "preco": preco_unit, "total": preco_unit})
                    
                    st.toast(f"✅ {sel_scan} adicionado!")
                    time.sleep(0.3)
                    st.rerun()

            # --- MODO 2: MANUAL (PESQUISA + BOTÃO) ---
            with aba_manual:
                sel_man = st.selectbox("Procure o produto pelo nome:", lista_nomes, key="man_input")
                if sel_man:
                    d_man = df_p[df_p['nome'] == sel_man].iloc[0]
                    st.write(f"Preço Unitário: **R$ {float(d_man['preco']):.2f}**")
                    qtd_man = st.number_input("Quantidade:", min_value=1, max_value=int(d_man['estoque']), value=1, key="qtd_man")
                    
                    if st.button("➕ ADICIONAR MANUALMENTE", use_container_width=True):
                        preco_unit_man = float(d_man['preco'])
                        
                        item_existente = False
                        for idx, item in enumerate(st.session_state.carrinho):
                            if item['item'] == sel_man:
                                st.session_state.carrinho[idx]['qtd'] += qtd_man
                                st.session_state.carrinho[idx]['total'] = st.session_state.carrinho[idx]['qtd'] * preco_unit_man
                                item_existente = True
                                break
                        
                        if not item_existente:
                            st.session_state.carrinho.append({"item": sel_man, "qtd": qtd_man, "preco": preco_unit_man, "total": preco_unit_man * qtd_man})
                        
                        st.success(f"{sel_man} adicionado!")
                        time.sleep(0.5)
                        st.rerun()

        with col_dir:
            st.subheader("🛍️ Seu Carrinho")
            if st.session_state.carrinho:
                v_total_compra = 0
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

                st.divider()
                st.markdown(f"## TOTAL: R$ {v_total_compra:.2f}")

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
                            agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                            v_novas = []
                            for it in st.session_state.carrinho:
                                v_liq = it['total'] * 0.97 
                                v_novas.append({
                                    "data": agora, "pdv": st.session_state.unidade, "produto": it['item'],
                                    "valor_bruto": it['total'], "valor_liquido": v_liq, "forma": forma
                                })
                                idx_est = df_p[df_p['nome'] == it['item']].index[0]
                                df_p.at[idx_est, 'estoque'] = int(df_p.at[idx_est, 'estoque']) - it['qtd']
                            
                            df_v_atual = carregar_dinamico("vendas")
                            conn.update(worksheet="vendas", data=pd.concat([df_v_atual, pd.DataFrame(v_novas)], ignore_index=True))
                            conn.update(worksheet="produtos", data=df_p)
                            st.cache_data.clear()
                            st.session_state.carrinho = []
                            st.success("Obrigado!")
                            st.balloons()
                            time.sleep(3)
                            st.rerun()
            else:
                st.info("Escolha uma opção ao lado para começar.")
    
    except Exception as e:
        if "429" in str(e):
            st.warning("Aguarde alguns segundos (limite de tráfego)...")
        else:
            st.error(f"Erro: {e}")

# ==================== 6. GESTÃO DE DESPESAS (CUSTOS FIXOS) ====================
elif menu == "💸 Despesas":
    st.header("💸 Registro de Custos e Despesas")
    
    try:
        # Carrega a aba de despesas do Sheets
        df_d = carregar_dinamico("despesas")
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("Registrar Nova")
            with st.form("form_despesa", clear_on_submit=True):
                descricao = st.text_input("Descrição (ex: Aluguel, Internet, Luz):")
                valor_d = st.number_input("Valor (R$):", min_value=0.0, format="%.2f")
                categoria = st.selectbox("Categoria:", ["Fixo", "Variável", "Manutenção", "Impostos", "Outros"])
                data_venc = st.date_input("Data do Gasto:")
                
                if st.form_submit_button("SALVAR DESPESA"):
                    if descricao and valor_d > 0:
                        nova_linha = {
                            "data": data_venc.strftime("%d/%m/%Y"),
                            "descricao": descricao,
                            "categoria": categoria,
                            "valor": valor_d
                        }
                        # Adiciona ao DataFrame existente
                        df_d = pd.concat([df_d, pd.DataFrame([nova_linha])], ignore_index=True)
                        
                        with st.spinner("Salvando..."):
                            conn.update(worksheet="despesas", data=df_d)
                            st.cache_data.clear() # Limpa cache para atualizar o Dashboard
                            st.success("Despesa registrada com sucesso!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.warning("Preencha a descrição e o valor.")

        with col2:
            st.subheader("Histórico de Gastos")
            if not df_d.empty:
                # Converte para número para garantir a soma correta
                df_d['valor'] = pd.to_numeric(df_d['valor'], errors='coerce')
                
                # Exibe a tabela
                st.dataframe(df_d.sort_index(ascending=False), use_container_width=True, hide_index=True)
                
                total_gastos = df_d['valor'].sum()
                st.metric("Total Acumulado em Despesas", f"R$ {total_gastos:,.2f}")
            else:
                st.info("Nenhuma despesa registrada ainda.")

    except Exception as e:
        st.error(f"Erro ao acessar despesas: {e}")

# ==================== 7. ENTRADA E CADASTRO (COM CÁLCULO DINÂMICO) ====================
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Gestão de Estoque e Preços")
    
    try:
        df_p = carregar_dinamico("produtos")
        tipo_acao = st.radio("O que deseja fazer?", ["Repor Estoque Existente", "Cadastrar Novo Produto"], horizontal=True)

        if tipo_acao == "Repor Estoque Existente":
            # 1. Seleção (Fora do form para atualizar os dados da tela)
            prod_sel = st.selectbox("Selecione o produto:", df_p['nome'].tolist())
            dados = df_p[df_p['nome'] == prod_sel].iloc[0]
            
            # 2. Entradas de valores para cálculo
            c1, c2, c3 = st.columns(3)
            with c1:
                qtd_inc = st.number_input("Quantidade que chegou:", min_value=1, step=1)
            with c2:
                custo = st.number_input("Custo Unitário (R$):", min_value=0.0, format="%.2f", key="custo_repo")
            with c3:
                margem = st.number_input("Margem de Lucro (%):", min_value=0.0, value=30.0, key="margem_repo")

            # CÁLCULO DINÂMICO (Aparece na hora)
            preco_sugerido = custo * (1 + (margem / 100))
            
            st.markdown(f"""
            <div style="background-color:#f0f2f6;padding:15px;border-radius:10px;border-left:5px solid #2e7d32">
                <strong>Sugestão de Venda:</strong> R$ {preco_sugerido:.2f}<br>
                <small>Estoque Atual: {dados['estoque']} | Novo Estoque: {int(dados['estoque']) + qtd_inc}</small>
            </div>
            """, unsafe_allow_html=True)

            # 3. Botão de confirmação
            preco_final = st.number_input("Preço Final que será aplicado (R$):", value=preco_sugerido, format="%.2f")
            
            if st.button("🚀 ATUALIZAR PRODUTO NO SISTEMA", use_container_width=True):
                idx = df_p[df_p['nome'] == prod_sel].index[0]
                df_p.at[idx, 'estoque'] = int(df_p.at[idx, 'estoque']) + qtd_inc
                df_p.at[idx, 'preco'] = preco_final
                
                with st.spinner("Salvando..."):
                    conn.update(worksheet="produtos", data=df_p)
                    st.cache_data.clear()
                    st.success(f"Estoque e Preço de {prod_sel} atualizados!")
                    time.sleep(1.5)
                    st.rerun()

        else:
            # --- CADASTRO DE NOVO PRODUTO ---
            st.subheader("Novo Cadastro")
            nome_n = st.text_input("Nome do Produto:")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                estoque_n = st.number_input("Estoque Inicial:", min_value=0, step=1)
            with c2:
                custo_n = st.number_input("Custo Unitário (R$):", min_value=0.0, format="%.2f")
            with c3:
                margem_n = st.number_input("Margem de Lucro (%):", min_value=0.0, value=30.0)
            
            # Cálculo automático
            venda_n = custo_n * (1 + (margem_n / 100))
            st.info(f"O preço de venda calculado é: **R$ {venda_n:.2f}**")
            
            preco_venda_final = st.number_input("Preço de Venda Final (ajuste se necessário):", value=venda_n, format="%.2f")

            if st.button("➕ CADASTRAR NOVO PRODUTO", use_container_width=True):
                if not nome_n:
                    st.error("Digite o nome do produto!")
                else:
                    novo_item = {
                        "nome": nome_n,
                        "estoque": estoque_n,
                        "estoque_minimo": 5,
                        "preco": preco_venda_final,
                        "validade": ""
                    }
                    # Adiciona e salva
                    df_novo = pd.concat([df_p, pd.DataFrame([novo_item])], ignore_index=True)
                    conn.update(worksheet="produtos", data=df_novo)
                    st.cache_data.clear()
                    st.success("Produto cadastrado!")
                    time.sleep(1.5)
                    st.rerun()

    except Exception as e:
        st.error(f"Erro na operação: {e}")

# ==================== 8. INVENTÁRIO (COM LIMPEZA DE VENCIDOS) ====================
elif menu == "📦 Inventário":
    st.header("📦 Gestão de Itens e Saneamento")
    
    df_p = carregar_dinamico("produtos")
    hoje = datetime.now()

    if not df_p.empty:
        tab_geral, tab_vencidos = st.tabs(["📋 Estoque Geral", "⚠️ Produtos Vencidos"])

        with tab_geral:
            st.subheader("Configurar Alerta de Estoque Mínimo")
            with st.form("f_inventario"):
                col_sel, col_qtd = st.columns([2, 1])
                p_sel = col_sel.selectbox("Selecione o Produto:", df_p['nome'].tolist())
                # Busca o valor atual para mostrar como padrão
                val_atual = int(df_p[df_p['nome'] == p_sel]['estoque_minimo'].values[0])
                n_min = col_qtd.number_input("Novo Limite Mínimo:", min_value=0, value=val_atual)
                
                if st.form_submit_button("Atualizar Limite de Segurança", use_container_width=True):
                    idx = df_p[df_p['nome'] == p_sel].index[0]
                    df_p.at[idx, 'estoque_minimo'] = n_min
                    conn.update(worksheet="produtos", data=df_p)
                    st.cache_data.clear()
                    st.success("Limite atualizado!")
                    st.rerun()

            st.divider()
            st.dataframe(df_p, use_container_width=True, hide_index=True)

        with tab_vencidos:
            st.subheader("Produtos com Data de Validade Ultrapassada")
            
            # Lógica para identificar vencidos
            vencidos_indices = []
            for idx, r in df_p.iterrows():
                try:
                    dt_val = datetime.strptime(str(r['validade']), "%d/%m/%Y")
                    if dt_val < hoje:
                        vencidos_indices.append(idx)
                except:
                    continue # Ignora se a data estiver vazia ou em formato errado

            if vencidos_indices:
                df_vencidos = df_p.loc[vencidos_indices]
                st.warning(f"Foram encontrados {len(df_vencidos)} produtos vencidos.")
                st.dataframe(df_vencidos[['nome', 'estoque', 'validade']], use_container_width=True)

                col_exc1, col_exc2 = st.columns(2)
                
                if col_exc1.button("🗑️ EXCLUIR TODOS OS VENCIDOS", type="primary", use_container_width=True):
                    # Remove as linhas do DataFrame
                    df_p_limpo = df_p.drop(vencidos_indices)
                    conn.update(worksheet="produtos", data=df_p_limpo)
                    st.cache_data.clear()
                    st.success("Todos os produtos vencidos foram removidos do sistema!")
                    time.sleep(1.5)
                    st.rerun()
                
                with col_exc2:
                    p_para_excluir = st.selectbox("Excluir item específico:", [""] + df_vencidos['nome'].tolist())
                    if st.button("Excluir Selecionado"):
                        if p_para_excluir:
                            df_p_limpo = df_p[df_p['nome'] != p_para_excluir]
                            conn.update(worksheet="produtos", data=df_p_limpo)
                            st.cache_data.clear()
                            st.success(f"{p_para_excluir} removido!")
                            time.sleep(1)
                            st.rerun()
            else:
                st.success("Excelente! Não há produtos vencidos no sistema.")

    else:
        st.warning("Nenhum produto cadastrado.")

# ==================== 9. CONTABILIDADE ====================
elif menu == "📂 Contabilidade":
    st.header("📂 Relatórios Contábeis")
    df_v = carregar_dinamico("vendas")
    st.download_button("Baixar Relatório de Vendas (CSV)", df_v.to_csv(index=False), "vendas.csv")
    st.dataframe(df_v, use_container_width=True)

# ==================== 10. CONFIGURAÇÕES (PDVs E TAXAS) ====================
elif menu == "📟 Configurações":
    st.header("📟 Gestão Operacional")
    
    aba_pdv, aba_maquinas = st.tabs(["📍 Pontos de Venda (PDVs)", "💳 Máquinas e Taxas"])

    with aba_pdv:
        st.subheader("Gestão de Acessos")
        df_pts = carregar_dinamico("pontos")
        
        with st.form("novo_p"):
            n = st.text_input("Nome da Unidade (ex: Condomínio Alpha)")
            s = st.text_input("Senha de Acesso")
            if st.form_submit_button("Cadastrar Unidade"):
                if n and s:
                    novo = pd.DataFrame([{"nome": n, "senha": s}])
                    conn.update(worksheet="pontos", data=pd.concat([df_pts, novo], ignore_index=True))
                    st.cache_data.clear()
                    st.success("Unidade cadastrada!")
                    st.rerun()
        
        st.dataframe(df_pts, use_container_width=True, hide_index=True)

    with aba_maquinas:
        st.subheader("Configuração de Operadoras de Pagamento")
        st.info("As taxas abaixo serão usadas para calcular o lucro líquido real de cada venda.")
        
        try:
            df_maq = carregar_dinamico("maquinas")
        except:
            # Estrutura com taxas separadas
            df_maq = pd.DataFrame(columns=["maquina", "taxa_pix", "taxa_debito", "taxa_credito"])

        with st.form("nova_maquina"):
            nome_m = st.text_input("Nome da Operadora/Máquina (ex: Stone, Mercado Pago):")
            
            c1, c2, c3 = st.columns(3)
            t_pix = c1.number_input("Taxa Pix (%)", min_value=0.0, value=0.0, step=0.01)
            t_deb = c2.number_input("Taxa Débito (%)", min_value=0.0, value=1.99, step=0.01)
            t_cre = c3.number_input("Taxa Crédito (%)", min_value=0.0, value=3.49, step=0.01)
            
            if st.form_submit_button("🚀 SALVAR CONFIGURAÇÃO DE TAXAS"):
                if nome_m:
                    nova_config = pd.DataFrame([{
                        "maquina": nome_m, 
                        "taxa_pix": t_pix, 
                        "taxa_debito": t_deb, 
                        "taxa_credito": t_cre
                    }])
                    # Atualiza ou adiciona
                    df_maq_final = pd.concat([df_maq, nova_config], ignore_index=True)
                    conn.update(worksheet="maquinas", data=df_maq_final)
                    st.cache_data.clear()
                    st.success(f"Taxas da {nome_m} configuradas!")
                    time.sleep(1)
                    st.rerun()

        if not df_maq.empty:
            st.divider()
            st.write("### Taxas Ativas")
            # Exibe com formatação de porcentagem
            st.dataframe(df_maq, use_container_width=True, hide_index=True)
