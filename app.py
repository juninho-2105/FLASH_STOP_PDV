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

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("📊 Performance Financeira")
    df_v = carregar_dinamico("vendas")
    df_d = carregar_dinamico("despesas")
    df_p = carregar_dinamico("produtos")

    if not df_v.empty and not df_d.empty:
        bruto = pd.to_numeric(df_v['valor_bruto'], errors='coerce').sum()
        liq = pd.to_numeric(df_v['valor_liquido'], errors='coerce').sum()
        gastos = pd.to_numeric(df_d['valor'], errors='coerce').sum()
        lucro = liq - gastos

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Bruto", f"R$ {bruto:,.2f}")
        c2.metric("Líquido", f"R$ {liq:,.2f}")
        c3.metric("Despesas", f"R$ {gastos:,.2f}")
        c4.metric("Lucro Real", f"R$ {lucro:,.2f}")
    else:
        st.info("Dados insuficientes para o Dashboard.")

# --- SELF-CHECKOUT ---
elif menu == "🛒 Self-Checkout":
    st.header("🛒 Checkout")
    df_p = carregar_dinamico("produtos")
    
    if not df_p.empty:
        p_nome = st.selectbox("Bipar ou Selecionar Produto:", [""] + df_p['nome'].tolist())
        if p_nome:
            dados_p = df_p[df_p['nome'] == p_nome].iloc[0]
            preco_unit = float(dados_p['preco'])
            if st.button(f"Adicionar {p_nome} - R$ {preco_unit:.2f}", use_container_width=True):
                st.session_state.carrinho.append({"produto": p_nome, "preco": preco_unit})
                st.toast(f"{p_nome} adicionado!")
                time.sleep(0.3)
                st.rerun()

        st.divider()
        if st.session_state.carrinho:
            df_cart = pd.DataFrame(st.session_state.carrinho)
            resumo = df_cart.groupby('produto').agg({'preco': 'first', 'produto': 'count'}).rename(columns={'produto': 'qtd'}).reset_index()

            for idx, item in resumo.iterrows():
                col_txt, col_btns = st.columns([3, 1])
                with col_txt:
                    st.markdown(f"**{item['qtd']}x** {item['produto']} | R$ {item['preco']*item['qtd']:.2f}")
                with col_btns:
                    m1, m2 = st.columns(2)
                    if m1.button("—", key=f"sub_{idx}"):
                        for i, p in enumerate(st.session_state.carrinho):
                            if p['produto'] == item['produto']:
                                st.session_state.carrinho.pop(i)
                                break
                        st.rerun()
                    if m2.button("+", key=f"add_{idx}"):
                        st.session_state.carrinho.append({"produto": item['produto'], "preco": item['preco']})
                        st.rerun()

            total = df_cart['preco'].sum()
            st.subheader(f"Total: R$ {total:.2f}")
            forma_pgto = st.radio("Forma de Pagamento:", ["Pix", "Débito", "Crédito"], horizontal=True)
            
            c_f1, c_f2 = st.columns(2)
            if c_f1.button("❌ CANCELAR", use_container_width=True):
                st.session_state.carrinho = []
                st.rerun()
            if c_f2.button("🚀 PAGAR", use_container_width=True, type="primary"):
                st.success("Venda Finalizada!")
                st.session_state.carrinho = []
                time.sleep(1)
                st.rerun()
    else: st.warning("Nenhum produto cadastrado.")

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

# --- INVENTÁRIO ---
elif menu == "📦 Inventário":
    st.header("📦 Gestão de Inventário")
    df_p = carregar_dinamico("produtos")
    if not df_p.empty:
        st.dataframe(df_p, use_container_width=True, hide_index=True)
        st.divider()
        st.subheader("🗑️ Descontinuar Produto")
        p_excluir = st.selectbox("Selecione para remover:", [""] + df_p['nome'].tolist())
        if st.button("EXCLUIR PERMANENTEMENTE", type="secondary"):
            if p_excluir:
                df_p = df_p[df_p['nome'] != p_excluir]
                conn.update(worksheet="produtos", data=df_p)
                st.cache_data.clear()
                st.error(f"{p_excluir} removido.")
                time.sleep(1)
                st.rerun()

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
            st.dataframe(df_pts[['nome', 'senha']], use_container_width=True, hide_index=True)
        
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
