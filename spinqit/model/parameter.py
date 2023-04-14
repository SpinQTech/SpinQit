from copy import deepcopy
from functools import reduce

import numpy as onp
from autograd import numpy as _np
from autograd.extend import primitive, defvjp
from autograd.tracer import Box
from autograd.numpy.numpy_boxes import ArrayBox
from autograd.numpy.numpy_vspaces import ComplexArrayVSpace, ArrayVSpace
from autograd.core import VSpace


@primitive
def asarray(vals, *args, **kwargs):
    """Gradient supporting autograd asarray"""
    if isinstance(vals, (onp.ndarray, _np.ndarray)):
        return _np.asarray(vals, *args, **kwargs)
    return _np.array(vals, *args, **kwargs)


def asarray_gradmaker(ans, *args, **kwargs):
    """Gradient maker for asarray"""
    del ans, args, kwargs
    return lambda g: g


defvjp(asarray, asarray_gradmaker, argnums=(0,))


class Parameter(_np.ndarray):
    """Constructs a SpinQ parameter for Parameterized Quantum Circuit.
    The Parameter is inherited by autograd.numpy, added the 'trainable', '_func' factors.
    which can be used by auto differentiation and other numpy basic operation

    Attributes:
        `trainable` : These attributes is considered in parameterized circuit,
                        to distinguish whether a param should be trained or not.

        '_func': Record the function that operate on the parameter, for auto differentiation.
                This attributes can be further improved
    """

    def __new__(cls, input_array, *args, trainable=True, _func=None, **kwargs):
        obj = asarray(input_array, *args, **kwargs)

        if isinstance(obj, onp.ndarray):
            obj = obj.view(cls)
            obj.trainable = trainable
            if _func is None:
                obj._func = []
            else:
                obj._func = _func

        return obj

    def __array_finalize__(self, obj):
        # pylint: disable=attribute-defined-outside-init
        if obj is None:  # pragma: no cover
            return

        self.trainable = getattr(obj, "trainable", None)
        self._func = getattr(obj, '_func', [])

    def __repr__(self):
        string = super().__repr__()
        return string[:-1] + f", trainable={self.trainable})"

    def __array_wrap__(self, obj):
        out_arr = Parameter(obj, trainable=self.trainable, _func=self._func)
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
            isinstance(x, onp.ndarray) and getattr(x, "trainable", True) for x in inputs
        )
        _func = [getattr(x, "_func", []) for x in inputs if isinstance(x, onp.ndarray)]

        # Iterate through the ufunc outputs and convert each to Parameter.
        # We also correctly set the trainable attribute.
        for i in range(len(ufunc_output)):  # pylint: disable=consider-using-enumerate
            ufunc_output[i] = Parameter(ufunc_output[i], trainable=trainable,  _func=_func[i])

        if len(ufunc_output) == 1:
            # the ufunc has a single output so return a single Parameter
            return ufunc_output[0]

        # otherwise we must return a tuple of tensors
        return tuple(ufunc_output)

    def __getitem__(self, *args, **kwargs):
        item = super().__getitem__(args, **kwargs)
        _func = deepcopy(self._func)
        if not isinstance(item, Parameter):
            item = Parameter(item, trainable=self.trainable, _func=_func)
        else:
            setattr(item, '_func', _func)
        return item

    def __hash__(self):
        if self.ndim == 0:
            # Allowing hashing if the Parameter is a scalar.
            # We hash both the scalar value *and* the differentiability information,
            # to match the behaviour of PyTorch.
            return hash((self.item(), self.trainable))

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
        try:
            iterator = super().__iter__()
            for i in iterator:
                yield i
        except TypeError:
            yield self

    def __len__(self):
        """
        For the special case:

            x = Parameter(1.)
            print(len(x))
            Although `x` is a numpy array but a 0-D array, to avoid this problem
        """
        try:
            length = super().__len__()
        except TypeError:
            length = 1
        return length

    @property
    def func(self):
        """
        Return the `function` for the auto differentiation
        """
        if len(self._func) == 1:
            return ParameterExpression(self._func[0])

        def fn(x):
            for f in self._func:
                x = f(x)
            return x

        return ParameterExpression(fn)

    @func.setter
    def func(self, fun):
        """
        Record the function, add the function to the _func.
        """
        self._func.append(fun)

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


class ParameterExpression:
    def __init__(self, fn):
        if isinstance(fn, ParameterExpression):
            self.fn = fn.fn
        else:
            self.fn = fn

    def __call__(self, params):
        _params = self.fn(params)
        if isinstance(_params, Parameter):
            _params.func = self.fn
        return _params


class NonDifferentiableError(Exception):
    """Exception raised if attempting to differentiate non-trainable
    :class:`~.Parameter using Autograd."""


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

        raise NonDifferentiableError(
            f"{x} is non-differentiable. Set the requires_grad attribute to True."
        )

    return ArrayBox(x, *args)


Box.type_mappings[Parameter] = parameter_to_arraybox
VSpace.mappings[Parameter] = lambda x: ComplexArrayVSpace(x) if onp.iscomplexobj(x) else ArrayVSpace(x)

if __name__ == '__main__':
    pass
