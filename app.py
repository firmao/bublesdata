import datetime
import io
import os
import re
from pathlib import Path
from urllib.parse import quote
import numpy as np
import pandas as pd
import plotly.express as px
from rdflib import Graph, Literal, Namespace, RDF, RDFS, OWL, XSD, URIRef
from rdflib.namespace import DCTERMS, PROV, SDO
from scipy import stats
import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

# ---------------------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OpenHeal TEA — ER Model, Data Analyzer & FAIR KG",
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
        "kg_class": "Participant",
        "uri_prefix": "participant",
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
        "kg_class": "CohortSummaryRow",
        "uri_prefix": "cohort-summary",
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
        "kg_class": "GameMatch",
        "uri_prefix": "match",
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
        "kg_class": "MatchKinematics",
        "uri_prefix": "kinematics-match",
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
        "kg_class": "KinematicWindow",
        "uri_prefix": "kinematics-window",
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
        "kg_class": "SusAssessment",
        "uri_prefix": "sus-assessment",
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
        "predicate": "hasMatch",
        "description": "Each participant plays 2–3 valid matches on Day 1 (GE & GC) and 0–3 matches on Day 2 (GE only).",
    },
    {
        "source": "01_participants",
        "target": "09_sus",
        "label": "1 : 1 (id_study)",
        "cardinality": "1 : 1",
        "join_key": "id_study",
        "predicate": "hasSusAssessment",
        "description": "Each participant completes one System Usability Scale (SUS) assessment at the end of their final session.",
    },
    {
        "source": "01_participants",
        "target": "02_cohort",
        "label": "Aggregates to (n=76)",
        "cardinality": "N : 1 (Derived)",
        "join_key": "group, sex, age, n_matches_*",
        "predicate": "aggregatedInCohortSummary",
        "description": "Manuscript Table 1 and ABNT sex × group contingency table are computed directly from 01_participants.",
    },
    {
        "source": "03_matches",
        "target": "04_kinematics_match",
        "label": "1 : 1 (id_match)",
        "cardinality": "1 : 1",
        "join_key": "id_match",
        "predicate": "hasWholeMatchKinematics",
        "description": "Every valid match in 03_matches (n = 333) has one corresponding whole-match kinematic summary row.",
    },
    {
        "source": "04_kinematics_match",
        "target": "05_kinematics_window",
        "label": "1 : 6 (id_match)",
        "cardinality": "1 : N (1 : 6)",
        "join_key": "id_match",
        "predicate": "hasKinematicWindow",
        "description": "Each whole match (n = 333) is partitioned into 6 contiguous equal-length time windows (~12s each, n = 1,998).",
    },
    {
        "source": "01_participants",
        "target": "04_kinematics_match",
        "label": "1 : N (id_study)",
        "cardinality": "1 : N (Denormalized FK)",
        "join_key": "id_study",
        "predicate": "hasMatchKinematics",
        "description": "Denormalized participant foreign key allowing direct joins between participant demographics and match kinematics.",
    },
    {
        "source": "01_participants",
        "target": "05_kinematics_window",
        "label": "1 : N (id_study)",
        "cardinality": "1 : N (Denormalized FK)",
        "join_key": "id_study",
        "predicate": "hasParticipantWindow",
        "description": "Denormalized participant foreign key linking participants directly to windowed kinematic segments.",
    },
]

OH = Namespace("https://w3id.org/openheal-tea/ontology#")
RES = Namespace("https://w3id.org/openheal-tea/resource/")


# ---------------------------------------------------------------------------
# FAIR Knowledge Graph Builder, Schema Extractor & Natural-Language Query Engine
# ---------------------------------------------------------------------------
def _slugify(val: object) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", str(val).strip())
    return s.strip("_") or "item"


def _literal_from_value(val: object):
    if pd.isna(val):
        return None
    if isinstance(val, (int, np.integer)):
        return Literal(int(val), datatype=XSD.integer)
    if isinstance(val, (float, np.floating)):
        if np.isnan(val) or np.isinf(val):
            return None
        return Literal(float(val), datatype=XSD.double)
    if isinstance(val, (bool, np.bool_)):
        return Literal(bool(val), datatype=XSD.boolean)
    return Literal(str(val), datatype=XSD.string)


def build_fair_knowledge_graph(
    loaded_data: dict,
    base_uri: str = "https://w3id.org/openheal-tea/resource/",
    ontology_uri: str = "https://w3id.org/openheal-tea/ontology#",
    include_codebook: bool = True,
    include_derived_tables: bool = True,
    license_url: str = "https://creativecommons.org/licenses/by/4.0/",
) -> tuple[Graph, dict]:
    """
    Dynamically converts all ER tables, relationships, and codebook metadata into an
    rdflib Knowledge Graph adhering to FAIR principles (Findable, Accessible,
    Interoperable, Reusable).
    """
    res_ns = Namespace(base_uri if base_uri.endswith(("/", "#")) else f"{base_uri}/")
    oh_ns = Namespace(ontology_uri if ontology_uri.endswith(("/", "#")) else f"{ontology_uri}#")

    g = Graph()
    g.bind("oh", oh_ns)
    g.bind("res", res_ns)
    g.bind("dcterms", DCTERMS)
    g.bind("prov", PROV)
    g.bind("schema", SDO)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    dataset_uri = res_ns["dataset/openheal-tea-er"]
    activity_uri = res_ns["activity/dynamic-er-to-fair-kg"]

    g.add((dataset_uri, RDF.type, SDO.Dataset))
    g.add((dataset_uri, RDF.type, OWL.Ontology))
    g.add((dataset_uri, DCTERMS.title, Literal("OpenHeal TEA Entity-Relationship Knowledge Graph", lang="en")))
    g.add((
        dataset_uri,
        DCTERMS.description,
        Literal(
            "FAIR Knowledge Graph dynamically generated from the OpenHeal TEA study relational tables "
            "(participants, cohort summary, matches, whole-match kinematics, windowed kinematics, and SUS).",
            lang="en",
        ),
    ))
    g.add((dataset_uri, DCTERMS.identifier, Literal(str(dataset_uri), datatype=XSD.anyURI)))
    g.add((dataset_uri, DCTERMS.license, URIRef(license_url)))
    g.add((
        dataset_uri,
        DCTERMS.accessRights,
        Literal("Accessible via RDF serializations (Turtle, JSON-LD, N-Triples) generated from ER sources.", lang="en"),
    ))
    g.add((dataset_uri, DCTERMS.conformsTo, URIRef("https://www.w3.org/TR/rdf12-concepts/")))
    g.add((dataset_uri, PROV.wasGeneratedBy, activity_uri))

    g.add((activity_uri, RDF.type, PROV.Activity))
    g.add((activity_uri, PROV.endedAtTime, Literal(now_iso, datatype=XSD.dateTime)))
    g.add((activity_uri, RDFS.label, Literal("Dynamic ER-to-FAIR-KG Transformation", lang="en")))

    participant_uris = {}
    match_uris = {}
    kin_match_uris = {}

    stats_summary = {
        "entities_processed": 0,
        "instances_created": 0,
        "data_triples": 0,
        "link_triples": 0,
        "codebook_triples": 0,
        "total_triples": 0,
        "ontology_uri": str(oh_ns),
        "resource_uri": str(res_ns),
    }

    for entity_key, meta in ENTITY_CONFIG.items():
        if entity_key not in loaded_data or not loaded_data[entity_key]["xlsx_exists"]:
            continue
        if not include_derived_tables and "Summary" in meta["category"]:
            continue

        bundle = loaded_data[entity_key]
        sheets = bundle["sheets"]
        data_sheet_name = meta["data_sheet"]
        if data_sheet_name not in sheets:
            continue

        df = sheets[data_sheet_name]
        class_uri = oh_ns[meta["kg_class"]]
        source_uri = res_ns[f"source/{_slugify(meta['xlsx'])}"]

        g.add((class_uri, RDF.type, OWL.Class))
        g.add((class_uri, RDFS.label, Literal(meta["kg_class"], lang="en")))
        g.add((class_uri, RDFS.comment, Literal(f"{entity_key}: {meta['subtitle']}", lang="en")))
        g.add((source_uri, RDF.type, PROV.Entity))
        g.add((source_uri, RDFS.label, Literal(meta["xlsx"])))

        stats_summary["entities_processed"] += 1

        cb_sheet_name = meta.get("codebook_sheet")
        if include_codebook and cb_sheet_name and cb_sheet_name in sheets:
            cb_df = sheets[cb_sheet_name]
            if not cb_df.empty and "column" in cb_df.columns:
                for _, cb_row in cb_df.iterrows():
                    col_name = cb_row.get("column")
                    if pd.isna(col_name) or str(col_name).strip().lower() in ("", "notes"):
                        continue
                    col_str = str(col_name).strip()
                    prop_uri = oh_ns[_slugify(col_str)]
                    g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
                    g.add((prop_uri, RDFS.domain, class_uri))
                    g.add((prop_uri, RDFS.label, Literal(col_str)))
                    before_cnt = len(g)

                    if "description" in cb_row and pd.notna(cb_row["description"]):
                        g.add((prop_uri, DCTERMS.description, Literal(str(cb_row["description"]), lang="en")))
                    for unit_key in ("unit / range", "scale / range"):
                        if unit_key in cb_row and pd.notna(cb_row[unit_key]):
                            g.add((prop_uri, oh_ns.unitOrRange, Literal(str(cb_row[unit_key]))))
                    for interp_key in ("interpretation", "interpretation / notes", "computation / direction"):
                        if interp_key in cb_row and pd.notna(cb_row[interp_key]):
                            g.add((prop_uri, oh_ns.interpretation, Literal(str(cb_row[interp_key]))))

                    stats_summary["codebook_triples"] += len(g) - before_cnt

        for idx, row in df.iterrows():
            if entity_key == "01_participants" and "id_study" in row:
                inst_id = _slugify(row["id_study"])
                inst_uri = res_ns[f"{meta['uri_prefix']}/{inst_id}"]
                participant_uris[row["id_study"]] = inst_uri
            elif entity_key in ("03_matches", "04_kinematics_match") and "id_match" in row:
                inst_id = _slugify(row["id_match"])
                inst_uri = res_ns[f"{meta['uri_prefix']}/{inst_id}"]
                if entity_key == "03_matches":
                    match_uris[row["id_match"]] = inst_uri
                else:
                    kin_match_uris[row["id_match"]] = inst_uri
            elif entity_key == "05_kinematics_window" and "id_match" in row and "window" in row:
                inst_id = f"{_slugify(row['id_match'])}_w{_slugify(row['window'])}"
                inst_uri = res_ns[f"{meta['uri_prefix']}/{inst_id}"]
            elif entity_key == "09_sus" and "id_study" in row:
                inst_id = _slugify(row["id_study"])
                inst_uri = res_ns[f"{meta['uri_prefix']}/{inst_id}"]
            else:
                pk_val = row.get(meta["pk"][0], idx) if meta["pk"] else idx
                inst_id = f"{idx}_{_slugify(pk_val)}"
                inst_uri = res_ns[f"{meta['uri_prefix']}/{inst_id}"]

            g.add((inst_uri, RDF.type, class_uri))
            g.add((inst_uri, DCTERMS.isPartOf, dataset_uri))
            g.add((inst_uri, PROV.wasDerivedFrom, source_uri))
            g.add((inst_uri, RDFS.label, Literal(f"{meta['kg_class']} {inst_id}")))
            stats_summary["instances_created"] += 1

            for col in df.columns:
                lit = _literal_from_value(row[col])
                if lit is None:
                    continue
                prop_uri = oh_ns[_slugify(col)]
                if (prop_uri, RDF.type, None) not in g:
                    g.add((prop_uri, RDF.type, OWL.DatatypeProperty))
                    g.add((prop_uri, RDFS.domain, class_uri))
                g.add((inst_uri, prop_uri, lit))
                stats_summary["data_triples"] += 1

            if entity_key in ("03_matches", "04_kinematics_match", "05_kinematics_window", "09_sus"):
                id_s = row.get("id_study")
                if pd.notna(id_s) and id_s in participant_uris:
                    p_uri = participant_uris[id_s]
                    if entity_key == "03_matches":
                        g.add((p_uri, oh_ns.hasMatch, inst_uri))
                        g.add((inst_uri, oh_ns.hasParticipant, p_uri))
                        stats_summary["link_triples"] += 2
                    elif entity_key == "04_kinematics_match":
                        g.add((p_uri, oh_ns.hasMatchKinematics, inst_uri))
                        g.add((inst_uri, oh_ns.hasParticipant, p_uri))
                        stats_summary["link_triples"] += 2
                    elif entity_key == "05_kinematics_window":
                        g.add((p_uri, oh_ns.hasParticipantWindow, inst_uri))
                        g.add((inst_uri, oh_ns.hasParticipant, p_uri))
                        stats_summary["link_triples"] += 2
                    elif entity_key == "09_sus":
                        g.add((p_uri, oh_ns.hasSusAssessment, inst_uri))
                        g.add((inst_uri, oh_ns.hasParticipant, p_uri))
                        stats_summary["link_triples"] += 2

            if entity_key == "04_kinematics_match" and "id_match" in row:
                m_id = row["id_match"]
                if pd.notna(m_id) and m_id in match_uris:
                    m_uri = match_uris[m_id]
                    g.add((m_uri, oh_ns.hasWholeMatchKinematics, inst_uri))
                    g.add((inst_uri, oh_ns.kinematicsOfMatch, m_uri))
                    stats_summary["link_triples"] += 2

            if entity_key == "05_kinematics_window" and "id_match" in row:
                m_id = row["id_match"]
                if pd.notna(m_id) and m_id in kin_match_uris:
                    km_uri = kin_match_uris[m_id]
                    g.add((km_uri, oh_ns.hasKinematicWindow, inst_uri))
                    g.add((inst_uri, oh_ns.windowOfMatchKinematics, km_uri))
                    stats_summary["link_triples"] += 2
                if pd.notna(m_id) and m_id in match_uris:
                    m_uri = match_uris[m_id]
                    g.add((inst_uri, oh_ns.windowOfMatch, m_uri))
                    stats_summary["link_triples"] += 1

    for rel in RELATIONSHIPS:
        pred_uri = oh_ns[_slugify(rel["predicate"])]
        src_cls = oh_ns[ENTITY_CONFIG[rel["source"]]["kg_class"]]
        tgt_cls = oh_ns[ENTITY_CONFIG[rel["target"]]["kg_class"]]
        g.add((pred_uri, RDF.type, OWL.ObjectProperty))
        g.add((pred_uri, RDFS.domain, src_cls))
        g.add((pred_uri, RDFS.range, tgt_cls))
        g.add((pred_uri, RDFS.comment, Literal(f"{rel['cardinality']} via {rel['join_key']}: {rel['description']}")))

    stats_summary["total_triples"] = len(g)
    return g, stats_summary


def extract_ontology_schema(kg_graph: Graph, ontology_uri: str) -> dict:
    """Extracts OWL Classes, ObjectProperties, DatatypeProperties, and a schema-only RDF Graph."""
    oh_ns = Namespace(ontology_uri if ontology_uri.endswith(("/", "#")) else f"{ontology_uri}#")
    schema_graph = Graph()
    schema_graph.bind("oh", oh_ns)
    schema_graph.bind("owl", OWL)
    schema_graph.bind("rdfs", RDFS)
    schema_graph.bind("dcterms", DCTERMS)

    classes = {}
    for cls_uri in kg_graph.subjects(RDF.type, OWL.Class):
        if not str(cls_uri).startswith(str(oh_ns)):
            continue
        cls_name = str(cls_uri).replace(str(oh_ns), "")
        comment = next(kg_graph.objects(cls_uri, RDFS.comment), None)
        inst_count = sum(1 for _ in kg_graph.subjects(RDF.type, cls_uri))
        classes[cls_name] = {
            "uri": str(cls_uri),
            "comment": str(comment) if comment else "",
            "instances": inst_count,
            "datatype_props": [],
        }
        for p, o in kg_graph.predicate_objects(cls_uri):
            if p in (RDF.type, RDFS.label, RDFS.comment):
                continue
            schema_graph.add((cls_uri, p, o))

    datatype_props = []
    for prop_uri in kg_graph.subjects(RDF.type, OWL.DatatypeProperty):
        p_name = str(prop_uri).replace(str(oh_ns), "")
        domains = [str(d).replace(str(oh_ns), "") for d in kg_graph.objects(prop_uri, RDFS.domain)]
        desc = next(kg_graph.objects(prop_uri, DCTERMS.description), None)
        unit = next(kg_graph.objects(prop_uri, oh_ns.unitOrRange), None)
        interp = next(kg_graph.objects(prop_uri, oh_ns.interpretation), None)

        for p, o in kg_graph.predicate_objects(prop_uri):
            schema_graph.add((prop_uri, p, o))

        prop_record = {
            "property": f"oh:{p_name}",
            "name": p_name,
            "domains": domains,
            "domain_str": ", ".join(domains) if domains else "-",
            "unit_or_range": str(unit) if unit else "",
            "description": str(desc) if desc else "",
            "interpretation": str(interp) if interp else "",
        }
        datatype_props.append(prop_record)
        for d in domains:
            if d in classes:
                classes[d]["datatype_props"].append(prop_record)

    object_props = []
    for op_uri in kg_graph.subjects(RDF.type, OWL.ObjectProperty):
        op_name = str(op_uri).replace(str(oh_ns), "")
        domains = [str(d).replace(str(oh_ns), "") for d in kg_graph.objects(op_uri, RDFS.domain)]
        ranges = [str(r).replace(str(oh_ns), "") for r in kg_graph.objects(op_uri, RDFS.range)]
        comment = next(kg_graph.objects(op_uri, RDFS.comment), None)

        for p, o in kg_graph.predicate_objects(op_uri):
            schema_graph.add((op_uri, p, o))

        for d in domains or [None]:
            for r in ranges or [None]:
                object_props.append({
                    "predicate": f"oh:{op_name}",
                    "name": op_name,
                    "domain": d or "-",
                    "range": r or "-",
                    "comment": str(comment) if comment else "",
                })

    return {
        "classes": classes,
        "datatype_props": datatype_props,
        "object_props": object_props,
        "schema_graph": schema_graph,
    }


def render_kg_schema_viewer(kg_graph: Graph, ontology_uri: str):
    """Renders an interactive graph plot and structured inspection of the FAIR KG ontology/schema."""
    schema_info = extract_ontology_schema(kg_graph, ontology_uri)
    classes = schema_info["classes"]
    datatype_props = schema_info["datatype_props"]
    object_props = schema_info["object_props"]
    schema_graph: Graph = schema_info["schema_graph"]

    class_colors = {
        "Participant": "#1E88E5",
        "CohortSummaryRow": "#7CB342",
        "GameMatch": "#FB8C00",
        "MatchKinematics": "#8E24AA",
        "KinematicWindow": "#D81B60",
        "SusAssessment": "#00897B",
    }

    with st.container(border=True):
        st.markdown("### 🧬 FAIR Knowledge Graph Schema / Ontology Explorer")
        st.caption(
            f"Ontology Namespace: `{ontology_uri}` — Visualizing **`{len(classes)}`** `owl:Class` nodes, "
            f"**`{len(object_props)}`** `owl:ObjectProperty` relations, and **`{len(datatype_props)}`** `owl:DatatypeProperty` attributes."
        )

        s_m1, s_m2, s_m3 = st.columns(3)
        s_m1.metric("OWL Classes", len(classes))
        s_m2.metric("Object Properties (Edges)", len(object_props))
        s_m3.metric("Datatype Properties (Attributes)", len(datatype_props))

        ctl1, ctl2 = st.columns(2)
        show_props_in_nodes = ctl1.checkbox("Show datatype properties inside class boxes", value=True, key="kg_schema_show_props")
        show_denorm_edges = ctl2.checkbox("Show denormalized/secondary object edges", value=True, key="kg_schema_show_sec_edges")

        nodes = []
        for cls_name, c_meta in classes.items():
            color_hex = class_colors.get(cls_name, "#38BDF8")
            prop_names = [p["name"] for p in c_meta["datatype_props"]]
            header = f"◈ oh:{cls_name}\n({c_meta['instances']:,} instances | {len(prop_names)} props)\n" + "─" * 26
            if show_props_in_nodes:
                shown = prop_names[:7]
                body = "\n".join(f"  • {pn}" for pn in shown)
                if len(prop_names) > 7:
                    body += f"\n  ... +{len(prop_names) - 7} more"
                label = f"{header}\n{body}" if body else header
            else:
                label = header

            nodes.append(
                Node(
                    id=cls_name,
                    label=label,
                    shape="box",
                    color={
                        "background": "#0F172A",
                        "border": color_hex,
                        "highlight": {"background": "#1E293B", "border": "#FACC15"},
                    },
                    borderWidth=3,
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
        for op in object_props:
            if op["domain"] not in classes or op["range"] not in classes:
                continue
            is_secondary = any(k in op["name"].lower() for k in ("participant", "matchkinematics", "participantwindow", "windowofmatch", "kinematicsofmatch"))
            if not show_denorm_edges and is_secondary:
                continue
            edges.append(
                Edge(
                    source=op["domain"],
                    target=op["range"],
                    label=op["predicate"],
                    color="#94A3B8" if not is_secondary else "#64748B",
                    dashes=is_secondary,
                    font={"color": "#E2E8F0", "size": 11, "align": "top", "strokeWidth": 0},
                    arrows="to",
                    smooth={"type": "cubicBezier"},
                )
            )

        schema_cfg = Config(
            width="100%",
            height=500,
            directed=True,
            physics=True,
            hierarchical=False,
            nodeHighlightBehavior=True,
            highlightColor="#FACC15",
            collapsible=False,
        )
        agraph(nodes=nodes, edges=edges, config=schema_cfg)

        st.markdown("#### 📋 Ontology Axioms & Vocabulary Reference")
        ax_tab1, ax_tab2, ax_tab3 = st.tabs(["Object Properties (Relations)", "Datatype Properties (Codebook)", "Ontology Turtle (.ttl)"])

        with ax_tab1:
            st.dataframe(pd.DataFrame(object_props)[["predicate", "domain", "range", "comment"]], use_container_width=True, hide_index=True)

        with ax_tab2:
            prop_filter = st.text_input("Filter properties by name, class, or description:", key="kg_schema_prop_filter", placeholder="e.g., sparc, group, sus, Participant...")
            dp_df = pd.DataFrame(datatype_props)[["property", "domain_str", "unit_or_range", "description", "interpretation"]]
            if prop_filter.strip():
                mask = dp_df.apply(lambda r: r.astype(str).str.contains(prop_filter.strip(), case=False).any(), axis=1)
                dp_df = dp_df[mask]
            st.dataframe(dp_df, use_container_width=True, hide_index=True)

        with ax_tab3:
            schema_ttl = schema_graph.serialize(format="turtle")
            st.download_button(
                "⬇️ Download Ontology Schema (.ttl)",
                data=schema_ttl.encode("utf-8"),
                file_name="openheal_tea_ontology_schema.ttl",
                mime="text/turtle",
                use_container_width=True,
            )
            st.code(schema_ttl, language="turtle")


def _extract_kg_schema_catalog(kg_graph: Graph, ontology_uri: str) -> dict:
    """Inspects OWL classes and DatatypeProperties directly from the RDF Knowledge Graph."""
    oh_ns = Namespace(ontology_uri if ontology_uri.endswith(("/", "#")) else f"{ontology_uri}#")
    prop_to_classes = {}
    prop_descriptions = {}
    prop_units = {}

    for prop in kg_graph.subjects(RDF.type, OWL.DatatypeProperty):
        p_local = str(prop).replace(str(oh_ns), "")
        domains = [str(d).replace(str(oh_ns), "") for d in kg_graph.objects(prop, RDFS.domain)]
        prop_to_classes[p_local] = domains
        desc = next(kg_graph.objects(prop, DCTERMS.description), None)
        if desc:
            prop_descriptions[p_local] = str(desc)
        unit = next(kg_graph.objects(prop, oh_ns.unitOrRange), None)
        if unit:
            prop_units[p_local] = str(unit)

    return {
        "prop_to_classes": prop_to_classes,
        "prop_descriptions": prop_descriptions,
        "prop_units": prop_units,
    }


def _sparql_df_from_graph(kg_graph: Graph, sparql_query: str) -> pd.DataFrame:
    """Executes a SPARQL query on the rdflib Graph and converts typed literals into a clean DataFrame."""
    qres = kg_graph.query(sparql_query)
    cols = [str(v) for v in qres.vars] if qres.vars else ["result"]
    parsed_rows = []
    for row in qres:
        row_vals = []
        for cell in row:
            if cell is None:
                row_vals.append(None)
            elif isinstance(cell, Literal):
                row_vals.append(cell.toPython())
            else:
                row_vals.append(str(cell))
        parsed_rows.append(row_vals)
    return pd.DataFrame(parsed_rows, columns=cols)


def query_fair_kg_in_natural_language(
    nl_prompt: str,
    kg_graph: Graph,
    ontology_uri: str = "https://w3id.org/openheal-tea/ontology#",
):
    """
    Translates a natural-language question into a cross-entity SPARQL query against the
    FAIR Knowledge Graph, executes it, computes statistical summaries, and builds a Plotly chart.
    """
    oh_prefix = ontology_uri if ontology_uri.endswith(("/", "#")) else f"{ontology_uri}#"
    catalog = _extract_kg_schema_catalog(kg_graph, oh_prefix)
    prop_to_classes = catalog["prop_to_classes"]
    q_low = nl_prompt.strip().lower()

    all_props = sorted(prop_to_classes.keys(), key=len, reverse=True)
    mentioned_props = [
        p for p in all_props
        if re.search(rf"\b{re.escape(p.lower())}\b", q_low)
    ]

    synonym_map = [
        (r"\b(smoothness|sparc)\b", "sparc_bilateral"),
        (r"\b(jerk|ldlj)\b", "ldlj_bilateral"),
        (r"\b(speed|velocity)\b", "speed_mean_bilateral"),
        (r"\b(path length|trajectory length)\b", "path_length_bilateral"),
        (r"\b(mirror|symmetry)\b", "mirror_score"),
        (r"\b(reaction time|rt)\b", "reaction_time_mean"),
        (r"\b(accuracy|hit rate|hits)\b", "hit_rate"),
        (r"\b(usability|sus score)\b", "sus"),
        (r"\b(idade|age)\b", "age"),
        (r"\b(sexo|sex|gender)\b", "sex"),
        (r"\b(grupo|group|asd|tea|control)\b", "group"),
        (r"\b(fase|phase)\b", "phase"),
        (r"\b(janela|window)\b", "window"),
        (r"\b(dia|day)\b", "day"),
    ]
    for pattern, mapped_prop in synonym_map:
        if mapped_prop in prop_to_classes and mapped_prop not in mentioned_props:
            if re.search(pattern, q_low):
                mentioned_props.append(mapped_prop)

    if any(k in q_low for k in ("codebook", "metadata", "unit", "definition", "meaning", "what is", "o que é", "describe")):
        target_p = mentioned_props[0] if mentioned_props else None
        filter_clause = f'FILTER(LCASE(STR(?property)) = "{target_p.lower()}")' if target_p else ""
        sparql = f"""PREFIX oh: <{oh_prefix}>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dcterms: <http://purl.org/dc/terms/>

SELECT ?property ?domainClass ?description ?unitOrRange ?interpretation
WHERE {{
  ?propUri a owl:DatatypeProperty ;
           rdfs:label ?property ;
           rdfs:domain ?dom .
  BIND(REPLACE(STR(?dom), "^.*#", "") AS ?domainClass)
  OPTIONAL {{ ?propUri dcterms:description ?description . }}
  OPTIONAL {{ ?propUri oh:unitOrRange ?unitOrRange . }}
  OPTIONAL {{ ?propUri oh:interpretation ?interpretation . }}
  {filter_clause}
}}
ORDER BY ?domainClass ?property"""
        res_df = _sparql_df_from_graph(kg_graph, sparql)
        insight = (
            f"**FAIR Codebook Lookup:** Retrieved **{len(res_df)}** ontology property definition(s) directly from RDF metadata."
        )
        return insight, sparql, res_df, None

    if ("sus_1" in q_low or "sus items" in q_low or "items" in q_low) and "sus_1" in prop_to_classes:
        item_triples = "\n  ".join([f"?susNode oh:sus_{i} ?sus_{i} ." for i in range(1, 11)])
        sparql = f"""PREFIX oh: <{oh_prefix}>

SELECT ?id_study ?group {' '.join(f'?sus_{i}' for i in range(1, 11))}
WHERE {{
  ?p a oh:Participant ;
     oh:id_study ?id_study ;
     oh:group ?group ;
     oh:hasSusAssessment ?susNode .
  {item_triples}
}}"""
        raw_df = _sparql_df_from_graph(kg_graph, sparql)
        melted = raw_df.melt(
            id_vars=["id_study", "group"],
            value_vars=[f"sus_{i}" for i in range(1, 11)],
            var_name="Item",
            value_name="Score",
        )
        summary_df = melted.groupby(["Item", "group"], as_index=False)["Score"].agg(mean="mean", sd="std", count="count")
        fig = px.bar(
            summary_df,
            x="Item",
            y="mean",
            error_y="sd",
            color="group",
            barmode="group",
            title="FAIR KG Query: Mean SUS Item Scores (1–5) by Study Group",
            labels={"mean": "Mean Rating (1–5)", "group": "Group"},
            template="plotly_dark",
        )
        insight = "**KG Semantic Analysis:** Mean usability rating across all 10 SUS items (`oh:sus_1`–`oh:sus_10`) joined with `oh:Participant` via `oh:hasSusAssessment`."
        return insight, sparql, summary_df, fig

    class_priority = [
        ("KinematicWindow", "w", "?p oh:hasParticipantWindow ?w ."),
        ("MatchKinematics", "km", "?p oh:hasMatchKinematics ?km ."),
        ("GameMatch", "m", "?p oh:hasMatch ?m ."),
        ("SusAssessment", "s", "?p oh:hasSusAssessment ?s ."),
        ("Participant", "p", ""),
    ]

    selected_class = "Participant"
    selected_var = "p"
    join_pattern = ""

    for cls_name, var_name, link_triple in class_priority:
        cls_props = [p for p in mentioned_props if cls_name in prop_to_classes.get(p, []) and p not in ("id_study", "group", "sex", "age")]
        if cls_props:
            selected_class = cls_name
            selected_var = var_name
            join_pattern = link_triple
            break

    select_vars = ["?id_study", "?group", "?sex", "?age"]
    where_lines = [
        f"?p a oh:Participant ;",
        f"   oh:id_study ?id_study ;",
        f"   oh:group ?group ;",
        f"   oh:sex ?sex ;",
        f"   oh:age ?age .",
    ]

    if selected_class != "Participant":
        where_lines.append(join_pattern)
        where_lines.append(f"?{selected_var} a oh:{selected_class} .")
        if selected_class in ("GameMatch", "MatchKinematics", "KinematicWindow"):
            select_vars.append("?id_match")
            where_lines.append(f"?{selected_var} oh:id_match ?id_match .")
        if selected_class == "KinematicWindow":
            select_vars.extend(["?window", "?phase"])
            where_lines.append(f"?{selected_var} oh:window ?window ; oh:phase ?phase .")
        if selected_class == "GameMatch":
            select_vars.extend(["?day", "?match_number"])
            where_lines.append(f"?{selected_var} oh:day ?day ; oh:match_number ?match_number .")

    for prop in mentioned_props:
        if f"?{prop}" in select_vars:
            continue
        domains = prop_to_classes.get(prop, [])
        if selected_class in domains:
            select_vars.append(f"?{prop}")
            where_lines.append(f"OPTIONAL {{ ?{selected_var} oh:{prop} ?{prop} . }}")
        elif "Participant" in domains:
            select_vars.append(f"?{prop}")
            where_lines.append(f"OPTIONAL {{ ?p oh:{prop} ?{prop} . }}")

    sparql = f"""PREFIX oh: <{oh_prefix}>

SELECT {' '.join(select_vars)}
WHERE {{
  {chr(10) + '  '.join(where_lines)}
}}"""

    df = _sparql_df_from_graph(kg_graph, sparql)
    if df.empty:
        return (
            "The SPARQL query executed cleanly but returned 0 rows. Try mentioning specific variables such as `sparc_bilateral`, `hit_rate`, `reaction_time_mean`, `sus`, or `age`.",
            sparql,
            df,
            None,
        )

    cat_candidates = [c for c in ["group", "sex", "phase", "window", "day", "match_number"] if c in df.columns]
    num_candidates = [
        c for c in mentioned_props
        if c in df.columns and c not in ("id_study", "id_match") and pd.api.types.is_numeric_dtype(df[c])
    ]
    if not num_candidates:
        num_candidates = [
            c for c in df.columns
            if c not in ("id_study", "id_match", "window", "day", "match_number") and pd.api.types.is_numeric_dtype(df[c])
        ]

    if any(k in q_low for k in ("correlat", "scatter", " vs ", "versus", "against", "relationship")) and len(num_candidates) >= 2:
        x_col, y_col = num_candidates[0], num_candidates[1]
        clean = df[[x_col, y_col, "group"]].dropna()
        r_val, p_val = stats.pearsonr(clean[x_col], clean[y_col])
        rho_val, rho_p = stats.spearmanr(clean[x_col], clean[y_col])

        fig = px.scatter(
            clean,
            x=x_col,
            y=y_col,
            color="group",
            trendline="ols",
            title=f"FAIR KG Query: {y_col} vs. {x_col} (r = {r_val:.3f}, ρ = {rho_val:.3f})",
            template="plotly_dark",
            opacity=0.82,
        )
        summary_df = pd.DataFrame([{
            "KG Class": selected_class,
            "X Attribute": f"oh:{x_col}",
            "Y Attribute": f"oh:{y_col}",
            "N": len(clean),
            "Pearson r": round(r_val, 4),
            "Pearson p": round(p_val, 4),
            "Spearman ρ": round(rho_val, 4),
            "Spearman p": round(rho_p, 4),
        }])
        insight = (
            f"**KG Correlation Analysis (`oh:{selected_class}`):** Across **n = {len(clean)}** linked RDF instances, "
            f"`oh:{x_col}` and `oh:{y_col}` exhibit **Pearson r = {r_val:.3f}** (p = {p_val:.4g}) and "
            f"**Spearman ρ = {rho_val:.3f}** (p = {rho_p:.4g})."
        )
        return insight, sparql, summary_df, fig

    mentioned_cats = [c for c in mentioned_props if c in cat_candidates]
    group_dim = mentioned_cats[0] if mentioned_cats else ("group" if "group" in df.columns else None)

    if num_candidates and group_dim:
        metric_col = num_candidates[0]
        clean = df[[group_dim, metric_col]].dropna()
        summary_df = (
            clean.groupby(group_dim)[metric_col]
            .agg(
                n="count",
                mean="mean",
                sd="std",
                median="median",
                q1=lambda s: s.quantile(0.25),
                q3=lambda s: s.quantile(0.75),
                min="min",
                max="max",
            )
            .reset_index()
        )

        stat_text = ""
        levels = sorted(clean[group_dim].unique())
        if len(levels) == 2:
            g1 = clean[clean[group_dim] == levels[0]][metric_col]
            g2 = clean[clean[group_dim] == levels[1]][metric_col]
            t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)
            _, u_pval = stats.mannwhitneyu(g1, g2)
            stat_text = f" | Welch's *t* = {t_stat:.2f} (p = {p_val:.4g}), Mann–Whitney *p* = {u_pval:.4g}"

        unit_label = catalog["prop_units"].get(metric_col, "")
        y_axis_title = f"{metric_col} ({unit_label})" if unit_label else metric_col

        if group_dim in ("window", "day", "match_number") and "group" in df.columns:
            trend_df = df.dropna(subset=[group_dim, metric_col]).groupby([group_dim, "group"], as_index=False)[metric_col].mean()
            fig = px.line(
                trend_df,
                x=group_dim,
                y=metric_col,
                color="group",
                markers=True,
                title=f"FAIR KG Query: Mean {metric_col} across {group_dim} by Group",
                labels={metric_col: y_axis_title},
                template="plotly_dark",
            )
        else:
            fig = px.box(
                clean,
                x=group_dim,
                y=metric_col,
                color=group_dim,
                points="all",
                title=f"FAIR KG Query: {metric_col} by {group_dim} (oh:{selected_class})",
                labels={metric_col: y_axis_title},
                template="plotly_dark",
            )

        insight = (
            f"**KG Semantic Analysis (`oh:{selected_class}`):** Evaluated **`oh:{metric_col}`** stratified by "
            f"**`oh:{group_dim}`** (n = {len(clean)} RDF triples){stat_text}."
        )
        return insight, sparql, summary_df, fig

    if len(mentioned_cats) >= 2:
        c1, c2 = mentioned_cats[0], mentioned_cats[1]
        ct = pd.crosstab(df[c1], df[c2], margins=True, margins_name="Total").reset_index()
        plot_df = df.groupby([c1, c2]).size().reset_index(name="Count")
        fig = px.bar(
            plot_df,
            x=c1,
            y="Count",
            color=c2,
            barmode="group",
            title=f"FAIR KG Query: Instance Counts by {c1} and {c2}",
            template="plotly_dark",
        )
        insight = f"**KG Contingency Analysis:** Cross-tabulation of **`oh:{c1}`** × **`oh:{c2}`** across n = {len(df)} instances."
        return insight, sparql, ct, fig

    counts = df.groupby(["group", "sex"]).size().reset_index(name="Participants")
    fig = px.bar(
        counts,
        x="group",
        y="Participants",
        color="sex",
        barmode="group",
        title="FAIR KG Query: Analytic Cohort Composition (oh:Participant)",
        template="plotly_dark",
    )
    insight = (
        f"**KG Overview (`oh:{selected_class}`):** Retrieved **{len(df)}** linked records via SPARQL. "
        "Include specific metrics (e.g., `sparc_bilateral`, `hit_rate`, `reaction_time_mean`, `sus`, `age`) for targeted statistical tests."
    )
    return insight, sparql, df.head(50), fig


# ---------------------------------------------------------------------------
# File Fingerprinting & Reactive Data Loaders
# ---------------------------------------------------------------------------
def get_files_signature(base_dir: str) -> tuple:
    """Returns a tuple of (filename, mtime_ns, size) for all .xlsx and .md files so cache auto-invalidates on disk changes."""
    base_path = Path(base_dir)
    sig = []
    for meta in ENTITY_CONFIG.values():
        for fname in (meta["xlsx"], meta["md"]):
            fpath = base_path / fname
            if fpath.exists():
                stat = fpath.stat()
                sig.append((fname, stat.st_mtime_ns, stat.st_size))
            else:
                sig.append((fname, None, None))
    return tuple(sig)


@st.cache_data
def load_all_datasets(base_dir: str, files_signature: tuple):
    """Loads all Excel sheets, codebooks, and Markdown files; automatically refreshes when files_signature changes."""
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

        if md_path.exists():
            md_text = md_path.read_text(encoding="utf-8")
        else:
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
        f"*{meta['subtitle']}* — Documentação gerada automaticamente a partir da aba `codebook` de `{meta['xlsx']}`.",
        "",
        "## Desenho e Chaves",
        f"- **Registros (linhas):** {len(data_df)}",
        f"- **Colunas:** {len(data_df.columns)}",
        f"- **Chave Primária (PK):** `{', '.join(meta['pk'])}`",
        f"- **Chaves Estrangeiras (FK):** `{', '.join(meta['fk']) if meta['fk'] else 'Nenhuma'}`",
        "",
    ]

    if not cb_df.empty:
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
# FAIR Knowledge Graph Panel (with Schema/Ontology Plot & NL Query Studio)
# ---------------------------------------------------------------------------
def render_fair_kg_modal_or_section(data_dir: str, loaded_data: dict):
    """Renders FAIR KG conversion options, execution button, schema plot button, NL query studio, and downloads."""
    st.markdown("---")
    st.subheader("🕸️ FAIR Knowledge Graph Converter & Natural Language Query")
    st.caption(
        "Dynamically transforms all ER entities, foreign-key links, and codebook semantics into a FAIR-compliant RDF graph, "
        "plots its ontology/schema, and lets you query the Knowledge Graph in natural language."
    )

    opt_c1, opt_c2, opt_c3 = st.columns(3)
    with opt_c1:
        base_uri = st.text_input("Resource Base URI", value="https://w3id.org/openheal-tea/resource/")
    with opt_c2:
        ontology_uri = st.text_input("Ontology Namespace URI", value="https://w3id.org/openheal-tea/ontology#")
    with opt_c3:
        license_url = st.text_input("FAIR License URI (R1.1)", value="https://creativecommons.org/licenses/by/4.0/")

    chk_c1, chk_c2 = st.columns(2)
    with chk_c1:
        include_codebook = st.checkbox("Include Codebook & Variable Semantics (R1.3)", value=True)
    with chk_c2:
        include_derived = st.checkbox("Include Derived Summary Tables (02_cohort)", value=True)

    btn_col1, btn_col2, btn_col3 = st.columns(3)
    with btn_col1:
        convert_clicked = st.button(
            "🕸️ Convert ER to FAIR Knowledge Graph",
            type="primary",
            use_container_width=True,
            key="btn_convert_fair_kg",
        )
    with btn_col2:
        show_schema_clicked = st.button(
            "🧬 Show KG Schema / Ontology",
            type="secondary",
            use_container_width=True,
            key="btn_show_kg_schema",
            help="Plot and inspect the Knowledge Graph OWL classes, object properties, and datatype attributes.",
        )
    with btn_col3:
        ask_nl_clicked = st.button(
            "💬 Ask in Natural Language",
            type="secondary",
            use_container_width=True,
            key="btn_open_nl_kg",
            help="Query the FAIR Knowledge Graph in natural language to generate charts, printable visualizations, and statistical analyses.",
        )

    if convert_clicked or ((show_schema_clicked or ask_nl_clicked) and "fair_kg_graph" not in st.session_state):
        with st.spinner("Building FAIR RDF Knowledge Graph across all ER tables..."):
            kg_graph, kg_stats = build_fair_knowledge_graph(
                loaded_data=loaded_data,
                base_uri=base_uri,
                ontology_uri=ontology_uri,
                include_codebook=include_codebook,
                include_derived_tables=include_derived,
                license_url=license_url,
            )
            st.session_state["fair_kg_graph"] = kg_graph
            st.session_state["fair_kg_stats"] = kg_stats

    if show_schema_clicked:
        st.session_state["show_kg_schema_viewer"] = not st.session_state.get("show_kg_schema_viewer", False) if False else True

    if ask_nl_clicked:
        st.session_state["show_kg_nl_studio"] = True

    if st.session_state.get("show_kg_schema_viewer") and "fair_kg_graph" in st.session_state:
        kg_graph: Graph = st.session_state["fair_kg_graph"]
        kg_stats: dict = st.session_state["fair_kg_stats"]
        render_kg_schema_viewer(kg_graph, kg_stats.get("ontology_uri", ontology_uri))

    if st.session_state.get("show_kg_nl_studio") and "fair_kg_graph" in st.session_state:
        kg_graph: Graph = st.session_state["fair_kg_graph"]
        kg_stats: dict = st.session_state["fair_kg_stats"]
        active_ont_uri = kg_stats.get("ontology_uri", ontology_uri)

        with st.container(border=True):
            st.markdown("### 💬 Ask the FAIR Knowledge Graph in Natural Language")
            st.caption(
                "Queries are translated into SPARQL over the RDF graph (joining `Participant`, `GameMatch`, `MatchKinematics`, "
                "`KinematicWindow`, and `SusAssessment` via semantic object links) with instant statistical analysis and printable charts."
            )

            sample_prompts = [
                "Compare sparc_bilateral by group",
                "Compare hit_rate by group",
                "Correlation between hit_rate and reaction_time_mean",
                "Compare sus by group",
                "Mean SUS items by group",
                "Compare sparc_bilateral across phase",
                "Count participants by group and sex",
                "Show codebook definition for sparc_bilateral",
            ]

            if "kg_nl_prompt" not in st.session_state:
                st.session_state["kg_nl_prompt"] = sample_prompts[0]

            st.caption("One-click example questions:")
            ex_cols = st.columns(2)
            for idx, prompt_txt in enumerate(sample_prompts):
                if ex_cols[idx % 2].button(f"✨ {prompt_txt}", key=f"kg_ex_{idx}", use_container_width=True):
                    st.session_state["kg_nl_prompt"] = prompt_txt

            q_in_col, q_btn_col = st.columns([3.5, 1.1])
            with q_in_col:
                nl_question = st.text_input(
                    "Enter your question about the Knowledge Graph:",
                    key="kg_nl_prompt",
                    placeholder="e.g., Compare sparc_bilateral by group, or Correlation between speed_mean_bilateral and path_length_bilateral",
                )
            with q_btn_col:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                run_nl = st.button("🚀 Run NL Query", type="primary", use_container_width=True, key="btn_exec_kg_nl")

            if nl_question.strip() or run_nl:
                insight_msg, generated_sparql, result_df, result_fig = query_fair_kg_in_natural_language(
                    nl_prompt=nl_question,
                    kg_graph=kg_graph,
                    ontology_uri=active_ont_uri,
                )

                st.success(insight_msg)

                with st.expander("🧾 View Executed SPARQL Query (Provenance & Reproducibility)", expanded=False):
                    st.code(generated_sparql, language="sparql")

                if result_fig is not None:
                    result_fig.update_layout(height=420, margin=dict(l=25, r=25, t=55, b=30))
                    st.plotly_chart(
                        result_fig,
                        use_container_width=True,
                        config={
                            "displaylogo": False,
                            "toImageButtonOptions": {
                                "format": "png",
                                "filename": "openheal_kg_chart",
                                "height": 700,
                                "width": 1100,
                                "scale": 2,
                            },
                        },
                    )

                    html_buf = io.StringIO()
                    result_fig.write_html(html_buf, include_plotlyjs="cdn", full_html=True)
                    printable_html = html_buf.getvalue().replace(
                        "</body>",
                        "<div style='text-align:center;margin:16px;font-family:sans-serif;'>"
                        "<button onclick='window.print()' style='padding:10px 20px;font-size:15px;cursor:pointer;'>🖨️ Print Chart</button>"
                        "</div></body>",
                    )

                    exp_c1, exp_c2 = st.columns(2)
                    exp_c1.download_button(
                        "🖨️ Download Printable Chart (.html)",
                        data=printable_html.encode("utf-8"),
                        file_name="openheal_kg_printable_chart.html",
                        mime="text/html",
                        use_container_width=True,
                        help="Opens a standalone print-ready chart page with a Print button (also supports PNG download via the chart camera icon).",
                    )
                    if result_df is not None and not result_df.empty:
                        exp_c2.download_button(
                            "⬇️ Download Analysis Table (.csv)",
                            data=result_df.to_csv(index=False).encode("utf-8"),
                            file_name="openheal_kg_analysis.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )

                if result_df is not None and not result_df.empty:
                    st.markdown("#### 📊 Statistical Analysis & SPARQL Result Table")
                    st.dataframe(result_df, use_container_width=True, hide_index=True)

    if "fair_kg_graph" in st.session_state and "fair_kg_stats" in st.session_state:
        kg_graph: Graph = st.session_state["fair_kg_graph"]
        kg_stats: dict = st.session_state["fair_kg_stats"]

        m_cols = st.columns(5)
        m_cols[0].metric("Total RDF Triples", f"{kg_stats['total_triples']:,}")
        m_cols[1].metric("Typed Instances", f"{kg_stats['instances_created']:,}")
        m_cols[2].metric("Data Property Triples", f"{kg_stats['data_triples']:,}")
        m_cols[3].metric("ER Object Link Triples", f"{kg_stats['link_triples']:,}")
        m_cols[4].metric("Codebook Triples", f"{kg_stats['codebook_triples']:,}")

        with st.expander("✅ FAIR Principles Conformance Checklist", expanded=False):
            fair_df = pd.DataFrame([
                {"Principle": "Findable (F1–F3)", "Implementation": "Globally unique HTTP URIs per Dataset, Class, Property, and Instance; explicit dcterms:identifier."},
                {"Principle": "Accessible (A1)", "Implementation": "Exportable in standard open RDF formats (Turtle, JSON-LD, N-Triples) with dcterms:accessRights."},
                {"Principle": "Interoperable (I1–I3)", "Implementation": "Uses RDF/RDFS/OWL/XSD/DCTERMS/PROV/Schema.org vocabularies and typed ER foreign-key object links."},
                {"Principle": "Reusable (R1–R1.3)", "Implementation": "Includes PROV-O provenance, source workbook links, CC-BY license metadata, and codebook units/ranges."},
            ])
            st.dataframe(fair_df, use_container_width=True, hide_index=True)

        ttl_str = kg_graph.serialize(format="turtle")
        jsonld_str = kg_graph.serialize(format="json-ld", indent=2)
        nt_str = kg_graph.serialize(format="nt")

        dl1, dl2, dl3, dl4 = st.columns(4)
        dl1.download_button(
            "⬇️ Download Turtle (.ttl)",
            data=ttl_str.encode("utf-8"),
            file_name="openheal_tea_fair_kg.ttl",
            mime="text/turtle",
            use_container_width=True,
        )
        dl2.download_button(
            "⬇️ Download JSON-LD (.jsonld)",
            data=jsonld_str.encode("utf-8"),
            file_name="openheal_tea_fair_kg.jsonld",
            mime="application/ld+json",
            use_container_width=True,
        )
        dl3.download_button(
            "⬇️ Download N-Triples (.nt)",
            data=nt_str.encode("utf-8"),
            file_name="openheal_tea_fair_kg.nt",
            mime="application/n-triples",
            use_container_width=True,
        )
        if dl4.button("💾 Save .ttl to Dataset Dir", use_container_width=True):
            out_path = Path(data_dir) / "openheal_tea_fair_kg.ttl"
            out_path.write_text(ttl_str, encoding="utf-8")
            st.success(f"Saved Knowledge Graph to `{out_path}`")

        kg_tab_sparql, kg_tab_ttl = st.tabs(["🔎 Raw SPARQL Editor", "📜 Turtle Serialization Preview"])
        with kg_tab_sparql:
            default_sparql = """PREFIX oh: <https://w3id.org/openheal-tea/ontology#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class (COUNT(?s) AS ?instance_count)
WHERE {
  ?s a ?class .
  ?class a <http://www.w3.org/2002/07/owl#Class> .
}
GROUP BY ?class
ORDER BY DESC(?instance_count)"""
            sparql_query = st.text_area("SPARQL SELECT Query:", value=default_sparql, height=160, key="fair_sparql_input")
            if st.button("▶ Run SPARQL", key="btn_run_fair_sparql"):
                try:
                    q_df = _sparql_df_from_graph(kg_graph, sparql_query)
                    st.dataframe(q_df, use_container_width=True, hide_index=True)
                except Exception as exc:
                    st.error(f"SPARQL error: {exc}")

        with kg_tab_ttl:
            st.code("\n".join(ttl_str.splitlines()[:120]), language="turtle")


# ---------------------------------------------------------------------------
# Google Sheets-Style "Analyze Data" Engine
# ---------------------------------------------------------------------------
def get_working_dataframe(
    entity_key: str,
    sheet_name: str,
    active_tables: dict,
    enrich_with_cohort: bool = True,
) -> pd.DataFrame:
    """Returns the selected table, optionally enriched with cohort group/sex/age via id_study."""
    df = active_tables[entity_key][sheet_name].copy()
    if (
        enrich_with_cohort
        and entity_key != "01_participants"
        and "id_study" in df.columns
        and "01_participants" in active_tables
    ):
        p_df = active_tables["01_participants"]["data"]
        join_cols = [c for c in ["id_study", "group", "sex", "age"] if c in p_df.columns and (c == "id_study" or c not in df.columns)]
        if len(join_cols) > 1:
            df = df.merge(p_df[join_cols], on="id_study", how="left")
    return df


def classify_columns(df: pd.DataFrame):
    """Separates identifiers, categoricals, and analytical numeric columns."""
    id_cols = [c for c in df.columns if c in ("id_study", "id_match")]
    cat_cols = []
    num_cols = []

    for col in df.columns:
        if col in id_cols:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            if df[col].nunique(dropna=True) <= 6 and col in ("day", "match_number", "moment", "window"):
                cat_cols.append(col)
            else:
                num_cols.append(col)
        else:
            if df[col].nunique(dropna=True) <= 25:
                cat_cols.append(col)

    return id_cols, cat_cols, num_cols


def generate_suggested_questions(entity_key: str, df: pd.DataFrame) -> list[str]:
    """Generates context-aware Google Sheets-style natural language questions for a table."""
    _, cat_cols, num_cols = classify_columns(df)
    suggestions = []

    if entity_key == "01_participants":
        suggestions = [
            "Compare age by group",
            "Count of participants by group and sex",
            "Distribution of age",
            "Compare n_matches_day2 by group",
        ]
    elif entity_key == "02_cohort":
        suggestions = ["Show summary table comparison"]
    elif entity_key == "03_matches":
        suggestions = [
            "Compare hit_rate by group",
            "Compare reaction_time_mean by group",
            "Correlation between hit_rate and reaction_time_mean",
            "Trend of hit_rate across day",
        ]
    elif entity_key == "04_kinematics_match":
        suggestions = [
            "Compare sparc_bilateral by group",
            "Compare speed_mean_bilateral by group",
            "Correlation between speed_mean_bilateral and path_length_bilateral",
            "Compare mirror_score by group",
        ]
    elif entity_key == "05_kinematics_window":
        suggestions = [
            "Compare sparc_bilateral across phase",
            "Compare sparc_bilateral by group",
            "Trend of speed_mean_bilateral across window",
            "Correlation between t_start and sparc_bilateral",
        ]
    elif entity_key == "09_sus":
        suggestions = [
            "Compare sus by group",
            "Distribution of sus",
            "Average score across sus_1 to sus_10 by group",
            "Correlation between age and sus",
        ]

    if not suggestions and num_cols:
        if cat_cols:
            suggestions.append(f"Compare {num_cols[0]} by {cat_cols[0]}")
        suggestions.append(f"Distribution of {num_cols[0]}")
        if len(num_cols) >= 2:
            suggestions.append(f"Correlation between {num_cols[0]} and {num_cols[1]}")

    return suggestions


def answer_natural_language_query(query: str, df: pd.DataFrame):
    """Parses a natural-language data question and returns an insight summary, summary table, and Plotly figure."""
    q = query.strip().lower()
    _, cat_cols, num_cols = classify_columns(df)
    all_cols = list(df.columns)

    mentioned_cols = [
        c for c in sorted(all_cols, key=len, reverse=True)
        if re.search(rf"\b{re.escape(c.lower())}\b", q)
    ]

    if ("sus_1" in q or "items" in q) and all(f"sus_{i}" in df.columns for i in range(1, 11)):
        sus_items = [f"sus_{i}" for i in range(1, 11)]
        if "group" in df.columns:
            melted = df.melt(id_vars=["group"], value_vars=sus_items, var_name="Item", value_name="Score")
            agg = melted.groupby(["Item", "group"], as_index=False)["Score"].mean()
            fig = px.bar(
                agg,
                x="Item",
                y="Score",
                color="group",
                barmode="group",
                title="Mean SUS Item Scores (1–5) by Group",
                template="plotly_dark",
            )
            return "Mean item-level usability ratings across `sus_1` through `sus_10` stratified by `group`.", agg, fig

    if any(k in q for k in ("correlat", "scatter", "versus", " vs ", "against", "relationship between")) and len(mentioned_cols) >= 2:
        x_col, y_col = mentioned_cols[0], mentioned_cols[1]
        if pd.api.types.is_numeric_dtype(df[x_col]) and pd.api.types.is_numeric_dtype(df[y_col]):
            clean = df[[x_col, y_col] + (["group"] if "group" in df.columns else [])].dropna()
            r_val, p_val = stats.pearsonr(clean[x_col], clean[y_col])
            rho_val, rho_p = stats.spearmanr(clean[x_col], clean[y_col])
            color_arg = "group" if "group" in clean.columns else None
            fig = px.scatter(
                clean,
                x=x_col,
                y=y_col,
                color=color_arg,
                trendline="ols",
                title=f"{y_col} vs. {x_col} (Pearson r = {r_val:.3f}, Spearman ρ = {rho_val:.3f})",
                template="plotly_dark",
                opacity=0.8,
            )
            summary_df = pd.DataFrame([{
                "X Variable": x_col,
                "Y Variable": y_col,
                "N": len(clean),
                "Pearson r": round(r_val, 4),
                "Pearson p": round(p_val, 4),
                "Spearman ρ": round(rho_val, 4),
                "Spearman p": round(rho_p, 4),
            }])
            insight = (
                f"**Correlation Insight:** `{x_col}` and `{y_col}` show a Pearson correlation of "
                f"**r = {r_val:.3f}** (p = {p_val:.4g}) and Spearman rank correlation **ρ = {rho_val:.3f}** (p = {rho_p:.4g}) across n = {len(clean)} rows."
            )
            return insight, summary_df, fig

    mentioned_num = [c for c in mentioned_cols if c in num_cols]
    mentioned_cat = [c for c in mentioned_cols if c in cat_cols]

    if mentioned_num and mentioned_cat:
        num_c = mentioned_num[0]
        cat_c = mentioned_cat[0]
        clean = df[[cat_c, num_c]].dropna()
        summary_df = (
            clean.groupby(cat_c)[num_c]
            .agg(
                count="count",
                mean="mean",
                sd="std",
                median="median",
                q1=lambda s: s.quantile(0.25),
                q3=lambda s: s.quantile(0.75),
            )
            .reset_index()
        )
        stat_note = ""
        unique_groups = clean[cat_c].unique()
        if len(unique_groups) == 2:
            g1 = clean[clean[cat_c] == unique_groups[0]][num_c]
            g2 = clean[clean[cat_c] == unique_groups[1]][num_c]
            t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)
            _, u_pval = stats.mannwhitneyu(g1, g2)
            stat_note = f" | Welch's *t* = {t_stat:.2f} (p = {p_val:.4g}), Mann–Whitney *p* = {u_pval:.4g}"

        fig = px.box(
            clean,
            x=cat_c,
            y=num_c,
            color=cat_c,
            points="all",
            title=f"{num_c} by {cat_c}",
            template="plotly_dark",
        )
        insight = f"**Comparison Insight:** Breakdown of **`{num_c}`** across **`{cat_c}`** ({len(unique_groups)} levels, n = {len(clean)}){stat_note}."
        return insight, summary_df, fig

    if len(mentioned_cat) >= 2:
        c1, c2 = mentioned_cat[0], mentioned_cat[1]
        ct = pd.crosstab(df[c1], df[c2], margins=True, margins_name="Total")
        plot_df = df.groupby([c1, c2]).size().reset_index(name="Count")
        fig = px.bar(
            plot_df,
            x=c1,
            y="Count",
            color=c2,
            barmode="group",
            title=f"Record Counts by {c1} and {c2}",
            template="plotly_dark",
        )
        insight = f"**Contingency Insight:** Cross-tabulation of **`{c1}`** × **`{c2}`**."
        return insight, ct.reset_index(), fig

    if mentioned_num:
        num_c = mentioned_num[0]
        clean = df[[num_c] + (["group"] if "group" in df.columns else [])].dropna()
        color_arg = "group" if "group" in clean.columns else None
        fig = px.histogram(
            clean,
            x=num_c,
            color=color_arg,
            marginal="box",
            barmode="overlay",
            title=f"Distribution of {num_c}",
            template="plotly_dark",
        )
        desc = clean[num_c].describe().to_frame().T
        insight = (
            f"**Distribution Insight:** **`{num_c}`** has mean = **{clean[num_c].mean():.3f}** (SD = {clean[num_c].std():.3f}), "
            f"median = **{clean[num_c].median():.3f}** [IQR: {clean[num_c].quantile(0.25):.3f}–{clean[num_c].quantile(0.75):.3f}]."
        )
        return insight, desc, fig

    if mentioned_cat:
        cat_c = mentioned_cat[0]
        counts = df[cat_c].value_counts(dropna=False).reset_index()
        counts.columns = [cat_c, "Count"]
        counts["Percentage (%)"] = (counts["Count"] / len(df) * 100).round(1)
        fig = px.pie(
            counts,
            names=cat_c,
            values="Count",
            hole=0.4,
            title=f"Share of Records by {cat_c}",
            template="plotly_dark",
        )
        insight = f"**Composition Insight:** Frequency breakdown of **`{cat_c}`** across {len(df)} rows."
        return insight, counts, fig

    return (
        "Showing full table summary statistics. Mention any specific column name (e.g., `sparc_bilateral`, `hit_rate`, `age`, `sus`) to generate targeted charts.",
        df.describe(include="all").T.reset_index().rename(columns={"index": "Column"}),
        None,
    )


def generate_auto_insights_cards(entity_key: str, df: pd.DataFrame) -> list[dict]:
    """Automatically discovers top statistical patterns & charts (like Google Sheets 'Analyze Data' feed)."""
    cards = []
    _, cat_cols, num_cols = classify_columns(df)

    if "group" in df.columns and df["group"].nunique() == 2 and len(num_cols) > 0:
        priority_outcomes = [
            "sparc_bilateral",
            "hit_rate",
            "reaction_time_mean",
            "sus",
            "speed_mean_bilateral",
            "age",
        ]
        target_col = next((c for c in priority_outcomes if c in num_cols), num_cols[0])
        clean = df[["group", target_col]].dropna()
        groups = sorted(clean["group"].unique())
        g1 = clean[clean["group"] == groups[0]][target_col]
        g2 = clean[clean["group"] == groups[1]][target_col]
        t_stat, p_val = stats.ttest_ind(g1, g2, equal_var=False)

        fig = px.box(
            clean,
            x="group",
            y=target_col,
            color="group",
            points="all",
            title=f"{target_col} by Group ({groups[0]} vs {groups[1]})",
            template="plotly_dark",
        )
        fig.update_layout(height=340, margin=dict(l=20, r=20, t=45, b=20), showlegend=False)
        cards.append({
            "title": f"Group Comparison: {target_col}",
            "caption": f"{groups[0]} mean = {g1.mean():.3f} vs. {groups[1]} mean = {g2.mean():.3f} (Welch p = {p_val:.4g})",
            "fig": fig,
        })

    if len(num_cols) >= 2:
        candidate_nums = [c for c in num_cols if not c.startswith("sus_")][:12]
        if len(candidate_nums) >= 2:
            corr_matrix = df[candidate_nums].corr(method="pearson").abs()
            arr = corr_matrix.to_numpy(dtype=float, copy=True)
            np.fill_diagonal(arr, 0.0)
            if arr.size > 0 and np.any(np.isfinite(arr)):
                max_idx = np.unravel_index(np.nanargmax(arr), arr.shape)
                c1 = corr_matrix.index[max_idx[0]]
                c2 = corr_matrix.columns[max_idx[1]]
                r_val = df[[c1, c2]].dropna().corr().iloc[0, 1]

                color_col = "group" if "group" in df.columns else None
                fig = px.scatter(
                    df.dropna(subset=[c1, c2]),
                    x=c1,
                    y=c2,
                    color=color_col,
                    trendline="ols",
                    title=f"Strongest Correlation: {c1} vs {c2} (r = {r_val:.2f})",
                    template="plotly_dark",
                )
                fig.update_layout(height=340, margin=dict(l=20, r=20, t=45, b=20))
                cards.append({
                    "title": f"Strongest Linear Association (r = {r_val:.3f})",
                    "caption": f"`{c1}` and `{c2}` exhibit the highest magnitude correlation in this table.",
                    "fig": fig,
                })

    for seq_col in ["phase", "window", "day", "match_number"]:
        if seq_col in df.columns and len(num_cols) > 0:
            outcome = next(
                (c for c in ["sparc_bilateral", "hit_rate", "reaction_time_mean", "speed_mean_bilateral"] if c in num_cols),
                num_cols[0],
            )
            group_keys = [seq_col, "group"] if "group" in df.columns else [seq_col]
            trend_df = df.groupby(group_keys, as_index=False)[outcome].mean()
            fig = px.line(
                trend_df,
                x=seq_col,
                y=outcome,
                color="group" if "group" in df.columns else None,
                markers=True,
                title=f"Mean {outcome} across {seq_col}",
                template="plotly_dark",
            )
            fig.update_layout(height=340, margin=dict(l=20, r=20, t=45, b=20))
            cards.append({
                "title": f"Progression across `{seq_col}`",
                "caption": f"Tracks average `{outcome}` across `{seq_col}` intervals.",
                "fig": fig,
            })
            break

    if len(cards) < 3 and len(num_cols) > 0:
        col0 = num_cols[0]
        fig = px.histogram(
            df.dropna(subset=[col0]),
            x=col0,
            color="group" if "group" in df.columns else None,
            marginal="box",
            title=f"Distribution of {col0}",
            template="plotly_dark",
        )
        fig.update_layout(height=340, margin=dict(l=20, r=20, t=45, b=20))
        cards.append({
            "title": f"Distribution: {col0}",
            "caption": f"Median = {df[col0].median():.3f}, IQR = {df[col0].quantile(0.75) - df[col0].quantile(0.25):.3f}",
            "fig": fig,
        })

    return cards


# ---------------------------------------------------------------------------
# View 1: Google Sheets-Style "Analyze Data" Page
# ---------------------------------------------------------------------------
def render_analyze_data_page(data_dir: str, loaded_data: dict):
    """Renders the dynamic multi-table data analysis workspace in a new browser tab/page."""
    current_sig = get_files_signature(data_dir)
    if st.session_state.get("analyzer_sig") != current_sig:
        st.session_state["analyzer_sig"] = current_sig
        st.session_state["working_tables"] = {
            k: {s_name: s_df.copy() for s_name, s_df in bundle["sheets"].items()}
            for k, bundle in loaded_data.items()
            if bundle["xlsx_exists"]
        }

    active_tables = st.session_state["working_tables"]
    available_entities = list(active_tables.keys())

    nav_col1, nav_col2, nav_col3 = st.columns([1.2, 3.2, 1.2])
    with nav_col1:
        st.link_button("⬅️ Back to ER Model", url=f"?page=er_model&dir={quote(data_dir)}", use_container_width=True)
    with nav_col2:
        st.markdown("## 📊 Analyze Data — Dynamic Multi-Table Explorer")
    with nav_col3:
        if st.button("🔄 Reload from .xlsx", use_container_width=True, help="Discard in-memory edits and re-read Excel files from disk."):
            st.cache_data.clear()
            st.session_state.pop("analyzer_sig", None)
            st.rerun()

    st.caption(
        "Inspired by Google Sheets **Analyze Data**: automatically computes live insights, pivot tables, correlations, "
        "and group comparisons across all `.xlsx` tables—updating immediately whenever any table changes on disk or in the Live Data Editor below."
    )

    st.sidebar.title("📊 Analyze Data Controls")
    selected_entity = st.sidebar.selectbox(
        "Target Table (.xlsx):",
        options=available_entities,
        format_func=lambda k: f"{k} ({ENTITY_CONFIG[k]['subtitle']})",
    )

    sheet_options = list(active_tables[selected_entity].keys())
    selected_sheet = st.sidebar.selectbox("Worksheet Tab:", options=sheet_options)

    enrich_cohort = st.sidebar.checkbox(
        "Auto-join `01_participants` (group, sex, age)",
        value=True,
        help="Automatically joins participant group (GE/GC), sex, and age via id_study so any table can be stratified by study group.",
    )

    df = get_working_dataframe(
        selected_entity,
        selected_sheet,
        active_tables,
        enrich_with_cohort=enrich_cohort,
    )

    st.markdown("### 1. Cross-Table Live Status")
    status_cols = st.columns(len(available_entities))
    for idx, ent_key in enumerate(available_entities):
        primary_s = ENTITY_CONFIG[ent_key]["data_sheet"]
        ent_df = active_tables[ent_key].get(primary_s, pd.DataFrame())
        status_cols[idx].metric(
            label=ent_key,
            value=f"{len(ent_df):,} rows",
            delta=f"{len(ent_df.columns)} cols",
            delta_color="off",
        )

    st.markdown("---")

    left_pane, right_pane = st.columns([1.15, 1.0], gap="large")

    with left_pane:
        tab_editor, tab_pivot, tab_corr = st.tabs(
            ["📝 Live Table Data (Editable)", "📐 Dynamic Pivot Table", "🔥 Correlation Matrix"]
        )

        with tab_editor:
            st.markdown(
                f"Editing **`{selected_entity}.xlsx` → `{selected_sheet}`** ({len(df)} rows × {len(df.columns)} columns). "
                "Any cell edits or added rows immediately update all charts, pivot tables, and insights."
            )
            raw_sheet_df = active_tables[selected_entity][selected_sheet]
            edited_df = st.data_editor(
                raw_sheet_df,
                num_rows="dynamic",
                use_container_width=True,
                height=440,
                key=f"editor_{selected_entity}_{selected_sheet}",
            )

            if not edited_df.equals(raw_sheet_df):
                st.session_state["working_tables"][selected_entity][selected_sheet] = edited_df
                st.rerun()

            btn_save_col, btn_info_col = st.columns([1.3, 2.7])
            with btn_save_col:
                if st.button("💾 Save Edits to .xlsx File", use_container_width=True):
                    target_xlsx = Path(data_dir) / ENTITY_CONFIG[selected_entity]["xlsx"]
                    try:
                        with pd.ExcelWriter(target_xlsx, engine="openpyxl") as writer:
                            for s_name, s_data in st.session_state["working_tables"][selected_entity].items():
                                s_data.to_excel(writer, sheet_name=s_name, index=False)
                        st.cache_data.clear()
                        st.success(f"Saved all sheets to `{target_xlsx.name}`!")
                    except Exception as exc:
                        st.error(f"Could not write to Excel file: {exc}")
            with btn_info_col:
                st.caption("Edits update the analysis immediately in memory; click **Save Edits to persist to disk.")

        with tab_pivot:
            st.markdown("#### Build a Custom Pivot Summary")
            _, cat_cols, num_cols = classify_columns(df)
            all_pivot_dims = cat_cols + [c for c in ["id_study"] if c in df.columns]

            if all_pivot_dims and num_cols:
                p_col1, p_col2 = st.columns(2)
                with p_col1:
                    row_dim = st.selectbox("Rows (Group By):", options=all_pivot_dims, index=0)
                    val_col = st.selectbox("Values (Metric):", options=num_cols, index=0)
                with p_col2:
                    col_dim_opt = ["None"] + [c for c in all_pivot_dims if c != row_dim]
                    col_dim = st.selectbox("Columns (Optional Split):", options=col_dim_opt, index=0)
                    agg_func = st.selectbox("Aggregation:", options=["mean", "median", "std", "count", "min", "max"], index=0)

                if col_dim == "None":
                    piv = df.groupby(row_dim, as_index=False)[val_col].agg(agg_func)
                    piv_fig = px.bar(
                        piv,
                        x=row_dim,
                        y=val_col,
                        color=row_dim,
                        title=f"{agg_func.title()} of {val_col} by {row_dim}",
                        template="plotly_dark",
                    )
                else:
                    piv = pd.pivot_table(
                        df,
                        index=row_dim,
                        columns=col_dim,
                        values=val_col,
                        aggfunc=agg_func,
                    ).reset_index()
                    melted_piv = df.groupby([row_dim, col_dim], as_index=False)[val_col].agg(agg_func)
                    piv_fig = px.bar(
                        melted_piv,
                        x=row_dim,
                        y=val_col,
                        color=col_dim,
                        barmode="group",
                        title=f"{agg_func.title()} of {val_col} by {row_dim} × {col_dim}",
                        template="plotly_dark",
                    )

                st.dataframe(piv, use_container_width=True, hide_index=True)
                st.plotly_chart(piv_fig, use_container_width=True)
            else:
                st.info("This worksheet does not have enough numeric and categorical columns for a pivot table.")

        with tab_corr:
            _, _, num_cols = classify_columns(df)
            if len(num_cols) >= 2:
                selected_corr_cols = st.multiselect(
                    "Select numeric variables for correlation heatmap:",
                    options=num_cols,
                    default=num_cols[:min(10, len(num_cols))],
                )
                corr_method = st.radio("Method:", ["pearson", "spearman"], horizontal=True)
                if len(selected_corr_cols) >= 2:
                    cmat = df[selected_corr_cols].corr(method=corr_method)
                    heatmap = px.imshow(
                        cmat,
                        text_auto=".2f",
                        color_continuous_scale="RdBu_r",
                        zmin=-1,
                        zmax=1,
                        title=f"{corr_method.title()} Correlation Matrix ({selected_entity})",
                        template="plotly_dark",
                    )
                    heatmap.update_layout(height=500)
                    st.plotly_chart(heatmap, use_container_width=True)
            else:
                st.info("Fewer than 2 numeric columns available in this worksheet.")

    with right_pane:
        st.markdown(
            """
            <div style="padding: 12px 16px; border-radius: 8px; border-left: 5px solid #38BDF8; background-color: rgba(30, 41, 59, 0.55); margin-bottom: 12px;">
                <h3 style="margin: 0;">✨ Analyze Data — Automated Insights</h3>
                <p style="margin: 4px 0 0 0; font-size: 0.9em; opacity: 0.85;">
                    Ask a question about your data or explore automatically detected patterns below.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        suggestions = generate_suggested_questions(selected_entity, df)
        q_state_key = f"nl_query_{selected_entity}_{selected_sheet}"
        if q_state_key not in st.session_state:
            st.session_state[q_state_key] = suggestions[0] if suggestions else ""

        if suggestions:
            st.caption("Suggested questions:")
            chip_cols = st.columns(2)
            for i, sug in enumerate(suggestions):
                if chip_cols[i % 2].button(f"💡 {sug}", key=f"chip_{selected_entity}_{selected_sheet}_{i}", use_container_width=True):
                    st.session_state[q_state_key] = sug

        user_query = st.text_input(
            "Ask a question about this table:",
            key=q_state_key,
            placeholder="e.g., Compare sparc_bilateral by group, or Correlation between hit_rate and reaction_time_mean",
        )

        if user_query.strip():
            insight_text, result_table, result_fig = answer_natural_language_query(user_query, df)
            st.success(insight_text)
            if result_fig is not None:
                result_fig.update_layout(height=360, margin=dict(l=20, r=20, t=45, b=20))
                st.plotly_chart(result_fig, use_container_width=True)
            if result_table is not None and not result_table.empty:
                st.dataframe(result_table, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🔍 Auto-Discovered Insights Feed")
        auto_cards = generate_auto_insights_cards(selected_entity, df)
        if auto_cards:
            for card in auto_cards:
                with st.container(border=True):
                    st.markdown(f"**")
                    st.caption(card["caption"])
                    st.plotly_chart(card["fig"], use_container_width=True)
        else:
            st.info("Select a data worksheet to view automated visual insights.")


# ---------------------------------------------------------------------------
# View 2: Interactive Entity-Relationship Diagram & Documentation Explorer
# ---------------------------------------------------------------------------
def render_er_model_page(data_dir: str, loaded_data: dict):
    """Renders the primary ER diagram, FAIR KG converter, and Markdown documentation explorer."""
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

    head_col, action_col = st.columns([3.5, 1.2])
    with head_col:
        st.title("OpenHeal TEA — Interactive Entity-Relationship Explorer")
        st.caption(
            "Click any entity node in the diagram (or select from the sidebar) to inspect its Markdown documentation, "
            "variable codebook, live Excel records, or convert the ER model into a FAIR Knowledge Graph."
        )
    with action_col:
        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
        st.link_button(
            "📊 Analyze data",
            url=f"?page=analyze_data&dir={quote(data_dir)}",
            type="primary",
            use_container_width=True,
            help="Opens a new webpage with live, dynamic data analysis across all tables.",
        )

    kpi_cols = st.columns(5)
    p_rows = len(loaded_data["01_participants"]["sheets"].get("data", []))
    m_rows = len(loaded_data["03_matches"]["sheets"].get("data", []))
    kw_rows = len(loaded_data["05_kinematics_window"]["sheets"].get("data", []))
    sus_rows = len(loaded_data["09_sus"]["sheets"].get("data", []))

    kpi_cols[0].metric("Entities (.xlsx)", f"{found_xlsx} Tables")
    kpi_cols[1].metric("Participants (01)", f"{p_rows} (38 GE / 38 GC)")
    kpi_cols[2].metric("Valid Matches (03 & 04)", f"{m_rows}")
    kpi_cols[3].metric("Kinematic Windows (05)", f"{kw_rows:,}")
    kpi_cols[4].metric("SUS Questionnaires (09)", f"{sus_rows}")

    st.markdown("---")

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

        with st.expander("🔗 Schema Relationships & Referential Integrity Audit", expanded=False):
            st.markdown("#### Active Foreign Key Relationships")
            rel_df = pd.DataFrame(RELATIONSHIPS)[
                ["source", "target", "cardinality", "join_key", "description"]
            ]
            st.dataframe(rel_df, use_container_width=True, hide_index=True)

            st.markdown("#### Live Excel Key Integrity Verification")
            integrity_df = compute_referential_integrity(loaded_data)
            st.dataframe(integrity_df, use_container_width=True, hide_index=True)

        # FAIR Knowledge Graph Converter, Schema Plotter & Natural Language Query Studio
        render_fair_kg_modal_or_section(data_dir, loaded_data)

    with col_doc:
        active_key = st.session_state["selected_entity"]
        active_bundle = loaded_data[active_key]
        active_meta = active_bundle["meta"]
        active_sheets = active_bundle["sheets"]

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

        with tab_md:
            if active_bundle["md_exists"]:
                st.caption(f"Source: `{active_meta['md']}`")
            else:
                st.info(
                    f"`{active_meta['md']}` was not found in the directory; displaying structured documentation built from `{active_meta['xlsx']}` (`codebook` sheet)."
                )
            st.markdown(active_bundle["md_text"])

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


# ---------------------------------------------------------------------------
# Entrypoint & Query-Param Page Router
# ---------------------------------------------------------------------------
def main():
    query_params = st.query_params
    active_page = query_params.get("page", "er_model")
    default_dir = query_params.get("dir", ".")

    st.sidebar.title("🧩 OpenHeal Navigation")
    data_dir = st.sidebar.text_input("Dataset Directory", value=default_dir)

    if not os.path.isdir(data_dir):
        st.error(f"Directory not found: `{data_dir}`")
        return

    files_sig = get_files_signature(data_dir)
    loaded_data = load_all_datasets(data_dir, files_sig)

    if active_page == "analyze_data":
        render_analyze_data_page(data_dir, loaded_data)
    else:
        render_er_model_page(data_dir, loaded_data)


if __name__ == "__main__":
    main()