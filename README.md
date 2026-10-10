# SpinQit

SpinQit is the quantum software development kit from SpinQ Technology Co., Ltd.

## Installation and Documentation

- SpinQit is available on Windows, Linux and MacOS. This package has been tested on Ubuntu 20.04 & 22.04 (x86_64), Windows 10 & 11 (x86_64), macOS Ventura 13.0 (M1 & x86_64).
- SpinQit requires Python 3.9, 3.10 or 3.11.  This package has been tested with Python 3.9.25, 3.10.20 and 3.11.16.

SpinQit can be installed using the following command:
```python
pip install spinqit
```

To build from the source on Github, you need a C/C++ compiler and CMake in addition. We do not recommend this way unless you are very familiar with the tools.

Please find the documentation in doc/GettingStarted.md. An online version is available at [https://doc.spinq.com/doc/spinqit/index.html](https://doc.spinq.com/doc/spinqit/index.html).

## Hello Example

The following example is a simple quantum program using SpinQit Python syntax. You can run it as a Python script.
```python
from spinqit import get_basic_simulator, get_compiler, Circuit, BasicSimulatorConfig
from spinqit import H, CX, Rx
from math import pi

# Write the program
circ = Circuit()
q = circ.allocateQubits(2)
circ << (Rx, q[0], pi)
circ << (H, q[1])
circ << (CX, (q[0], q[1]))

# Choose the compiler and backend
comp = get_compiler("native")
engine = get_basic_simulator()

# Compile
optimization_level = 0
exe = comp.compile(circ, optimization_level)

# Run
config = BasicSimulatorConfig()
config.configure_shots(1024)
result = engine.execute(exe, config)

print(result.counts)
```

Output:
```
{'10': 512, '11': 512}
```

There are three steps in a SpinQit program. 

1. Write the program. The example above shows how to allocate qubits and apply quantum gates to the qubits.
2. Generate an intermediate representation of the program by compiling it with the appropriate compiler. 
3. Run the code using your preferred backend. The example above uses the basic classical simulator.

