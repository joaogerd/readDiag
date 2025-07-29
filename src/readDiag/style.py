from dataclasses import dataclass, field
from typing import Dict, Any, List
import matplotlib.pyplot as plt

"""
Module: readDiag.style

This module provides the PlotConfig dataclass, which centralizes all default plotting
styles and parameters for the readDiag package. By adjusting attributes of PlotConfig,
users can customize global plot aesthetics (e.g., color schemes, fonts, grid styles,
and reference lines) in a single location.

Example:
    >>> from readDiag.style import PlotConfig
    >>> from readDiag.reader import diagAccess
    >>> from readDiag.plotting import diagPlotter
    >>> # Create a custom configuration
    >>> custom_cfg = PlotConfig(
    ...     style='seaborn-v0_8-darkgrid',
    ...     rc_params={
    ...         'axes.titlesize': 14,
    ...         'axes.titleweight': 'bold',
    ...         'axes.facecolor': '#F9F9F9',
    ...         'grid.color': 'lightgray',
    ...         'grid.linestyle': '--',
    ...         'grid.linewidth': 1.0
    ...     },
    ...     show_spines=True,
    ...     spines_sides=['left', 'bottom'],
    ...     spine_color='black',
    ...     spine_linewidth=1.0,
    ...     zero_line_kwargs={
    ...         'y': 0.0,
    ...         'ls': 'dashed',
    ...         'c': 'gray'
    ...     }
    ... )
"""

@dataclass
class PlotConfig:
    """
    Configuration container for global plot styling in the readDiag package.

    Attributes:
        style (str): Matplotlib style name (e.g., 'seaborn-v0_8-darkgrid').
        rc_params (Dict[str, Any]): Dictionary of rcParams applied globally via plt.rcParams.update().
        zero_line_kwargs (Dict[str, Any]): Parameters to draw a reference line at y=0 (optional).
        show_spines (bool): Whether to show plot spines (borders around plot). Default is True.
        spines_sides (List[str]): List of sides to show ('top', 'bottom', 'left', 'right').
                                  Ignored if show_spines is False.
        spine_color (str): Color applied to visible spines. Default is 'black'.
        spine_linewidth (float): Width of visible spines. Default is 1.0.
    """
    style: str = 'seaborn-v0_8-darkgrid'
    rc_params: Dict[str, Any] = field(default_factory=lambda: {
        'axes.titlesize': 10,
        'axes.titleweight': 'bold',
        'axes.titlelocation': 'left',
        'axes.facecolor': '#EAEAF2',
        'grid.color': 'white',
        'grid.linestyle': '-',
        'grid.linewidth': 1,
        'lines.linewidth': 1.5,
        'legend.fontsize': 10,
        'savefig.bbox': 'tight',
        'savefig.dpi': 100,
    })
    zero_line_kwargs: Dict[str, Any] = field(default_factory=lambda: {
        'y': 0.0,
        'ls': 'solid',
        'c': '#d3d3d3',
    })
    show_spines: bool = True
    spines_sides: List[str] = field(default_factory=lambda: ['left', 'bottom'])
    spine_color: str = 'black'
    spine_linewidth: float = 1.0

    def apply_to_axes(self, ax: plt.Axes) -> None:
        """
        Apply the style settings to a given matplotlib Axes object.

        This includes:
        - Enabling grid lines if defined in rc_params.
        - Setting the axes facecolor if defined.
        - Customizing which spines (borders) are visible, and how they look.

        Args:
            ax (matplotlib.axes.Axes): The target axes object.
        """
        # Enable grid
        if 'grid.linestyle' in self.rc_params:
            ax.grid(True,
                    which='both',
                    linestyle=self.rc_params.get('grid.linestyle', '--'),
                    color=self.rc_params.get('grid.color', '#d3d3d3'),
                    linewidth=self.rc_params.get('grid.linewidth', 1),
                    alpha=0.7)

        # Set facecolor
        facecolor = self.rc_params.get('axes.facecolor')
        if facecolor:
            ax.set_facecolor(facecolor)

        # Customize spines
        if self.show_spines:
            for side in ['top', 'bottom', 'left', 'right']:
                visible = side in self.spines_sides
                ax.spines[side].set_visible(visible)
                if visible:
                    ax.spines[side].set_color(self.spine_color)
                    ax.spines[side].set_linewidth(self.spine_linewidth)
        else:
            for spine in ax.spines.values():
                spine.set_visible(False)


# Example usage
if __name__ == "__main__":
    import matplotlib.pyplot as plt

    config = PlotConfig(
        style='seaborn-v0_8-darkgrid',
        rc_params={
            'axes.titlesize': 13,
            'axes.titleweight': 'bold',
            'axes.facecolor': '#F0F0F0',
            'grid.color': '#CCCCCC',
            'grid.linestyle': ':',
            'grid.linewidth': 0.8
        },
        show_spines=True,
        spines_sides=['left', 'bottom'],
        spine_color='darkblue',
        spine_linewidth=1.5,
        zero_line_kwargs={
            'y': 0.0,
            'ls': 'dotted',
            'c': 'gray'
        }
    )

    plt.style.use(config.style)
    plt.rcParams.update(config.rc_params)

    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [2, 1, 3], label='Demo Line')
    config.apply_to_axes(ax)
    ax.set_title("Styled Plot Example")
    ax.legend()
    plt.show()

