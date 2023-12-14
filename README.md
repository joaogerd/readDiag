# readDiag

readDiag is a Python package that provides a class to read and plot the [Gridpoint Statistical Interpolation](https://dtcenter.org/community-code/gridpoint-statistical-interpolation-gsi) diagnostics files. It can be used to retrieve and investigate important information from the data assimilation process:

![image](https://user-images.githubusercontent.com/6088258/183511751-21032794-b38c-44c0-8719-103ed1b98547.png)

## Installation

Use either `conda` or `python -m venv` to setup a virtual environment to install readDiag:

```
conda create -n readDiag python=3.9.18
conda activate readDiag
pip install readDiag
```

or

```
python -m venv readDiag
source readDiag/bin/activate
pip install readDiag
```

**Note:** When using `python -m venv` make sure to have Python >=3.9.18 installed on your system. For more information on how to use readDiag, take a look at the project's [documentation](https://gad-dimnt-cptec.github.io/readDiag/).

<a href="https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode" target="_blank"><img src="https://mirrors.creativecommons.org/presskit/buttons/88x31/png/by-nc-sa.png" alt="CC-BY-NC-SA" width="100"/></a>
