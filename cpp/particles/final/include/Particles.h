#pragma once

#include <vector>
#include <Eigen/Dense>

class Particles
{
public:
    struct Particle
    {
        Eigen::Vector2f position;
        Eigen::Vector2f velocity;
        float lifespan;

        Particle(const Eigen::Vector2f& pos, const Eigen::Vector2f& vel, float life)
            : position(pos), velocity(vel), lifespan(life) {}
    };

    Particles();
    ~Particles();

    // Add a new particle to the collection
    void addParticle(const Eigen::Vector2f& position, const Eigen::Vector2f& velocity, float lifespan);

    // Update all particles (move positions and decrease lifespans)
    void update(float deltaTime);

    // Remove dead particles (lifespan <= 0)
    void removeDeadParticles();

    // Get the number of active particles
    size_t getParticleCount() const;

    // Get particle at index (for rendering)
    const Particle& getParticle(size_t index) const;

    // Clear all particles
    void clear();

    // Get all particles (for iteration)
    const std::vector<Particle>& getParticles() const;

private:
    std::vector<Particle> m_particles;
};
