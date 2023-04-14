import numpy as np
import torch
from torch.autograd import Function


def _process_params(new_params):
    if hasattr(new_params, 'cpu'):
        new_params = new_params.cpu().detach().numpy()
    return new_params


class QuantumFunction(Function):
    """
    The class is for constructing the Pytorch Quantum model with our own quantum circuit.
    """

    @staticmethod
    def forward(ctx, params: torch.Tensor, expval_fn, state):
        ctx.torch_device = None
        if params.is_cuda:
            ctx.torch_device = params.get_device()

        _params = _process_params(params)

        expval_fn.update(_params)
        expval = torch.as_tensor(expval_fn.forward(state), device=ctx.torch_device)

        ctx.fn = expval_fn
        ctx.state = state
        ctx.params = _params
        return expval

    @staticmethod
    def backward(ctx, grad_output):
        expval_fn = ctx.fn
        _params = ctx.params
        state = ctx.state

        expval_fn.update(_params)
        _, gradients = expval_fn.backward(state)
        g_params = grad_output * torch.as_tensor(gradients, device=ctx.torch_device)
        return g_params, None, None


class QuantumModel(torch.nn.Module):
    def __init__(self,
                 expvalcost):
        super().__init__()
        init_params = expvalcost.params
        if isinstance(init_params, np.ndarray):
            init_params = torch.from_numpy(init_params).requires_grad_(True)
        else:
            init_params = init_params.clone().detach().requires_grad_(True)

        self.params = torch.nn.Parameter(init_params)
        expvalcost.update(self.params)
        self.quantum_fn = expvalcost

    def forward(self, state=None, circuit=None):
        if circuit is not None:
            self.quantum_fn.circuit = circuit
        if self.quantum_fn.backend_mode == 'spinq':

            if state is not None and len(state.size()) > 1:
                loss = torch.zeros(state.size(0))
                for i in range(state.size(0)):
                    loss[i] += QuantumFunction.apply(self.params, self.quantum_fn, state[i, :])
            else:
                loss = QuantumFunction.apply(self.params, self.quantum_fn, state)
            return loss
        else:
            return self.quantum_fn.forward(state)