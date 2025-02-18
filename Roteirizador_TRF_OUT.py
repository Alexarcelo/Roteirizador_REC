import streamlit as st
import mysql.connector
import decimal
import pandas as pd
from datetime import timedelta, time, datetime
from collections import Counter
import gspread 
from itertools import combinations
import requests
from google.cloud import secretmanager 
import json
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account

def gerar_df_phoenix(vw_name, base_luck):
    
    data_hoje = datetime.now()

    data_hoje_str = data_hoje.strftime("%Y-%m-%d")

    # Parametros de Login AWS
    config = {
    'user': 'user_automation_jpa',
    'password': 'luck_jpa_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': base_luck
    }
    # Conexão as Views
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()

    if base_luck=='test_phoenix_maceio':

        if vw_name=='vw_router':

            request_name = f'SELECT * FROM {vw_name} WHERE {vw_name}.`Data Execucao`>={data_hoje_str}'

        elif vw_name=='vw_payment_guide':

            request_name = f"SELECT 'Tipo de Servico', 'Reserva', 'Escala' FROM {vw_name}"

    else:

        request_name = f'SELECT * FROM {vw_name} WHERE {vw_name}.`Data Execucao`>={data_hoje_str}'

    # Script MySql para requests
    cursor.execute(
        request_name
    )
    # Coloca o request em uma variavel
    resultado = cursor.fetchall()
    # Busca apenas o cabecalhos do Banco
    cabecalho = [desc[0] for desc in cursor.description]

    # Fecha a conexão
    cursor.close()
    conexao.close()

    # Coloca em um dataframe e muda o tipo de decimal para float
    df = pd.DataFrame(resultado, columns=cabecalho)
    df = df.applymap(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)
    return df

def puxar_sequencias_hoteis(id_gsheet, lista_abas, lista_nomes_df_hoteis):

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(id_gsheet)

    for index in range(len(lista_abas)):

        aba = lista_abas[index]

        df_hotel = lista_nomes_df_hoteis[index]
        
        sheet = spreadsheet.worksheet(aba)

        sheet_data = sheet.get_all_values()

        st.session_state[df_hotel] = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

        st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'] = \
        st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'] = \
        pd.to_numeric(st.session_state[df_hotel]['Hoteis Juntos p/ Apoios'], errors='coerce')

        st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'] = \
        st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'] = \
        pd.to_numeric(st.session_state[df_hotel]['Hoteis Juntos p/ Carro Principal'], errors='coerce')

        st.session_state[df_hotel]['Bus'] = \
        st.session_state[df_hotel]['Bus'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Micro'] = \
        st.session_state[df_hotel]['Micro'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Van'] = \
        st.session_state[df_hotel]['Van'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Utilitario'] = \
        st.session_state[df_hotel]['Utilitario'].apply(lambda x: None if pd.isna(x) or str(x).strip() == '' else x)

        st.session_state[df_hotel]['Sequência'] = pd.to_numeric(st.session_state[df_hotel]['Sequência'], errors='coerce')

def transformar_timedelta(intervalo):
    
    intervalo = timedelta(hours=intervalo.hour, minutes=intervalo.minute, seconds=intervalo.second)

    return intervalo

def objeto_intervalo(titulo, valor_padrao, chave):

    intervalo_ref = st.time_input(label=titulo, value=valor_padrao, key=chave, step=300)
    
    intervalo_ref = transformar_timedelta(intervalo_ref)

    return intervalo_ref

def verificar_cadeirante(observacao):
    palavra = "CADEIRANTE"
    observacao_upper = str(observacao).upper()

    # Contador de letras da palavra 'CADEIRANTE'
    contador_cadeirante = Counter(palavra)

    # Divide a observação em palavras
    palavras_observacao = observacao_upper.split()

    # Verifica cada palavra individualmente
    for palavra_observacao in palavras_observacao:
        contador_palavra = Counter(palavra_observacao)

        # Verifica se todas as letras de 'CADEIRANTE' estão presentes na palavra
        for letra, quantidade in contador_cadeirante.items():
            if contador_palavra[letra] < quantidade:
                break  # Se faltar uma letra, passa para a próxima palavra
        else:
            # Se a palavra passou pela verificação, retorna True
            return True

    # Se nenhuma palavra contém todas as letras de 'CADEIRANTE', retorna False
    return False

def gerar_itens_faltantes(df_servicos, df_hoteis):

    lista_hoteis_df_router = df_servicos['Est Origem'].unique().tolist()

    lista_hoteis_sequencia = df_hoteis['Est Origem'].unique().tolist()

    itens_faltantes = set(lista_hoteis_df_router) - set(lista_hoteis_sequencia)

    itens_faltantes = list(itens_faltantes)

    return itens_faltantes, lista_hoteis_df_router

def inserir_hoteis_faltantes(itens_faltantes, aba_excel, regiao, id_gsheet):

    df_itens_faltantes = pd.DataFrame(itens_faltantes, columns=['Est Origem'])

    st.dataframe(df_itens_faltantes, hide_index=True)

    df_itens_faltantes[['Região', 'Sequência', 'Bus', 'Micro', 'Van', 'Utilitario', 'Hoteis Juntos p/ Apoios', 'Hoteis Juntos p/ Carro Principal']]=''

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)
    
    spreadsheet = client.open_by_key(id_gsheet)

    sheet = spreadsheet.worksheet(aba_excel)
    sheet_data = sheet.get_all_values()
    last_filled_row = len(sheet_data)
    data = df_itens_faltantes.values.tolist()
    start_row = last_filled_row + 1
    start_cell = f"A{start_row}"
    
    sheet.update(start_cell, data)

    st.error(f'Os hoteis acima não estão cadastrados na lista de sequência de hoteis. Eles foram inseridos no final da lista de {regiao}. Por favor, coloque-os na sequência e tente novamente')

def ordenar_juncoes(df_router_ref):

    max_juncao = df_router_ref['Junção'].dropna().max()

    if pd.isna(max_juncao):

        max_juncao = 0

    for juncao in range(1, int(max_juncao) + 1):

        df_ref = df_router_ref[(df_router_ref['Modo do Servico']=='REGULAR') & (df_router_ref['Junção']==juncao)].sort_values(by='Sequência', ascending=False)\
            .reset_index()

        if len(df_ref)>0:

            index_inicial = df_ref['index'].min()
    
            index_final = df_ref['index'].max()
    
            df_ref = df_ref.drop('index', axis=1)
    
            df_router_ref.iloc[index_inicial:index_final+1] = df_ref

    return df_router_ref

def colocar_menor_horario_juncao(df_router_ref, df_juncao_voos):

    df_menor_horario = pd.DataFrame(columns=['Junção', 'Menor Horário'])

    contador=0

    for juncao in df_juncao_voos['Junção'].unique().tolist():

        menor_horario = df_juncao_voos[df_juncao_voos['Junção']==juncao]['Horário'].min()

        df_menor_horario.at[contador, 'Junção']=juncao

        df_menor_horario.at[contador, 'Menor Horário']=menor_horario

        contador+=1

    df_router_ref = pd.merge(df_router_ref, df_menor_horario, on='Junção', how='left')

    return df_router_ref

def criar_df_servicos_2(df_servicos, df_juncao_voos, df_hoteis):

    # Criando coluna de paxs totais

    df_servicos['Total ADT | CHD'] = df_servicos['Total ADT'] + df_servicos['Total CHD']    

    # Preenchendo coluna 'Data Horario Apresentacao'

    df_servicos['Data Horario Apresentacao'] = pd.to_datetime(df_servicos['Data Voo'].astype(str) + ' ' + df_servicos['Horario Voo'].astype(str))
    
    # Criando coluna de Junção através de pd.merge

    df_servicos_2 = pd.merge(df_servicos, df_juncao_voos[['Servico', 'Voo', 'Junção']], on=['Servico', 'Voo'], how='left')

    # Criando colunas Micro Região e Sequência através de pd.merge

    df_servicos_2 = pd.merge(df_servicos_2, df_hoteis, on='Est Origem', how='left')

    # Ordenando dataframe por ['Modo do Servico', 'Servico', 'Junção', 'Voo', 'Sequência']

    df_servicos_2 = df_servicos_2.sort_values(by=['Modo do Servico', 'Junção', 'Voo', 'Sequência'], 
                                              ascending=[True, True, True, False]).reset_index(drop=True)

    # Ordenando cada junção pela sequência de hoteis

    df_servicos_2 = ordenar_juncoes(df_servicos_2)

    # Colocando qual o menor horário de cada junção

    df_servicos_2 = colocar_menor_horario_juncao(df_servicos_2, df_juncao_voos)

    # Identificar tipo de translado das junções

    df_voos_internacionais = pd.merge(df_juncao_voos[['Voo', 'Junção']], df_servicos_2[['Voo', 'Tipo do Translado']].drop_duplicates(), on='Voo', how='left')

    df_voos_internacionais = df_voos_internacionais[df_voos_internacionais['Tipo do Translado']=='Internacional'][['Junção', 'Tipo do Translado']]\
        .drop_duplicates().reset_index(drop=True)
    
    df_voos_internacionais = df_voos_internacionais.rename(columns={'Tipo do Translado': 'Tipo do Translado Junção'})

    df_servicos_2 = pd.merge(df_servicos_2, df_voos_internacionais, on='Junção', how='left')

    # Criando colunas Roteiro e Carros

    df_servicos_2['Roteiro']=0

    df_servicos_2['Carros']=0

    return df_servicos_2

def inserir_coluna_horario_ultimo_hotel(df_router_filtrado_2):
    
    df_router_filtrado_2['Antecipação Último Hotel'] = pd.NaT

    lista_horarios_esp = st.session_state.df_horario_esp_ultimo_hotel['Junção/Voo/Reserva'].unique().tolist()

    for index in range(len(df_router_filtrado_2)):

        voo_ref = df_router_filtrado_2.at[index, 'Voo']

        juncao_ref = df_router_filtrado_2.at[index, 'Junção']

        reserva_ref = df_router_filtrado_2.at[index, 'Reserva']

        if voo_ref in lista_horarios_esp:
            intervalor_inicial_ref = st.session_state.df_horario_esp_ultimo_hotel.loc[
                st.session_state.df_horario_esp_ultimo_hotel['Junção/Voo/Reserva'] == voo_ref, 
                'Antecipação Último Hotel'
            ].iloc[0]

            # Converter para timedelta, assumindo que o valor é uma string no formato "HH:MM:SS"
            df_router_filtrado_2.at[index, 'Antecipação Último Hotel'] = intervalor_inicial_ref

        elif juncao_ref in lista_horarios_esp:
            intervalor_inicial_ref = st.session_state.df_horario_esp_ultimo_hotel.loc[
                st.session_state.df_horario_esp_ultimo_hotel['Junção/Voo/Reserva'] == juncao_ref, 
                'Antecipação Último Hotel'
            ].iloc[0]

            # Converter para timedelta corretamente
            df_router_filtrado_2.at[index, 'Antecipação Último Hotel'] = intervalor_inicial_ref

        elif reserva_ref in lista_horarios_esp:
            intervalor_inicial_ref = st.session_state.df_horario_esp_ultimo_hotel.loc[
                st.session_state.df_horario_esp_ultimo_hotel['Junção/Voo/Reserva'] == reserva_ref, 
                'Antecipação Último Hotel'
            ].iloc[0]

            # Converter para timedelta corretamente
            df_router_filtrado_2.at[index, 'Antecipação Último Hotel'] = intervalor_inicial_ref

    df_router_filtrado_2['Antecipação Último Hotel'] = df_router_filtrado_2['Antecipação Último Hotel'].dt.time

    return df_router_filtrado_2

def definir_horario_primeiro_hotel(df, index):

    servico = df.at[index, 'Servico']

    data_voo = df.at[index, 'Data Voo']

    # nome_voo = df.at[index, 'Voo']

    # regiao = df.at[index, 'Região']

    if 'Junção' in df.columns.tolist():

        juncao = df.at[index, 'Junção']

    else:

        juncao = None

    modo = df.at[index, 'Modo do Servico']

    if pd.isna(juncao) or modo!='REGULAR':

        hora_voo = df.at[index, 'Horario Voo']

        tipo_voo = df.at[index, 'Tipo do Translado']

    else:

        hora_voo = df.at[index, 'Menor Horário']

        tipo_voo = 'Nacional'

    data_hora_voo_str = f'{data_voo} {hora_voo}'

    data_hora_voo = pd.to_datetime(data_hora_voo_str, format='%Y-%m-%d %H:%M:%S')

    horario_ultimo_hotel = df.at[index, 'Antecipação Último Hotel']

    if pd.isna(horario_ultimo_hotel):

        if (servico=='OUT (PORTO DE GALINHAS)' or servico=='OUT (SERRAMBI)' or servico=='OUT (CABO DE STO AGOSTINHO)') and \
            (hora_voo>=pd.to_datetime('11:00:00').time()):

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(time(4, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_pga_cab_pos_11)

        elif (servico=='OUT (PORTO DE GALINHAS)' or servico=='OUT (SERRAMBI)' or servico=='OUT (CABO DE STO AGOSTINHO)') and \
            hora_voo<pd.to_datetime('11:00:00').time():

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(time(4, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_pga_cab_pre_11)

        elif servico=='OUT (BOA VIAGEM | PIEDADE)':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(time(3, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_rec)

        elif servico=='OUT (MARAGOGI | JAPARATINGA)':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(time(5, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_mar_jpa)

        elif servico=='OUT (OLINDA)' or servico=='OUT RECIFE (CENTRO)':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(time(3, 30))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_ol)

        elif servico=='OUT (FAZENDA NOVA)' or servico=='OUT (JOÃO PESSOA-PB)' or servico=='OUT (MILAGRES)':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(time(6, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_mil)

        elif servico=='OUT (CARNEIROS I TAMANDARÉ)':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(time(4, 30))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_carneiros)

        elif servico=='OUT (ALAGOAS)' or servico=='OUT (MACEIÓ-AL)':

            if tipo_voo=='Internacional':

                return data_hora_voo - transformar_timedelta(time(7, 0))

            else:

                return data_hora_voo - transformar_timedelta(st.session_state.intervalo_inicial_mcz)

    else:

        horario_ultimo_hotel = transformar_timedelta(horario_ultimo_hotel)

        return data_hora_voo - horario_ultimo_hotel

def roteirizar_hoteis_mais_pax_max(df_servicos, roteiro, df_hoteis_pax_max):

    # Roteirizando reservas com mais paxs que a capacidade máxima da frota

    df_ref_reservas_pax_max = df_servicos.groupby(['Modo do Servico', 'Reserva', 'Servico', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_reservas_pax_max = df_ref_reservas_pax_max[df_ref_reservas_pax_max['Total ADT | CHD']>=st.session_state.pax_max].reset_index()

    if len(df_ref_reservas_pax_max)>0:

        carro=0

        for index in range(len(df_ref_reservas_pax_max)):

            roteiro+=1

            pax_ref = df_ref_reservas_pax_max.at[index, 'Total ADT | CHD']

            modo = df_ref_reservas_pax_max.at[index, 'Modo do Servico']

            servico = df_ref_reservas_pax_max.at[index, 'Servico']

            reserva_ref = df_ref_reservas_pax_max.at[index, 'Reserva']

            hotel = df_ref_reservas_pax_max.at[index, 'Est Origem']

            st.warning(f'O hotel {hotel} da reserva {reserva_ref} tem {pax_ref} paxs e, portanto vai ser roteirizado em um ônibus')

            carro+=1

            df_hotel_pax_max = df_servicos[(df_servicos['Reserva']==reserva_ref)].reset_index()

            df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index, 'index'])

            df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index]]], ignore_index=True)

            df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

            df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    # Roteirizando junções com mais paxs que a capacidade máxima da frota

    df_ref_com_juncao = df_servicos[(df_servicos['Bus']=='X') & ~(pd.isna(df_servicos['Junção']))]\
        .groupby(['Modo do Servico', 'Servico', 'Junção', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_com_juncao = df_ref_com_juncao[df_ref_com_juncao['Total ADT | CHD']>=st.session_state.pax_max].reset_index()

    if len(df_ref_com_juncao)>0:

        for index in range(len(df_ref_com_juncao)):

            carro=0

            roteiro+=1

            pax_ref = df_ref_com_juncao.at[index, 'Total ADT | CHD']

            loops = int(pax_ref//st.session_state.pax_max)

            modo = df_ref_com_juncao.at[index, 'Modo do Servico']

            servico = df_ref_com_juncao.at[index, 'Servico']

            ref_juncao = df_ref_com_juncao.at[index, 'Junção']

            hotel = df_ref_com_juncao.at[index, 'Est Origem']

            st.warning(f'O hotel {hotel} da junção {ref_juncao} tem {pax_ref} paxs e, portanto vai ser roteirizado em um ônibus')

            for loop in range(loops):

                carro+=1

                df_hotel_pax_max = df_servicos[(df_servicos['Modo do Servico']==modo) & (df_servicos['Servico']==servico) & 
                                                (df_servicos['Junção']==ref_juncao) & (df_servicos['Est Origem']==hotel)].reset_index()
                
                paxs_total_ref = 0
                
                for index_2, value in df_hotel_pax_max['Total ADT | CHD'].items():

                    if paxs_total_ref+value>st.session_state.pax_max:

                        break

                    else:

                        paxs_total_ref+=value

                        df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index_2, 'index'])

                        df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index_2]]], ignore_index=True)

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    # Roteirizando voos com mais paxs que a capacidade máxima da frota

    df_ref_sem_juncao = df_servicos[(df_servicos['Bus']=='X') & (pd.isna(df_servicos['Junção']))]\
        .groupby(['Modo do Servico', 'Servico', 'Voo', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_sem_juncao = df_ref_sem_juncao[df_ref_sem_juncao['Total ADT | CHD']>=st.session_state.pax_max].reset_index()

    if len(df_ref_sem_juncao)>0:

        for index in range(len(df_ref_sem_juncao)):

            carro=0

            roteiro+=1

            pax_ref = df_ref_sem_juncao.at[index, 'Total ADT | CHD']

            loops = int(pax_ref//st.session_state.pax_max)

            modo = df_ref_sem_juncao.at[index, 'Modo do Servico']

            servico = df_ref_sem_juncao.at[index, 'Servico']

            ref_voo = df_ref_sem_juncao.at[index, 'Voo']

            hotel = df_ref_sem_juncao.at[index, 'Est Origem']

            st.warning(f'O hotel {hotel} do voo {ref_voo} tem {pax_ref} paxs e, portanto vai ser roteirizado em um ônibus')

            for loop in range(loops):

                carro+=1

                df_hotel_pax_max = df_servicos[(df_servicos['Modo do Servico']==modo) & (df_servicos['Servico']==servico) & 
                                                (df_servicos['Voo']==ref_voo) & (df_servicos['Est Origem']==hotel)].reset_index()
                
                paxs_total_ref = 0
                
                for index_2, value in df_hotel_pax_max['Total ADT | CHD'].items():

                    if paxs_total_ref+value>st.session_state.pax_max:

                        break

                    else:

                        paxs_total_ref+=value

                        df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index_2, 'index'])

                        df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index_2]]], ignore_index=True)

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    # Transformando colunas 'Horario Voo' e 'Menor Horário' em datetime

    if len(df_hoteis_pax_max)>0:

        df_hoteis_pax_max['Horario Voo'] = pd.to_datetime(df_hoteis_pax_max['Horario Voo'], format='%H:%M:%S').dt.time
    
        df_hoteis_pax_max['Menor Horário'] = pd.to_datetime(df_hoteis_pax_max['Menor Horário'], format='%H:%M:%S').dt.time

    # Definindo horários de cada linha de df_hoteis_pax_max com a função definir_horario_primeiro_hotel

    for index in range(len(df_hoteis_pax_max)):

        df_hoteis_pax_max.at[index, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel(df_hoteis_pax_max, index)

    # Resetando os índices de df_servicos porque houve exclusão de linhas

    df_servicos = df_servicos.reset_index(drop=True)

    # Excluindo coluna 'index' do dataframe df_hoteis_pax_max

    if 'index' in df_hoteis_pax_max.columns.tolist():

        df_hoteis_pax_max = df_hoteis_pax_max.drop(columns=['index'])

    return df_servicos, df_hoteis_pax_max, roteiro

def definir_intervalo_ref(df, value):

    if ((df.at[value-1, 'Região']!='SERRAMBI') & (df.at[value, 'Região']=='SERRAMBI')) | ((df.at[value-1, 'Est Origem']=='SAMOA BEACH RESORT')) | ((df.at[value-1, 'Est Origem']=='NUI SUPREME')) | \
        ((df.at[value-1, 'Est Origem']=='LA FLEUR POLINESIA RESIDENCE E RESORT MURO ALTO')):

        return transformar_timedelta(st.session_state.intervalo_hoteis_bairros_iguais)*2
    
    elif (df.at[value-1, 'Região']!='JAPARATINGA') & (df.at[value, 'Região']=='JAPARATINGA'):

        return transformar_timedelta(st.session_state.intervalo_hoteis_bairros_iguais)*2

    else:

        return transformar_timedelta(st.session_state.intervalo_hoteis_bairros_iguais) 

def roteirizar_privativos(roteiro, df_servicos, index):

    roteiro+=1

    df_servicos.at[index, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel(df_servicos, index)
    
    df_servicos.at[index, 'Roteiro'] = roteiro
    
    df_servicos.at[index, 'Carros'] = 1

    return roteiro, df_servicos

def preencher_roteiro_carros(df_servicos, roteiro, carros, value):

    df_servicos.at[value, 'Roteiro'] = roteiro

    df_servicos.at[value, 'Carros'] = carros

    return df_servicos

def abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel):

    carros+=1

    df_servicos.at[value, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel(df_servicos, index)

    data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']

    paxs_total_roteiro = 0

    bairro = ''

    paxs_total_roteiro+=paxs_hotel

    df_servicos.at[value, 'Roteiro'] = roteiro

    df_servicos.at[value, 'Carros'] = carros

    return carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro

def contar_hoteis_df(df_ref):

    df_ref_contagem_hoteis = df_ref.groupby('Est Origem')['Hoteis Juntos p/ Carro Principal'].first().reset_index()

    hoteis_mesmo_voo=0

    for index in range(len(df_ref_contagem_hoteis)):

        if index==0:

            hoteis_mesmo_voo+=1

        elif not ((df_ref_contagem_hoteis.at[index, 'Hoteis Juntos p/ Carro Principal']==
                  df_ref_contagem_hoteis.at[index-1, 'Hoteis Juntos p/ Carro Principal']) and 
                  (~pd.isna(df_ref_contagem_hoteis.at[index, 'Hoteis Juntos p/ Carro Principal']))):

            hoteis_mesmo_voo+=1

    return hoteis_mesmo_voo

def gerar_horarios_apresentacao(df_servicos, roteiro, max_hoteis):

    for index in range(len(df_servicos)):

        if df_servicos.at[index, 'Modo do Servico']=='PRIVATIVO POR VEICULO' or df_servicos.at[index, 'Modo do Servico']=='PRIVATIVO POR PESSOA' or \
            df_servicos.at[index, 'Modo do Servico']=='CADEIRANTE' or df_servicos.at[index, 'Modo do Servico']=='EXCLUSIVO':

            roteiro, df_servicos = roteirizar_privativos(roteiro, df_servicos, index)

        elif df_servicos.at[index, 'Modo do Servico']=='REGULAR':

            juntar = df_servicos.at[index, 'Junção']

            voo = df_servicos.at[index, 'Voo']

            if pd.isna(juntar):

                df_ref = df_servicos[(df_servicos['Modo do Servico']=='REGULAR') & (df_servicos['Voo']==voo)].reset_index()

                index_inicial = df_ref['index'].min()              
                
                hoteis_mesmo_voo = contar_hoteis_df(df_ref)

                if index==index_inicial:

                    if hoteis_mesmo_voo<=max_hoteis:

                        roteiro+=1

                        carros = 1

                        paxs_total_roteiro = 0

                        bairro = ''

                        for index_2, value in df_ref['index'].items():

                            if value==index_inicial:

                                df_servicos.at[value, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel(df_servicos, value)
                                
                                data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']
                                
                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                paxs_total_roteiro+=paxs_hotel

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            elif (df_servicos.at[value, 'Est Origem']==df_servicos.at[value-1, 'Est Origem']) | (df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[value-1, 'Hoteis Juntos p/ Carro Principal']):

                                df_servicos.at[value, 'Data Horario Apresentacao']=df_servicos.at[value-1, 'Data Horario Apresentacao']

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            else:

                                bairro=df_servicos.at[value, 'Região']

                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                                    carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)

                                else:

                                    paxs_total_roteiro+=paxs_hotel

                                    if bairro!='':

                                        intervalo_ref = definir_intervalo_ref(df_servicos, value)
                                        
                                    if paxs_hotel>=st.session_state.pax_cinco_min:

                                        intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                    data_horario_hotel = df_servicos.at[value-1, 'Data Horario Apresentacao']-intervalo_ref

                                    if  data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                                        carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)

                                    else:

                                        df_servicos.at[value, 'Data Horario Apresentacao']=data_horario_hotel

                                        df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                    else:

                        roteiro+=1

                        carros = 1

                        paxs_total_roteiro = 0

                        contador_hoteis = 0

                        bairro = ''

                        for index_2, value in df_ref['index'].items():

                            if value==index_inicial:

                                df_servicos.at[value, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel(df_servicos, value)
                                
                                data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']
                                
                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                paxs_total_roteiro+=paxs_hotel

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                                contador_hoteis+=1

                            elif (df_servicos.at[value, 'Est Origem']==df_servicos.at[value-1, 'Est Origem']) | (df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[value-1, 'Hoteis Juntos p/ Carro Principal']):

                                df_servicos.at[value, 'Data Horario Apresentacao']=df_servicos.at[value-1, 'Data Horario Apresentacao']

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            else:

                                contador_hoteis+=1

                                bairro=df_servicos.at[value, 'Região']

                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                if contador_hoteis>max_hoteis:

                                    carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                    
                                    contador_hoteis = 1
                                    
                                else:

                                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                                        carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                        
                                        contador_hoteis = 1

                                    else:

                                        paxs_total_roteiro+=paxs_hotel

                                        if bairro!='':

                                            intervalo_ref = definir_intervalo_ref(df_servicos, value)
                                            
                                        if paxs_hotel>=st.session_state.pax_cinco_min:

                                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                        data_horario_hotel = df_servicos.at[value-1, 'Data Horario Apresentacao']-intervalo_ref

                                        if  data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                                            carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                            
                                            contador_hoteis = 1

                                        else:

                                            df_servicos.at[value, 'Data Horario Apresentacao']=data_horario_hotel

                                            df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

            else:

                df_ref = df_servicos[(df_servicos['Modo do Servico']=='REGULAR') & (df_servicos['Junção']==juntar)].reset_index()

                index_inicial = df_ref['index'].min()

                hoteis_mesma_juncao = contar_hoteis_df(df_ref)

                if index==index_inicial:

                    if hoteis_mesma_juncao<=max_hoteis:

                        roteiro+=1

                        carros = 1

                        paxs_total_roteiro = 0

                        bairro = ''

                        for index_2, value in df_ref['index'].items():

                            if value==index_inicial:

                                df_servicos.at[value, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_servicos, value)
                                
                                data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']
                                
                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                paxs_total_roteiro+=paxs_hotel

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            elif (df_servicos.at[value, 'Est Origem']==df_servicos.at[value-1, 'Est Origem']) | (df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[value-1, 'Hoteis Juntos p/ Carro Principal']):

                                df_servicos.at[value, 'Data Horario Apresentacao']=df_servicos.at[value-1, 'Data Horario Apresentacao']

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            else:

                                bairro=df_servicos.at[value, 'Região']

                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]\
                                        ['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                                    carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)

                                else:

                                    paxs_total_roteiro+=paxs_hotel

                                    if bairro!='':

                                        intervalo_ref = definir_intervalo_ref(df_servicos, value)
                                        
                                    if paxs_hotel>=st.session_state.pax_cinco_min:

                                        intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                    data_horario_hotel = df_servicos.at[value-1, 'Data Horario Apresentacao']-\
                                        intervalo_ref

                                    if  data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                                        carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)

                                    else:

                                        df_servicos.at[value, 'Data Horario Apresentacao']=data_horario_hotel

                                        df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                    else:

                        roteiro+=1

                        carros = 1

                        paxs_total_roteiro = 0

                        contador_hoteis = 0

                        bairro = ''

                        for index_2, value in df_ref['index'].items():

                            if value==index_inicial:

                                df_servicos.at[value, 'Data Horario Apresentacao'] = definir_horario_primeiro_hotel(df_servicos, value)
                                
                                data_horario_primeiro_hotel = df_servicos.at[value, 'Data Horario Apresentacao']
                                
                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                paxs_total_roteiro+=paxs_hotel

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                                contador_hoteis+=1

                            elif (df_servicos.at[value, 'Est Origem']==df_servicos.at[value-1, 'Est Origem']) | (df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[value-1, 'Hoteis Juntos p/ Carro Principal']):

                                df_servicos.at[value, 'Data Horario Apresentacao']=df_servicos.at[value-1, 'Data Horario Apresentacao']

                                df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

                            else:   

                                contador_hoteis+=1

                                bairro=df_servicos.at[value, 'Região']

                                if not pd.isna(df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_servicos.at[value, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_servicos.at[value, 'Est Origem']]['Total ADT | CHD'].sum()

                                if contador_hoteis>max_hoteis:

                                    carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                    
                                    contador_hoteis = 1
                                    
                                else:

                                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                                        carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                        
                                        contador_hoteis = 1

                                    else:

                                        paxs_total_roteiro+=paxs_hotel

                                        if bairro!='':

                                            intervalo_ref = definir_intervalo_ref(df_servicos, value)
                                            
                                        if paxs_hotel>=st.session_state.pax_cinco_min:

                                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                        data_horario_hotel = df_servicos.at[value-1, 'Data Horario Apresentacao']-\
                                            intervalo_ref

                                        if  data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                                            carros, roteiro, df_servicos, data_horario_primeiro_hotel, bairro, paxs_total_roteiro = abrir_novo_carro(carros, roteiro, df_servicos, value, index, paxs_hotel)
                                            
                                            contador_hoteis = 1

                                        else:

                                            df_servicos.at[value, 'Data Horario Apresentacao']=data_horario_hotel

                                            df_servicos = preencher_roteiro_carros(df_servicos, roteiro, carros, value)

    return df_servicos, roteiro

def gerar_roteiros_alternativos(df_servicos):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        n_hoteis_df_ref = contar_hoteis_df(df_ref)

        divisao_inteira = n_hoteis_df_ref // df_ref['Carros'].max()

        if n_hoteis_df_ref % df_ref['Carros'].max() == 0:

            max_hoteis = divisao_inteira

        else:

            max_hoteis = divisao_inteira + 1

        carros = 1

        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref)):

            if index==0:

                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                
                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                contador_hoteis+=1

            elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

            else:

                contador_hoteis+=1

                if contador_hoteis>max_hoteis:

                    carros+=1

                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref.at[index, 'Roteiro'] = item

                    df_ref.at[index, 'Carros'] = carros
                    
                    contador_hoteis = 1
                    
                else:

                    bairro=df_ref.at[index, 'Região']

                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                        carros+=1

                        df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)

                        data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                        paxs_total_roteiro = 0

                        bairro = ''

                        paxs_total_roteiro+=paxs_hotel

                        df_ref.at[index, 'Roteiro'] = item

                        df_ref.at[index, 'Carros'] = carros
                        
                        contador_hoteis = 1

                    else:

                        paxs_total_roteiro+=paxs_hotel

                        if bairro!='':

                            intervalo_ref = definir_intervalo_ref(df_ref, index)
                            
                        if paxs_hotel>=st.session_state.pax_cinco_min:

                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                        data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                        if data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):

                            carros+=1

                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)

                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                            paxs_total_roteiro = 0

                            bairro = ''

                            paxs_total_roteiro+=paxs_hotel

                            df_ref.at[index, 'Roteiro'] = item

                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1

                        else:

                            df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                            df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

        df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_2(df_servicos, max_hoteis_ref, intervalo_pu_hotel):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())
    
    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].sort_values(by='Sequência', ascending=False).reset_index(drop=True)

        carros = 1
    
        paxs_total_roteiro = 0

        contador_hoteis = 0

        bairro = ''

        for index in range(len(df_ref)):

            if index==0:

                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                
                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
                
                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                    
                else:

                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                paxs_total_roteiro+=paxs_hotel

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                contador_hoteis+=1

            elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']

                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

            else:

                contador_hoteis+=1

                if contador_hoteis>max_hoteis_ref:

                    carros+=1

                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                    paxs_total_roteiro = 0

                    bairro = ''

                    paxs_total_roteiro+=paxs_hotel

                    df_ref.at[index, 'Roteiro'] = item

                    df_ref.at[index, 'Carros'] = carros
                    
                    contador_hoteis = 1
                    
                else:

                    bairro=df_ref.at[index, 'Região']

                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

                    if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:

                        carros+=1

                        df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)

                        data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                        paxs_total_roteiro = 0

                        bairro = ''

                        paxs_total_roteiro+=paxs_hotel

                        df_ref.at[index, 'Roteiro'] = item

                        df_ref.at[index, 'Carros'] = carros
                        
                        contador_hoteis = 1

                    else:

                        paxs_total_roteiro+=paxs_hotel

                        if bairro!='':

                            intervalo_ref = definir_intervalo_ref(df_ref, index)
                            
                        if paxs_hotel>=st.session_state.pax_cinco_min:

                            intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                        data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref

                        if data_horario_primeiro_hotel - data_horario_hotel>intervalo_pu_hotel:

                            carros+=1

                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)

                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']

                            paxs_total_roteiro = 0

                            bairro = ''

                            paxs_total_roteiro+=paxs_hotel

                            df_ref.at[index, 'Roteiro'] = item

                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1

                        else:

                            df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel

                            df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

        df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_3(df_servicos):

    df_servicos_ref = df_servicos.sort_values(by=['Roteiro', 'Carros', 'Data Horario Apresentacao']).reset_index(drop=True)

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos_ref[df_servicos_ref['Roteiro']==item].reset_index(drop=True)

        df_regiao_carro = df_ref[['Região', 'Carros']].drop_duplicates().reset_index(drop=True)

        df_regiao_duplicada = df_regiao_carro.groupby('Região')['Carros'].count().reset_index()

        carros_repetidos = df_regiao_duplicada['Carros'].max()

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        if carros_repetidos>1:

            carros = 1
    
            paxs_total_roteiro = 0
    
            contador_hoteis = 0
    
            bairro = ''
    
            for index in range(len(df_ref)):
    
                if index==0:
    
                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                    
                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
                    
                    if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                        paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                        
                    else:

                        paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
    
                    paxs_total_roteiro+=paxs_hotel
    
                    df_ref = preencher_roteiro_carros(df_ref, item, carros, index)
    
                    contador_hoteis+=1

                elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):
    
                    df_ref.at[index, 'Data Horario Apresentacao']=df_ref.at[index-1, 'Data Horario Apresentacao']
    
                    df_ref = preencher_roteiro_carros(df_ref, item, carros, index)
    
                else:

                    bairro_anterior=df_ref.at[index-1, 'Região']

                    bairro=df_ref.at[index, 'Região']

                    if bairro_anterior!=bairro:

                        n_hoteis_novo_bairro = len(df_ref[df_ref['Região']==bairro]['Est Origem'].unique().tolist())

                        paxs_novo_bairro = df_ref[df_ref['Região'] == bairro]['Total ADT | CHD'].sum()

                        if n_hoteis_novo_bairro+contador_hoteis<=st.session_state.max_hoteis_roteirizacao and paxs_total_roteiro+paxs_novo_bairro<=st.session_state.pax_max:
    
                            contador_hoteis+=1
            
                            if contador_hoteis>st.session_state.max_hoteis_roteirizacao:
            
                                carros+=1
            
                                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                                
                                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
            
                                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
            
                                paxs_total_roteiro = 0
            
                                bairro = ''
            
                                paxs_total_roteiro+=paxs_hotel
            
                                df_ref.at[index, 'Roteiro'] = item
            
                                df_ref.at[index, 'Carros'] = carros
                                
                                contador_hoteis = 1
                                
                            else:

                                if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                    paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                    
                                else:
            
                                    paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
            
                                if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:
            
                                    carros+=1
            
                                    df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
            
                                    data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
            
                                    paxs_total_roteiro = 0
            
                                    bairro = ''
            
                                    paxs_total_roteiro+=paxs_hotel
            
                                    df_ref.at[index, 'Roteiro'] = item
            
                                    df_ref.at[index, 'Carros'] = carros
                                    
                                    contador_hoteis = 1
            
                                else:
            
                                    paxs_total_roteiro+=paxs_hotel
            
                                    if bairro!='':
            
                                        intervalo_ref = definir_intervalo_ref(df_ref, index)
                                        
                                    if paxs_hotel>=st.session_state.pax_cinco_min:

                                        intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)
            
                                    data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref
            
                                    if data_horario_primeiro_hotel - data_horario_hotel>transformar_timedelta(st.session_state.intervalo_pu_hotel):
            
                                        carros+=1
            
                                        df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
            
                                        data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
            
                                        paxs_total_roteiro = 0
            
                                        bairro = ''
            
                                        paxs_total_roteiro+=paxs_hotel
            
                                        df_ref.at[index, 'Roteiro'] = item
            
                                        df_ref.at[index, 'Carros'] = carros
                                        
                                        contador_hoteis = 1
            
                                    else:
            
                                        df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel
            
                                        df_ref = preencher_roteiro_carros(df_ref, item, carros, index)

                        else:

                            carros+=1
            
                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                            
                            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                
                            else:
        
                                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
        
                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
        
                            paxs_total_roteiro = 0
        
                            bairro = ''
        
                            paxs_total_roteiro+=paxs_hotel
        
                            df_ref.at[index, 'Roteiro'] = item
        
                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1

                    else:

                        contador_hoteis+=1
            
                        if contador_hoteis>st.session_state.max_hoteis_roteirizacao:
        
                            carros+=1
        
                            df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
                            
                            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                
                            else:
        
                                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
        
                            data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
        
                            paxs_total_roteiro = 0
        
                            bairro = ''
        
                            paxs_total_roteiro+=paxs_hotel
        
                            df_ref.at[index, 'Roteiro'] = item
        
                            df_ref.at[index, 'Carros'] = carros
                            
                            contador_hoteis = 1
                            
                        else:
        
                            bairro=df_ref.at[index, 'Região']
        
                            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                                
                            else:
        
                                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()
        
                            if paxs_total_roteiro+paxs_hotel>st.session_state.pax_max:
        
                                carros+=1
        
                                df_ref.at[index, 'Data Horario Apresentacao']=definir_horario_primeiro_hotel(df_ref, index)
        
                                data_horario_primeiro_hotel = df_ref.at[index, 'Data Horario Apresentacao']
        
                                paxs_total_roteiro = 0
        
                                bairro = ''
        
                                paxs_total_roteiro+=paxs_hotel
        
                                df_ref.at[index, 'Roteiro'] = item
        
                                df_ref.at[index, 'Carros'] = carros
                                
                                contador_hoteis = 1
        
                            else:
        
                                paxs_total_roteiro+=paxs_hotel
        
                                if bairro!='':
        
                                    intervalo_ref = definir_intervalo_ref(df_ref, index)
                                    
                                if paxs_hotel>=st.session_state.pax_cinco_min:

                                    intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

                                data_horario_hotel = df_ref.at[index-1, 'Data Horario Apresentacao']-intervalo_ref
        
                                df_ref.at[index, 'Data Horario Apresentacao']=data_horario_hotel
        
                                df_ref = preencher_roteiro_carros(df_ref, item, carros, index)
    
            df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_ref], ignore_index=True)

    return df_roteiros_alternativos

def plotar_roteiros_simples(df_servicos, row3, coluna):

    for item in df_servicos['Roteiro'].unique().tolist():

        df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        horario_inicial_voo = df_ref_1['Horario Voo'].min()

        horario_final_voo = df_ref_1['Horario Voo'].max()

        if horario_inicial_voo == horario_final_voo:

            titulo_voos = f'{horario_inicial_voo}'

        else:

            titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

        lista_nome_voos = df_ref_1['Voo'].unique().tolist()

        voos_unidos = ' + '.join(lista_nome_voos)

        for carro in df_ref_1['Carros'].unique().tolist():

            df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

            modo = df_ref_2.at[0, 'Modo do Servico']

            total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

            paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

            if modo=='REGULAR':
    
                titulo_roteiro = f'Roteiro {item}'

                titulo_carro = f'Veículo {carro}'

                titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

            else:

                reserva = df_ref_2.at[0, 'Reserva']

                titulo_roteiro = f'Roteiro {item}'

                titulo_carro = f'Veículo {carro}'

                titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

            df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()

            df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
        
            with row3[coluna]:

                container = st.container(border=True, height=500)

                container.header(titulo_roteiro)

                container.subheader(titulo_carro)

                container.markdown(titulo_modo_voo_pax)

                container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                if coluna==2:

                    coluna=0

                else:

                    coluna+=1

    return coluna

def plotar_roteiros_gerais_sem_apoio(df_servicos, df_alternativos, coluna, row3):

    for item in df_servicos['Roteiro'].unique().tolist():

        if not item in df_alternativos['Roteiro'].unique().tolist():

            df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)
    
            horario_inicial_voo = df_ref_1['Horario Voo'].min()
    
            horario_final_voo = df_ref_1['Horario Voo'].max()
    
            if horario_inicial_voo == horario_final_voo:
    
                titulo_voos = f'{horario_inicial_voo}'
    
            else:
    
                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)
    
            for carro in df_ref_1['Carros'].unique().tolist():
    
                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                if modo=='REGULAR':
    
                    titulo_roteiro = f'Roteiro {item}'
    
                    titulo_carro = f'Veículo {carro}'
    
                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                else:
    
                    reserva = df_ref_2.at[0, 'Reserva']
    
                    titulo_roteiro = f'Roteiro {item}'
    
                    titulo_carro = f'Veículo {carro}'
    
                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:
    
                    container = st.container(border=True, height=500)
    
                    container.header(titulo_roteiro)
    
                    container.subheader(titulo_carro)
    
                    container.markdown(titulo_modo_voo_pax)
    
                    container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    if coluna==2:
    
                        coluna=0
    
                    else:
    
                        coluna+=1

        else:

            if item in  df_alternativos['Roteiro'].unique().tolist():
    
                df_ref_1 = df_alternativos[df_alternativos['Roteiro']==item].reset_index(drop=True)
    
                horario_inicial_voo = df_ref_1['Horario Voo'].min()
    
                horario_final_voo = df_ref_1['Horario Voo'].max()
    
                if horario_inicial_voo == horario_final_voo:
    
                    titulo_voos = f'{horario_inicial_voo}'
    
                else:
    
                    titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

                lista_nome_voos = df_ref_1['Voo'].unique().tolist()

                voos_unidos = ' + '.join(lista_nome_voos)
    
                for carro in df_ref_1['Carros'].unique().tolist():
    
                    df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                    modo = df_ref_2.at[0, 'Modo do Servico']

                    total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                    paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                    if modo=='REGULAR':
    
                        titulo_roteiro = f'Opção Alternativa 1 | Roteiro {item}'
    
                        titulo_carro = f'Veículo {carro}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                    else:
    
                        reserva = df_ref_2.at[0, 'Reserva']
    
                        titulo_roteiro = f'Opção Alternativa 1 | Roteiro {item}'
    
                        titulo_carro = f'Veículo {carro}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'}).sort_values(by='Data Horario Apresentacao').reset_index()
                        
                    df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                
                    with row3[coluna]:
    
                        container = st.container(border=True, height=500)
    
                        container.header(titulo_roteiro)
    
                        container.subheader(titulo_carro)
    
                        container.markdown(titulo_modo_voo_pax)
    
                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        if coluna==2:
    
                            coluna=0
    
                        else:
    
                            coluna+=1

    return coluna

def definir_html(df_ref):

    if 'Data Horario Apresentacao' in df_ref.columns:
        
        df_ref = df_ref.sort_values(by='Data Horario Apresentacao').reset_index(drop=True)

        df_ref['Data Horario Apresentacao'] = df_ref['Data Horario Apresentacao'].dt.strftime('%d/%m/%Y %H:%M:%S')

    html=df_ref.to_html(index=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                text-align: center;  /* Centraliza o texto */
            }}
            table {{
                margin: 0 auto;  /* Centraliza a tabela */
                border-collapse: collapse;  /* Remove espaço entre as bordas da tabela */
            }}
            th, td {{
                padding: 8px;  /* Adiciona espaço ao redor do texto nas células */
                border: 1px solid black;  /* Adiciona bordas às células */
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    return html

def definir_html_2(df_ref):

    if 'Data Horario Apresentacao' in df_ref.columns:

        df_ref['Data Horario Apresentacao'] = df_ref['Data Horario Apresentacao'].dt.strftime('%d/%m/%Y %H:%M:%S')

    html=df_ref.to_html(index=False)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                text-align: center;  /* Centraliza o texto */
            }}
            table {{
                margin: 0 auto;  /* Centraliza a tabela */
                border-collapse: collapse;  /* Remove espaço entre as bordas da tabela */
            }}
            th, td {{
                padding: 8px;  /* Adiciona espaço ao redor do texto nas células */
                border: 1px solid black;  /* Adiciona bordas às células */
                text-align: center;
            }}
        </style>
    </head>
    <body>
        {html}
    </body>
    </html>
    """

    return html

def criar_output_html(nome_html, html):

    if len(st.session_state.df_juncao_voos)>0:

        with open(nome_html, "w", encoding="utf-8") as file:

            nome_regiao = nome_html.split()[2]

            nome_regiao = nome_regiao.replace('.html', '')

            file.write(f'<p style="font-size:50px;">{nome_regiao} | {st.session_state.data_roteiro_ref}</p>\n\n')

            file.write(f'<p style="font-size:40px;">Junção de Voos</p>\n\n')
            
            file.write(html)

        if len(st.session_state.df_horario_esp_ultimo_hotel)>0:

            html = definir_html_2(st.session_state.df_horario_esp_ultimo_hotel)
    
            with open(nome_html, "a", encoding="utf-8") as file:
    
                file.write(f'<p style="font-size:40px;">Antecipações Específicas</p>')
                
                file.write(html)

        with open(nome_html, "a", encoding="utf-8") as file:

            file.write(f'<p style="font-size:40px;">Roteiros</p>\n\n')

    elif len(st.session_state.df_horario_esp_ultimo_hotel)>0:

        html = definir_html_2(st.session_state.df_horario_esp_ultimo_hotel)
    
        with open(nome_html, "w", encoding="utf-8") as file:

            nome_regiao = nome_html.split()[2]

            nome_regiao = nome_regiao.replace('.html', '')

            file.write(f'<p style="font-size:50px;">{nome_regiao} | {st.session_state.data_roteiro_ref}</p>\n\n')
    
            file.write(f'<p style="font-size:40px;">Antecipações Específicas</p>')
            
            file.write(html)

            file.write(f'<p style="font-size:40px;">Roteiros</p>\n\n')

    else:

        with open(nome_html, "w", encoding="utf-8") as file:

            nome_regiao = nome_html.split()[2]

            nome_regiao = nome_regiao.replace('.html', '')

            file.write(f'<p style="font-size:50px;">{nome_regiao} | {st.session_state.data_roteiro_ref}</p>\n\n')

            file.write(f'<p style="font-size:40px;">Roteiros</p>\n\n')

def inserir_html_2(nome_html, df):

    html = definir_html_2(df)

    with open(nome_html, "a", encoding="utf-8") as file:

        file.write('<br><br><br>')

        file.write(f'<p style="font-size:40px;">Mapa de Serviços</p>\n\n')
        
        file.write(html)
        
def inserir_roteiros_html_sem_apoio(nome_html, df_pdf):

    roteiro = 0

    df_ref = df_pdf[['Roteiro', 'Carros', 'Horario Voo / Menor Horário']].drop_duplicates().reset_index(drop=True)

    for index in range(len(df_ref)):

        roteiro_ref = df_ref.at[index, 'Roteiro']

        carro_ref = df_ref.at[index, 'Carros']

        hv_ref = df_ref.at[index, 'Horario Voo / Menor Horário']

        df_ref_roteiro = df_pdf[(df_pdf['Roteiro']==roteiro_ref) & (df_pdf['Carros']==carro_ref) & 
                          (df_pdf['Horario Voo / Menor Horário']==hv_ref)].reset_index(drop=True)
        
        lista_nome_voos = df_ref_roteiro['Voo'].unique().tolist()

        voos_unidos = ' + '.join(lista_nome_voos)

        if carro_ref==1:

            roteiro+=1

        for carro in df_ref_roteiro['Carros'].unique().tolist():

            df_ref_carro = df_ref_roteiro[df_ref_roteiro['Carros']==carro]\
                [['Roteiro', 'Carros', 'Modo do Servico', 'Voo', 'Horario Voo', 'Junção', 'Est Origem', 'Total ADT | CHD', 
                'Data Horario Apresentacao']].reset_index(drop=True)
            
            total_paxs = df_ref_carro['Total ADT | CHD'].sum()
            
            html = definir_html(df_ref_carro)

            with open(nome_html, "a", encoding="utf-8") as file:

                file.write(f'<p style="font-size:30px;">Roteiro {roteiro} | Carro {carro} | {voos_unidos} | {int(total_paxs)} Paxs</p>\n\n')

                file.write(html)

                file.write('\n\n')

def verificar_rotas_alternativas_ou_plotar_roteiros_sem_apoio(df_roteiros_alternativos, row_warning, row3, coluna, df_hoteis_pax_max, df_router_filtrado_2, df_juncao_voos, nome_html):

    if len(st.session_state.df_roteiros_alternativos)>0 or len(st.session_state.df_roteiros_alternativos_2)>0 or len(st.session_state.df_roteiros_alternativos_3)>0 or \
        len(st.session_state.df_roteiros_alternativos_4)>0:

        with row_warning[0]:

            st.warning('Existem opções alternativas para algumas rotas. Por favor, informe quais rotas alternativas serão usadas.')

    else:

        lista_dfs = [df_hoteis_pax_max, df_router_filtrado_2]

        n_carros = 0

        for df in lista_dfs:
            
            if len(df)>0:

                n_carros += len(df[['Roteiro', 'Carros']].drop_duplicates())

        with row_warning[0]:

            st.header(f'A roteirização usou um total de {n_carros} carros')

        if len(df_hoteis_pax_max)>0:

            coluna = plotar_roteiros_simples(df_hoteis_pax_max, row3, coluna)

        coluna = plotar_roteiros_gerais_sem_apoio(df_router_filtrado_2, df_roteiros_alternativos, coluna, row3)

        html = definir_html(df_juncao_voos)

        criar_output_html(nome_html, html)

        df_pdf = pd.concat([df_router_filtrado_2, df_hoteis_pax_max], ignore_index=True)
        
        df_pdf_2 = df_pdf[['Reserva', 'Data Horario Apresentacao']].sort_values(by='Reserva').reset_index(drop=True)

        st.session_state.df_insercao = df_pdf[['Id_Reserva', 'Id_Servico', 'Data Horario Apresentacao', 'Data Horario Apresentacao Original']].reset_index(drop=True)
        
        for index in range(len(df_pdf)):

            tipo_de_servico_ref = df_pdf.at[index, 'Modo do Servico']

            juncao_ref_2 = df_pdf.at[index, 'Junção']

            if tipo_de_servico_ref == 'REGULAR' and not pd.isna(juncao_ref_2):

                df_pdf.at[index, 'Horario Voo / Menor Horário'] = df_pdf.at[index, 'Menor Horário']

            elif (tipo_de_servico_ref == 'REGULAR' and pd.isna(juncao_ref_2)) or (tipo_de_servico_ref != 'REGULAR'):

                df_pdf.at[index, 'Horario Voo / Menor Horário'] = df_pdf.at[index, 'Horario Voo']

        df_pdf = df_pdf.sort_values(by=['Horario Voo / Menor Horário', 'Junção']).reset_index(drop=True)

        inserir_roteiros_html_sem_apoio(nome_html, df_pdf)

        inserir_html_2(nome_html, df_pdf_2)

        with open(nome_html, "r", encoding="utf-8") as file:

            html_content = file.read()

        salvar_rotas_historico(df_pdf)

        st.download_button(
            label="Baixar Arquivo HTML",
            data=html_content,
            file_name=nome_html,
            mime="text/html"
        )

def plotar_roteiros_gerais_alternativos_sem_apoio(df_servicos, df_alternativos, df_alternativos_2, df_alternativos_3, df_alternativos_4, coluna):

    df_rotas_alternativas = pd.concat([df_alternativos['Roteiro'], df_alternativos_2['Roteiro'], df_alternativos_3['Roteiro'], df_alternativos_4['Roteiro']], ignore_index=True).reset_index()

    lista_todas_rotas_alternativas = sorted(df_rotas_alternativas['Roteiro'].unique().tolist())

    for item in lista_todas_rotas_alternativas:

        row3=st.columns(3)

        coluna=0

        df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        horario_inicial_voo = df_ref_1['Horario Voo'].min()

        horario_final_voo = df_ref_1['Horario Voo'].max()

        if horario_inicial_voo == horario_final_voo:

            titulo_voos = f'{horario_inicial_voo}'

        else:

            titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

        lista_nome_voos = df_ref_1['Voo'].unique().tolist()

        voos_unidos = ' + '.join(lista_nome_voos)

        for carro in df_ref_1['Carros'].unique().tolist():

            df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

            modo = df_ref_2.at[0, 'Modo do Servico']

            total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

            paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

            if modo=='REGULAR':

                titulo_roteiro = f'Roteiro {item}'

                titulo_carro = f'Veículo {carro}'

                titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

            else:

                reserva = df_ref_2.at[0, 'Reserva']

                titulo_roteiro = f'Roteiro {item}'

                titulo_carro = f'Veículo {carro}'

                titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

            df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                    .sort_values(by='Data Horario Apresentacao').reset_index()
                
            df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
        
            with row3[coluna]:

                container = st.container(border=True, height=500)

                container.header(titulo_roteiro)

                container.subheader(titulo_carro)

                container.markdown(titulo_modo_voo_pax)

                container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                if coluna==2:

                    coluna=0

                else:

                    coluna+=1

        if item in  df_alternativos['Roteiro'].unique().tolist():

            row3=st.columns(3)

            coluna=0

            df_ref_1 = df_alternativos[df_alternativos['Roteiro']==item].reset_index(drop=True)

            horario_inicial_voo = df_ref_1['Horario Voo'].min()

            horario_final_voo = df_ref_1['Horario Voo'].max()

            if horario_inicial_voo == horario_final_voo:

                titulo_voos = f'{horario_inicial_voo}'

            else:

                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':

                    titulo_roteiro = f'Opção Alternativa 1 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 1 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.header(titulo_roteiro)

                    container.subheader(titulo_carro)

                    container.markdown(titulo_modo_voo_pax)

                    container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

        if item in df_alternativos_2['Roteiro'].unique().tolist():

            row3=st.columns(3)

            coluna=0

            df_ref_1 = df_alternativos_2[df_alternativos_2['Roteiro']==item].reset_index(drop=True)

            horario_inicial_voo = df_ref_1['Horario Voo'].min()

            horario_final_voo = df_ref_1['Horario Voo'].max()

            if horario_inicial_voo == horario_final_voo:

                titulo_voos = f'{horario_inicial_voo}'

            else:

                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':

                    titulo_roteiro = f'Opção Alternativa 2 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 2 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()

                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.header(titulo_roteiro)

                    container.subheader(titulo_carro)

                    container.markdown(titulo_modo_voo_pax)

                    container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

        if item in  df_alternativos_3['Roteiro'].unique().tolist():

            row3=st.columns(3)

            coluna=0

            df_ref_1 = df_alternativos_3[df_alternativos_3['Roteiro']==item].reset_index(drop=True)

            horario_inicial_voo = df_ref_1['Horario Voo'].min()

            horario_final_voo = df_ref_1['Horario Voo'].max()

            if horario_inicial_voo == horario_final_voo:

                titulo_voos = f'{horario_inicial_voo}'

            else:

                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':

                    titulo_roteiro = f'Opção Alternativa 3 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 3 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()

                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.header(titulo_roteiro)

                    container.subheader(titulo_carro)

                    container.markdown(titulo_modo_voo_pax)

                    container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

        if item in  df_alternativos_4['Roteiro'].unique().tolist():

            row3=st.columns(3)

            coluna=0

            df_ref_1 = df_alternativos_4[df_alternativos_4['Roteiro']==item].reset_index(drop=True)

            horario_inicial_voo = df_ref_1['Horario Voo'].min()

            horario_final_voo = df_ref_1['Horario Voo'].max()

            if horario_inicial_voo == horario_final_voo:

                titulo_voos = f'{horario_inicial_voo}'

            else:

                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)

            for carro in df_ref_1['Carros'].unique().tolist():

                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)

                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))

                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())

                if modo=='REGULAR':

                    titulo_roteiro = f'Opção Alternativa 3 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                else:

                    reserva = df_ref_2.at[0, 'Reserva']

                    titulo_roteiro = f'Opção Alternativa 3 | Roteiro {item}'

                    titulo_carro = f'Veículo {carro}'

                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'

                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()

                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:

                    container = st.container(border=True, height=500)

                    container.header(titulo_roteiro)

                    container.subheader(titulo_carro)

                    container.markdown(titulo_modo_voo_pax)

                    container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)

                    if coluna==2:

                        coluna=0

                    else:

                        coluna+=1

    return coluna

def plotar_roteiros_gerais_final_sem_apoio(df_servicos, df_alternativos, coluna):

    lista_roteiros = df_servicos['Roteiro'].unique().tolist()

    lista_roteiros.extend(df_alternativos['Roteiro'].unique().tolist())

    lista_roteiros = sorted(lista_roteiros)

    for item in lista_roteiros:

        if not item in df_alternativos['Roteiro'].unique().tolist():

            df_ref_1 = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)
    
            horario_inicial_voo = df_ref_1['Horario Voo'].min()
    
            horario_final_voo = df_ref_1['Horario Voo'].max()
    
            if horario_inicial_voo == horario_final_voo:
    
                titulo_voos = f'{horario_inicial_voo}'
    
            else:
    
                titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

            lista_nome_voos = df_ref_1['Voo'].unique().tolist()

            voos_unidos = ' + '.join(lista_nome_voos)
    
            for carro in df_ref_1['Carros'].unique().tolist():
    
                df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                modo = df_ref_2.at[0, 'Modo do Servico']

                total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                if modo=='REGULAR':
    
                    titulo_roteiro = f'Roteiro {item}'
    
                    titulo_carro = f'Veículo {carro}'
    
                    titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                else:
    
                    reserva = df_ref_2.at[0, 'Reserva']
    
                    titulo_roteiro = f'Roteiro {item}'
    
                    titulo_carro = f'Veículo {carro}'
    
                    titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                        .sort_values(by='Data Horario Apresentacao').reset_index()
                    
                df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
            
                with row3[coluna]:
    
                    container = st.container(border=True, height=500)
    
                    container.header(titulo_roteiro)
    
                    container.subheader(titulo_carro)
    
                    container.markdown(titulo_modo_voo_pax)
    
                    container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                    if coluna==2:
    
                        coluna=0
    
                    else:
    
                        coluna+=1

        else:

            if item in  df_alternativos['Roteiro'].unique().tolist():
    
                df_ref_1 = df_alternativos[df_alternativos['Roteiro']==item].reset_index(drop=True)
    
                horario_inicial_voo = df_ref_1['Horario Voo'].min()
    
                horario_final_voo = df_ref_1['Horario Voo'].max()
    
                if horario_inicial_voo == horario_final_voo:
    
                    titulo_voos = f'{horario_inicial_voo}'
    
                else:
    
                    titulo_voos = f'{horario_inicial_voo} às {horario_final_voo}'

                lista_nome_voos = df_ref_1['Voo'].unique().tolist()

                voos_unidos = ' + '.join(lista_nome_voos)
    
                for carro in df_ref_1['Carros'].unique().tolist():
    
                    df_ref_2 = df_ref_1[df_ref_1['Carros']==carro].reset_index(drop=True)
    
                    modo = df_ref_2.at[0, 'Modo do Servico']

                    total_hoteis = int(len(df_ref_2['Est Origem'].unique().tolist()))
    
                    paxs_total = int(df_ref_2['Total ADT | CHD'].sum())
    
                    if modo=='REGULAR':
    
                        titulo_roteiro = f'Opção Alternativa | Roteiro {item}'
    
                        titulo_carro = f'Veículo {carro}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                    else:
    
                        reserva = df_ref_2.at[0, 'Reserva']
    
                        titulo_roteiro = f'Opção Alternativa | Roteiro {item}'
    
                        titulo_carro = f'Veículo {carro}'
    
                        titulo_modo_voo_pax = f'*{modo.title()} | {reserva} | {voos_unidos} | {titulo_voos} | {total_hoteis} hoteis | {paxs_total} paxs*'
    
                    df_ref_3 = df_ref_2.groupby('Est Origem').agg({'Total ADT | CHD': 'sum', 'Data Horario Apresentacao': 'first'})\
                            .sort_values(by='Data Horario Apresentacao').reset_index()
                        
                    df_ref_3 = df_ref_3.rename(columns={'Est Origem': 'Hotel', 'Total ADT | CHD': 'Paxs', 'Data Horario Apresentacao': 'Horário'})
                
                    with row3[coluna]:
    
                        container = st.container(border=True, height=500)
    
                        container.header(titulo_roteiro)
    
                        container.subheader(titulo_carro)
    
                        container.markdown(titulo_modo_voo_pax)
    
                        container.dataframe(df_ref_3[['Hotel', 'Paxs', 'Horário']], hide_index=True)
    
                        if coluna==2:
    
                            coluna=0
    
                        else:
    
                            coluna+=1

    return coluna

def gerar_horarios_apresentacao_2(df_servicos):

    for index in range(len(df_servicos)):

        if index==0:

            df_servicos.at[index, 'Data Horario Apresentacao']=\
                definir_horario_primeiro_hotel(df_servicos, index)
            
            if not pd.isna(df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                paxs_hotel = df_servicos[df_servicos['Hoteis Juntos p/ Carro Principal']==df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                    ['Total ADT | CHD'].sum()
                
            else:

                paxs_hotel = df_servicos[df_servicos['Est Origem']==df_servicos.at[index, 'Est Origem']]['Total ADT | CHD'].sum()


        elif (df_servicos.at[index, 'Est Origem']==df_servicos.at[index-1, 'Est Origem']) | \
            (df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']==df_servicos.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

            df_servicos.at[index, 'Data Horario Apresentacao']=\
                df_servicos.at[index-1, 'Data Horario Apresentacao']

        else:

            bairro=df_servicos.at[index, 'Região']

            if not pd.isna(df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                paxs_hotel = df_servicos[df_servicos['Hoteis Juntos p/ Carro Principal']==df_servicos.at[index, 'Hoteis Juntos p/ Carro Principal']]\
                    ['Total ADT | CHD'].sum()
                
            else:

                paxs_hotel = df_servicos[df_servicos['Est Origem']==df_servicos.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

            if bairro!='':

                intervalo_ref = definir_intervalo_ref(df_servicos, index)
                
            if paxs_hotel>=st.session_state.pax_cinco_min:

                intervalo_ref+=timedelta(hours=0, minutes=5, seconds=0)

            data_horario_hotel = df_servicos.at[index-1, 'Data Horario Apresentacao']-\
                intervalo_ref

            df_servicos.at[index, 'Data Horario Apresentacao']=data_horario_hotel

    return df_servicos

def atualizar_banco_dados(df_exportacao, base_luck):

    st.session_state.df_insercao = st.session_state.df_insercao.drop(st.session_state.df_insercao.index)

    config = {
    'user': 'user_automation',
    'password': 'auto_luck_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': base_luck
    }
    # Conexão ao banco de dados
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()
    
    # Coluna para armazenar o status da atualização
    df_exportacao['Status Serviço'] = ''
    df_exportacao['Status Auditoria'] = ''
    
    # Placeholder para exibir o DataFrame e atualizar em tempo real
    placeholder = st.empty()
    for idx, row in df_exportacao.iterrows():
        id_reserva = row['Id_Reserva']
        id_servico = row['Id_Servico']
        currentPresentationHour = str(row['Data Horario Apresentacao Original'])
        newPresentationHour = str(row['Data Horario Apresentacao'])
        
        data = '{"presentation_hour":["' + currentPresentationHour + '","' + newPresentationHour + ' Roteirizador"]}'
        
        #Horário atual em string

        hora_execucao = datetime.now()
    
        hora_execucao_menos_3h = hora_execucao - timedelta(hours=3)

        current_timestamp = int(hora_execucao_menos_3h.timestamp())
        
        try:
            # Atualizar o banco de dados se o ID já existir
            query = "UPDATE reserve_service SET presentation_hour = %s WHERE id = %s"
            cursor.execute(query, (newPresentationHour, id_servico))
            conexao.commit()
            df_exportacao.at[idx, 'Status Serviço'] = 'Atualizado com sucesso'
            
        except Exception as e:
            df_exportacao.at[idx, 'Status Serviço'] = f'Erro: {e}'
        
        try:
            # Adicionar registro de edição na tabela de auditoria
            query = "INSERT INTO changelogs (relatedObjectType, relatedObjectId, parentId, data, createdAt, type, userId, module, hostname) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, null)"
            cursor.execute(query, ('ReserveService', id_servico, id_reserva, data, current_timestamp, 'update', st.query_params["userId"], 'router'))
            conexao.commit()
            df_exportacao.at[idx, 'Status Auditoria'] = 'Atualizado com sucesso'
        except Exception as e:
            df_exportacao.at[idx, 'Status Auditoria'] = f'Erro: {e}'
            
        # Define o estilo para coloração condicional
        styled_df = df_exportacao.style.applymap(
            lambda val: 'background-color: green; color: white' if val == 'Atualizado com sucesso' 
            else ('background-color: red; color: white' if val != '' else ''),
            subset=['Status Serviço', 'Status Auditoria']
        )
        
        # Atualiza o DataFrame na interface em tempo real
        placeholder.dataframe(styled_df, hide_index=True, use_container_width=True)
        # time.sleep(0.5)
    
    cursor.close()
    conexao.close()
    return df_exportacao

def getUser(userId):

    config = {
    'user': 'user_automation',
    'password': 'auto_luck_2024',
    'host': 'comeia.cixat7j68g0n.us-east-1.rds.amazonaws.com',
    'database': 'test_phoenix_general'
    }
    
    # Conexão às Views usando o config modificado
    conexao = mysql.connector.connect(**config)
    cursor = conexao.cursor()

    request_name = f'SELECT * FROM user WHERE ID = {userId}'

    # Script MySQL para requests
    cursor.execute(request_name)
    # Coloca o request em uma variavel
    resultado = cursor.fetchall()
    # Busca apenas os cabeçalhos do Banco
    cabecalho = [desc[0] for desc in cursor.description]

    # Fecha a conexão
    cursor.close()
    conexao.close()

    # Coloca em um dataframe e converte decimal para float
    df = pd.DataFrame(resultado, columns=cabecalho)
    df = df.applymap(lambda x: float(x) if isinstance(x, decimal.Decimal) else x)
    return df

def identificar_apoios_em_df(df_servicos, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis):

    df_servicos['Apoios'] = ''

    for n_roteiro in df_servicos['Roteiro'].unique().tolist():

        df_ref = df_servicos[df_servicos['Roteiro']==n_roteiro].reset_index()

        for veiculo in df_ref['Carros'].unique().tolist():

            df_ref_2 = df_ref[df_ref['Carros']==veiculo].reset_index(drop=True)

            pax_carro = df_ref[df_ref['Carros']==veiculo]['Total ADT | CHD'].sum()

            limitacao_van = df_ref_2['Van'].isnull().any()

            limitacao_micro = df_ref_2['Micro'].isnull().any()

            limitacao_bus = df_ref_2['Bus'].isnull().any()

            if pax_carro>pax_max_utilitario and pax_carro<=pax_max_van and limitacao_van:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Van'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_van and pax_carro<=pax_max_micro and limitacao_micro:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Micro'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            elif pax_carro>pax_max_micro and limitacao_bus:

                df_ref_3 = df_ref_2[pd.isna(df_ref_2['Bus'])].reset_index(drop=True)

                for index in df_ref_3['index'].tolist():

                    df_servicos.at[index, 'Apoios']='X'

            if len(df_ref_2)>1:

                for index in range(len(df_ref_2)):

                    indice = df_ref_2.at[index, 'index']

                    regiao_ref = df_ref_2.at[index, 'Região']

                    if regiao_ref == 'CAMURUPIM':

                        df_servicos.at[indice, 'Apoios']='Y'

    df_roteiros_com_apoios = df_servicos[df_servicos['Apoios']!=''].reset_index()

    df_roteiros_com_apoios = df_roteiros_com_apoios[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

    for index in range(len(df_roteiros_com_apoios)):

        n_roteiro_ref = df_roteiros_com_apoios.at[index, 'Roteiro']

        n_carro_ref = df_roteiros_com_apoios.at[index, 'Carros']

        df_ref = df_servicos[(df_servicos['Roteiro']==n_roteiro_ref) & (df_servicos['Carros']==n_carro_ref)].sort_values(by=['Apoios', 'Sequência'], ascending=[False, False]).reset_index()

        df_ref_apoios = df_ref[df_ref['Apoios']=='X'].reset_index(drop=True)

        limitacao_van = df_ref_apoios['Van'].isnull().any()

        limitacao_micro = df_ref_apoios['Micro'].isnull().any()

        limitacao_bus = df_ref_apoios['Bus'].isnull().any()

        if limitacao_van:

            pax_max_ref = pax_max_utilitario

        elif limitacao_micro:

            pax_max_ref = pax_max_van

        elif limitacao_bus:

            pax_max_ref = pax_max_micro

        paxs_total_apoio = df_ref_apoios['Total ADT | CHD'].sum()

        df_ref_contagem_hoteis_apoios = df_ref[df_ref['Apoios']!=''].groupby('Est Origem')['Hoteis Juntos p/ Apoios'].first().reset_index()

        hoteis_total_apoio=0

        for index in range(len(df_ref_contagem_hoteis_apoios)):

            if index==0:

                hoteis_total_apoio+=1

            elif not ((df_ref_contagem_hoteis_apoios.at[index, 'Hoteis Juntos p/ Apoios']==df_ref_contagem_hoteis_apoios.at[index-1, 'Hoteis Juntos p/ Apoios']) and \
                      (~pd.isna(df_ref_contagem_hoteis_apoios.at[index, 'Hoteis Juntos p/ Apoios']))):

                hoteis_total_apoio+=1

        for index in range(len(df_ref)):

            hotel = df_ref.at[index, 'Est Origem']

            if not pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']):
                                    
                paxs_hotel = df_ref[df_ref['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']]['Total ADT | CHD'].sum()
                
            else:

                paxs_hotel = df_ref[df_ref['Est Origem']==df_ref.at[index, 'Est Origem']]['Total ADT | CHD'].sum()

            if index==0:

                if df_ref.at[index, 'Apoios']=='':

                    hoteis_total_apoio+=1

                    if paxs_total_apoio+paxs_hotel<=pax_max_ref:

                        paxs_total_apoio+=paxs_hotel

                        df_servicos.loc[(df_servicos['Est Origem']==hotel) & (df_servicos['Roteiro']==n_roteiro_ref) & (df_servicos['Carros']==n_carro_ref), 'Apoios']='X'

                    else:

                        break

            elif (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']) | (df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']):

                if (df_ref.at[index, 'Est Origem']==df_ref.at[index-1, 'Est Origem']):

                    df_servicos.loc[(df_servicos['Est Origem']==hotel) & (df_servicos['Roteiro']==n_roteiro_ref) & (df_servicos['Carros']==n_carro_ref), 'Apoios']='X'

                else:

                    df_servicos.loc[(df_servicos['Hoteis Juntos p/ Carro Principal']==df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']) & (df_servicos['Roteiro']==n_roteiro_ref) & \
                                    (df_servicos['Carros']==n_carro_ref), 'Apoios']='X'

            else:

                if df_ref.at[index, 'Apoios']=='':

                    if not ((df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']) and (~pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']))):

                        verificador_n_hoteis = hoteis_total_apoio+1

                    else:

                        verificador_n_hoteis = hoteis_total_apoio

                    if verificador_n_hoteis<=max_hoteis and paxs_total_apoio+paxs_hotel<=pax_max_ref:

                        if not ((df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']==df_ref.at[index-1, 'Hoteis Juntos p/ Carro Principal']) and (~pd.isna(df_ref.at[index, 'Hoteis Juntos p/ Carro Principal']))):

                            hoteis_total_apoio+=1

                        paxs_total_apoio+=paxs_hotel

                        df_servicos.loc[(df_servicos['Est Origem']==hotel) & (df_servicos['Roteiro']==n_roteiro_ref) & (df_servicos['Carros']==n_carro_ref), 'Apoios']='X'

                    else:

                        break

    return df_servicos

def gerar_roteiros_apoio(df_servicos):

    df_roteiros_apoios = df_servicos[(df_servicos['Apoios']=='X')].reset_index()

    df_servicos['Carros Apoios']=0

    df_roteiros_carros = df_roteiros_apoios[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

    for index, value in df_roteiros_carros['Roteiro'].items():

        df_ref = df_servicos[(df_servicos['Roteiro']==value)].sort_values(by=['Apoios', 'Sequência'], ascending=[False, False]).reset_index()

        df_ref_apoios = df_ref[(df_ref['Apoios']=='X')].reset_index(drop=True)

        df_ref_principal = df_ref[(df_ref['Apoios']!='X')].reset_index(drop=True)

        df_ref_principal = gerar_horarios_apresentacao_2(df_ref_principal)

        df_ref_apoios = gerar_horarios_apresentacao_2(df_ref_apoios)

        for index in range(len(df_ref_apoios)):

            index_2 = df_ref_apoios.at[index, 'index']

            df_servicos.at[index_2, 'Data Horario Apresentacao'] = df_ref_apoios.at[index, 'Data Horario Apresentacao']

            df_servicos.at[index_2, 'Carros Apoios'] = 1

    df_servicos = df_servicos.sort_values(by = ['Roteiro', 'Carros', 'Apoios', 'Carros Apoios']).reset_index(drop=True)

    df_roteiros_apoios = df_servicos[(df_servicos['Apoios']=='X')].reset_index()

    df_roteiros_carros = df_roteiros_apoios[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

    for index, value in df_roteiros_carros['Roteiro'].items():

        carro_n = 0

        df_ref = df_servicos[(df_servicos['Roteiro']==value)].reset_index()

        for index_2 in range(len(df_ref)):

            carro_principal = df_ref.at[index_2, 'Carros']

            carro_apoio = df_ref.at[index_2, 'Carros Apoios']

            index_principal = df_ref.at[index_2, 'index']

            if index_2==0:

                carro_n+=1

                df_servicos.at[index_principal, 'Carros']=carro_n

            elif carro_apoio!=0 and carro_apoio!=df_ref.at[index_2-1, 'Carros Apoios']:

                carro_n+=1

                df_servicos.at[index_principal, 'Carros']=carro_n

            elif carro_apoio!=0 and carro_apoio==df_ref.at[index_2-1, 'Carros Apoios']:

                df_servicos.at[index_principal, 'Carros']=carro_n

            elif carro_apoio==0 and carro_principal!=df_ref.at[index_2-1, 'Carros']:

                carro_n+=1

                df_servicos.at[index_principal, 'Carros']=carro_n

            elif carro_apoio==0 and carro_principal==df_ref.at[index_2-1, 'Carros']:

                df_servicos.at[index_principal, 'Carros']=carro_n

    return df_servicos

def roteirizar_hoteis_mais_pax_max_inacessibilidade(df_servicos, roteiro, df_hoteis_pax_max, pax_max, coluna_limitacao):

    # Roteirizando reservas com mais paxs que a capacidade máxima da frota

    df_ref_reservas_pax_max = df_servicos[pd.isna(df_servicos[coluna_limitacao])].groupby(['Modo do Servico', 'Reserva', 'Servico', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_reservas_pax_max = df_ref_reservas_pax_max[df_ref_reservas_pax_max['Total ADT | CHD']>=pax_max].reset_index()

    if len(df_ref_reservas_pax_max)>0:

        carro=0

        for index in range(len(df_ref_reservas_pax_max)):

            roteiro+=1

            pax_ref = df_ref_reservas_pax_max.at[index, 'Total ADT | CHD']

            modo = df_ref_reservas_pax_max.at[index, 'Modo do Servico']

            servico = df_ref_reservas_pax_max.at[index, 'Servico']

            reserva_ref = df_ref_reservas_pax_max.at[index, 'Reserva']

            hotel = df_ref_reservas_pax_max.at[index, 'Est Origem']

            if coluna_limitacao=='Van':

                st.warning(f'O hotel {hotel} da reserva {reserva_ref} tem {pax_ref} paxs e tem limitação de acessibilidade, portanto vai ser roteirizado em carros do tipo utilitário')

            elif coluna_limitacao=='Micro':

                st.warning(f'O hotel {hotel} da reserva {reserva_ref} tem {pax_ref} paxs e tem limitação de acessibilidade, portanto vai ser roteirizado em carros do tipo van')

            elif coluna_limitacao=='Bus':

                st.warning(f'O hotel {hotel} da reserva {reserva_ref} tem {pax_ref} paxs e tem limitação de acessibilidade, portanto vai ser roteirizado em carros do tipo micro')

            carro+=1

            df_hotel_pax_max = df_servicos[(df_servicos['Reserva']==reserva_ref)].reset_index()

            df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index, 'index'])

            df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index]]], ignore_index=True)

            df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

            df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    df_ref_sem_juncao = df_servicos[(pd.isna(df_servicos[coluna_limitacao])) & (pd.isna(df_servicos['Junção']))]\
        .groupby(['Modo do Servico', 'Servico', 'Voo', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_sem_juncao = df_ref_sem_juncao[df_ref_sem_juncao['Total ADT | CHD']>=pax_max].reset_index()

    df_ref_com_juncao = df_servicos[(pd.isna(df_servicos[coluna_limitacao])) & ~(pd.isna(df_servicos['Junção']))]\
        .groupby(['Modo do Servico', 'Servico', 'Junção', 'Est Origem']).agg({'Total ADT | CHD': 'sum'}).reset_index()

    df_ref_com_juncao = df_ref_com_juncao[df_ref_com_juncao['Total ADT | CHD']>=pax_max].reset_index()

    if len(df_ref_com_juncao)>0:

        for index in range(len(df_ref_com_juncao)):

            carro=0

            roteiro+=1

            pax_ref = df_ref_com_juncao.at[index, 'Total ADT | CHD']

            loops = int(pax_ref//pax_max)

            modo = df_ref_com_juncao.at[index, 'Modo do Servico']

            servico = df_ref_com_juncao.at[index, 'Servico']

            ref_juncao = df_ref_com_juncao.at[index, 'Junção']

            hotel = df_ref_com_juncao.at[index, 'Est Origem']

            if coluna_limitacao=='Van':

                st.warning(f'O hotel {hotel} da junção {ref_juncao} tem {pax_ref} paxs e tem limitação de acessibilidade, portanto vai ser roteirizado em carros do tipo utilitário')

            elif coluna_limitacao=='Micro':

                st.warning(f'O hotel {hotel} da junção {ref_juncao} tem {pax_ref} paxs e tem limitação de acessibilidade, portanto vai ser roteirizado em carros do tipo van')

            elif coluna_limitacao=='Bus':

                st.warning(f'O hotel {hotel} da junção {ref_juncao} tem {pax_ref} paxs e tem limitação de acessibilidade, portanto vai ser roteirizado em carros do tipo micro')

            for loop in range(loops):

                carro+=1

                df_hotel_pax_max = df_servicos[(df_servicos['Modo do Servico']==modo) & (df_servicos['Servico']==servico) & (df_servicos['Junção']==ref_juncao) & 
                                               (df_servicos['Est Origem']==hotel)].reset_index()
                
                paxs_total_ref = 0
                
                for index_2, value in df_hotel_pax_max['Total ADT | CHD'].items():

                    if paxs_total_ref+value>pax_max:

                        break

                    else:

                        paxs_total_ref+=value

                        df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index_2, 'index'])

                        df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index_2]]], ignore_index=True)

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    if len(df_ref_sem_juncao)>0:

        for index in range(len(df_ref_sem_juncao)):

            carro=0

            roteiro+=1

            pax_ref = df_ref_sem_juncao.at[index, 'Total ADT | CHD']

            loops = int(pax_ref//pax_max)

            modo = df_ref_sem_juncao.at[index, 'Modo do Servico']

            servico = df_ref_sem_juncao.at[index, 'Servico']

            ref_voo = df_ref_sem_juncao.at[index, 'Voo']

            hotel = df_ref_sem_juncao.at[index, 'Est Origem']

            if coluna_limitacao=='Van':

                st.warning(f'O hotel {hotel} do voo {ref_voo} tem {pax_ref} paxs e tem limitação de acessibilidade, portanto vai ser roteirizado em carros do tipo utilitário')

            elif coluna_limitacao=='Micro':

                st.warning(f'O hotel {hotel} do voo {ref_voo} tem {pax_ref} paxs e tem limitação de acessibilidade, portanto vai ser roteirizado em carros do tipo van')

            elif coluna_limitacao=='Bus':

                st.warning(f'O hotel {hotel} do voo {ref_voo} tem {pax_ref} paxs e tem limitação de acessibilidade, portanto vai ser roteirizado em carros do tipo micro')

            for loop in range(loops):

                carro+=1

                df_hotel_pax_max = df_servicos[(df_servicos['Modo do Servico']==modo) & (df_servicos['Servico']==servico) & (df_servicos['Voo']==ref_voo) & (df_servicos['Est Origem']==hotel)].reset_index()
                
                paxs_total_ref = 0
                
                for index_2, value in df_hotel_pax_max['Total ADT | CHD'].items():

                    if paxs_total_ref+value>pax_max:

                        break

                    else:

                        paxs_total_ref+=value

                        df_servicos = df_servicos.drop(index=df_hotel_pax_max.at[index_2, 'index'])

                        df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hotel_pax_max.loc[[index_2]]], ignore_index=True)

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Roteiro']=roteiro

                        df_hoteis_pax_max.at[len(df_hoteis_pax_max)-1, 'Carros']=carro

    if len(df_hoteis_pax_max)>0:

        df_hoteis_pax_max['Horario Voo'] = pd.to_datetime(df_hoteis_pax_max['Horario Voo'], format='%H:%M:%S').dt.time
    
        df_hoteis_pax_max['Menor Horário'] = pd.to_datetime(df_hoteis_pax_max['Menor Horário'], format='%H:%M:%S').dt.time

    for index in range(len(df_hoteis_pax_max)):

        df_hoteis_pax_max.at[index, 'Data Horario Apresentacao'] = \
            definir_horario_primeiro_hotel(df_hoteis_pax_max, index)

    df_servicos = df_servicos.reset_index(drop=True)

    if 'index' in df_hoteis_pax_max.columns.tolist():

        df_hoteis_pax_max = df_hoteis_pax_max.drop(columns=['index'])

    return df_servicos, df_hoteis_pax_max, roteiro

def verificar_voos_undefined():

    if len(st.session_state.df_router[st.session_state.df_router['Horario Voo']=='undefined']['Voo'].unique())>0:

        nome_voos_undefined = ', '.join(st.session_state.df_router[st.session_state.df_router['Horario Voo']=='undefined']['Voo'].unique())

        st.error(f'Os voos {nome_voos_undefined} foram cadastrados com horário vazio para alguma data específica. Por favor, entre nos cadastros deles, elimine essas agendas com horário vazio, comunique Thiago e tente novamente')

        st.stop()
        
def puxar_dados_phoenix():

    st.session_state.df_router = gerar_df_phoenix('vw_router', 'test_phoenix_recife')

    verificar_voos_undefined()

    st.session_state.df_router = st.session_state.df_router[(st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                            (~st.session_state.df_router['Status da Reserva'].isin(['CANCELADO', 'RASCUNHO', 'PENDENCIA DE IMPORTAÇÃO']))].reset_index(drop=True)

    st.session_state.df_router['Data Horario Apresentacao Original'] = st.session_state.df_router['Data Horario Apresentacao']

def objetos_parametros(row1):

    # Primeira coluna dos parâmetros

    with row1[0]:

        intervalo_inicial_pga_cab_pos_11 = objeto_intervalo('Antecipação Último Hotel | Porto ou Cabo | Voos após 11:00', time(4, 00), 'intervalo_inicial_pga_cab_pos_11')
        
        intervalo_inicial_pga_cab_pre_11 = objeto_intervalo('Antecipação Último Hotel | Porto ou Cabo | Voos antes 11:00', time(3, 30), 'intervalo_inicial_pga_cab_pre_11')
        
        intervalo_inicial_rec = objeto_intervalo('Antecipação Último Hotel | Recife', time(2, 30), 'intervalo_inicial_rec')

        intervalo_inicial_carneiros = objeto_intervalo('Antecipação Último Hotel | Carneiros', time(4, 30), 'intervalo_inicial_carneiros')

        max_hoteis_pga = st.number_input('Máximo de Hoteis por Carro - Porto', step=1, value=4, key='max_hoteis_pga')

    # Segunda coluna dos parâmetros

    with row1[1]:

        intervalo_inicial_mar_jpa = objeto_intervalo('Antecipação Último Hotel | Maragogi', time(5, 00), 'intervalo_inicial_mar_jpa')

        intervalo_inicial_ol = objeto_intervalo('Antecipação Último Hotel | Olinda', time(3, 00), 'intervalo_inicial_ol')

        intervalo_inicial_mil = objeto_intervalo('Antecipação Último Hotel | Milagres ou Fazenda Nova ou João Pessoa', time(6, 00), 'intervalo_inicial_mil')

        max_hoteis_rec = st.number_input('Máximo de Hoteis por Carro - Recife, Cabo, Maragogi, Olinda, Fazenda Nova, Carneiros, João Pessoa, Alagoas, Maceió e Milagres', step=1, value=3, key='max_hoteis_rec')

    # Terceira coluna dos parâmetros

    with row1[2]:

        intervalo_inicial_mcz = objeto_intervalo('Antecipação Último Hotel | Alagoas ou Maceió', time(7, 0), 'intervalo_inicial_mcz')

        intervalo_pu_hotel = objeto_intervalo('Intervalo Hoteis | Primeiro vs Último', time(0, 40), 'intervalo_pu_hotel')

        intervalo_hoteis_bairros_iguais = objeto_intervalo('Intervalo Entre Hoteis', time(0, 10), 'intervalo_hoteis_bairros_iguais')

        pax_max = st.number_input('Máximo de Paxs por Carro', step=1, value=48, key='pax_max')

        pax_cinco_min = st.number_input('Paxs Extras', step=1, value=100, key='pax_cinco_min', help='Número de paxs para aumentar intervalo entre hoteis em 5 minutos')

def definir_horarios_sem_maraca_serrambi(df_servicos):

    if st.session_state.servico_roteiro=='OUT (PORTO DE GALINHAS)':

        lista_regioes_roteiro = df_servicos['Região'].unique().tolist()

        if not 'MARACAÍPE' in lista_regioes_roteiro and not 'SERRAMBI' in lista_regioes_roteiro and 'VIA LOCAL' in lista_regioes_roteiro and \
            ('VILA 1' in lista_regioes_roteiro or 'VILA 2' in lista_regioes_roteiro):

            df_via_local = df_servicos[df_servicos['Região']=='VIA LOCAL'].reset_index(drop=True)

            df_outras_regioes = df_servicos[df_servicos['Região']!='VIA LOCAL'].reset_index(drop=True)

            df_nova_ordenacao = pd.concat([df_outras_regioes, df_via_local], ignore_index=True)

            df_nova_ordenacao = gerar_horarios_apresentacao_2(df_nova_ordenacao)

            df_servicos = df_nova_ordenacao

            return df_servicos

def roteirizar_sem_maraca_serrambi(df_servicos):

    df_roteiros_carros = df_servicos[['Roteiro', 'Carros']].drop_duplicates().reset_index(drop=True)

    for index in range(len(df_roteiros_carros)):

        roteiro_referencia = df_roteiros_carros.at[index, 'Roteiro']

        carro_referencia = df_roteiros_carros.at[index, 'Carros']

        df_referencia = df_servicos[(df_servicos['Roteiro']==roteiro_referencia) & (df_servicos['Carros']==carro_referencia)].reset_index()

        df_referencia = definir_horarios_sem_maraca_serrambi(df_referencia)

        if df_referencia is not None:

            for index_2, index_principal_ref in df_referencia['index'].items():

                df_servicos.at[index_principal_ref, 'Data Horario Apresentacao'] = df_referencia.at[index_2, 'Data Horario Apresentacao']

    return df_servicos

def verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos):

    lista_roteiros = df_router_filtrado_2['Roteiro'].unique().tolist()

    for roteiro_referencia in lista_roteiros:

        df_servicos_principal = df_router_filtrado_2[(df_router_filtrado_2['Roteiro']==roteiro_referencia)][['Id_Servico', 'Data Horario Apresentacao', 'Roteiro', 'Carros']].reset_index(drop=True)

        df_servicos_alternativo = df_roteiros_alternativos[(df_roteiros_alternativos['Roteiro']==roteiro_referencia)][['Id_Servico', 'Data Horario Apresentacao', 'Roteiro', 'Carros']].reset_index(drop=True)

        df_servicos_alternativo['Id_Servico'] = df_servicos_alternativo['Id_Servico'].astype('int64')

        df_servicos_alternativo['Roteiro'] = df_servicos_alternativo['Roteiro'].astype('int64')

        df_servicos_alternativo['Carros'] = df_servicos_alternativo['Carros'].astype('int64')

        df_servicos_principal['Id_Servico'] = df_servicos_principal['Id_Servico'].astype('int64')

        df_servicos_principal['Roteiro'] = df_servicos_principal['Roteiro'].astype('int64')

        df_servicos_principal['Carros'] = df_servicos_principal['Carros'].astype('int64')

        if df_servicos_principal.equals(df_servicos_alternativo):

            df_roteiros_alternativos = df_roteiros_alternativos[(df_roteiros_alternativos['Roteiro']!=roteiro_referencia)].reset_index(drop=True)

    return df_roteiros_alternativos

def gerar_roteiros_alternativos_4(df_servicos, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis):

    df_roteiros_alternativos = pd.DataFrame(columns=df_servicos.columns.tolist())

    lista_roteiros_alternativos = df_servicos[df_servicos['Carros']==2]['Roteiro'].unique().tolist()

    for item in lista_roteiros_alternativos:

        df_ref = df_servicos[df_servicos['Roteiro']==item].reset_index(drop=True)

        n_carro_ref = 0

        while len(df_ref)>0:

            df_ref_group_hotel = df_ref.groupby('Est Origem')['Total ADT | CHD'].sum().reset_index()

            if n_carro_ref==0:

                df_ref_group_carro = df_ref.groupby('Carros')['Total ADT | CHD'].sum().reset_index()

                carro_max = df_ref_group_carro['Total ADT | CHD'].max()

                if carro_max > pax_max_micro:

                    target = st.session_state.pax_max

                elif carro_max > pax_max_van:

                    target = pax_max_micro

                elif carro_max > pax_max_utilitario:

                    target = pax_max_van

            else:

                paxs_total_roteiro = df_ref_group_hotel['Total ADT | CHD'].sum()

                if paxs_total_roteiro > pax_max_micro:

                    target = st.session_state.pax_max

                elif paxs_total_roteiro > pax_max_van:

                    target = pax_max_micro

                elif paxs_total_roteiro > pax_max_utilitario:

                    target = pax_max_van

            n_carro_ref+=1

            df_agrupado_qtd_paxs = df_ref_group_hotel.groupby('Total ADT | CHD')['Est Origem'].count().reset_index()

            df_agrupado_qtd_paxs['Paxs Grupo Hotel'] = df_agrupado_qtd_paxs['Total ADT | CHD'] * df_agrupado_qtd_paxs['Est Origem']

            if len(df_agrupado_qtd_paxs)>=max_hoteis:

                lim_combinacoes = max_hoteis

            else:

                lim_combinacoes = len(df_agrupado_qtd_paxs)

            closest_sum = None
            closest_indices = []

            for r in range(1, lim_combinacoes+1):

                for comb in combinations(df_agrupado_qtd_paxs.index, r):

                    current_sum = df_agrupado_qtd_paxs.loc[list(comb), 'Paxs Grupo Hotel'].sum()

                    n_hoteis = df_agrupado_qtd_paxs.loc[list(comb), 'Est Origem'].sum()
                    
                    # Se for igual ao target, já encontramos a combinação perfeita
                    if current_sum == target and n_hoteis<=lim_combinacoes:
                        closest_sum = current_sum
                        closest_indices = list(comb)
                        encontrou_solucao = 1
                        break

                    else:

                        encontrou_solucao = 0

            if encontrou_solucao==1:
            
                ref_result_df = df_agrupado_qtd_paxs.loc[closest_indices]
            
                result_df = df_ref_group_hotel[df_ref_group_hotel['Total ADT | CHD'].isin(ref_result_df['Total ADT | CHD'].unique())]

            else:

                if len(df_ref_group_hotel)>=max_hoteis:

                    lim_combinacoes = max_hoteis

                else:

                    lim_combinacoes = len(df_ref_group_hotel)

                for r in range(lim_combinacoes, 0, -1):

                    for comb in combinations(df_ref_group_hotel.index, r):

                        current_sum = df_ref_group_hotel.loc[list(comb), 'Total ADT | CHD'].sum()
                        
                        # Se for igual ao target, já encontramos a combinação perfeita
                        if current_sum == target:
                            closest_sum = current_sum
                            closest_indices = list(comb)
                            break
                        
                        # Se estiver mais próximo do que a combinação anterior, atualizamos
                        if closest_sum is None or abs(target - current_sum) < abs(target - closest_sum):
                            closest_sum = current_sum
                            closest_indices = list(comb)
                    
                    # Parar o loop se a combinação exata foi encontrada
                    if closest_sum == target:
                        break

                result_df = df_ref_group_hotel.loc[closest_indices]

            lista_hoteis_melhor_comb = result_df['Est Origem'].tolist()

            df_rota_alternativa = df_ref[df_ref['Est Origem'].isin(lista_hoteis_melhor_comb)].sort_values(by='Sequência', ascending=False).reset_index(drop=True)

            df_rota_alternativa['Carros'] = n_carro_ref

            df_rota_alternativa = gerar_horarios_apresentacao_2(df_rota_alternativa)

            df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_rota_alternativa], ignore_index=True)

            df_ref = df_ref[~df_ref['Est Origem'].isin(lista_hoteis_melhor_comb)].reset_index(drop=True)

    return df_roteiros_alternativos

def recalcular_horarios_menor_horario(df_router_filtrado_2):

    df_roteiros_carros = df_router_filtrado_2[['Roteiro', 'Carros', 'Junção']].drop_duplicates().reset_index(drop=True)

    df_roteiros_carros = df_roteiros_carros[~pd.isna(df_roteiros_carros['Junção'])].reset_index(drop=True)

    for index in range(len(df_roteiros_carros)):

        roteiro_referencia = df_roteiros_carros.at[index, 'Roteiro']

        carro_referencia = df_roteiros_carros.at[index, 'Carros']

        df_ref = df_router_filtrado_2[(df_router_filtrado_2['Roteiro']==roteiro_referencia) & (df_router_filtrado_2['Carros']==carro_referencia)].reset_index()

        horario_voo_mais_cedo = df_ref['Horario Voo'].min()

        horario_menor_horario = df_ref['Menor Horário'].min()

        if horario_voo_mais_cedo!=horario_menor_horario:

            df_ref['Menor Horário'] = horario_voo_mais_cedo

            df_ref = gerar_horarios_apresentacao_2(df_ref)

            for index_2, index_principal in df_ref['index'].items():

                df_router_filtrado_2.at[index_principal, 'Data Horario Apresentacao'] = df_ref.at[index_2, 'Data Horario Apresentacao']

    return df_router_filtrado_2

def verificar_preenchimento_df_hoteis(df_hoteis_ref):

    hoteis_sem_regiao = df_hoteis_ref[df_hoteis_ref['Região']=='']['Est Origem'].unique().tolist()

    hoteis_sem_sequencia = df_hoteis_ref[pd.isna(df_hoteis_ref['Sequência'])]['Est Origem'].unique().tolist()

    hoteis_sem_acessibilidade = df_hoteis_ref[df_hoteis_ref[['Bus', 'Micro', 'Van', 'Utilitario']].isna().all(axis=1)]['Est Origem'].unique().tolist()

    hoteis_unificados = list(set(hoteis_sem_regiao + hoteis_sem_sequencia + hoteis_sem_acessibilidade))

    if len(hoteis_unificados)>0:

        nome_hoteis = ', '.join(hoteis_unificados)

        st.error(f'Os hoteis {nome_hoteis} estão com cadastro errado. Pode estar faltando o número da sequência, o nome da região ou o preenchimento da acessibilidade. Verifique, ajuste e tente novamente.')

        st.stop()

def puxar_historico(id_gsheet, lista_abas, lista_nomes_df_hoteis):

    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key(id_gsheet)

    for index in range(len(lista_abas)):

        aba = lista_abas[index]

        df_hotel = lista_nomes_df_hoteis[index]
        
        sheet = spreadsheet.worksheet(aba)

        sheet_data = sheet.get_all_values()

        st.session_state[df_hotel] = pd.DataFrame(sheet_data[1:], columns=sheet_data[0])

def inserir_df_rotas_geradas(aba_excel, df_insercao):
    
    nome_credencial = st.secrets["CREDENCIAL_SHEETS"]
    credentials = service_account.Credentials.from_service_account_info(nome_credencial)
    scope = ['https://www.googleapis.com/auth/spreadsheets']
    credentials = credentials.with_scopes(scope)
    client = gspread.authorize(credentials)
    
    # Abertura da planilha e aba
    spreadsheet = client.open_by_key('1az0u1yGWqIXE9KcUro6VznsVj7d5fozhH3dDsT1eI6A')
    sheet = spreadsheet.worksheet(aba_excel)
    
    # Limpeza do intervalo A2:Z10000
    sheet.batch_clear(["A2:AR10000"])
    
    def format_value(value):
        if isinstance(value, pd.Timestamp):  # Para colunas datetime no DataFrame
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif type(value) is datetime:  # Para objetos do tipo datetime
            return value.strftime('%Y-%m-%d')
        elif isinstance(value, float):  # Formatação opcional para floats
            return f"{value:.2f}"
        else:
            return str(value)  # Para outros tipos
    
    # Aplicando formatação aos valores do DataFrame
    data = df_insercao.applymap(format_value).values.tolist()
    start_cell = "A2"  # Sempre insere a partir da segunda linha
    sheet.update(start_cell, data)

def salvar_rotas_historico(df_pdf):

    puxar_historico('1az0u1yGWqIXE9KcUro6VznsVj7d5fozhH3dDsT1eI6A', ['Histórico Roteiros'], ['df_historico_roteiros'])

    st.session_state.df_historico_roteiros['Data Execucao'] = pd.to_datetime(st.session_state.df_historico_roteiros['Data Execucao']).dt.date

    st.session_state.df_historico_roteiros = st.session_state.df_historico_roteiros[~((st.session_state.df_historico_roteiros['Servico']==st.session_state.servico_roteiro) & 
                                                                                      (st.session_state.df_historico_roteiros['Data Execucao']==st.session_state.data_roteiro))].reset_index(drop=True)
    
    st.session_state.df_historico_roteiros = pd.concat([st.session_state.df_historico_roteiros, df_pdf], ignore_index=True)

    inserir_df_rotas_geradas('Histórico Roteiros', st.session_state.df_historico_roteiros)
    
st.set_page_config(layout='wide')

st.title('Roteirizador de Transfer Out - Recife')

st.divider()

st.header('Parâmetros')

row1 = st.columns(3)

# Verificando se o link está com ID do usuário

if not st.query_params or not st.query_params["userId"]:

    st.error("Usuário não autenticado")

    st.stop()

# Carrega os dados da tabela 'user`

if not 'df_user' in st.session_state:
    
    st.session_state.df_user = getUser(st.query_params["userId"])

# Puxando dados do phoenix ao abrir o roteirizador

if not 'df_router' in st.session_state:

    puxar_dados_phoenix()

if 'df_juncao_voos' not in st.session_state:

    st.session_state.df_juncao_voos = pd.DataFrame(columns=['Servico', 'Voo', 'Horário', 'Tipo do Translado', 'Junção'])

if 'df_horario_esp_ultimo_hotel' not in st.session_state:

    st.session_state.df_horario_esp_ultimo_hotel = pd.DataFrame(columns=['Junção/Voo/Reserva', 'Antecipação Último Hotel'])

objetos_parametros(row1)

st.divider()

st.header('Juntar Voos')

row2 = st.columns(3)

# Botões Atualizar Hoteis, Atualizar Dados Phoenix, campos de Data e botões de roteirizar e visualizar voos

with row2[0]:

    atualizar_phoenix = st.button('Atualizar Dados Phoenix')

    if atualizar_phoenix:

        puxar_dados_phoenix()

        if 'df_servico_voos_horarios' in st.session_state:
            
            st.session_state['df_servico_voos_horarios'] = pd.DataFrame(columns=['Servico', 'Voo', 'Horario Voo'])

    # Campo de data

    container_roteirizar = st.container(border=True)

    data_roteiro = container_roteirizar.date_input('Data do Roteiro', value=None, format='DD/MM/YYYY', key='data_roteiro')

    df_router_data_roteiro = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & (st.session_state.df_router['Tipo de Servico']=='OUT') & (st.session_state.df_router['Status do Servico']!='CANCELADO')].reset_index(drop=True)

    lista_servicos = df_router_data_roteiro[df_router_data_roteiro['Servico']!='OUT (SERRAMBI)']['Servico'].unique().tolist()

    lista_voos_data_roteiro = df_router_data_roteiro['Voo'].unique().tolist()

    servico_roteiro = container_roteirizar.selectbox('Serviço', lista_servicos, index=None, placeholder='Escolha um Serviço', key='servico_roteiro')  

    row_container = container_roteirizar.columns(2)

    # Botão roteirizar

    with row_container[0]:

        roteirizar = st.button('Roteirizar')

# Gerar dataframe com os voos da data selecionada e imprimir na tela o dataframe

if servico_roteiro:

    if servico_roteiro=='OUT (PORTO DE GALINHAS)' or servico_roteiro=='OUT (SERRAMBI)':

        df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                        (st.session_state.df_router['Tipo de Servico']=='OUT') & 
                                                        (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                        ((st.session_state.df_router['Servico']=='OUT (PORTO DE GALINHAS)') | 
                                                         (st.session_state.df_router['Servico']=='OUT (SERRAMBI)'))].reset_index(drop=True)

    else:

        df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                        (st.session_state.df_router['Tipo de Servico']=='OUT') & 
                                                        (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                        (st.session_state.df_router['Servico']==servico_roteiro)]\
                                                        .reset_index(drop=True)
    
    st.session_state.df_servico_voos_horarios = df_router_filtrado[['Servico', 'Voo', 'Horario Voo', 'Tipo do Translado']].sort_values(by=['Horario Voo']).drop_duplicates().reset_index(drop=True)

    df_router_filtrado = df_router_filtrado[~df_router_filtrado['Observacao'].str.upper().str.contains('CLD', na=False)]

    st.session_state.df_servico_voos_horarios['Paxs Regular']=0

    for index in range(len(st.session_state.df_servico_voos_horarios)):

        servico = st.session_state.df_servico_voos_horarios.at[index, 'Servico']

        voo = st.session_state.df_servico_voos_horarios.at[index, 'Voo']

        h_voo = st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo']

        total_paxs_ref = df_router_filtrado[(df_router_filtrado['Servico']==servico) & (df_router_filtrado['Voo']==voo) & (df_router_filtrado['Horario Voo']==h_voo) & (df_router_filtrado['Modo do Servico']=='REGULAR')]['Total ADT'].sum() + \
            df_router_filtrado[(df_router_filtrado['Servico']==servico) & (df_router_filtrado['Voo']==voo) & (df_router_filtrado['Horario Voo']==h_voo) & (df_router_filtrado['Modo do Servico']=='REGULAR')]['Total CHD'].sum()
        
        st.session_state.df_servico_voos_horarios.at[index, 'Paxs Regular'] = total_paxs_ref

    st.session_state.df_servico_voos_horarios['Horario Voo'] = pd.to_datetime(st.session_state.df_servico_voos_horarios['Horario Voo'], format='%H:%M:%S')

    for index in range(len(st.session_state.df_servico_voos_horarios)):

        tipo_translado = st.session_state.df_servico_voos_horarios.at[index, 'Tipo do Translado']

        horario_voo = st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo']

        if tipo_translado=='Internacional':

            if (servico_roteiro=='OUT (PORTO DE GALINHAS)' and horario_voo.time()<pd.to_datetime('11:00:00').time()) | (servico_roteiro=='OUT (OLINDA)') | \
                (servico_roteiro=='OUT (BOA VIAGEM | PIEDADE)'):

                st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo Ajustado'] = st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo']\
                    - transformar_timedelta(time(0,30))

            else:

                st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo Ajustado'] = st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo']
            
        else:

            st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo Ajustado'] = st.session_state.df_servico_voos_horarios.at[index, 'Horario Voo']
            
    st.session_state.df_servico_voos_horarios['Horario Voo'] = pd.to_datetime(st.session_state.df_servico_voos_horarios['Horario Voo'], format='%H:%M:%S').dt.time
    
    st.session_state.df_servico_voos_horarios['Horario Voo Ajustado'] = pd.to_datetime(st.session_state.df_servico_voos_horarios['Horario Voo Ajustado'], format='%H:%M:%S').dt.time
    
    st.session_state.df_servico_voos_horarios = st.session_state.df_servico_voos_horarios.sort_values(by='Horario Voo Ajustado').reset_index(drop=True)

# Botão pra limpar todos os dataframes

with row2[1]:

    container_botao = st.container()

    limpar_tudo = container_botao.button('Limpar Tudo', use_container_width=True)

if limpar_tudo:

    st.session_state.df_juncao_voos = st.session_state.df_juncao_voos.iloc[0:0]

    st.session_state.df_servico_voos_horarios = st.session_state.df_servico_voos_horarios.iloc[0:0]

    st.session_state.df_horario_esp_ultimo_hotel = st.session_state.df_horario_esp_ultimo_hotel.iloc[0:0]

    st.session_state.df_router_filtrado_2 = st.session_state.df_router_filtrado_2.iloc[0:0]

# Plotar voos do serviço/dia na tela

if servico_roteiro and 'df_servico_voos_horarios' in st.session_state:

    with row2[0]:

        st.dataframe(st.session_state.df_servico_voos_horarios, hide_index=True) 

# Formulário de Junção de Voos

with row2[1]:

    with st.form('juntar_voos_form_novo'):

        # Captando intervalo entre voos

        horario_inicial = st.time_input('Horário Inicial Voo (Ajustado)', value=None, key='horario_inicial', step=300)

        horario_final = st.time_input('Horário Final Voo (Ajustado)', value=None, key='horario_final', step=300) 

        lancar_juncao = st.form_submit_button('Lançar Junção')

        # Lançando junção

        if lancar_juncao and horario_inicial and horario_final:

            # Filtrando dataframe por Horario Voo e Servico

            if horario_inicial and horario_final and servico_roteiro:

                if servico_roteiro!='OUT (PORTO DE GALINHAS)' and servico_roteiro!='OUT (SERRAMBI)':

                    df_voos_hi_hf = st.session_state.df_servico_voos_horarios\
                        [(st.session_state.df_servico_voos_horarios['Horario Voo Ajustado']>=horario_inicial) & 
                        (st.session_state.df_servico_voos_horarios['Horario Voo Ajustado']<=horario_final) & 
                        (st.session_state.df_servico_voos_horarios['Servico']==servico_roteiro)]\
                            [['Servico', 'Voo', 'Horario Voo', 'Tipo do Translado', 'Paxs Regular']].reset_index(drop=True)
                    
                else:

                    df_voos_hi_hf = st.session_state.df_servico_voos_horarios\
                        [(st.session_state.df_servico_voos_horarios['Horario Voo Ajustado']>=horario_inicial) & 
                        (st.session_state.df_servico_voos_horarios['Horario Voo Ajustado']<=horario_final) & 
                        ((st.session_state.df_servico_voos_horarios['Servico']=='OUT (PORTO DE GALINHAS)') | 
                        (st.session_state.df_servico_voos_horarios['Servico']=='OUT (SERRAMBI)'))]\
                            [['Servico', 'Voo', 'Horario Voo', 'Tipo do Translado', 'Paxs Regular']].reset_index(drop=True)
                
                df_voos_hi_hf = df_voos_hi_hf.rename(columns={'Horario Voo': 'Horário'})

                df_voos_hi_hf = df_voos_hi_hf[df_voos_hi_hf['Paxs Regular']!=0].reset_index(drop=True)

                df_voos_hi_hf = df_voos_hi_hf[['Servico', 'Voo', 'Horário', 'Tipo do Translado']]
            
                if len(st.session_state.df_juncao_voos)>0:

                    juncao_max = st.session_state.df_juncao_voos['Junção'].max()

                    df_voos_hi_hf['Junção'] = juncao_max+1

                else:

                    df_voos_hi_hf['Junção'] = 1  

            st.session_state.df_juncao_voos = pd.concat([st.session_state.df_juncao_voos, df_voos_hi_hf], ignore_index=True)

# Voos não operantes e multiselect p/ horários específicos de último hotel em junções ou voos

with row2[1]:

    voos_nao_operantes = st.multiselect('Voos s/ Operar', sorted(lista_voos_data_roteiro))

    horario_ultimo_hotel_especifico = st.multiselect('Usar antecipação específica de último hotel p/ voo, junção ou reserva privativa?', ['Sim'])

# Plotando formulário para lançamento de horários específicos de último hotel em junções ou voos

if len(horario_ultimo_hotel_especifico)>0:

    with row2[1]:

        with st.form('horario_ph_especifico'):

            if servico_roteiro=='OUT (PORTO DE GALINHAS)' or servico_roteiro=='OUT (SERRAMBI)':

                df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                                (st.session_state.df_router['Tipo de Servico']=='OUT') & 
                                                                (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                                ((st.session_state.df_router['Servico']=='OUT (PORTO DE GALINHAS)') | 
                                                                (st.session_state.df_router['Servico']=='OUT (SERRAMBI)'))].reset_index(drop=True)

            else:

                df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & 
                                                                (st.session_state.df_router['Tipo de Servico']=='OUT') & 
                                                                (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                                (st.session_state.df_router['Servico']==servico_roteiro)]\
                                                                .reset_index(drop=True)
                
            df_router_filtrado = df_router_filtrado[~df_router_filtrado['Observacao'].str.upper().str.contains('CLD', na=False)]

            lista_juncoes = st.session_state.df_juncao_voos['Junção'].unique().tolist()

            lista_voos_com_juncao = st.session_state.df_juncao_voos['Voo'].unique().tolist()

            lista_voos_sem_juncao = [item for item in st.session_state.df_servico_voos_horarios['Voo'].unique().tolist() if not item in lista_voos_com_juncao]

            lista_juncoes.extend(lista_voos_sem_juncao)

            lista_reservas_pvt = df_router_filtrado[df_router_filtrado['Modo do Servico']!='REGULAR']['Reserva'].unique().tolist()

            lista_juncoes.extend(lista_reservas_pvt)

            juncao_ou_voo = st.selectbox('Escolha a Junção/Voo/Reserva Privativa', lista_juncoes, index=None)

            intervalo_inicial_especifico = objeto_intervalo('Antecipação Último Hotel', time(3, 0), 'intervalo_inicial_especifico')

            intervalo_inicial_especifico_str = str(intervalo_inicial_especifico)

            if len(intervalo_inicial_especifico_str)==7:

                intervalo_inicial_especifico_str = f'0{intervalo_inicial_especifico_str}'

            lancar_h_esp = st.form_submit_button('Lançar Antecipação Específica')

            if lancar_h_esp:

                lista_dados = [juncao_ou_voo, intervalo_inicial_especifico_str]

                st.session_state.df_horario_esp_ultimo_hotel.loc[len(st.session_state.df_horario_esp_ultimo_hotel)]=lista_dados

# Botões pra limpar junções

with row2[2]:

    row2_1 = st.columns(2)

    # Limpar todas as junções

    with row2_1[0]:

        limpar_juncoes = st.button('Limpar Todas as Junções')

    # Limpar junções específicas

    with row2_1[1]:

        limpar_juncao_esp = st.button('Limpar Junção Específica')

        juncao_limpar = st.number_input('Junção', step=1, value=None, key='juncao_limpar')

    # Se for pra limpar todas as junções

    if limpar_juncoes:

        voo=None

        st.session_state.df_juncao_voos = pd.DataFrame(columns=['Servico', 'Voo', 'Horário', 'Tipo do Translado', 'Junção'])

    # Se for limpar junções específicas

    if limpar_juncao_esp and juncao_limpar==1: # se a exclusão for da junção 1

        st.session_state.df_juncao_voos = st.session_state.df_juncao_voos[st.session_state.df_juncao_voos['Junção']!=juncao_limpar].reset_index(drop=True)

        for index, value in st.session_state.df_juncao_voos['Junção'].items():

            st.session_state.df_juncao_voos.at[index, 'Junção']-=1

    elif limpar_juncao_esp and juncao_limpar: # se a exclusão não for da junção 1

        st.session_state.df_juncao_voos = st.session_state.df_juncao_voos[st.session_state.df_juncao_voos['Junção']!=juncao_limpar].reset_index(drop=True)

        juncao_ref=1

        for juncao in st.session_state.df_juncao_voos['Junção'].unique().tolist():

            if juncao>1:

                juncao_ref+=1

                st.session_state.df_juncao_voos.loc[st.session_state.df_juncao_voos['Junção']==juncao, 'Junção']=juncao_ref   

    container_df_juncao_voos = st.container()     

    container_df_juncao_voos.dataframe(st.session_state.df_juncao_voos, hide_index=True, use_container_width=True)

# Plotar botão de limpar lançamentos de horários específicos p/ junções/voos e plotar dataframe com os lançamentos

if servico_roteiro and 'df_horario_esp_ultimo_hotel' in st.session_state:

    with row2[2]:

        limpar_lancamentos = st.button('Limpar Lançamentos')

        if limpar_lancamentos:

            st.session_state.df_horario_esp_ultimo_hotel = pd.DataFrame(columns=['Junção/Voo/Reserva', 'Antecipação Último Hotel'])

        st.dataframe(st.session_state.df_horario_esp_ultimo_hotel, hide_index=True) 

# Roteirizando Regiões

if roteirizar:

    puxar_sequencias_hoteis('1az0u1yGWqIXE9KcUro6VznsVj7d5fozhH3dDsT1eI6A', 
                            ['Hoteis Porto', 'Hoteis Boa Viagem', 'Hoteis Piedade', 'Hoteis Cabo', 'Hoteis Maragogi', 'Hoteis Olinda', 'Hoteis Fazenda Nova', 'Hoteis Carneiros', 'Hoteis Joao Pessoa', 
                             'Hoteis Recife Centro', 'Hoteis Alagoas', 'Hoteis Maceio', 'Hoteis Milagres', 'Hoteis Milagres/Patacho/Pt Pedras'], 
                             ['df_hoteis_porto', 'df_hoteis_boa_viagem', 'df_hoteis_piedade', 'df_hoteis_cabo', 'df_hoteis_maragogi', 'df_hoteis_olinda', 'df_hoteis_fazenda_nova', 
                              'df_hoteis_carneiros', 'df_hoteis_joao_pessoa', 'df_hoteis_recife_centro', 'df_hoteis_alagoas', 'df_hoteis_maceio', 'df_hoteis_milagres', 'df_hoteis_mil_pat_ped'])
    
    st.session_state.dict_regioes_hoteis = {'OUT (PORTO DE GALINHAS)': ['df_hoteis_porto', 'Porto', 'Hoteis Porto', 'Porto'], 
                                            'OUT (SERRAMBI)': ['df_hoteis_serrambi', 'Serrambi', 'Hoteis Serrambi', 'Serrambi'], 
                                            'OUT (CABO DE STO AGOSTINHO)': ['df_hoteis_cabo', 'Cabo', 'Hoteis Cabo', 'Cabo'], 
                                            'OUT (BOA VIAGEM | PIEDADE)': ['df_hoteis_boa_viagem', 'Boa Viagem', 'Hoteis Boa Viagem', 'Boa Viagem'], 
                                            'OUT (MARAGOGI | JAPARATINGA)': ['df_hoteis_maragogi', 'Maragogi', 'Hoteis Maragogi', 'Maragogi'], 
                                            'OUT (OLINDA)': ['df_hoteis_olinda', 'Olinda', 'Hoteis Olinda', 'Olinda'], 
                                            'OUT (FAZENDA NOVA)': ['df_hoteis_fazenda_nova', 'Fazenda Nova', 'Hoteis Fazenda Nova', 'Fazenda Nova'], 
                                            'OUT (JOÃO PESSOA-PB)': ['df_hoteis_joao_pessoa', 'Joao Pessoa', 'Hoteis Joao Pessoa', 'João Pessoa'], 
                                            'OUT (MILAGRES)': ['df_hoteis_milagres', 'Milagres', 'Hoteis Milagres', 'Milagres'], 
                                            'OUT (CARNEIROS I TAMANDARÉ)': ['df_hoteis_carneiros', 'Carneiros', 'Hoteis Carneiros', 'Carneiros'], 
                                            'OUT (ALAGOAS)': ['df_hoteis_alagoas', 'Alagoas', 'Hoteis Alagoas', 'Alagoas'], 
                                            'OUT (MACEIÓ-AL)': ['df_hoteis_maceio', 'Maceio', 'Hoteis Maceio', 'Maceió'], 
                                            'OUT (MILAGRES / PATACHO / PORTO DE PEDRAS)': ['df_hoteis_mil_pat_ped', 'Milagres-Patacho-Porto de Pedras', 'Hoteis Milagres/Patacho/Pt Pedras', 'Milagres-Patacho-Porto de Pedras'], 
                                            'OUT RECIFE (CENTRO)': ['df_hoteis_recife_centro', 'Recife Centro', 'Hoteis Recife Centro', 'Recife Centro']}

    nome_df_hotel = st.session_state.dict_regioes_hoteis[servico_roteiro][0]

    nome_html_ref = st.session_state.dict_regioes_hoteis[servico_roteiro][1]

    nome_aba_excel = st.session_state.dict_regioes_hoteis[servico_roteiro][2]

    nome_regiao = st.session_state.dict_regioes_hoteis[servico_roteiro][3]

    df_hoteis_ref = st.session_state[nome_df_hotel]

    verificar_preenchimento_df_hoteis(df_hoteis_ref)

    if servico_roteiro=='OUT (PORTO DE GALINHAS)':

        df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & (st.session_state.df_router['Tipo de Servico']=='OUT') &  
                                                        (st.session_state.df_router['Status do Servico']!='CANCELADO') & 
                                                        ((st.session_state.df_router['Servico']==servico_roteiro) | (st.session_state.df_router['Servico']=='OUT (SERRAMBI)')) & 
                                                        ~(st.session_state.df_router['Voo'].isin(voos_nao_operantes))].reset_index(drop=True)

    else:

        df_router_filtrado = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & (st.session_state.df_router['Tipo de Servico']=='OUT') &  
                                                        (st.session_state.df_router['Status do Servico']!='CANCELADO') & (st.session_state.df_router['Servico']==servico_roteiro) & 
                                                        ~(st.session_state.df_router['Voo'].isin(voos_nao_operantes))].reset_index(drop=True)

    # Categorizando serviços com 'CADEIRANTE' na observação
    
    df_router_filtrado['Modo do Servico'] = df_router_filtrado.apply(lambda row: 'CADEIRANTE' if verificar_cadeirante(row['Observacao']) else row['Modo do Servico'], axis=1)
    
    # Excluindo linhas onde exite 'CLD' na observação

    df_router_filtrado = df_router_filtrado[~df_router_filtrado['Observacao'].str.upper().str.contains('CLD', na=False)]

    if len(df_router_filtrado)==0:
    
        st.error('Depois de filtrar as reservas com CLD na observação não sobraram serviços para roteirizar.')

        st.stop()

    if servico_roteiro=='OUT (BOA VIAGEM | PIEDADE)':

        df_hoteis_ref = pd.concat([df_hoteis_ref, st.session_state.df_hoteis_piedade], ignore_index=True)

    # Verificando se todos os hoteis estão na lista da sequência
 
    itens_faltantes, lista_hoteis_df_router = gerar_itens_faltantes(df_router_filtrado, df_hoteis_ref)

    pax_max_utilitario = 4

    pax_max_van = 15

    pax_max_micro = 26

    if len(itens_faltantes)==0:

        # Mensagens de andamento do script informando como foi a verificação dos hoteis cadastrados

        st.success('Todos os hoteis estão cadastrados na lista de sequência de hoteis')

        df_router_filtrado_2 = criar_df_servicos_2(df_router_filtrado, st.session_state.df_juncao_voos, df_hoteis_ref)

        if servico_roteiro=='OUT (BOA VIAGEM | PIEDADE)':

            max_hoteis_roteirizacao = st.session_state.max_hoteis_rec

            lista_hoteis_piedade = st.session_state.df_hoteis_piedade['Est Origem'].unique().tolist()

            df_router_piedade = df_router_filtrado_2[df_router_filtrado_2['Est Origem'].isin(lista_hoteis_piedade)].reset_index(drop=True)
            
            df_router_bv = df_router_filtrado_2[~df_router_filtrado_2['Est Origem'].isin(lista_hoteis_piedade)].reset_index(drop=True)

            df_router_piedade = inserir_coluna_horario_ultimo_hotel(df_router_piedade)

            df_router_bv = inserir_coluna_horario_ultimo_hotel(df_router_bv)

            roteiro = 0

            df_router_piedade['Horario Voo'] = pd.to_datetime(df_router_piedade['Horario Voo'], format='%H:%M:%S').dt.time

            df_router_bv['Horario Voo'] = pd.to_datetime(df_router_bv['Horario Voo'], format='%H:%M:%S').dt.time

            lista_colunas = ['index']

            df_hoteis_pax_max_piedade = pd.DataFrame(columns=lista_colunas.extend(df_router_piedade.columns.tolist()))

            df_hoteis_pax_max_bv = pd.DataFrame(columns=lista_colunas.extend(df_router_bv.columns.tolist()))

            df_router_piedade, df_hoteis_pax_max_piedade, roteiro = \
                roteirizar_hoteis_mais_pax_max(df_router_piedade, roteiro, df_hoteis_pax_max_piedade)

            df_router_bv, df_hoteis_pax_max_bv, roteiro = \
                roteirizar_hoteis_mais_pax_max(df_router_bv, roteiro, df_hoteis_pax_max_bv)
            
            df_hoteis_pax_max_inacessibilidade_utilitario_bv = pd.DataFrame(columns=lista_colunas.extend(df_router_bv.columns.tolist()))

            df_hoteis_pax_max_inacessibilidade_van_bv = pd.DataFrame(columns=lista_colunas.extend(df_router_bv.columns.tolist()))

            df_hoteis_pax_max_inacessibilidade_micro_bv = pd.DataFrame(columns=lista_colunas.extend(df_router_bv.columns.tolist()))

            df_router_bv, df_hoteis_pax_max_inacessibilidade_utilitario_bv, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_bv, roteiro, df_hoteis_pax_max_inacessibilidade_utilitario_bv, pax_max_utilitario, 'Van')
            
            df_router_bv, df_hoteis_pax_max_inacessibilidade_van_bv, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_bv, roteiro, df_hoteis_pax_max_inacessibilidade_van_bv, pax_max_van, 'Micro')
            
            df_router_bv, df_hoteis_pax_max_inacessibilidade_micro_bv, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_bv, roteiro, df_hoteis_pax_max_inacessibilidade_micro_bv, pax_max_micro, 'Bus')
            
            df_hoteis_pax_max_inacessibilidade_utilitario_piedade = pd.DataFrame(columns=lista_colunas.extend(df_router_piedade.columns.tolist()))

            df_hoteis_pax_max_inacessibilidade_van_piedade = pd.DataFrame(columns=lista_colunas.extend(df_router_piedade.columns.tolist()))

            df_hoteis_pax_max_inacessibilidade_micro_piedade = pd.DataFrame(columns=lista_colunas.extend(df_router_piedade.columns.tolist()))

            df_router_piedade, df_hoteis_pax_max_inacessibilidade_utilitario_piedade, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_piedade, roteiro, df_hoteis_pax_max_inacessibilidade_utilitario_piedade, pax_max_utilitario, 'Van')
            
            df_router_piedade, df_hoteis_pax_max_inacessibilidade_van_piedade, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_piedade, roteiro, df_hoteis_pax_max_inacessibilidade_van_piedade, pax_max_van, 'Micro')
            
            df_router_piedade, df_hoteis_pax_max_inacessibilidade_micro_piedade, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_piedade, roteiro, df_hoteis_pax_max_inacessibilidade_micro_piedade, pax_max_micro, 'Bus')
            
            df_hoteis_pax_max = pd.concat([df_hoteis_pax_max_piedade, df_hoteis_pax_max_bv, df_hoteis_pax_max_inacessibilidade_utilitario_bv, df_hoteis_pax_max_inacessibilidade_van_bv, 
                                           df_hoteis_pax_max_inacessibilidade_micro_bv, df_hoteis_pax_max_inacessibilidade_utilitario_piedade, df_hoteis_pax_max_inacessibilidade_van_piedade, 
                                           df_hoteis_pax_max_inacessibilidade_micro_piedade], ignore_index=True)

            df_router_piedade, roteiro = gerar_horarios_apresentacao(df_router_piedade, roteiro, max_hoteis_roteirizacao)

            df_router_bv, roteiro = gerar_horarios_apresentacao(df_router_bv, roteiro, max_hoteis_roteirizacao)

            df_router_filtrado_2 = pd.concat([df_router_piedade, df_router_bv], ignore_index=True)

        elif servico_roteiro=='OUT (MILAGRES)' or servico_roteiro=='OUT (MACEIÓ-AL)' or servico_roteiro=='OUT (ALAGOAS)' or servico_roteiro=='OUT RECIFE (CENTRO)' or \
            servico_roteiro=='OUT (JOÃO PESSOA-PB)' or servico_roteiro=='OUT (CARNEIROS I TAMANDARÉ)' or servico_roteiro=='OUT (FAZENDA NOVA)' or servico_roteiro=='OUT (OLINDA)' or \
                servico_roteiro=='OUT (MARAGOGI | JAPARATINGA)' or servico_roteiro=='OUT (CABO DE STO AGOSTINHO)':

            max_hoteis_roteirizacao = st.session_state.max_hoteis_rec

            df_router_filtrado_2 = inserir_coluna_horario_ultimo_hotel(df_router_filtrado_2)

            roteiro = 0

            df_router_filtrado_2['Horario Voo'] = pd.to_datetime(df_router_filtrado_2['Horario Voo'], format='%H:%M:%S').dt.time

            lista_colunas = ['index']

            df_hoteis_pax_max = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

            df_router_filtrado_2, df_hoteis_pax_max, roteiro = \
                roteirizar_hoteis_mais_pax_max(df_router_filtrado_2, roteiro, df_hoteis_pax_max)
            
            df_hoteis_pax_max_inacessibilidade_utilitario = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

            df_hoteis_pax_max_inacessibilidade_van = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

            df_hoteis_pax_max_inacessibilidade_micro = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

            df_router_filtrado_2, df_hoteis_pax_max_inacessibilidade_utilitario, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_filtrado_2, roteiro, df_hoteis_pax_max_inacessibilidade_utilitario, pax_max_utilitario, 'Van')
            
            df_router_filtrado_2, df_hoteis_pax_max_inacessibilidade_van, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_filtrado_2, roteiro, df_hoteis_pax_max_inacessibilidade_van, pax_max_van, 'Micro')
            
            df_router_filtrado_2, df_hoteis_pax_max_inacessibilidade_micro, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_filtrado_2, roteiro, df_hoteis_pax_max_inacessibilidade_micro, pax_max_micro, 'Bus')
            
            df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hoteis_pax_max_inacessibilidade_utilitario, df_hoteis_pax_max_inacessibilidade_van, 
                                           df_hoteis_pax_max_inacessibilidade_micro], ignore_index=True)

            df_router_filtrado_2, roteiro = gerar_horarios_apresentacao(df_router_filtrado_2, roteiro, max_hoteis_roteirizacao)

        elif servico_roteiro=='OUT (PORTO DE GALINHAS)':

            max_hoteis_roteirizacao = st.session_state.max_hoteis_pga

            df_router_filtrado_2 = inserir_coluna_horario_ultimo_hotel(df_router_filtrado_2)

            roteiro = 0

            df_router_filtrado_2['Horario Voo'] = pd.to_datetime(df_router_filtrado_2['Horario Voo'], format='%H:%M:%S').dt.time

            lista_colunas = ['index']

            df_hoteis_pax_max = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

            df_router_filtrado_2, df_hoteis_pax_max, roteiro = \
                roteirizar_hoteis_mais_pax_max(df_router_filtrado_2, roteiro, df_hoteis_pax_max)
            
            df_hoteis_pax_max_inacessibilidade_utilitario = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

            df_hoteis_pax_max_inacessibilidade_van = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

            df_hoteis_pax_max_inacessibilidade_micro = pd.DataFrame(columns=lista_colunas.extend(df_router_filtrado_2.columns.tolist()))

            df_router_filtrado_2, df_hoteis_pax_max_inacessibilidade_utilitario, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_filtrado_2, roteiro, df_hoteis_pax_max_inacessibilidade_utilitario, pax_max_utilitario, 'Van')
            
            df_router_filtrado_2, df_hoteis_pax_max_inacessibilidade_van, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_filtrado_2, roteiro, df_hoteis_pax_max_inacessibilidade_van, pax_max_van, 'Micro')
            
            df_router_filtrado_2, df_hoteis_pax_max_inacessibilidade_micro, roteiro = \
                roteirizar_hoteis_mais_pax_max_inacessibilidade(df_router_filtrado_2, roteiro, df_hoteis_pax_max_inacessibilidade_micro, pax_max_micro, 'Bus')
            
            df_hoteis_pax_max = pd.concat([df_hoteis_pax_max, df_hoteis_pax_max_inacessibilidade_utilitario, df_hoteis_pax_max_inacessibilidade_van, 
                                           df_hoteis_pax_max_inacessibilidade_micro], ignore_index=True)

            df_router_filtrado_2, roteiro = gerar_horarios_apresentacao(df_router_filtrado_2, roteiro, max_hoteis_roteirizacao)

    else:

        inserir_hoteis_faltantes(itens_faltantes, nome_aba_excel, nome_regiao, '1az0u1yGWqIXE9KcUro6VznsVj7d5fozhH3dDsT1eI6A')

        st.stop()

    df_router_filtrado_2 = recalcular_horarios_menor_horario(df_router_filtrado_2)

    # Identificando serviços das rotas primárias que vão precisar de apoios

    # df_router_filtrado_2 = identificar_apoios_em_df(df_router_filtrado_2, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis_roteirizacao)

    # Gerando rotas de apoios de rotas primárias

    # df_router_filtrado_2 = gerar_roteiros_apoio(df_router_filtrado_2)

    # Gerando roteiros alternativos

    df_roteiros_alternativos = gerar_roteiros_alternativos(df_router_filtrado_2)

    df_roteiros_alternativos = recalcular_horarios_menor_horario(df_roteiros_alternativos)

    # Gerando roteiros alternativos 2

    max_hoteis_2 = 5

    intervalo_pu_hotel_2 = pd.Timedelta(hours=0, minutes=50, seconds=0)

    df_roteiros_alternativos_2 = gerar_roteiros_alternativos_2(df_router_filtrado_2, max_hoteis_2, intervalo_pu_hotel_2)

    df_roteiros_alternativos_2 = recalcular_horarios_menor_horario(df_roteiros_alternativos_2)

    st.session_state.max_hoteis_roteirizacao = max_hoteis_roteirizacao

    df_roteiros_alternativos_3 = gerar_roteiros_alternativos_3(df_router_filtrado_2)

    df_roteiros_alternativos_3 = recalcular_horarios_menor_horario(df_roteiros_alternativos_3)

    df_roteiros_alternativos_4 = gerar_roteiros_alternativos_4(df_router_filtrado_2, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis_2)

    df_roteiros_alternativos_4 = recalcular_horarios_menor_horario(df_roteiros_alternativos_4)
    
    # Identificando serviços das rotas alternativas que vão precisar de apoios

    # df_roteiros_alternativos = identificar_apoios_em_df(df_roteiros_alternativos, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis_roteirizacao)

    # Gerando rotas de apoios de rotas alternativas

    # df_roteiros_alternativos = gerar_roteiros_apoio(df_roteiros_alternativos)

    # Identificando serviços das rotas alternativas 2 que vão precisar de apoios

    # df_roteiros_alternativos_2 = identificar_apoios_em_df(df_roteiros_alternativos_2, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis_roteirizacao)

    # Gerando rotas de apoios de rotas alternativas 2

    # df_roteiros_alternativos_2 = gerar_roteiros_apoio(df_roteiros_alternativos_2)

    # Identificando serviços das rotas alternativas 3 que vão precisar de apoios

    # df_roteiros_alternativos_3 = identificar_apoios_em_df(df_roteiros_alternativos_3, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis_roteirizacao)

    # Gerando rotas de apoios de rotas alternativas 3

    # df_roteiros_alternativos_3 = gerar_roteiros_apoio(df_roteiros_alternativos_3)

    # df_roteiros_alternativos_4 = identificar_apoios_em_df(df_roteiros_alternativos_4, pax_max_utilitario, pax_max_van, pax_max_micro, max_hoteis_roteirizacao)

    # df_roteiros_alternativos_4 = gerar_roteiros_apoio(df_roteiros_alternativos_4)

    df_router_filtrado_2 = roteirizar_sem_maraca_serrambi(df_router_filtrado_2)

    df_roteiros_alternativos = roteirizar_sem_maraca_serrambi(df_roteiros_alternativos)

    df_roteiros_alternativos_2 = roteirizar_sem_maraca_serrambi(df_roteiros_alternativos_2)

    df_roteiros_alternativos_3 = roteirizar_sem_maraca_serrambi(df_roteiros_alternativos_3)

    df_roteiros_alternativos_4 = roteirizar_sem_maraca_serrambi(df_roteiros_alternativos_4)

    df_roteiros_alternativos = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos)

    df_roteiros_alternativos_2 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_2)

    df_roteiros_alternativos_2 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_2)

    df_roteiros_alternativos_3 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_3)

    df_roteiros_alternativos_3 = verificar_rotas_identicas(df_roteiros_alternativos_2, df_roteiros_alternativos_3)

    df_roteiros_alternativos_3 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_3)

    df_roteiros_alternativos_4 = verificar_rotas_identicas(df_router_filtrado_2, df_roteiros_alternativos_4)

    df_roteiros_alternativos_4 = verificar_rotas_identicas(df_roteiros_alternativos_3, df_roteiros_alternativos_4)

    df_roteiros_alternativos_4 = verificar_rotas_identicas(df_roteiros_alternativos_2, df_roteiros_alternativos_4)

    df_roteiros_alternativos_4 = verificar_rotas_identicas(df_roteiros_alternativos, df_roteiros_alternativos_4)

    st.divider()

    row_warning = st.columns(1)

    row3 = st.columns(3)

    coluna = 0
    
    hora_execucao = datetime.now()
    
    hora_execucao_menos_3h = hora_execucao - timedelta(hours=3)

    hora_execucao = hora_execucao_menos_3h.strftime("%d-%m-%Y %Hh%Mm")

    st.session_state.nome_html = f"{hora_execucao} {nome_html_ref}.html"

    st.session_state.data_roteiro_ref = data_roteiro.strftime("%d/%m/%Y")

    st.session_state.df_hoteis_pax_max = df_hoteis_pax_max

    st.session_state.df_router_filtrado_2 = df_router_filtrado_2

    st.session_state.df_roteiros_alternativos = df_roteiros_alternativos

    st.session_state.df_roteiros_alternativos_2 = df_roteiros_alternativos_2

    st.session_state.df_roteiros_alternativos_3 = df_roteiros_alternativos_3

    st.session_state.df_roteiros_alternativos_4 = df_roteiros_alternativos_4

    verificar_rotas_alternativas_ou_plotar_roteiros_sem_apoio(df_roteiros_alternativos, row_warning, row3, coluna, df_hoteis_pax_max, df_router_filtrado_2, st.session_state.df_juncao_voos, 
                                                              st.session_state.nome_html)

# Gerar roteiros finais

if 'nome_html' in st.session_state and (len(st.session_state.df_roteiros_alternativos)>0 or len(st.session_state.df_roteiros_alternativos_2)>0 or len(st.session_state.df_roteiros_alternativos_3)>0 or \
        len(st.session_state.df_roteiros_alternativos_4)>0):

    st.divider()

    row_rotas_alternativas = st.columns(1)

    row3 = st.columns(3)

    coluna = 0

    lista_rotas_alternativas = st.session_state.df_roteiros_alternativos['Roteiro'].unique().tolist()

    lista_rotas_alternativas_2 = st.session_state.df_roteiros_alternativos_2['Roteiro'].unique().tolist()

    lista_rotas_alternativas_3 = st.session_state.df_roteiros_alternativos_3['Roteiro'].unique().tolist()

    lista_rotas_alternativas_4 = st.session_state.df_roteiros_alternativos_4['Roteiro'].unique().tolist()

    if len(st.session_state.df_router_filtrado_2)>0:

        with row_rotas_alternativas[0]:

            st.markdown('*Rotas Alternativas 1 são rotas que buscam equilibrar a quantidade de hoteis em cada carro.*')

            rotas_alternativas = st.multiselect('Selecione as Rotas Alternativas 1 que serão usadas', lista_rotas_alternativas)

            st.markdown('*Rotas Alternativas 2 são rotas que tentam colocar apenas um carro para o roteiro, desde que o número de hoteis da rota não passe de 5 e o intervalo entre o primeiro e último hotel seja menor que 50 minutos.*')

            rotas_alternativas_2 = st.multiselect('Selecione as Rotas Alternativas 2 que serão usadas', lista_rotas_alternativas_2)

            st.markdown('*Rotas Alternativas 3 são rotas que evitam que dois carros de um roteiro estejam buscando um mesmo bairro/micro região.*')

            rotas_alternativas_3 = st.multiselect('Selecione as Rotas Alternativas 3 que serão usadas', lista_rotas_alternativas_3)

            st.markdown('*Rotas Alternativas 4 são rotas que tentam colocar menos carros, lotando os carros ao máximo e importando-se apenas com a quantidade máxima de 5 hoteis.*')

            rotas_alternativas_4 = st.multiselect('Selecione as Rotas Alternativas 4 que serão usadas', lista_rotas_alternativas_4)
        
            gerar_roteiro_final = st.button('Gerar Roteiro Final')

        if not gerar_roteiro_final:

            coluna = plotar_roteiros_gerais_alternativos_sem_apoio(st.session_state.df_router_filtrado_2, st.session_state.df_roteiros_alternativos, st.session_state.df_roteiros_alternativos_2, 
                                                                   st.session_state.df_roteiros_alternativos_3, st.session_state.df_roteiros_alternativos_4, coluna)
            
        else:

            if (set(rotas_alternativas) & set(rotas_alternativas_2)) or \
            (set(rotas_alternativas) & set(rotas_alternativas_3)) or \
            (set(rotas_alternativas) & set(rotas_alternativas_4)) or \
            (set(rotas_alternativas_2) & set(rotas_alternativas_3)) or \
            (set(rotas_alternativas_2) & set(rotas_alternativas_4))or \
            (set(rotas_alternativas_3) & set(rotas_alternativas_4)):

                st.error('Só pode selecionar uma opção alternativa p/ cada roteiro')

            else:

                if 'df_servico_voos_horarios' in st.session_state:
                    
                    st.session_state['df_servico_voos_horarios'] = pd.DataFrame(columns=['Servico', 'Voo', 'Horario Voo'])

                df_hoteis_pax_max = st.session_state.df_hoteis_pax_max

                df_router_filtrado_2 = st.session_state.df_router_filtrado_2

                if len(rotas_alternativas)>0:

                    df_roteiros_alternativos = st.session_state.df_roteiros_alternativos[st.session_state.df_roteiros_alternativos['Roteiro'].isin(rotas_alternativas)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas)].reset_index(drop=True)
                    
                else:

                    df_roteiros_alternativos = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos.columns.tolist())

                if len(rotas_alternativas_2)>0:

                    df_roteiros_alternativos_2 = st.session_state.df_roteiros_alternativos_2[st.session_state.df_roteiros_alternativos_2['Roteiro'].isin(rotas_alternativas_2)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_2)].reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_2], ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_2 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_2.columns.tolist())

                if len(rotas_alternativas_3)>0:

                    df_roteiros_alternativos_3 = st.session_state.df_roteiros_alternativos_3[st.session_state.df_roteiros_alternativos_3['Roteiro'].isin(rotas_alternativas_3)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_3)].reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_3], ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_3 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_3.columns.tolist())

                if len(rotas_alternativas_4)>0:

                    df_roteiros_alternativos_4 = st.session_state.df_roteiros_alternativos_4[st.session_state.df_roteiros_alternativos_4['Roteiro'].isin(rotas_alternativas_4)].reset_index(drop=True)
                    
                    df_router_filtrado_2 = df_router_filtrado_2[~df_router_filtrado_2['Roteiro'].isin(rotas_alternativas_4)].reset_index(drop=True)
                    
                    df_roteiros_alternativos = pd.concat([df_roteiros_alternativos, df_roteiros_alternativos_4], ignore_index=True)
                    
                else:

                    df_roteiros_alternativos_4 = pd.DataFrame(columns=st.session_state.df_roteiros_alternativos_4.columns.tolist())

                lista_dfs = [df_hoteis_pax_max, df_router_filtrado_2, df_roteiros_alternativos]

                n_carros = 0

                for df in lista_dfs:
                    
                    if len(df)>0:

                        n_carros += len(df[['Roteiro', 'Carros']].drop_duplicates())

                with row_rotas_alternativas[0]:

                    st.header(f'A roteirização usou um total de {n_carros} carros')

                if len(df_hoteis_pax_max)>0:

                    coluna = plotar_roteiros_simples(df_hoteis_pax_max, row3, coluna)

                coluna = plotar_roteiros_gerais_final_sem_apoio(df_router_filtrado_2, df_roteiros_alternativos, coluna)
                
                html = definir_html(st.session_state.df_juncao_voos)

                criar_output_html(st.session_state.nome_html, html)

                df_pdf = pd.concat([df_router_filtrado_2, df_hoteis_pax_max, df_roteiros_alternativos], ignore_index=True)

                st.session_state.df_insercao = df_pdf[['Id_Reserva', 'Id_Servico', 'Data Horario Apresentacao', 'Data Horario Apresentacao Original']].reset_index(drop=True)

                df_pdf_2 = df_pdf[['Reserva', 'Data Horario Apresentacao']].sort_values(by='Reserva').reset_index(drop=True)
                
                for index in range(len(df_pdf)):

                    tipo_de_servico_ref = df_pdf.at[index, 'Modo do Servico']

                    juncao_ref_2 = df_pdf.at[index, 'Junção']

                    if tipo_de_servico_ref == 'REGULAR' and not pd.isna(juncao_ref_2):

                        df_pdf.at[index, 'Horario Voo / Menor Horário'] = df_pdf.at[index, 'Menor Horário']

                    elif (tipo_de_servico_ref == 'REGULAR' and pd.isna(juncao_ref_2)) or (tipo_de_servico_ref != 'REGULAR'):

                        df_pdf.at[index, 'Horario Voo / Menor Horário'] = df_pdf.at[index, 'Horario Voo']

                df_pdf = df_pdf.sort_values(by=['Horario Voo / Menor Horário', 'Junção']).reset_index(drop=True)

                inserir_roteiros_html_sem_apoio(st.session_state.nome_html, df_pdf)

                inserir_html_2(st.session_state.nome_html, df_pdf_2)

                with open(st.session_state.nome_html, "r", encoding="utf-8") as file:

                    html_content = file.read()

                salvar_rotas_historico(df_pdf)

                st.download_button(
                    label="Baixar Arquivo HTML",
                    data=html_content,
                    file_name=st.session_state.nome_html,
                    mime="text/html"
                )

if 'df_insercao' in st.session_state and len(st.session_state.df_insercao)>0:

    lancar_horarios = st.button('Lançar Horários')

    if lancar_horarios and len(st.session_state.df_insercao)>0:

        df_insercao = atualizar_banco_dados(st.session_state.df_insercao, 'test_phoenix_recife')

        st.rerun()

if data_roteiro:

    enviar_informes_porto = st.button(f'Enviar Informativos de Saída | PORTO e SERRAMBI | {data_roteiro.strftime("%d/%m/%Y")}')

    enviar_informes_demais_destinos = st.button(f'Enviar Informativos de Saída | DEMAIS DESTINOS | {data_roteiro.strftime("%d/%m/%Y")}')

    if enviar_informes_porto:

        puxar_historico('1az0u1yGWqIXE9KcUro6VznsVj7d5fozhH3dDsT1eI6A', ['Histórico Roteiros'], ['df_historico_roteiros'])

        st.session_state.df_historico_roteiros['Data Execucao'] = pd.to_datetime(st.session_state.df_historico_roteiros['Data Execucao']).dt.date

        st.session_state.df_historico_roteiros['Id_Servico'] = pd.to_numeric(st.session_state.df_historico_roteiros['Id_Servico'])

        df_ref_thiago = st.session_state.df_historico_roteiros[(st.session_state.df_historico_roteiros['Data Execucao']==data_roteiro) & 
                                                               (st.session_state.df_historico_roteiros['Servico'].isin(['OUT (PORTO DE GALINHAS)', 'OUT (SERRAMBI)']))].reset_index(drop=True)

        df_verificacao = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & (st.session_state.df_router['Servico'].isin(['OUT (PORTO DE GALINHAS)', 'OUT (SERRAMBI)']))].reset_index(drop=True)

        reservas_nao_roteirizadas = df_verificacao.loc[~df_verificacao['Id_Servico'].isin(df_ref_thiago['Id_Servico']), 'Reserva'].unique()

        if len(reservas_nao_roteirizadas)>0:

            nome_reservas = ', '.join(reservas_nao_roteirizadas)

            st.warning(f'As reservas {nome_reservas} não foram roteirizadas e, portanto, não foi enviado informativos de saída para elas')
    
        if len(df_ref_thiago)>0:
    
            lista_ids_servicos = df_ref_thiago['Id_Servico'].tolist()

            webhook_thiago = "https://conexao.multiatend.com.br/webhook/luckenvioinformativoporto"
            
            data_roteiro_str = data_roteiro.strftime('%Y-%m-%d')
            
            payload = {"data": data_roteiro_str, 
                       "ids_servicos": lista_ids_servicos, 
                       "tag_servico": 'Porto e Serrambi'}
            
            response = requests.post(webhook_thiago, json=payload)
            
            if response.status_code == 200:
                
                    st.success(f"Informativos Enviados com Sucesso!")
                
            else:
                
                st.error(f"Erro. Favor contactar o suporte")

                st.error(f"{response}")
        else:

            st.error(f'Não existem roteiros feitos para a data e serviços selecionados')

    elif enviar_informes_demais_destinos:

        puxar_historico('1az0u1yGWqIXE9KcUro6VznsVj7d5fozhH3dDsT1eI6A', ['Histórico Roteiros'], ['df_historico_roteiros'])

        st.session_state.df_historico_roteiros['Data Execucao'] = pd.to_datetime(st.session_state.df_historico_roteiros['Data Execucao']).dt.date

        st.session_state.df_historico_roteiros['Id_Servico'] = pd.to_numeric(st.session_state.df_historico_roteiros['Id_Servico'])

        df_ref_thiago = st.session_state.df_historico_roteiros[(st.session_state.df_historico_roteiros['Data Execucao']==data_roteiro) & 
                                                               ~(st.session_state.df_historico_roteiros['Servico'].isin(['OUT (PORTO DE GALINHAS)', 'OUT (SERRAMBI)']))].reset_index(drop=True)

        df_verificacao = st.session_state.df_router[(st.session_state.df_router['Data Execucao']==data_roteiro) & ~(st.session_state.df_router['Servico'].isin(['OUT (PORTO DE GALINHAS)', 'OUT (SERRAMBI)'])) & 
                                                    (st.session_state.df_router['Tipo de Servico']=='OUT')].reset_index(drop=True)

        reservas_nao_roteirizadas = df_verificacao.loc[~df_verificacao['Id_Servico'].isin(df_ref_thiago['Id_Servico']), 'Reserva'].unique()

        if len(reservas_nao_roteirizadas)>0:

            nome_reservas = ', '.join(reservas_nao_roteirizadas)

            st.warning(f'As reservas {nome_reservas} não foram roteirizadas e, portanto, não foi enviado informativos de saída para elas')
    
        if len(df_ref_thiago)>0:
    
            lista_ids_servicos = df_ref_thiago['Id_Servico'].tolist()

            webhook_thiago = "https://conexao.multiatend.com.br/webhook/luckenvioinformativoporto"
            
            data_roteiro_str = data_roteiro.strftime('%Y-%m-%d')
            
            payload = {"data": data_roteiro_str, 
                       "ids_servicos": lista_ids_servicos, 
                       "tag_servico": 'Demais Destinos'}
            
            response = requests.post(webhook_thiago, json=payload)
            
            if response.status_code == 200:
                
                    st.success(f"Informativos Enviados com Sucesso!")
                
            else:
                
                st.error(f"Erro. Favor contactar o suporte")

                st.error(f"{response}")
        else:

            st.error(f'Não existem roteiros feitos para a data e serviços selecionados')
