"""
Build Phase-1 zero-copy module:

  cd python/bindings
  python3 setup.py build_ext --inplace
"""
from pathlib import Path
from setuptools import setup, Extension
import pybind11
import numpy
import sys

ROOT = Path(__file__).resolve().parents[2]
CPP_INCLUDE = ROOT / "cpp" / "include"

compile_args = ["-O3", "-std=c++17", "-fvisibility=hidden"]
if sys.platform == "win32":
    compile_args = ["/O2", "/std:c++17"]

ext = Extension(
    "prym_gyro_native",
    sources=["prym_gyro_bind.cpp"],
    include_dirs=[
        str(CPP_INCLUDE),
        pybind11.get_include(),
        numpy.get_include(),
    ],
    language="c++",
    extra_compile_args=compile_args,
)

setup(
    name="prym_gyro_native",
    version="0.1.3",
    description="PrymGyroSort zero-copy GyroRank binding",
    ext_modules=[ext],
    zip_safe=False,
)
