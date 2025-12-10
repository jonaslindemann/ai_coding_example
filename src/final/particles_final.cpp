#include "particles.h"

using namespace particles;

particles::Particle::Particle(Vector2 position, Vector2 velocity, float radius, Color color)
    : m_color(color), m_position(position), m_radius(radius), m_velocity(velocity)
{}

std::shared_ptr<particles::Particle> particles::Particle::create(Vector2 position, Vector2 velocity, float radius,
                                                                 Color color)
{
    return std::make_shared<Particle>(position, velocity, radius, color);
}

void particles::Particle::update()
{
    m_position = m_position + m_velocity;
}

void particles::Particle::draw()
{
    DrawCircleV(m_position.toVector2(), m_radius, m_color);
}

bool particles::Particle::isAlive()
{
    return true;
}

Vector2 particles::Particle::position()
{
    return m_position.toVector2();
}

float particles::Particle::radius()
{
    return m_radius;
}

Color particles::Particle::color()
{
    return m_color;
}

void particles::Particle::setPosition(Vector2 position)
{
    m_position = position;
}

void particles::Particle::setVelocity(Vector2 velocity)
{
    m_velocity = velocity;
}

void particles::Particle::reverseVelocity()
{
    m_velocity = m_velocity * -1.0f;
}

Vector2 particles::Particle::velocity()
{
    return m_velocity.toVector2();
}

void particles::Particle::bounceX()
{
    m_velocity = {m_velocity.x() * -1.0f, m_velocity.y()};
}

void particles::Particle::bounceY()
{
    m_velocity = {m_velocity.x(), m_velocity.y() * -1.0f};
}

particles::ParticleSystem::ParticleSystem(int nParticles)
{
    for (int i = 0; i < nParticles; i++)
    {
        Vector2 position = {GetRandomValue(0, GetScreenWidth()), GetRandomValue(0, GetScreenHeight())};
        Vector2 velocity = {GetRandomValue(-5, 5) * 0.1f, GetRandomValue(-5, 5) * 0.1f};
        float radius = GetRandomValue(5, 20);
        Color color = {GetRandomValue(0, 255), GetRandomValue(0, 255), GetRandomValue(0, 255), 255};

        m_particles.push_back(std::make_shared<Particle>(position, velocity, radius, color));
    }
}

std::shared_ptr<particles::ParticleSystem> particles::ParticleSystem::create(int nParticles)
{
    return std::make_shared<ParticleSystem>(nParticles);
}

void particles::ParticleSystem::update()
{
    for (auto &particle : m_particles)
    {
        particle->update();
    }
}

void particles::ParticleSystem::draw()
{
    for (auto &particle : m_particles)
    {
        particle->draw();
    }
}

void particles::ParticleSystem::checkBounds()
{
    for (auto &particle : m_particles)
    {
        if (particle->position().x < 0 || particle->position().x > GetScreenWidth())
        {
            particle->bounceX();
        }

        if (particle->position().y < 0 || particle->position().y > GetScreenHeight())
        {
            particle->bounceY();
        }
    }
}
