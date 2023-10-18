# Instalação - Remoto

Nesta página, são apresentadas informações específicas para o uso do readDiag nas máquina virtuais (e.g., Itapemirim e Ilópolis) e Egeon do CPTEC. Caso você deseja instalar o readDiag em uma máquina local, utilize as instruções da página [Instalação Local](instala_local.md).

## Itapemirim/Ilopolis

A máquina Ilopolis possui um servidor do Jupyter que pode ser utilizado para a execução do readDiag. Este servidor está acessível pelo endereço [http://ilopolis.cptec.inpe.br/](http://ilopolis.cptec.inpe.br/). Siga as instruções a seguir para criar um kernel do readDiag para ser utilizado dentro deste servidor do Jupyter.

### Instalação do Ambiente readDiag

!!! warning "Atenção"

    Nesta seção, considera-se que o usuário irá criar o ambiente readDiag e irá instalar o pacote dentro do ambiente.

1. Baixe o código do readDiag (no seu `$HOME`):

    ```bash linenums="1"
    gh repo clone GAD-DIMNT-CPTEC/readDiag
    ```
    ou

    ```bash linenums="1"
    git clone https://github.com/GAD-DIMNT-CPTEC/readDiag.git
    ```

2. Dentro do diretório do readDiag, crie o ambiente, ative-o e instale o readDiag:

    ```bash linenums="1"
    cd readDiag
    conda env create -f environment.yml
    conda activate readDiag
    python setup.py install
    ```

3. Instale o kernel do ambiente readDiag dentro do Jupyter:

    ```bash linenums="1"
    python -m ipykernel install --user --name readDiag --display-name "readDiag"
    ```

4. Acesse o host [http://ilopolis.cptec.inpe.br/](http://ilopolis.cptec.inpe.br/) e navegue até o diretório `$HOME/readDiag/notebooks` e clique no arquivo `readDiag_tutorial_completo-pt_br.ipynb`;

5. Na interface do Jupyter, altere o kernel para `readDiag`. Essa etapa é necessária para que seja possível executar o código.

### Reutilização do Ambiente readDiag

!!! warning "Atenção"

    Nesta seção, considera-se que o usuário irá reutilizar o ambiente readDiag com o pacote já instalado previamente. Neste caso, não é necessário criar um ambiente e nem instalar o readDiag.

1. Baixe o código do readDiag (no seu `$HOME`) - **para ter acesso aos notebooks de exemplos de uso do readDiag**:

    ```bash linenums="1"
    gh repo clone GAD-DIMNT-CPTEC/readDiag
    ```
    ou

    ```bash linenums="1"
    git clone https://github.com/GAD-DIMNT-CPTEC/readDiag.git 
    ```

2. Ative o ambiente `readDiag`:

    ```bash linenums="1"
    source /share/das/miniconda3/envs/readDiag/bin/activate
    ```

3. Instale o kernel do ambiente `readDiag` dentro do Jupyter:

    ```bash linenums="1"
    python -m ipykernel install --user --name readDiag --display-name "readDiag"
    ```

4. Acesse o host [http://ilopolis.cptec.inpe.br/](http://ilopolis.cptec.inpe.br/) e navegue até o diretório `$HOME/readDiag/notebooks` e clique no arquivo `readDiag_tutorial_completo-pt_br.ipynb`;

5. Na interface do Jupyter, altere o kernel para `readDiag`. Essa etapa é necessária para que seja possível executar o código.

## Egeon

Para utilizar o readDiag na Egeon, siga as instruções a seguir:

1. Realize as etapas 1 e 2 descritas na seção [Instalação do Ambiente readDiag](#instalacao-do-ambiente-readdiag);

2. Ative o ambiente `readDiag`:

    ```bash linenums="1"
    source /home/carlos.bastarz/.conda/envs/readDiag/bin/activate
    ```

3. Execute o comando a seguir - **anote a porta em que o jupyter está sendo executado, e.g., `jupyter:8889`**:

    ```bash linenums="1"
    jupyter-notebook --ip='*' --NotebookApp.token='' --NotebookApp.password='' --no-browser
    ```
4. No seu computador, execute o comando a seguir para abrir o Jupyter localmente - onde `localhost:XXXX` deve ser uma porta no seu computador, e.g., `localhost:8820`:

    ```bash linenums="1"
    ssh -N -f -L  localhost:XXXX:localhost:8889 <username>@egeon.cptec.inpe.br
    ```

5. No seu computador, abra o navegador e acesse o endereço `localhost:8820`.

!!! warning "Atenção"

    Caso seja necessário encerrar o Jupyter ou reiniciar o processo, execute os seguintes comandos - identifique o processo correspondente ao comando `ssh` executado e encerre-o:

    ```bash linenums="1"
    ps -ef | grep ssh
    kill -9 PID
    ```
