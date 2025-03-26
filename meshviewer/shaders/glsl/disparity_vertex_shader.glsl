#version 330 core
layout (location = 0) in vec3 position;

uniform mat4 model;
uniform mat4 leftView;
uniform mat4 rightView;
uniform mat4 projection;
uniform vec2 screenSize; // in pixels

out vec4 disparityData;

void main() {
    vec4 posModel = vec4(position, 1.0);
    
    // Compute projected positions from both cameras
    vec4 posLeft = projection * leftView * model * posModel;
    vec4 posRight = projection * rightView * model * posModel;
    
    // Perspective division to get normalized device coordinates (NDC)
    vec2 ndcLeft = posLeft.xy / posLeft.w;
    vec2 ndcRight = posRight.xy / posRight.w;
    
    // Convert NDC to pixel coordinates
    vec2 pixelLeft = ((ndcLeft + vec2(1.0)) * 0.5) * screenSize/10;
    vec2 pixelRight = ((ndcRight + vec2(1.0)) * 0.5) * screenSize/10;
    
    // Compute disparity (pixel offsets)
    vec2 dispLtoR = pixelRight - pixelLeft;
    vec2 dispRtoL = -dispLtoR; // or pixelLeft - pixelRight
    
    // Pack the disparity: R,G = left-to-right disparity, B,A = right-to-left disparity
    disparityData = vec4(dispLtoR, dispRtoL);
    
    // Use the left camera’s projection as the final vertex position.
    gl_Position = posLeft;
}
