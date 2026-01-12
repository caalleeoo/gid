import pandas as pd
from rapidfuzz import process, fuzz
from unidecode import unidecode
import time
import sys

class IndexadorArtesanal:
    def __init__(self, caminho_arquivo, threshold=80):
        self.caminho_arquivo = caminho_arquivo
        self.threshold = threshold
        self.df_reduzido = None
        self.relatorio = []
        self.inicio = time.time()

    def normalizar(self, texto):
        """Impressão digital do termo."""
        if not isinstance(texto, str):
            return str(texto)
        return unidecode(texto.lower().strip())

    def carregar_e_agrupar(self):
        print("--- Fase 1: Carregamento Inteligente ---")
        try:
            # CORREÇÃO 1: engine='python' e sep=None permite detectar se é ; ou , automaticamente
            df_bruto = pd.read_csv(
                self.caminho_arquivo, 
                header=None, 
                sep=None, 
                engine='python',
                names=['Termo_Original', 'Frequencia_Raw'],
                dtype={0: str} # Lê a primeira coluna como texto sempre
            )
            
            # CORREÇÃO 2: Tratamento robusto de números. Se não for número, vira 0.
            df_bruto['Frequencia'] = pd.to_numeric(df_bruto['Frequencia_Raw'], errors='coerce').fillna(0)
            df_bruto['Termo_Original'] = df_bruto['Termo_Original'].fillna('')

            print(f"✓ Leitura inicial: {len(df_bruto)} linhas.")

            # Normalização
            df_bruto['Termo_Normalizado'] = df_bruto['Termo_Original'].apply(self.normalizar)

            # Agrupamento (Peneira Grossa)
            self.df_reduzido = df_bruto.groupby('Termo_Normalizado').agg({
                'Termo_Original': 'first', 
                'Frequencia': 'sum'
            }).reset_index()

            print(f"✓ Termos únicos após normalização: {len(self.df_reduzido)}\n")

        except Exception as e:
            print(f"✗ Erro crítico ao ler arquivo: {e}")
            sys.exit(1)

    def analisar_profundidade(self):
        print("--- Fase 2: Análise Profunda (Fuzzy Logic) ---")
        
        termos_unicos = self.df_reduzido['Termo_Normalizado'].tolist()
        
        # CORREÇÃO 3 (CRÍTICA): Criar mapas de busca rápida (Dicionários)
        # Isso evita usar .loc dentro do loop, acelerando o processo em 100x
        mapa_original = pd.Series(
            self.df_reduzido.Termo_Original.values, 
            index=self.df_reduzido.Termo_Normalizado
        ).to_dict()
        
        mapa_frequencia = pd.Series(
            self.df_reduzido.Frequencia.values, 
            index=self.df_reduzido.Termo_Normalizado
        ).to_dict()
        
        ja_processados = set()
        total = len(termos_unicos)
        
        print("Iniciando varredura... (Isso usa muito processador)")
        
        for i, termo_foco in enumerate(termos_unicos):
            if i % 100 == 0:
                print(f"Progresso: {i}/{total} ({(i/total)*100:.1f}%)", end='\r')

            if termo_foco in ja_processados:
                continue

            matches = process.extract(
                termo_foco, 
                termos_unicos, 
                scorer=fuzz.token_set_ratio, 
                score_cutoff=self.threshold,
                limit=30
            )

            if len(matches) > 1:
                grupo_duplicatas = []
                freq_total = 0
                
                for match in matches:
                    termo_enc = match[0] # termo normalizado
                    score = match[1]
                    
                    # CORREÇÃO 3 (Uso): Busca instantânea no dicionário
                    nome_real = mapa_original.get(termo_enc, "Erro")
                    freq_real = mapa_frequencia.get(termo_enc, 0)
                    
                    grupo_duplicatas.append(f"{nome_real} ({score:.0f}%)")
                    freq_total += freq_real
                    
                    ja_processados.add(termo_enc)

                self.relatorio.append({
                    'Termo Principal': mapa_original[termo_foco],
                    'Possíveis Duplicatas': " | ".join(grupo_duplicatas),
                    'Total Variações': len(grupo_duplicatas),
                    'Frequência Somada': int(freq_total)
                })
            else:
                ja_processados.add(termo_foco)

        tempo = (time.time() - self.inicio) / 60
        print(f"\n\n✓ Análise concluída em {tempo:.2f} minutos.")
        print(f"✓ {len(self.relatorio)} grupos encontrados.")

    def salvar(self):
        if not self.relatorio:
            print("Nenhum padrão encontrado.")
            return

        df_final = pd.DataFrame(self.relatorio)
        df_final = df_final.sort_values(by='Total Variações', ascending=False)
        
        nome = 'relatorio_final.csv'
        # Usamos ; como separador no output para abrir fácil no Excel BR
        df_final.to_csv(nome, index=False, sep=';', encoding='utf-8-sig')
        print(f"✓ Salvo em: {nome}")

if __name__ == "__main__":
    # Configure aqui
    ARQUIVO = 'assuntos.csv' 
    SENSIBILIDADE = 80    
    
    app = IndexadorArtesanal(ARQUIVO, threshold=SENSIBILIDADE)
    app.carregar_e_agrupar()
    app.analisar_profundidade()
    app.salvar()