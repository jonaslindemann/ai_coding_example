
#ifndef _USE_MATH_DEFINES
#define _USE_MATH_DEFINES
#endif
#include <cmath>

#include <Eigen/Dense>
#include <iomanip>
#include <iostream>
#include <string>
#include <fstream>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#include <ofem/beam_model.h>
#include <ofem/beam_set.h>
#include <ofem/node_set.h>
#include <ofsolve/beam_solver.h>
#include <logger.h>

using namespace ofem;
using namespace ofsolver;

static void printUsage(const char *prog)
{
    std::cerr << "Usage: " << prog << " <model.df3> [options]\n"
              << "\n"
              << "Options:\n"
              << "  --eigen <n>      Compute n eigenvalues/frequencies (default: 0)\n"
              << "  --displacements  Print per-node displacements and rotations\n"
              << "  --reactions      Print per-node reaction forces and moments\n"
              << "  --elements       Print per-element section force summary\n"
              << "  --output <file>  Write results to file instead of stdout\n"
              << "  --help           Show this help message\n";
}

static std::string modelStateStr(ModelState s)
{
    switch (s)
    {
    case ModelState::Ok:              return "OK";
    case ModelState::NoNodes:         return "No nodes defined";
    case ModelState::NoElements:      return "No elements defined";
    case ModelState::NoBC:            return "No boundary conditions defined";
    case ModelState::NoLoads:         return "No loads defined";
    case ModelState::Unstable:        return "Model is unstable";
    case ModelState::Invalid:         return "Invalid model";
    case ModelState::Singular:        return "Singular stiffness matrix";
    case ModelState::UndefinedMaterial: return "Undefined material";
    case ModelState::SetupFailed:     return "Solver setup failed";
    case ModelState::SolveFailed:     return "Solve failed";
    case ModelState::RecomputeFailed: return "Recompute failed";
    default:                          return "Unknown error";
    }
}

int main(int argc, char *argv[])
{
    if (argc < 2)
    {
        printUsage(argv[0]);
        return 1;
    }

    std::string filename;
    int numEigen = 0;
    bool printDisplacements = false;
    bool printReactions = false;
    bool printElementForces = false;
    std::string outputFile;

    for (int i = 1; i < argc; ++i)
    {
        std::string arg = argv[i];
        if (arg == "--help" || arg == "-h")
        {
            printUsage(argv[0]);
            return 0;
        }
        else if (arg == "--eigen")
        {
            if (i + 1 >= argc)
            {
                Logger::instance()->log(LogLevel::Error, "--eigen requires a count argument");
                return 1;
            }
            numEigen = std::stoi(argv[++i]);
        }
        else if (arg == "--displacements")
        {
            printDisplacements = true;
        }
        else if (arg == "--reactions")
        {
            printReactions = true;
        }
        else if (arg == "--elements")
        {
            printElementForces = true;
        }
        else if (arg == "--output")
        {
            if (i + 1 >= argc)
            {
                Logger::instance()->log(LogLevel::Error, "--output requires a filename argument");
                return 1;
            }
            outputFile = argv[++i];
        }
        else if (arg[0] == '-')
        {
            Logger::instance()->log(LogLevel::Error, "Unknown option '%s'", arg.c_str());
            printUsage(argv[0]);
            return 1;
        }
        else
        {
            if (!filename.empty())
            {
                Logger::instance()->log(LogLevel::Error, "Multiple input files specified");
                return 1;
            }
            filename = arg;
        }
    }

    if (filename.empty())
    {
        Logger::instance()->log(LogLevel::Error, "No input file specified");
        printUsage(argv[0]);
        return 1;
    }

    // Redirect output if requested
    std::ofstream outFile;
    std::ostream *out = &std::cout;
    if (!outputFile.empty())
    {
        outFile.open(outputFile);
        if (!outFile)
        {
            Logger::instance()->log(LogLevel::Error, "Cannot open output file '%s'", outputFile.c_str());
            return 1;
        }
        out = &outFile;
    }

    Logger::instance()->log(LogLevel::Info, "---------------------");
    Logger::instance()->log(LogLevel::Info, "Simple 3D beam solver");
    Logger::instance()->log(LogLevel::Info, "---------------------");

    // Load model
    BeamModelPtr beamModel = BeamModel::create();
    beamModel->setFileName(filename);

    Logger::instance()->log(LogLevel::Info, "Loading model: %s", filename.c_str());
    if (!beamModel->open())
    {
        Logger::instance()->log(LogLevel::Error, "Could not open model file '%s'", filename.c_str());
        return 1;
    }

    NodeSet *nodeSet = beamModel->getNodeSet();
    BeamSet *elementSet = static_cast<BeamSet *>(beamModel->getElementSet());

    Logger::instance()->log(LogLevel::Info, "Model loaded: %zu nodes, %zu elements",
                            nodeSet->getSize(), elementSet->getSize());

    // Run solver
    Logger::instance()->log(LogLevel::Info, "Solving...");
    BeamSolverPtr solver = BeamSolver::create();
    solver->setBeamModel(beamModel.get());
    solver->execute();

    ModelState state = solver->modelState();
    if (state != ModelState::Ok)
    {
        Logger::instance()->log(LogLevel::Error, "Solver failed: %s", modelStateStr(state).c_str());
        return 2;
    }

    Logger::instance()->log(LogLevel::Info, "Solve complete.");

    // Print summary
    *out << std::fixed << std::setprecision(6);
    *out << "=== ObjectiveFrame Solver Results ===\n";
    *out << "Model file : " << filename << "\n";
    *out << "Nodes      : " << nodeSet->getSize() << "\n";
    *out << "Elements   : " << elementSet->getSize() << "\n";
    *out << "\n";

    *out << "--- Force / Moment Extremes ---\n";
    *out << "Max axial force N  : " << beamModel->maxN() << "\n";
    *out << "Min axial force N  : " << beamModel->minN() << "\n";
    *out << "Max torsion T      : " << beamModel->maxT() << "\n";
    *out << "Min torsion T      : " << beamModel->minT() << "\n";
    *out << "Max shear V        : " << beamModel->maxV() << "\n";
    *out << "Min shear V        : " << beamModel->minV() << "\n";
    *out << "Max moment M       : " << beamModel->maxM() << "\n";
    *out << "Min moment M       : " << beamModel->minM() << "\n";
    *out << "Max Navier stress  : " << beamModel->maxNavier() << "\n";
    *out << "Min Navier stress  : " << beamModel->minNavier() << "\n";
    *out << "Max reaction force : " << solver->getMaxReactionForce() << "\n";
    *out << "Max reaction moment: " << solver->getMaxReactionMoment() << "\n";
    *out << "Max node disp.     : " << solver->getMaxNodeValue() << "\n";
    *out << "\n";

    // Per-node results
    if (printDisplacements || printReactions)
    {
        *out << "--- Node Results ---\n";
        *out << std::setw(6) << "Node"
             << std::setw(14) << "dx" << std::setw(14) << "dy" << std::setw(14) << "dz";
        if (printDisplacements)
            *out << std::setw(14) << "rx" << std::setw(14) << "ry" << std::setw(14) << "rz";
        if (printReactions)
            *out << std::setw(14) << "Rx" << std::setw(14) << "Ry" << std::setw(14) << "Rz";
        *out << "\n";

        for (size_t i = 0; i < nodeSet->getSize(); ++i)
        {
            Node *node = nodeSet->getNode(static_cast<long>(i));
            if (node->getKind() == nkNotConnected)
                continue;

            *out << std::setw(6) << node->getNumber();

            // Displacements (values 0-2) and rotations (3-5)
            if (node->getKind() == nk6Dof && node->getValueSize() >= 6)
            {
                *out << std::setw(14) << node->getValue(0)
                     << std::setw(14) << node->getValue(1)
                     << std::setw(14) << node->getValue(2);
                if (printDisplacements)
                    *out << std::setw(14) << node->getValue(3)
                         << std::setw(14) << node->getValue(4)
                         << std::setw(14) << node->getValue(5);
                if (printReactions && node->getValueSize() >= 12)
                    *out << std::setw(14) << node->getValue(6)
                         << std::setw(14) << node->getValue(7)
                         << std::setw(14) << node->getValue(8);
            }
            else if (node->getKind() == nk3Dof && node->getValueSize() >= 3)
            {
                *out << std::setw(14) << node->getValue(0)
                     << std::setw(14) << node->getValue(1)
                     << std::setw(14) << node->getValue(2);
                if (printDisplacements)
                    *out << std::setw(14) << 0.0
                         << std::setw(14) << 0.0
                         << std::setw(14) << 0.0;
                if (printReactions && node->getValueSize() >= 6)
                    *out << std::setw(14) << node->getValue(3)
                         << std::setw(14) << node->getValue(4)
                         << std::setw(14) << node->getValue(5);
            }
            *out << "\n";
        }
        *out << "\n";
    }

    // Per-element section force summary (first evaluation point)
    if (printElementForces)
    {
        *out << "--- Element Section Forces (at first evaluation point) ---\n";
        *out << std::setw(8)  << "Element"
             << std::setw(14) << "N"
             << std::setw(14) << "T"
             << std::setw(14) << "Vy"
             << std::setw(14) << "Vz"
             << std::setw(14) << "My"
             << std::setw(14) << "Mz"
             << "\n";

        for (size_t i = 0; i < elementSet->getSize(); ++i)
        {
            Beam *beam = static_cast<Beam *>(elementSet->getElement(static_cast<long>(i)));
            *out << std::setw(8) << beam->getNumber();
            if (beam->getValueSize() >= 6)
            {
                for (int j = 0; j < 6; ++j)
                    *out << std::setw(14) << beam->getValue(j);
            }
            *out << "\n";
        }
        *out << "\n";
    }

    // Eigenvalue analysis
    if (numEigen > 0)
    {
        Logger::instance()->log(LogLevel::Info, "Computing %d eigenvalue(s)...", numEigen);
        if (solver->computeEigenModes(numEigen))
        {
            *out << "--- Eigenvalue Analysis (" << solver->getNumEigenModes() << " modes) ---\n";
            *out << std::setw(6) << "Mode"
                 << std::setw(20) << "Eigenvalue"
                 << std::setw(20) << "Freq (rad/s)"
                 << std::setw(20) << "Freq (Hz)"
                 << "\n";
            for (int m = 0; m < solver->getNumEigenModes(); ++m)
            {
                double lambda = solver->getEigenValue(m);
                double omega = (lambda > 0.0) ? std::sqrt(lambda) : 0.0;
                double freq  = omega / (2.0 * M_PI);
                *out << std::setw(6)  << (m + 1)
                     << std::setw(20) << lambda
                     << std::setw(20) << omega
                     << std::setw(20) << freq
                     << "\n";
            }
            *out << "\n";
        }
        else
        {
            Logger::instance()->log(LogLevel::Warning, "Eigenvalue analysis failed or produced no results");
        }
    }

    return 0;
}
