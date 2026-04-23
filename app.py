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

# ==================== 2. SISTEMA DE LOGIN OTIMIZADO ====================
if not st.session_state.autenticado:
    # Tenta Login Automático via Secrets (Para PDVs Autônomos)
    try:
        auto_user = st.secrets.get("AUTO_LOGIN_USER")
        auto_pass = st.secrets.get("AUTO_LOGIN_PASS")
        
        if auto_user and auto_pass:
            df_pts = carregar_dinamico("pontos")
            if auto_user in df_pts['nome'].values:
                senha_correta = str(df_pts[df_pts['nome'] == auto_user]['senha'].values[0])
                if auto_pass == senha_correta:
                    st.session_state.autenticado = True
                    st.session_state.unidade = auto_user
                    st.session_state.perfil = "pdv"
                    st.rerun()
    except:
        pass # Segue para o login manual se falhar

    # ... (Mantém o formulário de login manual abaixo para administradores)

# ==================== 3. DEFINIÇÃO DO MENU (ESSENCIAL) ====================
# Este bloco cria a variável 'menu' que os IFs abaixo vão usar

st.sidebar.title("⚡ Flash Stop")
st.sidebar.write(f"📍 **{st.session_state.unidade}**")

if st.session_state.perfil == "admin":
    menu = st.sidebar.radio("Navegação", [
 if st.session_state.perfil == "admin":
    menu = st.sidebar.radio("Navegação", [
        "📊 Dashboard", 
        "🛒 Self-Checkout", 
        "📱 Pedidos Online", # Nova aba
        "💰 Entrada Mercadoria", 
        # ... restantes
    ])
else:
    menu = st.sidebar.radio("Navegação", ["🛒 Self-Checkout", "📱 Pedidos Online", "📦 Inventário"])
    st.session_state.autenticado = False
    st.rerun()

# ==================== 4. LÓGICA DE TELAS (O QUE JÁ ESTÁ NO SEU CÓDIGO) ====================

if menu == "📊 Dashboard":
    # Seu código do Dashboard...
    pass

elif menu == "🛒 Self-Checkout":
    # Seu código do Checkout...
    pass

# ==================== NAVEGAÇÃO PRINCIPAL ====================

if menu == "📊 Dashboard":
    # Código do Dashboard
    pass

elif menu == "🛒 Self-Checkout":
    # Código do Checkout
    pass

elif menu == "💰 Entrada Mercadoria":
    # Código de Entrada
    pass

elif menu == "📦 Inventário":
    # Código de Inventário
    pass

# O ERRO ACONTECEU AQUI: Certifique-se de que NÃO existe um "else:" antes desta linha
elif menu == "💸 Despesas":
    st.header("💸 Gestão de Despesas")
    # Código de Despesas
    pass

elif menu == "📂 Contabilidade":
    # Código de Contabilidade
    pass

elif menu == "📟 Configurações":
    # Código de Configurações
    pass

# Opcional: O "else" só pode vir aqui, no final de tudo!
else:
    st.info("Selecione uma opção no menu.")
    
elif menu == "📱 Pedidos Online":
    st.header("📱 Pedidos Recebidos Online")
    
    df_vendas = carregar_dinamico("vendas")
    # Filtra apenas pedidos pendentes da unidade atual
    pedidos_online = df_vendas[(df_vendas['pdv'] == st.session_state.unidade) & 
                               (df_vendas['status'] == 'Pendente')]
    
    if not pedidos_online.empty:
        st.dataframe(pedidos_online, use_container_width=True)
        
        id_pedido = st.selectbox("Selecione o ID do Pedido para Concluir:", pedidos_online.index)
        if st.button("Confirmar Entrega/Retirada"):
            # Atualiza o status na planilha
            df_vendas.at[id_pedido, 'status'] = 'Concluído'
            conn.update(worksheet="vendas", data=df_vendas)
            st.cache_data.clear()
            st.success("Pedido finalizado!")
            st.rerun()
    else:
        st.info("Nenhum pedido online pendente no momento.")

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

# ==================== 5. SELF-CHECKOUT OTIMIZADO ====================
st.markdown(f"""
    <style>
    /* Cor de fundo e texto principal */
    .stApp {{
        background-color: #000000;
        color: #FFFFFF;
    }}
    /* Botões com a cor verde do logo */
    .stButton>button {{
        background-color: #76D72B;
        color: #000000;
        border-radius: 8px;
        font-weight: bold;
        border: none;
    }}
    .stButton>button:hover {{
        background-color: #5eb022;
        color: #FFFFFF;
    }}
    /* Inputs e Selectboxes */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {{
        background-color: #1E1E1E;
        color: #FFFFFF;
    }}
    </style>
""", unsafe_allow_html=True)

    # 1. LOGO COMPACTO
    col_l1, col_l2, col_l3 = st.columns([1.5, 1, 1.5])
    with col_l2:
        try:
            st.image("logo_flash_stop.png", use_container_width=True)
        except:
            st.markdown("<h3 style='text-align: center; color: #2e7d32; margin:0;'>FLASH STOP</h3>", unsafe_allow_html=True)

    # 2. BUSCA AUTOMÁTICA (BIPOU, PASSOU)
    df_p = carregar_dinamico("produtos")
    df_p.columns = df_p.columns.str.strip() # Limpeza de colunas
    
    st.write("")
    # Campo de seleção configurado para focar o leitor
    p_nome = st.selectbox("Aguardando bip ou seleção...", [""] + df_p['nome'].tolist(), key="scanner_input")

    if p_nome:
        dados_p = df_p[df_p['nome'] == p_nome].iloc[0]
        
        # Tentativa de pegar o preço (coluna preco_venda ou preco)
        col_preco = 'preco_venda' if 'preco_venda' in df_p.columns else 'preco'
        preco_unit = float(dados_p[col_preco])
        
        # Adição automática simplificada
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"**{p_nome}**")
        with c2:
            if st.button("➕ ADICIONAR", use_container_width=True, type="primary"):
                st.session_state.carrinho.append({
                    "id": len(st.session_state.carrinho) + 1,
                    "produto": p_nome,
                    "preco": preco_unit
                })
                st.toast("Adicionado!")
                time.sleep(0.4)
                st.rerun()

    st.divider()

    # 3. CARRINHO COMPACTO (PARA CELULAR/MÁQUINA DE CARTÃO)
    if st.session_state.carrinho:
        df_cart = pd.DataFrame(st.session_state.carrinho)
        resumo = df_cart.groupby('produto').agg({'preco': 'first', 'id': 'count'}).rename(columns={'id': 'qtd'}).reset_index()

        for idx, item in resumo.iterrows():
            # Layout em linha única para economizar espaço
            col_txt, col_btns = st.columns([2, 1.5])
            
            with col_txt:
                st.markdown(f"<small>{item['produto']}</small><br><b>R$ {item['preco']*item['qtd']:.2f}</b>", unsafe_allow_html=True)
            
            with col_btns:
                # Botões de + e - em miniatura
                m1, m2, m3 = st.columns([1, 1, 1])
                if m1.button("—", key=f"m_{idx}"):
                    for i, p in enumerate(st.session_state.carrinho):
                        if p['produto'] == item['produto']:
                            st.session_state.carrinho.pop(i)
                            break
                    st.rerun()
                
                m2.markdown(f"<p style='text-align:center; margin-top:5px;'>{item['qtd']}</p>", unsafe_allow_html=True)
                
                if m3.button("＋", key=f"p_{idx}"):
                    st.session_state.carrinho.append({"id":99, "produto":item['produto'], "preco":item['preco']})
                    st.rerun()

        st.divider()
        v_total = df_cart['preco'].sum()
        
        # Finalização
        st.markdown(f"<h3 style='text-align:center;'>Total: R$ {v_total:.2f}</h3>", unsafe_allow_html=True)
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            if st.button("❌ CANCELAR", use_container_width=True):
                st.session_state.carrinho = []
                st.rerun()
        with col_f2:
            if st.button("🚀 PAGAR", use_container_width=True, type="primary"):
                st.success("Processando...")
                st.session_state.carrinho = []
                time.sleep(1.5)
                st.rerun()
    else:
        st.info("Carrinho vazio")

# ==================== 6. GESTÃO DE DESPESAS (CUSTOS FIXOS/VARIÁVEIS) ====================
elif menu == "💸 Despesas":
    st.header("💸 Registro de Custos e Despesas")
    st.info("Lance aqui custos como aluguel, energia, reposição de estoque ou manutenção.")

    try:
        # Carrega a aba de despesas do Sheets
        df_d = carregar_dinamico("despesas")
        
        # Layout em colunas: Esquerda para Cadastro, Direita para Histórico
        col_cadastro, col_historico = st.columns([1, 1.5])
        
        with col_cadastro:
            st.subheader("Registrar Nova Despesa")
            with st.form("form_despesa", clear_on_submit=True):
                descricao = st.text_input("Descrição do Gasto:", placeholder="Ex: Aluguel Unidade X")
                valor_d = st.number_input("Valor (R$):", min_value=0.0, format="%.2f")
                
                # Categoria ajuda na análise do Dashboard futuramente
                categoria = st.selectbox("Categoria:", [
                    "Fixa (Aluguel/Internet)", 
                    "Variável (Energia/Água)", 
                    "Manutenção", 
                    "Impostos/Taxas", 
                    "Compra de Mercadoria",
                    "Outros"
                ])
                
                # Seleção de qual PDV gerou a despesa (importante para sua expansão)
                df_pts = carregar_dinamico("pontos")
                unidade_despesa = st.selectbox("Vincular à Unidade:", ["Geral / Administrativo"] + df_pts['nome'].tolist())
                
                data_venc = st.date_input("Data do Gasto:", value=datetime.now())
                
                if st.form_submit_button("✅ SALVAR DESPESA", use_container_width=True):
                    if descricao and valor_d > 0:
                        nova_linha = {
                            "data": data_venc.strftime("%d/%m/%Y"),
                            "unidade": unidade_despesa,
                            "descricao": descricao,
                            "categoria": categoria,
                            "valor": valor_d
                        }
                        
                        # Concatena e envia para o Google Sheets
                        df_d = pd.concat([df_d, pd.DataFrame([nova_linha])], ignore_index=True)
                        
                        with st.spinner("Atualizando registros..."):
                            conn.update(worksheet="despesas", data=df_d)
                            st.cache_data.clear() # Limpa cache para o Dashboard ler o novo gasto
                            st.success("Despesa registrada com sucesso!")
                            time.sleep(1)
                            st.rerun()
                    else:
                        st.error("Por favor, preencha a descrição e o valor.")

        with col_historico:
            st.subheader("Histórico de Saídas")
            if not df_d.empty:
                # Conversão para garantir soma correta e exibição limpa
                df_d['valor'] = pd.to_numeric(df_d['valor'], errors='coerce')
                
                # Filtro rápido por unidade no histórico
                unidade_filtro = st.multiselect("Filtrar histórico por unidade:", 
                                               options=df_d['unidade'].unique(),
                                               default=df_d['unidade'].unique())
                
                df_filtrado = df_d[df_d['unidade'].isin(unidade_filtro)]
                
                # Exibe a tabela invertida (mais recentes primeiro)
                st.dataframe(
                    df_filtrado.sort_index(ascending=False), 
                    use_container_width=True, 
                    hide_index=True
                )
                
                # Resumo financeiro rápido
                total_gastos = df_filtrado['valor'].sum()
                st.metric("Total no período selecionado", f"R$ {total_gastos:,.2f}")
                
                if st.button("🗑️ Limpar Todo o Histórico (Cuidado!)"):
                    if st.session_state.perfil == "admin":
                        conn.update(worksheet="despesas", data=pd.DataFrame(columns=["data", "unidade", "descricao", "categoria", "valor"]))
                        st.cache_data.clear()
                        st.rerun()
            else:
                st.info("Nenhuma despesa registrada ainda.")

    except Exception as e:
        st.error(f"Erro ao acessar a aba de despesas: {e}")
        st.info("Dica: Certifique-se de que existe uma aba chamada 'despesas' no seu Google Sheets.")

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

# ==================== 9. CONTABILIDADE (RELATÓRIOS E IMPRESSÃO) ====================
elif menu == "📂 Contabilidade":
    st.header("📂 Relatórios Contábeis")
    
    try:
        df_v = carregar_dinamico("vendas")
        
        if not df_v.empty:
            # Filtros por PDV
            lista_pdvs = ["Todos"] + df_v['pdv'].unique().tolist()
            pdv_sel = st.selectbox("Selecione a Unidade para o Relatório:", lista_pdvs)
            
            if pdv_sel != "Todos":
                df_filtrado = df_v[df_v['pdv'] == pdv_sel]
            else:
                df_filtrado = df_v

            # KPIs de Resumo
            bruto = pd.to_numeric(df_filtrado['valor_bruto'], errors='coerce').sum()
            liq = pd.to_numeric(df_filtrado['valor_liquido'], errors='coerce').sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Bruto", f"R$ {bruto:,.2f}")
            c2.metric("Total Líquido", f"R$ {liq:,.2f}")
            c3.metric("Qtd Vendas", len(df_filtrado))

            st.divider()

            # --- BOTÕES DE AÇÃO ---
            col_exp, col_imp = st.columns(2)
            
            with col_exp:
                # 1. BOTÃO DE EXPORTAÇÃO (CSV para Excel)
                csv = df_filtrado.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Exportar para Excel (CSV)",
                    data=csv,
                    file_name=f"vendas_{pdv_sel}_{datetime.now().strftime('%d_%m')}.csv",
                    mime='text/csv',
                    use_container_width=True
                )

            with col_imp:
                # 2. BOTÃO DE IMPRESSÃO (Simulação de Impressão de Relatório)
                # O Streamlit não imprime direto, então criamos um botão que prepara o layout
                if st.button("🖨️ Gerar Relatório para Impressão", use_container_width=True):
                    st.subheader(f"Relatório de Fechamento - {pdv_sel}")
                    st.write(f"Data do Relatório: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                    st.table(df_filtrado[['data', 'produto', 'valor_bruto', 'forma']])
                    st.info("Dica: Pressione Ctrl + P (ou Cmd + P) para imprimir esta página ou salvar como PDF.")
            
            st.divider()
            st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

        else:
            st.info("Sem dados de vendas para exibir.")

    except Exception as e:
        st.error(f"Erro ao gerar relatórios: {e}")

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
