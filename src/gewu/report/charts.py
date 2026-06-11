"""研报配图：价格走势与估值带（matplotlib，Agg 后端，无 GUI 依赖）。"""

from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from gewu.data.bundle import DataBundle  # noqa: E402

logger = logging.getLogger(__name__)

plt.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "Hiragino Sans GB",
    "Heiti SC",
    "Microsoft YaHei",
    "Noto Sans CJK SC",
    "SimHei",
    "Arial Unicode MS",
]
plt.rcParams["axes.unicode_minus"] = False


def render_charts(bundle: DataBundle, out_dir: Path) -> list[tuple[str, str]]:
    """生成图表并返回 [(标题, 相对文件名)]；单图失败不影响整体。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    charts: list[tuple[str, str]] = []
    for title, filename, renderer in (
        ("价格与均线", f"{bundle.symbol}_{bundle.as_of}_price.png", _render_price),
        ("估值历史", f"{bundle.symbol}_{bundle.as_of}_valuation.png", _render_valuation),
    ):
        try:
            if renderer(bundle, out_dir / filename):
                charts.append((title, filename))
        except Exception as error:
            logger.warning("图表 %s 生成失败: %s", title, error)
    return charts


def _render_price(bundle: DataBundle, path: Path) -> bool:
    df = bundle.daily.tail(250)
    if df.empty:
        return False
    fig, (ax_price, ax_volume) = plt.subplots(
        2, 1, figsize=(10, 6), sharex=True, height_ratios=[3, 1], constrained_layout=True
    )
    ax_price.plot(df["date"], df["close"], label="收盘价", linewidth=1.4)
    for column, label in (("ma20", "MA20"), ("ma60", "MA60")):
        if column in df.columns:
            ax_price.plot(df["date"], df[column], label=label, linewidth=0.9, alpha=0.85)
    ax_price.set_title(f"{bundle.name}（{bundle.symbol}）近一年走势 ｜ 截至 {bundle.as_of}")
    ax_price.legend(loc="best", fontsize=9)
    ax_price.grid(alpha=0.25)
    if "volume" in df.columns:
        ax_volume.bar(df["date"], df["volume"], width=1.0, alpha=0.5)
        ax_volume.set_ylabel("成交量")
        ax_volume.grid(alpha=0.25)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


def _render_valuation(bundle: DataBundle, path: Path) -> bool:
    valuation = bundle.valuation
    if valuation is None or valuation.empty:
        return False
    column, label = ("pe_ttm", "PE(TTM)") if "pe_ttm" in valuation.columns else ("pe_static", "PE(静态)")
    if column not in valuation.columns:
        return False
    df = valuation.tail(1250).dropna(subset=[column])
    if df.empty:
        return False
    series = df[column]
    fig, ax = plt.subplots(figsize=(10, 4), constrained_layout=True)
    ax.plot(df["date"], series, linewidth=1.2, label=label)
    for quantile, style in ((0.2, ":"), (0.5, "--"), (0.8, ":")):
        ax.axhline(
            series.quantile(quantile),
            linestyle=style,
            alpha=0.6,
            color="gray",
            label=f"{int(quantile * 100)}分位",
        )
    ax.set_title(f"{bundle.name}（{bundle.symbol}）{label} 五年走廊 ｜ 截至 {bundle.as_of}")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.25)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True
