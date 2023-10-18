# Instalação - Local

Para instalar o pacote readDiag, é recomendado que o usuário prepare um ambiente do Python específico para o seu uso. Para isto, no repositório encontra-se o arquivo [`environment.yml`](https://raw.githubusercontent.com/GAD-DIMNT-CPTEC/readDiag/master/environment.yml) para a construção desse ambiente utilizando a [Distribuição Python do Anaconda](https://www.anaconda.com/products/distribution) ou [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html).

Alguns dos pacotes do Python necessários para a utilização do readDiag:

* basemap (v1.2.1);
* cartopy (v0.17.0);
* geopandas (v0.10.2);
* matplotlib (v3.5.1);
* numpy (v1.21.6);
* pandas (v1.3.4);
* python (3.7.6);
* xarray (v0.20.2).

Para criar o ambiente Python para o uso do pacote readDiag, primeiro, instale o Anaconda (ou Miniconda) e, em seguida, obtenha uma cópia do repositório.

!!! note "Nota"

    Se você possui uma conta no GitHub e deseja participar do desenvolvimento do código, utilize uma das opções a seguir para obter uma cópia do repositório:

    1. Utilizando o comando `gh` (mais informações [aqui](https://cli.github.com/)):
        ```bash linenums="1"
        gh repo clone GAD-DIMNT-CPTEC/readDiag
        ```
    2. Utilizando o HTTPS (forma mais comum):
        ```bash linenums="1"
        git clone https://github.com/GAD-DIMNT-CPTEC/readDiag.git
        ```

    Se você apenas deseja conhecer o readDiag, obtenha uma cópia da última release em [https://github.com/GAD-DIMNT-CPTEC/readDiag/releases](https://github.com/GAD-DIMNT-CPTEC/readDiag/releases).

Com o comando `conda` disponível na máquina e com uma cópia do readDiag em disco, utilize o arquivo `environment.yml` para criar um ambiente de execução do readDiag. Para isso, siga as instruções a seguir.

!!! warning "Atenção"

    Para a instalação do pacote readDiag, é necessário que um compilador Fortran instalado no computador do usuário. Se o ambiente Python do readDiag estiver corretamente configurado, não será necessário instalar pacotes adicionais. Para as distribuições Linux baseadas no Ubuntu, utilize o comando a seguir para instalar o compilador GNU Fortran:

    ```bash linenums="1"
    sudo apt install gfortran
    ```
    
    Além do Linux nativo, pode-se também utilizar o WSL do Windows seguindo as mesmas instruções desta página. Para obter mais informações sobre a instalação do WSL, clique [aqui](https://learn.microsoft.com/pt-br/windows/wsl/install).

1. Entre no diretório onde o readDiag se encontra (se o arquivo estiver comprimido, descompacte-o antes). Localize o arquivo `environment.yml` e utilize-o para criar o ambiente:

    ```bash linenums="1"
    conda env create -f environment.yml
    ```

    !!! info "Informação"

        Esta etapa irá criar um ambiente virtual do Python onde serão instalados uma série de pacotes necessários para a instalação e execução do readDiag.

2. Após a criação do ambiente com o `conda`, instale o pacote readDiag. Para instalar o pacote do readDiag, primeiro ative o ambiente criado com o comando:

    ```bash linenums="1"
    conda activate readDiag
    ```

3. Instale o pacote readDiag com o comando:

    ```bash linenums="1"
    python setup.py install
    ```

!!! note "Nota"

    Para desinstalar o pacote readDiag (caso necessário), utilize o comando `pip uninstall gsidiag`.
