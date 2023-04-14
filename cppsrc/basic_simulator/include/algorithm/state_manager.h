/*
 * File:   state_manager.h
 * Author: Cong Guo
 * Email:  cguo@spinq.io
 * Company: 深圳量旋科技有限公司（SpinQ）
 * Date:    09/2021
 *
 */

#ifndef _STATE_MANAGER_H_
#define _STATE_MANAGER_H_

#include "../utilities/circuit.h"
#include "../utilities/condition.h"
#include "quantum_state.h"

#include <vector>
#include <unordered_set>
#include <unordered_map>
#include <iostream>
using namespace std;

class state_manager {
public:
    void execute_inplace(const circuit & circ);
    void execute(const circuit & circ);
    vector<StateType> getStateVector();
    vector<double> getProbabilities();
private:
    size_t m_qubit_num;
    size_t m_clbit_num;
    vector<quantum_state> m_states;
    unordered_set<size_t> m_measured_qubits;
    unordered_map<condition, vector<size_t>, hash_condition> m_cond_state;
    unordered_map<size_t, condition> m_secondary_index; // clbit to condition
    
    bool check_qubits(const vector<gate_unit>::iterator & git);
    void invalidate_condition_entry(size_t clbit);
};

#endif