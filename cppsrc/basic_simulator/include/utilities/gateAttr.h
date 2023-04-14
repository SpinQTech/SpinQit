/*
 * File:	gateAttr.h
 * Author:	Jingen Xiang
 * Email:	jxiang@spinq.cn
 * Company:	SpinQ Inc
 * Date：	07/2020
 *
 */

#ifndef _GATE_ATTR_H_
#define _GATE_ATTR_H_

#include <iostream>
#include <complex>
#include <string>
#include "matrix.h"
#include "simple_json.h"

#define SQRT2          1.4142135624
#ifndef PI
#define PI             3.1415926532
#endif
#define INVALID_QUBIT  0xFFFF

using namespace std;

typedef complex<double> StateType;

class gateAttr {
private:
    double             m_angle;

public:
    gateAttr();
    gateAttr(double angle);

    ~gateAttr();

    bool setAngle(double angle);

    double getAngle() const;
    matrix<StateType> getGateXMatrix() const;
    matrix<StateType> getGateYMatrix() const;
    matrix<StateType> getGateZMatrix() const;
    matrix<StateType> getGatePMatrix() const;
};


#endif // _GATE_ATTR_
