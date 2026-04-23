import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time
import streamlit as st
import pandas as pd
import time

# 1. SEMPRE A PRIMEIRA CONFIGURAÇÃO
st.set_page_config(page_title="Flash Stop", layout="wide")

# 2. DEFINA AS FUNÇÕES NO TOPO
@st.cache_data(ttl=60) # Isso faz o app carregar rápido
def carregar_dinamico(aba):
    # Aqui usamos a conexão com o Google Sheets que você já tem
    try:
        # Se você estiver usando st.connection:
        return conn.read(worksheet=aba)
    except NameError:
        st.error("A variável 'conn' (conexão) não foi definida antes da função!")
        return pd.DataFrame()


# ==================== 3. DEFINIÇÃO DO MENU (ESSENCIAL) ====================
# Este bloco cria a variável 'menu' que os IFs abaixo vão usar

st.sidebar.title("⚡ Flash Stop")
st.sidebar.write(f"📍 **{st.session_state.unidade}**")

if st.session_state.perfil == "admin":
    menu = st.sidebar.radio("Navegação", [
        "📊 Dashboard", 
        "🛒 Self-Checkout", 
        "💰 Entrada Mercadoria", 
        "📦 Inventário", 
        "💸 Despesas",
        "📂 Contabilidade", 
        "📟 Configurações"
    ])
else:
    # Perfil PDV (Totem do condomínio) só vê o Checkout e Inventário
    menu = st.sidebar.radio("Navegação", ["🛒 Self-Checkout", "📦 Inventário"])

st.sidebar.divider()

# BOTÃO SAIR
if st.sidebar.button("🚪 Sair / Trocar Usuário"):
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

# ==================== 5. SELF-CHECKOUT PROFISSIONAL V3 ====================
elif menu == "🛒 Self-Checkout":
    # Configuração de estilo para evitar cortes e centralizar botões
    st.markdown("""
        <style>
        .block-container { 
            padding-top: 1rem !important; 
            max-width: 100% !important; 
        }
        .main-title {
            text-align: center; 
            color: #2e7d32; 
            font-size: 30px; 
            font-weight: bold;
            margin-bottom: 20px;
        }
        /* Estilo para os botões de ação final ficarem centralizados */
        .div-botoes {
            display: flex;
            flex-direction: column;
            align-items: center;
            width: 100%;
        }
        .stButton button {
            width: 100%;
            max-width: 450px; /* Largura ideal para celular e tablet */
            height: 3.5rem;
            font-size: 18px;
            font-weight: bold;
            border-radius: 12px;
        }
        /* Card de produto */
        .product-card {
            background-color: #ffffff;
            border-left: 6px solid #2e7d32;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
            margin-bottom: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="main-title">FLASH STOP</div>', unsafe_allow_html=True)

    # 1. ENTRADA DE PRODUTOS (BIP OU SELEÇÃO)
    df_p = carregar_dinamico("produtos")
    
    # Criamos uma linha para o seletor e o botão
    c_input, c_add = st.columns([3, 1])
    
    with c_input:
        # O segredo do 'Bip' é o selectbox permitir a busca por texto
        p_selecionado = st.selectbox(
            "Bipe o código ou digite o nome:",
            options=[""] + df_p['nome'].tolist(),
            format_func=lambda x: "Aguardando bip ou seleção..." if x == "" else x,
            label_visibility="collapsed"
        )

    with c_add:
        if st.button("➕ ADD", type="primary", key="add_manual"):
            if p_selecionado:
                dados_p = df_p[df_p['nome'] == p_selecionado].iloc[0]
                # Verifica se a coluna é 'preco_venda' ou 'preco'
                p_col = 'preco_venda' if 'preco_venda' in df_p.columns else 'preco'
                st.session_state.carrinho.append({
                    "id": time.time(), 
                    "produto": p_selecionado, 
                    "preco": float(dados_p[p_col])
                })
                st.rerun()

    st.divider()

    # 2. LISTAGEM DO CARRINHO (ESTILO CARD)
    if st.session_state.carrinho:
        df_cart = pd.DataFrame(st.session_state.carrinho)
        resumo = df_cart.groupby('produto').agg({'preco': 'first', 'id': 'count'}).rename(columns={'id': 'qtd'}).reset_index()

        for idx, item in resumo.iterrows():
            st.markdown(f"""
                <div class="product-card">
                    <div style='font-size: 18px;'><b>{item['produto']}</b></div>
                    <div style='color: #555;'>{item['qtd']}x R$ {item['preco']:.2f} = <b>R$ {item['preco']*item['qtd']:.2f}</b></div>
                </div>
            """, unsafe_allow_html=True)
            
            # Controles de + e - logo abaixo do card
            b1, b2, b3, b_esp = st.columns([1, 1, 1, 4])
            if b1.button("—", key=f"btn_m_{idx}"):
                for i, p in enumerate(st.session_state.carrinho):
                    if p['produto'] == item['produto']:
                        st.session_state.carrinho.pop(i)
                        break
                st.rerun()
            b2.markdown(f"<p style='text-align:center; font-size:20px; font-weight:bold;'>{item['qtd']}</p>", unsafe_allow_html=True)
            if b3.button("＋", key=f"btn_p_{idx}"):
                st.session_state.carrinho.append({"id": time.time(), "produto": item['produto'], "preco": item['preco']})
                st.rerun()

        # 3. RODAPÉ DE PAGAMENTO
        st.divider()
        v_total = df_cart['preco'].sum()
        st.markdown(f"<h1 style='text-align:center;'>Total: R$ {v_total:.2f}</h1>", unsafe_allow_html=True)
        
        st.markdown("<p style='text-align:center;'>Escolha como pagar:</p>", unsafe_allow_html=True)
        forma_pgto = st.radio("", ["Pix", "Débito", "Crédito"], horizontal=True, label_visibility="collapsed")
        
        st.write("") # Respiro visual
        
        # Botões de Ação Final (Centralizados via CSS)
        if st.button("🚀 FINALIZAR COMPRA", type="primary"):
            st.balloons()
            st.success(f"Venda confirmada no {forma_pgto}!")
            st.session_state.carrinho = []
            time.sleep(2)
            st.rerun()
            
        if st.button("❌ CANCELAR"):
            st.session_state.carrinho = []
            st.rerun()
            
    else:
        st.info("🛒 Seu carrinho está vazio. Comece bipando um produto!")
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
    
    # Criando as duas abas
    aba_pdv, aba_maquinas = st.tabs(["📍 Pontos de Venda (PDVs)", "💳 Máquinas e Taxas"])

  # --- ABA 1: CADASTRO DE PDVS (USUÁRIOS) ---
    with aba_pdv:
        st.subheader("Gestão de Acessos e Unidades")
        df_pts = carregar_dinamico("pontos")
        
        # 1. Formulário de Cadastro
        with st.form("novo_p", clear_on_submit=True):
            st.write("Adicionar Nova Unidade")
            n = st.text_input("Nome da Unidade (ex: Condomínio Alpha)")
            s = st.text_input("Senha de Acesso para esta unidade")
            
            if st.form_submit_button("Cadastrar Unidade"):
                if n and s:
                    if n in df_pts['nome'].values:
                        st.error("Esta unidade já existe!")
                    else:
                        novo = pd.DataFrame([{"nome": n, "senha": s}])
                        conn.update(worksheet="pontos", data=pd.concat([df_pts, novo], ignore_index=True))
                        st.cache_data.clear()
                        st.success(f"Unidade {n} cadastrada com sucesso!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Preencha nome e senha.")
        
        st.divider()
        
        # 2. Lista de Unidades com Opção de Excluir
        st.write("### Unidades Cadastradas")
        if not df_pts.empty:
            for idx, row in df_pts.iterrows():
                # Criamos 3 colunas: Nome, Senha e o Botão de Lixeira
                c1, c2, c3 = st.columns([2, 2, 1])
                c1.write(f"📍 **{row['nome']}**")
                c2.write(f"🔑 `{row['senha']}`")
                
                # Botão de excluir com confirmação simples
                if c3.button("🗑️ Excluir", key=f"del_{row['nome']}", use_container_width=True):
                    # Remove o PDV da lista
                    df_pts_novo = df_pts[df_pts['nome'] != row['nome']]
                    
                    with st.spinner("Removendo unidade..."):
                        # Atualiza a aba 'pontos'
                        conn.update(worksheet="pontos", data=df_pts_novo)
                        
                        # LIMPEZA EM CASCATA: Também remove a máquina vinculada a esse PDV se existir
                        try:
                            df_maq_atual = carregar_dinamico("maquinas")
                            if row['nome'] in df_maq_atual['pdv_vinculado'].values:
                                df_maq_novo = df_maq_atual[df_maq_atual['pdv_vinculado'] != row['nome']]
                                conn.update(worksheet="maquinas", data=df_maq_novo)
                        except:
                            pass # Ignora se a aba máquinas não existir ou estiver vazia
                            
                        st.cache_data.clear()
                        st.success(f"Unidade {row['nome']} removida!")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("Nenhuma unidade cadastrada.")

    # --- ABA 2: VÍNCULO DE MÁQUINAS ---
    with aba_maquinas:
        st.subheader("Configuração de Operadoras por Unidade")
        st.info("Vincule uma máquina a um PDV para calcular o lucro líquido corretamente.")
        
        # Lista os PDVs cadastrados na ABA 1 para vincular aqui
        lista_pdvs = df_pts['nome'].tolist()

        try:
            df_maq = carregar_dinamico("maquinas")
        except:
            df_maq = pd.DataFrame(columns=["pdv_vinculado", "maquina", "taxa_pix", "taxa_debito", "taxa_credito"])

        with st.form("nova_maquina", clear_on_submit=True):
            if not lista_pdvs:
                st.warning("Cadastre um PDV primeiro na aba ao lado.")
            
            pdv_vinc = st.selectbox("Vincular esta máquina ao PDV:", options=lista_pdvs)
            nome_m = st.text_input("Nome da Operadora (ex: Stone, PagSeguro):")
            
            c1, c2, c3 = st.columns(3)
            t_pix = c1.number_input("Taxa Pix (%)", min_value=0.0, value=0.0, step=0.01)
            t_deb = c2.number_input("Taxa Débito (%)", min_value=0.0, value=1.99, step=0.01)
            t_cre = c3.number_input("Taxa Crédito (%)", min_value=0.0, value=3.49, step=0.01)
            
            if st.form_submit_button("🚀 SALVAR E VINCULAR TAXAS"):
                if nome_m and pdv_vinc:
                    nova_config = pd.DataFrame([{
                        "pdv_vinculado": pdv_vinc, 
                        "maquina": nome_m, 
                        "taxa_pix": t_pix, 
                        "taxa_debito": t_deb, 
                        "taxa_credito": t_cre
                    }])
                    
                    # Remove duplicata para o mesmo PDV
                    if not df_maq.empty and pdv_vinc in df_maq['pdv_vinculado'].values:
                        df_maq = df_maq[df_maq['pdv_vinculado'] != pdv_vinc]

                    df_maq_final = pd.concat([df_maq, nova_config], ignore_index=True)
                    
                    conn.update(worksheet="maquinas", data=df_maq_final)
                    st.cache_data.clear()
                    st.success(f"Configuração salva para {pdv_vinc}!")
                    time.sleep(1)
                    st.rerun()

        if not df_maq.empty:
            st.divider()
            st.write("### Resumo de Taxas por Unidade")
            st.dataframe(df_maq.sort_values("pdv_vinculado"), use_container_width=True, hide_index=True)
