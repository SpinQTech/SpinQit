# This code is part of Qiskit.
#
# (C) Copyright IBM 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


"""InnerProduct circuit."""


from spinqit.qiskit.circuit import QuantumRegister, QuantumCircuit


class InnerProduct(QuantumCircuit):
    r"""A 2n-qubit Boolean function that computes the inner product of
    two n-qubit vectors over :math:`F_2`.

    This implementation is a phase oracle which computes the following transform.

    .. math::

        \mathcal{IP}_{2n} : F_2^{2n} \rightarrow {-1, 1}
        \mathcal{IP}_{2n}(x_1, \cdots, x_n, y_1, \cdots, y_n) = (-1)^{x.y}

    The corresponding unitary is a diagonal, which induces a -1 phase on any inputs
    where the inner product of the top and bottom registers is 1. Otherwise it keeps
    the input intact.

    .. parsed-literal::


        q0_0: ─■──────────
               │
        q0_1: ─┼──■───────
               │  │
        q0_2: ─┼──┼──■────
               │  │  │
        q0_3: ─┼──┼──┼──■─
               │  │  │  │
        q1_0: ─■──┼──┼──┼─
                  │  │  │
        q1_1: ────■──┼──┼─
                     │  │
        q1_2: ───────■──┼─
                        │
        q1_3: ──────────■─


    Reference Circuit:
        .. jupyter-execute::
            :hide-code:

            from spinqit.qiskit.circuit.library import InnerProduct
            import qiskit.tools.jupyter
            circuit = InnerProduct(4)
            %circuit_library_info circuit
    """

    def __init__(self, num_qubits: int) -> None:
        """Return a circuit to compute the inner product of 2 n-qubit registers.

        Args:
            num_qubits: width of top and bottom registers (half total circuit width)
        """
        qr_a = QuantumRegister(num_qubits)
        qr_b = QuantumRegister(num_qubits)
        super().__init__(qr_a, qr_b, name="inner_product")

        for i in range(num_qubits):
            self.cz(qr_a[i], qr_b[i])
