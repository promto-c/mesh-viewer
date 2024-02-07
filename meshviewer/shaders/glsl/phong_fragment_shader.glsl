#version 330 core
out vec4 FragColor;

in vec3 FragPos;
in vec3 Normal;

// Define default values for uniforms
uniform vec3 lightPos = vec3(1.0, 1.0, 1.0);
uniform vec3 viewPos = vec3(0.0, 0.0, 0.0);
uniform vec3 lightColor = vec3(1.0, 1.0, 1.0); // White light by default
uniform vec3 objectColor = vec3(1.0, 0.5, 0.31); // Default object color
uniform float ambientStrength = 0.1;
uniform float specularStrength = 0.5;
uniform float shininess = 32.0;

void main() {
    // Ambient component
    vec3 ambient = ambientStrength * lightColor;

    // Diffuse component
    vec3 normalizedNormal = normalize(Normal);
    vec3 lightDir = normalize(lightPos - FragPos);
    float diff = max(dot(normalizedNormal, lightDir), 0.0);
    vec3 diffuse = diff * lightColor;

    // Specular component
    vec3 viewDir = normalize(viewPos - FragPos);
    vec3 reflectDir = reflect(-lightDir, normalizedNormal);  
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), shininess);
    vec3 specular = specularStrength * spec * lightColor;  

    vec3 result = (ambient + diffuse + specular) * objectColor;
    FragColor = vec4(result, 1.0);
}
