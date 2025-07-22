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
# 05 dez 2023 - J. G. de Mattos - Initial Version
#
# !REMARKS:
#
#EOP
#-----------------------------------------------------------------------------#
#BOC
import os
import numpy as np
import pandas as pd
import struct
from datetime import datetime

class diagAccess():

    """
    A class to handle reading and processing observation data from binary files.

    This class can read conventional observation data as well as satellite observation data.
    It interprets binary file content and structures the data into a readable format.

    Attributes:
        data (dict): A dictionary containing the processed data from the file.

    Examples:
        >>> diag = diagAccess('conventional_observation_diag_file')
        >>> print(diag.data)

        >>> diag = diagAccess('satellite_observation_diag_file')
        >>> print(diag.data)
    """
    
    #@profile
    def __init__(self, file_name):
        """
        Initializes the diagAccess class by determining the file type and reading the data accordingly.

        Args:
            file_name (str): The name of the file to be read.

        Raises:
            ValueError: If the file format is unsupported or cannot be processed.
            IOError: If there's an issue reading the file.

        Examples:
            >>> diag = diagAccess('diag_file')
        """

        self.udef = -1.0e15
        self.rtiny = 10 * np.finfo(float).tiny
        
        self._data_type = None
        self._data_frame = None

        try:
            with open(file_name, 'rb') as file:
                # Read the first 4 bytes of the file
                header = file.read(4)

                # Interpret the 4 bytes as a big-endian value
                value = struct.unpack('>I', header)[0]
        
                # Check the value and read data accordingly
                if value == 4:
                    self._data_type  = 1
                    self._data_frame = self._readConv(file_name)
                elif value >= 88:
                    self._data_type  = 2
                    self._data_frame = self._readRad(file_name)
                else:
                    raise ValueError("Unsupported file format or invalid header value.")

        except FileNotFoundError:
            raise FileNotFoundError(f"File '{file_name}' not found.")
        except (ValueError, IndexError) as e:
            raise ValueError(f"Error processing file '{file_name}': {e}")
        except Exception as e:
            # It might be useful to log the full exception or take other actions
            raise RuntimeError(f"An unexpected error occurred: {e}")

    #@profile
    def get_date(self):
        """
        Retrieves the date associated with the diagnostic data.
    
        This method returns the date extracted from the diagnostic file. The date is read as part of the file's
        header and converted to a datetime object representing the date and time of the observation or data recording.
    
        The date is expected to be in the format YYYYMMDDHH, where YYYY is the year, MM is the month, DD is the day,
        and HH is the hour. The method ensures this format is correctly interpreted to return an accurate datetime object.
    
        Returns:
            datetime.datetime: A datetime object representing the date and time extracted from the file. 
            This object is timezone-naive and should be interpreted as UTC unless otherwise specified in the file format.
    
        Raises:
            ValueError: If the date format in the file is incorrect or cannot be converted to a datetime object.
    
        Examples:
            >>> diag = diagAccess('example_diag_file.bin')
            >>> observation_date = diag.get_date()
            >>> print(observation_date)
            2020-01-01 00:00:00
        """
        if hasattr(self, '_idate') and self._idate:
            return self._idate
        else:
            raise AttributeError("File has not been read or date was not properly initialized.")

    #@profile
    def get_data_type(self):
        """
        Retrieves the type of data processed from the diagnostic file.

        This method returns the type of data that was read and processed from the diagnostic file. It's an 
        important method to understand the nature of the data being handled. The type is determined during the 
        initial file reading process based on specific criteria in the file's header.

        The data type can be either 'Conventional' or 'Radiance', which corresponds to different formats and 
        structures of diagnostic data. This information is crucial for downstream processing and analysis.

        Returns:
            int: An integer representing the type of data read. 
                 1 represents 'Conventional' data, and 2 represents 'Radiance' data.

        Raises:
            AttributeError: If the data type has not been set (i.e., if no file has been read yet).

        Examples:
            >>> diag = diagAccess('diag_file')
            >>> data_type = diag.get_data_type()
            >>> print(data_type)
        """
        if hasattr(self, '_data_type'):
            return self._data_type
        else:
            raise AttributeError("Data type has not been set. Please ensure a file has been read.")

    #@profile
    def get_data_frame(self):
        """
        Retrieves the DataFrame containing the processed diagnostic data.

        This method returns the DataFrame that holds the data processed from the diagnostic file. This DataFrame 
        is structured based on the specific format of the diagnostic data and includes all the relevant information 
        extracted from the file.

        It's important to note that the DataFrame is only available after successfully reading and processing a 
        diagnostic file. The DataFrame's structure and content will vary depending on the type of data (either 
        'Conventional' or 'Radiance').

        Returns:
            pandas.DataFrame: A DataFrame containing the processed diagnostic data. The structure and content 
                              of this DataFrame depend on the type of diagnostic data read from the file.

        Raises:
            AttributeError: If the DataFrame has not been set (i.e., if no file has been read or if an error 
                            occurred during file processing).

        Examples:
            >>> diag = diagAccess('diag_file')
            >>> data_frame = diag.get_data_frame()
            >>> print(data_frame)
        """
        if hasattr(self, '_data_frame') and self._data_frame is not None:
            return self._data_frame
        else:
            raise AttributeError("Data frame has not been set or initialized. Please ensure a file has been read and processed correctly.")
        
    #@profile
    def _read_conv_header(self, lu):
        """
        Reads the header from a binary conventional diagnostic file and 
        extracts relevant information.

        Args:
            lu (file object): An open file object for binary reading.

        Returns:
            tuple: A tuple containing the number of observations (nobs), 
                   the number of information per observation (ninfo), 
                   and the variable (var), or None if the end of the file is reached.

        Raises:
            EOFError: If an end-of-file error occurs.

        Examples:
            # This is an internal method, so no direct usage example.
        """

        header_dtype = [
            ('head', '>i4'), ('var', 'S3'), ('nchar', '>i4'),
            ('ninfo', '>i4'), ('nobs', '>i4'), ('mype', '>i4'),
            ('tail', '>i4'), ('tail2', '>i4')
        ]
        header = np.fromfile(lu, dtype=header_dtype, count=1)
        if len(header) == 0:
            return None  # Indica o fim do arquivo
        nobs = header['nobs'][0]
        ninfo = header['ninfo'][0]
        var = header['var'][0].decode('utf-8').strip()
        return nobs, ninfo, var
    
    #@profile
    def _read_conv_diag_data(self, lu, nobs, ninfo):
        """
        Reads the diagnostic data from the binary file.

        Args:
            lu (file object): An open file object for binary reading.
            nobs (int): Number of observations.
            ninfo (int): Number of information fields per observation.

        Returns:
            numpy.ndarray: A structured array containing the diagnostic data.

        Examples:
            # This is an internal method, so no direct usage example.
        """
      
        diagbuf_dtype = np.dtype([
            ('extrabytes_head', '>i4'),
            ('cdiagbuf', ('>S8', (nobs,))),
            ('rdiagbuf', ('>f4', (nobs, ninfo,))),
            ('extrabytes_tail', '>i4'),
        ])
        data = np.fromfile(lu, dtype=diagbuf_dtype, count=1)
        data = data.byteswap().newbyteorder()
        return data
    
    #@profile
    def _process_conv_data(self, data, var, nobs, ninfo, data_dict):
        """
        Processes the read data from the file and updates the data dictionary.

        Args:
            data (numpy.ndarray): Structured array containing the read data.
            var (str): Name of the variable.
            nobs (int): Number of observations.
            ninfo (int): Number of information fields per observation.
            data_dict (dict): Dictionary to store the processed data.

        Examples:
            # This is an internal method, so no direct usage example.
        """
        
        reshaped_rdiagbuf = data['rdiagbuf'].reshape(nobs,ninfo)
        kx_values = np.rint(reshaped_rdiagbuf[:, 0]).astype(int)
        for kx_value in np.unique(kx_values):
            idx = kx_values == kx_value
            selected_rows = reshaped_rdiagbuf[idx, :]
            #column_names = self._get_columns(var,ninfo)
            #selected_diagbuf = pd.DataFrame(selected_rows[:, 1:], columns=column_names)
            selected_diagbuf = pd.DataFrame(selected_rows[:, 1:])
            selected_diagbuf = self._process_rdiagbuf(selected_diagbuf, selected_rows[:, 1:], var, ninfo)
            # Check if 'var' is a key in 'data_dict'
            if var not in data_dict:
                data_dict[var] = {}
            # Check if 'kx_value' is a key in the dictionary referenced by 'data_dict[var]'
            if kx_value in data_dict[var]:
                # Concatenate if 'kx_value' is already present
                data_dict[var][kx_value] = pd.concat([data_dict[var][kx_value], selected_diagbuf], ignore_index=True)
            else:
                # Initialize 'data_dict[var][kx_value]' with 'selected_diagbuf' if 'kx_value' is not a key
                data_dict[var][kx_value] = selected_diagbuf


    @staticmethod
    def _get_base_columns():
        # Base columns
        return ['ks', 'lat', 'lon', 'elev', 'prs', 'dhgt', 'time', 
                'pbqc', 'emark', 'iusev', 'iuse', 'wpbqc', 'inp_err', 
                'adj_err', 'end_err', 'robs']

    #@profile
    def _get_columns(self, var, ninfo):
        """
        Returns a list of columns based on the value of 'var' and a condition
        based on 'ninfo'.

        For most data types, a specific set of associated columns are appended
        to a base set of columns. For 'uv', the last base column ('robs') is removed. 
        For 'gps', a unique and specific column list is returned. For 'sst', columns 
        'tref', 'dtw', 'dtc', 'tz' are included only if 'ninfo' is greater than or equal to 21.

        Args:
            var (str): A string indicating the desired data type. Can be
                       'q', 't', 'sst', 'uv', 'ps', or 'gps'.
            ninfo (int): An integer value used in conditional logic for 
                         including extra columns in the 'sst' case.

        Returns:
            list: A list of strings, where each string is a column name.
                  The list of columns depends on the value of 'var'.
        """

        base_columns = self._get_base_columns()

        # Mapping of var to specific columns
        specific_columns_map = {
            'q': ['omf', 'omf_wob', 'qsges'],
            't': ['omf', 'omf_wob'],
            'sst': ['omf'],
            'uv': ['robs_u', 'omf_u', 'omf_wob_u', 'robs_v', 'omf_v', 'omf_wob_v', 'factw'],
            'ps': ['omf', 'omf_wob'],
            'gps': ['inc_ba', 'imp_height', 'zsges', 'trefges', 'hob', 'gps_ref', 'qrefges']
        }

        # Include extra columns for 'sst' based on 'ninfo'
        if var == 'sst' and ninfo >= 21:
            specific_columns_map['sst'] = ['tref', 'dtw', 'dtc', 'tz']

        # Include extra columns for 't' based on 'ninfo'
        if var == 'sst' and ninfo >= 20:
            specific_columns_map['t'] = ['pof', 'wvv']

        # Special handling for 'gps'
        if var == 'gps':
            return ['ks', 'lat', 'lon', 'inc_ba', 'prs', 'imp_height', 'time', 
                    'zsges', 'pbqc', 'iusev', 'iuse', 'wpbqc', 'inp_err', 'adj_err',
                    'end_err', 'robs', 'trefges', 'hob', 'gps_ref', 'qrefges']

        # Get the specific columns for 'var'
        specific_columns = specific_columns_map.get(var, [])

        # For the case 'uv', remove 'robs' from base columns
        if var == 'uv':
            return base_columns[:-1] + specific_columns

        # For other cases, simply add the specific columns to the base
        return base_columns + specific_columns

    #@profile
    def _process_rdiagbuf(self, conv, rdiagbuf, var, ninfo):

        desired_order = self._get_base_columns()
        columns       = self._get_columns(var, ninfo)
        # Filtra a lista desejada para manter apenas as colunas que estão em df
        filtered_order = [col for col in desired_order if col in columns]
        # Adiciona as colunas que estão no df original mas não estão na lista desejada
        extra_cols = [col for col in columns if col not in filtered_order]
        # define nova ordem das colunas 
        new_order = filtered_order + extra_cols


        # Aplicar ajustes específicos de 'var'
        if var == 'gps':
            conv.iloc[:,columns.index('pbqc')] = rdiagbuf[:,9]
            conv[len(conv.columns)]  = rdiagbuf[:,16] * rdiagbuf[:,4]
            columns += ['omf']
        elif var == 'q':
            for key in ['robs', 'omf', 'inp_err', 'adj_err', 'end_err']:
                conv.iloc[:,columns.index(key)] *= 1000.0

        conv.columns =  columns
        
        # Reordena o DataFrame
        conv = conv[new_order]

        return conv
        


    #@profile
    def _readConv(self, file_name):
        """
        Reads and processes conventional observation data from a binary file.

        This method structures the data into a dictionary, where each key represents a variable.

        Args:
            file_name (str): The name of the file to be read.

        Returns:
            dict: A dictionary where keys are variable names and values are DataFrames of the extracted data.

        Raises:
            Exception: If an error occurs while reading the file.

        Examples:
            >>> diag = diagAccess('conventional_observation_file.bin')
            >>> conv_data = diag._readConv('conventional_observation_file.bin')
            >>> print(conv_data)
        """

        data_dict = {}
        with open(file_name, 'rb') as lu:
            try:
                # Reading three integers from the file. Assuming 'lu' is an open file-like object.
                head, idate_int, tail = np.fromfile(lu, dtype='>i4', count=3)
            
                # Convert idate to a string
                idate_str = str(idate_int)
            
                # Check if the string is of the correct length (10 characters for YYYYMMDDHH)
                if len(idate_str) == 10:
                    # Convert the string to a datetime object
                    self._idate = datetime.strptime(idate_str, "%Y%m%d%H")
                else:
                    # If the length is incorrect, raise an error
                    raise ValueError("Incorrect format for idate")
            
            except EOFError:
                # Raising a more descriptive exception if reading from the file fails
                raise Exception('Error reading idate value.')
                
            while True:
                header_result = self._read_conv_header(lu)
                if header_result is None:
                    break  # Fim do arquivo

                nobs, ninfo, var = header_result
                if nobs > 0:
                    data = self._read_conv_diag_data(lu, nobs, ninfo)
                    self._process_conv_data(data, var, nobs, ninfo, data_dict)
                else:
                    _ = np.fromfile(lu, dtype='>f4', count=1)  # Leitura adicional se nobs for zero



        return data_dict



    def _readRad(self, file_name):
        """
        Reads and processes satellite observation data from a binary file.

        Args:
            file_name (str): The name of the file to be read.

        Returns:
            dict: A dictionary containing processed data, or None if an error occurs.

        Raises:
            FileNotFoundError: If the file does not exist.
            Exception: For any other errors encountered during processing.

        Examples:
            >>> diag = diagAccess('satellite_observation_file.bin')
            >>> rad_data = diag._readRad('satellite_observation_file.bin')
            >>> print(rad_data)
        """

        # Define the data types for the header and channel information
        self.header_info_dtype = np.dtype([
            (   'head',  '>i4'),
            (   'isis', '>S20'),
            (  'dplat', '>S10'),
            ('obstype', '>S10'),
            (  'jiter',  '>i4'),
            ( 'nchanl',  '>i4'),
            (  'npred',  '>i4'),
            (  'idate',  '>i4'),
            (  'ireal',  '>i4'),
            ( 'ipchan',  '>i4'),
            ( 'iextra',  '>i4'),
            ( 'jextra',  '>i4'),
            (  'extra', '>S20'),
            (   'tail',  '>i4')
        ])
    
        self.channel_info_dtype = np.dtype([
            (  'head', '>i4'),
            (  'freq', '>f4'),
            (   'pol', '>f4'),
            (  'wave', '>f4'),
            ( 'varch', '>f4'),
            (  'tlap', '>f4'),
            (  'iuse', '>i4'),
            ('nuchan', '>i4'),
            (   'ich', '>i4'),
            (  'tail', '>i4')
        ])
    
        self.header_diagbuf = [
            'lat', 'lon', 'elev',
            'time', 'iscanp', 'zasat',
            'ilazi', 'pangs', 'isazi',
            'sgagl', 'sfcwc', 'sfclc',
            'sfcic', 'sfcsc', 'sfcwt',
            'sfclt', 'sfcit', 'sfcst',
            'sfcstp', 'sfcsmc', 'sfcltp',
            'sfcvf', 'sfcsd', 'sfcws',
            'clsORclw', 'cldpORtpwc'
        ]
    
        self.header_diagbufchan = [
            'tb_obs', 'omf', 'omf_nbc',
            'errinv', 'idqc', 'emiss',
            'tlach', 'ts',
        ]

        print(file_name)
        try:
            with open(file_name, 'rb') as file:
                # Read and process header data
                header, file_size = self._read_header(file, file_name)
                channel_df = self._read_channel_info(file, header['nchanl'])
                diag_data = self._read_diagnostic_data(file, file_size, header)
                diagbuf_df, diagbufchan_df, diagbufex_df = self._extract_dataframes(diag_data, header)
    
            # Construct dictionary containing processed dataframes
            data_dict = {
                'obstype': header['obstype'],
                'dplat': header['dplat'],
                'dataframes': {
                    'channel_df': channel_df,
                    'diagbuf_df': diagbuf_df,
                    'diagbufchan_df': diagbufchan_df,
                    'diagbufex_df': diagbufex_df
                }
            }
    
            return data_dict
    
        except FileNotFoundError:
            print(f"File {file_name} does not exist. Skipping processing.")
            return None
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            return None

    def _read_header(self, file, file_name):
        """
        Reads and processes header information from a satellite observation binary file.

        Args:
            file (file object): An open file object for binary reading.
            file_name (str): Path to the binary file.

        Returns:
            tuple: Tuple containing header information and file size.

        Raises:
            Exception: If an error occurs while reading the header.

        Examples:
            # This is an internal method, so no direct usage example.
        """

        try:

            # Read header data
            header = np.fromfile(file, dtype=self.header_info_dtype, count=1)[0]
    
            # Extract header values
            dplat   = header['dplat']
            obstype = header['obstype']
            nchanl  = header['nchanl']
            iextra  = header['iextra']
            jextra  = header['jextra']
            npred   = header['npred']
            ireal   = header['ireal']
            ipchan  = header['ipchan']
            tail    = header['tail']
            head    = header['head']
    
            # Calculate record size
            record_size = (ireal * 4) + ((ipchan + npred + 2) * nchanl * 4) + (iextra * jextra * 4)

            # Read the file size
            file_size = os.path.getsize(file_name)
    
            # Obtain the size of the header that has already been read
            header_size = (np.dtype(self.header_info_dtype).itemsize - 8) + (np.dtype(self.channel_info_dtype).itemsize - 8) * nchanl
    
            file_size = file_size - header_size
        
            return header, file_size
        except Exception as e:
            print(f"Error reading header: {str(e)}")
            raise

    def _read_channel_info(self, file, nchanl):
        """
        Reads and processes channel information from a satellite observation binary file.

        Args:
            file (file object): An open file object for binary reading.
            nchanl (int): Number of channels.

        Returns:
            pd.DataFrame: DataFrame containing processed channel information.

        Raises:
            Exception: If an error occurs while reading channel information.

        Examples:
            # This is an internal method, so no direct usage example.
        """

        try:
            # Read channel information using NumPy
            channel_info = np.fromfile(file, dtype=self.channel_info_dtype, count=nchanl)
    
            # byteswap
            channel_info = channel_info.byteswap().newbyteorder()  # Leveraging NumPy's operations
    
            # Convert to DataFrame after reading, reducing unnecessary allocations
            channel_df = pd.DataFrame(channel_info).drop(['head', 'tail'], axis=1)

            return channel_df
        except Exception as e:
            print(f"Error reading channel info: {str(e)}")
            raise


    def _read_diagnostic_data(self, file, file_size, header):
        """
        Reads and processes diagnostic data from a satellite observation binary file.

        Args:
            file (file object): An open file object for binary reading.
            file_size (int): Size of the binary file.
            header (dict): Header information.

        Returns:
            np.ndarray: Numpy array containing processed diagnostic data.

        Raises:
            Exception: If an error occurs while reading diagnostic data.

        Examples:
            # This is an internal method, so no direct usage example.
        """

        try:
            diagbuf_dtype = np.dtype([
                ('extrabytes_head', np.void, 4),
                ('diagbuf', ('>f4', header['ireal'])),
                ('diagbufchan', ('>f4', (header['ipchan'] + header['npred'] + 2) * header['nchanl'])),
                ('diagbufex', ('>f4', header['jextra'])) if header['iextra'] > 0 else ('>f4', 0),
                ('extrabytes_tail', np.void, 4),
            ])
        
            record_size = np.dtype(diagbuf_dtype).itemsize
            num_records = (file_size - 4) // (record_size + 8)
            buffer_size = num_records * record_size
            buffer = file.read(buffer_size)
            diag_data = np.frombuffer(buffer, dtype=diagbuf_dtype).byteswap().newbyteorder()
            return diag_data
        except Exception as e:
            print(f"Error reading diagnostic data: {str(e)}")
            raise

    def _extract_dataframes(self, diag_data, header):
        """
        Extracts diagnostic data into DataFrames from a satellite observation binary file.

        Args:
            diag_data (np.ndarray): Numpy array containing diagnostic data.
            header (dict): Header information.

        Returns:
            tuple: Tuple containing DataFrames of diagbuf, diagbufchan, and diagbufex.

        Raises:
            Exception: If an error occurs while extracting dataframes.

        Examples:
            # This is an internal method, so no direct usage example.
        """
        
        try:
            diagbuf_df = pd.DataFrame(diag_data['diagbuf'][:, 0:len(self.header_diagbuf)], columns=self.header_diagbuf)

            # Acrescenta os preditores baseado em npred
            for i in range(1,  header['npred']+3):
                key = 'pred{}'.format(i)
                self.header_diagbufchan.append(key)

            diagbufchan_df = []
            for i in range(header['nchanl']):
                start_index = i * (header['ipchan'] + header['npred'] + 2)
                end_index   = (i + 1) * (header['ipchan'] + header['npred'] + 2)
                df_part     = pd.DataFrame(diag_data['diagbufchan'][:, start_index:end_index], columns=self.header_diagbufchan)
                diagbufchan_df.append(df_part)
        
            diagbufex_df = pd.DataFrame(diag_data['diagbufex'])
        
            return diagbuf_df, diagbufchan_df, diagbufex_df
        except Exception as e:
            print(f"Error extracting dataframes: {str(e)}")
            raise
#EOC
#-----------------------------------------------------------------------------#

