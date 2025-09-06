from dataclasses import dataclass, field
from typing import Dict, Any, List
import matplotlib.pyplot as plt

"""
Module: readDiag.style
======================

Centralizes global plotting style for the ``readDiag`` package.

The main entry point is the :class:`PlotConfig` dataclass, which collects
``rcParams``, spines, grid, and reference-line settings. Users can instantiate
a :class:`PlotConfig` object to override default styling and then call
:meth:`apply_to_axes` on any Matplotlib axes.

Examples
--------
>>> from readDiag.style import PlotConfig
>>> cfg = PlotConfig(style="seaborn-v0_8-darkgrid", show_spines=True)
>>> import matplotlib.pyplot as plt
>>> fig, ax = plt.subplots()
>>> ax.plot([0, 1], [1, 2])
>>> cfg.apply_to_axes(ax)
>>> ax.set_title("Styled")
>>> plt.show()
"""


@dataclass
class PlotConfig:
    """Configuration container for global plot styling.

    This class centralizes Matplotlib styling options, including rcParams,
    grid appearance, background color, and spines visibility.

    Attributes
    ----------
    style : str
        Matplotlib style name, passed to ``plt.style.use`` 
        (e.g., ``'seaborn-v0_8-darkgrid'``).
    rc_params : dict
        Key–value overrides for Matplotlib's rcParams 
        (applied via ``plt.rcParams.update``).
        Typical entries: ``axes.titlesize``, ``axes.facecolor``,
        ``grid.linestyle``.
    zero_line_kwargs : dict
        Parameters for drawing a horizontal reference line at y=0
        (e.g., ``{'y': 0.0, 'ls': 'dashed', 'c': 'gray'}``).
    show_spines : bool
        Whether to display spines (axes borders). If ``False``,
        all spines are hidden.
    spines_sides : list of str
        Which spines to show if ``show_spines=True``.
        Options: ``['top','bottom','left','right']``.
    spine_color : str
        Color applied to visible spines.
    spine_linewidth : float
        Line width applied to visible spines.

    Examples
    --------
    Create and apply a custom configuration:

    >>> import matplotlib.pyplot as plt
    >>> from readDiag.style import PlotConfig
    >>> config = PlotConfig(
    ...     style='seaborn-v0_8-darkgrid',
    ...     rc_params={'axes.titlesize': 14, 'axes.facecolor': '#F0F0F0'},
    ...     spines_sides=['left', 'bottom'],
    ...     spine_color='darkblue',
    ...     spine_linewidth=1.5
    ... )
    >>> plt.style.use(config.style)
    >>> plt.rcParams.update(config.rc_params)
    >>> fig, ax = plt.subplots()
    >>> ax.plot([0, 1], [1, 2], label="Line")
    >>> config.apply_to_axes(ax)
    >>> ax.legend()
    >>> ax.set_title("Custom Styled Plot")
    >>> plt.show()
    """

    style: str = 'seaborn-v0_8-darkgrid'
    rc_params: Dict[str, Any] = field(default_factory=lambda: {
        'axes.titlesize': 10,
        'axes.titleweight': 'bold',
        'axes.titlelocation': 'center',
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
        """Apply this configuration to a Matplotlib Axes.

        This method applies grid, background facecolor, and spines settings
        according to the values stored in the dataclass.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            The axes to which style should be applied.

        Notes
        -----
        - Grid settings are pulled from ``rc_params`` (``grid.linestyle``,
          ``grid.color``, etc.).
        - If ``show_spines`` is False, all spines are hidden regardless of
          other settings.
        - Otherwise, only sides listed in ``spines_sides`` are shown and styled.

        Examples
        --------
        >>> import matplotlib.pyplot as plt
        >>> from readDiag.style import PlotConfig
        >>> cfg = PlotConfig(show_spines=False)
        >>> fig, ax = plt.subplots()
        >>> ax.plot([0, 1], [1, 2])
        >>> cfg.apply_to_axes(ax)
        >>> ax.set_title("No Spines")
        >>> plt.show()
        """
        # Enable grid lines if rc_params specify them
        if 'grid.linestyle' in self.rc_params:
            ax.grid(
                True,
                which='both',
                linestyle=self.rc_params.get('grid.linestyle', '--'),
                color=self.rc_params.get('grid.color', '#d3d3d3'),
                linewidth=self.rc_params.get('grid.linewidth', 1),
                alpha=0.7,
            )

        # Set background facecolor if defined
        facecolor = self.rc_params.get('axes.facecolor')
        if facecolor:
            ax.set_facecolor(facecolor)

        # Configure spines visibility and styling
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


# Example usage when run standalone (manual visual test)
if __name__ == "__main__":
    config = PlotConfig(
        style='seaborn-v0_8-darkgrid',
        rc_params={
            'axes.titlesize': 13,
            'axes.titleweight': 'bold',
            'axes.facecolor': '#F0F0F0',
            'grid.color': '#CCCCCC',
            'grid.linestyle': ':',
            'grid.linewidth': 0.8,
        },
        show_spines=True,
        spines_sides=['left', 'bottom'],
        spine_color='darkblue',
        spine_linewidth=1.5,
        zero_line_kwargs={'y': 0.0, 'ls': 'dotted', 'c': 'gray'},
    )

    # Apply global style
    plt.style.use(config.style)
    plt.rcParams.update(config.rc_params)

    # Create test plot
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [2, 1, 3], label='Demo Line')
    config.apply_to_axes(ax)
    ax.set_title("Styled Plot Example")
    ax.legend()
    plt.show()

