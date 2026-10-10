# Copyright 2022 SpinQ Technology Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# import setuptools
import os
import re
import sys

import platform
import subprocess
import tempfile

from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


def pybind11_build_env():
    """Expose setuptools' build dependency to CMake's Python subprocesses."""
    # Import only after setup_requires has been resolved, not at module load.
    import pybind11

    env = os.environ.copy()
    # Legacy setuptools can put setup_requires in .eggs, which changes this
    # process's sys.path but is not automatically inherited by CMake/Python.
    package_root = os.path.dirname(os.path.dirname(os.path.abspath(pybind11.__file__)))
    env['PYTHONPATH'] = os.pathsep.join(filter(None, [
        package_root, env.get('PYTHONPATH')]))
    return env


def cmake_generator(build_dir):
    """Use the requested/cached generator, or ask CMake for its default."""
    requested = os.environ.get('CMAKE_GENERATOR')
    if requested:
        return requested

    def read_generator(directory):
        cache = os.path.join(directory, 'CMakeCache.txt')
        if os.path.isfile(cache):
            with open(cache, encoding='utf-8') as handle:
                for line in handle:
                    if line.startswith('CMAKE_GENERATOR:INTERNAL='):
                        return line.partition('=')[2].strip()

    cached = read_generator(build_dir)
    if cached:
        return cached

    # Probe without enabling a compiler: VS 2017 defaults to Win32, so the
    # real project must receive -A x64 before its first compiler check.
    with tempfile.TemporaryDirectory(prefix='spinqit-cmake-') as directory:
        with open(os.path.join(directory, 'CMakeLists.txt'), 'w',
                  encoding='utf-8') as handle:
            handle.write('cmake_minimum_required(VERSION 3.18)\n'
                         'project(generator_probe NONE)\n')
        subprocess.check_output(['cmake', directory], cwd=directory)
        generator = read_generator(directory)
    if not generator:
        raise RuntimeError('Could not determine the CMake generator')
    return generator


def runtime_library_name():
    """Select the vendor library for a native build; leave sources in cppsrc/lib."""
    system = platform.system()
    machine = platform.machine().lower()
    if system == 'Windows' and machine in ('amd64', 'x86_64') and sys.maxsize > 2**32:
        return 'SpinQInterface_win_x86_64.dll'
    if system == 'Linux' and machine in ('amd64', 'x86_64'):
        return 'libSpinQInterface_linux_x86_64.so'
    if system == 'Darwin':
        if machine == 'x86_64':
            return 'libSpinQInterface_darwin_x86_64.dylib'
        if machine == 'arm64':
            return 'libSpinQInterface_darwin_arm_64.dylib'
    raise RuntimeError('No SpinQInterface library for {} {}'.format(system, machine))



class CMakeExtension(Extension):
    def __init__(self, name, sourcedir=''):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir or ROOT_DIR)


class CMakeBuild(build_ext):
    def get_outputs(self):
        outputs = super().get_outputs()
        for ext in self.extensions:
            outputs.append(os.path.join(
                os.path.dirname(self.get_ext_fullpath(ext.name)),
                runtime_library_name()))
        return outputs

    def run(self):
        try:
            out = subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError(
                "CMake must be installed to build the following extensions: " +
                ", ".join(e.name for e in self.extensions))

        version = re.search(r'version\s+(\d+)\.(\d+)', out.decode())
        if not version:
            raise RuntimeError('Could not determine the CMake version')
        if tuple(map(int, version.groups())) < (3, 18):
            raise RuntimeError('CMake >= 3.18 is required')

        for ext in self.extensions:
            self.build_extension(ext)

    def build_extension(self, ext):
        extdir = os.path.abspath(
            os.path.dirname(self.get_ext_fullpath(ext.name)))

        library_name = runtime_library_name()
        library_source = os.path.join(ext.sourcedir, 'cppsrc', 'lib', library_name)
        if not os.path.isfile(library_source):
            raise RuntimeError('Required SpinQInterface library is missing: ' + library_source)

        cmake_args = ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                      '-DPYTHON_EXECUTABLE=' + sys.executable]

        cfg = 'Debug' if self.debug else 'Release'
        build_args = ['--config', cfg, '--parallel', '2']

        # Single-config generators (including Ninja) choose the configuration
        # here; multi-config generators use --config at build time.
        cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
        generator = os.environ.get('CMAKE_GENERATOR')
        if platform.system() == "Windows":
            generator = cmake_generator(self.build_temp)
        if generator:
            # Explicitly use the selected generator for this build.
            cmake_args += ['-G', generator]

        if platform.system() == "Windows":
            cmake_args += ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}'.format(
                cfg.upper(),
                extdir)]
            if generator.startswith('Visual Studio') and sys.maxsize > 2**32:
                cmake_args += ['-A', 'x64']

        env = pybind11_build_env()
        env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(
            env.get('CXXFLAGS', ''),
            self.distribution.get_version())
        if not os.path.exists(self.build_temp):
            os.makedirs(self.build_temp)
        subprocess.check_call(['cmake', ext.sourcedir] + cmake_args,
                              cwd=self.build_temp, env=env)
        subprocess.check_call(['cmake', '--build', '.'] + build_args,
                              cwd=self.build_temp, env=env)

        # install, bdist_egg and bdist_wheel all consume this build directory.
        # A sibling library also supports build_ext --inplace without moving sources.
        self.mkpath(extdir)
        self.copy_file(library_source, os.path.join(extdir, library_name))
        if platform.system() == 'Darwin':
            self._fix_macos_library_path(ext, library_name)

    def _fix_macos_library_path(self, ext, library_name):
        """Relocate the dependency even if the vendor dylib has an absolute ID."""
        extension_path = os.path.abspath(self.get_ext_fullpath(ext.name))
        dependencies = subprocess.check_output(
            ['otool', '-L', extension_path], universal_newlines=True)
        target = '@loader_path/' + library_name
        changed = False
        for line in dependencies.splitlines()[1:]:
            dependency = line.strip().split(' (', 1)[0]
            if dependency.rsplit('/', 1)[-1] == library_name and dependency != target:
                subprocess.check_call([
                    'install_name_tool', '-change', dependency, target, extension_path])
                changed = True
        if changed:
            # Editing a Mach-O load command invalidates its existing signature.
            subprocess.check_call(['codesign', '--force', '--sign', '-', extension_path])


setup(
    name="spinqit",
    version="0.3.0",
    description="SpinQ Quantum Software Development Kit",
    packages=find_packages(),
    classifiers=[
        'Development Status :: 4 - Beta',
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS"
    ],
    ext_modules=[CMakeExtension('spinqit.spinq_backends')],
    setup_requires=['pybind11>=2.9.2'],
    install_requires=['numpy<2.0.0', 'scipy', 'scikit-learn', 'torch', 'autograd==1.5.0', 'psutil', 'retworkx', 'python-igraph==0.9.10', 'pybind11>=2.9.2', 'antlr4-python3-runtime==4.9.2', 'python-constraint', 'requests', 'matplotlib>=3.5', 'pycryptodome==3.11.0', 'autoray==0.6.1', 'noisyopt==0.2.2', 'sympy', 'zerorpc'],
    python_requires='>=3.8',
    cmdclass=dict(build_ext=CMakeBuild),
    package_data={'spinqit': ['compiler/qasm/include/qelib1.inc']},
    zip_safe=False
)
