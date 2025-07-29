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
# 25 jul 2025 - J. G. de Mattos - Initial Version
#
# !REMARKS:
#
#EOP
#-----------------------------------------------------------------------------#
#BOC


#EOC
#-----------------------------------------------------------------------------#

# ---------------------------------------------------------------------------
#src/readDiag/__init__.py
# ---------------------------------------------------------------------------

try:
    from .reader import diagAccess
    from .plotting import diagPlotter
    from .style import PlotConfig
    from .impact import ImpactAnalyzer, ExperimentComparator, ComparisonPlotter
    __all__ = ['diagAccess', 'diagPlotter', 'PlotConfig', 'ImpactAnalyzer', 'ExperimentComparator', 'ComparisonPlotter']
except ModuleNotFoundError:
    pass  # ou log, ou warning


