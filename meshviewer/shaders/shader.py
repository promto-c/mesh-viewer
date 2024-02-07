from meshviewer.shaders.base_shader import BaseShader

from pathlib import Path
SHADERS_ROOT = Path(__file__).parent

class PhongShader(BaseShader):
    def __init__(self) -> None:
        # Specify the paths to your vertex and fragment shader files
        vertex_shader_file = SHADERS_ROOT / "glsl/phong_vertex_shader.glsl"
        fragment_shader_file = SHADERS_ROOT / "glsl/phong_fragment_shader.glsl"

        super().__init__(vertex_shader_file, fragment_shader_file)

class BlinnPhongShader(BaseShader):
    def __init__(self):
        vertex_shader_file = SHADERS_ROOT / "glsl/blinn_phong_vertex_shader.glsl"
        fragment_shader_file = SHADERS_ROOT / "glsl/blinn_phong_fragment_shader.glsl"

        super().__init__(vertex_shader_file, fragment_shader_file)

class LambertianShader(BaseShader):
    def __init__(self) -> None:
        # Specify the paths to your vertex and fragment shader files
        vertex_shader_file = Path(__file__).parent / "glsl/lambertian_vertex_shader.glsl"
        fragment_shader_file = Path(__file__).parent / "glsl/lambertian_fragment_shader.glsl"

        super().__init__(vertex_shader_file, fragment_shader_file)
