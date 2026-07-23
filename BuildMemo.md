## Compile memo

Compilation has been tested on these OS.

- Windows 10 x86_64 Intel(R) Core(TM) i5-10400F
- Mac Mojave 10.14.8, Intel Core i5
- Mac Monterey 13.4, Apple M2

### Install Python
If you prefer to install Anaconda, please make sure to download the correct version for your OS and CPU.

### Install CMake

Download and install CMake https://cmake.org/download/

CMake 3.18 or newer is required to compile the native extension.

Remember to add CMake to your path.

```
export CMAKE_HOME=/Users/spinq/Desktop/CMake.app/Contents/bin
export PATH=$PATH:$CMAKE_HOME
```

### Compile SpinQSimulator

Request a copy of SpinQSimulator, and build it:

```
mkdir build && cd build
cmake ..
make
```

Put compiled library into `spinqit/cppsrc/lib`

PS: If it is a Mac env, you probably wants to rename the library

### Compile igraph library

Download src code https://igraph.org/c/

To compile a static library, run:

```
mkdir build && cd build
cmake ..
cmake --build .
```

To compile a dynamical library, run:

```
mkdir build && cd build
cmake -DBUILD_SHARED_LIBS=ON ..
cmake --build .
```

Compiled library can be found under `build/src`, put it into `spinqit/cppsrc/lib`

PS: For Mac, if you use a static library, its name should be `libigraph.a `, and can be renamed. If you use a dynamical library, its name should be `libigraph.0.dylib`, and cannot be renamed (otherwise source cannot be found when running python scripts)

### Compile spinqit

Pull this repo

Install required packages for spinqit by `requirement.txt`. This will help avoiding stucks while installing or packing spinqit

```
pip install -r requirements.txt
```

If pulling offical images are slow, try to change image sources

```
pip install  -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

Also, the full `torch` library can be pretty large, you can use command `pip install torch==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu` to install the cpu-only version of it

Check if you have all prerequisites. Make sure there is a `igraph` library and a `simulator-core` library that fits your OS

`spinqit/cppsrc/lib` should have the following sources：

```
cppsrc/lib/
├── SpinQInterface.dll
├── SpinQInterface.exp
├── SpinQInterface.lib
├── igraph.lib                         # igraph library for Windows
├── libigraph.a                        # igraph library for Linux
├── libsimulator-core.so               # simulator-core library for Linux
├── mac_arm64
│   ├── libigraph.a                    # igraph library for Mac arm64 (M1 chip)
│   └── libsimulator-core.dylib        # simulator-core library for Mac arm64 (M1 chip)
├── mac_x86_64
│   ├── libigraph.a                    # igraph library for Mac x86_64 (Intel chip)
│   └── libsimulator-core.dylib        # simulator-core library for Mac x86_64 (Intel chip)
└── simulator-core.lib                 # simulator-core library for Windows
```

Then install or build a wheel. These commands use the active Python interpreter and install the build-only dependencies declared in `pyproject.toml` in an isolated environment.

```
python -m pip install .
python -m pip wheel --no-deps .
```

### Issues

#### 1

If you have multiple envs, or you are using a virtual env, you may failed to find python library

```
CMake Error at /Users/spinq/Desktop/CMake.app/Contents/share/cmake-3.22/Modules/FindPackageHandleStandardArgs.cmake:230 (message):
  Could NOT find PythonLibs (missing: PYTHON_LIBRARIES PYTHON_INCLUDE_DIRS)
Call Stack (most recent call first):
  /Users/spinq/Desktop/CMake.app/Contents/share/cmake-3.22/Modules/FindPackageHandleStandardArgs.cmake:594 (_FPHSA_FAILURE_MESSAGE)
```

Use `python -m pip install .` from the intended environment. The build passes that interpreter and the isolated `pybind11` CMake directory explicitly; manual edits to `setup.py` should not be necessary.

#### 2

May occur this cannot find `Python.h` error when `pip install <spinqit_package>` or `python setup.py install`

```
/Users/spinq/Desktop/spinqit/build/spinqit/cppsrc/basic_simulator/include/basic_simulator.h:27:10: fatal error: 'Python.h' file not found
#include <Python.h>
         ^~~~~~~~~~
```

To fix this error, add an environment variable `CPLUS_INCLUDE_PATH`

```
export CPLUS_INCLUDE_PATH=/Users/spinq/anaconda3/envs/python39/include/python3.9
```

#### 3

May occur this when `pip install <spinqit_package>` or `python setup.py install` on Mac

```
ERROR: Could not install packages due to an OSError: [Errno 13] Permission denied: '/usr/local/spinqit'
Consider using the `--user` option or check the permissions.
```

Check premission, use `sudo` or `--user` for installation
