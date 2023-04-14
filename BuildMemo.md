## Compile memo

Compilation has been tested on these OS.

- Windows 10 x86_64 Intel(R) Core(TM) i5-10400F
- Mac Mojave 10.14.8, Intel Core i5
- Mac Monterey 13.4, Apple M2

### Install Python
If you prefer to install Anaconda, please make sure to download the correct version for your OS and CPU.

### Install CMake

Download and install CMake https://cmake.org/download/

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

If pulling offical images are slow, try to change image sources

```
pip install -r requirements.txt
```

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

Then install or pack the package

```
python setup.py install  # install at local
python setup.py bdist_wheel  # pack to a binary wheel
python setup.py sdist  # pack to a tar.gz of src
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

To fix this, you need to add `PYTHON_INCLUDE_DIR` and `PYTHON_LIBRARY` at line 56 of `setup.py`

```python
cmake_args = [
    '-DPYTHON_INCLUDE_DIR=/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.8/include/python3.8',
    '-DPYTHON_LIBRARY=/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.8/lib/libpython3.8.dylib',
    '-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
    '-DPYTHON_EXECUTABLE=' + sys.executable
]
```

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