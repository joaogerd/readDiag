def test_dunder_version():
    """Test that the package defines a non-empty version string.

    This test ensures that the package exposes a ``__version__`` attribute,
    which is a common convention in Python projects to track the library's
    version.

    The test verifies:
    - The attribute ``__version__`` exists in the package.
    - It is a non-empty string.

    Notes
    -----
    Having a ``__version__`` attribute is useful for:
    - Debugging compatibility issues.
    - Ensuring reproducibility in experiments.
    - Automatically tracking versions in documentation.

    Examples
    --------
    >>> import readDiag
    >>> hasattr(readDiag, "__version__")
    True
    >>> isinstance(readDiag.__version__, str)
    True
    """
    import readDiag
    # Ensure the package exposes __version__
    assert hasattr(readDiag, "__version__")

    # Retrieve and check the value
    v = readDiag.__version__
    assert isinstance(v, str) and len(v) > 0


def test_show_versions_runs(capsys):
    """Test that ``show_versions`` runs and prints expected output.

    This test captures the standard output of the ``show_versions`` function
    and verifies that it includes essential information such as the library
    name and the Python runtime.

    Parameters
    ----------
    capsys : pytest fixture
        Built-in pytest fixture that captures writes to stdout and stderr.

    Notes
    -----
    The ``show_versions`` function typically prints:
    - Package name and version
    - Python version
    - Dependency versions

    This is helpful for debugging and reproducibility in scientific workflows.

    Examples
    --------
    >>> import readDiag
    >>> readDiag.show_versions()  # doctest: +ELLIPSIS
    readDiag : 2.0.0
    Python   : 3.12...
    """
    import readDiag

    # Run the function that prints diagnostic info
    readDiag.show_versions()

    # Capture printed output
    out = capsys.readouterr().out

    # Ensure critical strings are present in the output
    assert "readDiag" in out and "Python" in out


