import base64
import io
from typing import Optional

import pandas as pd
import matplotlib
import matplotlib.pyplot as plt


matplotlib.use("Agg")  # server-side rendering


def generate_status_chart_base64(
    df: pd.DataFrame,
    *,
    status_col: str = "status",
    title: str = "Task Status Distribution",
) -> str:
    if df.empty or status_col not in df.columns:
        # Return empty string if nothing to plot (frontend can handle)
        return ""

    counts = df[status_col].fillna("Unknown").value_counts()

    plt.figure(figsize=(7, 4))
    plt.bar(counts.index.astype(str), counts.values)
    plt.title(title)
    plt.xlabel("Status")
    plt.ylabel("Count")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=140)
    plt.close()

    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_table_html(
    df: pd.DataFrame,
    *,
    max_rows: Optional[int] = 200,
) -> str:
    if df.empty:
        return "<p>No tasks found.</p>"

    out = df.copy()
    if max_rows is not None:
        out = out.head(max_rows)

    # Basic, readable HTML table (safe for simple internal UI use)
    return out.to_html(index=False, escape=True)
