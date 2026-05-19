<!-- README.md for bibliometrix-python -->

# bibliometrix-python

## A Python tool for comprehensive science mapping analysis

[![bibliometrix: An R-tool for comprehensive science mapping analysis.](https://www.bibliometrix.org/JOI-badge.svg)](https://doi.org/10.1016/j.joi.2017.08.007)

<p align="center">
<img src="https://www.bibliometrix.org/logo_new.png" width="400"/>
</p>

## Overview

**bibliometrix-python** is a Python implementation of the renowned **bibliometrix** R package, providing a comprehensive set of tools for quantitative research in bibliometrics and scientometrics.

This project reimplements the core functionality of [bibliometrix](https://github.com/massimoaria/bibliometrix) (developed by Massimo Aria and Corrado Cuccurullo) using Python and the Shiny for Python framework, making these powerful bibliometric tools accessible to the Python scientific community.

Bibliometrics applies quantitative analysis and statistics to scientific publications and their citation patterns. It has become essential across all scientific fields for evaluating growth, maturity, leading authors, conceptual and intellectual maps, and emerging trends within research communities.

**bibliometrix-python** supports scholars in three key phases of analysis:

- **Data importing and conversion** from major bibliographic databases (Web of Science, Scopus, PubMed, Dimensions, Lens, Cochrane) and live APIs (OpenAlex, PubMed E-utilities)
- **Bibliometric analysis** of publication datasets, including descriptive statistics, author productivity, and source impact
- **Building and visualizing networks** for co-citation, coupling, collaboration, and co-word analysis

---

## What's New — ETL Pipeline

Version 2.0 introduces a complete, source-agnostic **ETL (Extract → Transform → Load) pipeline** that replicates R's `bibliometrix::convert2df()` function in Python.

### Key additions

| Feature | Description |
|---------|-------------|
| **Unified schema** | All sources produce the same 24-column WoS-tagged DataFrame |
| **5 file sources** | Web of Science, Scopus CSV, Dimensions XLSX, PubMed TXT, Lens CSV |
| **2 live APIs** | OpenAlex REST (cursor pagination) and PubMed E-utilities (ESearch + EFetch XML) |
| **Dashboard API tab** | Fetch records directly from the UI — no file download required |
| **CLI** | `run_etl.py` for batch processing and automation |
| **Test suite** | 75 pytest tests across 6 modules |
| **Jupyter notebook** | `notebooks/etl_demo.ipynb` — 14-section end-to-end demo |

### Supported data sources

| Source | Mode | Format | Status |
|--------|------|--------|--------|
| Web of Science | File | `.txt`, `.bib`, `.ciw` | ✅ Fully supported |
| Scopus | File | `.csv`, `.bib` | ✅ Fully supported |
| Dimensions | File | `.xlsx`, `.csv` | ✅ Fully supported |
| PubMed | File | `.txt` (MEDLINE) | ✅ Fully supported |
| OpenAlex | Live API | REST JSON | ✅ Fully supported |
| PubMed API | Live API | E-utilities XML | ✅ Fully supported |
| Lens.org | File | `.csv` | 🚧 In progress |
| Cochrane CDSR | File | `.txt` | 🚧 In progress |

---

## biblioshiny: Python Edition

**bibliometrix-python** includes an interactive web application built with **Shiny for Python**, providing an intuitive interface for comprehensive bibliometric analysis.

### Data Management

- **Import raw data files** from Web of Science, Scopus, Dimensions, PubMed, Lens, or Cochrane
- **Fetch from live APIs** — search OpenAlex or PubMed directly from the dashboard
- **Load Bibliometrix files** — reload previously exported XLSX/CSV datasets
- **Use sample datasets** — built-in management collection for testing
- **Filter data** by publication year, language, document type, citation count, and Bradford's Law zones

### Analytics and Visualization

- **Three-level metrics** for comprehensive analysis:
  - **Sources**: journal performance, impact metrics, Bradford's Law, local impact, production over time
  - **Authors**: productivity, Lotka's Law, h-index, local impact, affiliations, collaboration patterns
  - **Documents**: citation analysis, most relevant papers, references spectroscopy

- **Countries Analysis**: scientific production by country, collaboration networks, corresponding authors' countries

### Knowledge Structure Analysis

- **Conceptual Structure**: co-word analysis, thematic mapping, thematic evolution
- **Intellectual Structure**: co-citation networks, historiograph, document coupling
- **Social Structure**: co-authorship networks at author, institution, and country levels

### Content Analysis

- **Word Analysis**: frequent words, word clouds, treemaps, word frequency over time
- **Trend Topics**: identify emerging and declining research topics
- **Three-Field Plot**: Sankey diagrams for author × keyword × journal relationships

### Advanced Features

- **AI-Powered Assistant**: Google Gemini AI chatbot for contextual help — 🧪 BETA
- **Interactive Reports**: generate comprehensive Excel reports from multiple analyses
- **Export Capabilities**: high-resolution PNG images and Excel tables

---

## Quick Start

### 1. Clone and set up environment

```bash
git clone https://github.com/PRAISELab-PicusLab/bibliometrix-python.git
cd bibliometrix-python

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

> **macOS note:** `requirements.txt` includes `pywin32` (Windows-only). If `pip install -r requirements.txt` fails, remove that line first:
> ```bash
> grep -v pywin32 requirements.txt > req_clean.txt && pip install -r req_clean.txt
> ```

### 2. Start the dashboard

```bash
python3 -m shiny run app.py --port 8000 --reload
```

Open your browser at: **http://127.0.0.1:8000**

### 3. Run the ETL pipeline (command line)

```bash
# File mode — auto-detects source from extension and columns
python3 run_etl.py --mode file --input sources/Scopus/Scopus.csv --output output/unified.csv

# API mode — live retrieval
python3 run_etl.py --mode api --platform openalex --query "bibliometrics" --max-records 200 --output output/oa.csv
python3 run_etl.py --mode api --platform pubmed_api --query "machine learning" --max-records 100
```

### 4. Use the Python API directly

```python
from www.services.etl import convert2df, run_file_pipeline, run_api_pipeline

# From a file
df, is_valid, errors = run_file_pipeline("sources/Scopus/Scopus.csv")

# From the OpenAlex API
df, is_valid, errors = run_api_pipeline("bibliometrics", platform="openalex", max_records=500)

# One-liner (equivalent to R's convert2df)
df = convert2df("sources/Dimensions/Dimensions.xlsx")
df = convert2df(source="openalex", query="scientometrics")
```

---

## ETL Package Reference

### Package layout

```
www/services/etl/
├── __init__.py       Public API: run_file_pipeline, run_api_pipeline, convert2df
├── schema.py         24-column WoS schema, type contracts, default values
├── mappings.py       Per-source column → WoS tag dictionaries
├── extractor.py      File loading and source auto-detection
├── api_retriever.py  OpenAlex REST + NCBI E-utilities fetchers
├── standardizer.py   Rename → normalize → type-enforce pipeline
├── sr_generator.py   Short Reference (SR) field computation
├── validator.py      Schema completeness and type-contract checks
├── exporter.py       CSV serialization for list-valued columns
└── pipeline.py       High-level orchestrators
```

### Unified schema (WoS tags)

Every DataFrame produced by the ETL pipeline contains exactly these 24 columns:

| Tag | Description | Type |
|-----|-------------|------|
| `DB` | Database source | `str` |
| `UT` | Unique document ID | `str` |
| `DI` | DOI | `str` |
| `PMID` | PubMed ID | `str` |
| `TI` | Title | `str` |
| `SO` | Journal / Source | `str` |
| `JI` | Abbreviated source title | `str` |
| `PY` | Publication year | `str` |
| `DT` | Document type | `str` |
| `LA` | Language | `str` |
| `TC` | Times cited | `int` |
| `AU` | Authors (abbreviated) | `list[str]` |
| `AF` | Authors (full name) | `list[str]` |
| `C1` | Affiliations | `list[str]` |
| `RP` | Reprint address | `str` |
| `CR` | Cited references | `list[str]` |
| `DE` | Author keywords | `list[str]` |
| `ID` | Index / MeSH keywords | `list[str]` |
| `AB` | Abstract | `str` |
| `VL` | Volume | `str` |
| `IS` | Issue | `str` |
| `BP` | Begin page | `str` |
| `EP` | End page | `str` |
| `SR` | Short reference key | `str` |

### CLI reference

```bash
python3 run_etl.py --mode file  --input PATH  [--source SOURCE]  [--output PATH]
python3 run_etl.py --mode api   --query TEXT  [--platform openalex|pubmed_api]
                                              [--max-records N]   [--output PATH]
```

Exit codes: `0` = valid, `1` = input error, `2` = validation warnings.

---

## Project Structure

```plaintext
bibliometrix-python/
│
├── app.py                      # Main Shiny application
├── run_etl.py                  # ETL command-line interface
├── requirements.txt            # Python dependencies
├── README.md
│
├── www/services/etl/           # ETL pipeline package (new)
│   ├── __init__.py
│   ├── schema.py
│   ├── mappings.py
│   ├── extractor.py
│   ├── api_retriever.py
│   ├── standardizer.py
│   ├── sr_generator.py
│   ├── validator.py
│   ├── exporter.py
│   └── pipeline.py
│
├── www/services/               # Core bibliometric services
│   ├── parsers.py
│   ├── format_functions.py
│   ├── metatagextraction.py
│   ├── cocmatrix.py
│   ├── histnetwork.py
│   └── ... (15+ service modules)
│
├── functions/                  # Shiny UI analysis functions
│   ├── get_data.py
│   ├── get_table.py
│   ├── get_database.py
│   └── ... (35+ analysis modules)
│
├── tests/etl/                  # ETL test suite (new)
│   ├── test_mappings.py
│   ├── test_extractor.py
│   ├── test_standardizer.py
│   ├── test_validator.py
│   ├── test_exporter.py
│   └── test_pipeline.py
│
├── notebooks/
│   └── etl_demo.ipynb          # 14-section ETL demo notebook
│
├── docs/
│   └── etl_project_report.md   # Architecture and design report
│
└── sources/                    # Sample datasets
    ├── Web_of_Science/
    ├── Scopus/
    ├── PubMed/
    ├── Dimensions/
    ├── Lens/
    └── Cochrane/
```

---

## Running Tests

```bash
# Activate the virtual environment first
source .venv/bin/activate

# Run the full ETL test suite
python3 -m pytest tests/etl/ -v

# Syntax check only (no environment dependencies needed)
python3 -m py_compile www/services/etl/*.py
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'prince'` | Virtual environment not active | `source .venv/bin/activate` |
| `ModuleNotFoundError: No module named 'google'` | Wrong `google` package | `pip install google-genai==1.16.1` |
| `Address already in use` | Port 8000 taken | `lsof -ti tcp:8000 \| xargs kill -9` or use `--port 8001` |
| `ModuleNotFoundError: No module named 'www'` | Wrong working directory | `cd bibliometrix-python` before running |
| Dashboard shows empty page after file upload | Stale browser cache | Hard-refresh (`Cmd+Shift+R`) |
| API fetch returns no results | Network/firewall | Check internet connectivity; try `--max-records 10` |

---

## How to cite

If you use this package for your research, please cite the original R package:

Aria, M. & Cuccurullo, C. (2017) **bibliometrix: An R-tool for comprehensive science mapping analysis**, *Journal of Informetrics*, 11(4), pp 959-975, Elsevier, DOI: 10.1016/j.joi.2017.08.007

---

## Community

**Original bibliometrix (R version):**
- Official website: https://www.bibliometrix.org
- CRAN page: https://cran.r-project.org/package=bibliometrix
- GitHub repository: https://github.com/massimoaria/bibliometrix

**Python implementation:**
- GitHub repository: https://github.com/PRAISELab-PicusLab/bibliometrix-python
- Issue tracker: https://github.com/PRAISELab-PicusLab/bibliometrix-python/issues

---

## Acknowledgments

This project is a Python reimplementation of the original **bibliometrix** R package developed by:

**Massimo Aria** and **Corrado Cuccurullo**
*University of Naples Federico II, Italy*

We are grateful for their pioneering work in making bibliometric analysis accessible to researchers worldwide.

### Main References

Aria, M. & Cuccurullo, C. (2017). **bibliometrix: An R-tool for comprehensive science mapping analysis**, *Journal of Informetrics*, 11(4), pp 959-975, Elsevier, DOI: 10.1016/j.joi.2017.08.007

Aria, M., Le, T., Cuccurullo, C., Belfiore, A., & Choe, J. (2024). **openalexR: An R-Tool for Collecting Bibliometric Data from OpenAlex**. *The R Journal*, DOI: 10.32614/RJ-2023-089

Aria, M., Cuccurullo, C., D'Aniello, L., Misuraca, M., & Spano, M. (2022). **Thematic Analysis as a New Culturomic Tool: The Social Media Coverage on COVID-19 Pandemic in Italy**. *Sustainability*, 14(6), 3643

---

## Contributing

We welcome contributions to improve the application! To contribute, open a pull request or report issues on our [issue tracker](https://github.com/PRAISELab-PicusLab/bibliometrix-python/issues).

---

## Team

This project was developed by:

**Mariano Barone** · **Gian Marco Orlando** · **Giuseppe Riccio** · **Antonio Romano** · **Diego Russo** · **Vincenzo Moscato**

*Department of Electrical Engineering and Information Technology*
*University of Naples Federico II, Italy*

**Research Lab:** The [PRAISE](https://github.com/PRAISELab) (PRedictive AnalytIcs for underUnderstanding big multimEdia data) research group is part of the PICUS Lab at the Department of Electrical Engineering and Information Technologies (DIETI), University of Naples Federico II, Italy.

---

## License

This application is distributed under the GNU General Public License as specified in the [LICENSE](LICENSE) file.

When used in a publication, please cite the original bibliometrix R package (see [How to cite](#how-to-cite) section).

---

<p align="center">
Made with ❤️ by PRAISELab Team at University of Naples Federico II
</p>
