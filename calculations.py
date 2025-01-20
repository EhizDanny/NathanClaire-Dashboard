# import pandas as pd
# import datetime
# from datetime import datetime, timedelta
# from dataclasses import dataclass, field
# from functools import lru_cache
# import atexit

# def importData() -> pd.DataFrame:
#     """
#     Returns:
#         pd.DataFrame: [pandas dataframe of the imported table from db]
#     """    
#     return pd.read_csv('infraData.csv')

# data = importData()

# latestTime = data['LogTimestamp'].max()

# @dataclass()
# class InfraCalculate:
#     """
#     Returns:
#         [measures]: [calculated measures for Infrastructure Monitoring]
#     """    
#     __data: pd.DataFrame
#     latestLog: pd.Timestamp = field(init = False) 
#     activeHosts: list = field(default_factory= list)
#     cpuUsage: int = field(init = False) 
#     avDiskUsage: int = field(init = False) 
#     currentCPU: float = field(init = False) 
#     currentDisk: float = field(init = False) 
#     currentNetworkTrafficAgg: float = field(init = False) 
#     currentNetworkTrafficRec: float = field(init = False) 
#     currentNetworkTrafficSent: float = field(init = False) 
#     currentDiskAvail: float   = field(init = False) 
#     currentDiskSpace: float  = field(init = False) 
#     currentFreeDisk: float  = field(init = False) 
#     currentTotalDisk: float = field(init = False) 
#     highCPUUsageCount: int = field(init = False) 
#     highDiskUsageCount: int  = field(init = False) 
#     highMemUsageCount: int = field(init = False) 
#     percentageDiskUsed: float = field(init = False) 
#     minutesDifference: str = field(init = False) 
#     totalServer: int  = field(init = False) 
#     servers: list = field(default_factory = list)

#     # Since other measures are calculated based on the contents of data,we cant require them as inputs during initialization. Instead, they are computed after the class instance is created.
    
#     def __post_init__(self) -> None:    
#         self.df = self.__data.copy()
#         self.latestLog = self.df['LogTimestamp'].max()
#         self.cpuUsage = self.df['CPUUsage'].mean()
#         self.avDiskUsage = self.df['DiskUsage'].mean()
#         self.avMemoryUsage = self.df['MemoryUsage'].mean()
#         self.currentCPU = self.df[self.df['LogTimestamp'] >= self.latestLog]['CPUUsage']
#         self.currentDisk = self.df[self.df['LogTimestamp'] >= self.latestLog]['DiskUsage']
#         self.currentDiskAvail = self.df[self.df['LogTimestamp'] >= self.latestLog]['TotalFreeDiskGB']
#         self.currentDiskSpace = self.df[self.df['LogTimestamp'] >= self.latestLog]['TotalDiskSpaceGB']
#         self.currentNetworkTrafficAgg = self.df[self.df['LogTimestamp'] >= self.latestLog]['NetworkTrafficAggregate']
#         self.currentNetworkTrafficRec = self.df[self.df['LogTimestamp'] >= self.latestLog]['NetworkTrafficReceived']
#         self.currentNetworkTrafficSent = self.df[self.df['LogTimestamp'] >= self.latestLog]['NetworkTrafficSent']
#         self.currentFreeDisk = self.df[self.df['LogTimestamp'] >= self.latestLog]['TotalFreeDiskGB']
#         self.currentTotalDisk = self.df[self.df['LogTimestamp'] >= self.latestLog]['TotalDiskSpaceGB']
#         self.df['HostAndIP'] =  self.df['Hostname'] + self.df['IPAddress'].str.replace('"', '')
#         self.servers = self.df.HostAndIP.unique().tolist()
#         self.totalServer = self.df.HostAndIP.nunique()
#         self.highCPUUsageCount = self.highMetric('CPUUsage')
#         self.highDiskUsageCount = self.highMetric('DiskUsage')
#         self.highMemUsageCount = self.highMetric('MemoryUsage')
#         self.activeHosts = self.df[pd.to_datetime(self.df['LogTimestamp']) >= (datetime.now() - timedelta(minutes = 5))]['IPAddress'].unique().tolist()
#         self.percentageDiskUsed = ((self.df['TotalDiskSpaceGB'] - self.df['TotalFreeDiskGB']) / self.df['TotalDiskSpaceGB']) * 100

#     def highMetric(self, variable: str) -> int:
#         """calculates the number of servers whose metric(CPU Usage, Disk Usage, or Memory Usage) has exceeded 85% in the last 5 minutes
#         Args:
#             variable ([str]): [choice metric, either 'CPUUsage' or 'DiskUsage' or 'MemoryUsage' ]
#         Returns:
#             int: [returns the number of servers that has its metric usage exceeded the 85% threshold]
#         """        
#         temporal = self.df.groupby('HostAndIP')[['LogTimestamp']].max().reset_index()
#         lastNoneBlank = []
#         for i in temporal.index:
#             lastNoneBlank.append(self.df[(self.df.HostAndIP == temporal.iloc[i]['HostAndIP']) \
#                                      & (self.df.LogTimestamp == temporal.iloc[i]['LogTimestamp'])][variable].values[0])
#         temporal['lastVar'] = pd.Series(lastNoneBlank)
#         return len(temporal[temporal.lastVar > 85])
    
    
import pandas as pd
import datetime
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from functools import lru_cache
import atexit

def importData() -> pd.DataFrame:
    """
    Returns:
        pd.DataFrame: [pandas dataframe of the imported table from db]
    """    
    return pd.read_parquet('infraParq.parquet', engine = 'fastparquet')

# data = importData()

# latestTime = data['LogTimestamp'].max()

@dataclass()
class InfraCalculate:
    """
    Returns:
        [measures]: [calculated measures for Infrastructure Monitoring]
    """    
    __data: pd.DataFrame
    latestLog: pd.Timestamp = field(init = False) 
    activeHosts: list = field(default_factory= list)
    cpuUsage: int = field(init = False) 
    avDiskUsage: int = field(init = False) 
    currentCPU: float = field(init = False) 
    currentMemory: float = field(init = False) 
    currentDisk: float = field(init = False) 
    currentNetworkTrafficAgg: float = field(init = False) 
    currentNetworkTrafficRec: float = field(init = False) 
    currentNetworkTrafficSent: float = field(init = False) 
    currentTotalMemory: float = field(init = False) 
    currentDiskAvail: float   = field(init = False) 
    currentDiskSpace: float  = field(init = False) 
    currentFreeDisk: float  = field(init = False) 
    currentTotalDisk: float = field(init = False) 
    highCPUUsageCount: int = field(init = False) 
    highDiskUsageCount: int  = field(init = False) 
    highMemUsageCount: int = field(init = False) 
    percentageDiskUsed: float = field(init = False) 
    minutesDifference: str = field(init = False) 
    totalServer: int  = field(init = False) 
    servers: list = field(default_factory = list)

    # Since other measures are calculated based on the contents of data,we cant require them as inputs during initialization. Instead, they are computed after the class instance is created.
    
    def __post_init__(self) -> None:    
        self.df = self.__data.copy()
        self.latestLog = self.df['LogTimestamp'].max()
        self.cpuUsage = self.df['CPUUsage'].mean()
        self.avDiskUsage = self.df['DiskUsage'].mean()
        self.avMemoryUsage = self.df['MemoryUsage'].mean()
        self.currentCPU = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['CPUUsage'])
        self.currentDisk = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['DiskUsage'])
        self.currentMemory = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['MemoryUsage'])
        self.currentDiskAvail = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['TotalFreeDiskGB'])
        self.currentDiskSpace = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['TotalDiskSpaceGB'])
        self.currentNetworkTrafficAgg = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['NetworkTrafficAggregate'])
        self.currentNetworkTrafficRec = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['NetworkTrafficReceived'])
        self.currentNetworkTrafficSent = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['NetworkTrafficSent'])
        self.currentFreeDisk = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['TotalFreeDiskGB'])
        self.currentTotalDisk = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['TotalDiskSpaceGB'])
        self.currentTotalMemory = sum(self.df[self.df['LogTimestamp'] >= self.latestLog]['TotalMemory'])
        self.df['HostAndIP'] =  self.df['Hostname'] + self.df['IPAddress'].str.replace('"', '')
        self.servers = self.df.HostAndIP.unique().tolist()
        self.totalServer = self.df.HostAndIP.nunique()
        self.highCPUUsageCount = self.highMetric('CPUUsage')
        self.highDiskUsageCount = self.highMetric('DiskUsage')
        self.highMemUsageCount = self.highMetric('MemoryUsage')
        self.activeHosts = self.df[pd.to_datetime(self.df['LogTimestamp']) >= (datetime.now() - timedelta(minutes = 5))]['IPAddress'].unique().tolist()
        self.percentageDiskUsed = ((self.df['TotalDiskSpaceGB'] - self.df['TotalFreeDiskGB']) / self.df['TotalDiskSpaceGB']) * 100

    def highMetric(self, variable: str) -> int:
        """calculates the number of servers whose metric(CPU Usage, Disk Usage, or Memory Usage) has exceeded 85% in the last 5 minutes
        Args:
            variable ([str]): [choice metric, either 'CPUUsage' or 'DiskUsage' or 'MemoryUsage' ]
        Returns:
            int: [returns the number of servers that has its metric usage exceeded the 85% threshold]
        """        
        # temporal = self.df.groupby('HostAndIP')[['LogTimestamp']].max().reset_index()
        # lastNoneBlank = []
        # for i in temporal.index:
        #     lastNoneBlank.append(self.df[(self.df.HostAndIP == temporal.iloc[i]['HostAndIP']) \
        #                              & (self.df.LogTimestamp == temporal.iloc[i]['LogTimestamp'])][variable].values[0])
        # temporal['lastVar'] = pd.Series(lastNoneBlank)
        # return len(temporal[temporal.lastVar > 85])
        return self.df[(self.df['LogTimestamp'] >= self.df['LogTimestamp'].max()) & (self.df[variable] > 85)]['HostAndIP'].nunique()
