# Installation - Remote

On this page, specific information is presented for using readDiag on virtual machines (e.g., Itapemirim and Ilópolis) and Egeon at CPTEC. If you want to install readDiag on a local machine, use the instructions on the [Local Installation](install_local.md) page.

## Itapemirim/Ilopolis

The Ilopolis machine has a Jupyter server that can be used to run readDiag. This server is accessible at [http://ilopolis.cptec.inpe.br/](http://ilopolis.cptec.inpe.br/). Follow the instructions below to create a readDiag kernel for use within this Jupyter server.

### Installing the readDiag Environment

!!! warning "Warning"

    In this section, it is assumed that the user will create the readDiag environment and install the package within the environment so the user can make modifications to the code.

1. Download the readDiag code (in your `$HOME`):

    ```bash linenums="1"
    gh repo clone GAD-DIMNT-CPTEC/readDiag
    ```
    or

    ```bash linenums="1"
    git clone https://github.com/GAD-DIMNT-CPTEC/readDiag.git
    ```

2. Inside the readDiag directory, create the environment, activate it, and install readDiag:

    ```bash linenums="1"
    cd readDiag
    conda env create -f environment.yml
    conda activate readDiag
    pip install -e .
    ```

    or,

    ```bash linenums="1"
    cd readDiag
    python -m venv readDiag-env
    source readDiag-env/bin/activate
    pip install -r requirements.txt
    pip install -e .
    ```

    !!! note "Note"

        By creating the environment, the `readDiag` will be installed automatically. It is important to note that by running `pip install -e .`, the readDiag released version of readDiag from PyPi will be uninstalled, and the repository version will be installed in edit (or development) mode. This way, modifications made to the code will be readly available without the need to reinstall the package.

3. Install the readDiag environment kernel within Jupyter:

    ```bash linenums="1"
    python -m ipykernel install --user --name readDiag --display-name "readDiag"
    ```

4. Access the host [http://ilopolis.cptec.inpe.br/](http://ilopolis.cptec.inpe.br/) and navigate to the `$HOME/readDiag/notebooks` directory and click on the `readDiag_tutorial_complete-en_us.ipynb` file;

5. In the Jupyter interface, change the kernel to `readDiag`. This step is necessary to execute the code.

### Reusing the readDiag Environment

!!! warning "Warning"

    In this section, it is assumed that the user will reuse the readDiag environment with the package already installed previously. In this case, it is not necessary to create an environment or install readDiag.

1. Download the readDiag code (in your `$HOME`) - **to access the readDiag usage example notebooks**:

    ```bash linenums="1"
    gh repo clone GAD-DIMNT-CPTEC/readDiag
    ```
    or

    ```bash linenums="1"
    git clone https://github.com/GAD-DIMNT-CPTEC/readDiag.git
    ```

2. Activate the `readDiag` environment:

    ```bash linenums="1"
    source /share/das/miniconda3/envs/readDiag/bin/activate
    ```

3. Install the `readDiag` environment kernel within Jupyter:

    ```bash linenums="1"
    python -m ipykernel install --user --name readDiag --display-name "readDiag"
    ```

4. Access the host [http://ilopolis.cptec.inpe.br/](http://ilopolis.cptec.inpe.br/) and navigate to the `$HOME/readDiag/notebooks` directory and click on the `readDiag_tutorial_complete-en_us.ipynb` file;

5. In the Jupyter interface, change the kernel to `readDiag`. This step is necessary to execute the code.

## Egeon

To use readDiag on Egeon, follow the instructions below:

1. Perform steps 1 and 2 described in the [Installing the readDiag Environment](#installing-the-readdiag-environment) section;

2. Activate the `readDiag` environment:

    ```bash linenums="1"
    source /home/carlos.bastarz/.conda/envs/readDiag/bin/activate
    ```

3. Execute the following command - **note the port on which Jupyter is being run, e.g., `jupyter:8889`**:

    ```bash linenums="1"
    jupyter-notebook --ip='*' --NotebookApp.token='' --NotebookApp.password='' --no-browser
    ```

4. On your computer, run the following command to open Jupyter locally - where `localhost:XXXX` should be a port on your computer, e.g., `localhost:8820`:

    ```bash linenums="1"
    ssh -N -f -L  localhost:XXXX:localhost:8889 <username>@egeon.cptec.inpe.br
    ```

5. On your computer, open the browser and access the address `localhost:8820`.

!!! warning "Warning"

    If it is necessary to terminate Jupyter or restart the process, run the following commands - identify the process corresponding to the executed `ssh` command and terminate it:

    ```bash linenums="1"
    ps -ef | grep ssh
    kill -9 PID
    ```
