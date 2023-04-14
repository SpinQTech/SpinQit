# Copyright 2021 SpinQ Technology Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import List
import numpy as np
import copy as cp
import random
import cmath
from .ZYZdecomposer import decompose_zyz
from spinqit.model import Instruction
from spinqit.model import DecomposerError
from spinqit.model import I, Rz, Ry, CX

TOLERANCE = 1.e-15
LOOP_LIMIT = 100
Magic=[[1,1j,0,0],[0,0,1j,1],[0,0,1j,-1],[1,-1j,0,0]]/np.sqrt(2)
M=np.matrix(Magic)
Mt=np.conjugate(np.transpose(M))
InCNOT=[[1,0,0,0],[0,0,0,1],[0,0,1,0],[0,1,0,0]]

def find_Udiag(U: np.matrix):
    D,Q=np.linalg.eig(U)
    Dt=cp.copy(D)
    Row=np.zeros([len(D),len(D)], complex)
    TF=True
    r1=[0,1,2,3]
    r2=cp.copy(r1)
   
    loop = 0
    while TF:
        if loop >= LOOP_LIMIT:
            break
        random.shuffle(r2)     
        for i in range(0,len(D)):
            for j in range(0,len(D)):
                Row[j,r2[i]]=np.round(cp.copy(Q[j,r1[i]]),5)
        loop += 1

        if ((np.round(np.dot(Row,np.transpose(Row)),3)==np.eye(4)).all()):
            if (np.round(np.linalg.det(Row),3)==1):    
                TF=False                           
    
    if (TF):
        raise  DecomposerError("No Such diagonalize matrix belong to SO(4)");
    
    for i in range(0,4):
        Dt[r2[i]]=cp.copy(D[r1[i]])
        
    Dt=np.array(Dt,complex)
    Row=np.array(Row,complex)
    return Dt, Row

def check(U):
    TF = True
    if (U[2,0]!=0):
        TF = False
    elif (U[2,1]!=0):
        TF = False
    elif (U[3,0]!=0):
        TF = False
    elif (U[3,1]!=0):
        TF = False
    elif (U[0,2]!=0):
        TF = False
    elif (U[0,3]!=0):
        TF = False
    elif (U[1,2]!=0):
        TF = False
    elif (U[1,3]!=0):
        TF = False
    return TF

def CANdecomposition(UCAN):
    Ucenter=np.dot(InCNOT,np.dot(UCAN,InCNOT));
    if not check(Ucenter):
        raise DecomposerError("U is not Canonical Form!")

    topU=np.array([[Ucenter[0,0],Ucenter[0,1]],[Ucenter[1,0],Ucenter[1,1]]]);
    botU=np.array([[Ucenter[2,2],Ucenter[2,3]],[Ucenter[3,2],Ucenter[3,3]]]);
    U3=np.dot(botU,np.linalg.inv(topU))
    
    return U3, topU

def ControlU(U):
    C=np.zeros([4,4],complex)
    C[0,0]=1
    C[1,1]=1
    C[2,2]=cp.copy(U[0,0])
    C[2,3]=cp.copy(U[0,1])
    C[3,2]=cp.copy(U[1,0])
    C[3,3]=cp.copy(U[1,1])
    return C

def De_Kron_Pro(C):
    C=np.array(C)
    C=C.reshape(2,2,2,2) 
    C=C.transpose(0,2,1,3)
    C=C.reshape(4,4)
	
    u,sv,vh=np.linalg.svd(C)

    A=np.sqrt(sv[0]) * u[:,0].reshape(2,2)
    B=np.sqrt(sv[0]) * vh[0,:].reshape(2,2)
    
    for i in range(0,2):
        for j in range(0,2):
            if abs(A[i,j])>1:
                A[i,j]=A[i,j]
            if abs(B[i,j])>1:
                B[i,j]=B[i,j]
    
    return A,B;

def ControllU_decomposition(CU):
    U=np.zeros([2,2],complex)
    U[0,0]=cp.copy(CU[2,2])
    U[0,1]=cp.copy(CU[2,3])
    U[1,0]=cp.copy(CU[3,2])
    U[1,1]=cp.copy(CU[3,3])
    alpha,beta,gamma,phase = decompose_zyz(U);

    return [phase, (alpha-gamma)/2, -(gamma+alpha)/2, -beta/2, beta/2, gamma]   

def decompose_two_qubit_gate(U: np.matrix, qubit0: int, qubit1: int) -> List[Instruction]:
    V=np.dot(Mt,np.dot(U,M))
    Vt=np.transpose(V)
    V2=np.dot(V, Vt)
    
    D, K2 = find_Udiag(V2)
    SqrtD = np.zeros([len(D), len(D)], complex)

    for i in range(0,len(D)):
        SqrtD[i,i]=cmath.sqrt(D[i])
    P=np.dot(K2,np.dot(SqrtD,np.transpose(K2)))    
    if (np.round(np.linalg.det(U),3)!=np.round(np.linalg.det(P),3)):
        SqrtD[0,0]=-SqrtD[0,0]        
        P=np.dot(K2,np.dot(SqrtD,np.transpose(K2)))
    
    K1=np.dot(np.linalg.inv(P),V)
    K3=np.dot(np.linalg.inv(K2),K1)
    U56=np.dot(M,np.dot(K2,Mt))
    U12=np.dot(M,np.dot(K3,Mt))
    
    UCAN=np.dot(M,np.dot(SqrtD,Mt))
    U3, U4=np.round(CANdecomposition(UCAN),5)

    ControlU3=ControlU(U3)
    U1,U2=De_Kron_Pro(U12)
    U5,U6=De_Kron_Pro(U56)    

    result = []  
    R=np.zeros(3, np.double)
    R1=np.zeros(3, np.double)

    R[0],R[1],R[2],R1[0] = decompose_zyz(U1)
    result.append(Instruction(Rz, [qubit0], [], R[0]))
    result.append(Instruction(Ry, [qubit0], [], R[1]))
    result.append(Instruction(Rz, [qubit0], [], R[2]))

    R[0],R[1],R[2],R1[0] = decompose_zyz(U2)
    result.append(Instruction(Rz, [qubit1], [], R[0]))
    result.append(Instruction(Ry, [qubit1], [], R[1]))
    result.append(Instruction(Rz, [qubit1], [], R[2]))

    result.append(Instruction(CX, [qubit1, qubit0], []))

    angles = ControllU_decomposition(ControlU3)

    result.append(Instruction(Rz, [qubit0], [], angles[0]))
    result.append(Instruction(Rz, [qubit1], [], angles[1]))
    result.append(Instruction(CX, [qubit0, qubit1], []))
    result.append(Instruction(Rz, [qubit1], [], angles[2]))
    result.append(Instruction(Ry, [qubit1], [], angles[3]))
    result.append(Instruction(CX, [qubit0, qubit1], []))
    result.append(Instruction(Ry, [qubit1], [], angles[4]))
    result.append(Instruction(Rz, [qubit1], [], angles[5]))

    R[0],R[1],R[2],R1[0] = decompose_zyz(U4)
    result.append(Instruction(Rz, [qubit1], [], R[0]))
    result.append(Instruction(Ry, [qubit1], [], R[1]))
    result.append(Instruction(Rz, [qubit1], [], R[2]))

    result.append(Instruction(CX, [qubit1, qubit0], []))

    R[0],R[1],R[2],R1[0] = decompose_zyz(U5)
    result.append(Instruction(Rz, [qubit0], [], R[0]))
    result.append(Instruction(Ry, [qubit0], [], R[1]))
    result.append(Instruction(Rz, [qubit0], [], R[2]))

    R[0],R[1],R[2],R1[0] = decompose_zyz(U6)
    
    result.append(Instruction(Rz, [qubit1], [], R[0]))
    result.append(Instruction(Ry, [qubit1], [], R[1]))
    result.append(Instruction(Rz, [qubit1], [], R[2]))

    return result

def check_decomposition(U: np.matrix, result: List, qubit0: int):
    Tot = np.eye(4, dtype=complex)
    for inst in result:
        if inst.gate == CX:
            if inst.qubits[0] == qubit0:
                g2 = CX.matrix([0])
            else:
                g2 = CX.matrix([1])
        else:
            g1 = inst.gate.matrix(inst.params)
            if inst.qubits[0] == qubit0:
                g2 = np.kron(g1, I.matrix([]))
            else:
                g2 = np.kron(I.matrix([]), g1)
        Tot = np.dot(g2, Tot)
    print(np.allclose(Tot, U, TOLERANCE, TOLERANCE))

if __name__ == '__main__':
    # CU_mat = CZ.matrix([0]) @ CY.matrix([0]) @ CZ.matrix([0])
    CU_mat = np.array([[1,0,0,0],[0,0,-1,0],[0,0,0,-1],[0,1,0,0]])
    inst_list = decompose_two_qubit_gate(CU_mat, 0, 1)
    # for inst in inst_list:
    #     print(inst.get_op())
    #     print(inst.qubits)
    #     print(inst.params)
    check_decomposition(CU_mat, inst_list, 0)