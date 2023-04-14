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

from scipy import linalg as lg
import numpy as np
import cmath, math

# def _params_zyz(mat):
#     coeff = lg.det(mat) ** (-0.5)
#     phase = -cmath.phase(coeff)
#     su_mat = coeff * mat

#     beta = 2 * math.atan2(abs(su_mat[1, 0]), abs(su_mat[0, 0]))
#     alphaplgamma2 = cmath.phase(su_mat[1, 1])
#     alphamigamma2 = cmath.phase(su_mat[1, 0])
#     gamma = alphaplgamma2 + alphamigamma2
#     alpha = alphaplgamma2 - alphamigamma2

#     return alpha, beta, gamma, phase

def decompose_zyz(mat):
    coeff = lg.det(mat)
    phase = 0.5 * cmath.phase(coeff)
    v_mat = cmath.exp(-1j * phase) * mat

    if abs(v_mat[0, 0]) < abs(v_mat[0, 1]):
        beta = 2*cmath.asin(abs(v_mat[0, 1]))
    else:
        beta = 2*cmath.acos(abs(v_mat[0, 0]))

    if cmath.cos(beta/2) == 0:
        gammaplalpha2 = 0.0
    else:
        gammaplalpha2 = cmath.phase(v_mat[1, 1] / cmath.cos(beta/2))

    if cmath.sin(beta/2) == 0:
        gammamialpha2 = 0.0
    else:
        gammamialpha2 = cmath.phase(v_mat[1, 0] / cmath.sin(beta/2))

    gamma = gammaplalpha2 + gammamialpha2
    alpha = gammaplalpha2 - gammamialpha2

    return alpha.real, beta.real, gamma.real, phase.real

def validate_zyz(mat, alpha, beta, gamma, phi):
    Rz_a = np.array([[cmath.exp(-1j*alpha / 2.0), 0.0], [0.0, cmath.exp(1j*alpha / 2.0)]])
    Rz_c = np.array([[cmath.exp(-1j*gamma / 2.0), 0.0], [0.0, cmath.exp(1j*gamma / 2.0)]])
    Ry_b = np.array([[cmath.cos(beta/2.0), -cmath.sin(beta/2.0)], [cmath.sin(beta/2), cmath.cos(beta/2)]])

    dmat = cmath.exp(1j*phi) * Rz_c @ Ry_b @ Rz_a
    
    return np.allclose(mat, dmat)     

if __name__ == '__main__':
    # hmat = np.array([[math.sqrt(2)/2, math.sqrt(2)/2], [math.sqrt(2)/2, -math.sqrt(2)/2]])
    umat = np.array([[ 0.+0.j, -1.00000228+0.j], [ 0.+1.00000228j, 0.+0.j]])
    a,b,g,p = decompose_zyz(umat)
    print(a,b,g,p)
    res = validate_zyz(umat, a, b, g, p)
    print(res)