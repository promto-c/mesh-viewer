#version 330 core
// Input variables from the vertex shader
in vec3 FragPos;
in vec3 Normal;

// Uniform variables for lighting and material properties
uniform vec3 lightPos;
uniform vec3 lightColor;
uniform vec3 objectColor;
uniform float ambientStrength = 0.1;
uniform float diffuseStrength = 1.0;

// Output variable for the fragment color
out vec4 FragColor;

void main() {
    // 1. Ambient lighting component
    vec3 ambient = ambientStrength * lightColor;

    // 2. Diffuse lighting component based on Lambertian reflection
    vec3 norm = normalize(Normal);                   // Normalize the interpolated normal
    vec3 lightDir = normalize(lightPos - FragPos);   // Direction vector from the fragment to the light source
    float diff = max(dot(norm, lightDir), 0.0);      // Compute the diffuse intensity (dot product)
    vec3 diffuse = diffuseStrength * diff * lightColor; // Scale diffuse component by light color and strength

    // 3. Combine ambient and diffuse components
    vec3 result = (ambient + diffuse) * objectColor; // Combine lighting components with object color
    FragColor = vec4(result, 1.0);                   // Output the final color
}
