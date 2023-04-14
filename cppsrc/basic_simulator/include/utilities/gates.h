/*
 * File:    gates.h
 * Author:  Jingen Xiang
 * Email:   jxiang@spinq.io
 * Company: 深圳量旋科技有限公司（SpinQ）
 * Date:    01/2019
 *
 */

#ifndef _GATES_H_
#define _GATES_H_

#include <iostream>
#include <complex>
#include <string>
#include <math.h>
#include "gateAttr.h"
#include "matrix.h"
#include "simple_json.h"
#include "condition.h"

#define SQRT2          1.4142135624
#ifndef PI
#define PI             3.1415926532
#endif
#define INVALID_QUBIT  0xFFFF

using namespace std;

typedef complex<double> StateType;

enum GATE_INDEX { INVALID_GATE = 0
                , I, H
                , X, Y, Z
                , X90, Y90, Z90
                , Rx, Ry, Rz, P        // attribute angle
                , S, Sd, T, Td
                , CNOT, YCON, ZCON
                , CCX
                , MEASURE};

class gates {
public:
    static GATE_INDEX getGateIndex(const string & gate_name);
    static string getGateName(GATE_INDEX index);

    static matrix<StateType> getGateI();
    static matrix<StateType> getGateH();
    static matrix<StateType> getGateX();
    static matrix<StateType> getGateY();
    static matrix<StateType> getGateZ();
    static matrix<StateType> getGateX90();
    static matrix<StateType> getGateY90();
    static matrix<StateType> getGateZ90();
    static matrix<StateType> getGateXr(double angle);
    static matrix<StateType> getGateYr(double angle);
    static matrix<StateType> getGateZr(double angle);
    static matrix<StateType> getGateP(double angle);
    static matrix<StateType> getGateS();
    static matrix<StateType> getGateSd();
    static matrix<StateType> getGateT();
    static matrix<StateType> getGateTd();
    static matrix<StateType> getGateCNOT();
    static matrix<StateType> getGateYCON();
    static matrix<StateType> getGateZCON();
    static matrix<StateType> getGateCCX();

    static bool executeGateI(vector<StateType> & state, size_t qubit);
    static bool executeGateH(vector<StateType> & state, size_t qubit);
    static bool executeGateX(vector<StateType> & state, size_t qubit);
    static bool executeGateY(vector<StateType> & state, size_t qubit);
    static bool executeGateZ(vector<StateType> & state, size_t qubit);
    static bool executeGateX90(vector<StateType> & state, size_t qubit);
    static bool executeGateY90(vector<StateType> & state, size_t qubit);
    static bool executeGateZ90(vector<StateType> & state, size_t qubit);
    static bool executeGateXr(vector<StateType> & state, size_t qubit, double theta);
    static bool executeGateYr(vector<StateType> & state, size_t qubit, double theta);
    static bool executeGateZr(vector<StateType> & state, size_t qubit, double theta);
    static bool executeGateP(vector<StateType> & state, size_t qubit, double theta);
    static bool executeGateS(vector<StateType> & state, size_t qubit);
    static bool executeGateSd(vector<StateType> & state, size_t qubit);
    static bool executeGateT(vector<StateType> & state, size_t qubit);
    static bool executeGateTd(vector<StateType> & state, size_t qubit);
    static bool executeGateCNOT( vector<StateType> & states
                               , size_t qubit_control
                               , size_t qubit_target);
    static bool executeGateYCON( vector<StateType> & states
                               , size_t qubit_control
                               , size_t qubit_target);
    static bool executeGateZCON( vector<StateType> & states
                               , size_t qubit_control
                               , size_t qubit_target);
    static bool executeGateCCX( vector<StateType> & states
                               , size_t qubit_control1
                               , size_t qubit_control2
                               , size_t qubit_target);

    static bool executeGateMeasure( vector<StateType> & states
                                  , size_t qubit
                                  , bool zero);

    static bool executeGate( vector<StateType> & states
                           , const size_t qubits[]
                           , const string & gate_name);

    static bool executeGate( vector<StateType> & states
                           , const size_t qubits[]
                           , const string & gate_name
                           , double theta);

    static bool executeGate( vector<StateType> & states
                           , const size_t qubits[]
                           , GATE_INDEX gate_index);

    static bool executeGate( vector<StateType> & states
                           , const size_t qubits[]
                           , GATE_INDEX gate_index
                           , double theta);
};

class gate_unit {
private:
    string        m_gate_name;   // the gate name
    GATE_INDEX    m_gate_index;  // the gate index in our system
    size_t        m_qubit;       // the matrix of gate
    size_t        m_qubit2;      // the target qubit for CNOT or the second control qubit for CCX
    size_t        m_qubit3;      // the target qubit for CCX
    size_t        m_qubit_num;   // the qubits number of gates apple to
    double        m_angle;       // the attribute rotate angle, works for Rx, Ry, Rz only
    size_t        m_clbit;       // the clbit if the gate is measure
    condition     m_condition;   // the if condition for this gate

public:
    gate_unit();
    gate_unit(const string & name, size_t qubit, size_t qubit2);
    gate_unit(const GATE_INDEX index, size_t qubit, size_t qubit2);
    gate_unit(const string & name, size_t qubit);
    gate_unit(const string & name, size_t qubit, double theta);
    gate_unit(const GATE_INDEX index, size_t qubit);
    gate_unit(const GATE_INDEX index, size_t qubit, double theta);
    gate_unit(const string & name, size_t qubit, size_t qubit2, size_t qubit3);
    gate_unit(const GATE_INDEX index, size_t qubit, size_t qubit2, size_t qubit3);

    string getGateName() const;
    GATE_INDEX getGateIndex() const;
    size_t getQubit() const;
    size_t getQubit2() const;
    size_t getQubit3() const;
    size_t getQubitNum() const;
    double getAngle() const;

    void setClbitTarget(size_t clbit);
    size_t getClbitTarget();
    bool hasCondition() const;
    void setCondition(const condition & con);
    condition getCondition() const;

    bool execute(vector<StateType> & states);

    string toJSON();
    bool parseFromJSON(const string & str_json);
};  // end of gate_unit;

inline bool operator==(const gate_unit & gate1, const gate_unit & gate2)
{
    if (  gate1.getGateName().compare(gate2.getGateName()) == 0
       && gate1.getGateIndex() == gate2.getGateIndex()
       && gate1.getQubit() == gate2.getQubit()
       && gate1.getQubit2() == gate2.getQubit2()
       && gate1.getQubit3() == gate2.getQubit3()
       && gate1.getQubitNum() == gate2.getQubitNum()
       && gate1.getAngle() == gate2.getAngle()) {
        return true;
    }

    return false;
}

inline ostream & operator<<(ostream & out, const gate_unit & gate)
{
    out << "gate name : " << gate.getGateName() << ", \n"
        << "gate index : " << gate.getGateIndex() << ", \n"
        << "qubit : " << gate.getQubit() << ", \n"
        << "qubit2 : " << gate.getQubit2() << ", \n"
        << "qubit3 : " << gate.getQubit3() << ", \n"
        << "qubit number : " << gate.getQubitNum() << "\n";
    if ( gate.getGateIndex() == GATE_INDEX::Rx
       || gate.getGateIndex() == GATE_INDEX::Ry
       || gate.getGateIndex() == GATE_INDEX::Rz) {
        out << "rotation angle : " << gate.getAngle() << "\n";
    }

    return out;
}

#endif // _GATES_H_
