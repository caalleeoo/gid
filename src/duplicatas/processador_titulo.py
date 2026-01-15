import pandas as pd
import os
import glob
import sys

# --- Configurações e Constantes ---
PREFIXO_SAIDA = 'relatorio_duplicatas'

def buscar_arquivo_csv():
    """
    Examina o diretório atual em busca de arquivos CSV.
    Ignora arquivos que contenham o PREFIXO_SAIDA para evitar
    processar o próprio relatório gerado anteriormente.
    """
    # Lista todos os csv na pasta
    arquivos = glob.glob("*.csv")
    
    # Filtra para excluir os arquivos de saída (se existirem)
    candidatos = [f for f in arquivos if PREFIXO_SAIDA not in f]
    
    if not candidatos:
        return None
    
    # Retorna o primeiro encontrado. 
    # Em um cenário mais complexo, poderíamos pedir para o usuário escolher,
    # mas para automação direta, o primeiro é a escolha lógica.
    return candidatos[0]

def normalizar_texto(texto):
    """
    Normaliza o texto para garantir comparações justas:
    - Converte para minúsculas
    - Remove espaços no início e fim
    """
    if isinstance(texto, str):
        return texto.strip().lower()
    return str(texto)

def gerar_relatorio_txt(df, nome_arquivo):
    """
    Gera um relatório TXT estruturado para leitura humana.
    """
    try:
        with open(nome_arquivo, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO DE DUPLICIDADES ENCONTRADAS\n")
            f.write("=====================================\n")
            f.write(f"Total de registros duplicados listados: {len(df)}\n\n")
            
            # Agrupa por título normalizado para exibir em blocos
            grupos = df.groupby('titulo_normalizado')
            
            contador = 0
            for _, grupo in grupos:
                contador += 1
                # Pega o título da primeira ocorrência para exibição
                titulo_display = grupo.iloc[0]['Titulo']
                
                f.write(f"#{contador} TÍTULO: {titulo_display}\n")
                f.write("-" * 80 + "\n")
                
                for _, row in grupo.iterrows():
                    data = row['Data'] if pd.notna(row['Data']) else "S/ Data"
                    link = row['Link'] if pd.notna(row['Link']) else "S/ Link"
                    f.write(f"   DATA: {data:<12} | LINK: {link}\n")
                
                f.write("\n")
        return True
    except Exception as e:
        print(f"Erro ao gerar TXT: {e}")
        return False

def main():
    print("--- Iniciando Processador de Duplicatas (Modo Dinâmico) ---\n")

    # 1. Detecção Automática do Arquivo
    arquivo_entrada = buscar_arquivo_csv()
    
    if not arquivo_entrada:
        print("ERRO: Nenhum arquivo .csv encontrado nesta pasta.")
        print("Certifique-se de que o script está na mesma pasta do arquivo de dados.")
        input("Pressione Enter para sair...")
        sys.exit()
        
    print(f"-> Arquivo detectado: '{arquivo_entrada}'")
    print("-> Lendo dados...")

    # 2. Carregamento Inteligente
    try:
        # Tenta ler com UTF-8, se falhar, tenta Latin-1 (comum em Excel antigo)
        try:
            df = pd.read_csv(arquivo_entrada, encoding='utf-8')
        except UnicodeDecodeError:
            print("   Aviso: Codificação UTF-8 falhou. Tentando Latin-1...")
            df = pd.read_csv(arquivo_entrada, encoding='latin-1')
            
    except Exception as e:
        print(f"ERRO CRÍTICO ao ler o arquivo: {e}")
        sys.exit()

    # Validação de Estrutura Mínima (precisamos de pelo menos 3 colunas)
    if len(df.columns) < 3:
        print(f"ERRO: O arquivo possui apenas {len(df.columns)} colunas. São necessárias pelo menos 3 (Título, Link, Data).")
        sys.exit()

    # 3. Normalização de Colunas (Assumindo Posição: 1=Titulo, 2=Link, 3=Data)
    # Renomeamos baseando-nos nos índices para garantir consistência independente dos nomes originais
    mapa_colunas = {
        df.columns[0]: 'Titulo',
        df.columns[1]: 'Link',
        df.columns[2]: 'Data'
    }
    df.rename(columns=mapa_colunas, inplace=True)

    # 4. Processamento (A Busca pela Perfeição)
    print("-> Processando duplicatas...")
    
    # Cria impressão digital do título
    df['titulo_normalizado'] = df['Titulo'].apply(normalizar_texto)
    
    # Encontra duplicatas (mantendo todas as ocorrências para comparação)
    duplicatas = df[df.duplicated(subset=['titulo_normalizado'], keep=False)].copy()
    
    if duplicatas.empty:
        print("\nRESULTADO: Nenhuma duplicata encontrada. Seu catálogo está limpo!")
        sys.exit()

    # Ordena para agrupar visualmente
    duplicatas.sort_values(by=['titulo_normalizado', 'Data'], inplace=True)
    
    print(f"-> Encontrados {len(duplicatas)} registros com títulos duplicados.")

    # 5. Exportação dos Artefatos
    print("\nGerando arquivos de saída...")
    
    # Preparando DataFrame final (removendo coluna auxiliar interna)
    df_final = duplicatas.drop(columns=['titulo_normalizado'])
    
    # Nomes dos arquivos
    nome_csv = f"{PREFIXO_SAIDA}.csv"
    nome_json = f"{PREFIXO_SAIDA}.json"
    nome_txt = f"{PREFIXO_SAIDA}.txt"
    
    # CSV
    df_final.to_csv(nome_csv, index=False, encoding='utf-8-sig') # utf-8-sig para compatibilidade Excel
    print(f"   [OK] {nome_csv}")
    
    # JSON
    df_final.to_json(nome_json, orient='records', force_ascii=False, indent=4)
    print(f"   [OK] {nome_json}")
    
    # TXT
    if gerar_relatorio_txt(duplicatas, nome_txt):
        print(f"   [OK] {nome_txt}")

    print("\n--- Concluído com sucesso ---")
    print("Verifique a pasta do script para encontrar os arquivos gerados.")

if __name__ == "__main__":
    main()