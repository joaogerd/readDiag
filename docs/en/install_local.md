# Installation - Local

To install the readDiag package, it is recommended that the user sets up a Python environment specifically for its use. This can be done using either `conda` or the `venv` Python module and the package installation can be completed via `pip`:

```bash linenums="1"
conda create -n readDiag python=3.9.18
conda activate readDiag
pip install readDiag
```

or,

```bash linenums="1"
python -m venv readDiag
source readDiag/bin/activate
pip install readDiag
```

Some of the Python packages installed along with readDiag include:

* Cartopy (v0.22.0)
* geopandas (v0.14.1)
* jupyterlab (v4.0.9)
* matplotlib (v3.8.2)
* numpy (v1.26.2)
* pandas (v2.1.4)
* xarray (v2023.12.0)

If you just want to check readDiag, grab a copy from the lasted release at [https://github.com/GAD-DIMNT-CPTEC/readDiag/releases](https://github.com/GAD-DIMNT-CPTEC/readDiag/releases) or [https://pypi.org/project/readDiag/#files](https://pypi.org/project/readDiag/#files).

To create the Python environment for using the readDiag package, first install Anaconda (or Miniconda), and then obtain a copy of the repository.

!!! note "Note"

    When creating the environment with `conda`, the user should indicate a Python version for the initial installation. For the current readDiag version, the user must use Python >=3.9.18. This ensures that dependency resolution works correctly during the installation process. With the `venv` module, it is necessary for the user to have a Python distribution installed with a version >=3.9.18. In both cases, it is recommended to use the [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html) Python distribution.

The readDiag package can be expanded and improved with new functionalities and bug corrections (which must be registered by [Pull Requests](https://github.com/GAD-DIMNT-CPTEC/readDiag/pulls)). To create a virtual  environment with all the necessary packages, use the file [`environment.yml`](https://raw.githubusercontent.com/GAD-DIMNT-CPTEC/readDiag/master/environment.yml) or [`requirements.txt`](https://raw.githubusercontent.com/GAD-DIMNT-CPTEC/readDiag/master/requirements.txt). For this, make sure to have Python >=3.9.18 installed and then clone the repository.

If you have a GitHub account and want to contribute to code development, use one of the following options to get a copy of the repository:

1. Using the `gh` command (more information [here](https://cli.github.com/)):

    ```bash linenums="1"
    gh repo clone GAD-DIMNT-CPTEC/readDiag
    ```

2. Using HTTPS (more common):

    ```bash linenums="1"
    git clone https://github.com/GAD-DIMNT-CPTEC/readDiag.git
    ```

    With the `conda` command available on the machine and a copy of readDiag on disk, use the `environment.yml` file to create a readDiag execution environment. To do this, follow the instructions below.
    
    !!! warning "Warning"
    
        F For the installation of the readDiag package, it is necessary to have a Fortran compiler installed on the user's computer. If the readDiag Python environment is correctly configured, additional package installation should not be necessary. For Ubuntu-based Linux distributions, use the following command to install the GNU Fortran compiler:
    
        ```bash linenums="1"
        sudo apt install gfortran
        ```
    
        In addition to native Linux, you can also use Windows WSL following the same instructions on this page. For more information on WSL installation, click [here](https://learn.microsoft.com/en-us/windows/wsl/install).

3. Navigate to the directory where readDiag is located (if the file is compressed, unzip it first). Locate the `environment.yml` file and use it to create the environment:

    ```bash linenums="1"
    conda env create -f environment.yml
    ```

    or, 

    ```bash linenums="1"
    python -m venv readDiag-dev
    source readDiag-dev/bin/activate
    pip install -r requirements.txt
    ```

    !!! info "Information"

        This step will create a virtual Python environment where a series of packages necessary for the installation and execution of readDiag will be installed. By using the `environment.yml`, it will be create an enviornment named `readDiag` with all the necessary packages. By using the `requirements.txt` file, it will be necessary to create the environment manually. In this case, both commands `pip install -r requirements.txt` and `pip install readDiag` have the same effects.

To uninstall the readDiag package (if necessary), use the command `pip uninstall readDiag`.
