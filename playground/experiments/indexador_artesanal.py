import pandas as pd
from rapidfuzz import process, fuzz
from unidecode import unidecode
import time
import sys
import os
from datetime import datetime

class IndexadorArtesanal:
    def __init__(self, caminho_arquivo, output_dir, threshold=85): # Aumentei levemente o threshold padrão
        self.caminho_arquivo = caminho_arquivo
        self.output_dir = output_dir
        self.threshold = threshold
        self.df_reduzido = None
        self.relatorio = []
        self.inicio = time.time()

    def normalizar(self, texto):
        """
        Normalização leve: apenas minúsculas e strip.
        NÃO removemos acentos aqui para a visualização final, 
        mas usaremos unidecode na comparação interna se necessário.
        """
        if not isinstance(texto, str):
            return str(texto)
        return texto.lower().strip()

    def carregar_e_agrupar(self):
        print(f"📂 [Fase 1] Carregamento Inteligente: {os.path.basename(self.caminho_arquivo)}")
        try:
            df_bruto = pd.read_csv(
                self.caminho_arquivo, 
                header=None, 
                sep=None, 
                engine='python',
                names=['Termo_Original', 'Frequencia_Raw'],
                dtype={0: str}
            )
            
            # Limpeza básica
            df_bruto['Frequencia'] = pd.to_numeric(df_bruto['Frequencia_Raw'], errors='coerce').fillna(0)
            df_bruto['Termo_Original'] = df_bruto['Termo_Original'].fillna('')
            
            # Criamos uma chave normalizada para agrupar idênticos exatos primeiro (ex: "Casa " e "casa")
            df_bruto['Chave_Busca'] = df_bruto['Termo_Original'].apply(self.normalizar)

            # Agrupamento inicial (Otimização)
            self.df_reduzido = df_bruto.groupby('Chave_Busca').agg({
                'Termo_Original': 'first', # Mantém a grafia original visualmente
                'Frequencia': 'sum'
            }).reset_index()
            
            # Ordena por frequência (termos mais comuns costumam ser os "corretos")
            self.df_reduzido = self.df_reduzido.sort_values(by='Frequencia', ascending=False)

            print(f"   ↳ Termos únicos para análise: {len(self.df_reduzido)}")
            print("-" * 50)

        except Exception as e:
            print(f"❌ Erro crítico ao ler arquivo: {e}")
            sys.exit(1)

    def analisar_profundidade(self):
        print("🧠 [Fase 2] Análise Estrita (Grafia e Plurais)")
# --- 1. CLÁUSULA DE GUARDA (Segurança) ---
        # Se a madeira não estiver na bancada, não começamos a trabalhar.
        if self.df_reduzido is None or self.df_reduzido.empty:
            print("⚠️ Aviso: 'df_reduzido' está vazio ou não foi carregado. Operação cancelada.")
            return

        # --- 2. O CÓDIGO ORIGINAL (Agora Seguro) ---
        print("   ↳ Usando algoritmo 'Ratio' (considera o termo como um todo)")
        
        # Lista de termos para processar
        termos_processar = self.df_reduzido['Chave_Busca'].tolist()
        
        # Mapas para recuperação rápida de dados originais
        mapa_original = pd.Series(
            self.df_reduzido.Termo_Original.values, 
            index=self.df_reduzido.Chave_Busca
        ).to_dict()
        
        mapa_frequencia = pd.Series(
            self.df_reduzido.Frequencia.values, 
            index=self.df_reduzido.Chave_Busca
        ).to_dict()
                
        ja_agrupados = set()
        total = len(termos_processar)
        
        # Vamos iterar. Como a lista está ordenada por frequência, 
        # assumimos que o primeiro que aparece é o "pai" (o termo correto/mais comum).
        for i, termo_pai in enumerate(termos_processar):
            
            if i % 100 == 0:
                percentual = (i / total) * 100
                sys.stdout.write(f"\r   ⏳ Progresso: {percentual:.1f}% ({i}/{total})")
                sys.stdout.flush()

            if termo_pai in ja_agrupados:
                continue
            
            # --- MUDANÇA CRUCIAL AQUI ---
            # fuzz.ratio: Compara a string inteira. 
            # "Banana" vs "Bananas" = Alto
            # "Banana" vs "Banana Prata" = Baixo (diferença de tamanho penaliza)
            matches = process.extract(
                termo_pai, 
                termos_processar, 
                scorer=fuzz.ratio,  # <--- O SEGREDO ESTÁ AQUI
                score_cutoff=self.threshold,
                limit=50
            )

            variacoes_encontradas = []
            freq_acumulada = 0
            
            # O primeiro match é sempre ele mesmo (score 100), então verificamos se há outros
            if len(matches) > 1:
                
                for match in matches:
                    termo_filho = match[0]
                    score = match[1]
                    
                    # Ignora se já foi agrupado antes (a menos que seja o próprio pai desta rodada)
                    if termo_filho in ja_agrupados and termo_filho != termo_pai:
                        continue
                        
                    nome_display = mapa_original.get(termo_filho, termo_filho)
                    freq = mapa_frequencia.get(termo_filho, 0)
                    
                    # Formata a saída para você ver claramente a diferença
                    if termo_filho == termo_pai:
                        # O termo principal
                        freq_acumulada += freq
                        ja_agrupados.add(termo_pai)
                    else:
                        # As variações (filhos)
                        variacoes_encontradas.append(f"{nome_display} [Score: {score:.0f}]")
                        freq_acumulada += freq
                        ja_agrupados.add(termo_filho)
                
                # Só adiciona ao relatório se encontrou FILHOS (variações reais)
                if variacoes_encontradas:
                    self.relatorio.append({
                        'Termo Sugerido (Mais Comum)': mapa_original[termo_pai],
                        'Variações Detectadas (Duplicatas)': " | ".join(variacoes_encontradas),
                        'Qtd Variações': len(variacoes_encontradas),
                        'Frequência Total': int(freq_acumulada)
                    })

        tempo = (time.time() - self.inicio) / 60
        print(f"\n\n✅ Análise concluída em {tempo:.2f} minutos.")
        print(f"📊 {len(self.relatorio)} grupos de correções encontrados.")

    def salvar(self):
        if not self.relatorio:
            print("✨ Nenhuma duplicata encontrada com esses parâmetros.")
            return

        df_final = pd.DataFrame(self.relatorio)
        # Ordena para mostrar os casos com mais variações primeiro (onde está a maior sujeira)
        df_final = df_final.sort_values(by='Qtd Variações', ascending=False)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        nome_arquivo = f"relatorio_correcao_fina_{timestamp}.csv"
        caminho_completo = os.path.join(self.output_dir, nome_arquivo)
        
        df_final.to_csv(caminho_completo, index=False, sep=';', encoding='utf-8-sig')
        print(f"💾 Relatório salvo em: {caminho_completo}")

if __name__ == "__main__":
    # --- CONFIGURAÇÃO ---
    dir_script = os.path.dirname(os.path.abspath(__file__))
    dir_raiz = os.path.abspath(os.path.join(dir_script, '..', '..'))
    
    # 1. Ajuste o nome do arquivo aqui
    NOME_ARQUIVO_ALVO = 'assuntos.csv' 
    
    # Busca automática
    caminho_input = os.path.join(dir_raiz, 'data', 'temp', NOME_ARQUIVO_ALVO)
    if not os.path.exists(caminho_input):
         caminho_input = os.path.join(dir_raiz, 'data', 'raw', NOME_ARQUIVO_ALVO)

    dir_output = os.path.join(dir_raiz, 'data', 'processed')
    os.makedirs(dir_output, exist_ok=True)
    
    # 2. Sensibilidade (Sugestão: 85 ou 88 para pegar apenas typos e plurais)
    # Se colocar 95 pega apenas typos muito óbvios.
    # Se colocar 70 começa a pegar coisas erradas.
    SENSIBILIDADE = 88 
    
    print("="*60)
    print(f"🔍 DETETIVE DE GRAFIA E PLURAIS - UnB")
    print("="*60)
    
    if os.path.exists(caminho_input):
        app = IndexadorArtesanal(caminho_input, dir_output, threshold=SENSIBILIDADE)
        app.carregar_e_agrupar()
        app.analisar_profundidade()
        app.salvar()
    else:
        print(f"❌ ARQUIVO NÃO ENCONTRADO: {NOME_ARQUIVO_ALVO}")