"""Build zero-copy module. PRYM_NATIVE=1 enables -march=native -fopenmp."""
from pathlib import Path
from setuptools import setup, Extension
import os
import pybind11
import numpy
import sys

ROOT = Path(__file__).resolve().parents[2]
CPP_INCLUDE = ROOT / "cpp" / "include"
native = os.environ.get("PRYM_NATIVE", "").strip() in ("1", "true", "yes")

if sys.platform == "win32":
    compile_args, link_args = ["/O2", "/std:c++17"], []
elif native:
    compile_args = ["-O3", "-std=c++17", "-fvisibility=hidden", "-march=native", "-fopenmp"]
    link_args = ["-fopenmp"]
else:
    compile_args = ["-O3", "-std=c++17", "-fvisibility=hidden"]
    link_args = []

ext = Extension(
    "prym_gyro_native",
    sources=["prym_gyro_bind.cpp"],
    include_dirs=[str(CPP_INCLUDE), pybind11.get_include(), numpy.get_include()],
    language="c++",
    extra_compile_args=compile_args,
    extra_link_args=link_args,
)

setup(name="prym_gyro_native", version="0.1.4", description="PrymGyroSort zero-copy binding",
      ext_modules=[ext], zip_safe=False)
