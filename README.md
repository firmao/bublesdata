# OpenHeal TEA — Interactive ER Explorer, Data Analyzer & FAIR Knowledge Graph

An interactive **Streamlit** application for exploring the relational schema, documentation, statistical patterns, and **FAIR** Knowledge Graph representation of the **OpenHeal TEA** study dataset.

## Key Features

- **Interactive Entity-Relationship (ER) Diagram (`streamlit-agraph`)**:
  - Visualizes study tables, primary/foreign keys (`PK` / `FK`), row and column counts, and cardinality links (`1 : 1`, `1 : N`, `N : 1`).
  - Clicking any entity node loads its Markdown documentation (`01_participants.md`, `02_cohort.md`, `04_kinematics_match.md`, `05_kinematics_window.md`, or codebook-synthesized documentation when a standalone `.md` file is absent), embedded `codebook` sheet, live data preview, and column statistics.
  - Runs live referential integrity checks across `id_study` and `id_match`.
- **Dynamic "Analyze Data" Workspace (`?page=analyze_data`)**:
  - Opens in a new browser tab/page via the **Analyze data** button.
  - Automatically refreshes whenever `.xlsx` files change on disk or when cells are edited in the live data grid (`st.data_editor`).
  - Provides natural-language question answering, suggested queries, auto-discovered insight cards (group comparisons, correlations, and progression trends), custom pivot tables, and correlation heatmaps.
- **FAIR Knowledge Graph Converter & Natural Language Query Studio**:
  - Dynamically builds an `rdflib` Knowledge Graph adhering to **Findable, Accessible, Interoperable, and Reusable (FAIR)** principles using typed URIs, `OWL`/`RDFS`/`XSD`/`DCTERMS`/`PROV`/`Schema.org` vocabularies, foreign-key object links, and codebook metadata.
  - Exports graphs in **Turtle (`.ttl`)**, **JSON-LD (`.jsonld`)**, and **N-Triples (`.nt`)**, supports direct **SPARQL** queries, and includes an **Ask in Natural Language** query studio with statistical summaries, SPARQL provenance inspection, CSV export, and printable/PNG chart downloads.

## Dataset Entities & Relationships

| Entity | Primary Key(s) | Foreign Key(s) | Role in Study |
| :--- | :--- | :--- | :--- |
| `01_participants` | `id_study` | — | Analytic cohort ($n = 76$: `38` GE with ASD confirmed by CARS-2, `38` GC matched 1:1 by sex and age) |
| `02_cohort` | `Variable` | `id_study` (aggregated) | Manuscript Table 1 and ABNT sex $\times$ group summary tables derived from `01_participants` |
| `03_matches` | `id_match` | `id_study` | Match-level game performance across Day 1 (GE & GC) and Day 2 (GE only) |
| `04_kinematics_match` | `id_match` | `id_study` | Whole-match 2D hand kinematics (`sparc_*`, `speed_mean_*`, `path_length_*`, `ldlj_*`, `traj_corr_*`, `mirror_score`) |
| `05_kinematics_window` | `id_match`, `window` | `id_match`, `id_study` | Windowed kinematics partitioned into 6 contiguous blocks per match (`early`, `middle`, `late` phases) |
| `09_sus` | `id_study` | `id_study` | System Usability Scale (SUS) item responses and composite usability score |

## Project Structure

```text
.
├── app.py
├── requirements.txt
├── README.md
├── 01_participants.xlsx
├── 01_participants.md
├── 02_cohort.xlsx
├── 02_cohort.md
├── 03_matches.xlsx
├── 04_kinematics_match.xlsx
├── 04_kinematics_match.md
├── 05_kinematics_window.xlsx
├── 05_kinematics_window.md
└── 09_sus.xlsx
```

## Installation & Usage

1. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the Streamlit app from the repository directory (or pass a custom dataset directory via the sidebar or `?dir=/path/to/data`):

   ```bash
   streamlit run app.py
   ```