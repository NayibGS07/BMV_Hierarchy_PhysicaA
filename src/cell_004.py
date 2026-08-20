# --- Notebook code cell 4 ---

import os, re, math, json, hashlib, logging, warnings, sys, platform
from pathlib import Path
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Tuple
from itertools import combinations
from collections import Counter

# NOTE: no global warnings.filterwarnings("ignore") here. A blanket
# suppression hides RuntimeWarnings (invalid values, overflow, division by
# zero) that can indicate real numerical problems, not just noise -- for a
# scientific pipeline whose output feeds a paper, silently discarding those
# is worse than the visual clutter of seeing them. The one well-understood,
# expected warning (statsmodels' KPSS InterpolationWarning, which fires
# whenever the test statistic falls outside the tabulated critical-value
# range -- a normal occurrence, not a defect) is still suppressed locally
# and narrowly inside test_gd_stationarity, not globally here.

import numpy as np
import pandas as pd
import matplotlib
# Embed TrueType (Type 42) fonts in PDF/PS output instead of matplotlib's
# default bitmap Type 3 fonts. This is the single most important setting
# for publication-quality vector figures: text stays sharp and selectable
# at any zoom level in the compiled PDF, and Elsevier/Physica A production
# systems handle Type 42 correctly (Type 3 fonts are a common cause of
# blurry text or rejected figures at proof stage).
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.rcParams["svg.fonttype"] = "none"
matplotlib.rcParams["font.family"] = "serif"  # matches typical LaTeX body font
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import networkx as nx
import yfinance as yf
from scipy.spatial.distance import squareform
from scipy.cluster.hierarchy import dendrogram, linkage as sp_linkage, cophenet
from scipy.stats import jarque_bera, pearsonr, spearmanr, rankdata
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree as scipy_minimum_spanning_tree
from tqdm import tqdm

try:
    from IPython.display import display, HTML
    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False

try:
    from statsmodels.stats.multitest import multipletests
    HAS_STATSMODELS = True
except ImportError:

    raise ImportError(
        "statsmodels is required and was not found. Run the Setup cell "
        "at the top of this notebook (which installs it), then restart "
        "the kernel and run all cells again. Do NOT proceed without it: "
        "BH-corrected significance and ADF/KPSS stationarity results are "
        "not valid without it."
    )

try:
    get_ipython
    plt.ion()
except NameError:
    pass

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s  %(levelname)-8s  %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("BMV-PhysicaA")

# ── Display helper ────────────────────────────────────────────────────────────
def show(df: pd.DataFrame, title: str = "", max_rows: int = 60) -> None:
    """Display DataFrame with informative title in notebook."""
    if HAS_IPYTHON:
        if title:
            display(HTML(f"<h4 style='color:#1565C0;margin-bottom:4px'>{title}</h4>"))
        display(df.head(max_rows))
    else:
        if title:
            print(f"\n{'─'*60}\n{title}\n{'─'*60}")
        print(df.head(max_rows).to_string())
