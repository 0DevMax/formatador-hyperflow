import streamlit as st
import pandas as pd
import io
import zipfile
import unicodedata
import openpyxl

linhas_por_df_ativacao = st.sidebar.number_input("Número de linhas por DataFrame (Ativação):", min_value=1, value=1000, step=1)
linhas_por_df_carteira = st.sidebar.number_input("Número de linhas por DataFrame (Carteira):", min_value=1, value=1000, step=1)
min_linhas_ultimo_df = st.sidebar.number_input("Número mínimo de linhas para o último DataFrame:", min_value=1, value=150, step=1)
linhas_por_df = st.sidebar.number_input("Número de linhas por DataFrame:", min_value=1, value=1000, step=1)

tipo_divisao = st.sidebar.radio("Tipo de Divisão:", ['Ativação/Carteira', 'Por Convênio', 'Outros'])

limites_zerados = [ 'govrj', 'govba']

def remover_acentos(x):
    if pd.isna(x):
        return x
    return unicodedata.normalize('NFKD', str(x)).encode('ascii', 'ignore').decode('utf-8')

def dividir_dataframe(df, linhas_por_df, min_linhas_ultimo_df=100):
    dfs = []
    for i in range(0, len(df), linhas_por_df):
        df_temp = df.iloc[i:i + linhas_por_df].copy()
        
        # Verifica se o último DataFrame tem menos linhas que o mínimo especificado
        if i + linhas_por_df >= len(df) and len(df_temp) < min_linhas_ultimo_df:
            if dfs:
                dfs[-1] = pd.concat([dfs[-1], df_temp], ignore_index=True)
            else:
                dfs.append(df_temp)
        else:
            dfs.append(df_temp)
        
        # Format monetary values
        for coluna in ['valor_liberado', 'valor_parcela']:
            df_temp[coluna] = df_temp[coluna].astype(str)
            df_temp[coluna] = df_temp[coluna].apply(lambda x: 'R$ ' + x if not x.startswith('R$ ') else x)
        
    return dfs

# Interface do Streamlit
st.title("Formatador para disparo Hyperflow")
st.sidebar.write("------")

campanha = st.sidebar.selectbox("Tipo da Campanha:", ['Novo', 'Benefício', 'Cartão'])

arquivo_principal = st.file_uploader("Escolha o arquivo", type=['csv'])

if arquivo_principal is not None:
    if campanha == 'Novo':
        campanha_selecionada = campanha
        valor_liberado_selecionado = 'valor_liberado_emprestimo'
        valor_parcela_selecionado = 'valor_parcela_emprestimo'
        prazo_selecionado = 'prazo_emprestimo'
        banco_selecionado = 'banco_emprestimo'
    elif campanha == 'Benefício':
        campanha_selecionada = campanha
        valor_liberado_selecionado = 'valor_liberado_beneficio'
        valor_parcela_selecionado = st.sidebar.selectbox("Selecione o valor da parcela:", ['limite_beneficio', 'valor_parcela_beneficio'])
        prazo_selecionado = 'prazo_beneficio'
        banco_selecionado = 'banco_beneficio'
    elif campanha == 'Cartão':
        campanha_selecionada = campanha
        valor_liberado_selecionado = 'valor_liberado_cartao'
        valor_parcela_selecionado = st.sidebar.selectbox("Selecione o valor da parcela:", ['limite_cartao', 'valor_parcela_cartao'])
        prazo_selecionado = 'prazo_cartao'
        banco_selecionado = 'banco_cartao'
    
    mapeamento_colunas = {        
        'id': 'FONE1',           
        'name': 'Nome_Cliente',  
        'cpf': 'CPF',           
        'phone': 'FONE1',       
        'valor_liberado': valor_liberado_selecionado,
        'campanha': 'Campanha',
        'valor_parcela': valor_parcela_selecionado,
        'prazo': prazo_selecionado,
        'banco_destino': banco_selecionado,
        'convenio': 'Convenio'
    }
    
    mapeamento_bancos = {
        2: 'MeuCash',
        243: 'Master',
        318: 'BMG',
        389: 'Mercantil',
        422: 'Safra',
        623: 'Pan',
        707: 'Daycoval',
        6613: 'VemCard'
    }
    
    try:
        # Processamento do arquivo
        import_hyper = pd.read_csv(arquivo_principal, encoding='latin1', sep=';')
        
        # Verificar se todas as colunas necessárias existem
        colunas_necessarias = list(mapeamento_colunas.values())
        missing_columns = [col for col in colunas_necessarias if col not in import_hyper.columns]
        
        if missing_columns:
            st.error(f"Colunas não encontradas no arquivo: {', '.join(missing_columns)}")
        else:
            # Criar um novo DataFrame com as colunas renomeadas
            import_hyper_renomeado = pd.DataFrame()
            for col_destino, col_origem in mapeamento_colunas.items():
                import_hyper_renomeado[col_destino] = import_hyper[col_origem]
            
            # Remover acentos do nome
            import_hyper_renomeado['name'] = import_hyper_renomeado['name'].apply(remover_acentos)
            
            # Aplicar mapeamento de banco_destino
            import_hyper_renomeado['banco_destino'] = import_hyper_renomeado['banco_destino'].apply(lambda x: mapeamento_bancos.get(x, x))
            
            zip_buffer = io.BytesIO()
            
            if tipo_divisao == 'Ativação/Carteira':
                # Filtragem dos dados
                import_hyper_ativacao = import_hyper_renomeado[import_hyper_renomeado['campanha'].str.endswith('_csativacao')]
                import_hyper_carteira = import_hyper_renomeado[import_hyper_renomeado['campanha'].str.endswith('csapp')]
                
                # Mostrar informações
                st.write(f"Total de leads: {len(import_hyper_renomeado)}")
                st.write(f"Leads Ativação: {len(import_hyper_ativacao)}")
                st.write(f"Leads Carteira: {len(import_hyper_carteira)}")
                
                # Dividir e criar arquivos
                dfs_ativacao = []
                dfs_carteira = []
                
                # Divisão dos DataFrames
                if len(import_hyper_ativacao) > 0:
                    dfs_ativacao = dividir_dataframe(import_hyper_ativacao, linhas_por_df_ativacao)
                    st.write(f"Arquivos de Ativação: {len(dfs_ativacao)} arquivos")
                
                if len(import_hyper_carteira) > 0:
                    dfs_carteira = dividir_dataframe(import_hyper_carteira, linhas_por_df_carteira)
                    st.write(f"Arquivos de Carteira: {len(dfs_carteira)} arquivos")
                
                # Criar ZIP se tiver arquivos para processar
                if dfs_ativacao or dfs_carteira:
                    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zf:
                        # Processar arquivos de ativação
                        for i, df in enumerate(dfs_ativacao):
                            if len(df) > 1:
                                campanha_valor = df['campanha'].iloc[1] if len(df) > 1 else "ativacao"
                                nome_arquivo = f"import_hyper_{campanha_valor}_{i + 1}.xlsx"
                                excel_buffer = io.BytesIO()
                                df.to_excel(excel_buffer, index=False)
                                excel_buffer.seek(0)
                                zf.writestr(nome_arquivo, excel_buffer.getvalue())
                        
                        # Processar arquivos de carteira
                        for i, df in enumerate(dfs_carteira):
                            if len(df) > 1:
                                campanha_valor = df['campanha'].iloc[1] if len(df) > 1 else "carteira"
                                nome_arquivo = f"import_hyper_{campanha_valor}_{i + 1}.xlsx"
                                excel_buffer = io.BytesIO()
                                df.to_excel(excel_buffer, index=False)
                                excel_buffer.seek(0)
                                zf.writestr(nome_arquivo.replace('.xlsx', '.xlsx'), excel_buffer.getvalue())
            elif tipo_divisao == 'Por Convênio':
                # Dividir por convênio
                convenios = import_hyper_renomeado['convenio'].unique()
                
                st.write("Quantidade de leads por convênio:")
                for convenio in convenios:
                    quantidade = len(import_hyper_renomeado[import_hyper_renomeado['convenio'] == convenio])
                    st.write(f"Convênio {convenio}: {quantidade} registros")
                
                with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zf:
                    for convenio in convenios:
                        df_convenio = import_hyper_renomeado[import_hyper_renomeado['convenio'] == convenio]
                        dfs_convenio = dividir_dataframe(df_convenio, linhas_por_df)
                        
                        st.write(f"Convênio {convenio}: {len(dfs_convenio)} arquivos")
                        
                        for i, df in enumerate(dfs_convenio):
                            if len(df) > 1:
                                nome_arquivo = f"import_hyper_convenio_{convenio}_{i + 1}.xlsx"
                                excel_buffer = io.BytesIO()
                                df.to_excel(excel_buffer, index=False)
                                excel_buffer.seek(0)
                                zf.writestr(nome_arquivo, excel_buffer.getvalue())
            else:
                # Divisão simples do DataFrame
                dfs = dividir_dataframe(import_hyper_renomeado, linhas_por_df)
                st.write(f"Total de arquivos: {len(dfs)}")
                
                # Criar ZIP com os arquivos
                with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zf:
                    for i, df in enumerate(dfs):
                        if len(df) > 1:
                            nome_arquivo = f"import_hyper_{i + 1}.xlsx"
                            excel_buffer = io.BytesIO()
                            df.to_excel(excel_buffer, index=False)
                            excel_buffer.seek(0)
                            zf.writestr(nome_arquivo.replace('.xlsx', '.xlsx'), excel_buffer.getvalue())
            
            # Oferecer o download do arquivo zip
            zip_buffer.seek(0)
            st.download_button(
                label="Baixar Todos os Arquivos (ZIP)",
                data=zip_buffer,
                file_name="todos_os_arquivos.zip",
                mime="application/zip"
            )

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {str(e)}")
        import traceback
        st.write("Detalhes do erro:")
        st.code(traceback.format_exc())
