/*
 * File:   quantum_state.h
 * Author: Jingen Xiang
 * Email:  jxiang@spinq.io
 * Company: 深圳量旋科技有限公司（SpinQ）
 * Date:    02/2019
 *
 */

#ifndef _QUANTUM_STATE_H_
#define _QUANTUM_STATE_H_

#include <cmath>
#include <iostream>
#include <complex>
#include <map>
#include "../utilities/circuit.h"

using namespace std;

typedef complex<double> StateType;

class quantum_state {
private:
    size_t                    m_qubit_num;          // the number of quantum bit
    size_t                    m_clbit_num;          // the number of classic bit.
    vector<vector<StateType>> m_state;              // the state of quantum.
    
    double                    m_state_probability;
    vector<int>               m_clbit_value;        // 
    map<size_t, size_t>       m_clbit_target;       // map from classical bit to qubit  
    
public:
    quantum_state();
    quantum_state(size_t qubit_num);
    quantum_state(size_t qubit_num, size_t clbit_num);
    quantum_state(size_t qubit_num, const vector<StateType> & state);
    quantum_state(const quantum_state & state_obj);
    ~quantum_state();

    size_t getQubitNum();
    size_t getQubitNum() const;
    size_t getClbitNum();
    size_t getClbitNum() const;
    vector<vector<StateType>> getAllQuantumState();
    vector<vector<StateType>> getAllQuantumState() const;
    vector<StateType> getInitialQuantumState();
    vector<StateType> getInitialQuantumState() const;
    vector<StateType> & getCurrentQuantumState();
    const vector<StateType> & getCurrentQuantumState() const;
    double getStateProb() const;

    bool reset();   // reset the quantum state to the initial quantum state.
    bool reset(size_t qubit_num);
    void appendQuantumState(const vector<StateType>& new_state);
    
    bool executeInitial(const circuit & cir); // execute circuit from initial
    bool execute(const circuit & cir);        // execute circuit from current
    vector<double> measure();            // measure the last quantum states;
    vector<vector<double>> measureAll(); // measure all quantum states.

    quantum_state measure_single_qubit(int qubit, int clbit);
    bool check_condition(const condition & cond);

//     void lazy_measure();
//     double calc_cond_prob(const condition & cond);

// private:
//     double calc_val_prob(const vector<int> & clbits, int val);
//     double calc_range_prob(const vector<int> & clbits, int beg, int end);
};

inline bool operator==(const quantum_state & qs1, const quantum_state & qs2)
{
    vector<vector<StateType>> state1 = qs1.getAllQuantumState();
    vector<vector<StateType>> state2 = qs2.getAllQuantumState();

    if (qs1.getQubitNum() != qs2.getQubitNum()) {
        return false;
    }

    if (state1.size() != state2.size()) {
        return false;
    }

    for (size_t i = 0; i < state1.size(); ++i) {
        if (state1[i] != state2[i]) {
            return false;
        }
    }

    return true;
}

inline ostream & operator<<(ostream & out, const quantum_state & qs)
{
    out << "qubit number   : " << qs.getQubitNum() << std::endl;
    out << "classic number : " << qs.getClbitNum() << std::endl;

    vector<vector<StateType>> state = qs.getAllQuantumState();
    vector<vector<StateType>>::iterator it1;
    size_t state_index = 0;
    for (it1 = state.begin(); it1 != state.end(); ++it1) {
        out << "state " << state_index++ << " : ";
        vector<StateType>::iterator it2;
        for (it2 = it1->begin(); it2 != it1->end(); ++it2) {
            out << *(it2) << "  ";
        }
        out << endl;
    }

    out << endl;
    return out;
}

#endif // _QUANTUM_STATE_H_
