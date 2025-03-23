import streamlit as st
import pandas as pd
import io
import zipfile

def dividir_dataframe(df, molde, linhas_por_df=300):
    dfs = []
    for i in range(0, len(df), linhas_por_df):
        df_temp = df.iloc[i:i + linhas_por_df].copy()
        # Add template at beginning and end
        df_temp = pd.concat([molde, df_temp, molde], ignore_index=True)
        
        # Format monetary values
        for coluna in ['valor_liberado', 'valor_parcela']:
            df_temp[coluna] = df_temp[coluna].astype(str)
            df_temp[coluna] = df_temp[coluna].apply(lambda x: 'R$ ' + x if not x.startswith('R$ ') else x)
        
        dfs.append(df_temp)
    return dfs

# Definição do DataFrame molde
molde = {
    'id': [557197162307],
    'name': ['Nigro'],
    'cpf': [1234567],
    'phone': [557197162307],
    'valor_liberado': ['R$ 50000000'],
    'campanha': ['tag_camp'],
    'valor_parcela': ['R$ 50000'],
    'prazo': [360],
    'banco_destino': ['Gringotts']
}
df_molde = pd.DataFrame(molde)

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
        valor_parcela_selecionado = 'valor_parcela_beneficio'
        prazo_selecionado = 'prazo_beneficio'
        banco_selecionado = 'banco_beneficio'
    elif campanha == 'Cartão':
        campanha_selecionada = campanha
        valor_liberado_selecionado = 'valor_liberado_cartao'
        valor_parcela_selecionado = 'valor_parcela_cartao'
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
        'banco_destino': banco_selecionado
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
            
            # Filtragem dos dados
            import_hyper_ativacao = import_hyper_renomeado[import_hyper_renomeado['campanha'].str.endswith('_csativacao')]
            import_hyper_carteira = import_hyper_renomeado[import_hyper_renomeado['campanha'].str.endswith('csapp')]
            
            # Mostrar informações
            st.write(f"Total de registros: {len(import_hyper_renomeado)}")
            st.write(f"Registros de ativação: {len(import_hyper_ativacao)}")
            st.write(f"Registros de carteira: {len(import_hyper_carteira)}")
            
            # Dividir e criar arquivos
            dfs_ativacao = []
            dfs_carteira = []
            
            # Divisão dos DataFrames
            if len(import_hyper_ativacao) > 0:
                dfs_ativacao = dividir_dataframe(import_hyper_ativacao, df_molde)
                st.write(f"Arquivos de Ativação: {len(dfs_ativacao)} arquivos")
            
            if len(import_hyper_carteira) > 0:
                dfs_carteira = dividir_dataframe(import_hyper_carteira, df_molde)
                st.write(f"Arquivos de Carteira: {len(dfs_carteira)} arquivos")
            
            # Criar ZIP se tiver arquivos para processar
            if dfs_ativacao or dfs_carteira:
                # Criar um buffer de memória para o arquivo zip
                zip_buffer = io.BytesIO()
                
                # Criar o arquivo zip
                with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zf:
                    # Processar arquivos de ativação
                    for i, df in enumerate(dfs_ativacao):
                        if len(df) > 1:  # Verificar se há dados reais (além do molde)
                            # Usar o valor do primeiro registro real (índice 1, já que 0 é o molde)
                            campanha_valor = df['campanha'].iloc[1] if len(df) > 1 else "ativacao"
                            nome_arquivo = f"import_hyper_{campanha_valor}_{i + 1}.csv"
                            csv_data = df.to_csv(index=False)
                            zf.writestr(nome_arquivo, csv_data)
                    
                    # Processar arquivos de carteira
                    for i, df in enumerate(dfs_carteira):
                        if len(df) > 1:  # Verificar se há dados reais (além do molde)
                            # Usar o valor do primeiro registro real (índice 1, já que 0 é o molde)
                            campanha_valor = df['campanha'].iloc[1] if len(df) > 1 else "carteira"
                            nome_arquivo = f"import_hyper_{campanha_valor}_{i + 1}.csv"
                            csv_data = df.to_csv(index=False)
                            zf.writestr(nome_arquivo, csv_data)
                
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