#pragma once

#include <Eigen/Dense>
#include <tuple>
#include <optional>

/**
 * Compute section forces in one dimensional beam element (beam1e).
 * 
 * Parameters:
 *     ex: [x1, x2] - element node coordinates
 *     ep: [E, I] - element properties (E: Young's modulus, I: moment of inertia)
 *     ed: [u1, u2, u3, u4] - element displacements
 *     eq: distributed load in local directions (optional, default = 0)
 *     nep: number of evaluation points (optional, default = 2)
 * 
 * Returns:
 *     std::tuple<Eigen::MatrixXd, Eigen::VectorXd, Eigen::VectorXd>:
 *         - es: section forces, local directions, in n points along the beam (n x 2)
 *         - edi: element displacements, local directions, in n points along the beam (n x 1)
 *         - eci: local x-coordinates of the evaluation points (n x 1)
 */
std::tuple<Eigen::MatrixXd, Eigen::VectorXd, Eigen::VectorXd> 
beam1s(const Eigen::Vector2d& ex, 
       const Eigen::Vector2d& ep, 
       const Eigen::Vector4d& ed, 
       std::optional<double> eq = std::nullopt, 
       std::optional<int> nep = std::nullopt) {
    
    // Extract material properties
    double E = ep(0);
    double I = ep(1);
    double EI = E * I;
    
    // Calculate element length
    double L = ex(1) - ex(0);
    
    // Set distributed load
    double qy = eq.value_or(0.0);
    
    // Set number of evaluation points
    int ne = nep.value_or(2);
    
    // Create coefficient matrix Cinv
    Eigen::Matrix4d Cinv;
    Cinv << 1.0,         0.0,        0.0,         0.0,
            0.0,         1.0,        0.0,         0.0,
            -3.0/(L*L), -2.0/L,      3.0/(L*L),  -1.0/L,
            2.0/(L*L*L), 1.0/(L*L), -2.0/(L*L*L), 1.0/(L*L);
    
    // Calculate coefficients Ca
    Eigen::Vector4d Ca = Cinv * ed;
    
    // Create x coordinates vector
    Eigen::VectorXd x(ne);
    double dx = (ne > 1) ? L / (ne - 1) : 0.0;
    for (int i = 0; i < ne; ++i) {
        x(i) = i * dx;
    }
    
    // Create helper vectors
    Eigen::VectorXd zero = Eigen::VectorXd::Zero(ne);
    Eigen::VectorXd one = Eigen::VectorXd::Ones(ne);
    
    // Create power vectors
    Eigen::VectorXd x2 = x.array().square();
    Eigen::VectorXd x3 = x.array().cube();
    Eigen::VectorXd x4 = x.array().pow(4);
    
    // Create coefficient matrices for polynomial evaluation
    Eigen::MatrixXd v_coeff(ne, 4);
    v_coeff.col(0) = one;
    v_coeff.col(1) = x;
    v_coeff.col(2) = x2;
    v_coeff.col(3) = x3;
    
    Eigen::MatrixXd d2v_coeff(ne, 4);
    d2v_coeff.col(0) = zero;
    d2v_coeff.col(1) = zero;
    d2v_coeff.col(2) = 2.0 * one;
    d2v_coeff.col(3) = 6.0 * x;
    
    Eigen::MatrixXd d3v_coeff(ne, 4);
    d3v_coeff.col(0) = zero;
    d3v_coeff.col(1) = zero;
    d3v_coeff.col(2) = zero;
    d3v_coeff.col(3) = 6.0 * one;
    
    // Calculate displacements and derivatives
    Eigen::VectorXd v = v_coeff * Ca + 
                        (qy / (24.0 * EI)) * (x4 - 2.0 * L * x3 + L * L * x2);
    
    Eigen::VectorXd d2v = d2v_coeff * Ca + 
                          (qy / (2.0 * EI)) * (x2 - L * x.array() + L * L / 12.0).matrix();
    
    Eigen::VectorXd d3v = d3v_coeff * Ca - 
                          qy * (x.array() - L / 2.0).matrix();
    
    // Calculate moments and shear forces
    Eigen::VectorXd M = EI * d2v;
    Eigen::VectorXd V = -EI * d3v;
    
    // Prepare outputs
    Eigen::VectorXd edi = v;
    Eigen::VectorXd eci = x;
    
    // Combine V and M into section forces matrix
    Eigen::MatrixXd es(ne, 2);
    es.col(0) = V;
    es.col(1) = M;
    
    return std::make_tuple(es, edi, eci);
}