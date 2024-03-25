# Copyright 2023 SpinQ Technology Co., Ltd.
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
from autograd.core import make_vjp as _make_vjp
import autograd.numpy as anp
from autograd.extend import vspace
from autograd.wrap_util import unary_to_nary
from autograd import elementwise_grad


class qgrad:
    def __init__(self, fun):
        self._forward = None
        self._fun = fun

    def __call__(self, *params):
        self._grad_fn = self._get_grad_fn(self._fun)
        grad_value, ans = self._grad_fn(*params)
        self._forward = ans
        return grad_value

    @property
    def forward(self):
        return self._forward

    @staticmethod
    @unary_to_nary
    def _get_grad_fn(fun, x):
        vjp, ans = _make_vjp(fun, x)
        if vspace(ans).iscomplex:
            return elementwise_grad(lambda x: anp.real(fun(x)))(x), ans
        return vjp(vspace(ans).ones()), ans
