#include <iostream>
#include <iomanip>
#include <Eigen/Dense>
#include "beam1s.h"

int main() {
    // Example usage of the beam1s function
    
    // Element node coordinates [x1, x2]
    Eigen::Vector2d ex;
    ex << 0.0, 1.0;  // 1 meter beam
    
    // Element properties [E, I]
    Eigen::Vector2d ep;
    ep << 2.1e11,    // Young's modulus (Pa) - steel
          8.33e-6;   // Moment of inertia (m^4)
    
    // Element displacements [u1, u2, u3, u4]
    Eigen::Vector4d ed;
    ed << 0.0,       // displacement at node 1
          0.001,     // rotation at node 1
          0.002,     // displacement at node 2  
          0.0015;    // rotation at node 2
    
    // Distributed load (optional)
    double qy = 1000.0;  // N/m
    
    // Number of evaluation points (optional)
    int nep = 5;
    
    // Call the beam1s function
    auto [es, edi, eci] = beam1s(ex, ep, ed, qy, nep);
    
    std::cout << "Beam Section Forces Analysis\n";
    std::cout << "============================\n\n";
    
    std::cout << "Element coordinates: [" << ex(0) << ", " << ex(1) << "] m\n";
    std::cout << "Young's modulus: " << ep(0) << " Pa\n";
    std::cout << "Moment of inertia: " << ep(1) << " m^4\n";
    std::cout << "Distributed load: " << qy << " N/m\n";
    std::cout << "Number of evaluation points: " << nep << "\n\n";
    
    std::cout << "Results:\n";
    std::cout << "Position (m) | Shear Force (N) | Moment (Nm) | Displacement (m)\n";
    std::cout << "-------------|-----------------|-------------|------------------\n";
    
    for (int i = 0; i < eci.size(); ++i) {
        std::cout << std::fixed << std::setprecision(4)
                  << std::setw(8) << eci(i) << " | "
                  << std::setw(12) << es(i, 0) << " | "
                  << std::setw(8) << es(i, 1) << " | "
                  << std::setw(12) << edi(i) << "\n";
    }
    
    return 0;
}