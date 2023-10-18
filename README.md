# readDiag

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/GAD-DIMNT-CPTEC/readDiag/HEAD)

**English:** the readDiag documentation is available [here](https://gad-dimnt-cptec.github.io/readDiag/).

Para facilitar o acesso ao conteúdo dos arquivos de diagnóstico do [Gridpoint Statistical Interpolation (GSI)](https://dtcenter.org/community-code/gridpoint-statistical-interpolation-gsi), foi escrito o pacote [readDiag](https://github.com/GAD-DIMNT-CPTEC/readDiag) que é uma interface Fortran/Python cujo objetivo é ler os arquivos binários de diagnóstico do GSI e criar estruturas de dados adequadas para a sua manipulação.

## Requerimentos

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

Para mais detalhes e possibilidades de instalação do readDiag, veja a página [https://gad-dimnt-cptec.github.io/readDiag/pt/instala_local](https://gad-dimnt-cptec.github.io/readDiag/pt/instala_local) do manual de utilização.

No repositório verifique o diretório `notebooks/` com alguns exemplos de utilização do readDiag. Utilize o Binder para abrir uma [seção iterativa de demonstração do readDiag](https://mybinder.org/v2/gh/GAD-DIMNT-CPTEC/readDiag/HEAD). Nesta seção, escolha o notebook `readDiag_tutorial_simples-pt_br.ipynb`.

<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode" target="_blank"><img src="https://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nc-sa.png" alt="CC-BY-NC-SA" width="100"/></a>
