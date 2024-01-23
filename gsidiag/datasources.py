import yaml
from os import path

class dataSourcesInfo:
    """
    A class to parse and store information from a YAML file containing observations data.

    Attributes:
        tab (dict): A dictionary to store the parsed observations data.
    """
    def __init__(self):
        """
        The constructor for dataSourcesInfo class. Reads from a YAML file and initializes the 'tab' attribute.
        """
        yaml_file = path.join(path.dirname(__file__), 'table.yml')

        with open(yaml_file, 'r') as file:
            self.data = yaml.safe_load(file)

        self.tab = {}
        for observation in self.data['observations']:
            kx = int(observation['kx'])
            self.tab[kx] = {}
            for detail in observation['details']:
                var = detail['var']
                self.tab[kx][var] = detail


def getVarInfo(kx, var, feature):
    """
    Retrieves information for a specified feature based on the kx and variable.

    Args:
        kx (int): The kx value to look up.
        var (str): The variable to look up.
        feature (str): The specific feature to retrieve information about.

    Returns:
        The value of the requested feature if found, otherwise None.
    """
    dataInfo = dataSourcesInfo()

    # verify if request exists
    if kx in dataInfo.tab:
        if var in dataInfo.tab[kx]:
            if feature in dataInfo.tab[kx][var]:
                return dataInfo.tab[kx][var][feature]
            else:
                print('Invalid Feature request:', feature)
                print('Try using one of:')
                for item in dataInfo.tab[kx][var]:
                    print('\t*', item)
        else:
            print('Variable', var, 'doesn\'t exist in kx', kx)
            print('Try using one of:')
            for item in dataInfo.tab[kx]:
                print('\t*', item)
    else:
        print('Invalid kx request:', kx)
        print('Try using one of:')
        for item in dataInfo.tab:
            print('\t*', item)

