import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta
import time
from streamlit_autorefresh import st_autorefresh # Necessário instalar: pip install streamlit-autorefresh
import requests # Certifique-se de que o requests está no seu requirements.txt
import streamlit as st

import streamlit as st

# 1. Configuração da aba (sempre o primeiro)
st.set_page_config(page_title="FlashStop PDV", page_icon="logo.png")

# 2. O Logo no topo
st.image("logo.png", width=200)

def enviar_telegram(mensagem):
    # Substitua pelos seus dados reais
    TOKEN = "8318147830:AAG9xVf5VzouaGcuWxtcPfUFOCfgjdtK4Yk"
    CHAT_ID = "2026386754"
    
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")


# ==================== 1. CONFIGURAÇÕES DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop - Gestão", layout="wide", page_icon="⚡")

# CSS para botões ultra-compactos (Certifique-se de que as aspas triplas envolvam o CSS)
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
    /* Os comandos que escondiam o menu foram removidos aqui */
    </style>
""", unsafe_allow_html=True)

# --- NOVO: HEARTBEAT (Anti-inatividade) ---
# Atualiza a página silenciosamente a cada 5 minutos para o tablet não desconectar
st_autorefresh(interval=5 * 60 * 1000, key="heartbeat_flashstop")


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
        return pd.DataFrame()

# ==================== 2. SISTEMA DE LOGIN (URL + MANUAL) ====================

# --- NOVO: CAPTURA DE PARÂMETROS DA URL ---
# Link de acesso direto: .../?pdv=NOME_DO_PDV&token=flash2026
query_params = st.query_params
TOKEN_MESTRE = "flash2026"

if not st.session_state.autenticado:
    if "pdv" in query_params and "token" in query_params:
        if query_params["token"] == TOKEN_MESTRE:
            st.session_state.update({
                "autenticado": True, 
                "unidade": query_params["pdv"], 
                "perfil": "pdv"
            })
            st.rerun()

# --- LOGIN MANUAL ---
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

# ==================== ABA: DASHBOARD (VISUAL ORIGINAL + BOTÃO TELEGRAM) ====================
if menu == "📊 Dashboard":
    st.header("📊 Painel de Controle Flash Stop")

    # 1. Carregamento de Dados
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_estoque_local = carregar_dinamico("estoque_pdv") 

    # --- FILTRO DE UNIDADE ---
    if df_v is not None and not df_v.empty:
        lista_unid = ["Todas"] + sorted(df_v['unidade'].unique().tolist())
        unidade_alvo = st.selectbox("Filtrar métricas financeiras por PDV:", lista_unid)
        if unidade_alvo != "Todas":
            df_v = df_v[df_v['unidade'] == unidade_alvo]
    else:
        unidade_alvo = "Todas"

    # --- PARTE A: MÉTRICAS FINANCEIRAS (O visual de 5 colunas que você gosta) ---
    st.subheader(f"💰 Resumo Financeiro - {unidade_alvo}")
    if df_v is not None and not df_v.empty:
        df_v['valor_bruto'] = pd.to_numeric(df_v['valor_bruto'], errors='coerce').fillna(0)
        df_v['valor_liquido'] = pd.to_numeric(df_v['valor_liquido'], errors='coerce').fillna(0)
        
        bruto_total = df_v['valor_bruto'].sum()
        liquido_cartao = df_v['valor_liquido'].sum()
        cashback_total = bruto_total * 0.02
        
        gastos = 0.0
        if df_d is not None and not df_d.empty and 'valor' in df_d.columns:
            df_d['valor'] = pd.to_numeric(df_d['valor'], errors='coerce').fillna(0)
            gastos = df_d['valor'].sum()

        lucro_final = liquido_cartao - gastos - cashback_total

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Faturamento Bruto", f"R$ {bruto_total:,.2f}")
        m2.metric("Despesas", f"R$ {gastos:,.2f}")
        m3.metric("Cashback (2%)", f"R$ {cashback_total:,.2f}")
        m4.metric("Líquido Cartão", f"R$ {liquido_cartao:,.2f}")
        m5.metric("Lucro Real", f"R$ {lucro_final:,.2f}")

        st.divider()
        st.subheader("📈 Evolução de Vendas Diárias")
        df_v['data'] = pd.to_datetime(df_v['data'], errors='coerce', dayfirst=True)
        vendas_diarias = df_v.groupby(df_v['data'].dt.date)['valor_bruto'].sum()
        st.area_chart(vendas_diarias, color="#32CD32")
    else:
        st.info("Aguardando dados de vendas.")

    st.divider()

    # --- PARTE B: ALERTAS OPERACIONAIS (VISUAL ORIGINAL REESTABELECIDO) ---
    st.subheader("🚨 Alertas de Operação (Por Unidade)")
    
    if df_estoque_local is not None and not df_estoque_local.empty:
        # Prevenção de erros nos dados
        df_estoque_local['quantidade'] = pd.to_numeric(df_estoque_local['quantidade'], errors='coerce').fillna(0)
        df_estoque_local['minimo_alerta'] = pd.to_numeric(df_estoque_local['minimo_alerta'], errors='coerce').fillna(5)
        df_estoque_local['validade_dt'] = pd.to_datetime(df_estoque_local['validade'], dayfirst=True, errors='coerce')
        hoje = datetime.now()

        # 1. BOTÃO DE NOTIFICAÇÃO (Posicionado antes dos cards para fácil acesso)
        if st.button("📲 Notificar Pendências no Telegram", use_container_width=True):
            # Filtros para a mensagem
            baixo_msg = df_estoque_local[df_estoque_local['quantidade'] <= df_estoque_local['minimo_alerta']]
            venc_msg = df_estoque_local[df_estoque_local['validade_dt'] <= hoje + timedelta(days=7)]
            
            if not baixo_msg.empty or not venc_msg.empty:
                msg = "<b>⚠️ FLASH STOP: RELATÓRIO DE PENDÊNCIAS</b>\n"
                if not baixo_msg.empty:
                    msg += "\n<b>📦 ESTOQUE:</b>\n"
                    for _, r in baixo_msg.iterrows():
                        msg += f"• {r['unidade']} | {r['nome']}: {int(r['quantidade'])} un\n"
                if not venc_msg.empty:
                    msg += "\n<b>📅 VALIDADES:</b>\n"
                    for _, r in venc_msg.iterrows():
                        status = "VENCIDO" if r['validade_dt'] < hoje else "VENCE LOGO"
                        msg += f"• {r['unidade']} | {status}: {r['nome']}\n"
                
                enviar_telegram(msg)
                st.toast("Enviado para o Telegram! ⚡")
            else:
                st.toast("Nada para enviar! Tudo OK. ✅")

        # 2. VISUAL DAS COLUNAS (Exatamente como era antes)
        col_estoque, col_validade = st.columns(2)

        with col_estoque:
            st.markdown("#### ⚠️ Estoque Crítico")
            baixo = df_estoque_local[df_estoque_local['quantidade'] <= df_estoque_local['minimo_alerta']]
            if not baixo.empty:
                for _, r in baixo.iterrows():
                    st.error(f"📍 **{r['unidade']}** | **{r['nome']}**: {int(r['quantidade'])} un (Mín: {int(r['minimo_alerta'])})")
            else:
                st.success("✅ Estoque em dia em todos os PDVs.")

        with col_validade:
            st.markdown("#### 📅 Validades")
            vencidos = df_estoque_local[df_estoque_local['validade_dt'] < hoje]
            vencendo_em_breve = df_estoque_local[(df_estoque_local['validade_dt'] >= hoje) & (df_estoque_local['validade_dt'] <= hoje + timedelta(days=7))]

            if not vencidos.empty:
                for _, r in vencidos.iterrows():
                    st.error(f"📍 **{r['unidade']}** | **VENCIDO:** {r['nome']} ({r['validade']})")
            
            if not vencendo_em_breve.empty:
                for _, r in vencendo_em_breve.iterrows():
                    st.warning(f"📍 **{r['unidade']}** | **Vence em breve:** {r['nome']} ({r['validade']})")
            
            if vencidos.empty and vencendo_em_breve.empty:
                st.success("✅ Validades em dia em todas as unidades.")
    else:
        st.info("Nenhum dado de estoque local encontrado.")
        
# ==================== ABA: SELF-CHECKOUT (VERSÃO FINAL CORRIGIDA) ====================
elif menu == "🛒 Self-Checkout":
   

    # 2. CARREGAMENTO DOS PRODUTOS
    df_p = carregar_dinamico("produtos")
    
    if df_p is not None and not df_p.empty:
        df_p.columns = [c.lower().strip() for c in df_p.columns]
        st.subheader("🛍️ Adicionar ao Carrinho")
        
        col_in, col_bt = st.columns([4, 1])
        
        with col_in:
            p_selecionado = st.selectbox(
                "Pesquisar Produto", 
                [""] + sorted(df_p['nome'].unique().tolist()), 
                key="v7_checkout_select", 
                label_visibility="collapsed"
            )
        
        with col_bt:
            if st.button("➕ ADD", use_container_width=True, type="secondary"):
                if p_selecionado:
                    try:
                        # Busca o valor na coluna 'preco_venda'
                        valor_bruto = df_p.loc[df_p['nome'] == p_selecionado, 'preco_venda'].values[0]
                        
                        # Tratamento para aceitar R$, vírgulas e pontos (Evita o erro de leitura)
                        if isinstance(valor_bruto, str):
                            valor_limpo = valor_bruto.replace('R$', '').replace('.', '').replace(',', '.').strip()
                            preco_final = float(valor_limpo)
                        else:
                            preco_final = float(valor_bruto)

                        st.session_state.carrinho.append({
                            "produto": p_selecionado, 
                            "preco": preco_final,
                            "unidade": st.session_state.unidade
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro no preço de '{p_selecionado}': {e}")

        st.divider()

      # 3. EXIBIÇÃO DO CARRINHO (COMPLETO COM BOTÕES)
        if st.session_state.carrinho:
            st.markdown("---")
            df_cart = pd.DataFrame(st.session_state.carrinho)
            
            # Agrupamento para não repetir itens na tela
            resumo_cart = df_cart.groupby('produto').agg({'preco': 'first', 'produto': 'count'}).rename(columns={'produto': 'qtd'}).reset_index()

            for idx, row in resumo_cart.iterrows():
                col_item, col_del = st.columns([5, 1])
                with col_item:
                    st.write(f"✅ **{row['qtd']}x** {row['produto']} — R$ {row['preco']:.2f} cada")
                with col_del:
                    if st.button("🗑️", key=f"btn_del_{row['produto']}"):
                        st.session_state.carrinho = [p for p in st.session_state.carrinho if p['produto'] != row['produto']]
                        st.rerun()

            # --- SOMA TOTAL ---
            total = df_cart['preco'].sum()
            st.markdown(f"<h1 style='text-align: center; color: #32CD32;'>TOTAL: R$ {total:.2f}</h1>", unsafe_allow_html=True)
            
            # --- PAGAMENTO (VOLTOU AQUI) ---
            st.subheader("💳 Pagamento")
            forma_pgto = st.radio("Escolha como pagar:", ["Pix", "Débito", "Crédito"], horizontal=True)
            
            # --- BOTÕES DE AÇÃO ---
            col_final, col_canc = st.columns(2)
            
            with col_final:
                if st.button("🏁 FINALIZAR COMPRA", use_container_width=True, type="primary"):
                    try:
                        agora = datetime.now().strftime("%d/%m/%Y %H:%M")
                        
                        # Salva no Sheets
                        venda_data = pd.DataFrame([{
                            "data": agora, 
                            "unidade": st.session_state.unidade, 
                            "valor_bruto": total, 
                            "metodo": forma_pgto
                        }])
                        
                        df_hist = carregar_dinamico("vendas")
                        df_novo = pd.concat([df_hist, venda_data], ignore_index=True)
                        conn.update(worksheet="vendas", data=df_novo)
                        
                        # Alerta Telegram
                        enviar_telegram(f"⚡ <b>VENDA: R$ {total:.2f}</b>\n📍 {st.session_state.unidade}\n💳 {forma_pgto}")

                        st.success("Venda concluída!")
                        st.balloons()
                        st.session_state.carrinho = []
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao salvar: {e}")

            with col_canc:
                if st.button("❌ Cancelar Tudo", use_container_width=True):
                    st.session_state.carrinho = []
                    st.rerun()
        else:
            st.info("Aguardando produtos no carrinho...")


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
                    

# ==================== ABA: INVENTÁRIO (MULTI-PDV - CORRIGIDA) ====================
elif menu == "📦 Inventário":
    st.header("📦 Gestão de Estoque Multi-PDV")
    
    # 1. CARREGAMENTO DOS DADOS
    df_geral = carregar_dinamico("produtos")      
    df_estoque = carregar_dinamico("estoque_pdv") 
    df_vendas = carregar_dinamico("vendas")       

    # --- AUTO-CORREÇÃO DE COLUNAS (Evita o KeyError) ---
    if df_estoque is not None and not df_estoque.empty:
        df_estoque.columns = [c.lower().strip() for c in df_estoque.columns]
    if df_vendas is not None and not df_vendas.empty:
        df_vendas.columns = [c.lower().strip() for c in df_vendas.columns]

    # 2. BUSCA DINÂMICA DE PDVs
    unidades_vendas = df_vendas['unidade'].unique().tolist() if df_vendas is not None and 'unidade' in df_vendas.columns else []
    unidades_estoque = df_estoque['unidade'].unique().tolist() if df_estoque is not None and 'unidade' in df_estoque.columns else []
    
    unidades_cadastradas = sorted(list(set(unidades_vendas + unidades_estoque)))
    
    if not unidades_cadastradas:
        unidades_cadastradas = ["Flash Stop 01"] # Unidade padrão inicial

    aba_geral, aba_unidade = st.tabs(["🌎 Catálogo Geral", "📍 Estoque por PDV"])

    # --- ABA 1: CATÁLOGO GERAL ---
    with aba_geral:
        st.subheader("Configuração Global de Produtos")
        if df_geral is not None and not df_geral.empty:
            df_geral.columns = [c.lower().strip() for c in df_geral.columns] # Normaliza colunas
            st.dataframe(df_geral[["nome", "preco_venda", "categoria"]], use_container_width=True, hide_index=True)
        else:
            st.warning("Cadastre produtos no catálogo geral primeiro.")

    # --- ABA 2: ESTOQUE POR PDV ---
    with aba_unidade:
        unidade_selecionada = st.selectbox("Selecione o PDV para gerir:", unidades_cadastradas)
        
        # Filtro Blindado
        if df_estoque is not None and 'unidade' in df_estoque.columns:
            df_local = df_estoque[df_estoque['unidade'] == unidade_selecionada]
            
            # Sincronização
            if df_geral is not None and 'nome' in df_geral.columns:
                produtos_faltantes = [p for p in df_geral['nome'].tolist() if p not in df_local['nome'].tolist()]
                
                if produtos_faltantes:
                    if st.button(f"📥 Sincronizar Itens com {unidade_selecionada}"):
                        novas_linhas = []
                        for p in produtos_faltantes:
                            novas_linhas.append({
                                "unidade": unidade_selecionada,
                                "nome": p,
                                "quantidade": 0,
                                "validade": "A definir",
                                "minimo_alerta": 5
                            })
                        df_estoque = pd.concat([df_estoque, pd.DataFrame(novas_linhas)], ignore_index=True)
                        conn.update(worksheet="estoque_pdv", data=df_estoque)
                        st.success("Sincronizado!")
                        st.rerun()

            if not df_local.empty:
                st.write(f"### Detalhes: {unidade_selecionada}")
                
                # Mostra: Nome, Quantidade Existente e Validade
                cols_mostrar = ["nome", "quantidade", "validade", "minimo_alerta"]
                st.dataframe(df_local[cols_mostrar], use_container_width=True, hide_index=True)

                st.divider()
                st.subheader("✏️ Atualizar Dados")
                p_edit = st.selectbox("Produto:", [""] + df_local['nome'].tolist())
                
                if p_edit:
                    item = df_local[df_local['nome'] == p_edit].iloc[0]
                    with st.form("form_edit"):
                        c1, c2, c3 = st.columns(3)
                        n_qtd = c1.number_input("Qtd Existente", value=int(item['quantidade']))
                        n_val = c2.text_input("Validade", value=str(item['validade']))
                        n_min = c3.number_input("Mínimo Alerta", value=int(item['minimo_alerta']))
                        
                        if st.form_submit_button("Salvar"):
                            idx = df_estoque[(df_estoque['unidade'] == unidade_selecionada) & (df_estoque['nome'] == p_edit)].index[0]
                            df_estoque.at[idx, 'quantidade'] = n_qtd
                            df_estoque.at[idx, 'validade'] = n_val
                            df_estoque.at[idx, 'minimo_alerta'] = n_min
                            conn.update(worksheet="estoque_pdv", data=df_estoque)
                            st.success("Salvo!")
                            st.rerun()
        else:
            st.error("⚠️ Erro: A aba 'estoque_pdv' no Sheets precisa ter a coluna 'unidade'.")
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
