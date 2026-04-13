#ifndef BEAM1S_H
#define BEAM1S_H

#include <Eigen/Dense>
#include <tuple>

/**
 * @brief Compute section forces in one dimensional beam element (beam1e).
 * 
 * @param ex Element node coordinates [x1, x2]
 * @param ep Element properties [E, I] where E is Young's modulus and I is moment of inertia
 * @param ed Element displacements [u1, u2, u3, u4]
 * @param eq Distributed load in local y-direction (default = 0.0)
 * @param nep Number of evaluation points (default = 2)
 * 
 * @return std::tuple containing:
 *         - es: Section forces [V, M] in n points along the beam (n x 2 matrix)
 *         - edi: Element displacements in n points along the beam (n x 1 vector)
 *         - eci: Local x-coordinates of evaluation points (n x 1 vector)
 */
std::tuple<Eigen::MatrixXd, Eigen::VectorXd, Eigen::VectorXd> 
beam1s(const Eigen::Vector2d& ex, 
       const Eigen::Vector2d& ep, 
       const Eigen::Vector4d& ed, 
       double eq = 0.0, 
       int nep = 2);

#endif // BEAM1S_H
