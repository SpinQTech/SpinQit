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

#include "operation.h"

Operation::Operation()
{
    m_angle = 0.0;
    m_control_qubit = -1;
    m_control_qubit2 = -1;
    m_delay = 0;
    m_qubit_index = -1;
    m_timeslot = 0;
}

Operation::Operation(const char * gate, int time_slot, int qubit0)
{
    m_type = gate;
    m_timeslot = time_slot;
    m_qubit_index = qubit0;
    m_angle = 0.0;
    m_control_qubit = -1;
    m_control_qubit2 = -1;
    m_delay = 0;
}

Operation::Operation(const char * gate, int time_slot, int qubit0, double angle)
{
    m_type = gate;
    m_timeslot = time_slot;
    m_qubit_index = qubit0;
    m_angle = angle;
    m_control_qubit = -1;
    m_control_qubit2 = -1;
    m_delay = 0;
}

Operation::Operation(const char * gate, int time_slot, int qubit0, int qubit1)
{
    m_type = gate;
    m_timeslot = time_slot;
    m_control_qubit = qubit0;
    m_qubit_index = qubit1;
    m_angle = 0.0;
    m_control_qubit2 = -1;
    m_delay = 0;
}
    
Operation::Operation(const char * gate, int time_slot, int qubit0, int qubit1, int qubit2)
{
    m_type = gate;
    m_timeslot = time_slot;
    m_control_qubit = qubit0;
    m_control_qubit2 = qubit1;
    m_qubit_index = qubit2;
    m_angle = 0.0;
    m_delay = 0;
}

string Operation::to_string()
{
    stringstream ss;
    ss << "{";
    ss << "\"angle\":" << m_angle << ",";
    ss << "\"controlQubit\":" << m_control_qubit << ",";
    ss << "\"controlQubit2\":" << m_control_qubit2 << ",";
    ss << "\"delay\":" << m_delay << ",";
    ss << "\"qubitIndex\":" << m_qubit_index << ",";
    ss << "\"timeslot\":" << m_timeslot << ",";
    ss << "\"type\":\"" << m_type << "\"";
    ss << "}";
    return ss.str();
}