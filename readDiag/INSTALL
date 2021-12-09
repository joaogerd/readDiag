ReadDiag - Uma interface Python para a leitura dos arquivos de diagnósticos do GSI

- Instruções para Compilação na Tupã

1) Obtenção do pacote
- Logar na Tupã, host eslogin01
$ ssh usuario@tupa.cptec.inpe.br -XC
$ ssh eslogin01

2) Alteração do compilador padrão
$ module swap PrgEnv-pgi PrgEnv-gnu

3) Obter uma cópia do ReadDiag do repositório
$ svn co https://svn.cptec.inpe.br/ad/trunk/ReadDiag

4) Compilação do pacote
$ cd ReadDiag
* Verificação do Python3 (distribuição do ActivePython):
- O resultado do seguinte comando deverá ser:
$ which python3
$ /scratchin/grupos/das/projetos/gdad/python/ActivePython-3.6/bin/python3

- Se o python3 na Tupã não estiver no caminho indicado acima, adicione o diretório "bin" do ActivePython no seu $USER/.bashr (ou $USER/.profile):
$ echo "export PATH="/scratchin/grupos/das/projetos/gdad/python/ActivePython-3.6/bin":${PATH}" >> $USER/.profile

- Execute o comando "source $USER/.profile" (ou "source $USER/.bashrc") ou abra um novo terminal e logue novamente na Tupã.

$ python3 setup.py install

5) Verificação da compilação
- Verifique se o seguinte arquivo foi criado:
* build/lib.*/diag2python.cpython-*.so

- Instruções para Compilação na Itepemirim (RECOMENDADO)

1) Obtenção do pacote
- Logar na Itepemirim
$ ssh usuario@itepemirim.cptec.inpe.br -XC

2) Criaçãdo ambiente de desenvolvimento utilizando o Anaconda
$ conda create -n ReadDiag

3) Ativação do ambiente criado
$ conda info --envs
$ conda activate ReadDiag

4) Instalação dos pacotes necessários
$ conda install -c conda-forge matplotlib basemap proj4 pyproj
$ conda install -c anaconda geos pandas

5) Obter uma cópia do ReadDiag do repositório
$ svn co https://svn.cptec.inpe.br/ad/trunk/ReadDiag

6) Compilação do pacote
$ python3 setup.py install

7) Verificação da compilação
- Verifique se o seguinte arquivo foi criado:
* build/lib.*/diag2python.cpython-*.so

- Uso

1) Export da variável PYTHONPATH (desta forma, pode-se utilizar o readdiag a partir de qualquer diretório)
$ export PYTHONPATH=$(pwd)/gsidiag

2) Abrir o prompt do Python3
$ python3

3) Importar a classe readDiag
>>> import readdiag as rd

Obs.: No sistema operacional Mac OS X, se o volume (partição) onde o pacote está sendo compilado estiver formatado sem a opção "Case Sensitive", não será possível fazer o pacote funcionar.

4) Acessando as funções e métodos da classe (tecla TAB)
>>> rd.<<TAB>>

Outras informações podem ser obtidas na página https://projetos.cptec.inpe.br/projects/ad/wiki/Readdiag

Grupo de Assimilação de Dados - CPTEC/INPE 
