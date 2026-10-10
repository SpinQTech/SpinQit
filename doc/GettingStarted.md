# Basics
## Requirements

- SpinQit is available on Windows, Linux, and macOS. This package has been tested on Ubuntu 20.04 & 22.04 (x86_64), Windows 10 & 11 (x86_64), macOS Ventura 13.0 (M1 & x86_64).
- SpinQit requires Python 3.9, 3.10 or 3.11.  This package has been tested with Python 3.9.25, 3.10.20 and 3.11.16.

## Installation
SpinQit can be installed using the following command:
```python
pip install spinqit
```

To build from the source on GitHub, you need a C/C++ compiler and CMake in addition. We do not recommend this approach unless you are very familiar with these tools.
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

More details about the syntax, compilers, and backends are introduced in the next section.


# Programming

## Syntax
SpinQit supports three programming syntaxes: native SpinQit Python syntax, [OpenQASM 2.0](https://arxiv.org/abs/1707.03429) syntax, and [IBM Qiskit](https://qiskit.org/) Python syntax.

### SpinQit Python

SpinQit allows users to define arbitrary quantum circuits. The basic concepts in SpinQit Python syntax are as follows. 

**Circuit**: In SpinQit, each quantum program is a Circuit instance.

**Quantum register**: A quantum register has a certain number of qubits, and must be allocated by a circuit using allocateQubits. A qubit is represented by the register name and its index. 

**Classical register**: A classical register has a certain number of classical bits, and must be allocated by a circuit using `allocateClbits`. A classical bit is represented by the register name and its index. A classical bit stores a measurement result in the quantum program, which is used by subsequent conditional statements.

**Quantum gates**: SpinQit defines 22 logical quantum gates (I, H, X, Y, Z, Rx, Ry, Rz, P, T, Td, S, Sd, CX/CNOT, CY, CZ, U, CP, SWAP, CCX, Ph, CSWAP) and two special gates (MEASURE and BARRIER). Specifically, P is the phase-shift gate, while Ph is the global-phase gate.

There is a special gate named StateVector which directly initializes the qubits to a specific state, but this gate is only supported by the torch simulator backend.

**Instruction**: An instruction consists of a quantum gate, qubits, optional classical bits, and an optional rotation angle in radians. SpinQit uses `<<` to add an instruction to a circuit, as shown in the example earlier.

**Custom quantum gate**: SpinQit provides a gate builder to define a custom quantum gate. The builder builds a gate based on sub-gates. Qubit indices and an optional parameter lambda are defined for each sub-gate. For example, a custom gate can be defined as follows:

```python
param_lambda = lambda params: params[0]
builder = GateBuilder(2)
builder.append(H, [0])
builder.append(CX, [0, 1])
builder.append(Rx, [0], param_lambda)
builder.append(Rx, [0], pi)
g = builder.to_gate()
circ << (g, qreg, pi)
```

`ControlledGate` is a class that adds a control qubit to a base gate and creates a new controlled gate.

```python
cswap = ControlledGate(SWAP)
circ << (cswap, (q[0], q[1], q[2]))
```

**Parameter**

Rotation gates and phase-shift gates take an angle in radians. This parameter can be a constant real number, or it can be a variable used in a variational quantum algorithm. A constant angle can be passed directly to a gate. To create trainable parameters, use `Circuit.add_params()` and pass the resulting parameters to the gates. Parameters can also be combined with constants or with other parameters in an expression, as shown below.

```python
circuit = Circuit()
q=circuit.allocateQubits(qubit_num)
weight = circuit.add_params(shape=(2,)) 
noise = circuit.add_params(shape=(2,)) 

for i in range(qubit_num):
    circuit << (X, q[i])
    circuit << (H, q[i])
    circuit << (Ry, q[i], weight[0])
    circuit << (Rz, q[i], weight[1])
    circuit << (P, q[i], weight[0] + noise[0])
    circuit << (P, q[i], weight[1] + noise[1])
```


**Conditions based on measurements**: In SpinQit, `Circuit` has a `measure` method to measure some of the qubits and store the results in classical bits. This method inserts a special MEASURE gate into the circuit. After the measurement, a gate can be applied conditionally based on the values of classical bits. Such control flow is also known as `cif`. A condition in SpinQit is a tuple containing a list of classical bits, a comparator string (`'=='`, `'!='`, `'>'`, `'>='`, `'<'`, or `'<='`), and an integer. The `|` operator is used to add a condition to an instruction. The usage is as follows:
```python
circ = Circuit()
q = circ.allocateQubits(2)
c = circ.allocateClbits(2)
circ << (H, q[0])
circ << (X, q[1])
circ.measure(q[0], c[0])
circ << (H, q[1]) | (c, '==', 0)
```

The MEASURE gate cannot be used in a custom gate or with `cif`. Currently, this feature can only be executed by the basic classical simulator.


### OpenQASM 2.0
SpinQit supports OpenQASM 2.0. The basic gates allowed in SpinQit include id, x, y, z, h, rx, ry, rz, t, tdg, s, sdg, p, cx, cy, cz, swap, ccx, u, U, CX, measure, and barrier. Other standard gates in OpenQASM can be called by including "qelib1.inc", which is provided by SpinQit and is exactly the same as the library file in OpenQASM.

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
SpinQit also supports the IBM Qiskit Python interface. The version supported by SpinQit is qiskit-0.31.0 (qiskit-terra-0.18.3). We include the qiskit.circuit package and some related packages in SpinQit. Therefore, you can construct a Qiskit QuantumCircuit instance and run it with SpinQit, even without installing Qiskit. In particular, SpinQit supports the QFT, QPE, and Grover primitives in Qiskit (in spinqit.qiskit.circuit.library), so you can build quantum algorithms based on these primitives. Nevertheless, SpinQit does not include all Qiskit code. If you want to use the qiskit.algorithm package and run the circuit on SpinQit backends, you still need to install Qiskit.

```python
from spinqit.qiskit.circuit import QuantumCircuit
from spinqit import get_compiler, get_basic_simulator, BasicSimulatorConfig
from math import pi

qc = QuantumCircuit(2)
qc.h(0)
qc.rx(pi, 1)
qc.cx(0, 1)

compiler = get_compiler('qiskit')
simulator = get_basic_simulator()
config = BasicSimulatorConfig()

exe = compiler.compile(qc, 0)
result = simulator.execute(exe, config)
print(result.states)
print(result.counts)
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

**Level 1** consists of two passes, with two algorithms applied in order. The first algorithm cancels consecutive redundant gates. Certain gates can be removed when they are repeated an even number of times on the same qubit(s) without affecting the final result. The gates that satisfy this property include the Pauli-X gate (X gate), Hadamard gate (H gate), and CNOT gate (CX gate). This algorithm removes these redundant gates from the circuit. Similarly, if multiple rotation gates rotate the same qubit around the same axis, this algorithm combines them into one rotation gate. The second algorithm collapses more than 3 consecutive single-qubit gates on the same qubit into several basic gates. The algorithm calculates the matrix that represents the consecutive gates and decomposes the matrix into basic gates. Currently, SpinQit uses ZYZ decomposition.

**Level 2** contains the two algorithms in Level 1 and then applies a third algorithm. The third algorithm collapses more than 6 consecutive two-qubit gates on the same two qubits into certain Ry, Rz, and CX gates.  The algorithm also calculates the matrix that represents the original gates and then decomposes the matrix.

**Level 3** first cancels redundant gates and then applies two optimization algorithms based on quantum state analysis introduced in [https://arxiv.org/abs/2012.07711v1](https://arxiv.org/abs/2012.07711v1). The two algorithms are reported to perform better than the most aggressive optimization level in Qiskit. After the two algorithms, the collapsing single-qubit-gate and collapsing two-qubit-gate passes are applied.

The optimization features in SpinQit are still experimental. More algorithms will be added in the future. Please let us know if you find any issues.

### Circuit Visualization

SpinQit provides a helper function to draw the intermediate representation after compilation. The output drawing shows the quantum circuit. 

<dl>
    <dt class="method-distract">
        <span class="method-name">spinqit.view.draw</span>
        <em class="method-param">(ir, filename, clbit_extend, decompose_level)</em>
    </dt>
</dl>

Draw an image for the intermediate representation of a circuit and save it to a PNG file.

<dl>
    <dd>
        <dl class="field-list simple">
            <dt class="field-odd">Parameters</dt>
            <dd class="field-odd"><p><strong>ir</strong> - IntermediateRepresentation, the intermediate representation of the circuit to draw</p>
            <p><strong>filename</strong> - str, the name of the output PNG file</p>
            <p><strong>clbit_extend</strong> - bool, False by default; show each classical bit in a row, or collapse all classical bits into one row</p>
            <p><strong>decompose_level</strong> - int, 0 by default; for decompose_level = n > 0, recursively decompose caller gates in the IR for n levels</p>
            </dd>
        </dl>
    </dd>
</dl>


## Backend
SpinQit has five backend types: a basic classical simulator, a PyTorch-based simulator, local quantum computers from SpinQ, a cloud backend for accessing online quantum computing resources, and a QASM-based backend.

### Basic Simulator

The basic simulator is a CPU-based local classical simulator. It supports measurement and conditional operations in the quantum circuit, but does not support autograd or parallel processing.

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

Each kind of backend in SpinQit has a get_value_and_grad_fn method that returns the evaluation result of an input quantum circuit and the corresponding grad function. This method is used by the QLayer interface of SpinQit which will be introduced later. This method has two important parameters, measure_op and grad_method, which specify the measurement in the evaluation and the type of grad function respectively.

The basic SpinQ simulator backend supports two types of gradient methods, parameter shift ("param_shift") and adjoint differentiation ("adjoint_differentiation"). Both gradient methods work only with the "expval" measure operation, which means expectation value.


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


The Torch simulator backend supports two types of gradient methods, parameter shift ("param_shift") and backpropagation ("backprop"). Parameter shift can work only with the "expval" measure operation, while backpropagation supports "expval" and "state". Here, "state" refers to the state-vector result.

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

The local quantum computer backend supports only parameter shift ("param_shift"). Parameter shift works only with the "expval" measure operation.


### Cloud
In order to use SpinQ's online experimental platform, you have to first register and add a public SSH key on [https://cloud.spinq.com.](https://cloud.spinq.com.) Please refer to the documentation online about SpinQ's online experimental platform [https://cloud.spinq.com/#/docs.](https://cloud.spinq.com/#/docs.) Username and key information are required to use the cloud backend. The `host` argument specifies the cloud platform URL to connect to. If it is omitted, the backend connects to SpinQ's online experimental platform by default. It can also be set to the URL of a private cloud that supports SpinQit.

For example, use SpinQ's online experimental platform by default as follows:

```python
backend = get_spinq_cloud(username, keyfile)
```

To connect to a compatible private cloud, provide its URL through `host`:

```python
backend = get_spinq_cloud(
    username,
    keyfile,
    host="https://private-cloud.example.com",
)
```
![SSH.PNG](SSH.PNG)
SpinQ provides multiple platforms with different numbers of qubits on SpinQ's online experimental platform. The cloud backend has a `get_platform` method, which returns a platform instance for one of `"gemini_vp"`, `"triangulum_vp"`, or `"sqc_25_vp"`. These platforms have 2, 3, and 25 qubits, respectively, and support quantum programs with up to the corresponding number of qubits.

The cloud backend returns a `SpinQCloudResult` object. Its `probabilities` property contains a dictionary whose keys are binary measurement results and whose values are the corresponding probabilities. Its `counts` property contains shot counts when they are returned by the cloud platform; otherwise, counts can be derived from the probabilities and the configured number of shots. If shots are not configured, the default is 1024.


<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.backend.SpinQCloudConfig</span>
    </dt>
</dl>

|Method|Description|
|---|---|
|configure_shots(shots)| Configure the total number of shots so that the count of each possible binary reading is calculated in the result. |
|configure_ip(addr)| Configure the ip address of the quantum computer. |
|configure_port(port)| Configure the port number of the quantum computer. |
|configure_account(username, password)| Configure the username and password that registered on the quantum computer. |
|configure_task(task_name, task_desc)| Configure the task name and description. |


The following example shows how to use the cloud backend and log in using your SSH key.

```python
username = "username"
keyfile = "/path/to/.ssh/id_rsa"

backend = get_spinq_cloud(username, keyfile)

gemini = backend.get_platform("gemini_vp")
print("gemini has " + str(gemini.machine_count) + " active machines.")

if gemini.available():
    comp = get_compiler("native")
    circ = Circuit()
    ...
    ir = comp.compile(circ, 0)
    config = SpinQCloudConfig()
    config.configure_platform('gemini_vp')
    config.configure_shots(1024)
    config.configure_task('newapitest1', 'newapi')

    res = backend.execute(ir, config)
else:
    print("No machine available for this platform.")
```

The cloud backend supports only parameter shift ("param_shift"). Parameter shift works only with the "expval" measure operation.

### QASM

SpinQit can convert its intermediate representation to OpenQASM code in string form so that any third-party platform that supports OpenQASM can execute code written in SpinQit. The QASM backend is initialized with a handle function that runs OpenQASM code. The result format of this backend depends on the actual execution platform. It is best to convert third-party results to SpinQit result formats in the handle. SpinQit provides a `QiskitQasmResult` class to process Qiskit results.

The following example shows how to define a handle for the QASM backend to use Qiskit 2.3.0 and qiskit-aer 0.17.2 to execute a quantum circuit.

```python
from qiskit import qasm2, transpile
from qiskit_aer import AerSimulator

from spinqit import (
    Circuit,
    H,
    CX,
    get_compiler,
    get_qasm_backend,
    QasmConfig,
    QiskitQasmResult,
)


def qiskit_function(qasm, shots=1024, *args, **kwargs):
    qc = qasm2.loads(qasm)

    print("Received OpenQASM:")
    print(qasm)

    simulator = AerSimulator(method="statevector")
    qc.save_statevector()
    qc = transpile(qc, simulator)

    aer_result = simulator.run(qc).result()
    statevector = aer_result.get_statevector(qc)

    result = QiskitQasmResult()
    result.set_result(
        getattr(statevector, "data", statevector),
        shots,
    )

    return result


circ = Circuit()
q = circ.allocateQubits(2)

circ << (H, q[0])
circ << (CX, (q[0], q[1]))

compiler = get_compiler("native")
exe = compiler.compile(circ, 0)

config = QasmConfig()
config.configure_shots(1024)

engine = get_qasm_backend(qiskit_function)
result = engine.execute(exe, config)

print("Probabilities:")
print(result.probabilities)

print("State vector:")
print(result.states)

print("Counts:")
print(result.counts)
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

This QASM backend supports parameter shift ("param_shift"). It also supports adjoint differentiation ("adjoint_differentiation") if the external QASM engine can return the state vector. Both gradient methods work only with the "expval" measure operation.


## Result
SpinQit provides four types of results. First, all the backends can provide the probabilities of binary readings as follows:
```
print(result.probabilities)
{'10': 0.4999999999809753, '11': 0.4999999999809753}
```
Note that SpinQit uses little-endian ordering; that is, the first bit in the result binary string corresponds to the first qubit in the quantum circuit.

Second, counts for each possible binary reading can be found in the result. The total number of shots is configurable; if it is not specified, the default is 1024.
```
print(result.counts)
{'10': 512, '11': 512}
```
Third, with the simulators, a random binary reading can be obtained from the result according to the probabilities via `get_random_reading()`.
```
print(result.get_random_reading())
11
```
Fourth, the two simulator backends can provide the state vector of all the qubits when the circuit contains no measurement gate or conditional gate based on the value of a classical register.
```
print(result.states)
[(1.37812710729329e-10+0j), (1.37812710729329e-10+0j), -0.7071067811865476j, -0.7071067811865476j]
```

The following table shows the result formats supported by each backend.

|Result|Basic Simulator|Torch Simulator|Local Quantum Computer|Cloud|QASM Backend|
|---|---|---|---|---|---|
|Probabilities|Y|Y|Y|Y|Y|
|Counts|Y|Y|Y|Y|Y|
|States|Y|Y|N|N|Y|
|Random Reading|Y|Y|N|N|Y|


## QLayer Interface
SpinQit provides an abstract interface named QLayer to simplify the implementation of variational quantum algorithms and quantum machine learning algorithms. QLayer encapsulates the backend, backend configuration, measurement operation, gradient function, and related components. QLayer can be defined via a decorator named `to_qlayer`. Developers use this decorator to wrap any function that returns a Circuit. With the `to_qlayer` decorator, the final result is the measurement result of the quantum circuit produced by the wrapped function and evaluated on the selected backend. QLayer can also work with the optimizers in SpinQit and interfaces for classical machine learning frameworks. These optimizers and frameworks call the gradient function specified in QLayer for gradient-based optimization. The following example shows how to use the `to_qlayer` decorator.

```python
from spinqit.interface import to_qlayer
from spinqit.algorithm.loss import expval
op = expval(generate_hamiltonian_matrix([('ZI', 1)]))
@to_qlayer(backend_mode='spinq', grad_method='param_shift', measure=op, interface='torch')
def build_circuit(weights_shape, qubit_num):
    circ = Circuit()
    weight = circ.add_params(shape=weights_shape) 
    q = circ.allocateQubits(qubit_num)
    ...
    return circ
```

More configuration information can be provided via `to_qlayer`:

```python
@to_qlayer(backend_mode='nmr', grad_method='param_shift', measure=expval(hamiltonian), interface='spinq', ip='192.168.8.176', port=55444, account=("user9", "123456"), shots=1024, task_name='nmrgradtest1', task_desc='nmr grad test')
```

The main parameters include:

<dl>
    <dd>
        <dl class="field-list simple">
            <dt class="field-odd">backend_mode</dt>
            <dd class="field-odd"> The backend to execute the circuit, and the current options are 'spinq', 'torch', 'cloud', and 'nmr' </dd>            
            <dt class="field-even">measure</dt>
            <dd class="field-even">This parameter must be a function creating a measurement operation. There are four types of measurement operations: states(), probs(mqubits=None), counts(shots=None, mqubits=None) and expval(hamiltonian). Here expval means the expectation value of a Hamiltonian, and the parameter hamiltonian is a scipy.sparse.csr_matrix or a list of (Pauli string, coefficient) pairs.</dd>
            <dt class="field-odd">interface</dt>
            <dd class="field-odd">There are four available interfaces: 'torch', 'tf', 'paddle', and 'spinq'. To avoid unnecessary data-type conversions, SpinQit provides interfaces that work with classical machine learning frameworks such as PyTorch, TensorFlow, and PaddlePaddle.</dd>
            <dt class="field-even">grad_method</dt>
            <dd class="field-even">Each backend supports one or more gradient functions. All the backends support 'param_shift'. In addition, 'torch' supports 'backprop' and 'spinq' supports 'adjoint_differentiation'.</dd>
        </dl>
    </dd>
</dl>

The following table summarizes the gradient methods and measure operations supported by each kind of backend in QLayer.


<table>
<tr>
<td>Backend Mode</td>
<td>Grad Method</td>
<td>MeasureOp</td>
</tr>
<tr>
<td rowspan=2>spinq</td>
<td>param_shift</td>
<td>expval</td>
</tr>
<tr>
<td>adjoint_differentiation</td>
<td>expval</td>
</tr>
<tr>
<td rowspan=2>torch</td>
<td>param_shift</td>
<td>expval</td>
</tr>
<tr>
<td>backprop</td>
<td>expval, state</td>
</tr>
<tr>
<td>cloud</td>
<td>param_shift</td>
<td>expval</td>
</tr>
<tr>
<td>nmr</td>
<td>param_shift</td>
<td>expval</td>
</tr>
</table>


## Library

SpinQit provides useful APIs for developers to use in their own quantum programs. Users can define custom quantum gates, build new quantum algorithms, and invoke existing algorithms. This section introduces SpinQit's APIs.

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
                    <p><strong>param_lambda</strong> - float or Callable, optional gate parameters; None by default</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>A RepeatBuilder instance</p>
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
                <p>Create an InverseBuilder instance.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>gate</strong> – Gate, the gate to invert</p>
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
                    <dd class="field-odd"><p><strong>ctrl_qubit_num</strong> – int, the number of control qubits. Note that the total number of qubits for the generated gate is the number of control qubits plus one.</p>
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
        <p>Build a Z-basis parametric Ising coupling gate.</p>
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
                    <dd class="field-odd"><p><strong>qubit_num</strong> – int, the number of qubits on which the gate acts</p>
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
        <p>Build an X-basis parametric Ising coupling gate.</p>
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
                    <dd class="field-odd"><p><strong>qubit_num</strong> – int, the number of qubits on which the gate acts</p>
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
        <p>Build a Y-basis parametric Ising coupling gate.</p>
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
                    <dd class="field-odd"><p><strong>qubit_num</strong> – int, the number of qubits on which the gate acts</p>
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
                    <p><strong>gate</strong> - Gate, numpy.ndarray, or list, the single-qubit gate applied to the target qubit; it can be a Gate instance in SpinQit or a unitary matrix represented by an ndarray or list</p>
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
                    <p><strong>gate</strong> - Gate, numpy.ndarray, or list, the single-qubit gate applied to the target qubit; it can be a Gate instance in SpinQit or a unitary matrix represented by an ndarray or list</p>
                    <p><strong>params</strong> – List, the parameters for the Gate instance, None by default</p>
                    <p><strong>up_to_diag</strong> – bool, whether to implement the uniformly controlled gate up to diagonal gates; False by default</p>
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
            <p><strong>control_bit</strong> - int, the control qubit; defaults to None</p>
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
        <dl>…12988 tokens truncated…
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
                <em class="method-param">(qlayer, *params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qlayer</strong> – QLayer, the interface wrapping circuit and execution configuration</p>
                    <p><strong>*params</strong> - Parameter, parameters used in the quantum circuit</p>
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
                <em class="method-param">(qlayer, *params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qlayer</strong> – QLayer, the interface wrapping circuit and execution configuration</p>
                    <p><strong>*params</strong> - Parameter, parameters used in the quantum circuit</p>
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
                <em class="method-param">(qlayer, *params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qlayer</strong> – Qlayer, the interface wrapping circuit and execution configuration</p>
                    <p><strong>*params</strong> - Parameter, parameters used in the quantum circuit</p>
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
                <em class="method-param">(maxiter, tolerance, learning_rate, verbose, optim_type, **kwargs)</em>
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
                    <p><strong>kwargs</strong> - dict, other parameters used by PyTorch optimizers</p>
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
                <em class="method-param">(qlayer, *params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qlayer</strong> – Qlayer, the interface wrapping circuit and execution configuration</p>
                    <p><strong>*params</strong> - Parameter, parameters used in the quantum circuit</p>
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
                <em class="method-param">(fn, *params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>fn</strong> – Qlayer, the interface wrapping circuit and execution configuration</p>
                    <p><strong>*params</strong> - Parameter, parameters used in the quantum circuit</p>
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
                <em class="method-param">(qlayer, *params)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Optimize the objective function.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>qlayer</strong> – Qlayer, the interface wrapping circuit and execution configuration</p>
                    <p><strong>*params</strong> - Parameter, parameters used in the quantum circuit</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The list of loss values</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>

### Solver
SpinQit provides two off-the-shelf problem solvers based on quantum algorithms. The satisfiability problem (SAT) and the traveling salesman problem (TSP) can model many real-world application problems and can be solved efficiently by quantum algorithms.

#### SATSolver

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.solver.SATSolver</span>
    </dt>
    <dd>
        <p>A solver to solve the satisfaction problem using Grover's algorithm.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(expr)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a SATSolver instance for a specific satisfaction problem.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>expr</strong> – str or sympy.logic.boolalg.And, the expression that represents the satisfaction problem to solve</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>An instance of SATSolver</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">solve</span>
                <em class="method-param">(backend_mode, **kwargs)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Solve the satisfaction on the given backend.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>backend_mode</strong> - str, the backend to execute the quantum circuit, one of 'spinq', 'torch', 'qasm', 'nmr', and 'cloud'</p>
                    <p><strong>**kwargs</strong> - Any, configurations for the backend</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The assignment satisfying the constraints</p>
                    </dd>
                </dl>
            </dd>
        </dl>
    </dd>
</dl>

#### TSPSolver

<dl>
    <dt class="class-distract">
        <em>class</em>
        <span class="class-desc">spinqit.solver.TSPSolver</span>
    </dt>
    <dd>
        <p>A solver to solve the traveling salesman problem using VQE algorithm.</p>
        <p><b>Methods</b></p>
        <dl>
            <dt class="method-distract">
                <span class="method-name">__init__</span>
                <em class="method-param">(vertex_num, weighted_adjacency, penalty)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Create a TSPSolver instance for a specific graph.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>vertex_num</strong> – int, the number of vertices</p>
                    <p><strong>weighted_adjacency</strong> – list or numpy.ndarray, the weighted adjacency matrix in which weighted_adjacency[i][j] is the weight of the edge from i to j</p>
                    <p><strong>penalty</strong> – float, a parameter required in the algorithm whose value must be larger than the maximum weight</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>An instance of TSPSolver</p>
                    </dd>
                </dl>
            </dd>
        </dl>
        <dl>
            <dt class="method-distract">
                <span class="method-name">solve</span>
                <em class="method-param">(iterations, backend_mode, grad_method, learning_rate)</em>
            </dt>
        </dl>
        <dl>
            <dd>
                <p>Solve the TSP problem with specific configurations.</p>
                <dl class="field-list simple">
                    <dt class="field-odd">Parameters</dt>
                    <dd class="field-odd"><p><strong>iterations</strong> - int, the number of maximum iterations</p>
                    <p><strong>backend_mode</strong> - str, the backend to execute the quantum circuit, 'spinq' or 'torch'</p>
                    <p><strong>grad_method</strong> - str, the gradient method used in VQE</p>
                    <p><strong>learning_rate</strong> = float, 0.1 by default, the learning rate used in the optimizer</p>
                    </dd>
                    <dt class="field-even">Returns</dt>
                    <dd class="field-even"><p>The visiting order of vertices</p>
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

Systems of linear equations are fundamental to many science and engineering problems, especially in machine learning. The Harrow-Hassidim-Lloyd algorithm (HHL) can be used to solve certain linear systems on a quantum computer.

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
from spinqit import Circuit, Rx, Rz, CX
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

circ = Circuit()
qreg = circ.allocateQubits(qubit_num)
params = circ.add_params(shape=(depth, qubit_num, 3))
for d in range(depth):
    for q in range(qubit_num):
        circ << (Rx, qreg[q], params[d][q][0])
        circ << (Rz, qreg[q], params[d][q][1])
        circ << (Rx, qreg[q], params[d][q][2])
    
    for q in range(qubit_num - 1):
        circ.append(CX, [qreg[q], qreg[q + 1]])
    circ.append(CX, [qreg[qubit_num - 1], qreg[0]])

optimizer = TorchOptimizer(maxiter=Iter, verbose=False, learning_rate=lr)
ham_mat = generate_hamiltonian_matrix(ham)
vqe = VQE(ham_mat, optimizer, ansatz=circ, params=(depth, qubit_num, 3))
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
from spinqit.algorithm.optimizer import ADAM, TorchOptimizer
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
iter_num = 30
lr = 0.1

np.random.seed(1024)
optimizer = TorchOptimizer(maxiter=iter_num, verbose=True, learning_rate=lr)
ham_mat = generate_hamiltonian_matrix(ham)
qaoa = QAOA(ham_mat, optimizer, depth)


loss = qaoa.run(mode='torch', grad_method='backprop')[-1]

result = qaoa.optimized_result
print(result.probabilities)
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
min_searcher = QSearching('min', backend_mode='torch', seed=seed)
min_idx = min_searcher.search(dataset, show=False)
print(max_idx, min_idx)
```
### QNN Example

The example below shows how to use the PyTorch interface in SpinQit to solve a classification problem.

```
import numpy as np
import torch
import torch.optim as optim
from torch import nn
from functools import partial

from spinqit import Circuit, Rz, Ry, CX, generate_hamiltonian_matrix
from spinqit.primitive import amplitude_encoding
from spinqit.interface import to_qlayer, TorchQuantumFunction
from spinqit.algorithm.loss import expval

#@to_qlayer(backend_mode='nmr', grad_method='param_shift', measure=expval(generate_hamiltonian_matrix([('ZI', 1)])), ip='192.168.2.4', port=59585, account=('user1','123456'), task_name='classifier', task_desc='test')
@to_qlayer(backend_mode='torch', grad_method='backprop', measure=expval(generate_hamiltonian_matrix([('ZI', 1)])))
def build_circuit(state, weights_shape, qubit_num, layer_num):
    circ = Circuit()
    weight = circ.add_params(shape=weights_shape) 
    q = circ.allocateQubits(qubit_num)
    
    state = state.numpy()
    
    #encode the input vector
    ilist = amplitude_encoding(state, q)
    circ.extend(ilist)
    
    for i in range(layer_num):
        for j in range(qubit_num):
            circ << (Rz, q[j], weight[i][j][0])
            circ << (Ry, q[j], weight[i][j][1])
            circ << (Rz, q[j], weight[i][j][2])
        circ << (CX, q)
    return circ


def get_data(file_path):
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
    x_train = torch.tensor(features[index[:n_train]], requires_grad=False).to(torch.float32)
    y_train = torch.tensor(Y[index[:n_train]], requires_grad=False).to(torch.float32)
    x_val = torch.tensor(features[index[n_train:]], requires_grad=False).to(torch.float32)
    y_val = Y[index[n_train:]]
    return n_train, x_train, y_train, x_val, y_val,


def get_model(qubit_num, layer_num, bias=None):
    weight_shape = (layer_num, qubit_num, 3)

    class MyQuantumModule(nn.Module):
        def __init__(self, qlayer_func, weight_shape, bias=None):
            super(MyQuantumModule, self).__init__()
            self.w = nn.Parameter(0.01 * torch.randn(weight_shape), requires_grad=True)
            self.b = bias
            self.qlayer_func = qlayer_func

        def forward(self, state):
            res = torch.zeros(state.size(0))
            if len(state.shape) > 1:
                for i in range(state.size(0)):
                    myqlayer = self.qlayer_func(state[i])
                    kwargs = dict(
                        qlayer=myqlayer,
                    )
                    loss = TorchQuantumFunction.apply(kwargs, self.w)
                    res[i] += loss
            else:
                myqlayer = self.qlayer_func(state)
                kwargs = dict(
                    qlayer=myqlayer,
                )
                res = TorchQuantumFunction.apply(kwargs, self.w)
            
            if self.b is not None:
                return res + self.b
            return res

    qlayer_func = partial(build_circuit, weights_shape = weight_shape, qubit_num=qubit_num, layer_num=layer_num)
    model = MyQuantumModule(qlayer_func, weight_shape, bias)
    return model


def test_train(model, num_train, features_train, labels_train, features_val, labels_val):
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
    assert np.allclose(total_error, 0)


if __name__ == '__main__':
    file_path = "resource/iris_classes_data.txt"
    qubit_num, layer_num = 2, 6
    seed = 1024
    np.random.seed(seed)
    torch.random.manual_seed(seed)
    bias = nn.Parameter(torch.tensor(0.0), requires_grad=True)
    model = get_model(qubit_num, layer_num, bias=bias)
    num_train, features_train, labels_train, features_val, labels_val, = get_data(file_path)
    test_train(model, num_train, features_train, labels_train, features_val, labels_val, )
```

The example below shows how to use the TensorFlow interface in SpinQit to solve the same classification problem.

```
import numpy as np
import tensorflow as tf
from tensorflow.keras import Sequential, losses, optimizers

from spinqit import Circuit, Rz, Ry, CX, generate_hamiltonian_matrix, StateVector
from spinqit.interface import to_qlayer
from spinqit.interface.tf_interface import QuantumLayer
from spinqit.algorithm.loss import expval

@to_qlayer(backend_mode='torch',
           grad_method='backprop',
           measure=expval(generate_hamiltonian_matrix([('ZI', 1)])))
def build_circuit(state_shape, weights_shape, qubit_num, layer_num):
    circ = Circuit()
    state = circ.add_params(shape=state_shape) 
    weight = circ.add_params(shape=weights_shape) 
    q = circ.allocateQubits(qubit_num)
    circ << (StateVector, q, state[:])
    for i in range(layer_num):
        for j in range(qubit_num):
            circ << (Rz, q[j], weight[i][j][0])
            circ << (Ry, q[j], weight[i][j][1])
            circ << (Rz, q[j], weight[i][j][2])
        circ << (CX, q)
    return circ

def get_data(file_path):
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

    x_train = tf.Variable(features[index[:n_train]], trainable=False)
    y_train = tf.Variable(Y[index[:n_train]], trainable=False)
    x_val = tf.Variable(features[index[n_train:]], trainable=False)

    y_val = Y[index[n_train:]]
    return n_train, x_train, y_train, x_val, y_val,

def get_model(qubit_num, layer_num, bias=None):
    weight_shape = (layer_num, qubit_num, 3)
    state_shape = (2 ** qubit_num)
    qlayer = build_circuit(state_shape, weight_shape, qubit_num, layer_num)
    
    ql = QuantumLayer(qlayer, weight_shape, bias)
    model = Sequential()
    model.add(ql)
    return model

def test_train(model, num_train, features_train, labels_train, features_val, labels_val):
    optimizer = optimizers.SGD(learning_rate=0.01, momentum=0.9, nesterov=True)
    loss_fn = losses.MeanSquaredError()
    iter = 55
    batch_size = 10
    print('-----begin train----------')
    for i in range(iter):
        batch_index = np.random.randint(0, num_train, (batch_size,))
        feats_train_batch = tf.gather(features_train, batch_index) 
        Y_train_batch = tf.gather(labels_train, batch_index)
        with tf.GradientTape() as tape:
            pred = model(feats_train_batch, training=True)
            loss = loss_fn(Y_train_batch, pred)
            gradients = tape.gradient(loss, model.trainable_variables)
            optimizer.apply_gradients(zip(gradients, model.trainable_variables))
            print(f'Loss : {loss.numpy()}')

    print('---------begin predict--------------')
    total_error = 0
    for k in range(features_val.shape[0]):
        test_x = features_val[k]
        pred = model(test_x)
        print(pred, labels_val[k])
        if abs(labels_val[k] - np.sign(pred.numpy())) > 1e-5:
            total_error = total_error + 1
            
    print(total_error)
    assert np.allclose(total_error, 0)


if __name__ == '__main__':
    file_path = "resource/iris_classes_data.txt"
    qubit_num, layer_num = 2, 6
    seed = 1024
    np.random.seed(seed)
    tf.random.set_seed(seed)
    bias = tf.Variable(0.0, trainable=True)
    model = get_model(qubit_num, layer_num, bias=bias)
    
    num_train, features_train, labels_train, features_val, labels_val, = get_data(file_path)
    test_train(model, num_train, features_train, labels_train, features_val, labels_val)
```
