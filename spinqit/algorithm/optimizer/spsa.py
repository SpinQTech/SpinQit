from noisyopt import minimizeSPSA
from spinqit.algorithm import Optimizer


class SPSAOptimizer(Optimizer):
    def __init__(self,
                 maxiter: int = 100,
                 verbose=False,
                 a=1.,
                 c=1.,
                 **kwargs):
        super().__init__()
        self.niter = maxiter
        self.verbose = verbose
        self.c = c
        self.a = a
        self.kwargs = kwargs

    def optimize(self, fn):
        params = fn.params
        res = minimizeSPSA(fn, params,
                           niter=self.niter,
                           disp=self.verbose,
                           paired=False,
                           c=self.c, a=self.a, **self.kwargs)
        return res
