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
try:
    import tensorflow as tf
except ImportError:
    raise ImportError(
        'You should install tensorflow first, use `pip install tensorflow` '
    )


def _validate_params(qlayer, params):
    if len(params) != len(qlayer.place_holder):
        raise ValueError(
            f'The number of parameter is wrong. The circuit need {len(qlayer.place_holder)} args, but got {len(params)}'
        )
    for param in params:
        if not isinstance(param, (tf.Variable, tf.Tensor)):
            raise ValueError(
                'The parameters for `tf` interface should be tf.Tensor'
            )

def get_quantum_func(qlayer):
    @tf.custom_gradient
    def quantum_op(*all_params):
        loss, backward_fn = qlayer.backend.get_value_and_grad_fn(qlayer.ir,
                                                                    qlayer.config,
                                                                    qlayer.measure_op,
                                                                    qlayer.place_holder,
                                                                    qlayer.grad_method)(params=all_params)
        if not isinstance(loss, dict):
            loss = tf.convert_to_tensor(loss)

        def grad_fn(dy):
            gradients = backward_fn(dy.numpy())
            g_params = tuple(tf.convert_to_tensor(v) for v in gradients)
            return *g_params,

        return loss, grad_fn
    return quantum_op

class QuantumLayer(tf.keras.layers.Layer):
    def __init__(self, qlayer, weight_shape, bias=None):
        super(QuantumLayer, self).__init__()
        self.w = tf.Variable(0.01 * tf.random.normal(shape=(weight_shape), mean=0, stddev=1.0), trainable=True)
        self.b = bias
        self.qlayer = qlayer

    def call(self, state):
        qop = get_quantum_func(self.qlayer)
        loss_list = []
        if len(state.shape) > 1:
            for i in range(state.shape[0]):
                loss = qop(state[i], self.w)
                loss_list.append(loss)
                res = tf.stack(loss_list)
        else:
            res = qop(state, self.w)
        
        if self.b is not None:
            return res + self.b
        return res

def execute(qlayer, *params):
    _validate_params(qlayer, params)
    if qlayer.backend_mode not in ['torch', 'spinq', 'jax', 'nmr', 'qasm']:
        raise ValueError(
            f'The backend_mode only support `torch`, `spinq`, `jax`, `nmr` and `qasm`, '
            f'but got backend {qlayer.backend_mode}'
        )
    quantum_op = get_quantum_func(qlayer)
    return quantum_op(*params)
