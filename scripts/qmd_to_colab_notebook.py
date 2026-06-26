#!/usr/bin/env python3
"""Convert structural-learning QMD tutorials to Colab notebooks with rpy2."""

import json
import re
from pathlib import Path

GITHUB_IMG = "https://raw.githubusercontent.com/zia207/Causal_Inference_R/main/Markdown/Image"

NOTEBOOKS = [
    {
        "qmd": "Markdown/02-08-05-05-03-02-DeepCausalML-dag-structure-learning-graph-neural-networks-DagGNN-r.qmd",
        "out": "Notebook/02_08_05_05_03_02_deep_causal_ml_dag_structure_learning_graph_neural_networks_daggnn_r.ipynb",
        "title_section": (
            "## DAG-GNN with {RCausalML}\n\n"
            "This notebook demonstrates DAG-GNN structure learning with graph neural networks using the "
            "{RCausalML} package: synthetic data generation, VAE+GNN training with augmented Lagrangian "
            "updates, structure recovery, and downstream ATE/CATE estimation.\n"
        ),
        "packages": [
            "torch", "igraph", "tidyverse", "ggraph",
            "corrplot", "patchwork", "RCausalML",
        ],
    },
    {
        "qmd": "Markdown/02-08-05-05-03-03-DeepCausalML-gradient-based-neural-learning-GranDag-r.qmd",
        "out": "Notebook/02_08_05_05_03_03_deep_causal_ml_gradient_based_neural_learning_grandag_r.ipynb",
        "title_section": (
            "## GraN-DAG with {RCausalML}\n\n"
            "This notebook implements GraN-DAG (gradient-based neural DAG learning) in R via {RCausalML}: "
            "masked MLPs per node, adjacency extraction, augmented Lagrangian optimization, and downstream "
            "causal effect estimation.\n"
        ),
        "packages": ["torch", "igraph", "tidyverse", "RCausalML", "knitr"],
    },
    {
        "qmd": "Markdown/02-08-05-05-03-04-DeepCausalML-DAGMA-NoCurl-r.qmd",
        "out": "Notebook/02_08_05_05_03_04_deep_causal_ml_dagma_nocurl_r.ipynb",
        "title_section": (
            "## DAGMA and DAG-NoCurl with {RCausalML}\n\n"
            "This notebook compares DAGMA Linear, DAGMA Nonlinear (MLP), and DAG-NoCurl on the IHDP "
            "benchmark using {RCausalML}.\n"
        ),
        "packages": [
            "tidyverse", "plyr", "RCausalML", "causaldata",
            "torch", "dagitty", "ggdag", "igraph", "corrplot", "R6",
        ],
    },
    {
        "qmd": "Markdown/02-08-05-05-03-05-DeepCausalML-causal-structural-learning-regularization-CASTLE-r.qmd",
        "out": "Notebook/02_08_05_05_03_05_deep_causal_ml_causal_structural_learning_regularization_castle_r.ipynb",
        "title_section": (
            "## CASTLE with {RCausalML}\n\n"
            "This notebook applies CASTLE (causal structure learning regularization) on IHDP-style data "
            "using {RCausalML}: joint graph learning, selective reconstruction, and supervised prediction.\n"
        ),
        "packages": [
            "tidyverse", "RCausalML", "causaldata",
            "torch", "dagitty", "ggdag", "igraph",
        ],
    },
]


def clean_markdown(text: str) -> str:
    text = re.sub(
        r"!\[\]\(Images/([^)]+)\)(?:\{[^}]*\})?",
        rf"![]({GITHUB_IMG}/\1)",
        text,
    )
    text = re.sub(r"\{#[^}]+\}", "", text)
    text = re.sub(r"\{\.unnumbered\}", "", text)
    text = re.sub(r"<a id=[^>]+></a>", "", text)
    text = re.sub(r"\n-{3,}\n", "\n\n", text)
    text = re.sub(r"\n\*Note:.*$", "", text, flags=re.DOTALL)
    return text.strip()


def split_qmd(content: str):
    parts = []
    pattern = re.compile(r"```\{r\}[^`]*```", re.DOTALL)
    last = 0
    for match in pattern.finditer(content):
        if match.start() > last:
            md = content[last:match.start()].strip()
            if md:
                parts.append(("markdown", md))
        code = match.group(0)
        code = re.sub(r"^```\{r\}[^\n]*\n", "", code)
        code = re.sub(r"\n```$", "", code)
        parts.append(("code", code.strip()))
        last = match.end()
    if last < len(content):
        md = content[last:].strip()
        if md:
            parts.append(("markdown", md))
    return parts


def md_cell(text: str):
    cleaned = clean_markdown(text)
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in cleaned.split("\n")],
    }


def code_cell(code: str):
    lines = ["%%R\n"] + [line + "\n" for line in code.split("\n")]
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines,
    }


def setup_cells(packages):
    pkg_str = ",\n  ".join(f'"{p}"' for p in packages)
    return [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["![R Banner](https://drive.google.com/uc?id=1visd1lH1fbGOM1qqlYJgPaubUt2srmme)\n"],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Setup R in Python Runtime - Install {rpy2}\n\n"
                "{rpy2} allows running R code in Colab Python runtime via `%%R` magic.\n"
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["!pip uninstall rpy2 -y\n\n!pip install rpy2==3.5.1\n\n%load_ext rpy2.ipython\n"],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Mount Google Drive\n\n"
                "Mount Google Drive if your data or R library folder is stored there.\n"
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": ["from google.colab import drive\n\ndrive.mount('/content/drive')\n"],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Set Up\n\n### Check and Install Required R Packages\n\n"
                "Following R packages are required to run this notebook. "
                "If any of these packages are not installed, you can install them using the code below:\n\n"
                + ", ".join(f"`{p}`" for p in packages)
                + "\n"
            ],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [f"%%R\npackages <- c(\n  {pkg_str}\n)\n"],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["### Install Missing Packages\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                '%%R\n# Install missing packages\n'
                '# new_packages <- packages[!(packages %in% installed.packages()[, "Package"])]\n'
                "# if (length(new_packages)) install.packages(new_packages)\n"
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["### Verify Installation\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                '%%R\n# Verify installation\ncat("Installed packages:\\n")\n'
                "print(sapply(packages, requireNamespace, quietly = TRUE))\n"
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["### Load R Packages\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "%%R\n# Load packages with suppressed messages\n"
                "invisible(lapply(packages, function(pkg) {\n"
                "  suppressPackageStartupMessages(library(pkg, character.only = TRUE))\n"
                "}))\n"
            ],
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": ["### Check Loaded Packages\n"],
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                '%%R\n# Check loaded packages\ncat("Successfully loaded packages:\\n")\n'
                'print(search()[grepl("package:", search())])\n'
            ],
        },
    ]


def is_setup_code(content: str) -> bool:
    if re.search(r"^packages\s*<-", content, re.MULTILINE):
        return True
    if re.search(r"^# Install missing packages", content):
        return True
    if re.search(r"^# Verify installation", content) and "requireNamespace" in content:
        return True
    if re.search(r"^find_pkg_root\s*<-", content):
        return True
    if re.search(r"^invisible\(lapply\(packages", content):
        return True
    if re.search(r"^#\| label: setup-packages", content):
        return True
    if re.search(r"^#\| label: packages-list", content):
        return True
    if re.search(r"^#\| label: install-missing-packages", content):
        return True
    if re.search(r"^#\| label: verify-installation", content):
        return True
    if re.search(r"^#\| label: load-required-libraries", content):
        return True
    return False


def clean_body_markdown(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^##\s+Implementation in R\s*\n+", "", text)
    text = re.sub(r"\n###\s+Setup\s*\n.*?(?=\n###\s|\n##\s|\Z)", "\n", text, flags=re.DOTALL)
    text = re.sub(
        r"\n###\s+Load and Check Required Libraries\s*\n.*?(?=\n###\s|\n##\s|\Z)",
        "\n",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\n###\s+Install Missing Packages\s*\n.*?(?=\n###\s|\n##\s|\Z)",
        "\n",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\n###\s+Verify Installation\s*\n.*?(?=\n###\s|\n##\s|\Z)",
        "\n",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"\n###\s+Load Required Libraries\s*\n.*?(?=\n###\s|\n##\s|\Z)",
        "\n",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"\n?###\s+Setup\s*$", "", text)
    return text.strip()


def split_intro_from_markdown(text: str):
    m = re.search(r"^##\s+Implementation in R\b", text, re.MULTILINE)
    if not m:
        return text.strip(), ""
    return text[: m.start()].strip(), text[m.start() :].strip()


def extract_intro(parts, title_section):
    intro_md = []
    body_parts = []
    seen_markdown = False
    for kind, content in parts:
        if kind == "markdown":
            if not seen_markdown:
                seen_markdown = True
                intro_part, impl_part = split_intro_from_markdown(content)
                if intro_part:
                    intro_md.append(intro_part)
                if impl_part:
                    body_parts.append((kind, impl_part))
            else:
                body_parts.append((kind, content))
        elif kind == "code":
            if is_setup_code(content):
                continue
            body_parts.append((kind, content))
        else:
            body_parts.append((kind, content))

    intro_text = "\n\n".join(intro_md)
    intro_text = clean_markdown(intro_text)
    if title_section and title_section.strip() not in intro_text:
        m = re.search(r"^(# .+)$", intro_text, re.MULTILINE)
        if m:
            insert_at = m.end()
            intro_text = intro_text[:insert_at] + "\n\n" + title_section.strip() + intro_text[insert_at:]
        else:
            intro_text = f"{intro_text}\n\n{title_section.strip()}"
    return intro_text, body_parts


def strip_setup_from_body(body_parts):
    cleaned = []
    for kind, content in body_parts:
        if kind == "markdown":
            if re.match(r"^###\s+Setup\s*$|^##\s+Setup\s*$", content.strip()):
                continue
            if re.search(
                r"^###\s+Load and Check Required Libraries|^###\s+Install Missing Packages|"
                r"^###\s+Verify Installation|^###\s+Load Required Libraries",
                content.strip(),
            ):
                continue
            if re.match(r"^##\s+Implementation in R\s*$", content.strip()):
                continue
            content = clean_body_markdown(content)
            if content:
                cleaned.append((kind, content))
        elif kind == "code":
            if is_setup_code(content):
                continue
            cleaned.append((kind, content))
        else:
            cleaned.append((kind, content))
    return cleaned


def convert(nb_cfg, root: Path):
    content = (root / nb_cfg["qmd"]).read_text(encoding="utf-8")
    parts = split_qmd(content)
    intro, body = extract_intro(parts, nb_cfg.get("title_section", ""))
    body = strip_setup_from_body(body)

    cells = setup_cells(nb_cfg["packages"])
    if intro.strip():
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in intro.split("\n")],
        })

    for kind, text in body:
        if kind == "markdown":
            cleaned = clean_body_markdown(clean_markdown(text))
            if not cleaned:
                continue
            if re.match(r"^###\s+Load and Check Required Libraries", cleaned):
                continue
            cells.append(md_cell(cleaned))
        else:
            cells.append(code_cell(text))

    nb = {
        "cells": cells,
        "metadata": {
            "colab": {"provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.10.0"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    out_path = root / nb_cfg["out"]
    out_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} ({len(cells)} cells)")


def main():
    root = Path(__file__).resolve().parents[1]
    for cfg in NOTEBOOKS:
        convert(cfg, root)


if __name__ == "__main__":
    main()
