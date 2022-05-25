# ReadDiag - Uma interface Python para a leitura dos arquivos de diagnósticos do GSI

## Instruções para Compilação na Tupã

### Obtenção do pacote

* Logar na Tupã, host eslogin01:

```
$ ssh usuario@tupa.cptec.inpe.br -XC
$ ssh eslogin01
```

* Alteração do compilador padrão:

```
$ module swap PrgEnv-pgi PrgEnv-gnu
```

* Obter uma cópia do ReadDiag do repositório:

```
$ svn co https://svn.cptec.inpe.br/ad/trunk/ReadDiag
```

* Compilação do pacote:

```
$ cd ReadDiag
```

### Verificação do Python3 (distribuição do ActivePython)

* O resultado do seguinte comando deverá ser:

```
$ which python3
$ /scratchin/grupos/das/projetos/gdad/python/ActivePython-3.6/bin/python3
```

* Se o python3 na Tupã não estiver no caminho indicado acima, adicione o diretório `bin` do ActivePython no seu `$USER/.bashrc` (ou `$USER/.profile`):

```
$ echo "export PATH="/scratchin/grupos/das/projetos/gdad/python/ActivePython-3.6/bin":${PATH}" >> $USER/.profile
```

* Execute o comando `source $USER/.profile` (ou `source $USER/.bashrc`) ou abra um novo terminal e logue novamente na Tupã.

* Instalação do pacote:

``
$ python3 setup.py install
``

### Verificação da compilação

* Verifique se o seguinte arquivo foi criado:
  * `build/lib.*/diag2python.cpython-*.so`

## Instruções para Compilação na Itepemirim (RECOMENDADO)

### Obtenção do pacote

* Logar na Itepemirim:

```
$ ssh usuario@itepemirim.cptec.inpe.br -XC
```

* Criação do ambiente de desenvolvimento utilizando o Anaconda:

```
$ conda create -n ReadDiag
```

* Ativação do ambiente criado:

```
$ conda info --envs
$ conda activate ReadDiag
```

* Instalação dos pacotes necessários:

```
$ conda install -c conda-forge matplotlib basemap proj4 pyproj
$ conda install -c anaconda geos pandas
```

* Obter uma cópia do ReadDiag do repositório:

```
$ svn co https://svn.cptec.inpe.br/ad/trunk/ReadDiag
```

* Instalação do pacote:

```
$ python3 setup.py install
```

### Verificação da compilação

* Verifique se o seguinte arquivo foi criado:
  * `build/lib.*/diag2python.cpython-*.so`

### Uso

* Export da variável `PYTHONPATH` (desta forma, pode-se utilizar o readdiag a partir de qualquer diretório):

```
$ export PYTHONPATH=$(pwd)/gsidiag
```

* Abrir o prompt do Python3:

```
$ python3
```

* Importar a classe readDiag:

```
>>> import readdiag as rd
```

**Obs.:** No sistema operacional Mac OS X, se o volume (partição) onde o pacote está sendo compilado estiver formatado sem a opção "Case Sensitive", não será possível fazer o pacote funcionar.

* Acessando as funções e métodos da classe (tecla TAB):

```
>>> rd.<<TAB>>
```

Outras informações podem ser obtidas na página [Wiki readDiag](https://github.com/GAD-DIMNT-CPTEC/readDiag/wiki).

Grupo de Assimilação de Dados - CPTEC/INPE 
