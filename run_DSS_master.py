# Native-python libs:
import time

# Third-party libraries:

# DSS related classes:
from dss.master import DSS

# My libraries:

# -----------------------------------------------------------------------------
# DSS Files:

# IEEETestCases:
# 13Bus
filename = r"D:\dss-pykit-testcases\IEEETestCases\13Bus\IEEE13Nodeckt.dss"

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    start_time = time.perf_counter()

    # Basic setup:
    std_unit = 'km'

    # Innitializing the DSS master class object:
    mydss = DSS(filename, std_unit, Dssview_disable=True)

    print('\nSimulation time: ' + str(round(time.perf_counter() - start_time, 2)) + ' [s]')
