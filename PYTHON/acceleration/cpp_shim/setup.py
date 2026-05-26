"""
cpp_shim/setup.py — pybind11 derleme yapilandirmasi
"""
from pybind11.setup_helpers import Pybind11Extension, build_ext
from setuptools import setup

ext_modules = [
    Pybind11Extension(
        "anatoliax_cpp",
        sources=[
            "cpp_shim/bindings.cpp",
            "cpp_shim/clock.cpp",
        ],
        include_dirs=["cpp_shim/include"],
        cxx_std=17,
        define_macros=[("VERSION_INFO", "1.0.0")],
    ),
]

setup(
    name="anatoliax_cpp",
    version="1.0.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
    zip_safe=False,
)
