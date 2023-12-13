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
# 24 Apr 2018 - J. G. de Mattos - Initial Version
#
# !REMARKS:
#
#EOP
#-----------------------------------------------------------------------------#
#BOC

import csv
from os import path

def getVarInfo(kx,var,feature):
    
    dataInfo = dataSourcesInfo()

    #
    # verify if request exist
    #
    if kx in dataInfo.tab:
        if var in dataInfo.tab[kx]:
            if feature in dataInfo.tab[kx][var]:
                return dataInfo.tab[kx][var][feature]
            else:
                print('Invalid Feature request:',feature)
                print('try use:')
                for item in dataInfo.tab[kx][var]:
                    print('\t*',item)
        else:
            print('Variable',var,'doesn\'t exist in kx',kx)
            print('try use:')
            for item in dataInfo.tab[kx]:
                print('\t*',item)
    else:
        print('Invalid kx request:', kx)
        print('try request:')
        for item in dataInfo.tab:
            print('\t*',item)


class dataSourcesInfo:

    def __init__(self):

        tableFile = path.join(path.dirname(__file__), 'table')
        
        with open(tableFile) as csv_data:
            reader = csv.reader(csv_data,skipinitialspace=True,delimiter=';')
            # eliminate blank rows if they exist
            rows = [row for row in reader if row]
#            rows.remove([''])
            headings = rows[0] # get headings
            self.tab = {}
            for row in rows[1:]:
                kx  = int(row[0])
                dic = {row[1]:dict(zip(headings[2::],row[2::]))}
                if kx in self.tab:
                    self.tab[kx].update(dic)
                else:
                    self.tab.update({kx:dic})



#EOC
#-----------------------------------------------------------------------------#

