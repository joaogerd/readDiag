"""
Module for reading and processing GSI diagnostic files.
Supports conventional (conv) and satellite radiance (rad) formats.
Includes optional memory-mapped reads, detailed logging, and parallel time-series reading.
"""
import os
import struct
import numpy as np
import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple, Optional, Any, Union, IO
import logging
import time
import functools
from logging.handlers import RotatingFileHandler

# Timing decorator for performance logging
def log_time(func):
    """Decorator to log execution time of class methods.

    Args:
        func (Callable): The function to be decorated.

    Returns:
        Callable: The wrapped function with timing logging.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        start = time.perf_counter()
        result = func(self, *args, **kwargs)
        duration = time.perf_counter() - start
        logger.info(f"{func.__name__} completed in {duration:.3f}s")
        return result
    return wrapper

# Configure module logger: console + rotating file handlers
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")

    # Console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File (rotates at 10 MB, keeps 5 backups)
    file_handler = RotatingFileHandler(
        "diagAccess.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Allow override via DIAGACCESS_LOG_LEVEL env var
level = os.getenv("DIAGACCESS_LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, level, logging.INFO))

class diagAccess:
    """
    Class to read and process GSI diagnostic files (conventional and radiance).

    This class supports automatic detection of file type (conventional or radiance)
    and provides structured access to diagnostic information via Pandas DataFrames.

    Attributes:
        file_name (str): Path to the GSI diagnostic file.
        var (Optional[str]): Observation variable to filter when reading.
        use_memmap (bool): Whether to use memory-mapped access for radiance data.

    Example:
        >>> from diagAccess import diagAccess
        >>> reader = diagAccess("diag_conv_ges.2023010100", var="t")
        >>> df_dict = reader.get_data_frame()
        >>> df_temp = df_dict["t"][120]  # Get channel 120

        >>> reader = diagAccess("diag_rad_ges.2023010100", use_memmap=True)
        >>> df_rad = reader.get_data_frame()["dataframes"]["diagbuf_df"]

        >>> df_all = diagAccess.read_time_series([
        ...     "diag_conv_ges.2023010100",
        ...     "diag_conv_ges.2023010112"
        ... ], var="uv")
    """
    # Radiance dtype cache
    _dtypes_inited: bool = False
    header_diagbuf: List[str] = [
        'lat','lon','elev','time','iscanp','zasat','ilazi','pangs','isazi','sgagl',
        'sfcwc','sfclc','sfcic','sfcsc','sfcwt','sfclt','sfcit','sfcst','sfcstp',
        'sfcsmc','sfcltp','sfcvf','sfcsd','sfcws','clsORclw','cldpORtpwc'
    ]
    header_diagbufchan: List[str] = ['tb_obs','omf','omf_nbc','errinv','idqc','emiss','tlach','ts']

    @classmethod
    def _init_dtypes(cls) -> None:
        """
        Initialize NumPy data types used to parse radiance file headers.

        This method caches dtype definitions to avoid redundant computation
        during multiple file reads.
        """
        if cls._dtypes_inited:
            return
        cls.header_info_dtype = np.dtype([
            ('head','>i4'),('isis','>S20'),('dplat','>S10'),('obstype','>S10'),
            ('jiter','>i4'),('nchanl','>i4'),('npred','>i4'),('idate','>i4'),
            ('ireal','>i4'),('ipchan','>i4'),('iextra','>i4'),('jextra','>i4'),
            ('extra','>S20'),('tail','>i4')
        ])
        cls.channel_info_dtype = np.dtype([
            ('head','>i4'),('freq','>f4'),('pol','>f4'),('wave','>f4'),
            ('varch','>f4'),('tlap','>f4'),('iuse','>i4'),('nuchan','>i4'),
            ('ich','>i4'),('tail','>i4')
        ])
        cls._dtypes_inited = True

    @staticmethod
    def _detect_format_file(file_name: str) -> str:
        """
        Detect the file format type (conventional or radiance).

        Args:
            file_name (str): Path to the diagnostic file.

        Returns:
            str: 'conv' if conventional, 'rad' otherwise.
        """
        with open(file_name, 'rb') as f:
            val = struct.unpack('>I', f.read(4))[0]
        return 'conv' if val == 4 else 'rad'

    def __init__(
        self,
        file_name: str,
        var: Optional[str]=None,
        use_memmap: bool=False
    ) -> None:
        """
        Initialize a diagAccess instance.

        Args:
            file_name (str): Path to the GSI diagnostic file.
            var (Optional[str], optional): Variable of interest. Defaults to None.
            use_memmap (bool, optional): Use memory-mapped reading. Defaults to False.

        Raises:
            ValueError: If the file is too small or has an invalid header.
        """
        logger.info(f"Initializing diagAccess: file={file_name}, var={var}, use_memmap={use_memmap}")
        size = os.path.getsize(file_name)
        if size < 4:
            logger.error(f"File too small: {file_name} ({size} bytes)")
            raise ValueError(f"File too small to detect format: {file_name}")
        self.file_name = file_name
        self.var = var
        self.use_memmap = use_memmap
        self._init_dtypes()
        self.udef = -1.0e15
        self.rtiny = 10 * np.finfo(float).tiny
        fmt = self._detect_format_file(file_name)
        if fmt=='conv':
            self._data_type=1
            self._data_frame=self._readConv()
        else:
            self._data_type=2
            self._data_frame=self._readRad()

            
    def get_date(self) -> datetime:
        """
        Get the datetime corresponding to the diagnostic file.

        Returns:
            datetime: The extracted date.

        Raises:
            AttributeError: If date has not been set.
        """
        if hasattr(self, '_idate'):
            return self._idate  # type: ignore
        raise AttributeError("Date not set.")

    def get_data_type(self) -> int:
        """
        Get the type of data in the file.

        Returns:
            int: 1 for conventional, 2 for radiance.
        """
        return self._data_type  # type: ignore

    def get_data_frame(self) -> Any:
        """
        Get the main data structure containing the diagnostic observations.

        Returns:
            Any: Dictionary of DataFrames (conventional) or structured dict (radiance).
        """
        return self._data_frame  # type: ignore

    # --- Conventional ---
    def _get_base_columns(self) -> List[str]:
        """
        Get the base column names common to conventional diagnostics.

        Returns:
            List[str]: List of column names.
        """
        return [
            'ks','lat','lon','elev','prs','dhgt','time','pbqc','emark',
            'iusev','iuse','wpbqc','inp_err','adj_err','end_err','robs'
        ]

    def _get_columns(self, var: str, ninfo: int) -> List[str]:
        """
        Construct column names for a given variable and number of fields.

        Args:
            var (str): Variable identifier (e.g., 't', 'q', 'uv', 'ps', etc).
            ninfo (int): Number of diagnostic fields per observation.

        Returns:
            List[str]: Column names to assign to the DataFrame.
        """
        base: List[str] = self._get_base_columns()
        map_cols: Dict[str, List[str]] = {
            'q': ['omf','omf_wob','qsges'],
            't': ['omf','omf_wob'],
            'sst': ['omf'],
            'uv': ['robs_u','omf_u','omf_wob_u','robs_v','omf_v','omf_wob_v','factw'],
            'ps': ['omf','omf_wob'],
            'gps': ['inc_ba','imp_height','zsges','trefges','hob','gps_ref','qrefges']
        }
        if var == 'sst' and ninfo >= 21:
            map_cols['sst'] = ['tref','dtw','dtc','tz']
        if var == 't' and ninfo >= 20:
            map_cols['t'] = ['pof','wvv']
        if var == 'gps':
            return [
                'ks','lat','lon','inc_ba','prs','imp_height','time','zsges',
                'pbqc','iusev','iuse','wpbqc','inp_err','adj_err','end_err',
                'robs','trefges','hob','gps_ref','qrefges'
            ]
        spec: List[str] = map_cols.get(var, [])
        return base[:-1] + spec if var == 'uv' else base + spec

    @log_time
    def _readConv(self) -> Dict[str, Dict[int, pd.DataFrame]]:
        """
        Read conventional diagnostic data from binary file.

        Returns:
            Dict[str, Dict[int, pd.DataFrame]]: Nested dictionary by variable and channel.

        Raises:
            ValueError: If the file header is invalid.
        """
        logger.info(f"Reading conventional diagnostics from {self.file_name}")
        # Protect against incomplete conventional file headers
        with open(self.file_name, 'rb') as f:
            try:
                hdr_vals = np.fromfile(f, '>i4', 3)
                if hdr_vals.size < 3:
                    raise IndexError
                _, idate, _ = hdr_vals
            except Exception:
                logger.error(f"Invalid conventional header in {self.file_name}", exc_info=True)
                raise ValueError(f"Invalid conventional header: {self.file_name}")
            self._idate = datetime.strptime(str(int(idate)), '%Y%m%d%H')
            result: Dict[str, Dict[int, pd.DataFrame]] = {}

            # Continue reading blocks
            while True:
                hv = self._read_conv_header(f)
                if hv is None:
                    break
                nobs, ninfo, var = hv
                if nobs > 0:
                    data = self._read_conv_diag_data(f, nobs, ninfo)
                    if not self.var or self.var == var:
                        self._process_conv_data(data, var, nobs, ninfo, result)
                else:
                    f.read(4)
        return result
    def _read_conv_header(self, f: IO[bytes]) -> Optional[Tuple[int, int, str]]:
        """
        Read and decode the header of a conventional diagnostic block.

        Args:
            f (IO[bytes]): Open file object.

        Returns:
            Optional[Tuple[int, int, str]]: Number of observations, info count, and variable name.
        """
        dtype = [
            ('head', '>i4'), ('var', 'S3'), ('nchar', '>i4'),
            ('ninfo', '>i4'), ('nobs', '>i4'), ('mype', '>i4'),
            ('tail', '>i4'), ('tail2', '>i4')
        ]
        hdr = np.fromfile(f, dtype, 1)
        if not hdr.size:
            return None
        return (
            int(hdr['nobs'][0]),
            int(hdr['ninfo'][0]),
            hdr['var'][0].decode().strip()
        )

    def _read_conv_diag_data(
        self,
        f: IO[bytes],
        nobs: int,
        ninfo: int
    ) -> Any:
        """
        Read diagnostic values from conventional data block.

        Args:
            f (IO[bytes]): Open file object.
            nobs (int): Number of observations.
            ninfo (int): Number of fields per observation.

        Returns:
            Any: Raw binary array of observation values.
        """
        dt = np.dtype([
            ('eh', '>i4'),
            ('cb', ('>S8', nobs)),
            ('rb', ('>f4', (nobs, ninfo))),
            ('et', '>i4')
        ])
        arr = np.fromfile(f, dt, 1).byteswap().newbyteorder()[0]
        return arr

    def _process_conv_data(
        self,
        data: Any,
        var: str,
        nobs: int,
        ninfo: int,
        out: Dict[str, Dict[int, pd.DataFrame]]
    ) -> None:
        """
        Convert raw data into DataFrame and insert it into the output structure.

        Args:
            data (Any): Raw array of diagnostic data.
            var (str): Observation variable.
            nobs (int): Number of observations.
            ninfo (int): Number of fields per observation.
            out (Dict[str, Dict[int, pd.DataFrame]]): Output dictionary to populate.
        """
        arr = data['rb'].reshape(nobs, ninfo)
        kx = np.rint(arr[:, 0]).astype(int)
        for k in np.unique(kx):
            rows = arr[kx == k, 1:]
            df = pd.DataFrame(rows, columns=self._get_columns(var, ninfo))
            out.setdefault(var, {})
            out[var][k] = (
                df
                if k not in out[var]
                else pd.concat([out[var][k], df], ignore_index=True)
            )

    # --- Radiance ---
    @log_time
    def _readRad(self) -> Dict[str, Any]:
        """
        Read radiance diagnostic data from binary file.

        Returns:
            Dict[str, Any]: Dictionary with metadata and dataframes.

        Raises:
            ValueError: If the header is invalid.
        """
        logger.info(f"Reading radiance diagnostics from {self.file_name} (memmap={self.use_memmap})")
        f: IO[bytes] = open(self.file_name, 'rb')
        # Protege o parse do header
        try:
            hdr, size = self._read_header(f)
        except IndexError:
            logger.error(f"Invalid radiance header in {self.file_name}", exc_info=True)
            raise ValueError(f"Invalid radiance header: {self.file_name}")
        # Continua a leitura normalmente
        chdf = self._read_channel_info(f, hdr['nchanl'])
        diag = self._read_diagnostic_data(f, size, hdr)
        df1, df_list, df2 = self._extract_dataframes(diag, hdr)
        f.close()
        return {
            'obstype': hdr['obstype'],
            'dplat': hdr['dplat'],
            'dataframes': {
                'channel_df': chdf,
                'diagbuf_df': df1,
                'diagbufchan_df': df_list,
                'diagbufex_df': df2
            }
        }

    def _read_header(self, f: IO[bytes]) -> Tuple[Dict[str, Any], int]:
        """
        Read and parse the main header of a radiance diagnostic file.

        Args:
            f (IO[bytes]): Open file object.

        Returns:
            Tuple[Dict[str, Any], int]: Parsed header and file size.
        """
        rec = np.fromfile(f, type(self).header_info_dtype, 1)[0]
        hdr = {k: rec[k] for k in rec.dtype.names}
        size = os.path.getsize(self.file_name)
        return hdr, size

    def _read_channel_info(
        self,
        f: IO[bytes],
        nchanl: int
    ) -> pd.DataFrame:
        """
        Read information for each radiance channel.

        Args:
            f (IO[bytes]): Open file object.
            nchanl (int): Number of channels in the file.

        Returns:
            pd.DataFrame: DataFrame containing channel-level metadata.
        """
        arr = np.fromfile(f, type(self).channel_info_dtype, nchanl)
        arr = arr.byteswap().newbyteorder()
        return pd.DataFrame(arr).drop(['head', 'tail'], axis=1)

    def _read_diagnostic_data(
        self,
        f: IO[bytes],
        file_size: int,
        header: Dict[str, Any]
    ) -> np.ndarray:
        """
        Read diagnostic data buffer from radiance file.

        Args:
            f (IO[bytes]): Open file object.
            file_size (int): Total file size in bytes.
            header (Dict[str, Any]): Parsed header values.

        Returns:
            np.ndarray: Structured array containing diagnostic data.
        """
        dt = np.dtype([
            ('eh', np.void, 4),
            ('db', ('>f4', header['ireal'])),
            ('dbc', ('>f4', (header['ipchan'] + header['npred'] + 2) * header['nchanl'])),
            ('dbe', ('>f4', header['jextra'])) if header['iextra'] > 0 else ('>f4', 0),
            ('et', np.void, 4)
        ])
        num = (file_size - 4) // dt.itemsize
        if self.use_memmap:
            offset = f.tell()
            mm = np.memmap(self.file_name, dtype=dt, mode='r', offset=offset, shape=(num,))
            f.seek(offset + num * dt.itemsize)
            return mm.byteswap().newbyteorder()
        buf = f.read(num * dt.itemsize)
        return np.frombuffer(buf, dtype=dt).byteswap().newbyteorder()

    def _extract_dataframes(
        self,
        diag: np.ndarray,
        header: Dict[str, Any]
    ) -> Tuple[pd.DataFrame, List[pd.DataFrame], pd.DataFrame]:
        """
        Extract DataFrames from radiance diagnostic array.

        Args:
            diag (np.ndarray): Structured array of diagnostic data.
            header (Dict[str, Any]): Header with dimension sizes.

        Returns:
            Tuple[pd.DataFrame, List[pd.DataFrame], pd.DataFrame]: Main data, per-channel data, and extra info.
        """
        df1 = pd.DataFrame(
            diag['db'][:, :len(self.header_diagbuf)], columns=self.header_diagbuf
        )
        chan_list: List[pd.DataFrame] = []
        total = header['ipchan'] + header['npred'] + 2
        cols = self.header_diagbufchan.copy()
        for i in range(1, header['npred'] + 3):
            cols.append(f'pred{i}')
        for i in range(header['nchanl']):
            s, e = i * total, (i + 1) * total
            chan_list.append(
                pd.DataFrame(diag['dbc'][:, s:e], columns=cols)
            )
        df2 = pd.DataFrame(diag['dbe'])
        return df1, chan_list, df2

    @classmethod
    @log_time
    def read_time_series(
        cls,
        file_list: List[str],
        var: Optional[str] = None,
        n_workers: int = 4
    ) -> Union[pd.DataFrame, List[Any]]:
        """
        Read and concatenate diagnostics from multiple files in parallel.

        Args:
            file_list (List[str]): List of file paths.
            var (Optional[str], optional): Variable to extract. Defaults to None.
            n_workers (int, optional): Number of parallel workers. Defaults to 4.

        Returns:
            Union[pd.DataFrame, List[Any]]: Concatenated DataFrame or list of outputs.

        Example:
            >>> files = ["diag_conv_ges.2023010100", "diag_conv_ges.2023010112"]
            >>> df_uv = diagAccess.read_time_series(files, var="uv")
        """
        """
        Read multiple diagnostic files in parallel and concatenate results for a given variable.
        """
        def _load(path: str) -> Union[pd.DataFrame, Any]:
            rd = cls(path, var)
            if rd.get_data_type() == 1:
                data = rd.get_data_frame().get(var, {})
                dfs: List[pd.DataFrame] = []
                for ch, df in data.items():
                    tmp = df.copy()
                    tmp['channel'] = ch
                    tmp['date'] = rd.get_date()
                    dfs.append(tmp)
                return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
            return rd.get_data_frame()

        with ThreadPoolExecutor(max_workers=n_workers) as exe:
            results = list(exe.map(_load, file_list))
        if results and isinstance(results[0], pd.DataFrame):
            return pd.concat(results, ignore_index=True)
        return results

# backward compatibility alias
DiagAccess = diagAccess

