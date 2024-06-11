#include "particle.h"

using namespace particles;

particles::Particle::Particle(Vector2 position, Vector2 velocity, float radius, Color color)
    : m_color(color), m_position(position), m_radius(radius), m_velocity(velocity)
{}

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
    return false;
}

Vector2 particles::Particle::position()
{
    return Vector2();
}

float particles::Particle::radius()
{
    return 0.0f;
}

Color particles::Particle::color()
{
    return Color();
}
