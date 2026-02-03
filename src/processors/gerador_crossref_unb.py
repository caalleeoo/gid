import csv
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import os

def converter_grau(grau_raw):
    """Mapeia o tipo de trabalho para o padrão internacional."""
    termo = str(grau_raw).lower() if grau_raw else ""
    if 'doutorado' in termo: return "Doctorate"
    if 'dissertação' in termo: return "Master"
    return "Thesis"

def criar_xml_unb_v_final():
    # 1. Solicitação de Caminho
    caminho_csv = input("Digite ou cole o caminho completo do arquivo CSV: ").strip().replace('"', '')
    
    if not os.path.exists(caminho_csv):
        print(f"Erro: O arquivo '{caminho_csv}' não foi encontrado.")
        return

    # Definir caminho de saída no mesmo diretório
    diretorio = os.path.dirname(caminho_csv)
    nome_base = os.path.splitext(os.path.basename(caminho_csv))[0]
    caminho_xml = os.path.join(diretorio, f"{nome_base}_para_crossref.xml")

    # 2. Configurações de Cabeçalho
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")[:-3]
    
    root = ET.Element("doi_batch", {
        "version": "5.4.0",
        "xmlns": "http://www.crossref.org/schema/5.4.0",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": "http://www.crossref.org/schema/5.4.0 http://www.crossref.org/schema/deposit/crossref5.4.0.xsd"
    })

    head = ET.SubElement(root, "head")
    ET.SubElement(head, "doi_batch_id").text = f"UnB_batch_{timestamp}"
    ET.SubElement(head, "timestamp").text = timestamp
    depositor = ET.SubElement(head, "depositor")
    ET.SubElement(depositor, "depositor_name").text = "bcunb:bcunb"
    ET.SubElement(depositor, "email_address").text = "patricianuness@unb.br"
    ET.SubElement(head, "registrant").text = "WEB-FORM"

    body = ET.SubElement(root, "body")

    # 3. Processamento dos Dados
    try:
        with open(caminho_csv, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                dissertation = ET.SubElement(body, "dissertation")
                
                # Ordem correta das tags conforme Schema
                contributors = ET.SubElement(dissertation, "contributors")
                person = ET.SubElement(contributors, "person_name", {"sequence": "first", "contributor_role": "author"})
                ET.SubElement(person, "given_name") # Reservado
                ET.SubElement(person, "surname").text = row.get('dc.contributor.author', '')

                titles = ET.SubElement(dissertation, "titles")
                ET.SubElement(titles, "title").text = row.get('dc.title', '')
                
                # Tratamento de Data
                data_raw = row.get('dc.date.submitted', '')
                app_date = ET.SubElement(dissertation, "approval_date")
                if len(data_raw) >= 10: # Formato YYYY-MM-DD
                    partes = data_raw.split('-')
                    ET.SubElement(app_date, "month").text = partes[1]
                    ET.SubElement(app_date, "day").text = partes[2]
                    ET.SubElement(app_date, "year").text = partes[0]
                else:
                    ET.SubElement(app_date, "year").text = data_raw[:4]

                # Instituição conforme legado
                inst = ET.SubElement(dissertation, "institution")
                ET.SubElement(inst, "institution_name").text = "Universidade de Brasília"
                ET.SubElement(inst, "institution_acronym").text = "UnB"
                
                unidade_raw = row.get('dc.description.unidade', '')
                if unidade_raw:
                    unidade_clean = ", ".join([u.strip() for u in unidade_raw.split('||')])
                    ET.SubElement(inst, "institution_department").text = unidade_clean

                ET.SubElement(dissertation, "degree").text = converter_grau(row.get('dc.type', ''))

                # DOI e URL
                doi_val = row.get('dc.identifier.doi[pt_BR]', '')
                doi_data = ET.SubElement(dissertation, "doi_data")
                ET.SubElement(doi_data, "doi").text = str(doi_val) if doi_val else ""
                ET.SubElement(doi_data, "resource").text = row.get('dc.identifier.uri', '')

        # 4. Finalização e Gravação
        xml_str = ET.tostring(root, encoding='utf-8')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")

        with open(caminho_xml, "w", encoding="utf-8") as out:
            out.write(pretty_xml)
        
        print("\n" + "="*50)
        print("ARTESANATO CONCLUÍDO COM SUCESSO!")
        print(f"Arquivo gerado: {caminho_xml}")
        print("="*50)

    except Exception as e:
        print(f"\nOcorreu um erro durante a criação do código: {e}")

if __name__ == "__main__":
    criar_xml_unb_v_final()