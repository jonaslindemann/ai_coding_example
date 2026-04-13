#include "beam1s.h"
#include <cmath>

std::tuple<Eigen::MatrixXd, Eigen::VectorXd, Eigen::VectorXd> 
beam1s(const Eigen::Vector2d& ex, 
       const Eigen::Vector2d& ep, 
       const Eigen::Vector4d& ed, 
       double eq, 
       int nep)
{
    // Extract element properties
    double E = ep(0);
    double I = ep(1);
    double EI = E * I;
    
    // Calculate element length
    double L = ex(1) - ex(0);
    
    // Distributed load
    double qy = eq;
    
    // Number of evaluation points
    int ne = nep;
    
    // Inverse transformation matrix
    Eigen::Matrix4d Cinv;
    Cinv << 1.0,        0.0,            0.0,            0.0,
            0.0,        1.0,            0.0,            0.0,
            -3.0/(L*L), -2.0/L,         3.0/(L*L),      -1.0/L,
            2.0/(L*L*L), 1.0/(L*L),     -2.0/(L*L*L),   1.0/(L*L);
    
    // Calculate coefficients
    Eigen::Vector4d Ca = Cinv * ed;
    
    // Create evaluation points
    Eigen::VectorXd x = Eigen::VectorXd::LinSpaced(ne, 0.0, L);
    
    // Initialize result matrices
    Eigen::VectorXd v(ne);
    Eigen::VectorXd d2v(ne);
    Eigen::VectorXd d3v(ne);
    
    // Calculate displacements and derivatives at each point
    for (int i = 0; i < ne; ++i) {
        double xi = x(i);
        double xi2 = xi * xi;
        double xi3 = xi2 * xi;
        double xi4 = xi3 * xi;
        
        // Displacement v
        v(i) = Ca(0) + Ca(1)*xi + Ca(2)*xi2 + Ca(3)*xi3 
               + qy/(24.0*EI) * (xi4 - 2.0*L*xi3 + L*L*xi2);
        
        // Second derivative d2v (curvature)
        d2v(i) = 2.0*Ca(2) + 6.0*Ca(3)*xi 
                 + qy/(2.0*EI) * (xi2 - L*xi + L*L/12.0);
        
        // Third derivative d3v
        d3v(i) = 6.0*Ca(3) - qy*(xi - L/2.0);
    }
    
    // Calculate section forces
    Eigen::VectorXd M = EI * d2v;    // Moment
    Eigen::VectorXd V = -EI * d3v;   // Shear force
    
    // Combine V and M into es matrix
    Eigen::MatrixXd es(ne, 2);
    es.col(0) = V;
    es.col(1) = M;
    
    return std::make_tuple(es, v, x);
}
