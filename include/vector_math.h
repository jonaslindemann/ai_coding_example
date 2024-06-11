#pragma once

#include <raylib.h>

#include <cmath>

namespace vector_math {

class Vec2d {
private:
    float m_x, m_y;

public:
    // Constructors
    Vec2d();
    Vec2d(float x, float y);
    Vec2d(const Vector2 &v);

    // Basic vector operations
    Vec2d operator+(const Vec2d &other) const;
    Vec2d operator-(const Vec2d &other) const;

    Vec2d operator*(float scalar) const;

    float magnitude() const;

    // Convert to raylib's Vector2
    Vector2 toVector2() const;

    // Getters for x and y
    float x() const;
    float y() const;
};

} // namespace vector_math
