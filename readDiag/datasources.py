
''' Python Markers List
        "."	point
        ","	pixel
        "o"	circle
        "v"	triangle_down
        "^"	triangle_up
        "<"	triangle_left
        ">"	triangle_right
        "1"	tri_down
        "2"	tri_up
        "3"	tri_left
        "4"	tri_right
        "8"	octagon
        "s"	square
        "p"	pentagon
        "P"	plus (filled)
        "*"	star
        "h"	hexagon1
        "H"	hexagon2
        "+"	plus
        "x"	x
        "X"	x (filled)
        "D"	diamond
        "d"	thin_diamond
        "|"	vline
        "_"	hline


"#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c", "#98df8a", "#d62728", "#ff9896", "#9467bd", "#c5b0d5", 
"#8c564b", "#c49c94", "#e377c2", "#f7b6d2", "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5", 
"#393b79", "#5254a3", "#6b6ecf", "#9c9ede", "#637939", "#8ca252", "#b5cf6b", "#cedb9c", "#8c6d31", "#bd9e39", 
"#e7ba52", "#e7cb94", "#843c39", "#ad494a", "#d6616b", "#e7969c", "#7b4173", "#a55194", "#ce6dbd", "#de9ed6", 

['ps', 't', 'q', 'uv', 'gps', 'pw']
'''

def getVarInfo(dtype, var, feature):

    dataSources = {
          1: [120, 'ps', 'ADPUPA', 'Radiossonde', '#1f77b4', 's', 1],
          2: [120, 'q',  'ADPUPA', 'Radiossonde', '#aec7e8', '*', 1],
          3: [120, 't',  'ADPUPA', 'Radiossonde', '#ff7f0e', '*', 1],

          4: [130, 't',  'AIRCFT', 'AIREP PIREP Air Plane Sensors', '#ffbb78', '*', 1],
          5: [130, 'q',  'AIRCFT', 'AIREP PIREP Air Plane Sensors', '#2ca02c', '*', -1],
          6: [230, 'uv', 'AIRCFT', 'AIREP PIREP Air Plane Sensors', '#98df8a', '*', 1],

          7: [153, 'pw','GPSIPW', 'GPS receptor', '#d62728', 's', -1],

          8: [180, 'ps', 'SFCSHP', 'Boias e sensor navios', '#ff9896', 's', 1],
          9: [180, 't',  'SFCSHP', 'Boias e sensor navios', '#9467bd', '*', 1],
         10: [180, 'q',  'SFCSHP', 'Boias e sensor navios', '#c5b0d5', '*', 1],
         11: [182, 'ps', 'SFCSHP', 'Boias e sensor navios', '#8c564b', 's', 1],
         12: [182, 't',  'SFCSHP', 'Boias e sensor navios', '#c49c94', '*', 1],
         13: [182, 'q',  'SFCSHP', 'Boias e sensor navios', '#e377c2', '*', 1],
         14: [280, 'uv', 'SFCSHP', 'Boias e sensor navios', '#f7b6d2', '*', 1],
         15: [282, 'uv', 'SFCSHP', 'Boias e sensor navios', '#7f7f7f', '*', 1],

         16: [181, 'ps', 'ADPSFC', 'Estação a superfície com pressão', '#c7c7c7', 's', 1],
         17: [181, 'sst','ADPSFC', 'Estação a superfície com pressão', '#bcbd22', '*', 1],
         18: [181, 't',  'ADPSFC', 'Estação a superfície com pressão', '#dbdb8d', '*', 1],
         19: [181, 'q',  'ADPSFC', 'Estação a superfície com pressão', '#17becf', '*', -1],
         20: [187, 'ps', 'ADPSFC', 'Estação a superfície com pressão', '#9edae5', 's', 1],
         21: [187, 't',  'ADPSFC', 'Estação a superfície com pressão', '#393b79', '*', -1],
         22: [187, 'q',  'ADPSFC', 'Estação a superfície com pressão', '#e7ba52', '*', -1],
         23: [281, 'uv', 'ADPSFC', 'Estação a superfície com pressão', '#5254a3', '*', -1],

         24: [183, 'ps', 'ADPSFC', 'Boias a estações sem pressão', '#e7cb94', 's', -1],
         25: [183, 'sst','ADPSFC', 'Boias a estações sem pressão', '#6b6ecf', '*', -1],
         26: [183, 't',  'ADPSFC', 'Boias a estações sem pressão', '#843c39', '*', -1],
         27: [183, 'q',  'ADPSFC', 'Boias a estações sem pressão', '#9c9ede', '*', -1],
         28: [284, 'uv', 'ADPSFC ADPSHP', 'Boiasnumber a estações sem pressão', '#ad494a', '*', -1],
         29: [287, 'uv', 'ADPSFC', 'Boias a estações sem pressão', '#637939', '*', -1],

         30: [223, 'uv', 'PROFLR', 'NOAA Profiler Network', '#d6616b', 's', 1],
         31: [224, 'uv', 'VADWND', 'NEXRAD (VAD)', '#8ca252', 'x', 1],
         32: [126, 't',  'RASSDA', 'RASSDA Profiler', '#e7969c', 's', -1],
         33: [228, 'uv', 'PROFLR', 'JMA Wind Profiler', '#378ef4', '*', -1],
         34: [229, 'uv', 'PROFLR', 'Profiler from Pilot Bulletins', '#7b4173', 's', 1],

         35: [220, 'uv', 'ADPUPA', 'Dropsonde', '#cedb9c', '*', 1],
         36: [220, 'ps', 'ADPUPA', 'Dropsonde', '#a55194', 's', -1],
         37: [250, 'uv',  'SATWND', 'JMA Vapor Todos Niveis Top e Deep HIMAWARI', '#e49d12', 'o', 1],
         38: [250, 'q',  'ADPUPA', 'Dropsonde', '#8c6d31', 'x', 1],
         39: [280, 't', 'ADPUPA', 'Dropsonde', '#ce6dbd', 'p', 1],
         40: [232, 'uv', 'ADPUPA', 'Dropsonde', '#bd9e39', 'P', 1],

         41: [253, 'uv', 'SATWND', 'EUMETSAT IR e VIS abaixo de 850', '#d6616b', '8', -1],
         42: [254, 'uv', 'SATWND', 'EUMETSAT IR e VIS abaixo de 850', '#bcbd22', 's', -1],
         43: [257, 'uv', 'SATWND', 'MODIS IR Todos Niveis (AQUA/TERRA)', '#dbdb8d', '*', -1],
         44: [259, 'uv', 'SATWND', 'MODIS VAPOR Todos Niveis DEEP (AQUA/TERRA)', '#17becf', 'o', -1],
         45: [258, 'uv', 'SATWND', 'MODIS VAPOR Todos Niveis TOP (AQUA/TERRA)', '#9edae5', 'p', -1],
         46: [243, 'uv', 'SATWND', 'EUMETSAT IR e VIS abaixo de 850', '#393b79', 'P', -1],
         47: [290, 'uv', 'ASCATW', 'Non-superobed Scatterometer Winds Over Ocean (ASCAT)', '#e7ba52', 'x', -1],
         48: [221, 'uv', 'ADPUPA', 'PIBAL', '#e7cb94', 'X', -1],
         49: [252, 'uv', 'SATWND', 'JMA IR e VIS abaixo de 850 Himawari', '#6b6ecf', '8', -1],
         50: [242, 'uv', 'SATWND', 'JMA IR e VIS Drift abaixo 850 (GMS,MTSAT,HIMAWARI)', '#843c39', 's', -1],
         51: [245, 'uv', 'SATWND', 'NESDID IR Todos Niveis (GOES)', '#9c9ede', '*', -1],
         52: [246, 'uv', 'SATWND', 'NESDID Canal vapor todos niveis top nuvem (GOES)', '#ad494a', 'o', -1],
         53: [247, 'uv', 'SATWND', 'NESDID Canal vapor todos niveis DEEP Layer(GOES)', '#637939', 'p', -1],
         54: [251, 'uv', 'SATWND', 'NESDID VIS todos niveis GOES', '#d6616b', 'x', -1],

         55: [  3, 'gps', 'GPS', 'GPS-INFO', '#297df1', '8', -1],
         56: [  4, 'gps', 'GPS', 'GPS-INFO', '#fe6f22', 's', -1],
         57: [740, 'gps', 'GPS', 'GPS-INFO', '#42b7a3', '*', -1],
         58: [745, 'gps', 'GPS', 'GPS-INFO', '#de57fb', 'o', -1],
         59: [744, 'gps', 'GPS', 'GPS-INFO', '#f1d34d', 'p', -1],
         60: [741, 'gps', 'GPS', 'GPS-INFO', '#d61d14', 'P', -1],
         61: [722, 'gps', 'GPS', 'GPS-INFO', '#2e8e24', 'x', -1]
	}

    varInfo = [dataSources[i] for i in dataSources if dataSources[i][0] == dtype if dataSources[i][1] == str(var)]

    if feature == 'number':       info = varInfo[0][0]
    if feature == 'var':          info = varInfo[0][1]
    if feature == 'abbreviation': info = varInfo[0][2]
    if feature == 'instrument':   info = varInfo[0][3]
    if feature == 'color':        info = varInfo[0][4]
    if feature == 'symbol':       info = varInfo[0][5]
    if feature == 'iuse':         info = varInfo[0][6]

    return info



