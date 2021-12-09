#!/usr/bin/env python
#-----------------------------------------------------------------------------#
#           Group on Data Assimilation Development - GDAD/CPTEC/INPE          #
#-----------------------------------------------------------------------------#
#BOP
#
# !SCRIPT:
#
# !DESCRIPTION:
#
# !CALLING SEQUENCE:
#
# !REVISION HISTORY: 
# 13 Apr 2018 - J. G. de Mattos - Initial Version
#
# !REMARKS:
#
#EOP
#-----------------------------------------------------------------------------#
#BOC
import setuptools
from numpy.distutils.core import Extension

ext  = Extension(name = 'diag2python',
                 extra_f77_compile_args=["-fconvert=big-endian"],
                 extra_f90_compile_args=["-fconvert=big-endian"],
                 sources=[
                          'gsidiag/fortran/m_string.f90',
                          'gsidiag/fortran/ReadDiagMod.f90',
                          'gsidiag/fortran/diag2python.f90',
			  'gsidiag/fortran/diag2python.pyf'])

if __name__ == "__main__":
    from numpy.distutils.core import setup
    setup(name         = 'gsidiag',
          version      = '2.0',
          description  = "Read and plot GSI diagnostics files",
          author       = "Joao Gerd Z. de Mattos",
          author_email = "joao.gerd@inpe.br",
          packages=setuptools.find_packages(),
          package_data={'': ['table']},

#          packages     = ['gsidiag'],
#          package_dir  = {'gsidiag':'src'},
          install_requires=["numpy","matplotlib",'basemap'],
          platforms = ["any"],
          ext_modules = [ext]
          )
#          packages = setuptools.find_packages(),

#          dependency_links=['git+https://github.com/matplotlib/basemap#egg=python-s3','https://github.com/matplotlib/basemap/archive/v1.1.0.tar.gz'],
#EOC
#-----------------------------------------------------------------------------#

