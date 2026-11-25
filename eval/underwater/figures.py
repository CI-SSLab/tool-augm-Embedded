#!/usr/bin/env python3
"""figures.py — Presentation figures for the image search (PNG, light theme).

  1 heatmap_objects.png     cosine between indexed objects (max over views), grouped by typology
  2 cosine_same_vs_diff.png  distribution of view-view cosines: same object vs different objects
  3 topk_examples.png        query photo + top-5 objects with score and decision, one row per C0/C1/C2
  4 pca_views.png            2D PCA of index views and query photos
  5 risk_coverage.png        risk-coverage curves when tau varies, underwater and famous-artworks sets
  6 accuracy_by_set.png      top-1 object and top-1 site for C0 and C1

Index thumbnails are drawn only when their licence is CC or public domain; In Copyright
and unlicensed ICCD photos become a grey tile with the object name. Query photos are Commons.

Usage:
    scripts/slurm/run.sh .venv/bin/python eval/underwater/figures.py \
        --results eval/underwater/results/images/results_images_curated_group_none_<id>.csv \
        --famous eval/famous/results/results_images_<id>.csv
"""
import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from PIL import Image  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from image_search import index  # noqa: E402

OUT = ROOT / "eval" / "underwater" / "results" / "figures"

# ── Palette (dataviz reference instance, light mode) ──────────────────────────
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"  # first three categorical slots: validated all-pairs
BLUES = LinearSegmentedColormap.from_list("blues", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
OPEN_LICENCE = ("creativecommons.org/licenses/by", "creativecommons.org/publicdomain", "/zero/", "/mark/")

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": False, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 11,
    "font.family": ["DejaVu Sans", "sans-serif"],
})

SHORT = {  # short names for axis labels
    "baia_odysseus": "Ulisse (Baia)", "baia_odysseus_companion": "Compagno con otre", "baia_dionysos": "Dioniso (Baia)",
    "baia_antonia": "Antonia (Baia)", "artemision_god": "Dio di Artemisio", "artemision_jockey": "Fantino di Artemisio",
    "antikythera_ephebe": "Efebo di Anticitera", "antikythera_philosopher": "Filosofo di Anticitera",
    "site_punta_epitaffio": "Punta Epitaffio", "site_miseno_porto": "Porto di Miseno",
    "site_torre_scassata": "Torre Scassata", "site_porto_1500910310": "Porto (Mondragone)",
    "site_vasche_1800177710": "Vasche (Briatico)",
}


def short(oid: str) -> str:
    return SHORT.get(oid, oid)


def save(fig, name: str):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / name)


# ── 1-2: index structure ──────────────────────────────────────────────────────

def object_order(rows: list, group: dict) -> list:
    # Museum objects first, then in-situ structures, in group CSV order
    seen = list(dict.fromkeys(r["object_id"] for r in rows))
    return sorted(seen, key=lambda o: (group[o]["typology"] != "museum_object", list(group).index(o)))


def heatmap(emb, rows, group):
    objs = object_order(rows, group)
    ids = np.array([r["object_id"] for r in rows])
    sim = emb @ emb.T
    m = np.full((len(objs), len(objs)), np.nan)
    for i, a in enumerate(objs):
        for j, b in enumerate(objs):
            if a != b:
                m[i, j] = sim[np.ix_(ids == a, ids == b)].max()
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(m, cmap=BLUES, vmin=0.5, vmax=1.0)
    ax.set_xticks(range(len(objs)), [short(o) for o in objs], rotation=50, ha="right")
    ax.set_yticks(range(len(objs)), [short(o) for o in objs])
    n_museum = sum(group[o]["typology"] == "museum_object" for o in objs)
    for k in (n_museum - 0.5,):
        ax.axhline(k, color=SURFACE, lw=3)
        ax.axvline(k, color=SURFACE, lw=3)
    ax.spines[:].set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.8)
    cb.set_label("coseno massimo fra le viste")
    cb.outline.set_visible(False)
    ax.set_title("Similarità fra gli oggetti dell'indice (diagonale esclusa)", loc="left", color=INK)
    save(fig, "heatmap_objects.png")


def same_vs_diff(emb, rows):
    ids = np.array([r["object_id"] for r in rows])
    sim = emb @ emb.T
    iu = np.triu_indices(len(rows), 1)
    same = ids[iu[0]] == ids[iu[1]]
    vals = sim[iu]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bins = np.linspace(0.4, 1.0, 37)
    ax.hist(vals[~same], bins=bins, color=S2, alpha=0.85, label=f"oggetti diversi (n={(~same).sum()})",
            edgecolor=SURFACE, linewidth=1)
    ax.hist(vals[same], bins=bins, color=S1, alpha=0.85, label=f"stesso oggetto (n={same.sum()})",
            edgecolor=SURFACE, linewidth=1)
    ax.set_xlabel("coseno fra due viste dell'indice")
    ax.set_ylabel("coppie di viste")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Le due distribuzioni si sovrappongono: serve il margine δ, non solo la soglia τ",
                 loc="left", color=INK)
    save(fig, "cosine_same_vs_diff.png")


# ── 3: top-k examples ─────────────────────────────────────────────────────────

def thumb_for(oid: str, rows: list):
    # First openly licensed view of the object, else None (grey tile)
    for r in rows:
        if r["object_id"] == oid and any(k in r["license"] for k in OPEN_LICENCE):
            try:
                return Image.open(index.cached_image(r["image_url"])).convert("RGB")
            except Exception:
                return None
    return None


def topk_examples(results, rows):
    picks = []
    for cond in ("C0", "C1", "C2"):
        cand = [r for r in results if r["set"] == cond and r.get("split", "test") == "test"]
        if cond == "C0":
            cand = [r for r in cand if r["outcome"] == "correct_match"] or cand
        if cond == "C1":
            cand = [r for r in cand if r["expected_object_id"] == "baia_dionysos"] or cand
        if cond == "C2":
            cand = [r for r in cand if "Riace" in r.get("category", "")] or cand
        if cand:
            picks.append(cand[0])
    fig, axes = plt.subplots(len(picks), 6, figsize=(15, 3.1 * len(picks)),
                             gridspec_kw={"width_ratios": [1.3, 1, 1, 1, 1, 1]})
    labels = {"C0": "C0 foto da museo", "C1": "C1 foto subacquea", "C2": "C2 negativo"}
    for row_axes, r in zip(np.atleast_2d(axes), picks):
        q = Image.open(index.cached_image(r["image_url"])).convert("RGB")
        row_axes[0].imshow(q)
        exp = short(r["expected_object_id"]) if r["expected_object_id"] else "non nell'indice"
        row_axes[0].set_title(f"{labels[r['set']]}\natteso: {exp}", fontsize=10, loc="left", color=INK)
        top = r["top5"].split("; ")
        scores = [float(r["s1"]), float(r["s2"])] + [None] * 3
        for k, (ax, oid) in enumerate(zip(row_axes[1:], top)):
            img = thumb_for(oid, rows)
            if img is not None:
                ax.imshow(img)
            else:
                ax.set_facecolor(GRID)
                ax.text(0.5, 0.5, "immagine\nnon riutilizzabile\n(InC / ICCD)", ha="center", va="center",
                        fontsize=8, color=MUTED, transform=ax.transAxes)
            ok = oid == r["expected_object_id"]
            score = f"  {scores[k]:.3f}" if scores[k] is not None else ""
            ax.set_title(f"{k + 1}. {short(oid)}{score}" + ("  ✓" if ok else ""), fontsize=9, loc="left",
                         color=INK if ok else INK2)
        row_axes[-1].text(1.04, 0.5, f"decisione:\n{r['decision']}\n({r['outcome'].replace('_', ' ')})",
                          transform=row_axes[-1].transAxes, va="center", fontsize=10, color=INK)
        for ax in row_axes:
            ax.set_xticks([])
            ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
    fig.suptitle("Ricerca dei simili: foto di query e primi 5 oggetti dell'indice (punteggi solo per i primi due)",
                 x=0.01, ha="left", color=INK)
    save(fig, "topk_examples.png")


# ── 4: PCA ────────────────────────────────────────────────────────────────────

def pca(emb, rows, group, results, query_emb):
    mean = emb.mean(0)
    _, _, vt = np.linalg.svd(emb - mean, full_matrices=False)
    p = (emb - mean) @ vt[:2].T
    fig, ax = plt.subplots(figsize=(9, 7))
    museum = np.array([group[r["object_id"]]["typology"] == "museum_object" for r in rows])
    ax.scatter(*p[museum].T, s=70, color=S1, edgecolor=SURFACE, linewidth=1.5, label="vista indice: reperto museale",
               zorder=3)
    ax.scatter(*p[~museum].T, s=70, color=S2, edgecolor=SURFACE, linewidth=1.5, label="vista indice: struttura in situ",
               zorder=3)
    # Hand offsets for the two in-situ labels that land on each other
    nudge = {"site_porto_1500910310": (6, 14), "site_vasche_1800177710": (6, -16)}
    for oid in dict.fromkeys(r["object_id"] for r in rows):
        c = p[[r["object_id"] == oid for r in rows]].mean(0)
        ax.annotate(short(oid), c, xytext=nudge.get(oid, (6, 6)), textcoords="offset points", fontsize=8, color=INK2)
    if len(query_emb):
        q = (query_emb - mean) @ vt[:2].T
        sets = np.array([r["set"] for r in results])
        ax.scatter(*q[sets == "C1"].T, s=40, marker="^", color=S3, edgecolor=SURFACE, linewidth=1,
                   label="query C1 (subacquea, oggetto nell'indice)", zorder=4)
        ax.scatter(*q[sets == "C2"].T, s=22, marker="x", color=MUTED, linewidth=1,
                   label="query C2 (negativo)", zorder=2)
    ax.set_xlabel("componente principale 1")
    ax.set_ylabel("componente principale 2")
    ax.legend(frameon=False, loc="best", fontsize=9)
    ax.set_title("Proiezione PCA degli embedding (EmbeddingGemma 2, budget 280)", loc="left", color=INK)
    save(fig, "pca_views.png")


# ── 5-6: decision quality ─────────────────────────────────────────────────────

def risk_coverage(curves: dict):
    # Accept when s1 >= tau. Coverage = accepted / all queries; risk = accepted that are wrong
    # (wrong object, or a negative accepted) / accepted
    fig, ax = plt.subplots(figsize=(8, 5))
    for (name, res), color in zip(curves.items(), (S1, S2)):
        s1 = np.array([float(r["s1"]) for r in res])
        ok = np.array([bool(r["expected_object_id"]) and r["top1"] == r["expected_object_id"] for r in res])
        taus = np.unique(np.concatenate([s1, [0.80]]))
        cov = [(s1 >= t).mean() for t in taus]
        risk = [1 - ok[s1 >= t].mean() if (s1 >= t).any() else 0 for t in taus]
        ax.plot(cov, risk, color=color, lw=2, label=name)
        k = np.argmin(abs(taus - 0.80))
        ax.plot(cov[k], risk[k], "o", ms=8, color=color, markeredgecolor=SURFACE, markeredgewidth=2)
        ax.annotate(f"τ = 0,80", (cov[k], risk[k]), xytext=(8, -14), textcoords="offset points", fontsize=9,
                    color=INK2)
    ax.set_xlabel("copertura (quota di query a cui il sistema risponde con un record)")
    ax.set_ylabel("rischio (quota di risposte con il record sbagliato)")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left")
    ax.set_title("Curva rischio-copertura al variare della soglia τ", loc="left", color=INK)
    save(fig, "risk_coverage.png")


def accuracy_by_set(results, group):
    site = {o: (g["arco_site_id"] or o) for o, g in group.items()}
    in_situ_site = {g["arco_site_id"]: o for o, g in group.items() if g["typology"] == "in_situ_structure"}
    site = {o: in_situ_site.get(s, s) for o, s in site.items()}  # objects and their site share one key
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(2)
    for k, (label, color, fn) in enumerate((
            ("oggetto giusto", S1, lambda r: r["top1"] == r["expected_object_id"]),
            ("sito giusto", S2, lambda r: site.get(r["top1"]) == site.get(r["expected_object_id"])))):
        vals = []
        for cond in ("C0", "C1"):
            sub = [r for r in results if r["set"] == cond]
            vals.append(100 * np.mean([fn(r) for r in sub]) if sub else 0)
        bars = ax.bar(x + (k - 0.5) * 0.36, vals, 0.34, color=color, label=label, edgecolor=SURFACE, linewidth=2)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 2, f"{v:.0f}%", ha="center", fontsize=10, color=INK)
    n = {c: sum(r["set"] == c for r in results) for c in ("C0", "C1")}
    ax.set_xticks(x, [f"C0 foto da museo (n={n['C0']})", f"C1 foto subacquea (n={n['C1']})"])
    ax.set_ylim(0, 110)
    ax.set_ylabel("top-1 (%)")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title("Salto di dominio: sott'acqua l'oggetto si perde, il sito resta", loc="left", color=INK)
    save(fig, "accuracy_by_set.png")


def main():
    p = argparse.ArgumentParser(description="Presentation figures for the image search")
    p.add_argument("--results", required=True, help="evaluate_images.py CSV on the underwater set")
    p.add_argument("--famous", default="", help="evaluate_images.py CSV on the famous-artworks set")
    p.add_argument("--no-embed", action="store_true", help="skip query embeddings in the PCA (no GPU)")
    args = p.parse_args()

    group_csv = index.CENSUS / "curated_group.csv"
    group = {g["object_id"]: g for g in csv.DictReader(open(group_csv, encoding="utf-8"))}
    emb, rows = index.load_index(index.index_dir("embeddinggemma-2_b280", group_csv))
    results = list(csv.DictReader(open(args.results, encoding="utf-8")))

    heatmap(emb, rows, group)
    same_vs_diff(emb, rows)
    topk_examples(results, rows)
    query_emb = np.zeros((0, emb.shape[1]))
    pca_rows = [r for r in results if r["set"] in ("C1", "C2")]
    if not args.no_embed:
        from image_search.encoder import Encoder, load_image
        query_emb = Encoder().embed([load_image(index.cached_image(r["image_url"])) for r in pca_rows])
    pca(emb, rows, group, pca_rows if len(query_emb) else [], query_emb)
    curves = {"subacqueo (C0 + C1 + C2)": results}
    if args.famous:
        curves["opere famose (originali, degradate, negativi)"] = list(csv.DictReader(open(args.famous, encoding="utf-8")))
    risk_coverage(curves)
    accuracy_by_set(results, group)


if __name__ == "__main__":
    main()
