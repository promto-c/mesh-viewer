#version 330 core
// Input variables from the vertex shader
in vec3 FragPos;
in vec3 Normal;

// Uniform variables for lighting and material properties
uniform vec3 lightPos = vec3(1.0, 1.0, 1.0);
uniform vec3 viewPos = vec3(0.0, 0.0, 0.0);
uniform vec3 lightColor = vec3(1.0, 1.0, 1.0);
uniform vec3 objectColor = vec3(1.0, 0.5, 0.31);
uniform float ambientStrength = 0.1;
uniform float specularStrength = 0.5;
uniform float shininess = 32.0;

// Output variable for the fragment color
out vec4 FragColor;

void main() {
    // 1. Ambient component: constant lighting regardless of direction
    vec3 ambient = ambientStrength * lightColor;

    // 2. Diffuse component: Lambert's cosine law
    vec3 norm = normalize(Normal);                  // Normalize interpolated normal
    vec3 lightDir = normalize(lightPos - FragPos);  // Direction vector from fragment to light source
    float diff = max(dot(norm, lightDir), 0.0);     // Dot product for diffuse component
    vec3 diffuse = diff * lightColor;               // Scale by light color

    // 3. Specular component: Phong reflection model
    vec3 viewDir = normalize(viewPos - FragPos);    // Direction from fragment to viewer
    vec3 reflectDir = reflect(-lightDir, norm);     // Reflect light direction around normal
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), shininess); // Specular intensity
    vec3 specular = specularStrength * spec * lightColor;            // Scale by light color and strength

    // Final color calculation combining all three components
    vec3 result = (ambient + diffuse + specular) * objectColor;
    FragColor = vec4(result, 1.0); // Output the final color
}
