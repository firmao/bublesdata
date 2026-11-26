import os
from pathlib import Path
import pandas as pd
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OpenHeal TEA — Interactive ER Model",
    page_icon="🧩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Schema & Domain Metadata Definitions
# ---------------------------------------------------------------------------
ENTITY_CONFIG = {
    "01_participants": {
        "title": "01_participants",
        "subtitle": "Analytic Cohort (Core Entity)",
        "xlsx": "01_participants.xlsx",
        "md": "01_participants.md",
        "data_sheet": "data",
        "codebook_sheet": "codebook",
        "pk": ["id_study"],
        "fk": [],
        "color": "#1E88E5",
        "category": "Core Cohort",
    },
    "02_cohort": {
        "title": "02_cohort",
        "subtitle": "Table 1 Summary & ABNT Stats",
        "xlsx": "02_cohort.xlsx",
        "md": "02_cohort.md",
        "data_sheet": "table1",
        "codebook_sheet": None,
        "pk": ["Variable"],
        "fk": ["id_study (aggregated)"],
        "color": "#7CB342",
        "category": "Summary / Derived",
    },
    "03_matches": {
        "title": "03_matches",
        "subtitle": "Game Match Performance",
        "xlsx": "03_matches.xlsx",
        "md": "03_matches.md",
        "data_sheet": "data",
        "codebook_sheet": "codebook",
        "pk": ["id_match"],
        "fk": ["id_study"],
        "color": "#FB8C00",
        "category": "Session & Match Data",
    },
    "04_kinematics_match": {
        "title": "04_kinematics_match",
        "subtitle": "Whole-Match 2D Kinematics",
        "xlsx": "04_kinematics_match.xlsx",
        "md": "04_kinematics_match.md",
        "data_sheet": "data",
        "codebook_sheet": "codebook",
        "pk": ["id_match"],
        "fk": ["id_study"],
        "color": "#8E24AA",
        "category": "Kinematics",
    },
    "05_kinematics_window": {
        "title": "05_kinematics_window",
        "subtitle": "Windowed Kinematics (6 x ~12s)",
        "xlsx": "05_kinematics_window.xlsx",
        "md": "05_kinematics_window.md",
        "data_sheet": "data",
        "codebook_sheet": "codebook",
        "pk": ["id_match", "window"],
        "fk": ["id_match", "id_study"],
        "color": "#D81B60",
        "category": "Kinematics",
    },
    "09_sus": {
        "title": "09_sus",
        "subtitle": "System Usability Scale (SUS)",
        "xlsx": "09_sus.xlsx",
        "md": "09_sus.md",
        "data_sheet": "data",
        "codebook_sheet": "codebook",
        "pk": ["id_study"],
        "fk": ["id_study"],
        "color": "#00897B",
        "category": "Questionnaire",
    },
}

RELATIONSHIPS = [
    {
        "source": "01_participants",
        "target": "03_matches",
        "label": "1 : N (id_study)",
        "cardinality": "1 : N",
        "join_key": "id_study",
        "description": "Each participant plays 2–3 valid matches on Day 1 (GE & GC) and 0–3 matches on Day 2 (GE only).",
    },
    {
        "source": "01_participants",
        "target": "09_sus",
        "label": "1 : 1 (id_study)",
        "cardinality": "1 : 1",
        "join_key": "id_study",
        "description": "Each participant completes one System Usability Scale (SUS) assessment at the end of their final session.",
    },
    {
        "source": "01_participants",
        "target": "02_cohort",
        "label": "Aggregates to (n=76)",
        "cardinality": "N : 1 (Derived)",
        "join_key": "group, sex, age, n_matches_*",
        "description": "Manuscript Table 1 and ABNT sex × group contingency table are computed directly from 01_participants.",
    },
    {
        "source": "03_matches",
        "target": "04_kinematics_match",
        "label": "1 : 1 (id_match)",
        "cardinality": "1 : 1",
        "join_key": "id_match",
        "description": "Every valid match in 03_matches (n = 333) has one corresponding whole-match kinematic summary row.",
    },
    {
        "source": "04_kinematics_match",
        "target": "05_kinematics_window",
        "label": "1 : 6 (id_match)",
        "cardinality": "1 : N (1 : 6)",
        "join_key": "id_match",
        "description": "Each whole match (n = 333) is partitioned into 6 contiguous equal-length time windows (~12s each, n = 1,998).",
    },
    {
        "source": "01_participants",
        "target": "04_kinematics_match",
        "label": "1 : N (id_study)",
        "cardinality": "1 : N (Denormalized FK)",
        "join_key": "id_study",
        "description": "Denormalized participant foreign key allowing direct joins between participant demographics and match kinematics.",
    },
    {
        "source": "01_participants",
        "target": "05_kinematics_window",
        "label": "1 : N (id_study)",
        "cardinality": "1 : N (Denormalized FK)",
        "join_key": "id_study",
        "description": "Denormalized participant foreign key linking participants directly to windowed kinematic segments.",
    },
]


# ---------------------------------------------------------------------------
# Data & Documentation Loaders (Cached)
# ---------------------------------------------------------------------------
@st.cache_data
def load_all_datasets(base_dir: str):
    """Loads all Excel sheets, codebooks, and Markdown files from base_dir."""
    base_path = Path(base_dir)
    loaded = {}

    for entity_key, meta in ENTITY_CONFIG.items():
        xlsx_path = base_path / meta["xlsx"]
        md_path = base_path / meta["md"]

        sheets = {}
        if xlsx_path.exists():
            xls = pd.ExcelFile(xlsx_path)
            for sheet_name in xls.sheet_names:
                sheets[sheet_name] = pd.read_excel(xlsx_path, sheet_name=sheet_name)

        md_text = ""
        if md_path.exists():
            md_text = md_path.read_text(encoding="utf-8")
        else:
            # Synthesize rich Markdown documentation from the embedded codebook if .md is absent
            md_text = synthesize_markdown_from_codebook(entity_key, meta, sheets)

        loaded[entity_key] = {
            "meta": meta,
            "sheets": sheets,
            "md_text": md_text,
            "xlsx_exists": xlsx_path.exists(),
            "md_exists": md_path.exists(),
        }

    return loaded


def synthesize_markdown_from_codebook(entity_key: str, meta: dict, sheets: dict) -> str:
    """Builds structured Markdown documentation from the Excel codebook tab when no .md file is present."""
    data_df = sheets.get(meta["data_sheet"], pd.DataFrame())
    cb_df = sheets.get(meta["codebook_sheet"], pd.DataFrame()) if meta["codebook_sheet"] else pd.DataFrame()

    lines = [
        f"# Tabela `{entity_key}`",
        "",
        f"*{meta['subtitle']}* — Documentação gerada automaticamente a partir da aba `codebook` de `{meta['xlsx']}` (arquivo `{meta['md']}` não encontrado no diretório).",
        "",
        "## Desenho e Chaves",
        f"- **Registros (linhas):** {len(data_df)}",
        f"- **Colunas:** {len(data_df.columns)}",
        f"- **Chave Primária (PK):** `{', '.join(meta['pk'])}`",
        f"- **Chaves Estrangeiras (FK):** `{', '.join(meta['fk']) if meta['fk'] else 'Nenhuma'}`",
        "",
    ]

    if not cb_df.empty:
        # Extract notes row if present at the bottom of the codebook sheet
        notes_rows = cb_df[cb_df.iloc[:, 0].astype(str).str.lower() == "notes"]
        clean_cb = cb_df[
            cb_df.iloc[:, 0].notna()
            & (cb_df.iloc[:, 0].astype(str).str.lower() != "notes")
        ].copy()

        lines.append("## Codebook")
        lines.append("")
        lines.append(clean_cb.to_markdown(index=False))
        lines.append("")

        if not notes_rows.empty:
            lines.append("## Notas do Codebook")
            for _, r in notes_rows.iterrows():
                note_vals = [str(v) for v in r.iloc[1:].dropna() if str(v).strip()]
                for nv in note_vals:
                    lines.append(f"- {nv}")

    return "\n".join(lines)


def build_node_label(entity_key: str, entity_bundle: dict, show_all_cols: bool = False) -> str:
    """Formats a clean UML/ER-style text label for each graph node."""
    meta = entity_bundle["meta"]
    sheets = entity_bundle["sheets"]
    df = sheets.get(meta["data_sheet"], pd.DataFrame())

    n_rows, n_cols = df.shape if not df.empty else (0, 0)
    header = f"📋 {entity_key}\n({n_rows} rows × {n_cols} cols)\n" + "─" * 24

    pk_set = set(meta["pk"])
    fk_set = set(meta["fk"])

    col_lines = []
    cols = list(df.columns)
    display_cols = cols if show_all_cols else cols[:8]

    for col in display_cols:
        dtype_short = str(df[col].dtype)
        if "int" in dtype_short:
            dtype_short = "int"
        elif "float" in dtype_short:
            dtype_short = "float"
        elif "object" in dtype_short:
            dtype_short = "str"

        badge = ""
        if col in pk_set and col in fk_set:
            badge = "🔑🔗 PK,FK "
        elif col in pk_set:
            badge = "🔑 PK "
        elif col in fk_set:
            badge = "🔗 FK "
        else:
            badge = "   • "

        col_lines.append(f"{badge}{col} ({dtype_short})")

    if not show_all_cols and len(cols) > 8:
        col_lines.append(f"   ... +{len(cols) - 8} more columns")

    return header + "\n" + "\n".join(col_lines)


def compute_referential_integrity(loaded_data: dict) -> pd.DataFrame:
    """Verifies join consistency across primary and foreign keys in the actual .xlsx files."""
    checks = []

    p_df = loaded_data["01_participants"]["sheets"].get("data", pd.DataFrame())
    m_df = loaded_data["03_matches"]["sheets"].get("data", pd.DataFrame())
    km_df = loaded_data["04_kinematics_match"]["sheets"].get("data", pd.DataFrame())
    kw_df = loaded_data["05_kinematics_window"]["sheets"].get("data", pd.DataFrame())
    sus_df = loaded_data["09_sus"]["sheets"].get("data", pd.DataFrame())

    if not p_df.empty and not m_df.empty:
        p_ids = set(p_df["id_study"])
        m_ids = set(m_df["id_study"])
        checks.append({
            "Relationship": "01_participants → 03_matches",
            "Join Key": "id_study",
            "Parent Unique Keys": len(p_ids),
            "Child Unique Keys": len(m_ids),
            "Orphan Child Keys": len(m_ids - p_ids),
            "Status": "✅ Valid" if len(m_ids - p_ids) == 0 else "⚠️ Orphan keys found",
        })

    if not p_df.empty and not sus_df.empty:
        p_ids = set(p_df["id_study"])
        s_ids = set(sus_df["id_study"])
        checks.append({
            "Relationship": "01_participants → 09_sus",
            "Join Key": "id_study",
            "Parent Unique Keys": len(p_ids),
            "Child Unique Keys": len(s_ids),
            "Orphan Child Keys": len(s_ids - p_ids),
            "Status": "✅ Valid (1:1 Complete)" if p_ids == s_ids else "⚠️ Mismatch",
        })

    if not m_df.empty and not km_df.empty:
        m_ids = set(m_df["id_match"])
        km_ids = set(km_df["id_match"])
        checks.append({
            "Relationship": "03_matches → 04_kinematics_match",
            "Join Key": "id_match",
            "Parent Unique Keys": len(m_ids),
            "Child Unique Keys": len(km_ids),
            "Orphan Child Keys": len(km_ids - m_ids),
            "Status": "✅ Valid (1:1 Complete)" if m_ids == km_ids else "⚠️ Mismatch",
        })

    if not km_df.empty and not kw_df.empty:
        km_ids = set(km_df["id_match"])
        kw_ids = set(kw_df["id_match"])
        windows_per_match = kw_df.groupby("id_match")["window"].nunique()
        all_six = (windows_per_match == 6).all()
        checks.append({
            "Relationship": "04_kinematics_match → 05_kinematics_window",
            "Join Key": "id_match",
            "Parent Unique Keys": len(km_ids),
            "Child Unique Keys": len(kw_ids),
            "Orphan Child Keys": len(kw_ids - km_ids),
            "Status": "✅ Valid (6 windows/match)" if (km_ids == kw_ids and all_six) else "⚠️ Mismatch",
        })

    return pd.DataFrame(checks)


# ---------------------------------------------------------------------------
# Main Application UI
# ---------------------------------------------------------------------------
def main():
    # Sidebar controls
    st.sidebar.title("🧩 ER Model Controls")
    data_dir = st.sidebar.text_input("Dataset Directory", value=".")

    if not os.path.isdir(data_dir):
        st.error(f"Directory not found: `{data_dir}`")
        return

    loaded_data = load_all_datasets(data_dir)

    # Check if files were found
    found_xlsx = sum(1 for v in loaded_data.values() if v["xlsx_exists"])
    if found_xlsx == 0:
        st.warning("No `.xlsx` dataset files found in the specified directory.")
        return

    st.sidebar.markdown("---")
    show_denormalized = st.sidebar.checkbox(
        "Show denormalized FK edges",
        value=False,
        help="Display direct id_study links from 01_participants to 04_kinematics_match and 05_kinematics_window.",
    )
    show_all_columns = st.sidebar.checkbox(
        "Expand all columns in diagram nodes",
        value=False,
        help="Show every attribute inside the graph boxes instead of truncating at 8 columns.",
    )
    physics_enabled = st.sidebar.checkbox(
        "Enable dynamic physics layout",
        value=True,
        help="Allow nodes to dynamically settle and respond to dragging.",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Direct Entity Selector")
    if "selected_entity" not in st.session_state:
        st.session_state["selected_entity"] = "01_participants"

    entity_keys = list(ENTITY_CONFIG.keys())
    selected_from_radio = st.sidebar.radio(
        "Select Entity to Inspect:",
        options=entity_keys,
        index=entity_keys.index(st.session_state["selected_entity"]),
        format_func=lambda k: f"{k} ({ENTITY_CONFIG[k]['subtitle']})",
    )
    if selected_from_radio != st.session_state["selected_entity"]:
        st.session_state["selected_entity"] = selected_from_radio

    # Header
    st.title("OpenHeal TEA — Interactive Entity-Relationship Explorer")
    st.caption(
        "Click any entity node in the diagram (or select from the sidebar) to inspect its Markdown documentation, "
        "variable codebook, schema keys, and live Excel records."
    )

    # Top KPI Metrics Row
    kpi_cols = st.columns(5)
    p_rows = len(loaded_data["01_participants"]["sheets"].get("data", []))
    m_rows = len(loaded_data["03_matches"]["sheets"].get("data", []))
    km_rows = len(loaded_data["04_kinematics_match"]["sheets"].get("data", []))
    kw_rows = len(loaded_data["05_kinematics_window"]["sheets"].get("data", []))
    sus_rows = len(loaded_data["09_sus"]["sheets"].get("data", []))

    kpi_cols[0].metric("Entities (.xlsx)", f"{found_xlsx} Tables")
    kpi_cols[1].metric("Participants (01)", f"{p_rows} (38 GE / 38 GC)")
    kpi_cols[2].metric("Valid Matches (03 & 04)", f"{m_rows}")
    kpi_cols[3].metric("Kinematic Windows (05)", f"{kw_rows:,}")
    kpi_cols[4].metric("SUS Questionnaires (09)", f"{sus_rows}")

    st.markdown("---")

    # Two-Column Interactive Workspace: Left = ER Diagram, Right = Documentation & Inspector
    col_graph, col_doc = st.columns([1.15, 1.0], gap="large")

    with col_graph:
        st.subheader("Interactive Entity-Relationship Diagram")
        st.markdown(
            "💡 **Tip:** Click a table node to load its documentation on the right. Drag nodes to rearrange."
        )

        nodes = []
        for key, bundle in loaded_data.items():
            if not bundle["xlsx_exists"]:
                continue
            is_selected = key == st.session_state["selected_entity"]
            base_color = bundle["meta"]["color"]

            nodes.append(
                Node(
                    id=key,
                    label=build_node_label(key, bundle, show_all_cols=show_all_columns),
                    shape="box",
                    color={
                        "background": "#1E293B" if not is_selected else "#0F172A",
                        "border": "#FACC15" if is_selected else base_color,
                        "highlight": {"background": "#0F172A", "border": "#FACC15"},
                    },
                    borderWidth=4 if is_selected else 2,
                    font={
                        "color": "#F8FAFC",
                        "face": "monospace",
                        "size": 12,
                        "align": "left",
                    },
                    margin=12,
                )
            )

        edges = []
        for rel in RELATIONSHIPS:
            if not show_denormalized and "Denormalized" in rel["cardinality"]:
                continue
            if not (
                loaded_data[rel["source"]]["xlsx_exists"]
                and loaded_data[rel["target"]]["xlsx_exists"]
            ):
                continue

            is_dashed = "Derived" in rel["cardinality"] or "Denormalized" in rel["cardinality"]
            edges.append(
                Edge(
                    source=rel["source"],
                    target=rel["target"],
                    label=rel["label"],
                    color="#94A3B8" if not is_dashed else "#64748B",
                    dashes=is_dashed,
                    font={"color": "#CBD5E1", "size": 11, "align": "top", "strokeWidth": 0},
                    arrows="to",
                    smooth={"type": "cubicBezier"},
                )
            )

        config = Config(
            width="100%",
            height=620,
            directed=True,
            physics=physics_enabled,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#FACC15",
            collapsible=False,
        )

        clicked_node = agraph(nodes=nodes, edges=edges, config=config)

        if clicked_node and clicked_node in ENTITY_CONFIG:
            if clicked_node != st.session_state["selected_entity"]:
                st.session_state["selected_entity"] = clicked_node
                st.rerun()

        # Referential Integrity & Relationships Summary below the graph
        with st.expander("🔗 Schema Relationships & Referential Integrity Audit", expanded=False):
            st.markdown("#### Active Foreign Key Relationships")
            rel_df = pd.DataFrame(RELATIONSHIPS)[
                ["source", "target", "cardinality", "join_key", "description"]
            ]
            st.dataframe(rel_df, use_container_width=True, hide_index=True)

            st.markdown("#### Live Excel Key Integrity Verification")
            integrity_df = compute_referential_integrity(loaded_data)
            st.dataframe(integrity_df, use_container_width=True, hide_index=True)

    with col_doc:
        active_key = st.session_state["selected_entity"]
        active_bundle = loaded_data[active_key]
        active_meta = active_bundle["meta"]
        active_sheets = active_bundle["sheets"]

        # Entity Header Card
        st.markdown(
            f"""
            <div style="padding: 14px 18px; border-radius: 8px; border-left: 6px solid {active_meta['color']}; background-color: rgba(30, 41, 59, 0.45); margin-bottom: 14px;">
                <h3 style="margin: 0; padding: 0;">📄 {active_key}</h3>
                <p style="margin: 4px 0 0 0; opacity: 0.85;">{active_meta['subtitle']} &nbsp;|&nbsp; <strong>Category:</strong> {active_meta['category']}</p>
                <p style="margin: 6px 0 0 0; font-size: 0.9em;">
                    🔑 <strong>PK:</strong> <code>{', '.join(active_meta['pk'])}</code> &nbsp;&nbsp;
                    🔗 <strong>FK:</strong> <code>{', '.join(active_meta['fk']) if active_meta['fk'] else 'None'}</code>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_md, tab_codebook, tab_data, tab_schema = st.tabs(
            ["📖 Documentation (.md)", "📚 Codebook", "📊 Excel Data Preview", "⚙️ Column Types & Stats"]
        )

        # Tab 1: Markdown Documentation
        with tab_md:
            if active_bundle["md_exists"]:
                st.caption(f"Source: `{active_meta['md']}`")
            else:
                st.info(
                    f"`{active_meta['md']}` was not found in the directory; displaying structured documentation built from `{active_meta['xlsx']}` (`codebook` sheet)."
                )
            st.markdown(active_bundle["md_text"])

        # Tab 2: Codebook Sheet
        with tab_codebook:
            cb_sheet = active_meta["codebook_sheet"]
            if cb_sheet and cb_sheet in active_sheets:
                cb_df = active_sheets[cb_sheet].dropna(how="all")
                search_cb = st.text_input(
                    "Filter codebook variables or descriptions:",
                    key=f"cb_search_{active_key}",
                    placeholder="e.g., sparc, reaction_time, sus_1...",
                )
                if search_cb:
                    mask = cb_df.apply(
                        lambda row: row.astype(str).str.contains(search_cb, case=False).any(),
                        axis=1,
                    )
                    cb_df = cb_df[mask]
                st.dataframe(cb_df, use_container_width=True, hide_index=True)
            else:
                st.info(
                    f"`{active_meta['xlsx']}` does not contain a separate `codebook` sheet (it is a summary table). See the Documentation or Excel Data Preview tabs."
                )

        # Tab 3: Live Excel Data Preview
        with tab_data:
            sheet_names = list(active_sheets.keys())
            chosen_sheet = st.selectbox(
                "Select Excel Sheet:",
                options=sheet_names,
                key=f"sheet_sel_{active_key}",
            )
            df_preview = active_sheets[chosen_sheet]
            st.caption(f"Shape: {df_preview.shape[0]} rows × {df_preview.shape[1]} columns")
            st.dataframe(df_preview, use_container_width=True, hide_index=True)

        # Tab 4: Schema & Summary Statistics
        with tab_schema:
            primary_df = active_sheets.get(active_meta["data_sheet"], pd.DataFrame())
            if not primary_df.empty:
                schema_rows = []
                for col in primary_df.columns:
                    col_series = primary_df[col]
                    schema_rows.append({
                        "Column": col,
                        "Key Role": (
                            "PK, FK"
                            if (col in active_meta["pk"] and col in active_meta["fk"])
                            else "PK"
                            if col in active_meta["pk"]
                            else "FK"
                            if col in active_meta["fk"]
                            else "-"
                        ),
                        "Data Type": str(col_series.dtype),
                        "Non-Null": int(col_series.notna().sum()),
                        "Nulls": int(col_series.isna().sum()),
                        "Unique Values": int(col_series.nunique()),
                        "Sample Values": ", ".join(map(str, col_series.dropna().unique()[:4])),
                    })
                st.dataframe(pd.DataFrame(schema_rows), use_container_width=True, hide_index=True)

                numeric_cols = primary_df.select_dtypes(include="number").columns
                if len(numeric_cols) > 0:
                    st.markdown("#### Numeric Summary Statistics")
                    st.dataframe(
                        primary_df[numeric_cols].describe().T[["count", "mean", "std", "min", "50%", "max"]],
                        use_container_width=True,
                    )


if __name__ == "__main__":
    main()
