#!/usr/bin/env python3
#-----------------------------------------------------------------------------#
#           Group on Data Assimilation Development - GDAD/CPTEC/INPE          #
#-----------------------------------------------------------------------------#
#BOP
#
# !SCRIPT: gsiDiag.py
#
# !DESCRIPTION: Class to read and plot GSI diagnostics files.
#
# !CALLING SEQUENCE:
#
# !REVISION HISTORY: 
# 09 out 2017 - J. G. de Mattos - Initial Version
#
# !REMARKS:
#   Work only with conventional diganostics files
#
#EOP
#-----------------------------------------------------------------------------#
#BOC

"""
This module defines the majority of gsidiag functions, including all plot types
"""
from diag2python import diag2python as d2p
#import .datasources as ds
from .datasources import getVarInfo
#from memory_profiler import profile
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mpl_toolkits.axes_grid1 import make_axes_locatable
from cartopy import crs as ccrs
import gc

def help():
    print('Esta é uma ajudada')


def getColor(minVal, maxVal, value, hex=False, cmapName=None):

    try:
       import matplotlib.cm as cm
       from matplotlib.colors import Normalize
       from matplotlib.colors import rgb2hex
    except ImportError:
       pass # module doesn't exist, deal with it.

    if cmapName is None:
        cmapName='Paired'

    # Get a color map
    cmap = cm.get_cmap(cmapName)

    # Get normalize function (takes data in range [vmin, vmax] -> [0, 1])
    norm = Normalize(vmin=minVal, vmax=maxVal)
    
    if hasattr(value,'__iter__'):

       color = []
       for i in range(len(value)):
          if hex is True:
              color.append(rgb2hex(cmap(norm(value[i]))))
          else:
              color.append(cmap(norm(value[i]),bytes=True))

    else:

        if hex is True:
            color = rgb2hex(cmap(norm(value)))
        else:
            color = cmap(norm(value),bytes=True)

    return color

def geoMap(**kwargs):
    
    if 'ax' not in kwargs:
        fig  = plt.figure(figsize=(12, 12))
        ax   = fig.add_subplot(1, 1, 1)#, projection=ccrs.PlateCarree())
    else:
        ax = kwargs['ax']
        del kwargs['ax']

    
    path=gpd.datasets.get_path('naturalearth_lowres')
    
    world = gpd.read_file(path)
    gdp_max = world['gdp_md_est'].max()
    gdp_min = world['gdp_md_est'].min()
    
    ax = world.plot(ax=ax, facecolor='lightgrey', edgecolor='k')#,**kwargs)
    
    # set axis range
    ax.set_xlim([-180,180])
    ax.set_xlabel('Longitude')
    ax.set_ylim([ -90, 90])
    ax.set_ylabel('Latitude')

    return ax

class read_diag(object):
    """
    read a diagnostic file from gsi. Return an array with
    some information.
    """
    #@profile(precision=8)
    def __init__(self, diagFile, diagFileAnl=None, isisList=None, zlevs=None):

        self._diagFile     = diagFile
        self._diagFileAnl  = diagFileAnl

        if diagFileAnl == None:
            extraInfo = False
        else:
            extraInfo = True

        convIndex =['lat','lon', 'elev', 'prs', 'hgt', 'press', 'time', 'idqc', 'iuse', 'iusev', 
                   'wpbqc', 'inp_err', 'adj_err', 'inverr', 'oer', 'obs', 'omf', 'oma', 'imp', 'dfs']

        radIndex  = ['lat','lon','elev','nchan','time','iuse','idqc','inverr','oer','obs',
                     'omf','omf_nobc','emiss','oma','oma_nobc','imp','dfs']
                     
        if isisList is None:
            isis = np.array(['None'],dtype='c').T
        else:
            # put all string with same length
            s=len(max(isisList,key=len))
            l=[]
            for i in isisList:
                l.append(i.ljust(s,' '))
            isis = np.array(l,dtype='c').T
            
        self._FNumber    = d2p.open(self._diagFile, self._diagFileAnl, isis)
        if (self._FNumber <= -1):
            self._FNumber = None
            print('Some was was wrong during reading files ...')
            return

        self._FileType   = d2p.getFileType(self._FNumber)
        if (self._FileType == -1):
            print('Some wrong was happening!')
            return
        
        self._undef = d2p.getUndef(self._FNumber)
        
        # set default levels to obtain data information
        if zlevs is None:
           self.zlevs = [1000.0,900.0,800.0,700.0,600.0,500.0,400.0,300.0,250.0,200.0,150.0,100.0,50.0,0.0]
        else:
           self.zlevs = zlevs

        #
        # Get extra informations
        #

        self._nVars     = d2p.getnvars(self._FNumber)
        vnames,nTypes   = d2p.getObsVarInfo(self._FNumber,self._nVars);
        self.varNames   = []
        self.obsInfo    = {}
        for i, name in enumerate(vnames):
            obsName = name.tostring().decode('UTF-8').strip()
            self.varNames.append(obsName)
            vTypes, svTypes = d2p.getVarTypes(self._FNumber,obsName, nTypes[i])
            sTypes = svTypes.tostring().decode('UTF-8').strip().split()
            df = {}
            if self._FileType == 1:
            # for convetional data
               for i, vType in enumerate(vTypes):
                   nObs = d2p.getobs(self._FNumber, obsName, vType, 'None', self.zlevs, len(self.zlevs))
                   if extraInfo is True:
                       d = pd.DataFrame(d2p.array2d.copy().T,index=convIndex).T
                       d.loc[d.oer == self._undef,["oer","imp","dfs"]] = np.nan
                       d2p.array2d = None
                   else:
                       d = pd.DataFrame(d2p.array2d.copy().T,index=convIndex[:17]).T
                       d2p.array2d = None
                   lon = (d.lon + 180) % 360 - 180
                   lat = d.lat
                   df[vType] = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(lon,lat))
                
            elif self._FileType == 2:
            # for satellite data
               for i, sType in enumerate(sTypes):
                   nObs = d2p.getobs(self._FNumber, obsName, 0, sType, self.zlevs, len(self.zlevs))
                   if extraInfo is True:
                       d   = pd.DataFrame(d2p.array2d.copy().T,index=radIndex).T
                       d.loc[d.oer == self._undef,["oer","imp","dfs"]] = np.nan
                       d2p.array2d = None
                   else:
                       d = pd.DataFrame(d2p.array2d.copy().T,index=radIndex[:13]).T
                       d2p.array2d = None
                   lon = (d.lon + 180) % 360 - 180
                   lat = d.lat
                   df[sType] = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(lon,lat))


            if self._FileType == 1:
                self.obsInfo[obsName] = pd.concat(df.values(),keys=df.keys(), names=['kx','points'])
            elif self._FileType == 2:
                self.obsInfo[obsName] = pd.concat(df.values(),keys=df.keys(), names=['SatId','points'])
            
        self.obs  = pd.concat(self.obsInfo, sort=False).reset_index(level=2, drop=True)

    def plot(self, var, id, param, mask=None, **kwargs):
        '''
        A função pgeomap faz plotagem da variável selecionada para cada tipo de fonte escolhida para uma determinada data e camada.
 
        Exemplo:
        gd.plot('ps', 187, 'obs', mask='iuse' == 1)
        
        No exemplo acima, será feito o plot do valor observado referente à variável pressão em superfície (ps)
        para a fonte 187 (ADPSFC) 
 
        lat:   Todas as latitudes das fontes utilizadas
        lon:   Todas as longitudes das fontes utilizadas
        prs:   Nível de pressão da observação.
        lev:   Níveis de pressão da observação.
        time:  Tempo de observação (minutos relativo ao tempo de análise)
        idqc:  PreBuffer de entrada qc ou event mark
        iuse:  Flag utilizado na análise (1=use; -1=monitoring)
        iusev: Flag utilizado na análise (valor)
        obs:  Observação
          
 
        '''
        #
        # Parse options 
        #
        if 'style' in kwargs:
            plt.style.use(kwargs['style'])
            del kwargs['style']
        else:
            plt.style.use('seaborn')
        
        if 'ax' not in kwargs:
            fig = plt.figure(figsize=(12, 12))
            ax  = fig.add_subplot(1, 1, 1)
        else:
            ax = kwargs['ax']
            del kwargs['ax']

        if kwargs.get('legend') is True:
            divider = make_axes_locatable(ax)
            cax     = divider.append_axes("right", size="5%", pad=0.1)
            kwargs['cax'] = cax

        if 'title' in kwargs:
            ax.set_title(kwargs['title'])

        if 'cmap' not in kwargs:
            kwargs['cmap'] = 'jet'

        ax = geoMap(ax=ax)

        if mask is None:
            ax  = self.obsInfo[var].loc[id].plot(param, ax=ax, **kwargs)
        else:
            df = self.obsInfo[var].loc[id]
            ax = df.query(mask).plot(param, ax=ax, **kwargs)

        
        return ax

    def ptmap(self, var, kxList=None, mask=None, **kwargs):
        '''
        A função ptmap faz plotagem da variável selecionada para cada tipo de fonte escolhida para uma determinada data.

        Exemplo:
        a.ptmap('uv', [290, 224, 223], )
        
        No exemplo acima, será feito o plot do vento (uv) para as fontes 290 (ASCATW), 224 (VADWND) e 223 (PROFLR)

        '''
        #
        # Parse options 
        #

        if 'style' in kwargs:
            plt.style.use(kwargs['style'])
            del kwargs['style']
        else:
            plt.style.use('seaborn')

        if 'ax' not in kwargs:
            fig  = plt.figure(figsize=(12, 12))
            ax   = fig.add_subplot(1, 1, 1)
        else:
            ax = kwargs['ax']
            del kwargs['ax']

        if kxList is None:
            kxList = self.obsInfo[var].index.levels[0].tolist()

        if 'alpha' not in kwargs:
            kwargs['alpha'] = 0.5

        if 'marker' not in kwargs:
            kwargs['marker'] = '*'

        if 'markersize' not in kwargs:
            kwargs['markersize'] = 5

        if 'linewidth' not in kwargs:
            kwargs['linewidth'] = 1

        if 'legend' not in kwargs:
            kwargs['legend'] = False
            legend = True
        else:
            legend = kwargs['legend']
            kwargs['legend'] = False
                
        
        ax = geoMap(ax=ax)

        # color range
        if type(kxList) is list:
            cmin = 0
            cmax = len(kxList)-1
        else:
            kxList = [kxList]
            cmin = 0
            cmax = 1

        legend_labels = []
        for i, kx in enumerate(kxList):
            df    = self.obsInfo[var].loc[kx]

            color = getColor(minVal=cmin, maxVal=cmax,
                             value=i,hex=True,cmapName='Paired')
            instr = getVarInfo(kx,var,'instrument')
            legend_labels.append(mpatches.Patch(color=color, 
                                 label=var + '-' + str(kx) + ' | ' + instr)
                                )

            if mask is None:
               ax = df.plot(ax=ax,c=color, **kwargs)
            else:
               ax = df.query(mask).plot(ax=ax,c=color, **kwargs)
        
        if legend is True:
            plt.subplots_adjust(left=0.05, bottom=0.05, right=0.70, top=0.90, wspace=0, hspace=0)
            plt.legend(handles=legend_labels, loc='upper right', bbox_to_anchor=(1.41, 1),
                       fancybox=False, shadow=False, frameon=False, numpoints=1, prop={"size": 9})

        plt.title('Distribuição Espacial dos Dados na Assimilação')


        return ax


    def pvmap(self, varList=None, mask=None, **kwargs):
        '''
        A função pvmap faz plotagem das variáveis selecionadas sem identificar o tipo de fonte para uma determinada data. 

        Exemplo:
        a.pvmap(['uv','ps','t','q'], mask='iuse==1')
        
        No exemplo acima, será feito o plot do vento (uv), da pressão em superfície (ps), da temperatura (t) e da umidade (q)
        dos dados assimilados (iuse=1).

        '''
        #
        # Parse options 
        #
        
        if 'style' in kwargs:
            plt.style.use(kwargs['style'])
            del kwargs['style']
        else:
            plt.style.use('seaborn')
        
        if 'ax' not in kwargs:
            fig = plt.figure(figsize=(12, 12))
            ax  = fig.add_subplot(1, 1, 1)
        else:
            ax = kwargs['ax']
            del kwargs['ax']

        if 'alpha' not in kwargs:
            kwargs['alpha'] = 0.5

        if 'marker' not in kwargs:
            kwargs['marker'] = '*'

        if 'markersize' not in kwargs:
            kwargs['markersize'] = 5

        if 'linewidth' not in kwargs:
            kwargs['linewidth'] = 1

        if 'legend' not in kwargs:
            kwargs['legend'] = False
            legend = True
        else:
            legend = kwargs['legend']
            kwargs['legend'] = False

        #
        # total by var
        #
        
        total = self.obs.groupby(level=0).size()

        #
        # parse options em kwargs

        if varList is None:
            varList = total.sort_values(ascending=False).keys()
        else:
            if type(varList) is list:
               varList = total[varList].sort_values(ascending=False).keys()
            else:
                varList = [varList]
        
        ax = geoMap(ax=ax)

        
        colors_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']
        setColor = 0
        legend_labels = []
        for var in varList:
            df    = self.obsInfo[var]
            legend_labels.append(mpatches.Patch(color=colors_palette[setColor], label=var) )

            if mask is None:
               ax = df.plot(ax=ax,c=colors_palette[setColor], **kwargs)
            else:
               ax = df.query(mask).plot(ax=ax,c=colors_palette[setColor], **kwargs)
            setColor += 1

        if legend is True:
            plt.legend(handles=legend_labels, numpoints=1, loc='best', bbox_to_anchor=(1.1, 0.6), 
                       fancybox=False, shadow=False, frameon=False, ncol=1, prop={"size": 10})


        return ax


    def pcount(self,varName,**kwargs):

        """
        Plots a histogram of the desired variable and types.

        Usage: pcount(VarName)
        """

        try:
           import matplotlib.pyplot as plt
           import matplotlib.cm as cm
           from matplotlib.colors import Normalize

        except ImportError:
           pass # module doesn't exist, deal with it.
        #
        # Parse options 
        #

        if 'style' in kwargs:
            plt.style.use(kwargs['style'])
            del kwargs['style']
        else:
            plt.style.use('seaborn')

        if 'alpha' not in kwargs:
            kwargs['alpha'] = 0.5

        if 'rot' not in kwargs:
            kwargs['rot'] = 45

        if 'legend' not in kwargs:
            kwargs['legend'] = False


        df = self.obsInfo[varName].groupby(level=0).size()

        # Get a color map
        colors = getColor(minVal=df.min(),maxVal=df.max(),
                          value=df.values,hex=True,cmapName='Paired')

        df.plot.bar(color=colors,**kwargs)

        plt.ylabel('Number of Observations')
        plt.xlabel('KX')
        plt.title('Variable Name : '+varName)
 
        plt.show()

    def vcount(self,**kwargs):

        """
        Plots a histogram of the total count of eath variable.

        Usage: pcount(**kwargs)
        """

        try:
           import matplotlib.pyplot as plt
           import matplotlib.cm as cm
           from matplotlib.colors import Normalize

        except ImportError:
           pass # module doesn't exist, deal with it.
        #
        # Parse options 
        #

        if 'style' in kwargs:
            plt.style.use(kwargs['style'])
            del kwargs['style']
        else:
            plt.style.use('seaborn')

        if 'alpha' not in kwargs:
            kwargs['alpha'] = 0.5

        if 'rot' not in kwargs:
            kwargs['rot'] = 90

        if 'legend' not in kwargs:
            kwargs['legend'] = False

        df = pd.DataFrame({key: len(value) for key, value in self.obsInfo.items()},index=['total']).T

        # Get a color map
        colors = getColor(minVal=df.min(),maxVal=df.max(),
                          value=df['total'].values,hex=True,cmapName='Paired')
         
        df.plot.bar(color=colors, **kwargs)

        plt.ylabel('Number of Observations')
        plt.xlabel('Variable Names')
        plt.title('Total Number of Observations')
 
        plt.show()

    def kxcount(self,**kwargs):

        """
        Plots a histogram of the total count by KX.

        Usage: pcount(**kwargs)
        """

        try:
           import matplotlib.pyplot as plt
           from matplotlib.colors import Normalize

        except ImportError:
           pass # module doesn't exist, deal with it.
        #
        # Parse options 
        #

        if 'style' in kwargs:
            plt.style.use(kwargs['style'])
            del kwargs['style']
        else:
            plt.style.use('seaborn')

        if 'alpha' not in kwargs:
            kwargs['alpha'] = 0.5

        if 'rot' not in kwargs:
            kwargs['rot'] = 90

        if 'legend' not in kwargs:
            kwargs['legend'] = False

        d  = pd.concat(self.obsInfo, sort=False).reset_index(level=2, drop=True)
        df = d.groupby(['kx']).size()

        # Get a color map
        colors = getColor(minVal=df.min(),maxVal=df.max(),
                          value=df.values,hex=True,cmapName='Paired')
         
         
        plt.style.use('seaborn')
        df.plot.bar(color=colors, **kwargs)

        plt.ylabel('Number of Observations by KX')
        plt.xlabel('KX number')
        plt.title('Total Number of Observations')
 
        plt.show()

    def overview(self):

        """
        Creates a dictionary of the existing variables and types. Returns a Python dictionary.

        Usage: overview()
        """

        variablesList = {}
        for var in self.varNames:
            variablesTypes = []
            for kx in self.obsInfo[var].index.levels[0]:
                variablesTypes.append(kx)
            variablesList.update({var:variablesTypes})
        return variablesList

    def pfileinfo(self):

        """
        Prints a fancy list of the existing variables and types.

        Usage: pfileinfo()
        """

        for name in self.varNames:
            print('Variable Name :',name)
            print('              └── kx => ', end='', flush=True)
            for kx in self.obsInfo[name].index.levels[0]:
               print(kx,' ', end='', flush=True)
            print()

            print()

            
    def close(self):

        """
        Closes a previous openned file. Returns an integer status value.

        Usage: close()
        """

        iret = d2p.close(self._FNumber)
        self._FileName = None # File name
        self._FNumber  = None # File unit number to be closed
        self._nVars    = None # Total of variables
        self.varNames  = None # Name of variables
        self.obsInfo   = None 
        self.nObs      = None # Number of observations for vName
        del self
        gc.collect()
        
        return iret

    
#EOC
#-----------------------------------------------------------------------------#

