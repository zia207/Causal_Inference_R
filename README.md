# Causal Inference in R

A comprehensive, hands-on guide to causal inference methods implemented in R — from randomized trials and DAGs through potential outcomes, time-series methods, and causal machine learning.

**Website:** [https://zia207.github.io/Causal_Inference_R/](https://zia207.github.io/Causal_Inference_R/)

## Overview

This repository contains tutorial notebooks and Quarto documents covering causal inference theory and practice in R. Each chapter includes runnable code, worked examples, and references to the underlying methods and literature.

Topics include:

- **Randomized Controlled Trials (RCTs)** — design, randomization, and implementation
- **Directed Acyclic Graphs (DAGs)** — graphical models, backdoor criterion, frontdoor criterion
- **Potential Outcomes Framework** — matching, DiD, IV, RDD, G-methods, doubly robust estimators
- **Temporal Causal Inference** — VAR/Granger, interrupted time series, panel methods, longitudinal G-methods
- **Causal Machine Learning** — causal trees/forests, meta-learners, uplift models, double ML, deep causal learning (NOTEARS, DAG-GNN, transformers, counterfactual models, and more)

## Repository structure

| Path | Description |
|------|-------------|
| [`Markdown/`](Markdown/) | Quarto source (`.qmd`) and website configuration (`_quarto.yml`) |
| [`Markdown/docs/`](Markdown/docs/) | Rendered HTML site (GitHub Pages output) |
| [`Notebook/`](Notebook/) | Jupyter notebooks (Colab-compatible) |
| [`Data/`](Data/) | Datasets used in tutorials |
| [`Image/`](Image/) | Figures and banners |

## Getting started

### Prerequisites

- [R](https://cran.r-project.org/) (4.x recommended)
- [Quarto](https://quarto.org/docs/get-started/) (for building the website)
- R packages as needed per chapter (e.g. `tidyverse`, `grf`, `RCausalML`, `torch`)

### Build the website locally

```bash
cd Markdown
quarto render
```

Preview in the browser:

```bash
quarto preview
```

### Run a notebook

Open any file in [`Notebook/`](Notebook/) in Jupyter, RStudio, or [Google Colab](https://colab.research.google.com/). Notebooks mirror the Quarto chapters and include install checks for required packages.

## Publish to GitHub Pages

The site is built from `Markdown/docs/`. After rendering:

```bash
cd Markdown
quarto publish gh-pages
```

Then enable **GitHub Pages** in the repository settings: branch `gh-pages`, folder `/ (root)`.

For automatic deployment on push, add a GitHub Actions workflow that runs `quarto render` in `Markdown/` and deploys `Markdown/docs/` via `actions/deploy-pages`.

## Related projects

- **[RCausalML](https://github.com/zia207/RCausalML)** — R package for causal inference with machine learning (many tutorials here use this package)
- **[R Data Science & Environment](https://sites.google.com/view/r-data-sci-env/home)** — broader R tutorials and resources

## Author

**Zia Ahmed** — [Upatta Analytics](https://www.linkedin.com/in/zia-ahmed207)

## License

Content is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) unless otherwise noted.
