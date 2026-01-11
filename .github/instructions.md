Aqui está a tradução técnica e adaptada do guia, mantendo a precisão terminológica e a elegância que o projeto exige.

**Objetivo:** Orientação curta e prática para ajudar um agente de IA a ser produtivo rapidamente ao trabalhar neste repositório (raspagem, normalização e processamento de metadados do repositorio.unb.br).

---

## O panorama geral (o que roda e onde)

* **Coletores (Harvesters)** (`src/harvesters/riunb/`): Raspam (fazem *scrape*) as páginas do repositório da UnB e produzem arquivos CSV com carimbos de data/hora (timestamps). Arquivos principais: `riunb_author.py`, `riunb_subjects.py`, `rinb_advisor.py`.
* **Processadores (Processors)** (`src/processors/`): Transformam e higienizam metadados XML (dublin_core) usando CSVs de referência. Arquivo principal: `organizador_metadados_unb.py`.
* **Detectores de duplicatas / auditores** (`src/duplicatas/`): Utilitários para detectar termos e autores quase duplicados. Arquivos principais: `indexador_artesanal.py`, `verificador_autores.py`.

**Fluxo de Dados:** Coletores -> CSV (data/raw ou diretório de trabalho) -> ingestão manual ou via script -> `organizador_metadados_unb.py` processa pastas XML e grava/sobrescreve arquivos `dublin_core.xml`. Os detectores de duplicatas operam nos CSVs (ou listas de frequência produzidas).

---

## Comandos de execução rápida / fluxos de trabalho do desenvolvedor ✅

* **Executar um coletor (cria CSV):**
* `python src/harvesters/riunb/riunb_author.py`
* `python src/harvesters/riunb/riunb_subjects.py`
* `python src/harvesters/riunb/rinb_advisor.py`


* **Executar o processador (interativo):**
* `python src/processors/organizador_metadados_unb.py` (ele solicita um caminho de pasta; armazena o último caminho utilizado em `.gid_last_path`)


* **Executar verificação de duplicatas / auditorias:**
* `python src/duplicatas/indexador_artesanal.py` (nome do arquivo configurável e constante `SENSIBILIDADE`)
* `python src/duplicatas/verificador_autores.py`



**Notas:**

* Os coletores criam saídas nomeadas como `riunb_<tipo>_scraping_YYYYMMDD_HHMM.csv` (timestamps ISO).
* Muitos scripts esperam codificação UTF-8 (use `utf-8-sig` ao ler CSVs exportados pelo Excel).

---

## Padrões importantes e convenções do projeto 🔧

* **Nomenclatura:** Os nomes dos arquivos incluem **timestamps ISO** para reprodutibilidade e para evitar colisões.
* **Sessões de Coleta:** Os coletores usam um padrão compartilhado `configurar_sessao()`: `requests.Session()` + `urllib3.Retry` + um `time.sleep(2.0)` polido entre as requisições. Respeite este padrão ao adicionar novos scrapers.
* **Formato CSV:** Geralmente `Termo,Frequência,Offset,Timestamp_Coleta` — os analisadores (parsers) esperam a frequência como numérico; alguns leitores usam detecção heurística de cabeçalho.
* **Limiares de Correspondência Difusa (Fuzzy Matching):** São constantes explícitas próximas ao topo dos arquivos:
* Padrão do `IndexadorArtesanal`: `threshold=70`
* `verificador_autores.py`: `LIMITE_SIMILARIDADE = 0.88`
* `organizador_metadados_unb.py`: `THRESHOLD_ADVISOR = 90`, `THRESHOLD_KEYWORD = 90`
* *Ajuste com cuidado* — estes valores codificam os compromissos do domínio entre abrangência (recall) e falsos positivos.


* **Normalização de Caracteres:** Funções como `normalizar` / `aplicar_regra_caracteres` lidam com acentos, caixa (maiúscula/minúscula) e regras para palavras curtas (preservando acrônimos como `UnB`, `DF`). Siga-as ao normalizar campos.
* **Efeitos Colaterais na Saída:** O `organizador_metadados_unb.py` sobrescreve/cria `dublin_core.xml` dentro de cada pasta de item; ele também apaga o arquivo XML original se processou um arquivo que não era `dublin_core`.

---

## Integrações externas / dependências ⚙️

* **Web:** `https://repositorio.unb.br` (os scrapers assumem a estrutura HTML: elementos `li.list-group-item` com `a` e `span.badge`). Mudanças no site podem quebrar os scrapers.
* **CSVs de Referência:** Para orientadores/palavras-chave, são referenciados com caminhos absolutos em `organizador_metadados_unb.py` (variáveis: `CAMINHO_CSV_ADVISORS`, `CAMINHO_CSV_KEYWORDS`). Certifique-se de que esses caminhos estejam disponíveis ou atualize-os para caminhos locais do projeto.
* **Principais bibliotecas Python utilizadas:** `requests`, `beautifulsoup4`, `pandas`, `rapidfuzz`/`thefuzz`, `unidecode`, `xml.etree.ElementTree`.

**Configuração sugerida do ambiente de desenvolvimento (descoberta a partir dos imports):**

```bash
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows
pip install pandas requests beautifulsoup4 rapidfuzz thefuzz unidecode

```

---

## Estilo de código e dicas comportamentais para edições ✍️

* **UX:** Preserve as mensagens em português voltadas ao usuário e os logs baseados em emojis (eles são a UX do projeto).
* **Robustez:** Mantenha o padrão `requests.Session()` + `Retry` para scrapers robustos e mantenha pequenos atrasos (2s) por polidez/cortesia.
* **Algoritmos de Texto:** Prefira `token_set_ratio` (rapidfuzz) para comparações termo-vs-termo (usado em `indexador_artesanal.py`) e `fuzz.token_sort_ratio` em `organizador_metadados_unb.py` para buscas difusas (fuzzy lookups) contra dicionários CSV.
* **Execução:** Ao adicionar funcionalidades, adicione um exemplo curto inline no bloco `__main__` do mesmo arquivo para manter os scripts executáveis via CLI (linha de comando).

---

## Armadilhas conhecidas / Pontos de atenção ⚠️

* **Performance:** Entradas grandes (50k+ linhas) podem tornar as passagens difusas (fuzzy passes) lentas e pesadas na memória. O `indexador_artesanal.py` avisa sobre minutos de processamento e marca termos agrupados agressivamente para reduzir relatos duplicados.
* **Caminhos Hardcoded:** Vários caminhos estão codificados de forma rígida (caminhos absolutos em `organizador_metadados_unb.py`). Atualize-os antes de rodar em um ambiente diferente.
* **Testes:** Não há testes automatizados ou CI atualmente; execute scripts em pequenos conjuntos de amostra e inspecione manualmente as saídas CSV/XML produzidas.

---

## Onde procurar exemplos rápidos no repositório 🔎

* **Padrão de Coleta (Harvester):** `src/harvesters/riunb/riunb_subjects.py` (configuração de sessão, saída CSV, polidez e detecção de repetição).
* **Transformações do Processador:** `src/processors/organizador_metadados_unb.py` (lógica de correspondência de assunto/orientador, tags obrigatórias, regras de higienização).
* **Detecção de Duplicatas:** `src/duplicatas/indexador_artesanal.py` e `src/duplicatas/verificador_autores.py` (normalização e heurísticas de pontuação).
