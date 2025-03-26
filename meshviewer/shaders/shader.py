from meshviewer.shaders.base_shader import BaseShader, SHADERS_ROOT


class PhongShader(BaseShader):
    FRAGMENT_SHADER_FILE = SHADERS_ROOT / "glsl/phong_fragment_shader.glsl"

class BlinnPhongShader(BaseShader):
    FRAGMENT_SHADER_FILE = SHADERS_ROOT / "glsl/blinn_phong_fragment_shader.glsl"

class LambertianShader(BaseShader):
    FRAGMENT_SHADER_FILE = SHADERS_ROOT / "glsl/lambertian_fragment_shader.glsl"

class DisparityShader(BaseShader):
    VERTEX_SHADER_FILE = SHADERS_ROOT / "glsl/disparity_vertex_shader.glsl"
    FRAGMENT_SHADER_FILE = SHADERS_ROOT / "glsl/disparity_fragment_shader.glsl"
