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

ext  = Extension(name='diag2python',
                 extra_f77_compile_args=['-fconvert=big-endian'],
                 extra_f90_compile_args=['-fconvert=big-endian'],
                 extra_link_args=['-fconvert=big-endian'],
                 sources=['gsidiag/f90/m_string.f90',
                          'gsidiag/f90/ReadDiagMod.f90',
                          'gsidiag/f90/ReadDiagModRad.f90',
                          'gsidiag/f90/diag2python.f90',
			              'gsidiag/f90/diag2python.pyf'])

if __name__ == "__main__":
    from numpy.distutils.core import setup
    setup(name='readDiag',
          version='1.2.3',
          long_description=open('README.md').read(),
          long_description_content_type='text/markdown',
          description='A Python class to read and plot the Gridpoint Statistical Interpolation diagnostics files.',
          author='Joao Gerd Z. de Mattos',
          author_email='joao.gerd@inpe.br',
          project_urls={
              'Source': 'https://github.com/GAD-DIMNT-CPTEC/readDiag',
              'Documentation': 'https://gad-dimnt-cptec.github.io/readDiag/',
          },
          license='CC BY-NC-SA-4.0',
          keyword=['gridpoint statistical interpolation', 'atmospheric data assimilation'],
          packages=['gsidiag'],
          package_data={'': ['table']},

          install_requires=['numpy>=1.22','matplotlib==3.8.2', 'xarray', 'Cartopy>=0.22.0', 'geopandas', 'jupyterlab'],
          platforms=['any'],
          zip_safe=False, 
          ext_modules=[ext],
          python_requires='>=3.9.18',
          )
#EOC
#-----------------------------------------------------------------------------#
