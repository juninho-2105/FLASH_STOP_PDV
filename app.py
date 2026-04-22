import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
# ==================== CONFIGURAÇÃO DA PÁGINA ====================
st.set_page_config(page_title="Flash Stop Pro v6.1", layout="wide",
page_icon="⚡")
conn = st.connection("gsheets", type=GSheetsConnection)
# --- MAPA DE COLUNAS CRÍTICAS ---
COLS = {
"produtos": ["nome", "estoque", "validade", "preco",
"estoque_minimo"],
"vendas": ["data", "pdv", "maquina", "produto", "valor_bruto",
"valor_liquido", "forma"],
"despesas": ["pdv", "descricao", "valor", "vencimento"],
"maquinas": ["nome_maquina", "pdv_vinculado", "taxa_debito",
"taxa_credito", "taxa_pix"],
"pontos": ["nome"]
}
# ==================== FUNÇÃO DE CARREGAMENTO SEGURO
====================
@st.cache_data(ttl=5)
def carregar(aba):
try:
df = conn.read(worksheet=aba, ttl=0).dropna(how='all')
for c in COLS.get(aba, []):
if c not in df.columns:
df[c] = 0 if any(x in c for x in ["taxa", "valor",

"preco", "estoque"]) else "-"

return df

except:
return pd.DataFrame(columns=COLS.get(aba, []))

def render_logo(font_size="42px"):
st.markdown(f'<div style="text-align:center;"><h1
style="font-family:Arial Black; font-size:{font_size};
color:#000;">FLASH <span style="color:#7CFC00;
font-style:italic;">STOP</span></h1></div>',
unsafe_allow_html=True)
# ==================== CONTROLE DE ACESSO ====================
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
render_logo("55px")
with st.form("login"):
u, s = st.text_input("Usuário"), st.text_input("Senha",

type="password")

if st.form_submit_button("Entrar"):
if u == "admin" and s == "flash123":
st.session_state.auth = True
st.rerun()

st.stop()
# ==================== MENU LATERAL ====================
with st.sidebar:
render_logo("30px")
st.divider()
menu = st.radio("Navegação", ["📊 Dashboard Principal", "️
Frente de Caixa (PDV)", "💰 Entrada/Estoque", "📈 Despesas", "📟
Configurações"])
if st.button("🔄 Forçar Sincronização"):
st.cache_data.clear()
st.rerun()

# ==================== 1. DASHBOARD PRINCIPAL ====================
if menu == "📊 Dashboard Principal":
st.header("📊 Resumo Financeiro Instantâneo")
df_v = carregar("vendas")
df_d = carregar("despesas")
# Conversão numérica segura
v_bruto_col = pd.to_numeric(df_v['valor_bruto'],
errors='coerce').fillna(0)
v_liq_col = pd.to_numeric(df_v['valor_liquido'],
errors='coerce').fillna(0)
d_val_col = pd.to_numeric(df_d['valor'],
errors='coerce').fillna(0)

bruto = v_bruto_col.sum()
liquido = v_liq_col.sum()
cashback = bruto * 0.02
gastos = d_val_col.sum()
resultado = liquido - gastos - cashback
# KPIs
c1, c2, c3, c4 = st.columns(4)
c1.metric("Vendas Brutas", f"R$ {bruto:,.2f}")
c2.metric("Líquido (Pós-Taxas)", f"R$ {liquido:,.2f}")
c3.metric("Cashback (2%)", f"R$ {cashback:,.2f}")
c4.metric("Resultado Final", f"R$ {resultado:,.2f}",
delta=float(resultado))
st.divider()
# Seção de Exportação
st.subheader("📤 Relatório para Contabilidade")
if not df_v.empty:
csv = df_v.to_csv(index=False).encode('utf-8-sig')
st.download_button(
label="📥 Baixar Vendas (CSV para Excel)",
data=csv,

file_name=f"FlashStop_Contador_{datetime.now().strftime('%d_%m_%Y')
}.csv",

mime="text/csv"
)
else:
st.info("Nenhuma venda registrada para exportação.")
# ==================== 2. FRENTE DE CAIXA ====================
elif menu == "️ Frente de Caixa (PDV)":
st.header("️ Operação de Venda")
df_p = carregar("produtos")
df_m = carregar("maquinas")
df_pts = carregar("pontos")
with st.form("venda_form"):
v_pdv = st.selectbox("Unidade/Condomínio",
df_pts['nome'].tolist()) if not df_pts.empty else ["-"]

v_prod = st.selectbox("Produto", df_p['nome'].tolist()) if

not df_p.empty else ["-"]
c1, c2 = st.columns(2)
v_forma = c1.selectbox("Forma", ["Pix", "Débito",

"Crédito", "Dinheiro"])

v_maq = c2.selectbox("Máquina", df_m[df_m['pdv_vinculado']

== v_pdv]['nome_maquina'].tolist() if not df_m.empty else
["Dinheiro"])

v_qtd = st.number_input("Quantidade", min_value=1, step=1)
if st.form_submit_button("FINALIZAR VENDA 🚀"):
if v_prod != "-":
idx = df_p[df_p['nome'] == v_prod].index[0]
preco_unit = float(df_p.at[idx, 'preco'])
v_bruto = preco_unit * v_qtd
taxa = 0.0
if v_maq != "Dinheiro":
m_info = df_m[df_m['nome_maquina'] ==

v_maq].iloc[0]

if v_forma == "Pix": taxa =

float(m_info['taxa_pix'])

elif v_forma == "Débito": taxa =

float(m_info['taxa_debito'])

elif v_forma == "Crédito": taxa =

float(m_info['taxa_credito'])

v_liq = v_bruto * (1 - (taxa/100))
df_p.at[idx, 'estoque'] = int(df_p.at[idx,

'estoque']) - v_qtd

nova_venda = pd.DataFrame([{"data":

datetime.now().strftime("%d/%m/%Y %H:%M"), "pdv": v_pdv, "maquina":
v_maq, "produto": v_prod, "valor_bruto": v_bruto, "valor_liquido":
v_liq, "forma": v_forma}])

conn.update(worksheet="vendas",
data=pd.concat([carregar("vendas"), nova_venda],
ignore_index=True))

conn.update(worksheet="produtos", data=df_p)
st.cache_data.clear()
st.success(f"Venda confirmada!")
time.sleep(1); st.rerun()

# [Outros módulos: Entrada/Estoque, Despesas e Configurações seguem
a lógica da v6.0]
