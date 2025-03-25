"""variables used across API implementation"""

import ctypes
import os
from ctypes.util import find_library
from pathlib import Path

import numba
import numpy as np
import psutil
from mpi4py import MPI

# pylint: disable=protected-access
_MPI_Comm_World_ptr = MPI._addressof(MPI.COMM_WORLD)

_MPI_DTYPES = {
    np.dtype("uint8"): MPI._addressof(MPI.CHAR),
    np.dtype("int32"): MPI._addressof(MPI.INT32_T),
    np.dtype("int64"): MPI._addressof(MPI.INT64_T),
    np.dtype("float"): MPI._addressof(MPI.FLOAT),
    np.dtype("double"): MPI._addressof(MPI.DOUBLE),
    np.dtype("complex64"): MPI._addressof(MPI.C_FLOAT_COMPLEX),
    np.dtype("complex128"): MPI._addressof(MPI.C_DOUBLE_COMPLEX),
}

if MPI._sizeof(MPI.Comm) == ctypes.sizeof(ctypes.c_int):
    _MpiComm = ctypes.c_int
else:
    _MpiComm = ctypes.c_void_p

if MPI._sizeof(MPI.Datatype) == ctypes.sizeof(ctypes.c_int):
    _MpiDatatype = ctypes.c_int
    _MpiOp = ctypes.c_int
else:
    _MpiDatatype = ctypes.c_void_p
    _MpiOp = ctypes.c_void_p

if MPI._sizeof(MPI.Request) == ctypes.sizeof(ctypes.c_int):
    RequestType = np.intc
else:
    RequestType = np.uintp

# pylint: enable=protected-access
_MpiStatusPtr = ctypes.c_void_p
_MpiRequestPtr = ctypes.c_void_p


# TODO: add proper handling of status objects
@numba.njit
def create_status_buffer(count=1):
    """Helper function for creating numpy array storing pointers to MPI_Status results."""
    return np.empty(count * 5, dtype=np.intc)


LIB = None
names = ("mpich", "mpi", "msmpi", "impi")

ps = psutil.Process(os.getpid())
windows = os.name == "nt"
if hasattr(ps, "memory_maps"):
    for dll in ps.memory_maps():
        path = Path(dll.path)
        if windows or path.stem.startswith("lib"):
            for name in names:
                if name + ("" if windows else ".") in path.stem:
                    LIB = str(path)
                    break

else:
    for name in names:
        LIB = find_library(name)
        if LIB is not None:
            break

if sys.platform == "darwin" and LIB is None:
        LIB_bash_str = "$(brew --cellar open-mpi)/$(brew list --versions open-mpi | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+')"
        LIB_bash = subprocess.run(f'echo {LIB_bash_str}', shell=True, stdout=subprocess.PIPE)
        if LIB_bash.returncode == 0:
            LIB = LIB_bash.stdout.decode('ascii').strip()+"/lib/libmpi.dylib"
            

if LIB is None:
    raise RuntimeError("no MPI library found")

libmpi = ctypes.CDLL(LIB)

send_recv_args = [
    ctypes.c_void_p,
    ctypes.c_int,
    _MpiDatatype,
    ctypes.c_int,
    ctypes.c_int,
    _MpiComm,
]

send_recv_async_args = send_recv_args + [_MpiRequestPtr]
