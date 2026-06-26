#!/usr/bin/env python3
"""Convert Deep Causal ML timeseries .qmd files (05-04-02..06) to Colab ipynb.

Matches the structure of Notebook/02_08_05_05_04_01_deep_causal_ml_timeseries_neural_granger_causuality_r.ipynb
"""

from __future__ import annotations

import json
import re
from pathlib import Path

BANNER_URL = "https://drive.google.com/uc?id=1QRhC0tCK2wUgujdffSCXsZUsPPs1V5nG"
GITHUB_IMG_BASE = (
    "https://raw.githubusercontent.com/zia207/Causal_Inference_R/main/Markdown"
)
MARKDOWN_DIR = Path("/home/zia207/Github/Causal_Inference_R/Markdown")
NOTEBOOK_DIR = Path("/home/zia207/Github/Causal_Inference_R/Notebook")

FILES = [
    (
        "02-08-05-05-04-02-DeepCausalML-timeseries-structural-causal-model-SMC-r.qmd",
        "02_08_05_05_04_02_deep_causal_ml_timeseries_structural_causal_model_smc_r.ipynb",
    ),
    (
        "02-08-05-05-04-03-DeepCausalML-attension-transformer-r.qmd",
        "02_08_05_05_04_03_deep_causal_ml_attension_transformer_r.ipynb",
    ),
    (
        "02-08-05-05-04-04-DeepCausalML-timeseries-RNN-LSTM-causaML-r.qmd",
        "02_08_05_05_04_04_deep_causal_ml_timeseries_rnn_lstm_causa_ml_r.ipynb",
    ),
    (
        "02-08-05-05-04-05-DeepCausalML-timeseries-graph-nn-r.qmd",
        "02_08_05_05_04_05_deep_causal_ml_timeseries_graph_nn_r.ipynb",
    ),
    (
        "02-08-05-05-04-06-DeepCausalML-timeseries-counterfactual-potential-causalML-r.qmd",
        "02_08_05_05_04_06_deep_causal_ml_timeseries_counterfactual_potential_causal_ml_r.ipynb",
    ),
]

SETUP_SPLIT = re.compile(
    r"^###\s+Load and Check Required Libraries\s*$", re.MULTILINE
)
SETUP_END = re.compile(
    r"^##\s+(Data|Part|Train|Utilities|Fit|Graph|Notes|Summary|Resources|Validation|Counterfactual|Model)\b",
    re.MULTILINE,
)


def to_source(text: str) -> list[str]:
    if not text:
        return [""]
    lines = text.splitlines(keepends=True)
    if not lines:
        return [text + "\n"]
    if not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return lines


def md_cell(content: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": to_source(content)}


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": to_source(source),
    }


def fix_image_urls(text: str) -> str:
    def abs_path(path: str) -> str:
        if path.startswith(("http://", "https://")):
            return path
        path = path.lstrip("/")
        if path.startswith("Images/"):
            path = "Image/" + path[len("Images/") :]
        return f"{GITHUB_IMG_BASE}/{path}"

    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f"![{m.group(1)}]({abs_path(m.group(2))})",
        text,
    )
    text = re.sub(
        r"\[(!\[[^\]]*\]\([^)]+\))\]\([^)]+\)",
        r"\1",
        text,
    )
    return text


def clean_markdown(text: str) -> str:
    text = fix_image_urls(text)
    text = re.sub(r"(!\[[^\]]*\]\([^)]+\))\{[^}]+\}", r"\1", text)
    text = re.sub(r"\s*\{\.unnumbered\}", "", text)
    text = re.sub(r"\s*\{#([^}]+)\}", "", text)
    text = re.sub(r"\[\[\d+\]\]", "", text)
    text = re.sub(r"^:{3,}.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:::.*$", "", text, flags=re.MULTILINE)
    text = text.replace(r"\_", "_")
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n" if text.strip() else ""


def strip_chunk_opts(code: str) -> str:
    return "\n".join(
        ln for ln in code.splitlines() if not ln.strip().startswith("#|")
    ).strip()


def parse_qmd(content: str) -> list[tuple[str, str]]:
    chunks: list[tuple[str, str]] = []
    pattern = re.compile(r"```\{[rR][^}]*\}(.*?)```", re.DOTALL)
    last = 0
    for m in pattern.finditer(content):
        before = content[last : m.start()]
        if before.strip():
            chunks.append(("markdown", before))
        code = strip_chunk_opts(m.group(1))
        if code:
            chunks.append(("r", code))
        last = m.end()
    after = content[last:]
    if after.strip():
        chunks.append(("markdown", after))
    return chunks


def extract_packages(code: str) -> list[str]:
    m = re.search(
        r"packages\s*<-\s*c\s*\((.*?)\)", code, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return []
    return re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))


def split_sections(raw: str) -> tuple[str, str, str]:
    split_m = SETUP_SPLIT.search(raw)
    if not split_m:
        return raw, "", ""

    intro = raw[: split_m.start()]
    rest = raw[split_m.start() :]
    end_m = SETUP_END.search(rest)
    if end_m:
        setup = rest[: end_m.start()]
        body = rest[end_m.start() :]
    else:
        setup = rest
        body = ""
    return intro, setup, body


def build_setup_cells(setup_raw: str) -> list[dict]:
    chunks = parse_qmd(setup_raw)
    cells: list[dict] = []
    packages: list[str] = []
    r_chunks: list[str] = []

    for kind, body in chunks:
        if kind == "r":
            if body.strip().startswith("packages"):
                packages = extract_packages(body)
            r_chunks.append(body)

    pkg_list = ", ".join(f"`{p}`" for p in packages) if packages else ""
    cells.append(
        md_cell(
            "## Set Up\n\n"
            "### Load and Check Required Libraries\n\n"
            "Following R packages are required to run this notebook:\n\n"
            f"{pkg_list}\n"
        )
    )

    if packages:
        pkg_lines = ",\n".join(f"  '{p}'" for p in packages)
        cells.append(code_cell(f"%%R\npackages <- c(\n{pkg_lines}\n)\n"))

    cells.append(md_cell("### Install Missing Packages\n"))
    cells.append(
        code_cell(
            "%%R\n"
            "# Install missing packages\n"
            "#new_packages <- packages[!(packages %in% installed.packages()[,\"Package\"])]\n"
            "#if(length(new_packages)) install.packages(new_packages)\n"
        )
    )

    cells.append(md_cell("### Verify Installation\n"))
    cells.append(
        code_cell(
            "%%R\n"
            'cat("Installed packages:\\n")\n'
            "print(sapply(packages, requireNamespace, quietly = TRUE))\n"
        )
    )

    cells.append(md_cell("### Load Required Libraries\n"))
    cells.append(
        code_cell(
            "%%R\n"
            "invisible(lapply(packages, function(pkg) {\n"
            "  suppressPackageStartupMessages(library(pkg, character.only = TRUE))\n"
            "})\n"
        )
    )

    for code in r_chunks:
        if code.strip().startswith("packages"):
            continue
        if re.search(r"Install missing packages", code, re.IGNORECASE):
            continue
        if re.search(r"Installed packages", code):
            continue
        if re.search(r"suppressPackageStartupMessages\(library", code):
            continue
        if re.search(r"devtools::load_all", code):
            continue
        cells.append(code_cell(f"%%R\n{code}\n"))

    return cells


def emit_body_chunks(chunks: list[tuple[str, str]]) -> list[dict]:
    cells: list[dict] = []
    for kind, body in chunks:
        if kind == "markdown":
            md = clean_markdown(body)
            if md.strip():
                cells.append(md_cell(md))
        else:
            cells.append(code_cell(f"%%R\n{body}\n"))
    return cells


def convert(qmd_path: Path, nb_path: Path) -> None:
    raw = qmd_path.read_text(encoding="utf-8")
    intro_raw, setup_raw, body_raw = split_sections(raw)

    cells: list[dict] = [md_cell(f"![R Banner]({BANNER_URL})\n")]

    intro_chunks = parse_qmd(intro_raw)
    intro_md = "".join(b for k, b in intro_chunks if k == "markdown")
    intro_md = clean_markdown(intro_md)
    intro_md = re.sub(
        r"^\[!\[\]\([^\)]*open_colab[^\)]*\)\]\([^\)]+\)\s*\n?",
        "",
        intro_md,
        flags=re.MULTILINE,
    )
    if intro_md.strip():
        cells.append(md_cell(intro_md))

    cells.append(
        md_cell(
            "## Setup R in Python Runtime - Install {rpy2}\n\n"
            "{rpy2} allows running R code in Colab Python runtime via `%%R` magic.\n"
        )
    )
    cells.append(
        code_cell(
            "!pip uninstall rpy2 -y\n\n"
            "!pip install rpy2==3.5.1\n\n"
            "%load_ext rpy2.ipython\n"
        )
    )
    cells.append(
        md_cell(
            "## Mount Google Drive\n\n"
            "Mount Google Drive if your data or R library folder is stored there.\n"
        )
    )
    cells.append(
        code_cell(
            "from google.colab import drive\n\n"
            "drive.mount('/content/drive')\n"
        )
    )

    cells.extend(build_setup_cells(setup_raw))
    cells.extend(emit_body_chunks(parse_qmd(body_raw)))

    notebook = {
        "cells": cells,
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
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    nb_path.write_text(
        json.dumps(notebook, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    n_code = sum(1 for c in cells if c["cell_type"] == "code")
    n_md = sum(1 for c in cells if c["cell_type"] == "markdown")
    print(f"  {qmd_path.name} -> {nb_path.name} ({n_md} md, {n_code} code)")


def main() -> None:
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    print("Converting timeseries 05-04-02..06 QMD files to Colab notebooks...\n")
    for qmd_name, nb_name in FILES:
        qmd_path = MARKDOWN_DIR / qmd_name
        nb_path = NOTEBOOK_DIR / nb_name
        if not qmd_path.exists():
            print(f"  SKIP (missing): {qmd_name}")
            continue
        convert(qmd_path, nb_path)
    print("\nDone.")


if __name__ == "__main__":
    main()
