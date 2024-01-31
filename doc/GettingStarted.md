# Basics
## Requirements

- SpinQit is available on Windows, Linux and MacOS. Only the **Windows** version can use a local quantum computer as a backend. This package has been tested on Ubuntu 20.04 & 22.04 (x86_64), Windows 10 (x86_64), MacOS Ventura 13.0 (M1, M2) and MacOS Mojave 10.14.6 (x86_64).
- SpinQit requires Python 3.8+.  This package has been tested with Python 3.8.13 and 3.9.12.
- We suggest you use Anaconda to set up your Python environment. Please refer to [https://docs.anaconda.com/anaconda/](https://docs.anaconda.com/anaconda/) about how to install and use a conda environment. On Windows, we recommend adding Anaconda to your PATH environment viarable to avoid unnecessary troubles.
## Installation
SpinQit can be installed using the following command:
```python
pip install spinqit
```

To build from the source on Github, you need a C/C++ compiler and CMake in addition. We do not recommend this way unless you are very familiar with the tools.
## First Example
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

More details about the syntaxes, compilers and backends will be introduced in the next section.

# Programming

## Syntax
SpinQit supports three types of programming syntaxes:  native SpinQit Python syntax, [OpenQASM 2.0](https://arxiv.org/abs/1707.03429) syntax, and [IBM Qiskit](https://qiskit.org/) Python syntax. 

### SpinQit Python

SpinQit allows users to define arbitrary quantum circuits. The basic concepts in SpinQit Python syntax are as follows. 

**Circuit**: In SpinQit, each quantum program is a Circuit instance.

**Quantum register**: A quantum register has a certain number of qubits, and must be allocated by a circuit using allocateQubits. A qubit is represented by the register name and its index. 

**Classical register**: A classical register has a certain number of classical bits, and must be allocated by a circuit using allocateClbits. A classical bit is represented by the register name and its index. A classical bit stores a measurement result in the quantum program, which is used by following if conditions.

**Quantum gates**: SpinQit defines 22 logic quantum gates (I, H, X, Y, Z, Rx, Ry, Rz, P, T, Td, S, Sd, CX/CNOT, CY, CZ, U, CP, SWAP, CCX, Ph, CSWAP) and two special gates (MEASURE and BARRIER). Specifically, P is the phase shift gate while Ph is the global phase gate.

**Instruction**: An instruction consists of a quantum gate, qubits, optional classical bits, and optional rotation radian for rotation gates. SpinQit uses << to add an instruction to a circuit, as shown in the example earlier.

**Custom quantum gate**: SpinQit provides a gate builder to define a custom quantum gate. The builder builds a gate based on sub-gates. Qubit indexes and optional parameter lambda are defined for each sub-gate. For example, a custom gate can be defined as follows:

```
plam = lambda params: params[0]
builder = GateBuilder(2)
builder.append(H, [0])
builder.append(CX, [0, 1])
builder.append(Rx, [0], plam)
builder.append(Rx, [0], pi)
g = builder.to_gate()
circ << (g, qreg, pi)
```

**Condition based on measurements**: In SpinQit, Circuit has a measure method to measure some of the qubits and store the result into classical bits. This method inserts a special MEASURE gate into the circuit. After the measurement, a gate can be conditionally applied, and the condition is based on the value of classical bits. Such a flow control is also known as cif. A condition in SpinQit is a tuple of a list of classical bits, a comparator string ('==', '!=', '>', '>=', '<', '<='), and an integer. The | operator is used to add a condition to an instruction. The usage will be like 
```
circ = Circuit()
q = circ.allocateQubits(2)
c = circ.allocateClbits(2)
circ << (H, q[0])
circ << (X, q[1])
circ.measure(q[0], c[0])
circ << (H, q[1]) | (c, '==', 0)
```

The MEASURE gate cannot be used in a custom gate or used with cif. Currently, this feature can only be executed by the basic classical simulator.


### OpenQASM 2.0
SpinQit supports OpenQASM 2.0. The basic gates allowed in SpinQit include id, x, y, z, h, rx, ry, rz, t, tdg, s, sdg, p, cx, cy, cz, swap, ccx, u, U, CX, measure, and barrier. Other standard gates in OpenQASM can be called by including "qelib1.inc" which is provided by SpinQit and exactly the same with the library file in OpenQASM.

```
OPENQASM 2.0;
include "qelib1.inc";

gate bell a,b
{
h a;
cx a,b;
}

qreg q[2];
creg c[2];

h q[0];
cx q[0],q[1];
bell q[0],q[1];
```
### IBM Qiskit
SpinQit also supports IBM Qiskit Python interface. The version SpinQit supports is qiskit-0.31.0 (qiskit-terra-0.18.3). We include the qiskit.circuit package and some related packages into SpinQit. Therefore, you can construct a Qiskit QuantumCircuit instance and run it with SpinQit, even without installing Qiskit. Particularly, SpinQit has supported QFT, QPE, and Grover primitives in Qiskit (in spinqit.qiskit.circuit.library) so that you can build up your quantum algorithms based on these primitives. Nevertheless, SpinQit does not include all the Qiskit code. If you want to use the qiskit.algorithm package and run the circuit on SpinQit backends, you still need to install Qiskit.

```python
from spinqit.qiskit.circuit import QuantumCircuit
qc = QuantumCircuit(2)
qc.x(0)
qc.rx(pi, 0)
qc.cx(0, 1)
```
## Compiler
Each syntax has its corresponding compiler. The get_compiler method is used to choose the compiler. The three options are “native”, “qasm”, and “qiskit”. All the compilers have a compile method with two arguments, and the second argument is always the optimization level, but the first argument is different. 

The native compiler takes a Circuit instance in SpinQit as the first argument. 
```python
circ = Circuit()
...
comp = get_compiler("native")
exe = comp.compile(circ, optimization_level)
```
The qasm compiler takes the path to a qasm file as the first argument. 
```python
comp = get_compiler('qasm')
exe = comp.compile("test/spinq/callee.qasm", optimization_level)
```
The qiskit compiler takes a Qiskit QuantumCircuit instance as the first argument.
```python
circ = QuantumCircuit(3)
...
comp = get_compiler("qiskit")
exe1 = comp.compile(circ, optimization_level)
```

### Compilation Optimization

SpinQit provides basic circuit optimization features. There are four optimization levels in SpinQit compilers, each associated with distinct combinations of optimization algorithms. 

**Level 0** means no optimization algorithm is applied. 

**Level 1** contains two passes and two algorithms are applied in order. The first algorithm cancels consecutive redundant gates. Certain gates can be removed when they are repeated an even number of times on the same qubit(s) without affecting the final result. The gates that satisfy this property include the Pauli-X gate (X gate), Hadamard gate (H gate), and CNOT gate (CX gate). This algorithm will remove these redundant gates from the circuit. Similarly, if a number of rotation gates rotates the same qubit around the same axis, this algorithm will combine them into one rotation gate. The second algorithm collapses more than 3 consecutive single-qubit gates on the same qubit into several basic gates. The algorithm calculates the matrix that represents the consecutive gates and decomposes the matrix to basic gates. Currently, SpinQit uses ZYZ decomposition. 

**Level 2** contains the two algorithms in Level 1 and then applies a third algorithm. The third algorithm collapses more than 6 consecutive two-qubit gates on the same two qubits into certain Ry, Rz, and CX gates.  The algorithm also calculates the matrix that represents the original gates and then decomposes the matrix.

**Level 3** first cancels redundant gates and then applies two optimization algorithms based on quantum state analysis introduced in [https://arxiv.org/abs/2012.07711v1](https://arxiv.org/abs/2012.07711v1). The two algorithms are reported to perform better than the most aggressive optimization level in Qiskit. After the two algorithm, the collapsing single-qubit gates and collapsing two-qubit gates passes are applied.

The optimization features in SpinQit are still experimental. More algorithms are will be added in the future. Please let us know if you find any issue.

## Backend
SpinQit has five different types of backends: a basic classical simulator, a simulator based on PyTorch, local quantum computers from SpinQ, the SpinQ cloud, and a QASM-based backend. 

### Basic Simulator

The basic simulator is a local classical simulator based on CPU. It supports measure and cif in the quantum circuit, but does not support autograd and parallel processing. 

The code below shows how to use the basic classical simulator to run a quantum program. The configuration methods of BasicSimulatorConfig are also listed below.
```python
engine = get_basic_simulator()
config = BasicSimulatorConfig()
config.configure_shots(1024)
result = engine.execute(exe, config)
```

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.backend.BasicSimulatorConfig</span>
    </dt>
</dl>


|Method|Description|
|---|---|
|configure_shots(shots)| Configure the total number of shots so that the count of each possible binary reading is calculated in the result. |
|configure_measure_qubits(mqubits)|Configure the subset of qubits to measure so that only the result about these qubits will be measured.|



### Torch Simulator
SpinQit includes another simulator based on PyTorch. This torch simulator supports autograd, and executes a quantum simulation in parallel on multiple CPU cores.  

The code example shows how to use the torch simulator. The configuration methods of TorchSimulatorConfig are also listed below.
```python
engine = get_torch_simulator()
config = TorchSimulatorConfig()
config.configure_num_thread(4)
result = engine.execute(exe, config)
```

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.backend.TorchSimulatorConfig</span>
    </dt>
</dl>

|Method|Description|
|---|---|
|configure_shots(shots)| Configure the total number of shots so that the count of each possible binary reading is calculated in the result. |
|configure_measure_qubits(mqubits)|Configure the subset of qubits to measure so that only the result about these qubits will be measured. |
|configure_num_thread(n_threads)|Configure the number of threads to run the simulation. |

### Local Quantum Computer
To use a local quantum computer from SpinQ, you first need to get the network information and register an account on the machine. Here Triangulum GUI is used as an example. For instructions on how to use other models, please contact our sales team.

![TriangulumIP.png](TriangulumIP.png)

![TriangulumRegister.png](TriangulumRegister.png)

The code example shows how to use a local quantum computer backend in SpinQit. The configuration methods of NMRConfig are listed below.
```python
engine = get_nmr()
config = NMRConfig()
config.configure_ip("192.168.137.1")
config.configure_port(55444)
config.configure_account("user9", "123456")
config.configure_task("task2", "Bell")
result = engine.execute(exe, config)
```

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.backend.NMRConfig</span>
    </dt>
</dl>

|Method|Description|
|---|---|
|configure_shots(shots)| Configure the total number of shots so that the count of each possible binary reading is calculated in the result. |
|configure_ip(addr)| Configure the ip address of the quantum computer. |
|configure_port(port)| Configure the port number of the quantum computer. |
|configure_account(username, password)| Configure the username and password that registered on the quantum computer. |
|configure_task(task_name, task_desc)| Configure the task name and description. |


### Cloud
In order to use the SpinQ cloud, you have to first register and add a public SSH key on [https://cloud.spinq.cn.](https://cloud.spinq.cn.) Please refer to the documentation online about the SpinQ cloud [https://cloud.spinq.cn/#/docs.](https://cloud.spinq.cn/#/docs.) Username and key information are required to use the cloud backend. 
![SSH.PNG](SSH.PNG)
SpinQ provides multiple platforms with different number of qubits on the SpinQ cloud. The cloud backend has a get_platform method, and this method can provide a platform instance from “gemini_vp”, “triangulum_vp”, “superconductor_vp”. These platforms have 2, 3 and 8 qubits respectively and support only quantum programs with fewer qubits. The result from the cloud backend contains only a probability distribution. The data type of the result is a dictionary. The keys in the dictionary are binary measurements. The values in the dictionary are the corresponding probabilities.


The following example shows how to use the cloud backend and login using your SSH key.

```python
username = "username"
message = username.encode(encoding="utf-8")

with open("\path\to\keyfile") as f:
    key = f.read()

rsakey = RSA.importKey(key)
signer = Signature_pkcs1_v1_5.new(rsakey)
digest = SHA256.new()
digest.update(message)
printable = digest.hexdigest()
sign = signer.sign(digest)
signature = base64.b64encode(sign)
signStr = str(signature, encoding = "utf-8")

# login
backend = get_spinq_cloud(username, signStr)

# choose a platform
gemini = backend.get_platform("gemini_vp")
print("gemini_vp has " + str(gemini.machine_count) + " active machines.")

if gemini.available():
    comp = get_compiler("native")
    circ = Circuit()
    ...
    ir = comp.compile(circ, 0)
    newTask = backend.submit_task("gemini_vp", ir, "spinqittask1")
    res = newTask.get_result()
else:
    print("No machine available for this platform.")
```

### QASM

SpinQit can convert its intermediate representation to OpenQASM codes in the form of string so that any third-party platform which suports OpenQASM can be used to execute codes written in SpinQit. The QASM backend is initialized using a handle function which can run OpenQASM codes. The result format of this backend depends on the actual execution platform. It would be better to convert the third-party results to the result formats of SpinQit in the handle. SpinQit provides a QiskitQasmResult class to process Qiskit results. 

The following example shows how to define a handle for the QASM backend to use Qiskit 0.31.0 to execute a quantum circuit.

```python
from qiskit import QuantumCircuit
from qiskit import execute
from qiskit import Aer
from spinqit import get_qasm_backend, QasmConfig, QiskitQasmResult

def qiskit_fn(qasm, shots=1024, *args, **kwargs):
    qc = QuantumCircuit.from_qasm_str(qasm)
    simulator = Aer.get_backend('statevector_simulator')
    result = execute(qc, simulator, *args, **kwargs).result()
    print(result.get_statevector())
    qiskit_result = QiskitQasmResult()
    qiskit_result.set_result(result.get_statevector(), shots)
    return qiskit_result

...

exe = compiler.compile(circuit, 0)
config = QasmConfig()
engine = get_qasm_backend(qiskit_fn)
states = engine.execute(exe, config).states
```


 The configuration methods of QasmConfig are listed below.

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.backend.QasmConfig</span>
    </dt>
</dl>

|Method|Description|
|---|---|
|configure_shots(shots)| Configure the total number of shots so that the count of each possible binary reading is calculated in the result. |
|configure_measure_qubits(mqubits)|Configure the subset of qubits to measure so that only the result about these qubits will be measured.|



## Result
SpinQit provides four types of results. First, all the backends can provide the probabilities of binary readings as follows:
```
print(result.probabilities)
{'10': 0.4999999999809753, '11': 0.4999999999809753}
```
Please notice that SpinQit uses the little endian, i.e., the first bit in the result binary string corresponds to the first qubit in the quantum circuit. 

Second,  the count of each possible binary reading can be found in the result except when the cloud backend is used. The total number of shots is configured otherwise 1024 will be used by default. 
```
print(result.counts)
{'10': 512, '11': 512}
```
Third, with the simulators, a random binary reading can be obtained from the result according to the probabilities via a get_random_reading method. 
```
print(result.get_random_reading())
11
```
Fourth, the two simulator backends can provide the state vector of all the qubits when there is no measure gate or conditional gate based on the value of a classical register.
```
print(result.states)
[(1.37812710729329e-10+0j), (1.37812710729329e-10+0j), -0.7071067811865476j, -0.7071067811865476j]
```

The following table shows the result formats supported by each backend.

||Basic Simulator|Torch Simulator|Local Quantum Computer|Cloud|QASM Backend|
|---|---|---|---|---|---|
|Probabilities|Y|Y|Y|Y|Y|
|Counts|Y|Y|Y|N|Y|
|States|Y|Y|N|N|Y|
|Random Reading|Y|Y|N|N|Y|


## Library

SpinQit provides useful APIs for developers to use in their own quantum programs. Users can define custom quantum gates, build new quantum algorithms, and invoke existing algorithms. This section introduces the APIs in SpinQit.

### GateBuilders

A gate builder is used to define a custom gate. The developer needs to call the to_gate method of a builder to get the gate. SpinQit also provides several specific gate builders:


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.model.RepeatBuilder</span>
    </dt>
    <dd>
        <p>Build a gate which applies the same subgate on multiple qubits.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(g, repeat, param_lambda)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a RepeatBuilder instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>g</strong> – Gate, the gate to repeat</p>
                    <p><strong>repeat</strong> – int, how many qubits to apply g</p>
                    <p><strong>param_lambda</strong> - float or Callable, optional parameters of gate, and None by default</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A GateBuilder instance </p>
                    </dd>
                    <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>h4 = RepeatBuilder(H, 4).to_gate() </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.model.InverseBuilder</span>
    </dt>
    <dd>
        <p>Build the inverse gate of a given gate.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(gate)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a InverseBuilder instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>gate</strong> – Gate, the gate to inverse</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A GateBuilder instance </p>
                    </dd>
                    <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>x_inv = InverseBuilder(X).to_gate() </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.model.MultiControlPhaseGateBuilder</span>
    </dt>
    <dd>
        <p>Build a multi-controlled phase gate or a multi-controlled Rz gate.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(ctrl_qubit_num)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a MultiControlPhaseGateBuilder instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>ctrl_qubit_num</strong> – int, the number of control qubits. Please notice that the total number of qubits for the generated gate is the number of control qubits plus one.</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A GateBuilder instance </p>
                    </dd>
                    <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>c3p = MultiControlPhaseGateBuilder(3).to_gate() </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.model.Z_IsingGateBuilder</span>
    </dt>
    <dd>
        <p>Build a Z-basis parameteric Ising coupling gate.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(qubit_num, name)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a Z_IsingGateBuilder instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qubit_num</strong> – int, the number of qubits interacted</p>
                    <p><strong>name</strong> - str, name of the gate, 'Z_Ising' by default</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A GateBuilder instance </p>
                    </dd>
                    <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>rzz = Z_IsingGateBuilder(2).to_gate() </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.model.X_IsingGateBuilder</span>
    </dt>
    <dd>
        <p>Build a X-basis parameteric Ising coupling gate.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(qubit_num, name)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a X_IsingGateBuilder instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qubit_num</strong> – int, the number of qubits interacted</p>
                    <p><strong>name</strong> - str, name of the gate, 'X_Ising' by default</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A GateBuilder instance </p>
                    </dd>
                    <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>rxx = X_IsingGateBuilder(2).to_gate() </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.model.Y_IsingGateBuilder</span>
    </dt>
    <dd>
        <p>Build a Y-basis parameteric Ising coupling gate.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(qubit_num, name)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a Y_IsingGateBuilder instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qubit_num</strong> – int, the number of qubits interacted</p>
                    <p><strong>name</strong> - str, name of the gate, 'Y_Ising' by default</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A GateBuilder instance </p>
                    </dd>
                    <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>ryy = Y_IsingGateBuilder(2).to_gate() </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.primitive.MultiControlledGateBuilder</span>
    </dt>
    <dd>
        <p>Build a multi-controlled single-qubit gate.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(ctrl_num, gate, params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a MultiControlledGateBuilder instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>ctrl_num</strong> – int, the number of control qubits</p>
                    <p><strong>gate</strong> - Gate, numpy.ndarray, or list, the single-qubit gate applied on the target qubit which could be a Gate instance in SpinQit or a unitary matrix of ndarray or list type </p>
                    <p><strong>params</strong> – List, the parameters for the Gate instance, None by default</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A GateBuilder instance </p>
                    </dd>
                    <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>mcz = MultiControlledGateBuilder(3, Z) </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.primitive.UniformlyControlledGateBuilder</span>
    </dt>
    <dd>
        <p>Build a uniformly controlled single-qubit gate.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(ctrl_num, gate, params, up_to_diag, add_phase)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a UniformlyControlledGateBuilder instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>ctrl_num</strong> – int, the number of control qubits</p>
                    <p><strong>gate</strong> - Gate, numpy.ndarray, or list, the single-qubit gate applied on the target qubit which could be a Gate instance in SpinQit or a unitary matrix of ndarray or list type </p>
                    <p><strong>params</strong> – List, the parameters for the Gate instance, None by default</p>
                    <p><strong>up_to_diag</strong> – bool, whether to implement the uniformly controlled gate up to diagnoal gates, False by default</p>
                    <p><strong>add_phase</strong> – bool, whether to add the global phase, True by default</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A GateBuilder instance </p>
                    </dd>
                    <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>ucz = UniformlyControlledGateBuilder(3, Rz, [np.pi/2]) </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>



### Primitives

The primitives in this section are subroutines used frequently in quantum programming. These primitives generate instructions or a composite gate to finish the quantum operations. Before generating the instructions, a Circuit instance must be created and qubits must be allocated.


<dl>
    <dt class="method-distract">
        <span class="method-name">spinqit.primitive.generate_power_gate</span>
        <em class="method-param">(gate, exponent, qubits, params, control, control_bit)</em>
    </dt>
</dl>

Generates the instructions that represent the power of a given gate. The power of the argument “gate” is decomposed to a group of subgates in this function. When “control” is True, the instructions represent the controlled power gate and the argument “control_bit” must be set. 

<dl>
    <dd>
        <dl class="field-list simple">
            <dt class="field-odd">Parameters</dt>
            <dd class="field-odd"><p><strong>gate</strong> - Gate, the base gate</p>
            <p><strong>exponent</strong> - int or float, the exponent</p>
            <p><strong>qubits</strong> - List,  where to apply the power of gate</p>
            <p><strong>params</strong> - List, optional parameters of gate, and the default value is []</p>
            <p><strong>control</strong> - bool,  whether to generate the controlled power gate, and the default value is False</p>
            <p><strong>control_bit</strong> - int, the control qubit, by default it is None</p>
            </dd>
            <dt class="field-even">Returns</dt>
            <dd class="field-even"><p>The instructions that represent the power of a given gate. </p>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.primitive.AmplitudeAmplification</span>
    </dt>
    <dd>
        <p>Generates the instructions for amplitude amplification.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(flip, flip_qubits, flip_params, state_operator, state_qubits, state_params, reflection_qubits)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create an AmplitudeAmplification instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>flip</strong> - Gate, the gate to flip the phase of the target</p>
                    <p><strong>flip_qubits</strong> - List,  the qubits to apply the flip gate</p>
                    <p><strong>flip_params</strong> - List, the optional parameters in the flip gate </p>
                    <p><strong>state_operator</strong> - Gate, the gate to prepare the state that represents the search space, by default using uniform superposition </p>
                    <p><strong>state_qubits</strong> - List, the qubits to prepare the state </p>
                    <p><strong>state_params</strong> - List, the optional parameters in the state operator gate </p>
                    <p><strong>reflection_qubits</strong> - List, the qubits to apply the reflect operation </p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>An AmplitudeAmplification instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">build</span>
                <em class="method-param">( )</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Return the instructions for amplitude amplification.</p>
                <dl class="field-list simple">
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A list of instructions for amplitude amplification</p>
                    </dd>
                     <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>We provide an example of the Grover algorithm that uses amplitude amplification in example/grover_example.py. </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.primitive.QFT</span>
    </dt>
    <dd>
        <p>Generates a gate for quantum Fourier transform or inverse quantum Fourier transform.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(qubit_num)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a QFT instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qubit_num</strong> - int, the number of qubits to apply QFT/inverse QFT</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A QFT instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">build</span>
                <em class="method-param">( )</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Build a gate for QFT.</p>
                <dl class="field-list simple">
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A gate to do quantum Fourier transform</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">inverse</span>
                <em class="method-param">( )</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Build a gate for inverse QFT.</p>
                <dl class="field-list simple">
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A gate to do inverse quantum Fourier transform</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.primitive.PhaseEstimation</span>
    </dt>
    <dd>
        <p>Generates instructions that estimate the eigenvalue of a given gate corresponding to a specific eigenvector.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(unitary, state_qubits, output_qubits, params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a PhaseEstimation instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>unitary</strong> - Gate, the gate to apply quantum phase estimation</p>
                    <p><strong>state_qubits</strong> - List, the qubits that encode the eigenvector</p>
                    <p><strong>output_qubits</strong> - List, the qubits that output the estimation result</p>
                    <p><strong>params</strong> - List, optional parameters of the input gate, and [] by default</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A PhaseEstimation instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">build</span>
                <em class="method-param">( )</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Generate instructions for QPE.</p>
                <dl class="field-list simple">
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>Instructions to do quantum phase estimation</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">inverse</span>
                <em class="method-param">( )</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Generate instructions for inverse QPE.</p>
                <dl class="field-list simple">
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>Instructions to do inverse quantum phase estimation</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>



<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.primitive.AmplitudeEstimation</span>
    </dt>
    <dd>
        <p>Given an operator U that U|0> = &radic;1-a |&Psi;<sub>0</sub>> + &radic;a |&Psi;<sub>1</sub>>, Generates instructions that estimate the amplitude a of the state |&Psi;<sub>1</sub>>.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(counting_num, searching_num, prep, oracle, prep_params, oracle_params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create an AmplitudeEstimation instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>counting_num</strong> - int, the number of qubits to read out the estimation</p>
                    <p><strong>searching_num</strong> - int, the number of qubits to apply the oracle</p>
                    <p><strong>prep</strong> - Gate, the gate to prepare the states</p>
                    <p><strong>oracle</strong> - Gate, the gate to </p>
                    <p><strong>prep_params</strong> - List, [] by default, the optional parameters in the prep gate </p>
                    <p><strong>oracle_params</strong> - List, [] by default, the optional parameters in the oracle gate </p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A PhaseEstimation instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">build</span>
                <em class="method-param">( )</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Generate instructions for QAE.</p>
                <dl class="field-list simple">
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>Instructions to do quantum amplitude estimation</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>



### Algorithms

SpinQit provides APIs for multiple quantum algorithms so that users can run them directly. We provide example codes to show how to use these APIs.


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.HHL</span>
    </dt>
    <dd>
        <p> Harrow-Hassidim-Lloyd (HHL) quantum algorithm is used to solve a system of linear equations.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(mat_A, vec_b)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Initialize an HHL solver.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>mat_A</strong> - np.ndarray, the coefficient matrix</p>
                    <p><strong>vec_b</strong> - np.ndarray, the right side constant vector</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>An HHL instance for a specific system of linear equations</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">run</span>
                <em class="method-param">(backend, config)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Run the solver.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>backend</strong> - BaseBackend, the backend instance to execute the algorithm</p>
                    <p><strong>config</strong> - Config, the configuration for the backend</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>None</p>
                    </dd>
                     <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>We provide an example of HHL in example/hhl_example.py </p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">get_measurements</span>
                <em class="method-param">( )</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Get the probabilities after running the solver.</p>
                <dl class="field-list simple">
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A dictionary of the probabilities of different measurements from the solver</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">get_state</span>
                <em class="method-param">( )</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Get the state vector after running the solver, working only with simulator backends.</p>
                <dl class="field-list simple">
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A dictionary of the probabilities of different measurements from the solver</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.VQE</span>
    </dt>
    <dd>
        <p> VQE is short for variational quantum eigensolver, which finds the minimum eigenvalue of a Hermitian matrix H. VQE uses a parameterized ansatz to implement the variational principle. When H describes the Hamiltonian of a system, VQE can obtain the ground state energy of the Hamiltonian.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(qubit_num, depth, hamiltonian, ansatz, optimizer)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Initialize a VQE solver.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qubit_num</strong> - int, the qubit number in the ansatz</p>
                    <p><strong>depth</strong> - int, how many times to repeat the ansatz circuit</p>
                    <p><strong>hamiltonian</strong> - scipy.sparse.csr_matrix or List, the input Hamiltonian which can be a matrix or described by its Pauli decomposition, i.e., a list of (Pauli string, coefficient) pairs</p>
                    <p><strong>ansatz</strong> - Circuit, the ansatz circuit, and a hardware efficient ansatz is used when this parameter is None</p>
                    <p><strong>optimizer</strong> - Optimizer, the optimizer used to optimize the variational parameters</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A VQE instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">run</span>
                <em class="method-param">(mode, grad_method)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Run the solver.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>mode</strong> - str, the backend mode, 'spinq' or 'torch', corresponding to the basic simulator and the pytorch simulator respectively</p>
                    <p><strong>grad_method</strong> - str, the method to calculate the gradients, 'param_shift' and 'adjoint_differentiation' for the 'spinq' mode and 'backprop' for the 'torch' mode</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A list of loss values</p>
                    </dd>
                     <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>We provide an example of VQE in example/vqe_h2_example.py </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.QAOA</span>
    </dt>
    <dd>
        <p> Quantum Approximate Optimization Algorithm (QAOA) is a variational algorithm to solve combinatorial optimization problems. </p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(qubit_num, depth, problem, mixer, optimizer)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Initialize a QAOA solver.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qubit_num</strong> - int, the qubit number in the ansatz</p>
                    <p><strong>depth</strong> - int, how many times to repeat the problem ansatz and the mixer ansatz</p>
                    <p><strong>hamiltonian</strong> - scipy.sparse.csr_matrix or List or Circuit, the problem Hamiltonian which can be a matrix, or described by its Pauli decomposition, i.e., a list of (Pauli string, coefficient) pairs, or a parameterized quantum circuit</p>
                    <p><strong>mixer</strong> - Circuit, the mixer circuit, and a default Rx ansatz is used when this parameter is None</p>
                    <p><strong>optimizer</strong> - Optimizer, the optimizer used to optimize the variational parameters</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A QAOA instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">run</span>
                <em class="method-param">(mode, grad_method)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Run the solver.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>mode</strong> - str, the backend mode, 'spinq' or 'torch', corresponding to the basic simulator and the pytorch simulator respectively</p>
                    <p><strong>grad_method</strong> - str, the method to calculate the gradients, 'param_shift' and 'adjoint_differentiation' for the 'spinq' mode and 'backprop' for the 'torch' mode</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A list of loss values</p>
                    </dd>
                     <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>We provide an example of QAOA in example/qaoa_maxcut_example.py </p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">get_measurements</span>
                <em class="method-param">(backend, config)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Get the measurements of the final circuit.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>backend</strong> - BaseBackend, the backend instance to execute the algorithm </p>
                    <p><strong>config</strong> - Config, the configuration for the backend</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>Result of the execution</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.QuantumCounting</span>
    </dt>
    <dd>
        <p> The Grover algorithm is designed to find a solution to an oracle function, while the quantum counting algorithm finds out how many of these solutions there are. This algorithm is a quantum phase estimation of the Grover operator. </p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(counting_num, searching_num, prep, oracle, prep_params, oracle_params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Initialize a QuantumCounting instance for a specific problem.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>counting_num</strong> - int, the number of qubits to read out the count </p>
                    <p><strong>searching_num</strong> - int, the number of qubits to apply the oracle</p>
                    <p><strong>prep</strong> - Gate, the gate to prepare the states</p>
                    <p><strong>oracle</strong> - Gate, the oracle to count</p>
                    <p><strong>prep_params</strong> - List, [] by default, the optional parameters in the prep gate</p>
                    <p><strong>oracle_params</strong> - List, [] by default, the optional parameters in the oracle gate</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A QuantumCounting instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">run</span>
                <em class="method-param">(backend, config)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Solve the quantum counting problem.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>backend</strong> - BaseBackend, the backend instance to execute the algorithm</p>
                    <p><strong>config</strong> - Config, the configuration for the backend</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The count of targets</p>
                    </dd>
                     <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>We provide an example of quantum counting in example/quantum_counting_example.py </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>



<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.QSearching</span>
    </dt>
    <dd>
        <p> The QSearching algorithm searches for the index of the maximum or minimum value in an array. </p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(find, backend, config, seed)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Initialize a QSearching instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>find</strong> - str, 'max' or 'min' </p>
                   <p><strong>backend</strong> - BaseBackend, the backend instance to execute the algorithm</p>
                    <p><strong>config</strong> - Config, the configuration for the backend</p>
                    <p><strong>seed</strong> - None, int, float, str, bytes or bytearray, the random seed used in the algorithm </p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A QSearching instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">search</span>
                <em class="method-param">(dataset)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Search for the max or min value in the dataset.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>dataset</strong> - arraylike, the input array to search</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The index of the max or min value</p>
                    </dd>
                     <dt class="field-odd">Example</dt>
                    <dd class="field-odd"><p>We provide an example of quantum counting in example/search_max_min.py </p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


### Quantum Machine Learning


SpinQit supports quantum machine learning by providing quantum encoding methods and optimizer interfaces. In addition, SpinQit provides interfaces to integrates with classical machine learning frameworks to conduct hybrid quantum-classical machine learning. An example shows how to implement a quantum classifier using SpinQit and PyTorch in example/qnn_example.py.

#### Encoding

Currently, there are three off-the-shelf encoding functions which convert classical information into quantum states or operations. These encoding functions can be used for quantum feature maps. Users can also define their own encoding circuit.


<dl>
    <dt class="method-distract">
        <span class="method-name">spinqit.primitive.amplitude_encoding</span>
        <em class="method-param">(vector, qubits)</em>
    </dt>
</dl>

Encodes classical information into amplitudes of quantum states. The amplitude of each quantum state is associated with a specific classical value in the input vector. The normalized state vector is equal to the normalized input vector.

<dl>
    <dd>
        <dl class="field-list simple">
            <dt class="field-odd">Parameters</dt>
            <dd class="field-odd"><p><strong>vector</strong> – np.ndarray, the input classical vector</p>
            <p><strong>qubits</strong> - List, the qubits to encode the input vector</p>
            </dd>
            <dt class="field-even">Returns</dt>
            <dd class="field-even"><p>The instructions prepare quantum states to encode the given vector. </p>
            </dd>
        </dl>
    </dd>
</dl>




<dl>
    <dt class="method-distract">
        <span class="method-name">spinqit.primitive.angle_encoding</span>
        <em class="method-param">(vector, qubits, rotate_gate)</em>
    </dt>
</dl>

Encodes classical information into parameters of rotation gates. 

<dl>
    <dd>
        <dl class="field-list simple">
            <dt class="field-odd">Parameters</dt>
            <dd class="field-odd"><p><strong>vector</strong> – np.ndarray, the input classical vector</p>
            <p><strong>qubits</strong> - List, the qubits to encode the input vector</p>
            <p><strong>rotate_gate</strong> - str, the rotation gate 'rx', 'ry' or 'rz' to use, 'ry' by default </p>
            </dd>
            <dt class="field-even">Returns</dt>
            <dd class="field-even"><p>The instructions for the rotation gates. </p>
            </dd>
        </dl>
    </dd>
</dl>



<dl>
    <dt class="method-distract">
        <span class="method-name">spinqit.primitive.iqp_encoding</span>
        <em class="method-param">(vector, qubits, depth, ring_pattern)</em>
    </dt>
</dl>

Encodes classical information $x$ into $(U_Z(x)H^{\otimes n})^d \vert 0^n\rangle$. Please refer to Havlíček, Vojtěch, et al. "Supervised learning with quantum-enhanced feature spaces." for details.

<dl>
    <dd>
        <dl class="field-list simple">
            <dt class="field-odd">Parameters</dt>
            <dd class="field-odd"><p><strong>vector</strong> – np.ndarray, the input classical vector</p>
            <p><strong>qubits</strong> - List, the qubits to encode the input vector</p>
            <p><strong>depth</strong> - int, 1 by default, how many times to repeat the basic IQP circuit
            <p><strong>ring_pattern</strong> - bool, False by default, whether to apply a rzz gate to the first and last qubits
            </dd>
            <dt class="field-even">Returns</dt>
            <dd class="field-even"><p>The instructions for the instantaneous quantum polynomial circuit. </p>
            </dd>
        </dl>
    </dd>
</dl>
    





#### Optimizer

SpinQit has three native optimizers and three interfaces to use optimizers from SciPy, PyTorch and Noisyopt.


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.optimizer.ADAM</span>
    </dt>
    <dd>
        <p>Native implementation of ADAM optimizer in SpinQit.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(maxiter, tolerance, learning_rate, beta1, beta2, noise_factor, verbose)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create an ADAM optimizer instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>maxiter</strong> – int, maximum number of iterations， 1000 by default </p>
                    <p><strong>tolerance</strong> – float, tolerance for termination, 1e-4 by default </p>
                    <p><strong>learning_rate</strong> – float, the learning rate, 0.01 by default </p>
                    <p><strong>beta1</strong> – float, decay rate for the first moment of the gradient, 0.9 by default </p>
                    <p><strong>beta2</strong> – float, decay rate for the second moment of the gradient, 0.99 by default </p>
                    <p><strong>noise_factor</strong> – float, noise factor which >= 0, 1e-8 by default </p>
                    <p><strong>verbose</strong> – bool, whether to show optimization details, True by default</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>An ADAM instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">optimize</span>
                <em class="method-param">(expval_fn)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>expval_fn</strong> – ExpvalCost, the objective function based on an Hamiltonian</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The list of loss values</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.optimizer.GradientDescent</span>
    </dt>
    <dd>
        <p>Native implementation of gradient descent optimizer in SpinQit.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(maxiter, tolerance, learning_rate, verbose)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a GradientDescent optimizer instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>maxiter</strong> – int, maximum number of iterations, 1000 by default </p>
                    <p><strong>tolerance</strong> – float, tolerance for termination, 1e-6 by default</p>
                    <p><strong>learning_rate</strong> – float, the learning rate, 0.01 by default </p>
                    <p><strong>verbose</strong> – bool, whether to show optimization details, True by default </p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A GradientDescent instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">optimize</span>
                <em class="method-param">(expval_fn)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>expval_fn</strong> – ExpvalCost, the objective function based on an Hamiltonian</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The list of loss values</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.optimizer.QuantumNaturalGradient</span>
    </dt>
    <dd>
        <p>Implementation of quantum natural gradient optimizer in SpinQit</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(maxiter, tolerance, learning_rate, verbose)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a QuantumNaturalGradient optimizer instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>maxiter</strong> – int, maximum number of iterations, 1000 by default </p>
                    <p><strong>tolerance</strong> – float, tolerance for termination, 1e-6 by default </p>
                    <p><strong>learning_rate</strong> – float, the learning rate, 0.01 by default </p>
                    <p><strong>verbose</strong> – bool, whether to show optimization details, True by default </p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A QuantumNaturalGradient instance</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">optimize</span>
                <em class="method-param">(expval_fn)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>expval_fn</strong> – ExpvalCost, the objective function based on an Hamiltonian</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The list of loss values</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.optimizer.TorchOptimizer</span>
    </dt>
    <dd>
        <p>Interface to use optimizers in PyTorch, including NAdam, Adam, SGD, AdamW, Adagrad</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(maxiter, tolerance, learning_rate, verbose, optim_type, *args, **kwargs)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a TorchOptimizer instance to call optimizers in PyTorch.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>maxiter</strong> – int, maximum number of iterations, 1000 by default</p>
                    <p><strong>tolerance</strong> – float, tolerance for termination, 1e-6 by default</p>
                    <p><strong>learning_rate</strong> – float, the learning rate, 0.01 by default</p>
                    <p><strong>verbose</strong> – bool, whether to show optimization details, True by default </p>
                    <p><strong>optim_type</strong> – str, 'NAdam', 'Adam', 'SGD', 'AdamW', or 'Adagrad', and the default type is 'NAdam'</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>An interface instance that calls the optimizers in PyTorch</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">optimize</span>
                <em class="method-param">(expval_fn)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>expval_fn</strong> – ExpvalCost, the objective function based on an Hamiltonian</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The list of loss values</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>



<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.optimizer.ScipyOptimizer</span>
    </dt>
    <dd>
        <p>Interface to call optimizers in SciPy, specifically, "Nelder-Mead" and "COBYLA" </p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(maxiter, tolerance, verbose, method, **kwargs)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a ScipyOptimizer instance to call optimizers in SciPy.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>maxiter</strong> – int, maximum number of iterations, 10000 by default</p>
                    <p><strong>tolerance</strong> – float, tolerance for termination, 1e-4</p>
                    <p><strong>verbose</strong> – bool, whether to show optimization details, False by default </p>
                    <p><strong>method</strong> – str, 'Nelder-Mead' or 'COBYLA', by default 'COBYLA'</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>An interface instance that calls the optimizers in SciPy</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">optimize</span>
                <em class="method-param">(expval_fn)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>expval_fn</strong> – ExpvalCost, the objective function based on an Hamiltonian</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The list of loss values</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.algorithm.optimizer.SPSAOptimizer</span>
    </dt>
    <dd>
        <p>Interface to use the minimizeSPSA optimizer from noisyopt.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(maxiter, verbose, a, c, **kwargs)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a SPSAOptimizer instance to call the minimizeSPSA optimizer.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>maxiter</strong> – int, maximum number of iterations, 100 by default</p>
                    <p><strong>verbose</strong> – bool, whether to show optimization details, False by default </p>
                    <p><strong>a</strong> - float, scaling parameter for step size, 1.0 by default </p>
                    <p><strong>c</strong> - float, scaling parameter for evaluation step size, 1.0 by default </p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>An interface instance that calls the minimizeSPSA optimizer </p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">optimize</span>
                <em class="method-param">(expval_fn)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>expval_fn</strong> – ExpvalCost, the objective function based on an Hamiltonian</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The list of loss values</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>


## Example
### Grover Example
The Grover search algorithm uses AmplitudeAmplification to find the target specified in the oracle.

```
from spinqit import get_basic_simulator, get_compiler, Circuit, BasicSimulatorConfig
from spinqit import AmplitudeAmplification, GateBuilder, RepeatBuilder
from spinqit import H, X, Z
from spinqit.primitive import MultiControlledGateBuilder
from math import pi

circ = Circuit()
q = circ.allocateQubits(4)

hbuilder = RepeatBuilder(H, 4)
circ << (hbuilder.to_gate(), q)

# Build the oracle for 1100
oracle_builder = GateBuilder(4)
oracle_builder.append(X, [2])
oracle_builder.append(X, [3])

mcz_builder = MultiControlledGateBuilder(3, gate=Z)
oracle_builder.append(mcz_builder.to_gate(), list(range(4)))

oracle_builder.append(X, [2])
oracle_builder.append(X, [3])

grover = AmplitudeAmplification(oracle_builder.to_gate(), q)
circ.extend(grover.build())

# Set up the backend and the compiler
engine = get_basic_simulator()
comp = get_compiler("native")
optimization_level = 0
exe = comp.compile(circ, optimization_level)
config = BasicSimulatorConfig()
config.configure_shots(1024)

# Run
result = engine.execute(exe, config)
print(result.counts)
```

### HHL Example

Systems of linear equations are foundamental to various science and engineering problems, especially many machine learning algorithms. The Harrow-Hassidim-Lloyd algorithm (HHL) can be used 

```
from spinqit.algorithm import HHL
from spinqit import get_basic_simulator, BasicSimulatorConfig
import numpy as np

# Input the linear equations
mat = np.array([[2.5, -0.5], [-0.5, 2.5]])
vec = np.array([1, 0])

# Set up the backend
engine = get_basic_simulator()
config = BasicSimulatorConfig()
config.configure_shots(1024)

# Run
solver = HHL(mat, vec)
solver.run(engine, config)
print(solver.get_state())
print(solver.get_measurements())
```

### VQE Example

Variational Quantum Eigensolver (VQE) can be used for quantum chemistry and optimization problems. The following example shows how to use VQE to calculate the ground state of the hydrogen molecule.

```
import numpy as np
from spinqit import generate_hamiltonian_matrix
from spinqit import Circuit, Parameter, Rx, Rz, CX
from spinqit.algorithm import VQE
from spinqit.algorithm.optimizer import TorchOptimizer

ham = [("IIII", -0.04207255194749729), 
       ("ZIII", 0.17771358229095718), 
       ("IZII", 0.17771358229095718),
       ("IIZI", -0.24274501260934922), 
       ("IIIZ", -0.24274501260934922), 
       ("ZIZI", 0.1229333044929736), 
       ("IZIZ", 0.1229333044929736),
       ("ZIIZ", 0.16768338855598627), 
       ("IZZI", 0.16768338855598627), 
       ("ZZII", 0.1705975927683594), 
       ("IIZZ", 0.17627661394176986), 
       ("YYXX", -0.044750084063012674), 
       ("XXYY", -0.044750084063012674),
       ("YXXY", 0.044750084063012674),
       ("XYYX", 0.044750084063012674)]

depth = 1
qubit_num = len(ham[0][0])
Iter = 100
lr = 0.1
seed = 1024
np.random.seed(seed)

params = Parameter(np.random.uniform(0, 2 * np.pi, 3 * qubit_num * depth),
                               trainable=True)
ansatz = Circuit(params)
qreg = ansatz.allocateQubits(qubit_num)
for d in range(depth):
    for q in range(qubit_num):
        ansatz << (Rx, qreg[q], lambda x, idx=3 * qubit_num * d + 3 * q: x[idx])
        ansatz << (Rz, qreg[q], lambda x, idx=3 * qubit_num * d + 3 * q + 1: x[idx])
        ansatz << (Rx, qreg[q], lambda x, idx=3 * qubit_num * d + 3 * q + 2: x[idx])
    
    for q in range(qubit_num - 1):
        ansatz.append(CX, [qreg[q], qreg[q + 1]])
    ansatz.append(CX, [qreg[qubit_num - 1], qreg[0]])

optimizer = TorchOptimizer(maxiter=Iter, verbose=False, learning_rate=lr)
ham_mat = generate_hamiltonian_matrix(ham)
vqe = VQE(qubit_num, depth, ham_mat, ansatz, optimizer=optimizer)
loss_list = vqe.run(mode='torch', grad_method='backprop')
# loss_list = vqe.run(mode='spinq', grad_method='param_shift')
# loss_list = vqe.run(mode='spinq', grad_method='adjoint_differentiation')
print(loss_list)
```



### QAOA Example

Quantum approximate optimization algorithm (QAOA) is a framework to solve optimization problems. This example shows how to solve the MaxCut problem using QAOA in SpinQit.

```
import numpy as np

from spinqit import get_basic_simulator, BasicSimulatorConfig
from spinqit import generate_hamiltonian_matrix
from spinqit.algorithm.optimizer.adam import ADAM
from spinqit.algorithm.qaoa import QAOA

    
vcount = 4
E = [(0,1), (1,2), (2,3), (3,0)]

# Build Hamiltonian
ham = []
for (u,v) in E:
    pauli_str = ''
    for i in range(vcount):
        if i == u or i == v:
            pauli_str += 'Z'
        else:
            pauli_str += 'I'
    ham.append((pauli_str, 1.0))
print(ham)
# ham = [('ZZII', 1.0), ('IZZI', 1.0), ('IIZZ', 1.0), ('ZIIZ', 1.0), ('IZIZ', 1.0)]

qubit_num = vcount
depth = 4
Iter = 50
lr = 0.1

np.random.seed(1024)
optimizer = ADAM(maxiter=Iter, verbose=True, learning_rate=lr, )
ham_mat = generate_hamiltonian_matrix(ham)
qaoa = QAOA(qubit_num, depth, optimizer=optimizer, problem=ham_mat, )

loss = qaoa.run(mode='torch', grad_method='backprop')[-1]

backend = get_basic_simulator()
config = BasicSimulatorConfig()
config.configure_shots(1024)
result = qaoa.get_measurements(backend, config)
print(result.counts)
```

### Quantum Counting Example

The example shows how to estimate the number of targets in the input values using the QuantumCounting algorithm. There should be 8 numbers ending with 1 in the example below.

```
from spinqit import get_basic_simulator, BasicSimulatorConfig
from spinqit import GateBuilder, RepeatBuilder
from spinqit import H, Z
from spinqit.algorithm import QuantumCounting
from math import pi

hbuilder = RepeatBuilder(H, 4)

# Build the oracle for ***1
oracle_builder = GateBuilder(4)
oracle_builder.append(Z, [3])

# Set up the backend
engine = get_basic_simulator()
config = BasicSimulatorConfig()
config.configure_shots(1024)

qc = QuantumCounting(4, 4, hbuilder.to_gate(), oracle_builder.to_gate())
ret = qc.run(engine, config)
print(ret)
```

### QSearching Example

The QSearching algorithm searches for the index of the maximum or minimum value in an array.

```
from spinqit.algorithm import QSearching

dataset = [2, 3, 1, 4, 5, 6, 7, 15]
seed = 330
max_searcher = QSearching(seed=seed)
max_idx = max_searcher.search(dataset, show=False)
min_searcher = QSearching(objective='min', seed=seed)
min_idx = min_searcher.search(dataset, show=False)
print(max_idx, min_idx)
```
### QNN Example

The example below shows how to use SpinQit and PyTorch together to solve a classification problem.

``` 
import numpy as np
import torch
import torch.optim as optim
from torch import nn

from spinqit import Circuit, Parameter
from spinqit import Rz, Ry, CX
from spinqit.algorithm import ExpvalCost
from spinqit.algorithm import QuantumModel


def build_circuit(weights, qubit_num, layer_num):
    circ = Circuit(weights)
    q = circ.allocateQubits(qubit_num)

    for i in range(layer_num):
        circ << (Rz, q[0], lambda x, idx=i * layer_num + 0: x[idx])
        circ << (Ry, q[0], lambda x, idx=i * layer_num + 1: x[idx])
        circ << (Rz, q[0], lambda x, idx=i * layer_num + 2: x[idx])
        circ << (Rz, q[1], lambda x, idx=i * layer_num + 3: x[idx])
        circ << (Ry, q[1], lambda x, idx=i * layer_num + 4: x[idx])
        circ << (Rz, q[1], lambda x, idx=i * layer_num + 5: x[idx])
        circ << (CX, q)
    return circ


def get_data():
    file_path = "../resource/iris_classes_data.txt"
    data = np.loadtxt(file_path)
    Xdata = data[:, 0:2]
    padding = 0.3 * np.ones((len(Xdata), 1))
    X_pad = np.c_[np.c_[Xdata, padding], np.zeros((len(Xdata), 1))]
    normalization = np.sqrt(np.sum(X_pad ** 2, -1))
    X_norm = (X_pad.T / normalization).T

    features = X_norm

    Y = data[:, -1]
    np.random.seed(0)
    num_data = len(Y)
    n_train = int(0.75 * num_data)
    index = np.random.permutation(range(num_data))
    x_train = torch.tensor(features[index[:n_train]]).to(torch.float32)
    y_train = torch.tensor(Y[index[:n_train]]).to(torch.float32)
    x_val = torch.tensor(features[index[n_train:]]).to(torch.float32)
    y_val = Y[index[n_train:]]
    return n_train, x_train, y_train, x_val, y_val,


def get_model():
    qubit_num, layer_num = 2, 6

    class HybridModel(nn.Module):
        def __init__(self, n_qubit, n_layer, ):
            super(HybridModel, self).__init__()
            w = 0.01 * Parameter(np.random.randn(layer_num * qubit_num * 3), trainable=True)
            circuit = build_circuit(w, n_qubit, n_layer, )
            fn = ExpvalCost(circuit,
                            hamiltonian=([('Z', 1)]),
                            backend_mode='torch',
                            grad_method='backprop', )
            quantum_layer = QuantumModel(fn)
            quantum_layer.quantum_fn.update_backend_config(qubits=[0])
            b = torch.tensor(0.0)

            self.b = nn.Parameter(b, requires_grad=True)
            self.quantum_layer = quantum_layer

        def forward(self, state, ):
            return self.quantum_layer(state=state) + self.b

    model = HybridModel(qubit_num, layer_num)
    return model


def test_train():
    model = get_model()
    num_train, features_train, labels_train, features_val, labels_val, = get_data()
    optimizer = optim.SGD(model.parameters(), lr=0.01, momentum=0.9, nesterov=True)
    loss_fn = nn.MSELoss()
    iter = 45
    batch_size = 10

    print('-----begin train----------')
    for i in range(iter):
        batch_index = np.random.randint(0, num_train, (batch_size,))
        feats_train_batch = features_train[batch_index]
        Y_train_batch = labels_train[batch_index]

        optimizer.zero_grad()
        pred = model(feats_train_batch)

        loss = loss_fn(pred, Y_train_batch)
        print(f'Loss : {loss.item()}')
        loss.backward()
        optimizer.step()

    print('---------begin predict--------------')
    total_error = 0
    with torch.no_grad():
        for k in range(len(features_val)):
            test_x = features_val[k].reshape(-1)
            pred = model(test_x)
            print(pred, labels_val[k])
            if abs(labels_val[k] - np.sign(pred.item())) > 1e-5:
                total_error = total_error + 1

    print(total_error)


if __name__ == '__main__':
    seed = 1024
    np.random.seed(seed)
    test_train()
```


<style>
html.writer-html5 .rst-content table {
  width:100%
}
html.writer-html5 .rst-content table th{
  vertical-align:middle;
  font-weight:normal;
}
html.writer-html5 .rst-content table th:nth-child(1) {
  width:150px;
}
html.writer-html5 .rst-content table th:nth-child(2) p{
  white-space:normal;
}
html.writer-html5 .rst-content table td:nth-child(2) p{
  white-space:normal;
}

.class-distract{
    color: #2980b9;
    border-top: 3px solid #6ab0de;
    background: #e7f2fa;
    line-height: normal;
    font-weight: 700;
    display: inline-block;
    padding: 6px;
}
.class-distract em{
    color: #2980b9;
    font-style: italic;
}
.class-distract .class-desc{
    color: #000;
    font-family: SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,Courier New,Courier,monospace;
}

.admonition-distract .admonition-title{
    padding: 6px 12px;
    font-size: 16px;
    font-weight: 700;
    background-color: #6ab0de;
    color: #fff;
    box-sizing: border-box;
    width: 100%;
    margin: 0;
}
.admonition-distract .admonition-desc{
    background-color: #e7f2fa;
    padding: 12px;
    margin-bottom: 12px;
}
.rst-content .code-distract{
    color: darkgreen;
    border: 1px solid #e1e4e5;
    font-size: 75%;
}

.method-distract{
    border: none;
    border-left: 3px solid #ccc;
    background: #f0f0f0;
    color: #555;
    padding: 6px;
}

.method-distract .method-name{
    color: #000;
    font-family: SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,Courier New,Courier,monospace;
}
.method-distract .method-param{
    font-size: 90%;
    color: #555;
}

.method-distract .sub-param-distract{
    margin: 0 0 12px 24px;
}
.field-list{
    display: grid;
    grid-template-columns: max-content auto;
}
.field-list dt{
    background: rgba(118, 185, 0, 0.1);
    color: rgba(59,93,0,1);
    font-weight: 700;
    line-height: 24px;
    border-top: solid 3px rgba(59,93,0,1);
}
.field-list dd{
    margin: 0 0 12px 24px;
    line-height: 24px;
}
.field-list dd p {
    margin-bottom: 12px !important;
}
</style>

