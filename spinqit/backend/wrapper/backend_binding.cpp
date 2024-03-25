/**
 * Copyright 2021 SpinQ Technology Co., Ltd.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "basic_simulator.h"
#include "nmr.h"
#include "model/result.h"
#include <pybind11/stl.h>
#include <pybind11/complex.h>
#include <pybind11/pybind11.h>

namespace py = pybind11;

PYBIND11_MODULE(spinq_backends, m) {
    m.doc() = "SpinQ Backends";
    
    py::class_<BasicSimulator>(m, "BasicSimulator")
    .def(py::init<>())
    .def("execute", &BasicSimulator::execute);
    // .def("print_circuit", &BasicSimulator::printCircuit);

    py::class_<Nmr>(m, "NMR")
    .def(py::init<>())
    .def("execute", &Nmr::execute);

    py::class_<Result>(m, "Result")
    .def(py::init<>())
    .def_readwrite("states", &Result::states)
    .def_readwrite("probabilities", &Result::probabilities)
    .def_property_readonly("counts", &Result::get_counts)
    .def("get_random_reading", &Result::get_random_reading);
}