import streamlit as st
import pandas as pd
import glob
import datetime as dt
import altair as alt
import plotly.graph_objects as go
import tkinter as tk
from tkinter import filedialog
import time

st.set_page_config(layout="wide")
st.title('Carteira')
#####################################
#### Concatenate all excel files ####
#####################################
##------------------- Selecionar diretorio com arquivos da B3
## Set up tkinter
#root = tk.Tk()
#root.withdraw()

## Make folder picker dialog appear on top of other windows
#root.wm_attributes('-topmost', 1)

## Folder picker button
#st.sidebar.title('Selecionar arquivos')
#st.sidebar.write('Selecione a pasta contendo os arquivos:')
#clicked = st.sidebar.button('Abrir')
#dirname = "C:/"
#if clicked:
#    dirname = st.sidebar.text_input('Pasta selecionada:', filedialog.askdirectory(master=root))

#placeholder = st.empty()
#for img_array in img_arrays:
#  placeholder.image(img_array)
#  time.sleep(30)



#with st.spinner('Wait for it...'):
#    time.sleep(5)

flag_files = {"Movimentação": False, "Negociação": False, "Posição": False}

df_movimentacao = pd.DataFrame()
df_negociacao = pd.DataFrame()
df_posicao = pd.DataFrame()

uploaded_files = st.sidebar.file_uploader("Escolha os arquivos (*.xlsx)", type=["csv", "xlsx"], accept_multiple_files=True)

#while all(flag_files):
   # st.sidebar.warning('This is a warning', icon="⚠️")
for uploaded_file in uploaded_files:
    ## movimentacao
    if uploaded_file.name.startswith("movimentacao"):
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        df_movimentacao = df_movimentacao.append(df,ignore_index=True)
        flag_files["Movimentação"] = True
    
    ## negociacao
    if uploaded_file.name.startswith("negociacao"):
        df = pd.read_excel(uploaded_file, engine="openpyxl")
        df_negociacao = df_negociacao.append(df,ignore_index=True)
        flag_files["Negociação"] = True

    ## posicao
    if uploaded_file.name.startswith("posicao"):
        df = pd.read_excel(uploaded_file, sheet_name="Fundo de Investimento")
        df_posicao = df_posicao.append(df,ignore_index=True)
        flag_files["Posição"] = True


if not all(flag_files):
    st.sidebar.success('This is a success message!', icon="✅")

#------------------------------------
## movimentacao
#------------------------------------
#df_movimentacao = pd.DataFrame()
#for f in glob.glob("movimentacao*.xlsx"):
#    df = pd.read_excel(f, engine="openpyxl")
#    df_movimentacao = df_movimentacao.append(df,ignore_index=True)

df_movimentacao.drop_duplicates(keep='first', inplace=True)
df_movimentacao=df_movimentacao[~df_movimentacao["Preço unitário"].isin(["-"])] # dropping rows with no values
df_movimentacao['Produto'] = df_movimentacao.Produto.str.split(' -', expand=True).apply(lambda x: (x[0]), axis=1) # Formating ticker's name
df_movimentacao['Data'] = pd.to_datetime(df_movimentacao['Data'], dayfirst=True)
df_movimentacao['Date_month'] = df_movimentacao.Data.dt.to_period("M").astype("str")
df_movimentacao['Date_year'] = df_movimentacao.Data.dt.year.astype("str")


#------------------------------------
## negociacao
#------------------------------------
#df_negociacao = pd.DataFrame()
#for f in glob.glob("negociacao*.xlsx"):
#    df = pd.read_excel(f, engine="openpyxl")
#    df_negociacao = df_negociacao.append(df,ignore_index=True)

df_negociacao.drop_duplicates(keep='first', inplace=True)

#------------------------------------
## posicao
#------------------------------------
#df_posicao = pd.read_excel("posicao-2023-01-12.xlsx", sheet_name="Fundo de Investimento")
df_posicao=df_posicao.dropna() # dropping rows with no values
# Add ticker type
df_tickerType = pd.read_excel("subscricoes.xlsx", sheet_name="ticker_type")
df_posicao['ticker_type'] = df_posicao['Código de Negociação'].map(df_tickerType.set_index('Ticker')['Type'])
df_posicao['percent'] = (df_posicao.Quantidade/df_posicao.Quantidade.sum())*100
df_posicao['percent'] = df_posicao['percent'].round(decimals=2).astype('str') + ' %'
#st.dataframe(df_posicao)


#############################################
#### Corrigindo desdobramentos ocorridos ####
#############################################
#------------------------------------
## MGLU3 em 2020 Cotas x4
#------------------------------------
desdobramento_MGLU3 = 4
quantidade = df_negociacao[df_negociacao["Código de Negociação"] == "MGLU3F"]["Quantidade"].values[0] * desdobramento_MGLU3
preco = df_negociacao[df_negociacao["Código de Negociação"] == "MGLU3F"]["Preço"].values[0] / desdobramento_MGLU3
valor = quantidade * preco
### Corrigindo o desdobramento do MGLU3
df_negociacao.loc[df_negociacao["Código de Negociação"] == "MGLU3F", 'Quantidade'] = quantidade
df_negociacao.loc[df_negociacao["Código de Negociação"] == "MGLU3F", 'Preço'] = preco
df_negociacao.loc[df_negociacao["Código de Negociação"] == "MGLU3F", 'Valor'] = valor
df_negociacao.loc[df_negociacao["Código de Negociação"] == "MGLU3F", 'Código de Negociação'] = 'MGLU3'

#------------------------------------
## KISU11 em 2021 Cotas x10
#------------------------------------
desdobramento_KISU11 = 10
quantidade = df_negociacao[df_negociacao["Código de Negociação"] == "KISU11"]["Quantidade"].values[0] * desdobramento_KISU11
preco = df_negociacao[df_negociacao["Código de Negociação"] == "KISU11"]["Preço"].values[0] / desdobramento_KISU11
valor = quantidade * preco
### Corrigindo o desdobramento do KISU11
df_negociacao.loc[df_negociacao["Código de Negociação"] == "KISU11", 'Quantidade'] = quantidade
df_negociacao.loc[df_negociacao["Código de Negociação"] == "KISU11", 'Preço'] = preco
df_negociacao.loc[df_negociacao["Código de Negociação"] == "KISU11", 'Valor'] = valor

#################################
#### Adicionando subscricoes ####
#################################
### Abrir arquivo de subscricoes. Base de dados criada por mim para manter o historico das subscricoes
df_subscricoes = pd.read_excel("subscricoes.xlsx", sheet_name="subscricoes")
df_negociacao = df_negociacao.append(df_subscricoes, ignore_index=True)

#################################
#### Filters sideBar         ####
#################################

st.sidebar.write("Filtros")
selected_movimentacao = st.sidebar.multiselect('Selecione as Movimentações:', df_movimentacao["Movimentação"].drop_duplicates(keep='first', inplace=False), default=["Rendimento", "Juros Sobre Capital Próprio", "Dividendo"])
df_movimentacao=df_movimentacao[df_movimentacao["Movimentação"].isin(selected_movimentacao)]
allTickers = df_movimentacao.Produto.drop_duplicates(keep='first', inplace=False)

all_options = st.sidebar.checkbox("Select all Tickers")
if all_options:
    selected_tickers = st.sidebar.multiselect('Selecione os Tickers:', allTickers, default=allTickers)
else:
    selected_tickers = st.sidebar.multiselect('Selecione os Tickers:', allTickers, default=["HGLG11", "DEVA11"])

min_Value=pd.to_datetime(df_movimentacao.Data.min())
max_Value=pd.to_datetime(df_movimentacao.Data.max())

selected_date_begin = st.sidebar.date_input('Data de Inicio',  value=min_Value, min_value=min_Value, max_value=max_Value)
selected_date_end = st.sidebar.date_input('Data de Fim',  value=max_Value, min_value=min_Value, max_value=max_Value)

# Show the data as a dataframe.
filtered_df_movimentacao = df_movimentacao.loc[(df_movimentacao.Produto.isin(selected_tickers)) & \
                            (df_movimentacao.Data >= dt.datetime.combine(selected_date_begin, dt.datetime.min.time())) & \
                            (df_movimentacao.Data <= dt.datetime.combine(selected_date_end, dt.datetime.min.time()))]
#st.dataframe(filtered_df_movimentacao)

#################################
####    Tabela preco medio   ####
#################################
st.write('Preços medios')
df_synthesis = df_negociacao.groupby("Código de Negociação").sum()
df_synthesis.drop(['Preço'], axis=1, inplace=True)
df_synthesis["Preco_medio"] = df_synthesis["Valor"]/df_synthesis["Quantidade"]
df_synthesis.rename(columns={"Valor": "Valor Investido", "Quantidade": "Numero de quotas"}, inplace=True)
st.dataframe(df_synthesis.style.format(subset=['Valor Investido', 'Preco_medio'], formatter="{:.2f}"))

#################################
####    Plotting             ####
#################################
#### groupping multiple rows from the same ticker and creating a new dataframe to be plotted
operValue_sub_df_movimentacao = filtered_df_movimentacao.groupby(["Produto"])["Valor da Operação"].sum().reset_index()
unitPrice_sub_df_movimentacao = filtered_df_movimentacao.groupby(["Produto"])["Preço unitário"].first().reset_index()
#### plotting TOTAL
df_totalYear_gruped = filtered_df_movimentacao.groupby(["Date_month"])["Valor da Operação"].sum()

#colMovimentoMensal, colTotalMovimentacao = st.columns(2)

#------------------------------------
## Movimentação mensal
#------------------------------------
st.header("Movimentação mensal")

graphicRendimentoTotal = alt.Chart(operValue_sub_df_movimentacao).mark_bar(opacity=0.6).encode(
    x=alt.X("Produto", type="nominal", title="Tickers"),
    y=alt.Y("Valor da Operação", type="quantitative", title="Rendimento total recebido (R$)", axis=alt.Axis(orient="left"))
)

graphicMovimentoMensal = alt.Chart(unitPrice_sub_df_movimentacao).mark_circle().encode(
    x=alt.X("Produto", type="nominal", title="Tickers"),
    y=alt.Y2("Preço unitário", type="quantitative", title="Rendimento por cota (R$)", axis=alt.Axis(orient="right"))
)

c = alt.layer(graphicRendimentoTotal, graphicMovimentoMensal).resolve_scale(y='independent')

#with colMovimentoMensal:
st.altair_chart(c)


#------------------------------------
## Rendimento total mensal
#------------------------------------
st.header("Rendimento total")

#with colTotalMovimentacao:
st.bar_chart(df_totalYear_gruped)

#------------------------------------
## Rendimento total Anual
#------------------------------------
df_perYear = df_movimentacao.groupby("Date_year")["Valor da Operação"].sum()
st.bar_chart(df_perYear)

#------------------------------------
## Posicoes na carteira
#------------------------------------
container1 = st.container()
col1, col2 = st.columns(2)

auxQtdCotas = df_posicao[df_posicao["Código de Negociação"].isin(filtered_df_movimentacao["Produto"])]
pos_quantidadeCotas = go.Figure(data=[go.Pie(labels=auxQtdCotas["Código de Negociação"],
                                    values=auxQtdCotas.Quantidade,
                                    hole=.3)],
                                layout=go.Layout(showlegend=False,
                                        margin={'l': 0, 'r': 0, 't': 20, 'b': 0},
                                        title=go.layout.Title(text="FIIs - % quantidade de cotas")))

pos_quantidadeCotas.update_traces(textposition='inside', textinfo='label+percent')

auxValInvest = df_posicao[df_posicao["Código de Negociação"].isin(filtered_df_movimentacao["Produto"])]
pos_valorInvestido = go.Figure(data=[go.Pie(labels=auxValInvest["Código de Negociação"],
                                    values=auxValInvest["Valor Atualizado"],
                                    hole=.3)],
                                layout=go.Layout(showlegend=False,
                                        margin={'l': 0, 'r': 0, 't': 20, 'b': 0},
                                        title=go.layout.Title(text="FIIs - % valor investido")))
pos_valorInvestido.update_traces(textposition='inside', textinfo='label+percent')

                                    
with container1:
    with col1:
        st.plotly_chart(pos_quantidadeCotas, use_container_width=True)
    with col2:
        st.plotly_chart(pos_valorInvestido, use_container_width=True)

#------------------------------------
## Posicoes na carteira - versao 2
#------------------------------------
container2 = st.container()
col3, col4 = st.columns(2)

aux1 = df_posicao.groupby("Produto")["Quantidade"].sum().reset_index()
hPos_quantidadeCotas = alt.Chart(aux1, title="FIIs - Ranking por Quantidade de Cotas").mark_bar(opacity=0.6).encode(
    x=alt.X("Quantidade", type="quantitative", title="R$"),
    y=alt.Y("Produto", type="nominal", title="Tickers", sort='-x'),
)
aux2 = df_posicao.groupby("Produto")["Valor Atualizado"].sum().reset_index()
hPos_valorInvestido = alt.Chart(aux2, title="FIIs - Ranking por Valor Investido").mark_bar(opacity=0.6).encode(
    x=alt.X("Valor Atualizado", type="quantitative", title="R$"),
    y=alt.Y("Produto", type="nominal", title="Tickers", sort='-x'),
)

#text = hPos_quantidadeCotas.mark_text(align="left", baseline="middle", color='white').encode(
#        text=alt.Text("Valor Atualizado:Q", format=",.0f"))

with col3:
    st.altair_chart(hPos_quantidadeCotas, use_container_width=True)
with col4:
    st.altair_chart(hPos_valorInvestido, use_container_width=True)


#------------------------------------
## Posicoes na carteira - versao 3
#------------------------------------
import plotly.express as px
container3 = st.container()
col5, col6 = st.columns(2)

#df = px.data.tips()
fig = px.sunburst(df_posicao, path=['ticker_type','Código de Negociação', 'Quantidade'], values='Quantidade', title="Quantidade de Cotas")
fig2 = px.sunburst(df_posicao, path=['ticker_type','Código de Negociação', 'Valor Atualizado'], values='Valor Atualizado', title="Valor investido")

with container3:
    with col5:
        st.plotly_chart(fig, use_container_width=True)

    with col6:
        st.plotly_chart(fig2, use_container_width=True)
    

