import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time

# ==================== 1. CONFIGURAÇÕES DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop - Gestão", layout="wide", page_icon="⚡")

# CSS para botões ultra-compactos e ajustes de interface
st.markdown("""
    <style>
    /* Botões menores no checkout */
    .stButton>button {
        border-radius: 6px;
        padding: 2px 5px;
    }
    div[data-testid="column"] button {
        height: 32px !important;
        width: 32px !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }
    /* Esconder branding do Streamlit conforme solicitado */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# Inicialização de Estados de Sessão
if 'autenticado' not in st.session_state: st.session_state.autenticado = False
if 'carrinho' not in st.session_state: st.session_state.carrinho = []
if 'unidade' not in st.session_state: st.session_state.unidade = ""
if 'perfil' not in st.session_state: st.session_state.perfil = ""

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def carregar_dinamico(aba):
    try:
        return conn.read(worksheet=aba, ttl=0)
    except Exception:
        # Cria DataFrame vazio se a aba não existir para evitar crash
        return pd.DataFrame()

# ==================== 2. SISTEMA DE LOGIN ====================
if not st.session_state.autenticado:
    st.title("⚡ Flash Stop - Acesso")
    with st.form("login_form"):
        user = st.text_input("Usuário / PDV")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", use_container_width=True):
            df_pts = carregar_dinamico("pontos")
            if user == "admin" and senha == "flash123":
                st.session_state.update({"autenticado": True, "unidade": "Administração", "perfil": "admin"})
                st.rerun()
            elif not df_pts.empty and user in df_pts['nome'].values:
                senha_correta = str(df_pts[df_pts['nome'] == user]['senha'].values[0])
                if senha == senha_correta:
                    st.session_state.update({"autenticado": True, "unidade": user, "perfil": "pdv"})
                    st.rerun()
                else: st.error("Senha incorreta.")
            else: st.error("Usuário não encontrado.")
    st.stop()

# ==================== 3. MENU LATERAL ====================
st.sidebar.title("⚡ Flash Stop")
st.sidebar.write(f"📍 **{st.session_state.unidade}**")

opcoes = ["📊 Dashboard", "🛒 Self-Checkout", "💰 Entrada Mercadoria", "📦 Inventário", "💸 Despesas", "📂 Contabilidade", "📟 Configurações"] if st.session_state.perfil == "admin" else ["🛒 Self-Checkout", "📦 Inventário"]
menu = st.sidebar.radio("Navegação", opcoes)

if st.sidebar.button("🚪 Sair"):
    st.session_state.autenticado = False
    st.rerun()

# ==================== 4. LÓGICA DAS TELAS ====================

# --- DASHBOARD REVISADO COM CASHBACK E ALERTAS ---
if menu == "📊 Dashboard":
    st.header("📊 Painel de Controle Flash Stop")
    
    # 1. Carregamento de Dados
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_p = carregar_dinamico("produtos")

    # --- PARTE A: MÉTRICAS FINANCEIRAS ---
    st.subheader("💰 Resumo Financeiro")
    if not df_v.empty:
        # Tratamento de dados numéricos
        df_v['valor_bruto'] = pd.to_numeric(df_v['valor_bruto'], errors='coerce').fillna(0)
        df_v['valor_liquido'] = pd.to_numeric(df_v['valor_liquido'], errors='coerce').fillna(0)
        
        # Cálculos Principais
        bruto_total = df_v['valor_bruto'].sum()
        liquido_cartao = df_v['valor_liquido'].sum()
        cashback_total = bruto_total * 0.02
        
        gastos = 0.0
        if not df_d.empty and 'valor' in df_d.columns:
            df_d['valor'] = pd.to_numeric(df_d['valor'], errors='coerce').fillna(0)
            gastos = df_d['valor'].sum()

        lucro_final = liquido_cartao - gastos - cashback_total

        # Exibição das Métricas
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Faturamento Bruto", f"R$ {bruto_total:,.2f}")
        m2.metric("Despesas", f"R$ {gastos:,.2f}")
        m3.metric("Cashback (2%)", f"R$ {cashback_total:,.2f}")
        m4.metric("Líquido Cartão", f"R$ {liquido_cartao:,.2f}")
        m5.metric("Lucro Real", f"R$ {lucro_final:,.2f}")

        # --- GRÁFICO DE VENDAS DIÁRIAS ---
        st.divider()
        st.subheader("📈 Evolução de Vendas Diárias")
        df_v['data'] = pd.to_datetime(df_v['data'], errors='coerce', dayfirst=True)
        vendas_diarias = df_v.groupby(df_v['data'].dt.date)['valor_bruto'].sum()
        st.area_chart(vendas_diarias)
    else:
        st.info("Aguardando dados de vendas para gerar o painel financeiro.")

    st.divider()

  # --- PARTE B: ALERTAS OPERACIONAIS (DINÂMICOS) ---
    st.subheader("🚨 Alertas de Operação")
    if not df_p.empty:
        col_estoque, col_validade = st.columns(2)

        with col_estoque:
            st.markdown("#### ⚠️ Estoque Crítico (Limite Personalizado)")
            
            # Garante que as colunas sejam numéricas para a comparação
            df_p['estoque'] = pd.to_numeric(df_p['estoque'], errors='coerce').fillna(0)
            if 'estoque_minimo' not in df_p.columns:
                df_p['estoque_minimo'] = 5 # Valor reserva caso a coluna não exista
            else:
                df_p['estoque_minimo'] = pd.to_numeric(df_p['estoque_minimo'], errors='coerce').fillna(5)

            # FILTRO CRÍTICO: Compara o estoque com o limite definido no inventário
            baixo = df_p[df_p['estoque'] <= df_p['estoque_minimo']]
            
            if not baixo.empty:
                for _, r in baixo.iterrows():
                    st.error(f"**{r['nome']}**: {int(r['estoque'])} un (Mínimo: {int(r['estoque_minimo'])})")
            else:
                st.success("✅ Todos os produtos acima do limite mínimo.")

        with col_validade:
            st.markdown("#### 📅 Validades")
            df_p['validade_dt'] = pd.to_datetime(df_p['validade'], dayfirst=True, errors='coerce')
            hoje = datetime.now()
            
            vencidos = df_p[df_p['validade_dt'] < hoje]
            vencendo_em_breve = df_p[(df_p['validade_dt'] >= hoje) & (df_p['validade_dt'] <= hoje + timedelta(days=7))]

            if not vencidos.empty:
                for _, r in vencidos.iterrows():
                    st.error(f"**VENCIDO:** {r['nome']} ({r['validade']})")
            
            if not vencendo_em_breve.empty:
                for _, r in vencendo_em_breve.iterrows():
                    st.warning(f"**Vence em 7 dias:** {r['nome']} ({r['validade']})")
            
            if vencidos.empty and vencendo_em_breve.empty:
                st.success("✅ Validades em dia.")
    else:
        st.info("Nenhum produto cadastrado para monitoramento.")
                           

# ==================== ABA: SELF-CHECKOUT (LOGO IDÊNTICO À FOTO) ====================
elif menu == "🛒 Self-Checkout":
    # --- LOGO CUSTOMIZADO (HTML/CSS) ---
    st.markdown("""
        <style>
        .logo-container {
            background-color: black;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            margin-bottom: 25px;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: 'Arial Black', Gadget, sans-serif; /* Fonte robusta similar */
        }
        .logo-lightning {
            color: #32CD32; /* Verde Limão */
            font-size: 80px;
            margin-right: 20px;
            line-height: 1;
        }
        .logo-text-block {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            line-height: 1;
        }
        .logo-flash {
            color: #32CD32; /* Verde Limão */
            font-size: 60px;
            text-transform: lowercase; /* Garante minúsculas */
            font-weight: bold;
        }
        .logo-stop {
            color: white;
            font-size: 60px;
            text-transform: lowercase; /* Garante minúsculas */
            font-weight: bold;
            margin-top: -10px; /* Cola as linhas */
        }
        .logo-convenience {
            color: white;
            font-size: 16px;
            text-transform: uppercase; /* Garante maiúsculas */
            letter-spacing: 2px; /* Espaçamento entre letras */
            margin-top: 5px;
            font-weight: normal;
        }
        </style>
        <div class="logo-container">
            <div class="logo-lightning">⚡</div>
            <div class="logo-text-block">
                <div class="logo-flash">flash</div>
                <div class="logo-stop">stop</div>
                <div class="logo-convenience">CONVENIÊNCIA</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h3 style='text-align: center;'>Terminal de Autoatendimento</h3>", unsafe_allow_html=True)
    
    # --- 1. Carregamento e Tratamento de Dados (Foco em preco_venda) ---
    df_p = carregar_dinamico("produtos")
    
    if not df_p.empty:
        # Função para garantir a leitura correta do preco_venda (trata R$, vírgulas e pontos)
        def sanitizar_preco(valor):
            try:
                v = str(valor).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
                return float(v)
            except:
                return 0.0

        # Define a coluna correta (preco_venda) e limpa os dados
        col_preco = 'preco_venda' if 'preco_venda' in df_p.columns else 'preco'
        df_p[col_preco] = df_p[col_preco].apply(sanitizar_preco)
        
        # --- 2. Entrada de Produto (Bip ou Manual com Botão de Confirmação) ---
        st.subheader("🛍️ Adicionar Produto")
        col_input, col_btn = st.columns([3, 1])
        
        with col_input:
            p_selecionado = st.selectbox(
                "Use o leitor ou busque pelo nome:", 
                [""] + df_p['nome'].tolist(), 
                key="input_checkout_final_v1"
            )
        
        with col_btn:
            # O botão evita que o sistema processe bips falsos ou recarregamentos duplicados
            if st.button("➕ Adicionar", use_container_width=True):
                if p_selecionado:
                    item_info = df_p[df_p['nome'] == p_selecionado].iloc[0]
                    st.session_state.carrinho.append({
                        "produto": item_info['nome'], 
                        "preco": item_info[col_preco], # Usando o preço sanitizado de preco_venda
                        "unidade": st.session_state.unidade
                    })
                    st.toast(f"✅ {p_selecionado} no carrinho!")
                    time.sleep(0.1)
                    st.rerun()

        st.divider()

        # --- 3. Exibição do Carrinho e Pagamento ---
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            resumo = df_cart.groupby('produto').agg({'preco': 'first', 'produto': 'count'}).rename(columns={'produto': 'qtd'}).reset_index()

            for idx, row in resumo.iterrows():
                c_item, c_sub = st.columns([5, 1])
                c_item.write(f"**{row['qtd']}x** {row['produto']} (R$ {row['preco']:.2f})")
                if c_sub.button("—", key=f"btn_del_{idx}"):
                    for i, p in enumerate(st.session_state.carrinho):
                        if p['produto'] == row['produto']:
                            st.session_state.carrinho.pop(i)
                            break
                    st.rerun()

            total_venda = df_cart['preco'].sum()
            st.markdown(f"<h2 style='text-align: center;'>Total: R$ {total_venda:.2f}</h2>", unsafe_allow_html=True)
            
            forma_pagto = st.radio("Pagamento:", ["Pix", "Débito", "Crédito"], horizontal=True)

            st.write("") 

            # --- 4. Botões de Finalização (Empilhados e Centralizados) ---
            if st.button("🏁 FINALIZAR COMPRA", use_container_width=True, type="primary"):
                # Registro da venda e baixa de estoque...
                nova_venda = pd.DataFrame([{
                    "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "unidade": st.session_state.unidade,
                    "valor_bruto": total_venda,
                    "valor_liquido": total_venda * 0.97, 
                    "forma_pgto": forma_pagto
                }])
                
                for item in st.session_state.carrinho:
                    idx_p = df_p[df_p['nome'] == item['produto']].index[0]
                    df_p.at[idx_p, 'estoque'] = max(0, int(df_p.at[idx_p, 'estoque']) - 1)

                conn.update(worksheet="vendas", data=pd.concat([carregar_dinamico("vendas"), nova_venda], ignore_index=True))
                conn.update(worksheet="produtos", data=df_p)
                
                st.session_state.carrinho = []
                st.success("Compra Finalizada!")
                st.balloons()
                time.sleep(1.5)
                st.rerun()
                
            if st.button("❌ CANCELAR COMPRA", use_container_width=True):
                st.session_state.carrinho = []
                st.rerun()
        else:
            st.info("Aguardando produtos...")
    else:
        st.warning("Nenhum produto cadastrado no inventário.")

# --- ENTRADA DE MERCADORIA E NOVO CADASTRO ---
elif menu == "💰 Entrada Mercadoria":
    st.header("💰 Gestão de Estoque e Preços")
    df_p = carregar_dinamico("produtos")

    # Seletor de modo
    modo = st.radio("Selecione a operação:", ["Repor Estoque", "Cadastrar Novo Produto"], horizontal=True)

    if modo == "Repor Estoque":
        if not df_p.empty:
            prod_sel = st.selectbox("Selecione o Produto:", df_p['nome'].tolist())
            with st.form("form_reposicao"):
                c1, c2, c3 = st.columns(3)
                qtd_chegando = c1.number_input("Qtd Chegando:", min_value=1)
                custo = c2.number_input("Custo Unitário (R$):", value=0.0)
                margem = c3.number_input("Margem (%)", value=40.0)
                
                validade = st.date_input("Nova Validade:", value=datetime.now() + timedelta(days=90))
                
                preco_sugerido = custo * (1 + (margem/100))
                preco_venda = st.number_input("Confirmar Preço de Venda (R$):", value=preco_sugerido)
                
                if st.form_submit_button("Atualizar Produto"):
                    idx = df_p[df_p['nome'] == prod_sel].index[0]
                    # Soma ao estoque atual e atualiza preço/validade
                    df_p.at[idx, 'estoque'] = int(df_p.at[idx, 'estoque']) + qtd_chegando
                    df_p.at[idx, 'preco'] = preco_venda
                    df_p.at[idx, 'validade'] = validade.strftime("%d/%m/%Y")
                    
                    conn.update(worksheet="produtos", data=df_p)
                    st.cache_data.clear()
                    st.success(f"Estoque de {prod_sel} atualizado!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.warning("Nenhum produto cadastrado para repor.")

    else:
        # --- MODO NOVO CADASTRO ---
        st.subheader("📝 Cadastrar Novo Item no Sistema")
        with st.form("form_cadastro_novo"):
            nome_n = st.text_input("Nome do Produto:")
            c1, c2, c3 = st.columns(3)
            estoque_i = c1.number_input("Estoque Inicial:", min_value=0)
            custo_i = c2.number_input("Custo de Compra (R$):", value=0.0)
            margem_i = c3.number_input("Margem Desejada (%)", value=40.0)
            
            validade_i = st.date_input("Validade:", value=datetime.now() + timedelta(days=90))
            
            preco_final_n = custo_i * (1 + (margem_i/100))
            preco_venda_n = st.number_input("Preço de Venda Final (R$):", value=preco_final_n)

            if st.form_submit_button("Salvar Novo Produto"):
                if nome_n:
                    # Cria a nova linha respeitando as colunas do seu Sheets
                    novo_item = pd.DataFrame([{
                        "nome": nome_n,
                        "estoque": estoque_i,
                        "preco": preco_venda_n,
                        "validade": validade_i.strftime("%d/%m/%Y"),
                        "estoque_minimo": 5  # Valor padrão de segurança
                    }])
                    
                    df_atualizado = pd.concat([df_p, novo_item], ignore_index=True)
                    conn.update(worksheet="produtos", data=df_atualizado)
                    st.cache_data.clear()
                    st.success(f"{nome_n} cadastrado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("O nome do produto é obrigatório.")

# ==================== ABA: INVENTÁRIO (VERSÃO INTEGRADA) ====================
elif menu == "📦 Inventário":
    st.header("📦 Gestão de Estoque e Produtos")
    
    # Carregamento dos dados
    df_p = carregar_dinamico("produtos")
    
    if df_p is not None and not df_p.empty:
        # --- 1. TRATAMENTO E SANITIZAÇÃO DE DADOS ---
        col_venda = 'preco_venda' if 'preco_venda' in df_p.columns else 'preco'
        
        # Converte para numérico para garantir cálculos e formatação
        df_p[col_venda] = pd.to_numeric(df_p[col_venda].astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)
        df_p['estoque'] = pd.to_numeric(df_p['estoque'], errors='coerce').fillna(0)
        
        # Garante que a coluna de estoque mínimo exista
        if 'estoque_minimo' not in df_p.columns:
            df_p['estoque_minimo'] = 5
        else:
            df_p['estoque_minimo'] = pd.to_numeric(df_p['estoque_minimo'], errors='coerce').fillna(5)

        # --- 2. VISUALIZAÇÃO COM FORMATAÇÃO DE MOEDA ---
        st.subheader("📋 Lista de Produtos Atuais")
        
        # Estilização: Linhas em vermelho se o estoque for menor ou igual ao mínimo
        def destacar_estoque_baixo(s):
            is_low = s['estoque'] <= s['estoque_minimo']
            return ['background-color: #ffcccc' if is_low else '' for _ in s]

        st.dataframe(
            df_p.style.format({
                col_venda: "R$ {:,.2f}",
                "estoque": "{:.0f}",
                "estoque_minimo": "{:.0f}"
            }).apply(destacar_estoque_baixo, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        st.caption("💡 Linhas em vermelho indicam que o produto atingiu o nível crítico definido.")

        st.divider()

        # --- 3. EDIÇÃO DE PRODUTO (PREÇO E ESTOQUE) ---
        st.subheader("✏️ Atualizar Produto")
        p_escolhido = st.selectbox("Selecione o produto para editar:", [""] + df_p['nome'].tolist())
        
        if p_escolhido:
            item_atual = df_p[df_p['nome'] == p_escolhido].iloc[0]
            
            with st.form("form_edicao"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    novo_preco = st.number_input("Preço de Venda (R$):", value=float(item_atual[col_venda]), step=0.01, format="%.2f")
                with c2:
                    nova_qtd = st.number_input("Quantidade em Estoque:", value=int(item_atual['estoque']), step=1)
                with c3:
                    novo_minimo = st.number_input("Aviso de Estoque Mínimo:", value=int(item_atual['estoque_minimo']), step=1)
                
                if st.form_submit_button("✅ SALVAR ALTERAÇÕES", use_container_width=True):
                    idx = df_p[df_p['nome'] == p_escolhido].index[0]
                    df_p.at[idx, col_venda] = novo_preco
                    df_p.at[idx, 'estoque'] = nova_qtd
                    df_p.at[idx, 'estoque_minimo'] = novo_minimo
                    
                    conn.update(worksheet="produtos", data=df_p)
                    st.cache_data.clear()
                    st.success(f"Dados de '{p_escolhido}' atualizados com sucesso!")
                    time.sleep(1)
                    st.rerun()

        st.divider()

        # --- 4. LIMPEZA DE CATÁLOGO (REMOVER PRODUTOS) ---
        st.subheader("🗑️ Limpeza de Catálogo")
        with st.expander("Excluir produtos (Vencidos ou Descontinuados)"):
            st.info("Use esta opção para remover permanentemente um item do seu inventário.")
            
            # Identificação de motivos para exclusão
            hoje = datetime.now()
            opcoes_del = []
            for _, r in df_p.iterrows():
                motivo = ""
                if 'validade' in df_p.columns:
                    v_dt = pd.to_datetime(r['validade'], dayfirst=True, errors='coerce')
                    if pd.notnull(v_dt) and v_dt < hoje:
                        motivo += " [VENCIDO]"
                if r['estoque'] <= 0:
                    motivo += " [SEM ESTOQUE]"
                
                opcoes_del.append(f"{r['nome']}{motivo}")

            p_del = st.selectbox("Escolha o item para remover:", [""] + opcoes_del, key="del_box")

            if st.button("🗑️ EXCLUIR DEFINITIVAMENTE", type="primary", use_container_width=True):
                if p_del != "":
                    nome_real = p_del.split(" [")[0] # Pega o nome antes do aviso
                    df_p = df_p[df_p['nome'] != nome_real]
                    
                    conn.update(worksheet="produtos", data=df_p)
                    st.cache_data.clear()
                    st.error(f"Produto '{nome_real}' removido do sistema.")
                    time.sleep(1.5)
                    st.rerun()
    else:
        st.warning("Nenhum dado encontrado na aba 'produtos' da sua planilha.")
        
# --- GESTÃO DE DESPESAS ---
elif menu == "💸 Despesas":
    st.header("💸 Gestão de Despesas")
    df_d = carregar_dinamico("despesas")
    
    tab_fixa, tab_variavel = st.tabs(["📌 Despesas Fixas (Recorrentes)", "💸 Despesas Variáveis"])

    with tab_fixa:
        st.subheader("Contas do Mês")
        # Interface para facilitar o lançamento de contas padrão
        col1, col2, col3 = st.columns(3)
        tipo_fixo = col1.selectbox("Tipo de Conta:", ["Aluguel", "Energia", "Água", "Internet", "Condomínio", "Outros"])
        valor_fixo = col2.number_input("Valor da Fatura (R$):", min_value=0.0, key="val_fixo")
        vencimento = col3.date_input("Data de Vencimento:", value=datetime.now())

        if st.button("Registrar Pagamento Fixo", use_container_width=True):
            nova_despesa = pd.DataFrame([{
                "data": vencimento.strftime("%d/%m/%Y"),
                "categoria": "Fixa",
                "descricao": tipo_fixo,
                "valor": valor_fixo,
                "unidade": st.session_state.unidade
            }])
            df_atualizado = pd.concat([df_d, nova_despesa], ignore_index=True)
            conn.update(worksheet="despesas", data=df_atualizado)
            st.cache_data.clear()
            st.success(f"Pagamento de {tipo_fixo} registrado!")
            time.sleep(1)
            st.rerun()

    with tab_variavel:
        st.subheader("Gastos Pontuais")
        with st.form("form_despesa_var"):
            data_v = st.date_input("Data do Gasto:", value=datetime.now())
            desc_v = st.text_input("Descrição (Ex: Reposição de Emergência, Limpeza):")
            valor_v = st.number_input("Valor Pago (R$):", min_value=0.0)
            
            if st.form_submit_button("Salvar Despesa Variável"):
                if desc_v and valor_v > 0:
                    nova_despesa_v = pd.DataFrame([{
                        "data": data_v.strftime("%d/%m/%Y"),
                        "categoria": "Variável",
                        "descricao": desc_v,
                        "valor": valor_v,
                        "unidade": st.session_state.unidade
                    }])
                    df_atualizado = pd.concat([df_d, nova_despesa_v], ignore_index=True)
                    conn.update(worksheet="despesas", data=df_atualizado)
                    st.cache_data.clear()
                    st.success("Despesa variável salva!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Preencha a descrição e o valor.")

    st.divider()
    st.subheader("📋 Histórico Recente")
    if not df_d.empty:
        # Filtra apenas as despesas da unidade atual (ou todas se for admin)
        if st.session_state.perfil == "admin":
            st.dataframe(df_d.tail(10), use_container_width=True, hide_index=True)
        else:
            df_unidade = df_d[df_d['unidade'] == st.session_state.unidade]
            st.dataframe(df_unidade.tail(10), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhuma despesa registrada ainda.")

# --- ABA CONTABILIDADE ---
elif menu == "📂 Contabilidade":
    st.header("📂 Relatórios Contábeis")
    
    # Carregamento de dados
    df_vendas = carregar_dinamico("vendas")
    df_pontos = carregar_dinamico("pontos")
    
    if df_vendas.empty:
        st.warning("Sem dados de vendas para gerar relatórios.")
    else:
        # 1. Filtros de Geração
        with st.expander("🔍 Filtros do Relatório", expanded=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            
            pdv_sel = col_f1.selectbox("Selecione o PDV:", df_pontos['nome'].tolist())
            mes_ref = col_f2.selectbox("Mês de Referência:", ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"])
            taxa_adm = col_f3.number_input("Taxa Média Cartão (%):", value=2.5)

        # 2. Processamento de Dados (Filtro por Unidade)
        df_vendas['valor_bruto'] = pd.to_numeric(df_vendas['valor_bruto'], errors='coerce')
        df_pdv = df_vendas[df_vendas['unidade'] == pdv_sel].copy()
        
        # Cálculos Contábeis
        total_bruto = df_pdv['valor_bruto'].sum()
        total_taxas = total_bruto * (taxa_adm / 100)
        total_liquido = total_bruto - total_taxas
        total_transacoes = len(df_pdv)

        # 3. Visualização do Relatório (Layout de Impressão)
        st.markdown(f"""
            <div style="border: 1px solid #ddd; padding: 20px; border-radius: 10px; background-color: white; color: black;">
                <h2 style="text-align: center; margin-bottom: 0;">FLASH STOP - RELATÓRIO CONTÁBIL</h2>
                <p style="text-align: center; color: #666;">Unidade: {pdv_sel} | Competência: {mes_ref} 2026</p>
                <hr>
                <table style="width: 100%; font-size: 16px;">
                    <tr><td><b>Faturamento Bruto:</b></td><td style="text-align: right;">R$ {total_bruto:,.2f}</td></tr>
                    <tr><td><b>Taxas Operacionais (Est.):</b></td><td style="text-align: right; color: red;">- R$ {total_taxas:,.2f}</td></tr>
                    <tr style="font-size: 20px; border-top: 2px solid #000;">
                        <td><b>Repasse Líquido:</b></td><td style="text-align: right;"><b>R$ {total_liquido:,.2f}</b></td></tr>
                </table>
                <br>
                <p style="font-size: 12px;">Total de Transações no período: {total_transacoes}</p>
            </div>
        """, unsafe_allow_html=True)

        st.write("") # Espaçador

        # 4. Botões de Exportação
        col_ex1, col_ex2 = st.columns(2)
        
        # Exportar Excel (Formatado para o Contador)
        csv = df_pdv.to_csv(index=False).encode('utf-8')
        col_ex1.download_button(
            label="💾 Baixar Planilha (CSV)",
            data=csv,
            file_name=f"Contabilidade_FlashStop_{pdv_sel}_{mes_ref}.csv",
            mime="text/csv",
            use_container_width=True
        )

        # Botão de Impressão (Aciona o comando de impressão do navegador)
        if col_ex2.button("🖨️ Imprimir / Gerar PDF", use_container_width=True):
            st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
            st.info("Use a opção 'Salvar como PDF' na tela de impressão que abriu.")

        # Exibição analítica para conferência rápida
        with st.expander("Visualizar Detalhamento de Vendas"):
            st.dataframe(df_pdv, use_container_width=True, hide_index=True)
            
# --- ABA CONFIGURAÇÕES ---
elif menu == "📟 Configurações":
    st.header("📟 Configurações do Sistema")
    
    # Carregamento de dados
    df_pts = carregar_dinamico("pontos")
    # Tenta carregar aba de máquinas, se não existir cria DataFrame padrão
    try:
        df_maquinas = carregar_dinamico("maquinas")
    except:
        df_maquinas = pd.DataFrame(columns=["maquina", "pdv_vinculado", "taxa_debito", "taxa_credito", "taxa_pix"])

    tab_pdv, tab_maquinas = st.tabs(["📍 Gestão de PDVs", "💳 Máquinas e Taxas"])

    # --- TAB: GESTÃO DE PDVs ---
    with tab_pdv:
        st.subheader("Unidades Cadastradas")
        if not df_pts.empty:
            # Exibe a tabela para conferência
            st.dataframe(df_pts[['nome', 'senha']], use_container_width=True, hide_index=True)
            
            st.divider()
            st.subheader("🗑️ Remover Unidade")
            # Seletor para escolher qual PDV deletar
            pdv_para_excluir = st.selectbox("Selecione o PDV para remover:", [""] + df_pts['nome'].tolist())
            
            if st.button("Confirmar Exclusão do PDV", type="secondary", use_container_width=True):
                if pdv_para_excluir != "":
                    # Filtra o DataFrame mantendo todos, exceto o selecionado
                    df_pts_novo = df_pts[df_pts['nome'] != pdv_para_excluir]
                    
                    # Atualiza o Google Sheets
                    conn.update(worksheet="pontos", data=df_pts_novo)
                    st.cache_data.clear() # Limpa o cache para atualizar a lista
                    
                    st.error(f"Unidade {pdv_para_excluir} removida com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Selecione uma unidade para excluir.")
        else:
            st.info("Nenhum PDV cadastrado.")
        
        st.divider()
        st.subheader("➕ Inserir Novo PDV")
        with st.form("novo_pdv_form"):
            novo_nome = st.text_input("Nome da Unidade / Condomínio:")
            nova_senha = st.text_input("Senha de Acesso:", type="password")
            if st.form_submit_button("Cadastrar Unidade"):
                if novo_nome and nova_senha:
                    novo_pdv = pd.DataFrame([{"nome": novo_nome, "senha": nova_senha}])
                    df_pts_atu = pd.concat([df_pts, novo_pdv], ignore_index=True)
                    conn.update(worksheet="pontos", data=df_pts_atu)
                    st.cache_data.clear()
                    st.success(f"PDV {novo_nome} cadastrado!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Preencha nome e senha.")
    # --- TAB: MÁQUINAS E TAXAS ---
    with tab_maquinas:
        st.subheader("Máquinas Vinculadas")
        if not df_maquinas.empty:
            st.dataframe(df_maquinas, use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma máquina cadastrada.")

        st.divider()
        st.subheader("🔗 Cadastrar e Vincular Máquina")
        with st.form("nova_maquina_form"):
            nome_maq = st.text_input("Identificação da Máquina (Ex: Stone 01, PagSeguro):")
            pdv_vinculo = st.selectbox("Vincular ao PDV:", df_pts['nome'].tolist() if not df_pts.empty else ["Nenhum PDV cadastrado"])
            
            c1, c2, c3 = st.columns(3)
            t_deb = c1.number_input("Taxa Débito (%)", min_value=0.0, step=0.01, format="%.2f")
            t_cre = c2.number_input("Taxa Crédito (%)", min_value=0.0, step=0.01, format="%.2f")
            t_pix = c3.number_input("Taxa Pix (%)", min_value=0.0, step=0.01, format="%.2f")

            if st.form_submit_button("Salvar Configuração de Máquina"):
                if nome_maq and pdv_vinculo != "Nenhum PDV cadastrado":
                    nova_maq_data = pd.DataFrame([{
                        "maquina": nome_maq,
                        "pdv_vinculado": pdv_vinculo,
                        "taxa_debito": t_deb,
                        "taxa_credito": t_cre,
                        "taxa_pix": t_pix
                    }])
                    df_maq_atu = pd.concat([df_maquinas, nova_maq_data], ignore_index=True)
                    conn.update(worksheet="maquinas", data=df_maq_atu)
                    st.cache_data.clear()
                    st.success(f"Máquina {nome_maq} vinculada a {pdv_vinculo}!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Verifique os dados da máquina e o vínculo com o PDV.")
