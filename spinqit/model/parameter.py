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
import numpy as onp
from autograd import numpy as anp
from autograd.core import VSpace
from autograd.extend import primitive, defvjp
from autograd.numpy.numpy_boxes import ArrayBox
from autograd.numpy.numpy_vspaces import ComplexArrayVSpace, ArrayVSpace
from autograd.tracer import Box
from autoray.lazy import LazyArray


@primitive
def asarray(vals, *args, **kwargs):
    """Gradient supporting autograd asarray"""
    if isinstance(vals, (onp.ndarray, anp.ndarray)):
        return anp.asarray(vals, *args, **kwargs)
    return anp.array(vals, *args, **kwargs)


def asarray_gradmaker(ans, *args, **kwargs):
    """Gradient maker for asarray"""
    del ans, args, kwargs
    return lambda g: g


defvjp(asarray, asarray_gradmaker, argnums=(0,))


class Parameter(anp.ndarray):
    """Constructs a SpinQ parameter for Parameterized Quantum Circuit.
    The Parameter is inherited by autograd.numpy, added the 'trainable' factors.
    which can be used by auto differentiation and other numpy basic operation

    Attributes:
        `trainable` : These attributes is considered in parameterized circuit,
                        to distinguish whether a param should be trained or not.

    """

    def __new__(cls,
                input_array,
                *args,
                trainable=True,
                **kwargs):
        obj = asarray(input_array, *args, **kwargs)

        if isinstance(obj, onp.ndarray):
            obj = obj.view(cls)
            obj.trainable = trainable

        return obj

    def __array_finalize__(self, obj):
        # pylint: disable=attribute-defined-outside-init
        if obj is None:  # pragma: no cover
            return

        self.trainable = getattr(obj, "trainable", None)

    def __repr__(self):
        string = super().__repr__()
        return string[:-1] + f", trainable={self.trainable})"

    def __array_wrap__(self, obj):
        out_arr = Parameter(obj, trainable=self.trainable,
                            )
        return super().__array_wrap__(out_arr)

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        # pylint: disable=no-member,attribute-defined-outside-init

        # unwrap any outputs the ufunc might have
        outputs = [i.view(onp.ndarray) for i in kwargs.get("out", ())]

        if outputs:
            # Insert the unwrapped outputs into the keyword
            # args dictionary, to be passed to ndarray.__array_ufunc__
            outputs = tuple(outputs)
            kwargs["out"] = outputs
        else:
            # If the ufunc has no ouputs, we simply
            # create a tuple containing None for all potential outputs.
            outputs = (None,) * ufunc.nout

        # unwrap the input arguments to the ufunc
        args = [i.unwrap() if hasattr(i, "unwrap") else i for i in inputs]

        # call the ndarray.__array_ufunc__ method to compute the result
        # of the vectorized ufunc
        res = super().__array_ufunc__(ufunc, method, *args, **kwargs)

        if ufunc.nout == 1:
            res = (res,)

        # construct a list of ufunc outputs to return
        ufunc_output = [
            (onp.asarray(result) if output is None else output)
            for result, output in zip(res, outputs)
        ]

        # if any of the inputs were trainable, the output is also trainable
        trainable = any(
            (isinstance(x, Parameter) and getattr(x, "trainable", True)) for x in inputs
        )

        # Iterate through the ufunc outputs and convert each to Parameter.
        # We also correctly set the trainable attribute.
        for i in range(len(ufunc_output)):  # pylint: disable=consider-using-enumerate
            ufunc_output[i] = Parameter(ufunc_output[i], trainable=trainable)

        if len(ufunc_output) == 1:
            # the ufunc has a single output so return a single Parameter
            return ufunc_output[0]

        # otherwise we must return a tuple of tensors
        return tuple(ufunc_output)

    def __getitem__(self, *args, **kwargs):
        item = super().__getitem__(*args, **kwargs)
        if not isinstance(item, Parameter):
            item = Parameter(item, trainable=self.trainable, )
        return item

    def __hash__(self):
        if self.ndim == 0:
            # Allowing hashing if the Parameter is a scalar.
            # We hash both the scalar value *and* the differentiability information,
            # to match the behaviour of PyTorch.
            return hash((self.item(), self.trainable,))

        raise TypeError("unhashable type: 'Parameter'")

    def __reduce__(self):
        # Called when pickling the object.
        # Numpy ndarray uses __reduce__ instead of __getstate__ to prepare an object for
        # pickling. self.trainable needs to be included in the tuple returned by
        # __reduce__ in order to be preserved in the unpickled object.
        reduced_obj = super().__reduce__()
        # The last (2nd) element of this tuple holds the data. Add trainable to this:
        full_reduced_data = reduced_obj[2] + (self.trainable,)
        return reduced_obj[0], reduced_obj[1], full_reduced_data

    def __setstate__(self, reduced_obj) -> None:
        # Called when unpickling the object.
        # Set self.trainable with the last element in the tuple returned by __reduce__:
        # pylint: disable=attribute-defined-outside-init,no-member
        self.trainable = reduced_obj[-1]
        # And call parent's __setstate__ without this element:
        super().__setstate__(reduced_obj[:-1])

    def __round__(self, n=None):
        return onp.round(self, n)

    def __iter__(self):
        """
        For the special case:

            x = Parameter(1.)
            for i in x:
                print(i)
            Although `x` is a numpy array but not iterable, to avoid this problem
        """
        if self.ndim == 0:
            yield self
        yield from super().__iter__()

    def __len__(self):
        """
        For the special case:

            x = Parameter(1.)
            print(len(x))
            Although `x` is a numpy array but a 0-D array, to avoid this problem
        """
        if self.ndim == 0:
            return 1
        return super().__len__()

    def unwrap(self):
        """Converts the Parameter to a standard, non-differentiable NumPy ndarray or Python scalar if
        the Parameter is 0-dimensional.

        All information regarding differentiability of the Parameter will be lost.
        """
        if self.ndim == 0:
            return self.view(onp.ndarray).item()

        return self.view(onp.ndarray)

    def numpy(self):
        """Converts the Parameter to a standard, non-differentiable NumPy ndarray or Python scalar if
        the Parameter is 0-dimensional.
        """
        return self.unwrap()


LazyParameter = LazyArray
LazyParameter.__name__ = 'PlaceHolder'

LazyParameter.__deepcopy__ = lambda self, memodict={}: LazyParameter(
    fn=self.fn,
    args=self.args,
    kwargs=self.kwargs,
    backend=self._backend,
    shape=self.shape,
    deps=self.deps,
)


class PlaceHolder:
    def __new__(cls, shape, backend='autograd'):
        return LazyParameter.from_shape(shape, backend=backend)


def parameter_to_arraybox(x, *args):
    """Convert a :class:`~.Parameter` to an Autograd ``ArrayBox``.

    Args:
        x (array_like): Any data structure in any form that can be converted to
            an array. This includes lists, lists of tuples, tuples, tuples of tuples,
            tuples of lists and ndarrays.

    Returns:
        autograd.numpy.numpy_boxes.ArrayBox: Autograd ArrayBox instance of the array

    Raises:
        NonDifferentiableError: if the provided tensor is non-differentiable
    """
    if isinstance(x, Parameter):
        if x.trainable:
            return ArrayBox(x, *args)

    return ArrayBox(x, *args)


Box.type_mappings[Parameter] = parameter_to_arraybox
VSpace.mappings[Parameter] = lambda x: ComplexArrayVSpace(x) if onp.iscomplexobj(x) else ArrayVSpace(x)
