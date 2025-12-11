def beam1s(ex, ep, ed, eq=None, nep=None):
    """
    Compute section forces in one dimensional beam element (beam1e).

    Parameters:

        ex = [x1 x2]        element node coordinates

        ep = [E I]          element properties,
                            E:  Young's modulus
                            I:  moment of inertia

        ed = [u1 ... u4]    element displacements

        eq = qy             distributed load, local directions

        nep                 number of evaluation points ( default=2 )

    Returns:

        es = [ V1 M1        section forces, local directions, in
               V2 M2        n points along the beam, dim(es)= n x 2
               .........]

        edi = [ v1          element displacements, local directions,
                v2          in n points along the beam, dim(es)= n x 1
                .......]

            eci = [ x1      local x-coordinates of the evaluation
                    x2      points, (x1=0 and xn=L)
                    ...]

    """
    EI = ep[0]*ep[1]
    L = ex[1]-ex[0]

    qy = 0.

    if not eq is None:
        qy = eq

    ne = 2

    if nep != None:
        ne = nep

    Cinv = np.mat([
        [1, 0,  0,  0],
        [0, 1,  0,  0],
        [-3/(L**2), -2/L,   3/(L**2),   -1/L],
        [2/(L**3),  1/(L**2),   -2/(L**3),  1/(L**2)]
    ])

    Ca = (Cinv@ed).T

    x = np.asmatrix(np.arange(0., L+L/(ne-1), L/(ne-1))).T
    zero = np.asmatrix(np.zeros([len(x)])).T
    one = np.asmatrix(np.ones([len(x)])).T

    v = np.concatenate((one, x, np.power(x, 2), np.power(x, 3)), 1)@Ca \
                        + qy/(24*EI)*(np.power(x,4) - 2*L*np.power(x,3) + (L**2)*np.power(x,2))
    d2v = np.concatenate((zero, zero, 2*one, 6*x), 1)@Ca \
                        + qy/(2*EI)*(np.power(x,2) - L*x + L**2/12)
    d3v = np.concatenate((zero, zero, zero, 6*one), 1)@Ca - qy*(x - L/2)

    M = EI*d2v
    V = -EI*d3v
    edi = v
    eci = x
    es = np.concatenate((V, M), 1)

    return (es, edi, eci)