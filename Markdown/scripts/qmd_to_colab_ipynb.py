#!/usr/bin/env python3
"""Convert Quarto .qmd files to Colab-ready .ipynb with rpy2 %%R magic."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

QMD_DIR = Path("/home/zia207/Github/Causal_Inference_R/Markdown")
OUT_DIR = Path("/home/zia207/Github/Causal_Inference_R/Colab_Notebook")

QMD_FILES = [
    "02-08-01-00-randomized-controlled-trials-introduction-r.qmd",
    "02-08-01-01-randomized-controlled-trials-design-r.qmd",
    "02-08-01-02-randomized-controlled-trials-randomization-r.qmd",
    "02-08-01-03-randomized-controlled-trials-implementation-phase-r.qmd",
    "02-08-02-00-graphical-models-introduction-r.qmd",
    "02-08-02-01-graphical-models-basic-work-example-r.qmd",
    "02-08-02-02-graphical-models-advanced-work-example-r.qmd",
    "02-08-03-00-potential-outcomes-framework-introduction-r.qmd",
    "02-08-03-01-potential-outcomes-framework-causal-estimands-r.qmd",
    "02-08-03-02-potential-outcomes-framework-regression-adjustment-r.qmd",
    "02-08-03-03-potential-outcomes-framework-propensity-score-matching-r.qmd",
    "02-08-03-04-potential-outcomes-framework-doubly-robust-estimators-r.qmd",
    "02-08-03-05-potential-outcomes-framework-difference-in-differences-r.qmd",
    "02-08-03-06-potential-outcomes-framework-instrumental-variable-r.qmd",
    "02-08-03-07-potential-outcomes-framework-regression-discontinuity-design-r.qmd",
    "02-08-03-08-potential-outcomes-framework-g-methods-r.qmd",
    "02-08-04-causal-timeseries-introduction-r.qmd",
    "index.qmd",
]

R_BANNER = "![R Banner](https://drive.google.com/uc?id=1LhRCsnq8s3y0M76oN3-GEUfWQVL_yUv-)\n"

BASE_R_PACKAGES = {"tidyverse"}


def qmd_to_ipynb_name(qmd_name: str) -> str:
    stem = qmd_name.replace(".qmd", "")
    name = stem.replace("-", "_")
    if name == "index":
        return "index_r.ipynb"
    return name + ".ipynb"


def new_id() -> str:
    return str(uuid.uuid4())


def to_source_lines(text: str) -> list[str]:
    """Split text into Jupyter source lines (each line ends with \\n)."""
    if not text:
        return []
    lines = text.splitlines(keepends=True)
    if not lines:
        return [text + "\n"] if text else []
    if not lines[-1].endswith("\n"):
        lines[-1] = lines[-1] + "\n"
    return lines


def md_cell(text: str, cell_id: str | None = None) -> dict:
    cell = {
        "cell_type": "markdown",
        "metadata": {},
        "source": to_source_lines(text),
    }
    if cell_id:
        cell["id"] = cell_id
    return cell


def code_cell(source: str, cell_id: str | None = None) -> dict:
    cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": to_source_lines(source),
    }
    if cell_id:
        cell["id"] = cell_id
    return cell


def convert_callouts(text: str) -> str:
    """Convert Quarto callout divs to markdown blockquotes."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        m = re.match(r"^::: \{?callout-([^\s\}]+)\}?\s*$", stripped)
        if m:
            kind = m.group(1)
            i += 1
            block: list[str] = []
            while i < len(lines) and lines[i].strip() != ":::":
                block.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1  # skip closing :::
            out.append(f"> **Note ({kind})**\n")
            for bl in block:
                for bline in bl.splitlines(keepends=True):
                    if bline.strip().startswith("##"):
                        title = bline.strip().lstrip("#").strip()
                        out.append(f"> **{title}**\n")
                    elif bline.strip():
                        out.append(
                            bline
                            if bline.startswith(">")
                            else "> " + bline.rstrip("\n") + "\n"
                        )
                    else:
                        out.append(">\n")
            out.append("\n")
        else:
            out.append(lines[i])
            i += 1
    return "".join(out)


def clean_markdown(text: str) -> str:
    """Normalize Quarto/Pandoc markdown for Colab."""
    text = convert_callouts(text)
    # Remove remaining fenced div / layout blocks
    text = re.sub(r"^:{3,}.*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"^:::.*$", "", text, flags=re.MULTILINE)

    # Image attributes: ![](path){width="..."} -> ![](path)
    text = re.sub(
        r"(!\[[^\]]*\]\([^)]+\))\{[^}]+\}",
        r"\1",
        text,
    )
    # Linked images with attributes
    text = re.sub(
        r"\[(!\[[^\]]*\]\([^)]+\))\{[^}]+\}\]\(([^)]+)\)",
        r"[\1](\2)",
        text,
    )

    # Header attributes: # Title {.unnumbered}
    text = re.sub(r"\s*\{\.unnumbered\}", "", text)
    text = re.sub(r"\s*\{#([^}]+)\}", "", text)

    # Quarto cross-refs [[42]]
    text = re.sub(r"\[\[\d+\]\]", "", text)

    # Fix escaped underscores in math (common in qmd)
    text = text.replace(r"\_", "_")

    # Collapse excessive blank lines
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip() + "\n"


def extract_packages_from_r(code: str) -> set[str]:
    pkgs: set[str] = set()
    for m in re.finditer(r"library\s*\(\s*([^\s),]+)\s*\)", code):
        pkgs.add(m.group(1).strip())
    for m in re.finditer(r"require\s*\(\s*([^\s),]+)\s*\)", code):
        pkgs.add(m.group(1).strip())
    for m in re.finditer(r"requireNamespace\s*\(\s*['\"]?([^'\"),\s]+)", code):
        pkgs.add(m.group(1).strip())
    for m in re.finditer(
        r"install\.packages\s*\(\s*c?\s*\(?\s*['\"]([^'\"]+)['\"]",
        code,
    ):
        pkgs.add(m.group(1).strip())
    for m in re.finditer(
        r"install\.packages\s*\(\s*c\s*\(\s*([^)]+)\)",
        code,
        re.DOTALL,
    ):
        inner = m.group(1)
        for q in re.findall(r"['\"]([^'\"]+)['\"]", inner):
            pkgs.add(q.strip())
    return pkgs


def is_chunk_option_line(line: str) -> bool:
    s = line.strip()
    return s.startswith("#|") or s.startswith("# |")


def clean_r_code(code: str) -> str:
    lines = code.splitlines()
    cleaned = []
    for line in lines:
        if is_chunk_option_line(line):
            continue
        # Skip commented-only install lines in body (handled in setup)
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def is_setup_only_chunk(code: str) -> bool:
    """Detect chunks that only install/load packages (merged into Colab setup)."""
    lines = [
        ln.strip()
        for ln in code.splitlines()
        if ln.strip() and not is_chunk_option_line(ln) and not ln.strip().startswith("#")
    ]
    if not lines:
        return True
    setup_patterns = (
        r"^install\.packages",
        r"^library\(",
        r"^require\(",
        r"^requireNamespace\(",
        r"^\.libPaths\(",
        r"^packages\s*<-",
        r"^new\.packages\s*<-",
    )
    return all(any(re.match(p, ln) for p in setup_patterns) for ln in lines)


def parse_qmd(content: str) -> tuple[list[tuple[str, str]], set[str]]:
    """
    Parse qmd into list of ('markdown'|'r', content) segments.
    Returns segments and discovered R packages.
    """
    segments: list[tuple[str, str]] = []
    all_packages: set[str] = set()

    chunk_re = re.compile(r"^```\{([^}]*)\}\s*$", re.MULTILINE)
    fence_re = re.compile(r"^```\s*$", re.MULTILINE)

    pos = 0
    while pos < len(content):
        m = chunk_re.search(content, pos)
        if not m:
            tail = content[pos:].strip()
            if tail:
                segments.append(("markdown", tail))
            break

        md_before = content[pos : m.start()].strip()
        if md_before:
            segments.append(("markdown", md_before))

        lang_spec = m.group(1).strip().lower()
        chunk_start = m.end()
        end_m = fence_re.search(content, chunk_start)
        if not end_m:
            tail = content[chunk_start:].strip()
            if tail:
                if lang_spec.startswith("r"):
                    segments.append(("r", tail))
                    all_packages |= extract_packages_from_r(tail)
                else:
                    segments.append(("markdown", f"```{lang_spec}\n{tail}\n```"))
            break

        chunk_body = content[chunk_start : end_m.start()]
        pos = end_m.end()

        if lang_spec.startswith("r"):
            cleaned = clean_r_code(chunk_body)
            if cleaned:
                all_packages |= extract_packages_from_r(cleaned)
                segments.append(("r", cleaned))
        else:
            segments.append(
                ("markdown", f"```{lang_spec}\n{chunk_body.strip()}\n```")
            )

    return segments, all_packages


def setup_cells(packages: set[str]) -> list[dict]:
    """Standard Colab + rpy2 header cells (matches reference notebook)."""
    pkgs = sorted(BASE_R_PACKAGES | packages)
    pkg_lines = ",\n".join(f"          '{p}'" for p in pkgs)
    cells: list[dict] = [
        md_cell(R_BANNER, new_id()),
        md_cell(
            "## Setup R in Python Runtime - Install {rpy2}\n\n"
            "{rpy2} allows running R code in Colab Python runtime via `%%R` magic.\n"
        ),
        code_cell(
            "!pip uninstall rpy2 -y\n"
            "!pip install rpy2==3.5.1\n"
            "%load_ext rpy2.ipython\n"
        ),
        md_cell(
            "## Mount Google Drive\n\n"
            "Mount Google Drive if your data or R library folder is stored there.\n"
        ),
        code_cell(
            "from google.colab import drive\n"
            "drive.mount('/content/drive')\n"
        ),
        md_cell("## Check and Install Required R Packages"),
        code_cell(f"%%R\npackages <- c(\n{pkg_lines}\n)\n"),
        md_cell(
            "``` r\n"
            "#| warning: false\n"
            "#| error: false\n\n"
            "# Install missing packages\n"
            "new.packages <- packages[!(packages %in% installed.packages(lib='drive/My Drive/R/')[,\"Package\"])]\n"
            "if(length(new.packages)) install.packages(new.packages, lib='drive/My Drive/R/')\n"
            "```\n"
        ),
        md_cell("### Verify Installation"),
        code_cell("%%R\n# Verify installation\ncat(\"Installed packages:\\n\")"),
        md_cell("### Load Packages"),
        code_cell(
            "%%R\n"
            "# set library path\n"
            ".libPaths('drive/My Drive/R')\n"
            "# Verify installation\n"
            "cat(\"Installed packages:\\n\")\n"
            "print(sapply(packages, requireNamespace, quietly = TRUE))\n"
        ),
        md_cell("### Check Loaded Packages"),
        code_cell('%%R\n# Check loaded packages\ncat("Successfully loaded packages:\\n")'),
    ]
    return cells


def strip_header_markdown(md: str) -> str:
    """Remove colab link / banner blocks already covered by standard header."""
    lines = md.splitlines()
    out: list[str] = []
    skip_until_content = True
    for line in lines:
        stripped = line.strip()
        if skip_until_content:
            if stripped.startswith("[![]") and "open_colab" in stripped:
                continue
            if stripped.startswith("[![]") and (
                "RENEW_logo" in stripped or "github_R" in stripped
            ):
                continue
            if stripped.startswith("![]") and "banner" in stripped.lower():
                continue
            if stripped.startswith("::::") or stripped.startswith(":::"):
                continue
            if not stripped:
                continue
            skip_until_content = False
        out.append(line)
    return "\n".join(out)


def convert_qmd(qmd_path: Path) -> dict:
    raw = qmd_path.read_text(encoding="utf-8")
    segments, packages = parse_qmd(raw)

    cells: list[dict] = [md_cell(R_BANNER, new_id())]

    # First markdown block (title/overview) before Colab setup, like reference notebook
    rest_segments = segments
    if segments and segments[0][0] == "markdown":
        intro = clean_markdown(strip_header_markdown(segments[0][1]))
        if intro.strip():
            cells.append(md_cell(intro))
        rest_segments = segments[1:]

    cells.extend(setup_cells(packages)[1:])  # skip duplicate banner

    for kind, body in rest_segments:
        if kind == "markdown":
            md = clean_markdown(strip_header_markdown(body))
            if not md.strip():
                continue
            cells.append(md_cell(md))
        else:
            if is_setup_only_chunk(body):
                continue
            r_source = "%%R\n" + body + "\n"
            cells.append(code_cell(r_source))

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
            "colab": {"provenance": []},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    return notebook


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for qmd_name in QMD_FILES:
        qmd_path = QMD_DIR / qmd_name
        if not qmd_path.exists():
            print(f"SKIP (missing): {qmd_name}")
            continue
        nb = convert_qmd(qmd_path)
        out_name = qmd_to_ipynb_name(qmd_name)
        out_path = OUT_DIR / out_name
        out_path.write_text(
            json.dumps(nb, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        n_code = sum(1 for c in nb["cells"] if c["cell_type"] == "code")
        n_md = sum(1 for c in nb["cells"] if c["cell_type"] == "markdown")
        print(f"Wrote {out_name}: {n_md} markdown, {n_code} code cells")


if __name__ == "__main__":
    main()
