// Disparity Shader
#version 330 core

in vec3 FragPos;
in vec3 Normal;

// Uniforms for disparity rendering
uniform float eyeSeparation;
uniform float nearClip;
uniform float farClip;
uniform float fov;

out vec4 FragColor;

float linearizeDepth(float depth) {
    float z = depth * 2.0 - 1.0;
    return (2.0 * nearClip * farClip) / (farClip + nearClip - z * (farClip - nearClip));
}

void main() {
    float z_linear = linearizeDepth(gl_FragCoord.z);
    float focal = 1.0 / tan(radians(fov) / 2.0);
    float disparity = eyeSeparation * focal / z_linear;
    FragColor = vec4(disparity, 0.0, 0.0, 1.0);
}
