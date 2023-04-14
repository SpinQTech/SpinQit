/*
 * File: circuit.h
 * Author:  Jingen Xiang
 * Email:   jxiang@spinq.io
 * Company: 深圳量旋科技有限公司（SpinQ）
 * Date:    01/2019
 *
 */

#ifndef _CIRCUIT_H_
#define _CIRCUIT_H_

#include <vector>
#include <complex>
#include <iostream>
#include <assert.h>
#include "gates.h"
#include "simple_json.h"

class circuit_unit {
private:
    size_t            m_qubit_num;    // the number of qubits
    size_t            m_measure_num;  // the number of measure gates
    vector<gate_unit> m_circuit_unit; // the gates applied to this circuit unit

public:
    circuit_unit();
    circuit_unit(const vector<gate_unit> & gates);

    size_t getQubitNum() const;
    size_t getMeasureNum() const;
    vector<gate_unit> getCircuitUnit() const;

    bool execute(vector<StateType> & states);

    string toJSON();
    bool parseFromJSON(const string & str_json);
};

inline bool operator==( const circuit_unit & circuit1
                      , const circuit_unit & circuit2)
{
    if (  circuit1.getQubitNum() == circuit2.getQubitNum()
       && circuit1.getCircuitUnit() == circuit2.getCircuitUnit()) {
        return true;
    }

    return false;
}


class circuit {
private:
    size_t               m_qubit_num;    // the number of qubits;
    size_t               m_clbit_num;    // the number of clbits;
    size_t               m_circuit_num;  // the number of circuit unit;
    vector<circuit_unit> m_circuit;      // the list of circuit unit;

public:
    circuit();
    circuit(const vector<circuit_unit> & circuit);
    circuit(const vector<circuit_unit> & circuit, size_t clbit_num);

    ~circuit();

    void setCircuit(const vector<circuit_unit> & circuit);

    size_t getQubitNum() const;
    size_t getClbitNum() const;
    size_t getCircuitNum() const;
    vector<circuit_unit> getCircuit() const;

    bool execute(vector<StateType> & states);

    string toJSON();
    bool parseFromJSON(const string & json);
};

inline bool operator==(const circuit & circuit1, const circuit & circuit2)
{
    if (  circuit1.getQubitNum() == circuit2.getQubitNum()
       && circuit1.getCircuitNum() == circuit2.getCircuitNum()
       && circuit1.getCircuit() == circuit2.getCircuit()) {
        return true;
    }

    return false;
}

#endif // _CIRCUIT_H_
