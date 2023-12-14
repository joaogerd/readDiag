# Instalação - Local

Para instalar o pacote readDiag, é recomendado que o usuário prepare um ambiente do Python específico para o seu uso. Isto pode ser feito com o `conda` ou com o módulo `venv` do Python e a instalação do pacote pode ser feita através do `pip`:

```bash linenums="1"
conda create -n readDiag python=3.9.18
conda activate readDiag
pip install readDiag
```

ou,

```bash linenums="1"
python -m venv readDiag
source readDiag/bin/activate
pip install readDiag
```

Alguns dos pacotes do Python que são instalados junto com o readDiag:

* Cartopy (v0.22.0)
* geopandas (v0.14.1)
* jupyterlab (v4.0.9)
* matplotlib (v3.8.2)
* numpy (v1.26.2)
* pandas (v2.1.4)
* xarray (v2023.12.0)

Se você apenas deseja conhecer o readDiag, obtenha uma cópia da última release em [https://github.com/GAD-DIMNT-CPTEC/readDiag/releases](https://github.com/GAD-DIMNT-CPTEC/readDiag/releases) ou em [https://pypi.org/project/readDiag/#files](https://pypi.org/project/readDiag/#files).

!!! note "Nota"

    Quando a criação do ambiente for feita com o `conda`, o usuário deverá indicar uma versão do Python para a instalação. Para a versão atual do readDiag, o usuário deve indicar uma versão >=3.9.18. Isso garantirá que a resolução de dependências de pacotes seja resolvida corretamente durante o processo de instalação. Com o módulo `venv` do Python, é necessário que o usuário tenha instalado em sua máquina também alguma distribuição do Python versão >=3.9.18. Para ambos os casos, recomenda-se a instalação do [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/miniconda-install.html).

O readDiag pode ser modificado e expandido para receber novas funcionalidades e correções de bugs (as quais devem ser submetidas ao projeto por meio de [Pull Requests](https://github.com/GAD-DIMNT-CPTEC/readDiag/pulls)). Para criar um ambiente com todos os pacotes necessários para o seu desenvolvimento, utilize o arquivo [`environment.yml`](https://raw.githubusercontent.com/GAD-DIMNT-CPTEC/readDiag/master/environment.yml) ou [`requirements.txt`](https://raw.githubusercontent.com/GAD-DIMNT-CPTEC/readDiag/master/requirements.txt). Para isso, certifique-se de ter o Python (>=3.9.18) instalado na máquina e, em seguida, obtenha uma cópia do repositório.

Se você possui uma conta no GitHub e deseja participar do desenvolvimento do código, utilize uma das opções a seguir para obter uma cópia do repositório:

1. Utilizando o comando `gh` (mais informações [aqui](https://cli.github.com/)):

    ```bash linenums="1"
    gh repo clone GAD-DIMNT-CPTEC/readDiag
    ```

2. Utilizando o HTTPS (forma mais comum):

    ```bash linenums="1"
    git clone https://github.com/GAD-DIMNT-CPTEC/readDiag.git
    ```

    Com o comando `conda` disponível na máquina e com uma cópia do readDiag em disco, utilize o arquivo `environment.yml` ou `requirements.txt` para criar um ambiente de execução do readDiag. Para isso, siga as instruções a seguir.
    
    !!! warning "Atenção"
    
        Para a instalação do pacote readDiag, é necessário que um compilador Fortran instalado no computador do usuário. Se o ambiente Python do readDiag estiver corretamente configurado, não será necessário instalar pacotes adicionais. Para as distribuições Linux baseadas no Ubuntu, utilize o comando a seguir para instalar o compilador GNU Fortran:
    
        ```bash linenums="1"
        sudo apt install gfortran
        ```
        
        Além do Linux nativo, pode-se também utilizar o WSL do Windows seguindo as mesmas instruções desta página. Para obter mais informações sobre a instalação do WSL, clique [aqui](https://learn.microsoft.com/pt-br/windows/wsl/install).

3. Entre no diretório onde o readDiag se encontra (se o arquivo estiver comprimido, descompacte-o antes). Localize o arquivo `environment.yml` e utilize-o para criar o ambiente:

    ```bash linenums="1"
    conda env create -f environment.yml
    ```

    ou, 

    ```bash linenums="1"
    python -m venv readDiag-dev
    source readDiag-dev/bin/activate
    pip install -r requirements.txt
    ```

    !!! info "Informação"

        Esta etapa irá criar um ambiente virtual do Python onde serão instalados uma série de pacotes necessários para a instalação e execução do readDiag. Com a utilização do arquivo `environment.yml`, será criado o ambiente de nome `readDiag` com todos os pacotes necessários. Com a utilização do arquivo `requirements.txt`, é necessário criar o ambiente manualmente. Neste caso, os comandos `pip install -r requirements.txt` e `pip install readDiag` tem os mesmos efeitos.

Para desinstalar o pacote readDiag (caso necessário), utilize o comando `pip uninstall readDiag`.
