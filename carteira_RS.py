import streamlit as st
import pandas as pd
import datetime as dt
import altair as alt
import plotly.graph_objects as go
import tkinter as tk
from tkinter import filedialog
import streamlit_authenticator as stauth
import yaml
from tickerType import *
import yfinance as yf
#import time

#####################################
#### Concatenate all excel files ####
#####################################
class CarteiraB3:
     
    def __init__(self):
        self.df_movimentacao = pd.DataFrame()
        self.df_negociacao = pd.DataFrame()
        self.df_posicao = pd.DataFrame()
        self.df_tickerType = pd.DataFrame()
        self.df_subscricoes = pd.DataFrame()
        self.df_desdobramentos = pd.DataFrame()
        self.filtered_df_movimentacao = pd.DataFrame()
        self.selected_movimentacao = []
        
    
    def getFiles(self):

        flag_files = {"Movimentação": False, "Negociação": False, "Posição": False, "Ticker types": False}

        uploaded_files = st.sidebar.file_uploader("Escolha os arquivos (*.xlsx)", type=["xls", "xlsx", "xlsm", "xlsb", "odf", "ods", "odt"], accept_multiple_files=True)

        for uploaded_file in uploaded_files:
            ## movimentacao (mandatory)
            if uploaded_file.name.startswith("movimentacao"):
                df = pd.read_excel(uploaded_file, engine="openpyxl")
                self.df_movimentacao = self.df_movimentacao.append(df,ignore_index=True)
                flag_files["Movimentação"] = True
            
            ## negociacao (mandatory)
            if uploaded_file.name.startswith("negociacao"):
                df = pd.read_excel(uploaded_file, engine="openpyxl")
                self.df_negociacao = self.df_negociacao.append(df,ignore_index=True)
                flag_files["Negociação"] = True

            ## posicao (mandatory)
            if uploaded_file.name.startswith("posicao"):
                df = pd.read_excel(uploaded_file, sheet_name="Fundo de Investimento")
                self.df_posicao = self.df_posicao.append(df,ignore_index=True)
                flag_files["Posição"] = True

            ## subscricoes
            if uploaded_file.name.startswith("subscricoes"):
                df_subs = pd.read_excel(uploaded_file, sheet_name="subscricoes")
                self.df_subscricoes = self.df_subscricoes.append(df_subs,ignore_index=True)

            ## desdobramentos
            if uploaded_file.name.startswith("desdobramento"):
                df = pd.read_excel(uploaded_file, sheet_name="desdobramentos")
                self.df_desdobramentos = self.df_desdobramentos.append(df,ignore_index=True)

            ## tickers type
            if uploaded_file.name.startswith("tickerTypes"):
                flag_files["Ticker types"] = True
                df = pd.read_excel(uploaded_file, sheet_name="ticker_type")
                self.df_tickerType = self.df_tickerType.append(df,ignore_index=True)
                
        if not flag_files["Ticker types"]: #take from internal database
            df = pd.DataFrame(list(dict_tickerTypes.items()), columns=['Ticker','Type'])
            self.df_tickerType = self.df_tickerType.append(df,ignore_index=True)
            flag_files["Ticker types"] = True
     

        msg = "Carregue os arquivos: " + ' | '.join([k for k in flag_files.keys() if flag_files[k] == False and k not in ["Ticker types"]])
 
        if all(flag_files.values()):
            st.sidebar.success('Arquivos carregados com sucesso!', icon="✅")
            self.processFiles()
        else:
            st.sidebar.warning(msg, icon="⚠️")

    
    def processFiles(self):
        #------------------------------------
        ## movimentacao
        #------------------------------------        
        self.df_movimentacao.drop_duplicates(keep='first', inplace=True)
        self.df_movimentacao=self.df_movimentacao[~self.df_movimentacao["Preço unitário"].isin(["-"])] # dropping rows with no values
        self.df_movimentacao['Produto'] = self.df_movimentacao.Produto.str.split(' -', expand=True).apply(lambda x: (x[0]), axis=1) # Formating ticker's name
        self.df_movimentacao['Data'] = pd.to_datetime(self.df_movimentacao['Data'], dayfirst=True)
        self.df_movimentacao['Date_month'] = self.df_movimentacao.Data.dt.to_period("M").astype("str")
        self.df_movimentacao['Date_year'] = self.df_movimentacao.Data.dt.year.astype("str")
        #st.dataframe(self.df_movimentacao)

        #------------------------------------
        ## negociacao
        #------------------------------------
        ### Adicionando subscricoes
        if not self.df_subscricoes.empty:
            self.df_negociacao = self.df_negociacao.append(self.df_subscricoes, ignore_index=True)

        self.df_negociacao.drop_duplicates(keep='first', inplace=True)
        self.df_negociacao['Data do Negócio'] = pd.to_datetime(self.df_negociacao['Data do Negócio'], dayfirst=True)

        

        #------------------------------------
        ## posicao
        #------------------------------------
        self.df_posicao=self.df_posicao.dropna() # dropping rows with no values
        # Add ticker type
        self.df_posicao['ticker_type'] = self.df_posicao['Código de Negociação'].map(self.df_tickerType.set_index('Ticker')["Type"])
        self.df_posicao['ticker_type'] = self.df_posicao['ticker_type'].fillna('TbD')
        self.df_posicao['percent'] = (self.df_posicao.Quantidade/self.df_posicao.Quantidade.sum())*100
        self.df_posicao['percent'] = self.df_posicao['percent'].round(decimals=2).astype('str') + ' %'


        #------------------------------------
        ## desdobramentos
        #------------------------------------
        if not self.df_desdobramentos.empty:
            self.df_desdobramentos['Data'] = pd.to_datetime(self.df_desdobramentos['Data'], dayfirst=True)

        ### Aplicar desdobramentos, se houver
        if not self.df_desdobramentos.empty:
            self.corrigeDesdobramentos()
        else:
            self.sideBar()
            self.precosMedio()

#############################################
#### Corrigindo desdobramentos ocorridos ####
#############################################
    def corrigeDesdobramentos(self):
        for ticker in self.df_desdobramentos.Tickers:
            data_desdobramento = pd.Timestamp(self.df_desdobramentos.loc[self.df_desdobramentos.Tickers == ticker, "Data"].values[0])
            proporcao = float(self.df_desdobramentos.loc[self.df_desdobramentos.Tickers == ticker, "proporcao"].values[0])
           

            self.df_negociacao.loc[(self.df_negociacao["Data do Negócio"] <= data_desdobramento) &\
                                (self.df_negociacao["Código de Negociação"] == ticker) | \
                                (self.df_negociacao["Código de Negociação"] == ticker + "F"), "Quantidade"] = self.df_negociacao.loc[(self.df_negociacao["Data do Negócio"] <= data_desdobramento) &\
                                                                                                            (self.df_negociacao["Código de Negociação"] == ticker) | \
                                                                                                            (self.df_negociacao["Código de Negociação"] == ticker + "F"), "Quantidade"] * proporcao

            self.df_negociacao.loc[(self.df_negociacao["Data do Negócio"] <= data_desdobramento) &\
                                (self.df_negociacao["Código de Negociação"] == ticker) | \
                                (self.df_negociacao["Código de Negociação"] == ticker + "F"), "Preço"] = self.df_negociacao.loc[(self.df_negociacao["Data do Negócio"] <= data_desdobramento) &\
                                                                                                        (self.df_negociacao["Código de Negociação"] == ticker) | \
                                                                                                        (self.df_negociacao["Código de Negociação"] == ticker + "F"), "Preço"] / proporcao
       
        self.sideBar()
        self.precosMedio()

#################################
#### Filters sideBar         ####
#################################   
    def sideBar(self):
        st.sidebar.write("Filtros")
        
        ### Movimentacao
        allMovimentacao = self.df_movimentacao["Movimentação"].drop_duplicates(keep='first', inplace=False)
        all_option_movimentacao = st.sidebar.checkbox("Selecione todas as Movimentações")
        
        if all_option_movimentacao:
            self.selected_movimentacao = st.sidebar.multiselect('Selecione as Movimentações:', allMovimentacao, default=allMovimentacao)
        else:
            self.selected_movimentacao = st.sidebar.multiselect('Selecione as Movimentações:', allMovimentacao, default=["Rendimento", "Juros Sobre Capital Próprio", "Dividendo"])

        ### Tickers
        allTickers = self.df_movimentacao.loc[(self.df_movimentacao["Movimentação"].isin(self.selected_movimentacao)), "Produto"].drop_duplicates(keep='first', inplace=False)
        all_options_ticker = st.sidebar.checkbox("Selecione todos Tickers")
        if all_options_ticker:
            selected_tickers = st.sidebar.multiselect('Selecione os Tickers:', allTickers, default=allTickers)
        else:
            selected_tickers = st.sidebar.multiselect('Selecione os Tickers:', allTickers, default=["MXRF11"])

        min_Value=pd.to_datetime(self.df_movimentacao.Data.min())
        max_Value=pd.to_datetime(self.df_movimentacao.Data.max())

        selected_date_begin = st.sidebar.date_input('Data de Inicio',  value=min_Value, min_value=min_Value, max_value=max_Value)
        selected_date_end = st.sidebar.date_input('Data de Fim',  value=max_Value, min_value=min_Value, max_value=max_Value)

        # Show the data as a dataframe.
        self.filtered_df_movimentacao = self.df_movimentacao.loc[(self.df_movimentacao.Produto.isin(selected_tickers)) & \
                                    self.df_movimentacao["Movimentação"].isin(self.selected_movimentacao) & \
                                    (self.df_movimentacao.Data >= dt.datetime.combine(selected_date_begin, dt.datetime.min.time())) & \
                                    (self.df_movimentacao.Data <= dt.datetime.combine(selected_date_end, dt.datetime.min.time()))]
        #st.dataframe(self.filtered_df_movimentacao)

        self.plotting()

#################################
####    Colorir celulas   ####
################################# 
    # def _color_cell(self, val1):
    #     st.write(val1)
    #     color = 'red' if val1 < 100 else 'green'
    #     return 'color: {}'.format(color)
    def _color_cell(self, x):
        c1 = 'color: red'
        c2 = '' 
        #compare columns
        mask = x['Preco_medio'] > x['Preco Atual']
        #DataFrame with same index and columns names as original filled empty strings
        df1 =  pd.DataFrame(c2, index=x.index, columns=x.columns)
        #modify values of df1 column by boolean mask
        df1.loc[mask, 'Preco_medio'] = c1
        return df1       

#################################
####    Tabela preco medio   ####
################################# 
    def precosMedio(self):
        st.write('Preços medios (R$)')
        df_synthesis = self.df_negociacao.groupby("Código de Negociação").sum()
        df_synthesis.drop(['Preço'], axis=1, inplace=True)
        df_synthesis["Preco_medio"] = df_synthesis["Valor"]/df_synthesis["Quantidade"]
        df_synthesis.rename(columns={"Valor": "Valor Investido", "Quantidade": "Numero de quotas"}, inplace=True)

        #### Add Ticker live prices
        with st.spinner("Pesquisando valores atuais..."):
            try:
                for tkt, row in df_synthesis.iterrows():
                    tker = yf.Ticker(tkt+".SA")
                    precoAtual = tker.fast_info.last_price
                    df_synthesis.loc[tkt, "Preco Atual"] = precoAtual
                    
                    
                #df_synthesis.style.applymap(self._color_cell)#("background-color: darkorange")
                st.dataframe(df_synthesis.style.format(subset=['Valor Investido', 'Preco_medio', 'Preco Atual'], formatter="{:.2f}")\
                                                .apply(self._color_cell, subset=['Preco_medio', 'Preco Atual'], axis=None))
            except:
                st.warning("Não foi possível receber os valores atuais do yFinance. Atualize a página!")
                st.dataframe(df_synthesis.style.format(subset=['Valor Investido', 'Preco_medio'], formatter="{:.2f}"))


#################################
####    Plotting             ####
#################################
    def plotting(self):
        #### groupping multiple rows from the same ticker and creating a new dataframe to be plotted
        operValue_sub_df_movimentacao = self.filtered_df_movimentacao.groupby(["Produto"])["Valor da Operação"].sum().reset_index()
        unitPrice_sub_df_movimentacao = self.filtered_df_movimentacao.groupby(["Produto"])["Preço unitário"].first().reset_index()
        #### plotting TOTAL
        df_totalYear_gruped = self.filtered_df_movimentacao.groupby(["Date_month"])["Valor da Operação"].sum()
        #st.dataframe(df_totalYear_gruped)
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
        st.header("Rendimento total (R$)")

        #with colTotalMovimentacao:
        st.bar_chart(df_totalYear_gruped)

        #------------------------------------
        ## Rendimento total Anual
        #------------------------------------
        aux_perYear = self.df_movimentacao.loc[self.df_movimentacao["Movimentação"].isin(self.selected_movimentacao)]
        df_perYear = aux_perYear.groupby("Date_year")["Valor da Operação"].sum()
        #st.dataframe(df_perYear)
        st.bar_chart(df_perYear)

        #------------------------------------
        ## Posicoes na carteira
        #------------------------------------
        container1 = st.container()
        col1, col2 = st.columns(2)

        auxQtdCotas = self.df_posicao[self.df_posicao["Código de Negociação"].isin(self.filtered_df_movimentacao["Produto"])]
        pos_quantidadeCotas = go.Figure(data=[go.Pie(labels=auxQtdCotas["Código de Negociação"],
                                            values=auxQtdCotas.Quantidade,
                                            hole=.3)],
                                        layout=go.Layout(showlegend=False,
                                                margin={'l': 0, 'r': 0, 't': 20, 'b': 0},
                                                title=go.layout.Title(text="FIIs - % quantidade de cotas")))

        pos_quantidadeCotas.update_traces(textposition='inside', textinfo='label+percent')

        auxValInvest = self.df_posicao[self.df_posicao["Código de Negociação"].isin(self.filtered_df_movimentacao["Produto"])]
        pos_valorInvestido = go.Figure(data=[go.Pie(labels=auxValInvest["Código de Negociação"],
                                            values=auxValInvest["Valor Atualizado"],
                                            hole=.3)],
                                        layout=go.Layout(showlegend=False,
                                                margin={'l': 0, 'r': 0, 't': 20, 'b': 0},
                                                title=go.layout.Title(text="FIIs - % valor de mercado")))
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

        aux1 = self.df_posicao.groupby("Produto")["Quantidade"].sum().reset_index()
        hPos_quantidadeCotas = alt.Chart(aux1, title="FIIs - Ranking por Quantidade de Cotas").mark_bar(opacity=0.6).encode(
            x=alt.X("Quantidade", type="quantitative", title="Número de cotas"),
            y=alt.Y("Produto", type="nominal", title="Tickers", sort='-x'),
        )
        aux2 = self.df_posicao.groupby("Produto")["Valor Atualizado"].sum().reset_index()
        hPos_valorInvestido = alt.Chart(aux2, title="FIIs - Ranking por valor de mercado").mark_bar(opacity=0.6).encode(
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
        fig = px.sunburst(self.df_posicao, path=['ticker_type','Código de Negociação', 'Quantidade'], values='Quantidade', title="Quantidade de Cotas")
        fig2 = px.sunburst(self.df_posicao, path=['ticker_type','Código de Negociação', 'Valor Atualizado'], values='Valor Atualizado', title="Valor de mercado (R$)")

        with container3:
            with col5:
                st.plotly_chart(fig, use_container_width=True)

            with col6:
                st.plotly_chart(fig2, use_container_width=True)
            

if __name__ == "__main__":
    st.set_page_config(layout="wide")

    st.markdown("<h1 style='text-align: center; color: tomato;'>CarteiraR</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: tomato;'>(V 0.1)</h3>", unsafe_allow_html=True)
   

    ####### Login

    with open('config.yaml') as file:
        config = yaml.safe_load(file)
    
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    ) 

    name, authentication_status, username = authenticator.login('Login', 'main')

    if st.session_state["authentication_status"]:
        st.write(f'Bem vindo *{st.session_state["name"]}*')
        authenticator.logout('Logout', 'main')

        myAssets = CarteiraB3()
        myAssets.getFiles()

    elif st.session_state["authentication_status"] is False:
        st.error('Username/password is incorrect')
    elif st.session_state["authentication_status"] is None:
        st.warning('Please enter your username and password')
    
