#!/usr/bin/env python3
#-----------------------------------------------------------------------------#
#           Group on Data Assimilation Development - GDAD/CPTEC/INPE          #
#-----------------------------------------------------------------------------#
#BOP
#
# !SCRIPT: ReadDiag.py
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

from diag2python import diag2python as d2p
import numpy as np
import pandas as pd

class open(object):
    FileName  = None  # File name (gsi diag from ges or anl)
    FileName2 = None  # File name (gsi diag from anl)
    FNumber   = None  # File unit number to be opened
    nVars     = None  # Total of variables
    VarNames  = None  # Name of variables
    ObsInfo   = None  #
    nObs      = None  # Number of observations for vName
    used      = False # Variable used (or not) in GSI

    def __init__(self,FileName, FileName2=None):
        self.FileName   = FileName
        self.FileName2  = FileName2
        self.FNumber    = d2p.open(self.FileName, self.FileName2)

        if (self.FNumber == -1):
            self.FNumber = None
            return

        self.__used = True

        # set default levels to obtain data information
        self.std_levs = [1000.0,900.0,800.0,700.0,600.0,500.0,400.0,300.0,250.0,200.0,150.0,100.0,50.0,0.0]

        #
        # Get extra informations
        #

        self.nVars      = d2p.getnvars(self.FNumber)
        vnames          = d2p.getvarnames(self.FNumber,self.nVars)
        self.VarNames   = []
        self.ObsInfo    = {}
        for i, name in enumerate(vnames):
            self.VarNames.append(name.tostring().decode('UTF-8').strip())
            ttt = d2p.getvarinfo(self.FNumber, self.VarNames[i])
            self.ObsInfo[self.VarNames[i]] = d2p.array2d.astype(int).copy()
            d2p.array2d = None
            
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


    def GTable(self, VarName, kx, ObsLevels=None):

        """
        Creates a list of the desired variable. Returns a Numpy array.

        Usage: GTable(VarName, kx, ObsLevels=None)
        """

        if ObsLevels == None:
           self.nObs     = d2p.getobs(self.FNumber, VarName, kx, self.std_levs, len(self.std_levs))
        else:
           self.nObs     = d2p.getobs(self.FNumber, VarName, kx, ObsLevels, len(ObsLevels))


        if (self.nObs > 0):
            ObsTable      = d2p.array2d.copy()
            d2p.array2d   = None
        else:
            print('No observation found for ObsName',VarName, 'and ObsType', kx)
            ObsTable = None

        return ObsTable

    def GTable_df(self, VarName, kx, ObsLevels=None):

        """
        Creates a list of the desired variable. Returns a Pandas dataframe.

        Usage: GTable_df(VarName, kx, ObsLevels=None)
        """
        
        if ObsLevels == None:
           self.nObs     = d2p.getobs(self.FNumber, VarName, kx, self.std_levs, len(self.std_levs))
        else:
           self.nObs     = d2p.getobs(self.FNumber, VarName, kx, ObsLevels, len(ObsLevels))


        if (self.nObs > 0):
            ObsTable      = d2p.array2d.copy()
            d2p.array2d   = None
        else:
            print('No observation found for ObsName',VarName, 'and ObsType', kx)
            ObsTable = None

        # Create a pandas dataframe from the ObsTable object:
        ObsTable_df = pd.DataFrame(ObsTable)

        # Rename the columns of the dataframe
        ObsTable_df.columns = ["lat","lon","elev","prs","dhgt","levs",         \
                           "time","pbqc","iuse","iusev","wpbqc","inp_err", \
                           "adj_err","end_err","robs","omf","oma","imp","dfs","kx"]

        return ObsTable_df

    def GDict(self, VarName, kx, ObsLevel=None, ObsLevels=None):

        """
        Return a dicionary with observations info by class.

        Attributes:
           lat     : observation latitude (degrees)
           lon     : observation longitude (degrees)
           elev    : station elevation (meters)
           prs     : observation pressure (hPa)
           dhgt    : observation height (meters)
           levs    : observation reference level (hPa)
           time    : obs time (minutes relative to analysis time)
           pbqc    : input prepbufr qc or event mark
           iuse    : analysis usage flag (1=use, -1=monitoring )
           iusev   : analysis usage flag ( value )
           wpbqc   : nonlinear qc relative weight
           inp_err : prepbufr inverse obs error (unit**-1)
           adj_err : read_prepbufr inverse obs error (unit**-1)
           end_err : final inverse observation error (unit**-1)
           robs    : observation
           diff    : obs-ges used in analysis (K)
           rmod

         Some dependent attributs:
           qsges : guess saturation specific humidity (only for humidity)
           factw : 10m wind reduction factor (only for wind speed)
           pof   : data pof (only for temperature aircraft)
           wvv   : data vertical velocity (only for temperature aircraft)
           tref  : sst Tr (adiative transfer model) (only for sst observation)
           dtw   : sst dt_warm at zob (only for sst observation)
           dtc   : sst dt_cool at zob (only for sst observation)
           tz    : sst d(tz)/d(tr) at zob (only for sst observation)

        Usage: GDict(VarName, kx, ObsLevel=None, ObsLevels=None)
        """

        if ObsLevels == None:
           __tmp = self.GTable(VarName, kx, self.std_levs)
        else:
           __tmp = self.GTable(VarName, kx, ObsLevels)

        ObsDict = {}
        if self.nObs > 0:
            if not ObsLevel == None:
                Glat, Glon, Gelev, Gprs, Gdhgt,
                Glev, Gtime, Gpbqc, Giuse, Giusev, 
                Gwpbqc, Ginp_err, Gadj_err, Gend_err, 
                Grobs, Gdiff, Grmod = [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []
                if (VarName == 'q'):                   
                    Gqsges= []
                elif (VarName == 'uv'):
                    Gfactw = []
                elif (VarName == 't'):
                    Gpof, Gwvv = [], []
                elif (VarName == 'sst'):
                    GTref, Gdtw, Gdtc, Gtz = [], [], [], [], []

                for idx in range(0, len(__tmp)):
                    if int(__tmp[idx, 3]) == ObsLevel:
                        Glat.append(__tmp[idx,  0])
                        Glon.append(__tmp[idx,  1])
                        Gelev.append(__tmp[idx,  2])
                        Gprs.append(__tmp[idx,  3])
                        Gdhgt.append(__tmp[idx,  4])
                        Glev.append(__tmp[idx,  5])
                        Gtime.append(__tmp[idx,  6])
                        Gpbqc.append(__tmp[idx,  7])
                        Giuse.append(__tmp[idx,  8])
                        Giusev.append(__tmp[idx,  9])
                        Gwpbqc.append(__tmp[idx, 10])
                        Ginp_err.append(__tmp[idx, 11])
                        Gadj_err.append(__tmp[idx, 12])
                        Gend_err.append(__tmp[idx, 13])
                        Grobs.append(__tmp[idx, 14])
                        Gdiff.append(__tmp[idx, 15])
                        Grmod.append(__tmp[idx, 16])

                        if (VarName == 'q'):
                            Gqsges.append(__tmp[idx, 18])
                        elif(VarName == 'uv'):
                            Gfactw.append(__tmp[idx, 18])
                        elif(VarName == 't'):
                            Gpof.append(__tmp[idx, 18])
                            Gwvv.append(__tmp[idx, 19])
                        elif(VarName == 'sst'):
                            GTref.append(__tmp[idx, 18])
                            Gdtw.append(__tmp[idx, 19])
                            Gdtc.append(__tmp[idx, 20])
                            Gdz.append(__tmp[idx, 21])
            else:
                Glat     = __tmp[ : ,  0]
                Glon     = __tmp[ : ,  1]
                Gelev    = __tmp[ : ,  2]
                Gprs     = __tmp[ : ,  3]
                Gdhgt    = __tmp[ : ,  4]
                Glev     = __tmp[ : ,  5]
                Gtime    = __tmp[ : ,  6]
                Gpbqc    = __tmp[ : ,  7]
                Giuse    = __tmp[ : ,  8]
                Giusev   = __tmp[ : ,  9]
                Gwpbqc   = __tmp[ : , 10]
                Ginp_err = __tmp[ : , 11]
                Gadj_err = __tmp[ : , 12]
                Gend_err = __tmp[ : , 13]
                Grobs    = __tmp[ : , 14]
                Gdiff    = __tmp[ : , 15]
                Grmod    = __tmp[ : , 16]

                ObsDict.update({'lat':   Glat})
                ObsDict.update({'lon':   Glon})
                ObsDict.update({'elev':  Gelev})
                ObsDict.update({'prs':   Gprs})
                ObsDict.update({'dhgt':  Gdhgt})
                ObsDict.update({'lev':   Glev})
                ObsDict.update({'time':  Gtime})
                ObsDict.update({'pbqc':  Gpbqc})
                ObsDict.update({'iuse':  Giuse})
                ObsDict.update({'iusev': Giusev})
                ObsDict.update({'wpbqc': Gwpbqc})
                ObsDict.update({'inp_err': Ginp_err})
                ObsDict.update({'adj_err': Gadj_err})
                ObsDict.update({'end_err': Gend_err})
                ObsDict.update({'robs':  Grobs})
                ObsDict.update({'diff':  Gdiff})
                ObsDict.update({'rmod':  Grmod})

                if (VarName == 'q'):
                    Gqsges = __tmp[ : , 18]
                    ObsDict.update({'qsges':  Gqsges})
                elif(VarName == 'uv'):
                    Gfactw = __tmp[ : , 18]
                    ObsDict.update({'factw':  Gfactw})
                elif(VarName == 't'):
                    Gpof = __tmp[ : , 18]
                    Gwvv = __tmp[ : , 19]
                    ObsDict.update({'pof':  Gpof})
                    ObsDict.update({'wvv':  Gwvv})
                elif(VarName == 'sst'):
                    GTref = __tmp[ : , 18]
                    Gdtw  = __tmp[ : , 19]
                    Gdtc  = __tmp[ : , 20]
                    Gdz   = __tmp[ : , 21]
                    ObsDict.update({'Tref': GTref})
                    ObsDict.update({'dtw':  Gdtw})
                    ObsDict.update({'dtc':  Gdtc})
                    ObsDict.update({'tz':   Gtz})

            d2p.array2d     = None
        else:
            print('No observation found for ObsName', VarName, 'and ObsType', kx)
            ObsTable = None

        return ObsDict


    def overview(self):

        """
        Creates a dictionary of the existing variables and types. Returns a Python dictionary.

        Usage: overview()
        """

        variablesList = {}
        for var in self.VarNames:
            variablesTypes = []
            for kx in self.ObsInfo[var][:,0]:
                variablesTypes.append(kx)
            variablesList.update({var:variablesTypes})

        return variablesList

    def pfileinfo(self):

        """
        Prints a fancy list of the existing variables and types.

        Usage: pfileinfo()
        """

        for name in self.VarNames:
            print('Variable Name :',name)
            print('              └── kx => ', end='', flush=True)
            for kx in self.ObsInfo[name][:,0]:
               print(kx,' ', end='', flush=True)
            print()

#            for kx in self.ObsInfo[name][:,0]:
#               print('{0:7d}'.format(kx),' ', end='', flush=True)
#            print()
#            print('             └── total :', end='', flush=True)
#            for total in self.ObsInfo[name][:,1]:
#               print('|{0:7d}|'.format(total),' ', end='', flush=True)
#            print()
            print()


    def pcount(self,VarName):

        """
        Plots a histogram of the desired variable and types.

        Usage: pcount(VarName)
        """

        try:
           import matplotlib.pyplot as plt
        except ImportError:
           pass # module doesn't exist, deal with it.

        kx       = self.ObsInfo[VarName][:,0]
        y_pos    = np.arange(len(kx))
        contagem = self.ObsInfo[VarName][:,1]
 
        plt.bar(y_pos, contagem, align='center', alpha=0.5)
        plt.xticks(y_pos, kx)
        plt.ylabel('Number of Observations')
        plt.xlabel('KX')
        plt.title('Variable Name : '+VarName)
        plt.xticks(rotation = 45)
 
        plt.show()

    def pgeomap(self, VarName, kx, WhatPlot, title=None, Data=None, Nmin=None, Nmax=None, WhatLabel=None):

        """
        Plots a spatial distribution of a desired variable and type with a specified attribute.

        Usage: pgeomap(VarName, kx, WhatPlot, title=None, Data=None, Nmin=None, Nmax=None, WhatLabel=None)
        """

        from mpl_toolkits.basemap import Basemap
        import matplotlib.pyplot as plt

        __tmp = self.GTable(VarName, kx)

        if not __tmp is None:

            # Make this plot larger.
#            fig = plt.figure(figsize=(11.0, 8.5))
#            ax  = fig.add_subplot(111)
#            fig, ax = plt.subplots(1,1,figsize=(8,9))
            fig, ax = plt.subplots(1,figsize=(10,8))
            # Define map as cylindical equidistant
            m = Basemap(projection = 'cyl', # Projection map
                        llcrnrlat  =  -90,  #Lower Left  CoRNeR Latitude
                        urcrnrlat  =   90,  #Upper Right CoRNeR Latitude
                        llcrnrlon  = -180,  #Lower Left  CoRNeR Longitude
                        urcrnrlon  =  180,  #Upper Right CoRNeR Longitude
                        resolution = 'c')

            # draw coastlines, country boundaries, fill continents.
            m.drawcoastlines(linewidth=0.5, color = 'grey')
            m.drawcountries(linewidth=0.5, color = 'grey')
            
            # Fill continents with acolor
            #map.fillcontinents(color='coral',lake_color='aqua')

            # draw the edge of the map projection region (the projection limb)
            #map.drawmapboundary(fill_color='aqua')

            # draw latitude grid lines every 30 degrees.
            parallels = np.arange(-90, 91, 30)
            #             left, rigth,   top, botton
            labels    = [True, False, False,  False]
            m.drawparallels(parallels, labels=labels, linewidth=0.25)

            # draw longitude grid lines every 30 degrees.
            meridians = np.arange(0, 360, 30)
            #             left, rigth,   top, botton
            labels    = [False, False, False, True]
            m.drawmeridians(meridians, labels=labels, linewidth=0.25)

            # Get lat/lon positions for all 
            lon = __tmp[:, 1]
            lon1 = lon.copy()
            for n, l in enumerate(lon1):
               if l >= 180:
                  lon1[n]=lon1[n]-360. 
            lon = lon1
            lat = __tmp[:, 0]

            wp = None
            if WhatPlot is not None:
                wp = WhatPlot.lower()
            
            lons, lats = m(lon,lat)
            vals= __tmp[:,5]
            legend="None flag"
            if   (wp == 'pbqc'):
              i=0
              lons=[]
              lats=[]
              vals=[]
              while (i != len(__tmp[:,5])):
                if (__tmp[i,5]>=4):
                  if(__tmp[i,2]>=Nmin and __tmp[i,2]<=Nmax):
                    vals.append(__tmp[i,5])
                    lons.append(lon[i])
                    lats.append(lat[i])
                i=i+1
                lista=()#recebendo o dado do pbqc
                legend = 'pbqc flag'
            elif (wp == 'iuse'):
                val    = __tmp[:,6]
                vals   = val
                legend = 'iuse flag'
            elif (wp == 'use'):
                val    = __tmp[:,7]
                vals   = val
                legend = 'use flag'
            elif (wp == 'robs'):
                val    = __tmp[:,8]
                vals   = val
                legend = VarName.upper() + ' (observation)'
            elif (wp == 'diff'):
                val    = __tmp[:,9]
                vals   = val
                legend = VarName.upper() + ' (omf or oma)'
            elif (wp == 'rmod'):
                val    = __tmp[:,10]
                vals   = val
                legend = VarName.upper() + ' (model)'
            elif (wp == None):
                val    = __tmp[:,9]
                vals   = val
                legend = VarName.upper() + ' (omf or oma)'
                

            # Save a nice dark grey as a variable
            almost_black = '#262626'
            cm = plt.cm.get_cmap('jet')#'RdYlBu')
            geomap = plt.scatter(lons, lats, c=vals, cmap=cm, s=15, edgecolor=almost_black, linewidth=0.15)
            cbar = plt.colorbar(mappable = geomap, ax = ax, shrink=0.5)   # Mappable 'maps' the values of s to an array of RGB colors defined by a color palette
            cbar.set_label(legend)
            if (title != None ):
               plt.title('Data: '+str(Data)+' |'+' Convencionais | Filtro:'+WhatPlot)
               plt.savefig(WhatPlot+str(Data)+'.png')
               
            plt.show()
            
#
#

    def ptmap(self, VarName, kx):
        
        """
        Plots a spatial distribution of a desired variable and type.

        Usage: ptmap(VarName, kx)
        """

        from gsidiag import dataSources as Ds

        try:
           from mpl_toolkits.basemap import Basemap
        except ImportError:
           print('plese install basemap package') #pass # module doesn't exist, deal with it.

        import matplotlib.pyplot as plt	    
        import matplotlib.patches as mpatches

        fig = plt.figure(figsize=(6, 5), edgecolor='w')
        #map_land = '#ececec'
        map_land = 'white'
        map_land_lines = 'darkgray'
        map_oceans = 'white'
        m = Basemap(llcrnrlon=-180, urcrnrlon=180, llcrnrlat=-90, urcrnrlat=90, projection='mill', resolution='c')
        m.drawcoastlines(linewidth=0.5, color=map_land_lines)
        m.drawmapboundary(fill_color=map_oceans)
        m.fillcontinents(color=map_land, lake_color=map_oceans)
        m.drawparallels(np.arange(-90., 120., 30.), labels=[1, 0, 0, 0], linewidth=0, fontsize=9)
        m.drawmeridians(np.arange(-180., 180., 60.), labels=[0, 0, 0, 1], linewidth=0, fontsize=9)

        legend_labels = []
        legNCols = 3
        legXMargin = 1.05
        sCol_3 = 0

        for ivar in kx:
            __tmp = self.GTable(VarName, ivar)
            if not __tmp is None:
                plon = [(x - 360) if (x > 180) else x for x in __tmp[:, 1][:]]
                plat = __tmp[:, 0]
                xpt, ypt = m(plon, plat)
                m.plot(xpt, ypt, str(Ds.getVarInfo(int(ivar), VarName, 'symbol')), alpha=0.5, markersize=2, linewidth=1, color=Ds.getVarInfo(int(ivar), VarName, 'color'))
                legend_labels.append(mpatches.Patch(color=Ds.getVarInfo(int(ivar), VarName, 'color'), label=VarName + '-' + str(ivar) + ' | ' + Ds.getVarInfo(int(ivar), VarName, 'instrument')))
                if len(Ds.getVarInfo(int(ivar), VarName, 'instrument')) > 15 and len(Ds.getVarInfo(int(lista), VarName, 'instrument')) <= 30 and sCol_3 == 0:
                    legNCols = 2
                    legXMargin = 1.0
                if len(Ds.getVarInfo(int(ivar), VarName, 'instrument')) > 30:
                    legNCols = 1
                    legXMargin = 0.9
                    sCol_3 += 1

        plt.tight_layout()
        plt.subplots_adjust(left=None, bottom=0.20, right=None, top=0.90, wspace=None, hspace=None)

        # plt.legend(handles=legend_labels, numpoints=1, bbox_to_anchor=(0.0, -0.14), fancybox=False, shadow=False, frameon=False, ncol=legNCols, prop={"size": 9})
        plt.legend(handles=legend_labels, numpoints=1, loc='right center', bbox_to_anchor=(legXMargin, -0.05), fancybox=False, shadow=False, frameon=False, ncol=legNCols, prop={"size": 9})
        # plt.legend(handles=legend_labels, numpoints=1, loc='lower center', bbox_to_anchor=(0.5, -0.35), fancybox=False, shadow=False, frameon=False, ncol=2, prop={"size": 9})
        plt.subplots_adjust(left=0.02, bottom=0.24, right=1.00, top=0.93, wspace=None, hspace=None)
        plt.title('Distribuição das fontes de dados consideradas na assimilação', fontsize='10')
        plt.show()
#
#

    def ptmap(self, VarName, kx):

        """
        Plots a spatial distribution of a desired variable and type.

        Usage: ptmap(VarName, kx)
        """

        from gsidiag import dataSources as Ds
        from mpl_toolkits.basemap import Basemap
        import matplotlib.pyplot as plt	    
        import matplotlib.patches as mpatches

        fig = plt.figure(figsize=(6, 5), edgecolor='w')
        #map_land = '#ececec'
        map_land = 'white'
        map_land_lines = 'darkgray'
        map_oceans = 'white'
        m = Basemap(llcrnrlon=-180, urcrnrlon=180, llcrnrlat=-90, urcrnrlat=90, projection='mill', resolution='c')
        m.drawcoastlines(linewidth=0.5, color=map_land_lines)
        m.drawmapboundary(fill_color=map_oceans)
        m.fillcontinents(color=map_land, lake_color=map_oceans)
        m.drawparallels(np.arange(-90., 120., 30.), labels=[1, 0, 0, 0], linewidth=0, fontsize=9)
        m.drawmeridians(np.arange(-180., 180., 60.), labels=[0, 0, 0, 1], linewidth=0, fontsize=9)

        legend_labels = []
        legNCols = 3
        legXMargin = 1.05
        sCol_3 = 0

        for ivar in kx:
            __tmp = self.GTable(VarName, ivar)
            if not __tmp is None:
                plon = [(x - 360) if (x > 180) else x for x in __tmp[:, 1][:]]
                plat = __tmp[:, 0]
                xpt, ypt = m(plon, plat)
                m.plot(xpt, ypt, str(Ds.getVarInfo(int(ivar), VarName, 'symbol')), alpha=0.5, markersize=2, linewidth=1, color=Ds.getVarInfo(int(ivar), VarName, 'color'))
                legend_labels.append(mpatches.Patch(color=Ds.getVarInfo(int(ivar), VarName, 'color'), label=VarName + '-' + str(ivar) + ' | ' + Ds.getVarInfo(int(ivar), VarName, 'instrument')))
                if len(Ds.getVarInfo(int(ivar), VarName, 'instrument')) > 15 and len(Ds.getVarInfo(int(ivar), VarName, 'instrument')) <= 30 and sCol_3 == 0:
                    legNCols = 2
                    legXMargin = 1.0
                if len(Ds.getVarInfo(int(ivar), VarName, 'instrument')) > 30:
                    legNCols = 1
                    legXMargin = 0.9
                    sCol_3 += 1

        plt.tight_layout()
        plt.subplots_adjust(left=None, bottom=0.20, right=None, top=0.90, wspace=None, hspace=None)

        # plt.legend(handles=legend_labels, numpoints=1, bbox_to_anchor=(0.0, -0.14), fancybox=False, shadow=False, frameon=False, ncol=legNCols, prop={"size": 9})
        plt.legend(handles=legend_labels, numpoints=1, loc='right center', bbox_to_anchor=(legXMargin, -0.05), fancybox=False, shadow=False, frameon=False, ncol=legNCols, prop={"size": 9})
        # plt.legend(handles=legend_labels, numpoints=1, loc='lower center', bbox_to_anchor=(0.5, -0.35), fancybox=False, shadow=False, frameon=False, ncol=2, prop={"size": 9})
        plt.subplots_adjust(left=0.02, bottom=0.24, right=1.00, top=0.93, wspace=None, hspace=None)
        plt.title('Distribuição das fontes de dados consideradas na assimilação', fontsize='10')
        plt.show()

        #
        #

    def pvmap(self, VarName, use=None):

        """
        Plots a spatial distribution of a desired variable with specified attributes.

        Usage: pvmap(VarName, use=None)
        """

        from gsidiag import dataSources as Ds
        from mpl_toolkits.basemap import Basemap
        import matplotlib.pyplot as plt	    
        import matplotlib.patches as mpatches

        if len(use) == 1:
            fig = plt.figure(figsize=(6, 4), edgecolor='w')
        else:
            fig = plt.figure(figsize=(5, 6.5), edgecolor='w')

        #map_land = '#ececec'
        map_land = 'white'
        map_land_lines = 'darkgray'
        map_oceans = 'white'

        for n, idxuse in enumerate(use):

            if idxuse == 1:  data_status = 'Utilizado'
            if idxuse == -1: data_status = 'Monitorado'

            plt.subplot(len(use), 1, (n+1))
            plt.title('Variáveis consideradas na assimilação (' + data_status + ')', fontsize='10')
            m = Basemap(llcrnrlon=-180, urcrnrlon=180, llcrnrlat=-90, urcrnrlat=90, projection='mill', resolution='c')
            m.drawcoastlines(linewidth=0.5, color=map_land_lines)
            m.drawmapboundary(fill_color=map_oceans)
            m.fillcontinents(color=map_land, lake_color=map_oceans)
            m.drawparallels(np.arange(-90., 120., 30.), labels=[1, 0, 0, 0], linewidth=0, fontsize=9)
            m.drawmeridians(np.arange(-180., 180., 60.), labels=[0, 0, 0, 1], linewidth=0, fontsize=9)

            __tmp_obsinfo = self.ObsInfo

            colors_palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']
            setColor = 0
            legend_labels = []
            for xvar in VarName:
                for xtype in __tmp_obsinfo[xvar][:, 0]:
                    __tmp = self.GTable(xvar, xtype)
                    if not __tmp is None:
                        plon_1 = __tmp[:, 1][__tmp[:, 6].astype(int) == int(idxuse)]
                        plon   = [(x - 360) if (x > 180) else x for x in plon_1]
                        plat   = __tmp[:, 0][__tmp[:, 6].astype(int) == int(idxuse)]
                        del plon_1

                        xpt, ypt = m(plon, plat)
                        m.plot(xpt, ypt, 's', alpha=1.0, markersize=1, markerfacecolor="None", color=colors_palette[setColor])

                legend_labels.append(mpatches.Patch(color=colors_palette[setColor], label=xvar))
                plt.legend(handles=legend_labels, numpoints=1, loc='left center', bbox_to_anchor=(1, 0.9), fancybox=False, shadow=False, frameon=False, ncol=1, prop={"size": 10})
                setColor += 1

        plt.tight_layout()

        if len(use) == 1:
            plt.subplots_adjust(left=0.07, bottom=0.05, right=0.87, top=0.94, wspace=None, hspace=None)
        else:
            plt.subplots_adjust(left=0.0, bottom=0.04, right=0.95, top=0.94, wspace=None, hspace=0.22)
        plt.show()
        return

#EOC
#-----------------------------------------------------------------------------#
