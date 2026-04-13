
#ifndef _USE_MATH_DEFINES
#define _USE_MATH_DEFINES
#endif
#include <cmath>

#include <Eigen/Dense>
#include <chrono>
#include <filesystem>
#include <iomanip>
#include <iostream>
#include <string>
#include <fstream>
#include <vector>

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
namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;
using Ms    = std::chrono::duration<double, std::milli>;

static void printUsage(const char *prog)
{
    std::cerr << "Usage: " << prog << " <model.df3> [options]\n"
              << "       " << prog << " --benchmark [directory]\n"
              << "\n"
              << "Options:\n"
              << "  --eigen <n>      Compute n eigenvalues/frequencies (default: 0)\n"
              << "  --displacements  Print per-node displacements and rotations\n"
              << "  --reactions      Print per-node reaction forces and moments\n"
              << "  --elements       Print per-element section force summary\n"
              << "  --output <file>  Write results to file instead of stdout\n"
              << "  --benchmark [d]  Run all .df3 files in directory d (default: .)\n"
              << "  --repeat <n>     Repeat each benchmark run n times (default: 1)\n"
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

struct BenchResult
{
    std::string filename;
    size_t      nodes    = 0;
    size_t      elements = 0;
    // aggregate solve timing across repeats
    double      solveMin = 0.0;
    double      solveAvg = 0.0;
    double      solveMax = 0.0;
    // load and total from the first run
    double      loadMs   = 0.0;
    double      totalMs  = 0.0;
    int         repeats  = 0;
    bool        ok       = false;
    std::string error;
};

static BenchResult benchmarkFile(const std::string &path, int repeats)
{
    BenchResult r;
    r.filename = fs::path(path).filename().string();
    r.repeats  = repeats;

    // First run: load + solve, capture load time and model info
    auto t0 = Clock::now();

    BeamModelPtr beamModel = BeamModel::create();
    beamModel->setFileName(path);
    if (!beamModel->open())
    {
        r.error   = "Could not open file";
        r.totalMs = Ms(Clock::now() - t0).count();
        return r;
    }

    r.loadMs   = Ms(Clock::now() - t0).count();
    r.nodes    = beamModel->getNodeSet()->getSize();
    r.elements = static_cast<BeamSet *>(beamModel->getElementSet())->getSize();

    // Validate on the first run
    {
        auto t1 = Clock::now();
        BeamSolverPtr solver = BeamSolver::create();
        solver->setBeamModel(beamModel.get());
        solver->execute();
        double ms = Ms(Clock::now() - t1).count();

        ModelState state = solver->modelState();
        if (state != ModelState::Ok)
        {
            r.error   = modelStateStr(state);
            r.totalMs = Ms(Clock::now() - t0).count();
            return r;
        }
        r.ok      = true;
        r.solveMin = r.solveMax = r.solveAvg = ms;
    }

    // Remaining repeat runs (solve only — model already loaded)
    for (int rep = 1; rep < repeats; ++rep)
    {
        // Reload so each run starts from the same state
        BeamModelPtr m = BeamModel::create();
        m->setFileName(path);
        m->open();

        auto t1 = Clock::now();
        BeamSolverPtr solver = BeamSolver::create();
        solver->setBeamModel(m.get());
        solver->execute();
        double ms = Ms(Clock::now() - t1).count();

        r.solveMin  = std::min(r.solveMin, ms);
        r.solveMax  = std::max(r.solveMax, ms);
        r.solveAvg += ms;
    }

    r.solveAvg /= repeats;
    r.totalMs   = r.loadMs + r.solveAvg;

    return r;
}

static int runBenchmark(const std::string &dir, int repeats)
{
    std::error_code ec;
    if (!fs::is_directory(dir, ec))
    {
        Logger::instance()->log(LogLevel::Error, "Benchmark directory not found: %s", dir.c_str());
        return 1;
    }

    std::vector<std::string> files;
    for (const auto &entry : fs::directory_iterator(dir, ec))
        if (entry.is_regular_file() && entry.path().extension() == ".df3")
            files.push_back(entry.path().string());

    if (files.empty())
    {
        Logger::instance()->log(LogLevel::Warning, "No .df3 files found in: %s", dir.c_str());
        return 0;
    }

    std::sort(files.begin(), files.end());

    Logger::instance()->log(LogLevel::Info, "Benchmarking %zu file(s) in: %s  (repeats: %d)",
                            files.size(), dir.c_str(), repeats);

    std::vector<BenchResult> results;
    results.reserve(files.size());

    for (const auto &f : files)
    {
        Logger::instance()->log(LogLevel::Info, "  Running: %s",
                                fs::path(f).filename().string().c_str());
        results.push_back(benchmarkFile(f, repeats));
    }

    // Column widths
    size_t nameW = 8;
    for (const auto &r : results)
        nameW = std::max(nameW, r.filename.size());
    nameW += 2;

    const bool multi = repeats > 1;

    std::cout << "\n=== Benchmark Results";
    if (multi)
        std::cout << " (" << repeats << " repeats)";
    std::cout << " ===\n\n";

    std::cout << std::fixed << std::setprecision(2);
    std::cout << std::left  << std::setw(static_cast<int>(nameW)) << "File"
              << std::right << std::setw(7)  << "Nodes"
                            << std::setw(10) << "Elements"
                            << std::setw(11) << "Load ms";
    if (multi)
        std::cout << std::setw(11) << "Min ms"
                  << std::setw(11) << "Avg ms"
                  << std::setw(11) << "Max ms";
    else
        std::cout << std::setw(11) << "Solve ms";
    std::cout << std::setw(11) << "Total ms"
              << "  Status\n";

    const int tableW = static_cast<int>(nameW) + 7 + 10 + 11 + (multi ? 33 : 11) + 11;
    std::cout << std::string(tableW, '-') << "\n";

    double grandTotal = 0.0;
    int    passed     = 0;
    int    failed     = 0;

    for (const auto &r : results)
    {
        grandTotal += r.totalMs;
        if (r.ok) ++passed; else ++failed;

        std::cout << std::left  << std::setw(static_cast<int>(nameW)) << r.filename
                  << std::right << std::setw(7)  << r.nodes
                                << std::setw(10) << r.elements
                                << std::setw(11) << r.loadMs;
        if (multi)
            std::cout << std::setw(11) << r.solveMin
                      << std::setw(11) << r.solveAvg
                      << std::setw(11) << r.solveMax;
        else
            std::cout << std::setw(11) << r.solveAvg;
        std::cout << std::setw(11) << r.totalMs
                  << "  " << (r.ok ? "OK" : "FAIL: " + r.error)
                  << "\n";
    }

    std::cout << std::string(tableW, '-') << "\n";
    std::cout << "Files: " << results.size()
              << "  Passed: " << passed
              << "  Failed: " << failed
              << "  Total: " << grandTotal << " ms\n\n";

    return failed > 0 ? 2 : 0;
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
    bool benchmark = false;
    std::string benchmarkDir = ".";
    int benchmarkRepeats = 1;

    for (int i = 1; i < argc; ++i)
    {
        std::string arg = argv[i];
        if (arg == "--help" || arg == "-h")
        {
            printUsage(argv[0]);
            return 0;
        }
        else if (arg == "--benchmark")
        {
            benchmark = true;
            if (i + 1 < argc && argv[i + 1][0] != '-')
                benchmarkDir = argv[++i];
        }
        else if (arg == "--repeat")
        {
            if (i + 1 >= argc)
            {
                Logger::instance()->log(LogLevel::Error, "--repeat requires a count argument");
                return 1;
            }
            benchmarkRepeats = std::stoi(argv[++i]);
            if (benchmarkRepeats < 1)
            {
                Logger::instance()->log(LogLevel::Error, "--repeat count must be >= 1");
                return 1;
            }
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

    if (benchmark)
        return runBenchmark(benchmarkDir, benchmarkRepeats);

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

    auto tStart = Clock::now();

    // Load model
    BeamModelPtr beamModel = BeamModel::create();
    beamModel->setFileName(filename);

    Logger::instance()->log(LogLevel::Info, "Loading model: %s", filename.c_str());
    auto tLoad = Clock::now();
    if (!beamModel->open())
    {
        Logger::instance()->log(LogLevel::Error, "Could not open model file '%s'", filename.c_str());
        return 1;
    }
    double loadMs = Ms(Clock::now() - tLoad).count();

    NodeSet *nodeSet = beamModel->getNodeSet();
    BeamSet *elementSet = static_cast<BeamSet *>(beamModel->getElementSet());

    Logger::instance()->log(LogLevel::Info, "Model loaded: %zu nodes, %zu elements (%.2f ms)",
                            nodeSet->getSize(), elementSet->getSize(), loadMs);

    // Run solver
    Logger::instance()->log(LogLevel::Info, "Solving...");
    auto tSolve = Clock::now();
    BeamSolverPtr solver = BeamSolver::create();
    solver->setBeamModel(beamModel.get());
    solver->execute();
    double solveMs = Ms(Clock::now() - tSolve).count();
    double totalMs = Ms(Clock::now() - tStart).count();

    ModelState state = solver->modelState();
    if (state != ModelState::Ok)
    {
        Logger::instance()->log(LogLevel::Error, "Solver failed: %s", modelStateStr(state).c_str());
        return 2;
    }

    Logger::instance()->log(LogLevel::Info, "Solve complete.  load: %.2f ms  solve: %.2f ms  total: %.2f ms",
                            loadMs, solveMs, totalMs);

    // Print summary
    *out << std::fixed << std::setprecision(6);
    *out << "=== ObjectiveFrame Solver Results ===\n";
    *out << "Model file : " << filename << "\n";
    *out << "Nodes      : " << nodeSet->getSize() << "\n";
    *out << "Elements   : " << elementSet->getSize() << "\n";
    *out << std::setprecision(2);
    *out << "Load time  : " << loadMs  << " ms\n";
    *out << "Solve time : " << solveMs << " ms\n";
    *out << "Total time : " << totalMs << " ms\n";
    *out << std::setprecision(6) << "\n";

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
        auto tEigen = Clock::now();
        if (solver->computeEigenModes(numEigen))
        {
            double eigenMs = Ms(Clock::now() - tEigen).count();
            Logger::instance()->log(LogLevel::Info, "Eigenvalue analysis complete. (%.2f ms)", eigenMs);
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
