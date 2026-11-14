"""Record the exact local numerical environment, without opening market data."""
import contextlib
import hashlib
import importlib.metadata
import io
import os
import platform
import struct
import sys
import warnings
from pathlib import Path

import numpy as np

THREAD_ENV = {
    "PYTHONHASHSEED": "0",
    "OPENBLAS_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fingerprint():
    root = Path(np.__file__).parent
    selected = {root / "__init__.py", root / "random/__init__.py"}
    selected.update((root / "random").glob("*.so"))
    selected.update((root / "core").glob("*.so"))
    selected.update((root / ".dylibs").glob("*.dylib"))
    build = io.StringIO()
    with warnings.catch_warnings(), contextlib.redirect_stdout(build):
        warnings.filterwarnings("ignore", message="Install `pyyaml` for better output", category=UserWarning)
        np.show_config()
    return {
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_full_version": sys.version,
        "python_compiler": platform.python_compiler(),
        "python_executable_sha256": digest(Path(sys.executable).resolve()),
        "base_python_executable_sha256": digest(Path(sys._base_executable).resolve()),
        "isolated_virtual_environment": sys.prefix != sys.base_prefix,
        "platform": platform.platform(),
        "os_release": platform.release(),
        "macos_version": platform.mac_ver()[0],
        "machine": platform.machine(),
        "pointer_bits": struct.calcsize("P") * 8,
        "byteorder": sys.byteorder,
        "float_format": {"mant_dig": sys.float_info.mant_dig, "max_exp": sys.float_info.max_exp,
                         "rounds": sys.float_info.rounds, "numpy_float64_bits": np.finfo(np.float64).bits},
        "packages": dict(sorted((d.metadata["Name"].lower(), d.version) for d in importlib.metadata.distributions())),
        "process_controls": {key: os.environ.get(key) for key in THREAD_ENV},
        "numpy_numeric_files_sha256": {str(p.relative_to(root)): digest(p) for p in sorted(selected)},
        "numpy_cpu_features": dict(np.core._multiarray_umath.__cpu_features__),
        "numpy_build_configuration": build.getvalue(),
    }


def rng_probe():
    """Synthetic RNG compatibility vectors, NOT Bootstrap or trade resampling."""
    seed = 20261114
    return {
        "seed": seed,
        "bit_generator": "PCG64",
        "raw_uint64_size_8": [int(x) for x in np.random.PCG64(seed).random_raw(8)],
        "generator_integers": {
            "low": 0, "high_exclusive": 17, "size": 16, "dtype": "int64", "endpoint": False,
            "values": [int(x) for x in np.random.Generator(np.random.PCG64(seed)).integers(0, 17, size=16, dtype=np.int64, endpoint=False)],
        },
    }
