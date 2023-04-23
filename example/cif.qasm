OPENQASM 2.0;
include "qelib1.inc";

qreg q[3];
creg c[3];

h q[0];
x q[1];
measure q[0] -> c[0];
if (c==0) u(pi/2,0,pi) q[2];
//if (c==0) x q[2];
h q[2];
