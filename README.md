# rss-br

Ferramenta para fazer uma **busca ampla de jornais do Brasil** e descobrir/validar **feeds RSS/Atom/XML**, gerando um dataset para análise (quantos feeds existem e quais tópicos/categorias aparecem).

Nesta primeira etapa, o foco é:

- **Buscar uma lista de jornais brasileiros** (via Wikidata)
- **Descobrir possíveis feeds** nos sites (HTML `link rel="alternate"` + caminhos comuns como `/feed`, `/rss.xml`, etc.)
- **Validar e parsear** RSS/Atom
- **Extrair tópicos/categorias** (tags/categories dos itens do feed)
- **Exportar** resultados em JSON/CSV + um resumo por tópico

## Requisitos

- Python **3.12+**

## Instalação

Crie um virtualenv e instale dependências:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Opcional (para usar o comando `rss-br`):

```bash
python3 -m pip install -e .
```

## Uso

### Rodar a varredura

Exemplo rápido (100 sites, 20 threads):

```bash
python3 -m rss_br.cli scan --max-sites 100 --max-workers 20 --out-dir data
```

Se você instalou `-e .`, pode usar:

```bash
rss-br scan --max-sites 100 --max-workers 20 --out-dir data
```

### Arquivos gerados

Dentro de `--out-dir` (por padrão `data/`):

- `feeds.json`: resultado completo (sites + feeds + erros)
- `feeds.csv`: CSV achatado (1 linha por feed)
- `topics.json`: resumo por tópico/categoria (quantos feeds e quantos sites)

> Observação: `data/` está no `.gitignore` (não versiona o dataset).

### Gerar relatório depois (a partir do JSON)

```bash
python3 -m rss_br.cli report --input data/feeds.json --min-count 2
```

## Próximos passos sugeridos

- Enriquecer a fonte (ex.: incluir Wikidata para “news website”, ou uma lista curada por estado/cidade)
- Melhorar descoberta (sitemap, `robots.txt`, heurísticas por CMS)
- Classificar tópicos com normalização (sinônimos, lower, acentos) e/ou NLP
