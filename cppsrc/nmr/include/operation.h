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

#ifndef OPERATION_H
#define OPERATION_H

#include <string>
#include <sstream>
using namespace std;

class Operation
{
public:
    double m_angle;
    int m_control_qubit;
    int m_control_qubit2;
    int m_delay;
    int m_qubit_index;
    int m_timeslot;
    string m_type;

    Operation();
    Operation(const char * gate, int time_slot, int qubit0);
    Operation(const char * gate, int time_slot, int qubit0, double angle);
    Operation(const char * gate, int time_slot, int qubit0, int qubit1);
    Operation(const char * gate, int time_slot, int qubit0, int qubit1, int qubit2);
    string to_string();
};
#endif