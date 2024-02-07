#version 330 core

out vec4 FragColor;

in vec3 Normal; // Normal from vertex shader
in vec3 FragPos; // Fragment position from vertex shader

uniform vec3 lightPos; // Position of the light source
uniform vec3 lightColor; // Color of the light
uniform vec3 objectColor; // Color of the object

void main()
{
    // Ambient lighting
    float ambientStrength = 0.1;
    vec3 ambient = ambientStrength * lightColor;
    
    // Diffuse lighting
    vec3 norm = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(norm, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;
    
    // Combine the two components
    vec3 result = (ambient + diffuse) * objectColor;
    FragColor = vec4(result, 1.0);
}
