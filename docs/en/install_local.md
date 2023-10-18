# Installation - Local

To install the readDiag package, it is recommended that the user set up a Python environment specifically for its use. To do this, the repository contains the [`environment.yml`](https://raw.githubusercontent.com/GAD-DIMNT-CPTEC/readDiag/master/environment.yml) file for building this environment using either the [Anaconda Python Distribution](https://www.anaconda.com/products/distribution) or [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html).

Some of the required Python packages for using readDiag:

* basemap (v1.2.1);
* cartopy (v0.17.0);
* geopandas (v0.10.2);
* matplotlib (v3.5.1);
* numpy (v1.21.6);
* pandas (v1.3.4);
* python (3.7.6);
* xarray (v0.20.2).

To create the Python environment for using the readDiag package, first install Anaconda (or Miniconda), and then obtain a copy of the repository.

!!! note "Note"

    If you have a GitHub account and want to contribute to code development, use one of the following options to get a copy of the repository:

    1. Using the `gh` command (more information [here](https://cli.github.com/)):
        ```bash linenums="1"
        gh repo clone GAD-DIMNT-CPTEC/readDiag
        ```
    2. Using HTTPS (more common):
        ```bash linenums="1"
        git clone https://github.com/GAD-DIMNT-CPTEC/readDiag.git
        ```

    If you just want to learn about readDiag, get a copy of the latest release at [https://github.com/GAD-DIMNT-CPTEC/readDiag/releases](https://github.com/GAD-DIMNT-CPTEC/readDiag/releases).

With the `conda` command available on the machine and a copy of readDiag on disk, use the `environment.yml` file to create a readDiag execution environment. To do this, follow the instructions below.

!!! warning "Warning"

    For the installation of the readDiag package, it is necessary to have a Fortran compiler installed on the user's computer. If the readDiag Python environment is correctly configured, additional package installation should not be necessary. For Ubuntu-based Linux distributions, use the following command to install the GNU Fortran compiler:

    ```bash linenums="1"
    sudo apt install gfortran
    ```

    In addition to native Linux, you can also use Windows WSL following the same instructions on this page. For more information on WSL installation, click [here](https://learn.microsoft.com/en-us/windows/wsl/install).

1. Navigate to the directory where readDiag is located (if the file is compressed, unzip it first). Locate the `environment.yml` file and use it to create the environment:

    ```bash linenums="1"
    conda env create -f environment.yml
    ```

    !!! info "Information"

        This step will create a virtual Python environment where a series of packages necessary for the installation and execution of readDiag will be installed.

2. After creating the environment with `conda`, install the readDiag package. To install the readDiag package, first activate the created environment with the command:

    ```bash linenums="1"
    conda activate readDiag
    ```

3. Install the readDiag package with the command:

    ```bash linenums="1"
    python setup.py install
    ```

!!! note "Note"

    To uninstall the readDiag package (if necessary), use the command `pip uninstall gsidiag`.
