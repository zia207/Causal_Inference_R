#!/usr/bin/env python3
"""Convert Deep Causal ML .qmd files to Colab ipynb (matches 05_05_00 reference format)."""

from __future__ import annotations

import json
import re
from pathlib import Path

BANNER_URL = "https://drive.google.com/uc?id=1XhiFy05neEFIKwuP9xN8Th9OBl-LYKbv"
GITHUB_IMG_BASE = "https://raw.githubusercontent.com/zia207/Causal_Inference_R/main/Markdown"
MARKDOWN_DIR = Path("/home/zia207/Github/Causal_Inference_R/Markdown")
NOTEBOOK_DIR = Path("/home/zia207/Github/Causal_Inference_R/Notebook")

FILES = [
    (
        "02-08-05-05-01-01-DeepCausalML-TARNET-r.qmd",
        "02_08_05_05_01_01_deep_causal_ml_tarnet_r.ipynb",
    ),
    (
        "02-08-05-05-01-02-DeepCausalML-CFRTNet-r.qmd",
        "02_08_05_05_01_02_deep_causal_ml_cfrnet_r.ipynb",
    ),
    (
        "02-08-05-05-01-03-DeepCausalML-DragonNet-r.qmd",
        "02_08_05_05_01_03_deep_causal_ml_dragonnet_r.ipynb",
    ),
    (
        "02-08-05-05-01-04-DeepCausalML-GANITE-r.qmd",
        "02_08_05_05_01_04_deep_causal_ml_ganite_r.ipynb",
    ),
]

SETUP_R_MD = (
    "## Setup R in Python Runtime - Install {rpy2}\n\n"
    "{rpy2} allows running R code in Colab Python runtime via `%%R` magic.\n"
)
SETUP_R_CODE = (
    "!pip uninstall rpy2 -y\n\n"
    "!pip install rpy2==3.5.1\n\n"
    "%load_ext rpy2.ipython\n"
)
DRIVE_MD = (
    "## Mount Google Drive\n\n"
    "Mount Google Drive if your data or R library folder is stored there.\n"
)
DRIVE_CODE = (
    "from google.colab import drive\n\n"
    "drive.mount('/content/drive')\n"
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
    """Rewrite local Markdown image paths to GitHub raw URLs."""

    def abs_path(path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{GITHUB_IMG_BASE}/{path.lstrip('/')}"

    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: f"![{m.group(1)}]({abs_path(m.group(2))})",
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
    text = re.sub(r"\n-{10,}\n", "\n\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n" if text.strip() else ""


def strip_chunk_opts(code: str) -> str:
    lines = [ln for ln in code.splitlines() if not ln.strip().startswith("#|")]
    return "\n".join(lines).strip()


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


def split_markdown_at_h2(text: str) -> list[str]:
    text = clean_markdown(text)
    if not text.strip():
        return []
    parts = re.split(r"(?=^## )", text, flags=re.MULTILINE)
    return [p for p in parts if p.strip()]


def is_setup_header(md: str) -> bool:
    return bool(re.search(r"^##\s+Set\s*[Uu]p\b", md, re.MULTILINE))


def is_install_hdr(md: str) -> bool:
    return bool(re.search(r"###\s+Install Missing Packages", md, re.IGNORECASE))


def is_verify_hdr(md: str) -> bool:
    return bool(re.search(r"###\s+Verify Installation", md, re.IGNORECASE))


def is_load_hdr(md: str) -> bool:
    return bool(re.search(r"###\s+Load R Packages", md, re.MULTILINE))


def is_check_hdr(md: str) -> bool:
    return bool(re.search(r"###\s+Check Loaded Packages", md, re.IGNORECASE))


def split_at_setup(raw: str) -> tuple[str, str]:
    m = re.search(r"^(##\s+Set\s*[Uu]p\b)", raw, re.MULTILINE)
    if m:
        return raw[: m.start()], raw[m.start():]
    return raw, ""


def convert(qmd_path: Path, nb_path: Path) -> None:
    raw = qmd_path.read_text(encoding="utf-8")
    intro_raw, setup_raw = split_at_setup(raw)

    cells: list[dict] = [md_cell(f"![R Banner]({BANNER_URL})")]

    intro_chunks = parse_qmd(intro_raw)
    intro_md = "".join(body for kind, body in intro_chunks if kind == "markdown")
    for part in split_markdown_at_h2(intro_md):
        cells.append(md_cell(part))

    cells.append(md_cell(SETUP_R_MD))
    cells.append(code_cell(SETUP_R_CODE))
    cells.append(md_cell(DRIVE_MD))
    cells.append(code_cell(DRIVE_CODE))

    rest_chunks = parse_qmd(setup_raw)
    state = "normal"
    i = 0
    while i < len(rest_chunks):
        kind, body = rest_chunks[i]

        if kind == "markdown":
            md = clean_markdown(body)
            if not md.strip():
                i += 1
                continue

            if is_setup_header(md):
                cells.append(md_cell(md))
                state = "setup"
                i += 1
                continue

            if state == "setup":
                if is_install_hdr(md):
                    cells.append(md_cell("### Install Missing Packages\n"))
                    state = "after_install_hdr"
                elif is_verify_hdr(md):
                    cells.append(md_cell("### Verify Installation\n"))
                    state = "after_verify_hdr"
                elif is_load_hdr(md):
                    cells.append(md_cell("### Load R Packages\n"))
                    state = "after_load_hdr"
                elif is_check_hdr(md):
                    cells.append(md_cell("### Check Loaded Packages\n"))
                    state = "after_check_hdr"
                else:
                    cells.append(md_cell(md))
                i += 1
                continue

            for part in split_markdown_at_h2(md):
                cells.append(md_cell(part))
            i += 1
            continue

        if state == "after_install_hdr":
            cells.append(
                code_cell(
                    "%%R\n"
                    "# Install missing packages\n"
                    "# new_packages <- packages[!(packages %in% installed.packages()[, \"Package\"])]\n"
                    "# if (length(new_packages)) install.packages(new_packages)\n"
                )
            )
            state = "setup"
        elif state == "after_verify_hdr":
            cells.append(
                code_cell(
                    "%%R\n"
                    "# Verify installation\n"
                    "cat(\"Installed packages:\\n\")\n"
                    "print(sapply(packages, requireNamespace, quietly = TRUE))\n"
                )
            )
            state = "setup"
        elif state == "after_load_hdr":
            cells.append(
                code_cell(
                    "%%R\n"
                    "# Load packages with suppressed messages\n"
                    "invisible(lapply(packages, function(pkg) {\n"
                    "  suppressPackageStartupMessages(library(pkg, character.only = TRUE))\n"
                    "}))\n"
                )
            )
            state = "setup"
        elif state == "after_check_hdr":
            cells.append(
                code_cell(
                    "%%R\n"
                    "# Check loaded packages\n"
                    "cat(\"Successfully loaded packages:\\n\")\n"
                    "print(search()[grepl(\"package:\", search())])\n"
                )
            )
            state = "body"
        else:
            cells.append(code_cell(f"%%R\n{body}\n"))

        i += 1

    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "pygments_lexer": "ipython3",
            },
            "colab": {"provenance": [], "toc_visible": True},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
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
    print("Converting Deep Causal ML QMD files to Colab notebooks...\n")
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
