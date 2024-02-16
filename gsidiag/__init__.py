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
"""
This package defines some functions to read and plot gsi diagnostic files.\
For help please use help() function.
"""
from .__main__ import (help,getColor,geoMap,setcolor,read_diag,plot_diag)
from .datasources import getVarInfo

__name__    = 'readDiag'
__version__ = '1.2.3'

#EOC
#-----------------------------------------------------------------------------#

