import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network
import tempfile
import os

from data import CHARACTERS, RELATIONSHIPS, EDGE_COLOURS, GROUP_COLOURS
from lineage_tree import (
    build_descendants,
    render_html as render_lineage_html,
    all_ancestors_with_descendants,
)

st.set_page_config(page_title="Bible Knowledge Graph", layout="wide")
st.title("La Sacra Bibbia — Knowledge Graph")
st.caption(f"{len(CHARACTERS)} biblical characters · {len(RELATIONSHIPS)} relationships")

tab_graph, tab_tree = st.tabs(["Knowledge Graph", "Family Tree"])

# ══════════════════════════════════════════════════════════════════
#  SIDEBAR — shared filters & settings
# ══════════════════════════════════════════════════════════════════
st.sidebar.header("Filters")

all_groups = sorted(set(c["group"] for c in CHARACTERS.values()))
selected_groups = st.sidebar.multiselect(
    "Character type", all_groups, default=all_groups
)

testament_filter = st.sidebar.radio(
    "Testament", ["All", "Old Testament", "New Testament"]
)
testament_map = {"All": None, "Old Testament": "OT", "New Testament": "NT"}
t_filter = testament_map[testament_filter]

all_rel_types = sorted(set(r for _, _, r in RELATIONSHIPS))
selected_rels = st.sidebar.multiselect(
    "Relationship type", all_rel_types, default=all_rel_types
)

search = st.sidebar.text_input("Search character").strip()

st.sidebar.markdown("---")
st.sidebar.header("Graph settings")
graph_height = st.sidebar.slider("Graph height (px)", 400, 1200, 800, 50)
physics_enabled = st.sidebar.checkbox("Physics simulation", value=True)
gravity = st.sidebar.slider("Gravity", -300, 0, -80, 10)
spring_length = st.sidebar.slider("Spring length", 50, 500, 200, 25)
show_labels = st.sidebar.checkbox("Show edge labels", value=False)

# ══════════════════════════════════════════════════════════════════
#  FILTER LOGIC
# ══════════════════════════════════════════════════════════════════
base_chars = {
    name for name, info in CHARACTERS.items()
    if info["group"] in selected_groups
    and (t_filter is None or info["testament"] == t_filter)
}

if search:
    matched = {n for n in base_chars if search.lower() in n.lower()}
    neighbours = set()
    for s, t, r in RELATIONSHIPS:
        if s in matched and t in CHARACTERS:
            neighbours.add(t)
        if t in matched and s in CHARACTERS:
            neighbours.add(s)
    visible_chars = matched | neighbours
else:
    visible_chars = base_chars

valid_rels = [
    (s, t, r) for s, t, r in RELATIONSHIPS
    if s in CHARACTERS and t in CHARACTERS
    and s in visible_chars and t in visible_chars
    and r in selected_rels
]

# ══════════════════════════════════════════════════════════════════
#  HELPER — render a pyvis network as HTML component
# ══════════════════════════════════════════════════════════════════
CUSTOM_CSS = """
<style>
.vis-navigation .vis-button {
    background-color: rgba(50, 50, 80, 0.8) !important;
    border: 1px solid #555 !important;
    border-radius: 4px !important;
}
.vis-navigation .vis-button:hover {
    background-color: rgba(80, 80, 120, 0.9) !important;
}
div.vis-tooltip {
    background-color: #2d2d44 !important;
    color: #ffffff !important;
    border: 1px solid #555 !important;
    border-radius: 6px !important;
    padding: 8px 12px !important;
    font-family: sans-serif !important;
    font-size: 13px !important;
}
</style>
"""

def render_network(net, height):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        net.save_graph(f.name)
        tmp_path = f.name
    with open(tmp_path, "r") as f:
        html = f.read()
    html = html.replace("</head>", CUSTOM_CSS + "</head>")
    components.html(html, height=height + 50, scrolling=False)
    os.unlink(tmp_path)

# Key figures get larger nodes
KEY_FIGURES = {
    "Jesus": 45, "Abraham": 35, "Moses": 35, "David": 35,
    "Mary": 30, "Peter": 30, "Paul": 30, "Solomon": 28,
    "Jacob": 28, "Joseph": 25, "Elijah": 25, "Isaiah": 25,
    "Noah": 25, "Daniel": 25, "Adam": 25,
}

# ══════════════════════════════════════════════════════════════════
#  TAB 1 — Knowledge Graph
# ══════════════════════════════════════════════════════════════════
with tab_graph:
    net = Network(
        height=f"{graph_height}px",
        width="100%",
        directed=True,
        bgcolor="#1a1a2e",
        font_color="#ffffff",
        select_menu=False,
        filter_menu=False,
    )

    for name in visible_chars:
        info = CHARACTERS[name]
        size = KEY_FIGURES.get(name, 15)
        colour = GROUP_COLOURS.get(info["group"], "#95A5A6")
        title = f"<b>{name}</b><br>{info['desc']}<br><i>{info['group'].title()} — {'Old' if info['testament'] == 'OT' else 'New'} Testament</i>"
        net.add_node(
            name, label=name, size=size, color=colour, title=title,
            font={"size": 12, "color": "#eeeeee"},
            borderWidth=2, borderWidthSelected=4,
        )

    for source, target, rel in valid_rels:
        is_spouse = rel == "spouse"
        colour = "#FF6B81" if is_spouse else EDGE_COLOURS.get(rel, "#555555")
        net.add_edge(
            source, target, title=rel,
            label="spouse" if is_spouse else (rel if show_labels else ""),
            color=colour,
            width=4 if is_spouse else 1.5,
            arrows="" if is_spouse else "to",
            dashes=[8, 4] if is_spouse else False,
            font={"size": 10, "color": "#FF6B81", "align": "middle"} if is_spouse else (
                {"size": 8, "color": "#aaaaaa", "align": "middle"} if show_labels else {"size": 0}
            ),
            smooth={"type": "continuous"},
        )

    net.set_options(f"""
    {{
      "interaction": {{
        "navigationButtons": true,
        "keyboard": {{ "enabled": true, "speed": {{ "x": 10, "y": 10, "zoom": 0.03 }} }},
        "zoomView": true, "dragView": true, "hover": true,
        "tooltipDelay": 100, "zoomSpeed": 0.6
      }},
      "physics": {{
        "enabled": {str(physics_enabled).lower()},
        "barnesHut": {{
          "gravitationalConstant": {gravity}, "centralGravity": 0.3,
          "springLength": {spring_length}, "springConstant": 0.04,
          "damping": 0.09, "avoidOverlap": 0.2
        }},
        "stabilization": {{ "enabled": true, "iterations": 200, "updateInterval": 25 }}
      }},
      "nodes": {{ "shape": "dot", "scaling": {{ "min": 10, "max": 50 }} }},
      "edges": {{ "smooth": {{ "type": "continuous", "forceDirection": "none" }}, "selectionWidth": 3 }}
    }}
    """)

    col1, col2 = st.columns([5, 1])

    with col1:
        render_network(net, graph_height)
        st.caption("**Zoom:** scroll wheel or +/- buttons · **Pan:** click & drag · **Keyboard:** arrow keys to pan, +/- to zoom")

    with col2:
        st.markdown("### Legend")
        for group, colour in GROUP_COLOURS.items():
            count = sum(1 for n in visible_chars if CHARACTERS[n]["group"] == group)
            if count > 0:
                st.markdown(
                    f'<span style="color:{colour}; font-size:18px;">&#9679;</span> {group.title()} ({count})',
                    unsafe_allow_html=True,
                )
        st.markdown("---")
        st.markdown(f"**Visible nodes:** {len(visible_chars)}")
        st.markdown(f"**Visible edges:** {len(valid_rels)}")

# ══════════════════════════════════════════════════════════════════
#  TAB 2 — Family Tree (hierarchical parent/ancestor view)
# ══════════════════════════════════════════════════════════════════
with tab_tree:
    st.subheader("Family Tree")

    tree_view = st.radio(
        "View",
        ["Lineage view (classic boxed tree)", "Graph view (network)"],
        horizontal=True,
        key="tree_view_mode",
    )

  # ──────────────────────────────────────────────────────────────────
  #  LINEAGE VIEW — bespoke generation-banded classic family tree
  # ──────────────────────────────────────────────────────────────────
if tree_view == "Lineage view (classic boxed tree)":
    with tab_tree:
        LINEAGE_PRESETS = {
            "Adam → Noah (Primeval)": ("Adam", 10),
            "Adam → Jesus (full)": ("Adam", 65),
            "Noah → his sons (Table of Nations)": ("Noah", 2),
            "Shem → Abraham (Gen 11)": ("Shem", 10),
            "Abraham → Jacob (Patriarchs)": ("Abraham", 3),
            "Abraham → Jesus (Matt 1)": ("Abraham", 45),
            "Jacob & his 12 sons": ("Jacob", 1),
            "Esau → Edomite chiefs": ("Esau", 3),
            "Judah → David": ("Judah", 10),
            "Levi → Moses, Aaron & Korah": ("Levi", 5),
            "David → Solomon → Rehoboam": ("David", 3),
            "Kings of Judah (Solomon onward)": ("Solomon", 20),
            "Kings of Israel (Northern)": ("Jeroboam I", 8),
            "Jeconiah → Joseph of Nazareth (Matt 1:12-16)": ("Jehoiachin", 14),
            "Herod the Great": ("Herod the Great", 3),
        }

        src_col, pick_col, depth_col = st.columns([1.2, 2, 1])
        with src_col:
            lineage_source = st.radio(
                "Start from",
                ["Preset lineage", "Pick an ancestor"],
                key="lineage_source",
            )

        if lineage_source == "Preset lineage":
            with pick_col:
                preset_name = st.selectbox(
                    "Lineage", list(LINEAGE_PRESETS.keys()), key="lineage_preset"
                )
            root_name, depth = LINEAGE_PRESETS[preset_name]
            with depth_col:
                depth = st.slider(
                    "Generations", 1, 70, depth, key="lineage_preset_depth"
                )
        else:
            ancestor_choices = all_ancestors_with_descendants(CHARACTERS, RELATIONSHIPS)
            default_idx = (
                ancestor_choices.index("Abraham") if "Abraham" in ancestor_choices else 0
            )
            with pick_col:
                root_name = st.selectbox(
                    "Starting ancestor",
                    ancestor_choices,
                    index=default_idx,
                    key="lineage_root",
                )
            with depth_col:
                depth = st.slider(
                    "Generations deep", 1, 70, 4, key="lineage_depth"
                )

        height_cap = st.slider(
            "Max height (px)", 400, 1600, 900, 50, key="lineage_height"
        )

        tree = build_descendants(root_name, depth, CHARACTERS, RELATIONSHIPS)
        html, _ = render_lineage_html(tree, CHARACTERS, height_cap=height_cap)
        components.html(html, height=height_cap + 8, scrolling=False)

        st.markdown(
            '<span style="color:#5DADE2;font-size:16px;">&#9679;</span> Male / '
            '<span style="color:#F1948A;font-size:16px;">&#9679;</span> Female · '
            '<span style="color:#5DADE2;">━━</span> Parent → Child · '
            '<span style="color:#FF6B81;">╌ ❤ ╌</span> Spouse · '
            '<span style="color:#F5C518;">▭</span> Root ancestor',
            unsafe_allow_html=True,
        )
        if tree and tree["nodes"]:
            st.caption(
                f"{len(tree['nodes'])} descendants of **{root_name}** "
                f"across {max(n['gen'] for n in tree['nodes'].values()) + 1} generations · "
                "**scroll wheel** to zoom · **click & drag** to pan · "
                "toolbar: − / + / fit-to-width / reset"
            )

  # ──────────────────────────────────────────────────────────────────
  #  GRAPH VIEW — existing pyvis hierarchical tree
  # ──────────────────────────────────────────────────────────────────
elif tree_view == "Graph view (network)":
  with tab_tree:
    FAMILY_RELS = {"parent", "ancestor"}

    # Collect all parent/ancestor edges
    family_edges = [
        (s, t, r) for s, t, r in RELATIONSHIPS
        if r in FAMILY_RELS and s in CHARACTERS and t in CHARACTERS
    ]

    # Collect all people who appear in family edges
    family_people = set()
    for s, t, r in family_edges:
        family_people.add(s)
        family_people.add(t)

    # Add spouse edges to show couples side-by-side
    spouse_edges = [
        (s, t, r) for s, t, r in RELATIONSHIPS
        if r == "spouse" and s in family_people and t in family_people
    ]

    # Apply search filter to family tree too
    if search:
        matched_family = {n for n in family_people if search.lower() in n.lower()}
        family_neighbours = set()
        for s, t, r in family_edges + spouse_edges:
            if s in matched_family:
                family_neighbours.add(t)
            if t in matched_family:
                family_neighbours.add(s)
        family_visible = matched_family | family_neighbours
    else:
        family_visible = family_people

    # Select family line
    family_lines = {
        "All families": None,
        "Adam → Noah (Primeval)": ["Adam", "Seth", "Enoch", "Methuselah", "Lamech", "Noah", "Shem", "Ham", "Japheth"],
        "Abraham → Jacob (Patriarchs)": ["Abraham", "Sarah", "Hagar", "Isaac", "Rebekah", "Ishmael", "Jacob", "Esau", "Leah", "Rachel", "Laban"],
        "Jacob's 12 Sons (Tribes)": ["Jacob", "Leah", "Rachel", "Reuben", "Simeon", "Levi", "Judah", "Dan", "Naphtali", "Gad", "Asher", "Issachar", "Zebulun", "Joseph", "Benjamin", "Dinah"],
        "Joseph → Egypt": ["Jacob", "Rachel", "Joseph", "Asenath", "Ephraim", "Manasseh", "Benjamin"],
        "Judah → David": ["Judah", "Tamar", "Boaz", "Ruth", "Jesse", "David"],
        "David's family": ["David", "Bathsheba", "Michal", "Abigail", "Solomon", "Absalom", "Amnon", "Adonijah", "Tamar daughter of David", "Nathan"],
        "Kings of Judah": ["Solomon", "Rehoboam", "Abijah", "Asa", "Jehoshaphat", "Jehoram of Judah", "Ahaziah of Judah", "Joash of Judah", "Amaziah", "Uzziah", "Jotham", "Ahaz", "Hezekiah", "Manasseh of Judah", "Amon", "Josiah", "Jehoahaz of Judah", "Jehoiakim", "Jehoiachin", "Zedekiah"],
        "Kings of Israel (North)": ["Jeroboam I", "Nadab of Israel", "Baasha", "Elah", "Zimri", "Omri", "Ahab", "Jezebel", "Ahaziah of Israel", "Joram of Israel", "Jehu", "Jehoahaz of Israel", "Jehoash of Israel", "Jeroboam II", "Zechariah of Israel", "Shallum", "Menahem", "Pekahiah", "Pekah", "Hoshea"],
        "Ahab & Jezebel": ["Omri", "Ahab", "Jezebel", "Ahaziah of Israel", "Joram of Israel"],
        "Moses & Aaron": ["Levi", "Moses", "Zipporah", "Jethro", "Aaron", "Miriam", "Nadab", "Abihu", "Eleazar", "Phinehas"],
        "Herod & Jesus": ["Herod the Great", "Jesus", "Mary", "Joseph of Nazareth", "Elizabeth", "Zechariah the priest", "John the Baptist", "James the Just"],
        "Maccabees": ["Mattathias", "Judas Maccabeus", "Eleazar Maccabeus"],
        "Noah's sons": ["Noah", "Shem", "Ham", "Japheth", "Nimrod"],
    }

    selected_line = st.selectbox("Family line", list(family_lines.keys()))
    line_members = family_lines[selected_line]

    tree_height = st.slider("Tree height (px)", 400, 1500, 900, 50, key="tree_h")
    show_spouse = st.checkbox("Show spouse connections", value=True)

    # Build the tree network
    tree = Network(
        height=f"{tree_height}px",
        width="100%",
        directed=True,
        bgcolor="#1a1a2e",
        font_color="#ffffff",
        select_menu=False,
        filter_menu=False,
    )

    # Determine which people to include
    if line_members is not None:
        tree_people = {p for p in line_members if p in CHARACTERS}
    else:
        tree_people = family_visible

    # Auto-include spouses of visible people so marriages always show
    if show_spouse:
        all_spouse_edges = [
            (s, t, r) for s, t, r in RELATIONSHIPS
            if r == "spouse" and s in CHARACTERS and t in CHARACTERS
        ]
        spouses_to_add = set()
        for s, t, r in all_spouse_edges:
            if s in tree_people and t not in tree_people:
                spouses_to_add.add(t)
            if t in tree_people and s not in tree_people:
                spouses_to_add.add(s)
        tree_people = tree_people | spouses_to_add

    # Filter edges — include parent edges where a spouse is parent too
    tree_edges = [
        (s, t, r) for s, t, r in family_edges
        if s in tree_people and t in tree_people
    ]

    if show_spouse:
        tree_spouse = [
            (s, t, r) for s, t, r in all_spouse_edges
            if s in tree_people and t in tree_people
        ]
    else:
        tree_spouse = []

    # Only include people that have at least one connection
    connected = set()
    for s, t, r in tree_edges + tree_spouse:
        connected.add(s)
        connected.add(t)
    tree_people = tree_people & connected if connected else tree_people

    # Gender colours for family tree
    MALE_COLOUR = "#5DADE2"
    FEMALE_COLOUR = "#F1948A"
    FEMALE_GROUPS = {"matriarch", "queen"}

    for name in tree_people:
        if name not in CHARACTERS:
            continue
        info = CHARACTERS[name]
        is_female = info["group"] in FEMALE_GROUPS
        colour = FEMALE_COLOUR if is_female else MALE_COLOUR
        size = KEY_FIGURES.get(name, 18)
        shape = "dot"
        title = f"<b>{name}</b><br>{info['desc']}"
        tree.add_node(
            name, label=name, size=size, color=colour, title=title,
            shape=shape, font={"size": 14, "color": "#eeeeee"},
            borderWidth=2,
        )

    for s, t, r in tree_edges:
        label = "ancestor" if r == "ancestor" else ""
        tree.add_edge(
            s, t, color="#5DADE2", width=2.5, arrows="to",
            label=label, font={"size": 9, "color": "#aaaaaa"},
            dashes=True if r == "ancestor" else False,
            title=r,
        )

    for s, t, r in tree_spouse:
        tree.add_edge(
            s, t, color="#FF6B81", width=4, arrows="",
            dashes=[8, 4], title="spouse",
            label="\u2764", font={"size": 14, "color": "#FF6B81"},
        )

    tree.set_options(f"""
    {{
      "interaction": {{
        "navigationButtons": true,
        "keyboard": {{ "enabled": true, "speed": {{ "x": 10, "y": 10, "zoom": 0.03 }} }},
        "zoomView": true, "dragView": true, "hover": true,
        "tooltipDelay": 100, "zoomSpeed": 0.6
      }},
      "layout": {{
        "hierarchical": {{
          "enabled": true,
          "direction": "UD",
          "sortMethod": "directed",
          "levelSeparation": 150,
          "nodeSpacing": 180,
          "treeSpacing": 250,
          "blockShifting": true,
          "edgeMinimization": true,
          "parentCentralization": true
        }}
      }},
      "physics": {{
        "enabled": false
      }},
      "nodes": {{ "shape": "dot" }},
      "edges": {{
        "smooth": {{ "type": "cubicBezier", "forceDirection": "vertical", "roundness": 0.4 }}
      }}
    }}
    """)

    render_network(tree, tree_height)

    tc1, tc2 = st.columns(2)
    with tc1:
        st.caption("**Zoom:** scroll wheel or +/- buttons · **Pan:** click & drag")
        st.markdown(
            '<span style="color:#5DADE2; font-size:16px;">&#9679;</span> Male / '
            '<span style="color:#F1948A; font-size:16px;">&#9679;</span> Female · '
            '<span style="color:#5DADE2;">━━</span> Parent → Child · '
            '<span style="color:#5DADE2;">╌╌╌</span> Ancestor · '
            '<span style="color:#FF6B81;">━ ❤ ━</span> Spouse',
            unsafe_allow_html=True,
        )
    with tc2:
        st.metric("People", len(tree_people))
        st.metric("Connections", len(tree_edges) + len(tree_spouse))
