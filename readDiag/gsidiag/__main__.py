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
import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
from cartopy import crs as ccrs

def help():
    print('Esta é uma ajudada')

class read_diag(object):
    """
    read a diagnostic file from gsi. Return an array with
    some information.
    """

    def __init__(self, diagFile, diagFileAnl=None, isisList=None, zlevs=None):

        self.diagFile     = diagFile
        self.diagFileAnl  = diagFileAnl

        if diagFileAnl == None:
            extraInfo = False
        else:
            extraInfo = True

        convIndex =['lat','lon', 'elev', 'prs', 'hgt', 'press', 'time', 'pbqc', 'iuse', 'iusev', 
                   'wpbqc', 'inp_err', 'adj_err', 'end_err', 'robs', 'omf', 'oma', 'imp', 'dfs']

        radIndex  = ['lat','lon','elev','nchan','time','iuse','idqc','errinv','oer','tb_obs',
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
            
        self.FNumber    = d2p.open(self.diagFile, self.diagFileAnl, isis)

        if (self.FNumber == -1):
            self.FNumber = None
            return

        self.FileType   = d2p.getFileType(self.FNumber)
        if (self.FileType == -1):
            print('Some wrong was happening!')
            return
        

        # set default levels to obtain data information
        if zlevs is None:
           self.zlevs = [1000.0,900.0,800.0,700.0,600.0,500.0,400.0,300.0,250.0,200.0,150.0,100.0,50.0,0.0]
        else:
           self.zlevs = zlevs

        #
        # Get extra informations
        #

        self.nVars      = d2p.getnvars(self.FNumber)
        vnames,nTypes   = d2p.getObsVarInfo(self.FNumber,self.nVars);
        self.varNames   = []
        self.obsInfo    = {}
        for i, name in enumerate(vnames):
            obsName = name.tostring().decode('UTF-8').strip()
            self.varNames.append(obsName)
            vTypes, svTypes = d2p.getVarTypes(self.FNumber,obsName, nTypes[i])
            sTypes = svTypes.tostring().decode('UTF-8').strip().split()
            df = {}
            if self.FileType == 1:
            # for convetional data
               for i, vType in enumerate(vTypes):
                   nObs = d2p.getobs(self.FNumber, obsName, vType, 'None', self.zlevs, len(self.zlevs))
                   if extraInfo is True:
                       d = pd.DataFrame(d2p.array2d.copy().T,index=convIndex).T
                       d2p.array2d = None
                   else:
                       d = pd.DataFrame(d2p.array2d.copy().T,index=convIndex[:16]).T
                       d2p.array2d = None
                   lon = (d.lon + 180) % 360 - 180
                   lat = d.lat
                   df[sType] = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(lon,lat))
                
            elif self.FileType == 2:
            # for satellite data
               for i, sType in enumerate(sTypes):
                   nObs = d2p.getobs(self.FNumber, obsName, 0, sType, self.zlevs, len(self.zlevs))
                   if extraInfo is True:
                       d   = pd.DataFrame(d2p.array2d.copy().T,index=radIndex).T
                       d2p.array2d = None
                   else:
                       d = pd.DataFrame(d2p.array2d.copy().T,index=radIndex[:13]).T
                       d2p.array2d = None
                   lon = (d.lon + 180) % 360 - 180
                   lat = d.lat
                   df[sType] = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(lon,lat))

            if self.FileType == 1:
                self.obsInfo[obsName] = pd.concat(df.values(),keys=df.keys(), names=['kx','points'])
            elif self.FileType == 2:
                self.obsInfo[obsName] = pd.concat(df.values(),keys=df.keys(), names=['SatId','points'])

    def plot(self, var, sat, diag, mask=None, ax=None, **plt_kwargs):

         if ax is None:
             fig = plt.figure(figsize=(12, 12))
             ax  = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

         path=gpd.datasets.get_path('naturalearth_lowres')

         world = gpd.read_file(path)
         gdp_max = world['gdp_md_est'].max()
         gdp_min = world['gdp_md_est'].min()

         ax = world.plot(ax=ax, facecolor='lightgrey', edgecolor='grey', )
         
         if mask is None:
             ax = self.obsInfo[var].loc[sat].plot(diag, ax=ax, **plt_kwargs)
         else:
             df = self.obsInfo[var].loc[sat]
             ax = df.query(mask).plot(diag, ax=ax, **plt_kwargs)

         
#         if plt_kwargs['legend'] == True:
#             plt.title( title=var+'_'+sat )



         return fig, ax

    def close(self):

        """
        Closes a previous openned file. Returns an integer status value.

        Usage: close()
        """

        iret = d2p.close(self.FNumber)
        self.FileName = None # File name
        self.FNumber  = None # File unit number to be closed
        self.nVars    = None # Total of variables
        self.VarNames = None # Name of variables
        self.ObsInfo  = None 
        self.nObs     = None # Number of observations for vName
        return iret


#EOC
#-----------------------------------------------------------------------------#

