from scipy.optimize import minimize

from spinqit.algorithm.optimizer.optimizer import Optimizer


class ScipyOptimizer(Optimizer):
    def __init__(self, maxiter: int = 10000,
                 tolerance: float = 1e-4,
                 verbose=False,
                 method='COBYLA',
                 **kwargs):
        super(ScipyOptimizer, self).__init__()
        if kwargs.get('option', None):
            self.options = kwargs.get('option', None)
        else:
            self.options = {'maxiter': maxiter,
                            'disp': verbose}
        self.tol = tolerance
        self.method = method
        self.kwargs = kwargs

    def optimize(self, fn):
        params = fn.params
        res = minimize(fn, params,
                       method=self.method, options=self.options,
                       tol=self.tol, **self.kwargs)
        return res
