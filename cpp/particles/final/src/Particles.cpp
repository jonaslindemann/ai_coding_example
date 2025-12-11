#include "Particles.h"
#include <algorithm>

Particles::Particles()
{
}

Particles::~Particles()
{
}

void Particles::addParticle(const Eigen::Vector2f& position, const Eigen::Vector2f& velocity, float lifespan)
{
    m_particles.emplace_back(position, velocity, lifespan);
}

void Particles::update(float deltaTime)
{
    // Update all particles
    for (auto& particle : m_particles)
    {
        // Update position based on velocity
        particle.position += particle.velocity * deltaTime;
        
        // Decrease lifespan
        particle.lifespan -= deltaTime;
    }
}

void Particles::removeDeadParticles()
{
    // Remove particles with lifespan <= 0
    m_particles.erase(
        std::remove_if(m_particles.begin(), m_particles.end(),
            [](const Particle& p) { return p.lifespan <= 0.0f; }),
        m_particles.end()
    );
}

size_t Particles::getParticleCount() const
{
    return m_particles.size();
}

const Particles::Particle& Particles::getParticle(size_t index) const
{
    return m_particles[index];
}

void Particles::clear()
{
    m_particles.clear();
}

const std::vector<Particles::Particle>& Particles::getParticles() const
{
    return m_particles;
}
