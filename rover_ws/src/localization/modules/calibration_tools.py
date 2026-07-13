import numpy as np
from scipy import linalg


def apply_calibration(data, hard_iron, soft_iron):
    # Subtract hard iron bias and apply soft iron correction
    data_corrected = (data - hard_iron.T) @ soft_iron.T
    return data_corrected

def ellipsoid_fit(s):
    # D (samples)
    D = np.array([s[0]**2., s[1]**2., s[2]**2.,
                    2.*s[1]*s[2], 2.*s[0]*s[2], 2.*s[0]*s[1],
                    2.*s[0], 2.*s[1], 2.*s[2], np.ones_like(s[0])])

    S = np.dot(D, D.T)
    S_11 = S[:6,:6]
    S_12 = S[:6,6:]
    S_21 = S[6:,:6]
    S_22 = S[6:,6:]

    C = np.array([[-1,  1,  1,  0,  0,  0],
                    [ 1, -1,  1,  0,  0,  0],
                    [ 1,  1, -1,  0,  0,  0],
                    [ 0,  0,  0, -4,  0,  0],
                    [ 0,  0,  0,  0, -4,  0],
                    [ 0,  0,  0,  0,  0, -4]])

    E = np.dot(linalg.inv(C),
                S_11 - np.dot(S_12, np.dot(linalg.inv(S_22), S_21)))

    E_w, E_v = np.linalg.eig(E)
    v_1 = E_v[:, np.argmax(E_w)]
    if v_1[0] < 0: v_1 = -v_1

    v_2 = np.dot(np.dot(-np.linalg.inv(S_22), S_21), v_1)

    M = np.array([[v_1[0], v_1[5], v_1[4]],
                    [v_1[5], v_1[1], v_1[3]],
                    [v_1[4], v_1[3], v_1[2]]])
    n = np.array([[v_2[0]],
                    [v_2[1]],
                    [v_2[2]]])
    d = v_2[3]

    return M, n, d

def get_calib_params(mag_array, expected_field):
    M, n, d = ellipsoid_fit(mag_array)
    # Calculate calibration parameters
    M_1 = linalg.inv(M)
    hard_iron = -np.dot(M_1, n).flatten() #hard iron bias
    soft_iron = np.real(expected_field / np.sqrt(np.dot(n.T, np.dot(M_1, n)) - d) * linalg.sqrtm(M)) #soft iron
    return hard_iron, soft_iron