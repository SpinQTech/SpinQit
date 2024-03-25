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

from autoray import register_backend
from autoray.autoray import (
    register_function, _MODULE_ALIASES, _CUSTOM_WRAPPERS, _FUNCS, complex_add_re_im, svd_not_full_matrices_wrapper,
)

from spinqit import Parameter
from spinqit.utils.function import get_interface

# ------------------------- Pytorch -------------------------------

try:
    import torch

    IMPORTED_TORCH = True
except ImportError as e:
    IMPORTED_TORCH = False


def torch_asarray_wrapper(old_fn):
    def new_fn(tensor, **kwargs):
        interface = get_interface(tensor)
        if interface == 'paddle':
            import paddle
            tensor = torch.from_dlpack(paddle.utils.dlpack.to_dlpack(tensor))
        elif interface == 'tensorflow':
            import tensorflow as tf
            tensor = torch.from_dlpack(tf.experimental.dlpack.to_dlpack(tf.convert_to_tensor(tensor)))
        elif interface == 'numpy':
            tensor = Parameter(tensor)
        elif interface == 'jax':
            tensor = Parameter(tensor)
        return old_fn(tensor, **kwargs)

    return new_fn


if IMPORTED_TORCH:
    register_function(backend='torch', name='asarray', fn=torch_asarray_wrapper, wrap=True)

# ------------------------- Paddle --------------------------
try:
    import paddle

    IMPORTED_PADDLE = True
except ImportError as e:
    IMPORTED_PADDLE = False


def paddle_asarray_fn(tensor, **kwargs):
    interface = get_interface(tensor)
    if interface == 'torch':
        import torch
        tensor = paddle.utils.dlpack.from_dlpack(torch.utils.dlpack.to_dlpack(tensor))
    elif interface == 'tensorflow':
        import tensorflow as tf
        tensor = paddle.utils.dlpack.from_dlpack(tf.experimental.dlpack.to_dlpack(tf.convert_to_tensor(tensor)))
    return paddle.to_tensor(tensor, **kwargs)


if IMPORTED_PADDLE:
    register_backend(paddle.Tensor, 'paddle')
    register_function(backend='paddle', name='asarray', fn=paddle_asarray_fn)
    register_function(backend='paddle', name='astype', fn=paddle.cast)


# -------------------------------- SpinQ ---------------------------------#

def spinq_asarray_fn(tensor, **kwargs):
    from spinqit.utils.function import requires_grad
    interface = get_interface(tensor)
    if interface == 'torch':
        tensor = tensor.cpu().detach().numpy()
    if not kwargs.get('trainable', None):
        kwargs.update(dict(trainable=requires_grad(tensor)))
    return Parameter(tensor, **kwargs)


def spinq_where_wrapper(fn):
    def new_fn(*args, **kwargs):

        trainable = True
        if len(args) > 1:
            x = args[1]
            if hasattr(x, 'trainable'):
                trainable = x.trainable
        elif len(args) == 0:
            x = kwargs.get('x', None)
            if x is not None:
                trainable = x.trainable
        res = fn(*args, **kwargs)
        return Parameter(res, trainable=trainable)
    return new_fn


register_backend(Parameter, 'spinq')
_MODULE_ALIASES["spinq"] = "autograd.numpy"
_CUSTOM_WRAPPERS["spinq", "linalg.svd"] = svd_not_full_matrices_wrapper
_FUNCS["spinq", "complex"] = complex_add_re_im
register_function(backend='spinq', name='asarray', fn=spinq_asarray_fn)
register_function(backend='numpy', name='where', fn=spinq_where_wrapper, wrap=True)
