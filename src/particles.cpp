#include "particles.h"

using namespace particles;

Particle::Particle(const vector_math::Vec2d &position, const vector_math::Vec2d &velocity, const Color &color,
                   float radius)
    : m_position(position), m_velocity(velocity), m_color(color), m_radius(radius)
{}

std::shared_ptr<Particle> Particle::create(const vector_math::Vec2d &position, const vector_math::Vec2d &velocity,
                                           const Color &color, float radius)
{
    return std::make_shared<Particle>(position, velocity, color, radius);
}

void Particle::update()
{
    m_position = m_position + m_velocity;
}

void Particle::draw() const
{
    DrawCircleV(m_position.toVector2(), m_radius, m_color);
}

ParticleSystem::ParticleSystem(int nParticles)
{
    for (int i = 0; i < nParticles; ++i)
    {
        float x = GetRandomValue(0, GetScreenWidth());
        float y = GetRandomValue(0, GetScreenHeight());
        float vx = GetRandomValue(-5, 5);
        float vy = GetRandomValue(-5, 5);
        Color color = {GetRandomValue(0, 255), GetRandomValue(0, 255), GetRandomValue(0, 255), 255};
        float radius = GetRandomValue(5, 20);
        m_particles.push_back(Particle::create({x, y}, {vx, vy}, color, radius));
    }
}

std::shared_ptr<ParticleSystem> ParticleSystem::create(int nParticles)
{
    return std::make_shared<ParticleSystem>(nParticles);
}

void ParticleSystem::update()
{
    for (auto &particle : m_particles)
    {
        particle->update();
    }
}

void ParticleSystem::draw() const
{
    for (const auto &particle : m_particles)
    {
        particle->draw();
    }
}
