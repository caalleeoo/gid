import requests
from bs4 import BeautifulSoup
import csv
import json
import time
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os

# --- 1. A Arte da Conexão (Resiliência) ---
def configurar_sessao_robusta():
    """
    Cria uma sessão HTTP que não desiste facilmente.
    Como um diplomata paciente, ela tenta renegociar se o servidor falhar.
    """
    sessao = requests.Session()
    retentativas = Retry(
        total=5,
        backoff_factor=2,  # Espera exponencial: 2s, 4s, 8s...
        status_forcelist=[429, 500, 502, 503, 504],
        raise_on_status=False
    )
    sessao.mount('https://', HTTPAdapter(max_retries=retentativas))
    return sessao

# --- 2. O Núcleo de Extração ---
def extrair_titulos_unb_massivo():
    # Configurações de Arquivo
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M")
    arquivo_csv = f"riunb_titulos_{timestamp_str}.csv"
    arquivo_json = f"riunb_titulos_{timestamp_str}.json"
    
    # Parâmetros da Jornada
    base_url = "https://repositorio.unb.br/browse"
    offset = 0
    rpp = 50  # 50 é um número áureo aqui: rápido o suficiente, leve o suficiente.
    total_coletado = 0
    
    # Lista para manter os dados em memória para o JSON final
    buffer_memoria = []

    # Cabeçalhos para parecer um navegador legítimo (Ética Digital)
    headers = {
        'User-Agent': 'AcademicScraper/2.0 (University Research; contact: researcher@unb.br)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }

    sessao = configurar_sessao_robusta()

    print(f"🏛️  [INÍCIO] Iniciando a Grande Coleta de Títulos RIUnB")
    print(f"📦 [SAÍDA] CSV (Stream): {arquivo_csv} | JSON (Final): {arquivo_json}")
    print(f"🌊 [LOTE] Processando {rpp} itens por página")
    print("-" * 60)

    try:
        # Abrimos o CSV em modo 'w' (write) e mantemos aberto
        with open(arquivo_csv, mode='w', newline='', encoding='utf-8-sig') as f_csv:
            writer = csv.writer(f_csv)
            # O cabeçalho agora inclui o Link, pois títulos sem link são apenas texto morto.
            writer.writerow(['Titulo', 'Link_Relativo', 'Offset_Origem', 'Data_Coleta'])
            
            while True:
                # Ordenação por título (ASC) garante a sequência alfabética
                params = {
                    'type': 'title', 
                    'order': 'ASC', 
                    'rpp': str(rpp), 
                    'offset': str(offset)
                }
                
                try:
                    # Feedback visual dinâmico (sobrescreve a linha para não poluir o terminal)
                    print(f"⏳ Coletando lote iniciando em {offset}... ", end='\r')
                    
                    response = sessao.get(base_url, params=params, headers=headers, timeout=60)
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Estratégia de Seleção:
                    # O DSpace geralmente lista títulos dentro de <li> com class 'list-group-item'
                    # Dentro dele, procuramos o primeiro <a> que contém o título.
                    itens = soup.find_all('li', class_='list-group-item')
                    
                    # Critério de Parada: Página vazia
                    if not itens:
                        print(f"\n✅ [FIM] O oceano de dados acabou. Offset final: {offset}.")
                        break

                    itens_nesta_pagina = 0
                    current_time = datetime.now().isoformat()

                    for item in itens:
                        tag_a = item.find('a')
                        
                        if tag_a:
                            titulo = tag_a.get_text(strip=True)
                            link = tag_a.get('href', '')
                            
                            # 1. Escreve no CSV (Segurança imediata)
                            writer.writerow([titulo, link, offset, current_time])
                            
                            # 2. Guarda na Memória (Para o JSON final)
                            dado_estruturado = {
                                "titulo": titulo,
                                "url_relativa": link,
                                "origem_offset": offset,
                                "coletado_em": current_time
                            }
                            buffer_memoria.append(dado_estruturado)
                            itens_nesta_pagina += 1

                    # Validação de Segurança (Se a página retornou itens, mas não conseguimos extrair nenhum)
                    if itens_nesta_pagina == 0 and len(itens) > 0:
                        print(f"\n⚠️ [ALERTA] Itens encontrados no HTML mas nenhum título extraído. Verifique os seletores.")
                        # Opcional: break, mas melhor continuar para ver se é só uma página ruim
                    
                    total_coletado += itens_nesta_pagina
                    print(f"✨ Progresso: {total_coletado} títulos salvos. (Último lote: {itens_nesta_pagina} itens)")

                    offset += rpp
                    
                    # Pausa Elegante: Não bombardeie o servidor da universidade.
                    time.sleep(1.5) 

                except Exception as e:
                    print(f"\n❌ [ERRO] Falha no offset {offset}: {e}")
                    print(f"🛡️ [RECUPERAÇÃO] O sistema aguardará 20s e tentará novamente...")
                    time.sleep(20)
                    # O 'continue' aqui faz o loop tentar o MESMO offset novamente
                    continue

        # --- Fase Final: A Cristalização do JSON ---
        print("\n" + "-" * 60)
        print(f"💾 Gerando arquivo JSON consolidado com {len(buffer_memoria)} registros...")
        
        with open(arquivo_json, 'w', encoding='utf-8') as f_json:
            json.dump(buffer_memoria, f_json, ensure_ascii=False, indent=4)

        print(f"🏆 [SUCESSO ABSOLUTO]")
        print(f"   CSV: {os.path.abspath(arquivo_csv)}")
        print(f"   JSON: {os.path.abspath(arquivo_json)}")
        print(f"   Total de Títulos: {total_coletado}")

    except KeyboardInterrupt:
        print(f"\n🛑 [PAUSA MANUAL] Script interrompido. O CSV contém dados seguros até o offset {offset}.")
        # Tenta salvar o JSON do que já temos
        if buffer_memoria:
            print("💾 Salvando JSON parcial de emergência...")
            with open(arquivo_json, 'w', encoding='utf-8') as f_json:
                json.dump(buffer_memoria, f_json, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    extrair_titulos_unb_massivo()