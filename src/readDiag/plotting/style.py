"""
Reusable Matplotlib styling helpers for readDiag.

This module provides a Nature-inspired figure style while preserving the
historical ``PlotConfig`` API used by older plotting code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, Union
import string
import warnings

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import to_rgb
from matplotlib.figure import Figure


FigureKind = Literal["single", "double", "wide", "extended", "custom"]
FigureMode = Literal["main", "extended", "review"]
ExportFormat = Literal["pdf", "eps", "svg", "png", "tiff", "tif", "jpg", "jpeg"]

__all__ = ["NatureFigureStyle", "PlotConfig", "use_nature_style"]


@dataclass
class NatureFigureStyle:
    """Matplotlib helper for producing Nature-inspired scientific figures."""

    base_fontsize: float = 6.0
    min_fontsize: float = 5.0
    max_fontsize: float = 7.0
    panel_label_size: float = 8.0

    font_family: str = "Arial"
    fallback_fonts: Tuple[str, ...] = (
        "Arial",
        "Helvetica",
        "DejaVu Sans",
        "Liberation Sans",
    )

    dpi: int = 450
    line_width: float = 0.6
    axis_width: float = 0.5
    tick_length: float = 2.5
    marker_size: float = 3.0

    use_grid: bool = False
    grid_alpha: float = 0.25
    grid_width: float = 0.35

    single_column_width_mm: float = 89.0
    double_column_width_mm: float = 183.0
    max_main_height_mm: float = 170.0
    extended_width_mm: float = 180.0
    extended_height_mm: float = 170.0

    palette: Dict[str, str] = field(default_factory=lambda: {
        "black": "#000000",
        "orange": "#E69F00",
        "sky_blue": "#56B4E9",
        "bluish_green": "#009E73",
        "yellow": "#F0E442",
        "blue": "#0072B2",
        "vermillion": "#D55E00",
        "reddish_purple": "#CC79A7",
    })

    def mm_to_inch(self, value_mm: float) -> float:
        """Convert millimetres to inches."""
        return value_mm / 25.4

    def inch_to_mm(self, value_inch: float) -> float:
        """Convert inches to millimetres."""
        return value_inch * 25.4

    def get_palette(self, include_black: bool = False) -> List[str]:
        """Return a colour-blind-accessible palette."""
        keys = list(self.palette.keys())
        if not include_black and "black" in keys:
            keys.remove("black")
        return [self.palette[k] for k in keys]

    def set_global_style(self) -> None:
        """Configure Matplotlib rcParams for Nature-inspired figures."""
        mpl.rcParams.update({
            "font.family": "sans-serif",
            "font.sans-serif": list(self.fallback_fonts),
            "font.size": self.base_fontsize,
            "axes.titlesize": self.max_fontsize,
            "axes.labelsize": self.base_fontsize,
            "xtick.labelsize": self.min_fontsize,
            "ytick.labelsize": self.min_fontsize,
            "legend.fontsize": self.min_fontsize,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "lines.linewidth": self.line_width,
            "lines.markersize": self.marker_size,
            "patch.linewidth": self.line_width,
            "axes.linewidth": self.axis_width,
            "axes.grid": self.use_grid,
            "axes.spines.top": True,
            "axes.spines.right": True,
            "axes.edgecolor": "black",
            "axes.labelcolor": "black",
            "xtick.color": "black",
            "ytick.color": "black",
            "xtick.major.width": self.axis_width,
            "ytick.major.width": self.axis_width,
            "xtick.major.size": self.tick_length,
            "ytick.major.size": self.tick_length,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.frameon": False,
            "legend.handlelength": 1.2,
            "legend.borderaxespad": 0.4,
            "figure.dpi": 150,
            "savefig.dpi": self.dpi,
            "savefig.transparent": False,
            "savefig.facecolor": "white",
            "savefig.edgecolor": "white",
            "figure.facecolor": "white",
            "figure.constrained_layout.use": True,
        })
        mpl.rcParams["axes.prop_cycle"] = mpl.cycler(color=self.get_palette())

    def _size_mm(
        self,
        kind: FigureKind = "single",
        height_mm: Optional[float] = None,
        width_mm: Optional[float] = None,
        aspect: float = 0.75,
    ) -> Tuple[float, float]:
        """Resolve figure size in millimetres."""
        if kind == "single":
            width = self.single_column_width_mm
        elif kind in {"double", "wide"}:
            width = self.double_column_width_mm
        elif kind == "extended":
            width = self.extended_width_mm
        elif kind == "custom":
            if width_mm is None:
                raise ValueError("width_mm must be provided when kind='custom'.")
            width = float(width_mm)
        else:
            raise ValueError(f"Unknown figure kind: {kind}")

        height = float(height_mm) if height_mm is not None else width * aspect
        max_height = self.extended_height_mm if kind == "extended" else self.max_main_height_mm
        if height > max_height:
            warnings.warn(
                f"Requested height {height:.1f} mm exceeds recommended maximum "
                f"{max_height:.1f} mm for kind='{kind}'.",
                UserWarning,
            )
        return width, height

    def create_figure(
        self,
        kind: FigureKind = "single",
        height_mm: Optional[float] = None,
        width_mm: Optional[float] = None,
        aspect: float = 0.75,
        nrows: int = 1,
        ncols: int = 1,
        sharex: bool = False,
        sharey: bool = False,
        squeeze: bool = True,
        **subplots_kwargs,
    ):
        """Create a new Matplotlib figure using Nature-inspired dimensions."""
        self.set_global_style()
        width_mm_resolved, height_mm_resolved = self._size_mm(
            kind=kind,
            height_mm=height_mm,
            width_mm=width_mm,
            aspect=aspect,
        )
        figsize = (
            self.mm_to_inch(width_mm_resolved),
            self.mm_to_inch(height_mm_resolved),
        )
        fig, axes = plt.subplots(
            nrows=nrows,
            ncols=ncols,
            figsize=figsize,
            sharex=sharex,
            sharey=sharey,
            squeeze=squeeze,
            constrained_layout=True,
            **subplots_kwargs,
        )
        self.apply_to_figure(fig)
        return fig, axes

    def create_multipanel_figure(
        self,
        nrows: int,
        ncols: int,
        kind: FigureKind = "double",
        height_mm: Optional[float] = None,
        width_mm: Optional[float] = None,
        aspect: float = 0.65,
        label_panels: bool = True,
        **kwargs,
    ):
        """Create a multi-panel figure with optional lowercase panel labels."""
        fig, axes = self.create_figure(
            kind=kind,
            height_mm=height_mm,
            width_mm=width_mm,
            aspect=aspect,
            nrows=nrows,
            ncols=ncols,
            squeeze=False,
            **kwargs,
        )
        axes_flat = list(axes.ravel())
        if label_panels:
            self.add_panel_labels(fig, axes_flat)
        return fig, axes_flat

    def apply_to_figure(self, fig: Figure) -> Figure:
        """Apply styling to all axes in an existing figure."""
        for ax in fig.get_axes():
            self.apply_to_axes(ax)
        return fig

    def apply_to_axes(
        self,
        ax: Axes,
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        title: Optional[str] = None,
        despine_top: bool = False,
        despine_right: bool = False,
        grid: Optional[bool] = None,
    ) -> Axes:
        """Apply Nature-inspired styling to an Axes object."""
        if xlabel is not None:
            ax.set_xlabel(xlabel, fontsize=self.base_fontsize, color="black")
        if ylabel is not None:
            ax.set_ylabel(ylabel, fontsize=self.base_fontsize, color="black")
        if title is not None:
            ax.set_title(title, fontsize=self.max_fontsize, color="black", pad=3)

        for spine in ax.spines.values():
            spine.set_linewidth(self.axis_width)
            spine.set_color("black")

        if despine_top:
            ax.spines["top"].set_visible(False)
        if despine_right:
            ax.spines["right"].set_visible(False)

        ax.tick_params(
            axis="both",
            which="major",
            labelsize=self.min_fontsize,
            width=self.axis_width,
            length=self.tick_length,
            direction="out",
            colors="black",
        )
        ax.tick_params(
            axis="both",
            which="minor",
            width=max(self.axis_width * 0.8, 0.25),
            length=max(self.tick_length * 0.6, 1.0),
            direction="out",
            colors="black",
        )

        use_grid = self.use_grid if grid is None else grid
        if use_grid:
            ax.grid(
                True,
                linewidth=self.grid_width,
                alpha=self.grid_alpha,
                color="0.5",
            )
        else:
            ax.grid(False)

        ax.xaxis.label.set_color("black")
        ax.yaxis.label.set_color("black")
        ax.title.set_color("black")

        legend = ax.get_legend()
        if legend is not None:
            legend.set_frame_on(False)
            for text in legend.get_texts():
                text.set_fontsize(self.min_fontsize)
                text.set_color("black")

        return ax

    def add_panel_labels(
        self,
        fig: Figure,
        axes: Optional[Sequence[Axes]] = None,
        labels: Optional[Sequence[str]] = None,
        x: float = -0.10,
        y: float = 1.04,
    ) -> None:
        """Add lowercase bold panel labels to axes."""
        if axes is None:
            axes = fig.get_axes()
        if labels is None:
            labels = list(string.ascii_lowercase[: len(axes)])
        for ax, label in zip(axes, labels):
            ax.text(
                x,
                y,
                label,
                transform=ax.transAxes,
                fontsize=self.panel_label_size,
                fontweight="bold",
                fontstyle="normal",
                va="bottom",
                ha="left",
                color="black",
            )

    def despine(
        self,
        ax: Axes,
        top: bool = True,
        right: bool = True,
        left: bool = False,
        bottom: bool = False,
    ) -> Axes:
        """Hide selected spines."""
        ax.spines["top"].set_visible(not top)
        ax.spines["right"].set_visible(not right)
        ax.spines["left"].set_visible(not left)
        ax.spines["bottom"].set_visible(not bottom)
        return ax

    def set_axis_labels(
        self,
        ax: Axes,
        xlabel: str,
        ylabel: str,
        require_units: bool = True,
    ) -> Axes:
        """Set axis labels and optionally warn if units are missing."""
        if require_units:
            for name, label in {"x": xlabel, "y": ylabel}.items():
                if "(" not in label or ")" not in label:
                    warnings.warn(
                        f"{name}-axis label '{label}' may be missing units in parentheses.",
                        UserWarning,
                    )
        ax.set_xlabel(xlabel, fontsize=self.base_fontsize, color="black")
        ax.set_ylabel(ylabel, fontsize=self.base_fontsize, color="black")
        return ax

    def style_legend(self, ax: Axes, loc: str = "best", ncol: int = 1, **kwargs):
        """Create or restyle a legend using black text and no frame."""
        legend = ax.legend(
            loc=loc,
            ncol=ncol,
            frameon=False,
            fontsize=self.min_fontsize,
            **kwargs,
        )
        for text in legend.get_texts():
            text.set_color("black")
            text.set_fontsize(self.min_fontsize)
        return legend

    def contrast_ratio(self, color1: str, color2: str) -> float:
        """Compute WCAG contrast ratio between two colours."""
        def relative_luminance(rgb):
            values = []
            for c in rgb:
                if c <= 0.03928:
                    values.append(c / 12.92)
                else:
                    values.append(((c + 0.055) / 1.055) ** 2.4)
            r, g, b = values
            return 0.2126 * r + 0.7152 * g + 0.0722 * b

        rgb1 = to_rgb(color1)
        rgb2 = to_rgb(color2)
        l1 = relative_luminance(rgb1)
        l2 = relative_luminance(rgb2)
        lighter = max(l1, l2)
        darker = min(l1, l2)
        return (lighter + 0.05) / (darker + 0.05)

    def validate_figure(
        self,
        fig: Figure,
        mode: FigureMode = "main",
        target_format: Optional[ExportFormat] = None,
        check_units: bool = True,
        check_contrast: bool = True,
        max_axes: int = 12,
    ) -> List[str]:
        """Validate a figure against key Nature-inspired checks."""
        issues: List[str] = []
        width_mm = self.inch_to_mm(fig.get_figwidth())
        height_mm = self.inch_to_mm(fig.get_figheight())

        if mode == "extended":
            max_width = self.extended_width_mm
            max_height = self.extended_height_mm
        else:
            max_width = self.double_column_width_mm
            max_height = self.max_main_height_mm

        if width_mm > max_width + 0.5:
            issues.append(
                f"Figure width is {width_mm:.1f} mm; recommended maximum is "
                f"{max_width:.1f} mm for mode='{mode}'."
            )
        if height_mm > max_height + 0.5:
            issues.append(
                f"Figure height is {height_mm:.1f} mm; recommended maximum is "
                f"{max_height:.1f} mm for mode='{mode}'."
            )

        axes = fig.get_axes()
        if len(axes) > max_axes:
            issues.append(
                f"Figure contains {len(axes)} axes/panels. Check whether the "
                "composition is too dense or should be split."
            )

        for ax_idx, ax in enumerate(axes, start=1):
            x_grid_on = any(line.get_visible() for line in ax.get_xgridlines())
            y_grid_on = any(line.get_visible() for line in ax.get_ygridlines())
            if x_grid_on or y_grid_on:
                issues.append(
                    f"Axes {ax_idx}: background gridlines are visible. "
                    "Nature generally asks authors to avoid them."
                )

            if check_units:
                xlabel = ax.get_xlabel()
                ylabel = ax.get_ylabel()
                if xlabel and ("(" not in xlabel or ")" not in xlabel):
                    issues.append(
                        f"Axes {ax_idx}: x-label '{xlabel}' may be missing units in parentheses."
                    )
                if ylabel and ("(" not in ylabel or ")" not in ylabel):
                    issues.append(
                        f"Axes {ax_idx}: y-label '{ylabel}' may be missing units in parentheses."
                    )

            texts = list(ax.texts)
            texts.extend([ax.title, ax.xaxis.label, ax.yaxis.label])
            texts.extend(ax.get_xticklabels())
            texts.extend(ax.get_yticklabels())
            legend = ax.get_legend()
            if legend is not None:
                texts.extend(legend.get_texts())

            for text in texts:
                if not text.get_visible():
                    continue
                content = text.get_text()
                size = text.get_fontsize()
                if content and size < self.min_fontsize:
                    issues.append(
                        f"Axes {ax_idx}: text '{content[:30]}' has size "
                        f"{size:.1f} pt, below {self.min_fontsize:.1f} pt."
                    )
                is_panel_label = (
                    len(content) == 1
                    and content in string.ascii_lowercase
                    and text.get_fontweight() in {"bold", 700, "heavy"}
                )
                if content and size > self.max_fontsize and not is_panel_label:
                    issues.append(
                        f"Axes {ax_idx}: text '{content[:30]}' has size "
                        f"{size:.1f} pt, above ordinary text maximum "
                        f"{self.max_fontsize:.1f} pt."
                    )
                color = text.get_color()
                if color not in {"black", "white", "#000000", "#ffffff", "#FFFFFF"}:
                    issues.append(
                        f"Axes {ax_idx}: text '{content[:30]}' appears to use "
                        f"coloured text ({color}). Nature discourages coloured text."
                    )
                if check_contrast and content:
                    try:
                        ratio = self.contrast_ratio(color, "white")
                        if ratio < 4.5:
                            issues.append(
                                f"Axes {ax_idx}: text '{content[:30]}' may have "
                                f"low contrast against white background "
                                f"(ratio={ratio:.2f})."
                            )
                    except ValueError:
                        pass

            for line in ax.lines:
                lw = line.get_linewidth()
                if lw < 0.25:
                    issues.append(f"Axes {ax_idx}: line width {lw:.2f} pt is very thin.")
                if lw > 1.0:
                    issues.append(
                        f"Axes {ax_idx}: line width {lw:.2f} pt exceeds 1 pt. "
                        "This may be too heavy for compact journal figures."
                    )

        if target_format is not None:
            fmt = target_format.lower()
            if mode == "main":
                preferred = {"pdf", "eps"}
                acceptable = {"svg", "ps"}
                not_accepted = {"png", "tiff", "tif", "jpg", "jpeg"}
                if fmt in not_accepted:
                    issues.append(
                        f"Format '.{fmt}' is not accepted by Nature for main figures. "
                        "Prefer editable vector PDF or EPS."
                    )
                elif fmt not in preferred and fmt not in acceptable:
                    issues.append(
                        f"Format '.{fmt}' is not listed as a preferred/acceptable "
                        "main-figure format."
                    )
            if mode == "extended":
                accepted = {"jpg", "jpeg", "tiff", "tif", "eps"}
                if fmt not in accepted:
                    issues.append(
                        f"Format '.{fmt}' is not listed for Extended Data. "
                        "Nature lists JPEG, TIFF or EPS."
                    )
        return issues

    def export(
        self,
        fig: Figure,
        filename: Union[str, Path],
        mode: FigureMode = "main",
        dpi: Optional[int] = None,
        bbox_inches: Union[str, None] = "tight",
        pad_inches: float = 0.01,
        validate: bool = True,
        fail_on_warning: bool = False,
        **savefig_kwargs,
    ) -> List[str]:
        """Export a figure with Nature-inspired settings."""
        path = Path(filename)
        fmt = path.suffix.lower().replace(".", "")
        if not fmt:
            raise ValueError("Filename must include an extension, e.g. .pdf or .png.")
        if dpi is None:
            dpi = 300 if mode == "extended" else self.dpi

        issues: List[str] = []
        if validate:
            issues = self.validate_figure(fig, mode=mode, target_format=fmt)  # type: ignore[arg-type]
            for issue in issues:
                warnings.warn(issue, UserWarning)
            if fail_on_warning and issues:
                raise RuntimeError("Figure validation failed:\n- " + "\n- ".join(issues))

        savefig_defaults = {
            "dpi": dpi,
            "bbox_inches": bbox_inches,
            "pad_inches": pad_inches,
            "facecolor": "white",
            "edgecolor": "white",
        }
        savefig_defaults.update(savefig_kwargs)
        fig.savefig(path, **savefig_defaults)
        return issues


@dataclass
class PlotConfig:
    """Backward-compatible lightweight plotting configuration."""

    style: str = "default"
    rc_params: Dict[str, Any] = field(default_factory=lambda: {
        "axes.titlesize": 7,
        "axes.titleweight": "normal",
        "axes.titlelocation": "center",
        "axes.facecolor": "white",
        "grid.color": "0.5",
        "grid.linestyle": "--",
        "grid.linewidth": 0.35,
        "lines.linewidth": 0.6,
        "legend.fontsize": 5,
        "savefig.bbox": "tight",
        "savefig.dpi": 450,
    })
    zero_line_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        "y": 0.0,
        "ls": "solid",
        "c": "black",
        "lw": 0.5,
    })
    show_spines: bool = True
    spines_sides: List[str] = field(default_factory=lambda: ["left", "bottom"])
    spine_color: str = "black"
    spine_linewidth: float = 0.5

    def apply_to_axes(self, ax: plt.Axes) -> None:
        """Apply this compatibility configuration to a Matplotlib Axes."""
        facecolor = self.rc_params.get("axes.facecolor")
        if facecolor:
            ax.set_facecolor(facecolor)

        if self.show_spines:
            for side in ["top", "bottom", "left", "right"]:
                visible = side in self.spines_sides
                ax.spines[side].set_visible(visible)
                if visible:
                    ax.spines[side].set_color(self.spine_color)
                    ax.spines[side].set_linewidth(self.spine_linewidth)
        else:
            for spine in ax.spines.values():
                spine.set_visible(False)

        ax.tick_params(
            axis="both",
            which="major",
            labelsize=5,
            width=self.spine_linewidth,
            length=2.5,
            direction="out",
            colors="black",
        )


def use_nature_style() -> NatureFigureStyle:
    """Create a NatureFigureStyle instance and apply global Matplotlib style."""
    style = NatureFigureStyle()
    style.set_global_style()
    return style
