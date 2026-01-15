import csv
import difflib
import re
import os
import json
import unicodedata
import sys  # <--- Necessário para a barra de progresso

# --- CONFIGURAÇÃO ---
ARQUIVO_ENTRADA = 'autores.csv'
PREFIXO_SAIDA = 'relatorio_duplicatas'
LIMITE_SIMILARIDADE_VISUAL = 0.88

class ArtesaoFonetico:
    """Especialista em transformar texto escrito em representação sonora (PT-BR)."""
    
    @staticmethod
    def remover_acentos(texto: str) -> str:
        nfkd = unicodedata.normalize('NFKD', texto)
        return "".join([c for c in nfkd if not unicodedata.combining(c)])

    @staticmethod
    def gerar_impressao_digital(texto: str) -> str:
        if not texto: return ""
        s = ArtesaoFonetico.remover_acentos(texto.upper())
        s = re.sub(r'[^A-Z]', '', s)
        
        # Fonética simplificada PT-BR
        if s.startswith('H'): s = s[1:]
        s = s.replace('PH', 'F').replace('Y', 'I')
        s = s.replace('QU', 'K').replace('CA', 'KA').replace('CO', 'KO').replace('CU', 'KU')
        s = s.replace('Ç', 'S').replace('Z', 'S').replace('X', 'S').replace('SS', 'S').replace('SC', 'S')
        s = s.replace('GE', 'JE').replace('GI', 'JI')
        s = s.replace('W', 'V')
        s = re.sub(r'(.)\1+', r'\1', s)
        
        return s

class ArtesaoDeDados:
    @staticmethod
    def normalizar(texto: str) -> str:
        if not texto: return ""
        limpo = re.sub(r'[^\w\s,]', '', texto) 
        limpo = re.sub(r'\s+', ' ', limpo.strip())
        return limpo.upper()

    @staticmethod
    def calcular_similaridade_visual(a: str, b: str) -> float:
        return difflib.SequenceMatcher(None, a, b).ratio()

    @staticmethod
    def verificar_inclusao(nome_curto: str, nome_longo: str) -> bool:
        nc = nome_curto.replace('.', '').strip()
        nl = nome_longo.replace('.', '').strip()
        if len(nc) >= len(nl): return False
        return nl.startswith(nc)

class UX:
    """Responsável pela experiência do usuário no terminal."""
    @staticmethod
    def mostrar_barra(atual, total, prefixo='', tamanho=30):
        percents = 100.0 * (atual / float(total))
        # Cria a barra visual (ex: █ █ ░ ░)
        cheio = int(tamanho * atual // total)
        barra = '█' * cheio + '░' * (tamanho - cheio)
        
        # \r retorna o cursor para o início da linha (sem pular linha)
        sys.stdout.write(f'\r{prefixo} |{barra}| {percents:.1f}% Completo')
        sys.stdout.flush() # Força a atualização imediata da tela

def reconstruir_linha_fragmentada(linha: list) -> tuple:
    if len(linha) == 2: return linha[0], linha[1]
    elif len(linha) >= 3:
        return ",".join(linha[:-1]), linha[-1]
    return linha[0], "0"

# --- EXPORTADORES ---
def exportar_txt(relatorio, nome_arquivo):
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        f.write("RELATÓRIO DE DUPLICIDADES\n=========================\n\n")
        for i, grupo in enumerate(relatorio, 1):
            f.write(f"GRUPO #{i}\n")
            for item in grupo:
                marcador = "   |->" if item.get('is_similar') else " [ORIGEM]"
                f.write(f"{marcador} {item['original']:<30} [Som: {item['fonetica']}] -- {item.get('motivo','')}\n")
            f.write("-" * 60 + "\n")
    print(f"✓ TXT: {nome_arquivo}")

def exportar_csv(relatorio, nome_arquivo):
    cabecalho = ['ID_Grupo', 'Status', 'Nome_Original', 'Cod_Fonetico', 'Frequencia', 'Motivo', 'Score_Visual']
    with open(nome_arquivo, 'w', encoding='utf-8', newline='') as f:
        escritor = csv.DictWriter(f, fieldnames=cabecalho)
        escritor.writeheader()
        for i, grupo in enumerate(relatorio, 1):
            for item in grupo:
                escritor.writerow({
                    'ID_Grupo': i,
                    'Status': 'SIMILAR' if item.get('is_similar') else 'PIVO',
                    'Nome_Original': item['original'],
                    'Cod_Fonetico': item['fonetica'],
                    'Frequencia': item['freq'],
                    'Motivo': item.get('motivo', 'N/A'),
                    'Score_Visual': item.get('score', 'N/A')
                })
    print(f"✓ CSV: {nome_arquivo}")

def exportar_json(relatorio, nome_arquivo):
    estrutura = {"meta": {"algoritmo": "Hibrido + UX"}, "conflitos": relatorio}
    with open(nome_arquivo, 'w', encoding='utf-8') as f:
        json.dump(estrutura, f, indent=4, ensure_ascii=False)
    print(f"✓ JSON: {nome_arquivo}")

# --- FLUXO PRINCIPAL ---

def auditar_csv():
    print(f"--- Iniciando Auditoria Híbrida ---")
    
    if not os.path.exists(ARQUIVO_ENTRADA):
        with open(ARQUIVO_ENTRADA, 'w', encoding='utf-8') as f:
            f.write("Autor,Frequencia\nLUIZ SOUZA,10\nLUIS SOUSA,5\nJOAO,1\nJOAO DA SILVA,2\n")
        print(f"-> Arquivo de teste '{ARQUIVO_ENTRADA}' criado.")

    dados = []
    try:
        with open(ARQUIVO_ENTRADA, mode='r', encoding='utf-8-sig') as f:
            leitor = csv.reader(f)
            next(leitor, None)
            print("Lendo arquivo e gerando fonética...")
            for linha in leitor:
                if not linha: continue
                nome, freq = reconstruir_linha_fragmentada(linha)
                dados.append({
                    "original": nome,
                    "norm": ArtesaoDeDados.normalizar(nome),
                    "fonetica": ArtesaoFonetico.gerar_impressao_digital(nome),
                    "freq": freq
                })
    except Exception as e:
        print(f"Erro: {e}")
        return

    total_registros = len(dados)
    print(f"Analisando {total_registros} registros cruzados...")

    relatorio = []
    ignorados = set()

    # LOOP PRINCIPAL COM BARRA DE PROGRESSO
    for i in range(total_registros):
        
        # --- ATUALIZAÇÃO VISUAL ---
        UX.mostrar_barra(i + 1, total_registros, prefixo="Analisando")
        # --------------------------

        if i in ignorados: continue
        
        pivo = dados[i]
        pivo_copy = pivo.copy()
        pivo_copy['is_similar'] = False
        grupo = [pivo_copy]
        match_found = False

        for j in range(i + 1, total_registros):
            if j in ignorados: continue
            
            candidato = dados[j]
            
            score_visual = ArtesaoDeDados.calcular_similaridade_visual(pivo['norm'], candidato['norm'])
            match_fonetico = (pivo['fonetica'] == candidato['fonetica']) and (len(pivo['fonetica']) > 2)
            
            motivo = ""
            if score_visual > LIMITE_SIMILARIDADE_VISUAL:
                motivo = f"Visual ({score_visual:.0%})"
            elif match_fonetico:
                motivo = "Fonética Idêntica"
            elif ArtesaoDeDados.verificar_inclusao(pivo['norm'], candidato['norm']):
                motivo = "Inclusão"

            if motivo:
                cand_copy = candidato.copy()
                cand_copy['motivo'] = motivo
                cand_copy['score'] = f"{score_visual:.2f}"
                cand_copy['is_similar'] = True
                grupo.append(cand_copy)
                ignorados.add(j)
                match_found = True

        if match_found:
            relatorio.append(grupo)

    # Limpa a linha da barra de progresso para não atrapalhar o relatório final
    print() 
    print("-" * 30)
    
    exportar_txt(relatorio, f"{PREFIXO_SAIDA}.txt")
    exportar_csv(relatorio, f"{PREFIXO_SAIDA}.csv")
    exportar_json(relatorio, f"{PREFIXO_SAIDA}.json")
    
    print("\nProcesso concluído.")

if __name__ == "__main__":
    auditar_csv()