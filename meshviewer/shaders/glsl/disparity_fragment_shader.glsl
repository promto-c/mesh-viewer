#version 330 core
in vec4 disparityData;
out vec4 FragColor;

void main() {
    FragColor = disparityData;
}
