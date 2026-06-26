#!/usr/bin/env python3
"""Convert QMD files to Google Colab R notebooks (ipynb format).

Structure follows the reference notebook: 02_08_05_01_01_causal_tree_r.ipynb
"""

import json
import re
import os

BANNER_URL = "https://drive.google.com/uc?id=1LhRCsnq8s3y0M76oN3-GEUfWQVL_yUv-"

# ── Helpers ────────────────────────────────────────────────────────────────────

def make_source(text: str) -> list:
    """Convert a text block to Jupyter cell source (list of strings)."""
    text = text.strip()
    if not text:
        return [""]
    lines = text.split("\n")
    result = []
    for i, line in enumerate(lines):
        result.append(line + "\n" if i < len(lines) - 1 else line)
    return result


def md_cell(cell_id: int, content: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": f"a1b2c3d4-0001-4001-8001-{cell_id:012d}",
        "metadata": {},
        "source": make_source(content),
    }


def code_cell(cell_id: int, source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": f"a1b2c3d4-0001-4001-8001-{cell_id:012d}",
        "metadata": {},
        "outputs": [],
        "source": make_source(source),
    }


# ── QMD parsing ────────────────────────────────────────────────────────────────

def strip_chunk_opts(code: str) -> str:
    """Remove #| option lines (Quarto chunk options) from R code."""
    lines = [l for l in code.split("\n") if not l.strip().startswith("#|")]
    return "\n".join(lines).strip()


def clean_markdown(text: str) -> str:
    """Clean QMD-specific markdown for Jupyter display."""
    # Remove {.unnumbered} from headings
    text = re.sub(r"\s*\{\.unnumbered\}", "", text)
    # Remove image size attributes like {width="576"}
    text = re.sub(r"(!\[[^\]]*\]\([^)]+\))\{[^}]*\}", r"\1", text)
    # Convert ::: callout-note / ::: callout-tip blocks → blockquote
    def replace_callout(m):
        inner = m.group(2).strip()
        kind = m.group(1).strip().split("-")[-1].capitalize()
        lines = inner.split("\n")
        quoted = "\n".join("> " + l if l.strip() else ">" for l in lines)
        return f"> **{kind}:**\n{quoted}"
    text = re.sub(
        r":::\s*callout-(\w+)\s*\n(.*?):::",
        replace_callout,
        text,
        flags=re.DOTALL,
    )
    # Remove any remaining ::: lines
    text = re.sub(r"^:::\s*.*$", "", text, flags=re.MULTILINE)
    return text.strip()


def parse_qmd(content: str) -> list:
    """Parse QMD into list of ('markdown'|'r', text) tuples."""
    chunks = []
    # Pattern: ```{r...} ... ``` (possibly with options)
    pattern = re.compile(r"```\{[rR][^}]*\}(.*?)```", re.DOTALL)
    last_end = 0
    for m in pattern.finditer(content):
        before = content[last_end : m.start()]
        if before.strip():
            chunks.append(("markdown", before))
        r_code = strip_chunk_opts(m.group(1))
        if r_code:
            chunks.append(("r", r_code))
        last_end = m.end()
    after = content[last_end:]
    if after.strip():
        chunks.append(("markdown", after))
    return chunks


# ── Colab setup cells (static) ─────────────────────────────────────────────────

SETUP_MD = (
    "## Setup R in Python Runtime - Install {rpy2}\n\n"
    "{rpy2} allows running R code in Colab Python runtime via `%%R` magic."
)

SETUP_CODE = (
    "!pip uninstall rpy2 -y\n"
    "!pip install rpy2==3.5.1\n"
    "%load_ext rpy2.ipython"
)

DRIVE_MD = (
    "## Mount Google Drive\n\n"
    "Mount Google Drive if your data or R library folder is stored there."
)

DRIVE_CODE = (
    "from google.colab import drive\n"
    "drive.mount('/content/drive')"
)

INSTALL_R = (
    "%%R\n"
    "# Install missing packages\n"
    "new.packages <- packages[!(packages %in% installed.packages(lib='drive/My Drive/R/')[,\"Package\"])]\n"
    "if(length(new.packages)) install.packages(new.packages, lib='drive/My Drive/R/')"
)

LIBPATH_VERIFY_R = (
    "%%R\n"
    "# set library path\n"
    ".libPaths('drive/My Drive/R')\n"
    "# Verify installation\n"
    "cat(\"Installed packages:\\n\")\n"
    "print(sapply(packages, requireNamespace, quietly = TRUE))"
)

CHECK_PARTIAL_R = (
    "%%R\n"
    "# Check loaded packages\n"
    "cat(\"Successfully loaded packages:\\n\")"
)

LOAD_CHECK_R = (
    "%%R\n"
    "# Load packages with suppressed messages\n"
    "invisible(lapply(packages, function(pkg) {\n"
    "  suppressPackageStartupMessages(library(pkg, character.only = TRUE))\n"
    "}))\n"
    "# Check loaded packages\n"
    "cat(\"Successfully loaded packages:\\n\")\n"
    "print(search()[grepl(\"package:\", search())])"
)


# ── Main converter ──────────────────────────────────────────────────────────────

def convert(qmd_path: str, nb_path: str):
    with open(qmd_path, "r", encoding="utf-8") as f:
        raw = f.read()

    # ── Split raw content at "## Set Up" boundary ──────────────────────────────
    # The heading can be "## Set Up" or "## Setup" (with/without space)
    setup_pattern = re.compile(r"^(##\s+Set\s*[Uu]p\b)", re.MULTILINE)
    m = setup_pattern.search(raw)
    if m:
        intro_raw = raw[: m.start()]
        setup_raw = raw[m.start():]
    else:
        intro_raw = raw
        setup_raw = ""

    cells = []
    cid = [1]  # mutable counter

    def add_md(content):
        cells.append(md_cell(cid[0], content))
        cid[0] += 1

    def add_code(source):
        cells.append(code_cell(cid[0], source))
        cid[0] += 1

    # ── Cell 1: banner ──────────────────────────────────────────────────────────
    add_md(f"![R Banner]({BANNER_URL})")

    # ── Cell 2: title + intro ──────────────────────────────────────────────────
    # Parse intro_raw for markdown text only (no code blocks expected here normally)
    intro_chunks = parse_qmd(intro_raw)
    intro_parts = []
    for ctype, text in intro_chunks:
        if ctype == "markdown":
            cleaned = clean_markdown(text)
            # Remove the local banner image line (first line)
            cleaned = re.sub(r"^!\[\]\(Images/[^\)]+\)\s*\n?", "", cleaned, flags=re.MULTILINE)
            if cleaned.strip():
                intro_parts.append(cleaned)
        # If there are code blocks in the intro (rare), skip them for now

    if intro_parts:
        add_md("\n\n".join(intro_parts))

    # ── Cells 3-6: static Colab setup ─────────────────────────────────────────
    add_md(SETUP_MD)
    add_code(SETUP_CODE)
    add_md(DRIVE_MD)
    add_code(DRIVE_CODE)

    # ── Process Set Up section chunks ──────────────────────────────────────────
    # We iterate the setup chunks, handling known sub-sections specially
    # so that install/load cells get Colab-compatible versions.

    remaining = parse_qmd(setup_raw)

    # State machine: track which setup sub-section we're in
    NORMAL = "normal"
    AFTER_INSTALL_HDR = "after_install_hdr"
    AFTER_LOAD_HDR = "after_load_hdr"
    AFTER_CHECK_HDR = "after_check_hdr"

    state = NORMAL
    i = 0
    while i < len(remaining):
        ctype, text = remaining[i]

        if ctype == "markdown":
            cleaned = clean_markdown(text)
            # Remove local banner image lines
            cleaned = re.sub(r"^!\[\]\(Images/[^\)]+\)\s*\n?", "", cleaned, flags=re.MULTILINE)

            if not cleaned.strip():
                i += 1
                continue

            # ── Detect "## Set Up" header → emit it, reset state ──────────────
            if re.search(r"^##\s+Set\s*[Uu]p", cleaned, re.MULTILINE):
                add_md(cleaned)
                state = NORMAL
                i += 1
                continue

            # ── Detect "### Install Missing Packages" ─────────────────────────
            if re.search(r"Install Missing Packages", cleaned, re.IGNORECASE):
                add_md("### Install Missing Packages")
                state = AFTER_INSTALL_HDR
                i += 1
                continue

            # ── Detect "### Load R Packages" ──────────────────────────────────
            if re.search(r"^###\s+Load R Packages", cleaned, re.MULTILINE):
                add_md("### Load R Packages")
                state = AFTER_LOAD_HDR
                i += 1
                continue

            # ── Detect "### Check Loaded Packages" ────────────────────────────
            if re.search(r"Check Loaded Packages", cleaned, re.IGNORECASE):
                add_md("### Check Loaded Packages")
                state = AFTER_CHECK_HDR
                i += 1
                continue

            # Everything else: emit as markdown
            add_md(cleaned)
            state = NORMAL

        elif ctype == "r":
            code = text

            if state == AFTER_INSTALL_HDR:
                # Replace with Colab version (drive library path)
                add_code(INSTALL_R)
                state = NORMAL
            elif state == AFTER_LOAD_HDR:
                # Replace with Colab version (.libPaths + verify)
                add_code(LIBPATH_VERIFY_R)
                state = NORMAL
            elif state == AFTER_CHECK_HDR:
                # First: partial check cell; second: combined load+check cell
                add_code(CHECK_PARTIAL_R)
                add_code(LOAD_CHECK_R)
                state = NORMAL
            else:
                add_code(f"%%R\n{code}")

        i += 1

    # ── Build notebook ─────────────────────────────────────────────────────────
    notebook = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "colab": {"provenance": []},
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.10.0",
            },
        },
        "cells": cells,
    }

    with open(nb_path, "w", encoding="utf-8") as f:
        json.dump(notebook, f, indent=1, ensure_ascii=False)

    print(f"  ✓  {os.path.basename(qmd_path)}  →  {os.path.basename(nb_path)}")


# ── Run all conversions ────────────────────────────────────────────────────────

MARKDOWN_DIR = "/home/zia207/Github/Causal_Inference_R/Markdown"
NOTEBOOK_DIR = "/home/zia207/Github/Causal_Inference_R/Notebook"

FILES = [
    ("02-08-05-01-02-causal-forest-r.qmd",                "02_08_05_01_02_causal_forest_r.ipynb"),
    ("02-08-05-01-03-causal-survival-forest-r.qmd",       "02_08_05_01_03_causal_survival_forest_r.ipynb"),
    ("02-08-05-01-04-instrumental-causal-forest-r.qmd",   "02_08_05_01_04_instrumental_causal_forest_r.ipynb"),
    ("02-08-05-01-05-multi-arm-causal-forest-r.qmd",      "02_08_05_01_05_multi_arm_causal_forest_r.ipynb"),
    ("02-08-05-01-06-causal-xgboost-r.qmd",               "02_08_05_01_06_causal_xgboost_r.ipynb"),
    ("02-08-05-01-07-instrumental-causal-xgboost-r.qmd",  "02_08_05_01_07_instrumental_causal_xgboost_r.ipynb"),
    ("02-08-05-01-08-multi-arm-causal-boost-r.qmd",       "02_08_05_01_08_multi_arm_causal_boost_r.ipynb"),
]

if __name__ == "__main__":
    print("Converting QMD files to Google Colab notebooks ...\n")
    for qmd_file, nb_file in FILES:
        qmd_path = os.path.join(MARKDOWN_DIR, qmd_file)
        nb_path = os.path.join(NOTEBOOK_DIR, nb_file)
        if os.path.exists(qmd_path):
            convert(qmd_path, nb_path)
        else:
            print(f"  ✗  Not found: {qmd_path}")
    print("\nDone.")
