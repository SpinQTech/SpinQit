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

#ifndef CONSTANTS_H
#define CONSTANTS_H

namespace constants
{
    constexpr double epsilon {1e-10};

    constexpr char qubit_num_attr[] = "qnum";
    constexpr char clbit_num_attr[] = "cnum";
    constexpr char edge_qubit_attr[] = "qubit";
    constexpr char edge_clbit_attr[] = "clbit";
    constexpr char edge_conbit_attr[] = "conbit";
    constexpr char node_name_attr[] = "name";
    constexpr char node_qubits_attr[] = "qubits";
    constexpr char node_params_attr[] = "params";
    constexpr char node_params_index[] = "pindex";
    constexpr char node_type_attr[] = "type";
    constexpr char node_cmp_attr[] = "cmp";
    constexpr char node_constant_attr[] = "constant";
    constexpr char gate_def[] = "def";
    constexpr char measurement[] = "MEASURE";

    constexpr int node_type_op { 0 };
    constexpr int node_type_caller { 1 };
    constexpr int node_type_def { 2 };
    constexpr int node_type_callee { 3 };
    constexpr int node_type_register { 4 };
    constexpr int node_type_init_qubit { 5 };
    constexpr int node_type_init_clbit { 6 }; 
}
#endif