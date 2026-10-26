from pathlib import Path
import numpy as np

from textwrap import fill
from matplotlib import colormaps
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator

from shared.eda_schemas import (
    EDAResult,
    GroupComparison,
    CategoricalComparison,
    PlotArtifact,
)


def save_categorical_bar_chart(
    result: EDAResult,
    column_name: str,
    run_dir: str | Path,
    *,
    plot_index: int = 1,
) -> PlotArtifact:
    if plot_index < 1:
        raise ValueError("plot_index must be positive.")

    if column_name not in result.categorical_summaries:
        raise ValueError(
            f"No categorical summary found for {column_name!r}."
        )

    summary = result.categorical_summaries[column_name]

    if not summary.top_values:
        raise ValueError(
            f"No observed categories to plot for {column_name!r}."
        )

    labels = [
        item.value
        for item in summary.top_values
    ]

    counts = [
        item.count
        for item in summary.top_values
    ]

    if len(set(labels)) != len(labels):
        labels = [
            f"{item.value} ({item.value_type})"
            for item in summary.top_values
        ]

    if summary.other_count > 0:
        labels.append("Other categories (combined)")
        counts.append(summary.other_count)

    relative_path = (
        Path("plots")
        / f"categorical_{plot_index:03d}.png"
    )

    output_path = Path(run_dir) / relative_path

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    title = f"{column_name}: category counts"

    figure = Figure(
        figsize=(9, max(3, 0.5 * len(labels) + 1.5)),
        layout="constrained",
    )

    FigureCanvasAgg(figure)

    axes = figure.subplots()

    positions = list(range(len(labels)))

    bars = axes.barh(
        positions,
        counts,
        color="#2563eb",
    )

    axes.set_yticks(positions, labels=labels)
    axes.invert_yaxis()

    axes.set_xlabel("Count (missing values excluded)")
    axes.set_title(title, parse_math=False)

    for label in axes.get_yticklabels():
        label.set_parse_math(False)

    axes.xaxis.set_major_locator(
        MaxNLocator(integer=True)
    )

    axes.set_xlim(0, max(counts) * 1.2)

    axes.bar_label(bars, padding=3)

    try:
        with output_path.open("xb") as output_file:
            figure.savefig(
                output_file,
                format="png",
                dpi=150,
            )
    finally:
        figure.clear()

    return PlotArtifact(
        column=column_name,
        path=relative_path.as_posix(),
        title=title,
        description=(
            "Counts of stored top categories; remaining known "
            "values are combined when present. "
            "Missing values are excluded."
        ),
    )

def save_correlation_heatmap(
    result: EDAResult,
    run_dir: str | Path,
) -> PlotArtifact | None:
    summary = result.correlation_summary

    if summary is None or len(summary.columns) < 2:
        return None

    columns = summary.columns

    if not any(
        summary.matrix[left][right] is not None
        for left in columns
        for right in columns
        if left != right
    ):
        return None

    matrix = np.array([
        [
            summary.matrix[left][right]
            if summary.matrix[left][right] is not None
            else np.nan
            for right in columns
        ]
        for left in columns
    ])

    size = max(
        6,
        0.7 * len(columns) + 2,
    )

    figure = Figure(
        figsize=(size, size),
        layout="constrained",
    )

    FigureCanvasAgg(figure)

    axes = figure.subplots()

    cmap = colormaps["RdBu_r"].with_extremes(bad="#e5e7eb")

    image = axes.imshow(
        np.ma.masked_invalid(matrix),
        cmap=cmap,
        vmin=-1,
        vmax=1,
    )

    positions = list(
        range(len(columns))
    )

    axes.set_xticks(
        positions,
        labels=columns,
        rotation=45,
        ha="right",
    )

    axes.set_yticks(
        positions,
        labels=columns,
    )

    for label in (
        axes.get_xticklabels()
        + axes.get_yticklabels()
    ):
        label.set_parse_math(False)

    for row, left in enumerate(columns):
        for column, right in enumerate(columns):
            value = summary.matrix[left][right]

            count = (
                summary.pair_counts[left][right]
            )

            text = (
                f"{value:.2f}\nn={count}"
                if value is not None
                else f"N/A\nn={count}"
            )

            axes.text(
                column,
                row,
                text,
                ha="center",
                va="center",
                fontsize=(
                    9 if len(columns) <= 8 else 7
                ),
                color=(
                    "white"
                    if (
                        value is not None
                        and abs(value) > 0.6
                    )
                    else "#111827"
                ),
            )

    title = (
        "Numerical relationships: "
        "Pearson correlation"
    )

    axes.set_title(
        title,
        parse_math=False,
        pad=18,
    )

    figure.colorbar(
        image,
        ax=axes,
        label="Pearson correlation",
        shrink=0.8,
    )

    relative_path = (
        Path("plots")
        / "correlation_heatmap.png"
    )

    output_path = (
        Path(run_dir) / relative_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with output_path.open("xb") as output:
            figure.savefig(
                output,
                format="png",
                dpi=150,
            )
    finally:
        figure.clear()

    return PlotArtifact(
        kind="correlation_heatmap",
        columns=columns,
        path=relative_path.as_posix(),
        title=title,
        description=(
            "Pearson correlations between numerical "
            "columns. Each cell shows the coefficient "
            "and usable row count (n). Missing and "
            "infinite values are excluded per "
            "comparison. N/A means unavailable."
        ),
    )
def save_group_comparison_chart(
    comparison: GroupComparison,
    run_dir: str | Path,
    *,
    plot_index: int = 1,
) -> PlotArtifact:
    if type(plot_index) is not int or plot_index < 1:
        raise ValueError(
            "plot_index must be a positive integer."
        )

    if len(comparison.groups) < 2:
        raise ValueError(
            "At least two groups are required."
        )

    labels = [
        group.value
        for group in comparison.groups
    ]

    if len(set(labels)) != len(labels):
        labels = [
            f"{group.value} ({group.value_type})"
            for group in comparison.groups
        ]

    labels = [
        f"{label} (n={group.count})"
        for label, group in zip(
            labels,
            comparison.groups,
        )
    ]

    means = [
        group.mean
        for group in comparison.groups
    ]

    positions = list(range(len(labels)))

    figure = Figure(
        figsize=(
            9,
            max(3.5, 0.45 * len(labels) + 1.5),
        ),
        layout="constrained",
    )

    FigureCanvasAgg(figure)
    axes = figure.subplots()

    bars = axes.barh(
        positions,
        means,
        color="#2563eb",
    )

    axes.set_yticks(positions, labels=labels)
    axes.invert_yaxis()
    axes.axvline(
        0,
        color="#64748b",
        linewidth=0.8,
    )
    axes.margins(x=0.2)

    axes.set_xlabel(
        f"Mean {comparison.numeric_column}",
        parse_math=False,
    )

    title = (
        f"{comparison.numeric_column} by "
        f"{comparison.category_column}: group averages"
    )

    axes.set_title(title, parse_math=False)

    for label in axes.get_yticklabels():
        label.set_parse_math(False)

    axes.bar_label(
        bars,
        fmt="%.2f",
        padding=4,
    )

    relative_path = (
        Path("plots")
        / f"group_comparison_{plot_index:03d}.png"
    )

    output_path = Path(run_dir) / relative_path
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with output_path.open("xb") as output:
            figure.savefig(
                output,
                format="png",
                dpi=150,
            )
    finally:
        figure.clear()

    return PlotArtifact(
        kind="group_comparison",
        columns=[
            comparison.category_column,
            comparison.numeric_column,
        ],
        path=relative_path.as_posix(),
        title=title,
        description=(
            "Average numerical value within each category. "
            "Labels show usable row counts (n). "
            "These are descriptive averages; uncertainty "
            "and statistical significance are not estimated."
        ),
    )
def save_numeric_distribution_chart(
    result: EDAResult,
    column_name: str,
    run_dir: str | Path,
    *,
    plot_index: int = 1,
) -> PlotArtifact | None:
    if type(plot_index) is not int or plot_index < 1:
        raise ValueError(
            "plot_index must be a positive integer."
        )

    if column_name not in result.numeric_distributions:
        raise ValueError(
            f"No distribution summary for {column_name!r}."
        )

    summary = result.numeric_distributions[column_name]

    if not summary.histogram_counts:
        return None

    edges = np.asarray(summary.histogram_edges)
    counts = summary.histogram_counts

    figure = Figure(
        figsize=(10, 4.5),
        layout="constrained",
    )

    FigureCanvasAgg(figure)

    histogram, box = figure.subplots(
        1,
        2,
        gridspec_kw={"width_ratios": [3, 1]},
    )

    histogram.bar(
        edges[:-1],
        counts,
        width=np.diff(edges),
        align="edge",
        color="#2563eb",
        edgecolor="white",
    )

    histogram.axvline(
        summary.median,
        color="#dc2626",
        linestyle="--",
        label="Median",
    )

    histogram.set_title("Histogram")

    histogram.set_xlabel(
        column_name,
        parse_math=False,
    )

    histogram.set_ylabel("Number of usable rows")

    histogram.yaxis.set_major_locator(
        MaxNLocator(integer=True)
    )

    histogram.legend()

    box.bxp(
        [{
            "q1": summary.q1,
            "med": summary.median,
            "q3": summary.q3,
            "whislo": summary.lower_whisker,
            "whishi": summary.upper_whisker,
            "fliers": summary.outlier_sample,
        }],
        patch_artist=True,
        boxprops={"facecolor": "#93c5fd"},
        medianprops={"color": "#dc2626"},
        flierprops={
            "marker": "o",
            "markersize": 4,
            "markerfacecolor": "#f97316",
            "markeredgecolor": "#f97316",
        },
    )

    box.set_title("Box plot")
    box.set_xticks([])

    box.set_ylabel(
        column_name,
        parse_math=False,
    )

    flagged = (
        "not checked"
        if summary.potential_outlier_count is None
        else str(summary.potential_outlier_count)
    )

    title = (
        f"{column_name}: distribution "
        f"(n={summary.finite_count})"
    )

    figure.suptitle(
        title,
        parse_math=False,
    )

    figure.supxlabel(
        f"Missing: {summary.missing_count} | "
        f"Infinite: {summary.infinite_count} | "
        f"Potential outliers: {flagged}\n"
        "At most 20 flagged values are shown. "
        "Flags need review.",
        fontsize=9,
    )

    relative_path = (
        Path("plots")
        / f"numeric_distribution_{plot_index:03d}.png"
    )

    output_path = Path(run_dir) / relative_path

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with output_path.open("xb") as output:
            figure.savefig(
                output,
                format="png",
                dpi=150,
            )
    finally:
        figure.clear()

    return PlotArtifact(
        kind="numeric_distribution",
        column=column_name,
        columns=[column_name],
        path=relative_path.as_posix(),
        title=title,
        description=(
            "Histogram and box plot of finite values. "
            "Potential outliers use the 1.5 x IQR rule "
            "when available. At most 20 flagged values "
            "are displayed; the saved count includes "
            "all flags. See summary notes."
        ),
    )



def save_categorical_comparison_chart(
    comparison: CategoricalComparison,
    run_dir: str | Path,
    *,
    plot_index: int = 1,
) -> PlotArtifact:
    if type(plot_index) is not int or plot_index < 1:
        raise ValueError(
            "plot_index must be a positive integer."
        )

    counts = np.asarray(
        comparison.counts,
        dtype=int,
    )

    percentages = np.asarray(
        comparison.percentages,
        dtype=float,
    )

    def labels_for(values):
        labels = [
            item.value
            for item in values
        ]

        if len(set(labels)) != len(labels):
            labels = [
                f"{item.value} ({item.value_type})"
                for item in values
            ]

        return [
            fill(label, width=24)
            for label in labels
        ]

    group_labels = labels_for(
        comparison.group_values
    )

    category_labels = labels_for(
        comparison.comparison_values
    )

    group_labels = [
        f"{label} (n={count})"
        for label, count in zip(
            group_labels,
            comparison.group_counts,
        )
    ]

    height = max(
        4,
        0.55 * sum(
            label.count("\n") + 1
            for label in group_labels
        ) + 1.5,
        0.3 * sum(
            label.count("\n") + 1
            for label in category_labels
        ) + 1.5,
    )

    figure = Figure(
        figsize=(10, height),
        layout="constrained",
    )

    FigureCanvasAgg(figure)
    axes = figure.subplots()

    positions = np.arange(len(group_labels))
    left = np.zeros(len(group_labels))
    palette = colormaps["tab10"]

    for column_index, label in enumerate(
        category_labels
    ):
        widths = percentages[:, column_index]
        color = palette(column_index % 10)

        axes.barh(
            positions,
            widths,
            left=left,
            color=color,
            label=label,
        )

        brightness = (
            0.2126 * color[0]
            + 0.7152 * color[1]
            + 0.0722 * color[2]
        )

        text_color = (
            "black"
            if brightness > 0.55
            else "white"
        )

        for row_index, width in enumerate(widths):
            if width >= 10:
                axes.text(
                    left[row_index] + width / 2,
                    positions[row_index],
                    f"{width:.1f}%\n"
                    f"{counts[row_index, column_index]} rows",
                    ha="center",
                    va="center",
                    color=text_color,
                    fontsize=9,
                )

        left += widths

    axes.set_yticks(
        positions,
        labels=group_labels,
    )

    axes.invert_yaxis()
    axes.set_xlim(0, 100)

    axes.set_xlabel(
        "Percentage within each usable group (%)"
    )

    axes.set_ylabel(
        comparison.group_column,
        parse_math=False,
    )

    for label in axes.get_yticklabels():
        label.set_parse_math(False)

    title = (
        f"{comparison.comparison_column} within "
        f"{comparison.group_column}"
    )

    axes.set_title(
        title,
        parse_math=False,
    )

    legend = axes.legend(
        title=comparison.comparison_column,
        loc="upper left",
        bbox_to_anchor=(1.02, 1),
        frameon=False,
        fontsize=9,
    )

    legend.get_title().set_parse_math(False)

    for label in legend.get_texts():
        label.set_parse_math(False)

    figure.supxlabel(
        f"Usable rows: {comparison.usable_rows} | "
        f"Excluded rows: {comparison.excluded_rows}\n"
        "Small segments may be unlabelled. "
        "Percentages are descriptive.",
        fontsize=9,
    )

    relative_path = (
        Path("plots")
        / f"categorical_comparison_{plot_index:03d}.png"
    )

    output_path = Path(run_dir) / relative_path

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        with output_path.open("xb") as output:
            figure.savefig(
                output,
                format="png",
                dpi=150,
            )
    finally:
        figure.clear()

    return PlotArtifact(
        kind="categorical_comparison",
        columns=[
            comparison.group_column,
            comparison.comparison_column,
        ],
        path=relative_path.as_posix(),
        title=title,
        description=(
            "100% stacked bars show category percentages "
            "within each usable group. Group labels show "
            "usable row counts (n). Counts and full "
            "percentages are saved in the report."
        ),
    )
def save_target_charts(
    result: EDAResult,
    run_dir: str | Path,
) -> list[PlotArtifact]:
    focus = result.target_analysis

    if focus is None:
        return []

    saved = []

    def already_saved(kind, columns):
        return any(
            plot.kind == kind
            and (
                plot.columns == columns
                or (
                    len(columns) == 1
                    and plot.column == columns[0]
                )
            )
            for plot in result.plots + saved
        )

    column = focus.config.target_column

    if focus.config.task_type == "classification":
        if (
            focus.class_summary is not None
            and focus.class_summary.top_values
            and not already_saved(
                "categorical_bar",
                [column],
            )
        ):
            saved.append(
                save_categorical_bar_chart(
                    result=result,
                    column_name=column,
                    run_dir=run_dir,
                    plot_index=(
                        len(result.categorical_columns) + 1
                    ),
                )
            )

    elif not already_saved(
        "numeric_distribution",
        [column],
    ):
        plot = save_numeric_distribution_chart(
            result=result,
            column_name=column,
            run_dir=run_dir,
            plot_index=len(result.numeric_columns) + 1,
        )

        if plot is not None:
            saved.append(plot)

    for index, comparison in enumerate(
        focus.group_comparisons,
        start=len(result.group_comparisons) + 1,
    ):
        columns = [
            comparison.category_column,
            comparison.numeric_column,
        ]

        if not already_saved(
            "group_comparison",
            columns,
        ):
            saved.append(
                save_group_comparison_chart(
                    comparison=comparison,
                    run_dir=run_dir,
                    plot_index=index,
                )
            )

    for index, comparison in enumerate(
        focus.categorical_comparisons,
        start=len(result.categorical_comparisons) + 1,
    ):
        columns = [
            comparison.group_column,
            comparison.comparison_column,
        ]

        if not already_saved(
            "categorical_comparison",
            columns,
        ):
            saved.append(
                save_categorical_comparison_chart(
                    comparison=comparison,
                    run_dir=run_dir,
                    plot_index=index,
                )
            )

    focus.plot_paths = [
        plot.path
        for plot in result.plots + saved
        if (
            plot.column == column
            or column in plot.columns
        )
    ]

    return saved

def save_time_charts(
    result: EDAResult,
    run_dir: str | Path,
    *,
    include_counts: bool = True,
    numeric_columns: list[str] | None = None,
    plot_index_start: int = 0,
) -> list[PlotArtifact]:
    analysis = result.time_analysis

    if analysis is None or not analysis.period_starts:
        return []
    if type(include_counts) is not bool:
        raise ValueError(
            "include_counts must be Boolean."
        )

    if (
        type(plot_index_start) is not int
        or plot_index_start < 0
    ):
        raise ValueError(
            "plot_index_start must be a non-negative integer."
        )
    saved = []
    date_column = analysis.config.date_column

    eligible = [
        name
        for name, trend in analysis.numeric_trends.items()
        if sum(
            mean is not None
            for mean in trend.means
        ) >= 2
    ]

    if numeric_columns is None:
        eligible = eligible[:6]

    else:
        if (
            set(numeric_columns)
            - set(analysis.numeric_trends)
        ):
            raise ValueError(
                "An unavailable numerical time "
                "column was requested."
            )

        eligible = [
            name
            for name in numeric_columns
            if name in eligible
        ]

    series = (
        [None] if include_counts else []
    ) + eligible

    for index, name in enumerate(
        series,
        start=plot_index_start,
    ):
        kind = (
            "time_row_counts"
            if name is None
            else "time_numeric_mean"
        )

        columns = (
            [date_column]
            if name is None
            else [date_column, name]
        )

        if any(
            plot.kind == kind
            and plot.columns == columns
            for plot in result.plots + saved
        ):
            continue

        figure = Figure(
            figsize=(10, 4.5),
            layout="constrained",
        )

        FigureCanvasAgg(figure)
        axes = figure.subplots()

        positions = np.arange(
            len(analysis.period_starts)
        )

        if name is None:
            bars = axes.bar(
                positions,
                analysis.row_counts,
                color="#2563eb",
            )

            axes.set_ylabel("Uploaded rows")

            axes.yaxis.set_major_locator(
                MaxNLocator(integer=True)
            )

            if len(positions) <= 12:
                axes.bar_label(
                    bars,
                    padding=3,
                )

            title = (
                "Uploaded rows over time: "
                f"{date_column}"
            )

            relative_path = (
                Path("plots") / "time_rows.png"
            )

        else:
            trend = analysis.numeric_trends[name]

            values = np.array([
                np.nan if value is None else value
                for value in trend.means
            ])

            axes.plot(
                positions,
                values,
                marker="o",
                color="#2563eb",
                linewidth=1.8,
            )

            axes.set_ylabel(
                f"Average {name}",
                parse_math=False,
            )

            if len(positions) <= 12:
                for position, value, count in zip(
                    positions,
                    values,
                    trend.counts,
                ):
                    if np.isfinite(value):
                        axes.annotate(
                            f"n={count}",
                            (position, value),
                            xytext=(0, 7),
                            textcoords="offset points",
                            ha="center",
                            fontsize=8,
                        )

            title = (
                f"Average {name} by "
                f"{analysis.config.frequency}"
            )

            relative_path = (
                Path("plots")
                / f"time_mean_{index:03d}.png"
            )

        ticks = np.unique(
            np.linspace(
                0,
                len(positions) - 1,
                min(8, len(positions)),
                dtype=int,
            )
        )

        axes.set_xticks(
            ticks,
            labels=[
                analysis.period_starts[i]
                for i in ticks
            ],
            rotation=30,
            ha="right",
        )

        axes.set_xlabel(
            f"{analysis.config.frequency.capitalize()} "
            "starting (UTC)"
        )

        axes.set_title(
            title,
            parse_math=False,
        )

        axes.grid(axis="y", alpha=0.2)
        axes.margins(x=0.03, y=0.15)

        figure.supxlabel(
            f"Rows with usable dates: {analysis.usable_rows} | "
            f"Excluded dates: {analysis.excluded_rows}\n"
            "Empty periods have no numerical average. "
            "No gaps are filled.",
            fontsize=9,
        )

        output_path = Path(run_dir) / relative_path

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            with output_path.open("xb") as output:
                figure.savefig(
                    output,
                    format="png",
                    dpi=150,
                )
        finally:
            figure.clear()

        saved.append(
            PlotArtifact(
                kind=kind,
                column=(
                    date_column
                    if name is None
                    else name
                ),
                columns=columns,
                path=relative_path.as_posix(),
                title=title,
                description=(
                    "Uploaded row counts per calendar period."
                    if name is None
                    else
                    "Average finite numerical value per "
                    "calendar period. Missing means create "
                    "gaps. Per-period usable counts are "
                    "stored in time_analysis."
                ),
            )
        )

    analysis.plot_paths = [
        plot.path
        for plot in result.plots + saved
        if (
            plot.kind in {
                "time_row_counts",
                "time_numeric_mean",
            }
            and plot.columns
            and plot.columns[0] == date_column
        )
    ]

    return saved
