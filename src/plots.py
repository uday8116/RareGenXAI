"""Generate evaluation figures from measured results; never fabricate numbers."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def main():
    source = Path("results/synthetic_summary.csv")
    if not source.exists():
        raise FileNotFoundError("Run python -m src.evaluate first")
    df = pd.read_csv(source)
    out = Path("results")
    for metric in ("top1", "top5", "mrr"):
        fig, ax = plt.subplots(figsize=(7, 4))
        for (method, quality), group in df.groupby(["method", "quality"]):
            group = group.sort_values("missing_rate")
            ax.plot(group["missing_rate"] * 100, group[metric], marker="o",
                    label=f"{method}, evidence weights={quality}")
        ax.set_xlabel("Missing phenotype observations (%)")
        ax.set_ylabel(metric.upper())
        ax.set_ylim(0, 1)
        ax.set_title(f"Synthetic benchmark: {metric.upper()} vs missingness")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out / f"{metric}_vs_missingness.png", dpi=160)
        plt.close(fig)
    print("Generated three figures from results/synthetic_summary.csv")

if __name__ == "__main__":
    main()
