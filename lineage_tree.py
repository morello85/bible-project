"""Bespoke classic family tree renderer.

Builds a descendants tree from `parent` edges starting at a root character,
then lays it out as a generation-banded SVG with rounded-rect boxes,
right-angle parent-child connectors and dashed spouse links.
"""

from collections import defaultdict
from html import escape

# ── layout constants (px) ──────────────────────────────────────────────
BOX_W = 150
BOX_H = 58
SPOUSE_GAP = 30
SIBLING_GAP = 38
GEN_GAP = 110
MARGIN_X = 30
MARGIN_Y = 30
GEN_LABEL_W = 70

FEMALE_GROUPS = {"matriarch", "queen"}


# ── tree construction ──────────────────────────────────────────────────
def build_descendants(root, depth, characters, relationships):
    """BFS down `parent` edges from root, capped at `depth` generations.

    Returns {"root": name, "nodes": {name: {gen, children, spouses}}} or None.
    """
    if root not in characters:
        return None

    children_of = defaultdict(list)
    spouses_of = defaultdict(list)
    for s, t, r in relationships:
        if s not in characters or t not in characters:
            continue
        if r == "parent":
            if t not in children_of[s]:
                children_of[s].append(t)
        elif r == "spouse":
            if t not in spouses_of[s]:
                spouses_of[s].append(t)
            if s not in spouses_of[t]:
                spouses_of[t].append(s)

    nodes = {}
    queue = [(root, 0)]
    while queue:
        name, gen = queue.pop(0)
        if name in nodes or gen > depth:
            continue
        nodes[name] = {"gen": gen, "children": [], "spouses": []}
        if gen < depth:
            for child in children_of[name]:
                if child not in nodes:
                    queue.append((child, gen + 1))

    for name, info in nodes.items():
        info["children"] = [c for c in children_of[name] if c in nodes]
        info["spouses"] = [
            sp for sp in spouses_of[name]
            if sp in characters and sp not in nodes
        ]

    return {"root": root, "nodes": nodes}


def all_ancestors_with_descendants(characters, relationships):
    """Characters who appear as the parent in a `parent` edge — valid roots."""
    return sorted({
        s for s, t, r in relationships
        if r == "parent" and s in characters and t in characters
    })


# ── layout ─────────────────────────────────────────────────────────────
def _layout(tree):
    nodes = tree["nodes"]
    root = tree["root"]
    widths = {}

    def calc_width(name):
        if name in widths:
            return widths[name]
        node = nodes[name]
        n_sp = len(node["spouses"])
        unit_w = (1 + n_sp) * BOX_W + n_sp * SPOUSE_GAP
        children = node["children"]
        if not children:
            widths[name] = unit_w
            return unit_w
        cw_sum = sum(calc_width(c) for c in children) + (len(children) - 1) * SIBLING_GAP
        widths[name] = max(unit_w, cw_sum)
        return widths[name]

    calc_width(root)

    positions = {}

    def place(name, left_x):
        node = nodes[name]
        n_sp = len(node["spouses"])
        unit_w = (1 + n_sp) * BOX_W + n_sp * SPOUSE_GAP
        subtree_w = widths[name]
        unit_left = left_x + (subtree_w - unit_w) // 2
        y = MARGIN_Y + node["gen"] * (BOX_H + GEN_GAP)

        positions[name] = {
            "x": unit_left, "y": y, "kind": "person",
            "spouses": [],
        }
        person_center = unit_left + BOX_W // 2

        sx = unit_left + BOX_W
        for sp in node["spouses"]:
            sx += SPOUSE_GAP
            key = ("spouse", name, sp)
            positions[key] = {
                "x": sx, "y": y, "kind": "spouse", "name": sp, "of": name,
            }
            positions[name]["spouses"].append(key)
            sx += BOX_W

        children = node["children"]
        if not children:
            return person_center

        cw_list = [widths[c] for c in children]
        total_cw = sum(cw_list) + (len(children) - 1) * SIBLING_GAP
        cx = left_x + (subtree_w - total_cw) // 2
        child_centers = []
        for i, child in enumerate(children):
            cc = place(child, cx)
            child_centers.append(cc)
            cx += cw_list[i] + SIBLING_GAP

        positions[name]["child_centers"] = child_centers
        positions[name]["drop_x"] = unit_left + unit_w // 2
        return person_center

    place(root, MARGIN_X + GEN_LABEL_W)
    return positions


# ── rendering ──────────────────────────────────────────────────────────
LINE_COLOR = "#5DADE2"
LINE_WIDTH = 2
SPOUSE_COLOR = "#FF6B81"

MALE_FILL = "#2C5F8D"
MALE_BORDER = "#5DADE2"
FEMALE_FILL = "#8B3A4F"
FEMALE_BORDER = "#F1948A"
ROOT_GLOW = "#F5C518"


def render_html(tree, characters, height_cap=900):
    if not tree or not tree.get("nodes"):
        return (
            "<div style='padding:24px;color:#aaa;background:#1a1a2e;"
            "border-radius:8px;'>No descendants found in the data.</div>",
            0,
        )

    nodes = tree["nodes"]
    root = tree["root"]
    positions = _layout(tree)

    max_x = max(p["x"] + BOX_W for p in positions.values())
    max_y = max(p["y"] + BOX_H for p in positions.values())
    svg_w = max_x + MARGIN_X
    svg_h = max_y + MARGIN_Y

    elements = []

    # generation lanes
    gens = sorted({n["gen"] for n in nodes.values()})
    for gen in gens:
        y = MARGIN_Y + gen * (BOX_H + GEN_GAP) - 10
        lane_fill = "#23234a" if gen % 2 == 0 else "#1d1d3e"
        elements.append(
            f'<rect x="0" y="{y}" width="{svg_w}" height="{BOX_H + 20}" '
            f'fill="{lane_fill}" opacity="0.35"/>'
        )
        elements.append(
            f'<text x="14" y="{y + BOX_H // 2 + 8}" fill="#777" '
            f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="10" '
            f'font-weight="700" letter-spacing="1">GEN {gen + 1}</text>'
        )

    # parent-child connectors (drawn under boxes)
    for name in nodes:
        p = positions[name]
        if "child_centers" not in p:
            continue
        drop_x = p["drop_x"]
        parent_bottom = p["y"] + BOX_H
        mid_y = parent_bottom + GEN_GAP // 2
        child_top = parent_bottom + GEN_GAP

        elements.append(
            f'<line x1="{drop_x}" y1="{parent_bottom}" x2="{drop_x}" y2="{mid_y}" '
            f'stroke="{LINE_COLOR}" stroke-width="{LINE_WIDTH}" stroke-linecap="round"/>'
        )
        xs = p["child_centers"] + [drop_x]
        if len(set(xs)) > 1:
            elements.append(
                f'<line x1="{min(xs)}" y1="{mid_y}" x2="{max(xs)}" y2="{mid_y}" '
                f'stroke="{LINE_COLOR}" stroke-width="{LINE_WIDTH}" stroke-linecap="round"/>'
            )
        for cc in p["child_centers"]:
            elements.append(
                f'<line x1="{cc}" y1="{mid_y}" x2="{cc}" y2="{child_top}" '
                f'stroke="{LINE_COLOR}" stroke-width="{LINE_WIDTH}" stroke-linecap="round"/>'
            )

    # spouse connectors
    for name in nodes:
        p = positions[name]
        for sp_key in p.get("spouses", []):
            sp = positions[sp_key]
            y = p["y"] + BOX_H // 2
            if sp["x"] >= p["x"]:
                x1 = p["x"] + BOX_W
                x2 = sp["x"]
            else:
                x1 = sp["x"] + BOX_W
                x2 = p["x"]
            elements.append(
                f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" '
                f'stroke="{SPOUSE_COLOR}" stroke-width="3" stroke-dasharray="6,3"/>'
            )
            elements.append(
                f'<text x="{(x1 + x2) // 2}" y="{y - 5}" fill="{SPOUSE_COLOR}" '
                f'font-family="sans-serif" font-size="13" text-anchor="middle">&#10084;</text>'
            )

    # boxes
    for key, pos in positions.items():
        if pos["kind"] == "person":
            name = key
        else:
            name = pos["name"]
        if name not in characters:
            continue
        info = characters[name]
        is_female = info["group"] in FEMALE_GROUPS
        fill = FEMALE_FILL if is_female else MALE_FILL
        border = FEMALE_BORDER if is_female else MALE_BORDER
        x, y = pos["x"], pos["y"]
        cx = x + BOX_W // 2

        is_root = (pos["kind"] == "person" and name == root)
        glow = ""
        if is_root:
            glow = (
                f'<rect x="{x - 3}" y="{y - 3}" width="{BOX_W + 6}" height="{BOX_H + 6}" '
                f'rx="11" ry="11" fill="none" stroke="{ROOT_GLOW}" stroke-width="2" '
                f'opacity="0.9"/>'
            )

        role = info["group"].title()
        desc = info.get("desc", "")

        elements.append(
            f'{glow}'
            f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="9" ry="9" '
            f'fill="{fill}" stroke="{border}" stroke-width="2"/>'
            f'<text x="{cx}" y="{y + 24}" fill="#ffffff" '
            f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="13" '
            f'font-weight="700" text-anchor="middle">{escape(name)}</text>'
            f'<text x="{cx}" y="{y + 42}" fill="#dde2ec" '
            f'font-family="ui-sans-serif,system-ui,sans-serif" font-size="10" '
            f'text-anchor="middle">{escape(role)}</text>'
            f'<title>{escape(name)} — {escape(desc)}</title>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{svg_h}" '
        f'viewBox="0 0 {svg_w} {svg_h}" style="display:block;background:#1a1a2e;">'
        + "".join(elements)
        + "</svg>"
    )

    container_h = min(svg_h + 4, height_cap)
    html = (
        f'<div style="background:#1a1a2e;border:1px solid #2d2d44;border-radius:10px;'
        f'overflow:auto;max-height:{height_cap}px;width:100%;">{svg}</div>'
    )
    return html, container_h
