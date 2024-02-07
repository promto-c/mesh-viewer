from typing import Any, Dict, List

import re
import numpy as np

from OpenGL import GL

class ShaderUtils:

    # Define a class constant dictionary for GL type to string conversion
    GL_TYPE_TO_STRING = {
        GL.GL_FLOAT: 'float',
        GL.GL_FLOAT_VEC2: 'vec2',
        GL.GL_FLOAT_VEC3: 'vec3',
        GL.GL_FLOAT_VEC4: 'vec4',
        GL.GL_INT: 'int',
        GL.GL_INT_VEC2: 'ivec2',
        GL.GL_INT_VEC3: 'ivec3',
        GL.GL_INT_VEC4: 'ivec4',
        GL.GL_UNSIGNED_INT: 'unsigned int',
        GL.GL_UNSIGNED_INT_VEC2: 'uvec2',
        GL.GL_UNSIGNED_INT_VEC3: 'uvec3',
        GL.GL_UNSIGNED_INT_VEC4: 'uvec4',
        GL.GL_BOOL: 'bool',
        GL.GL_BOOL_VEC2: 'bvec2',
        GL.GL_BOOL_VEC3: 'bvec3',
        GL.GL_BOOL_VEC4: 'bvec4',
        GL.GL_FLOAT_MAT2: 'mat2',
        GL.GL_FLOAT_MAT3: 'mat3',
        GL.GL_FLOAT_MAT4: 'mat4',
        GL.GL_SAMPLER_2D: 'sampler2D',
        GL.GL_SAMPLER_3D: 'sampler3D',
        GL.GL_SAMPLER_CUBE: 'samplerCube',
        GL.GL_SAMPLER_2D_SHADOW: 'sampler2DShadow',
        # Add more types as needed
    }

    # Regular expression to match GLSL uniform declarations with optional default values
    UNIFORM_PATTERN = re.compile(
        r"uniform\s+(?P<type>\w+)\s+(?P<name>\w+)(?:\s*=\s*(?P<default>.*?))?;"
    )

    @staticmethod
    def extract_uniforms(shader_source: str) -> Dict[str, Dict[str, Any]]:
        """Extracts uniform names, types, and default values from a shader source.

        Args:
            shader_source (str): The GLSL shader source code as a string.

        Returns:
            Dict[str, Dict[str, Any]]: A dictionary where each key is the uniform name, and the value is another
                dictionary containing the 'type' and 'default' value of the uniform.
        """
        uniforms = {}
        for match in ShaderUtils.UNIFORM_PATTERN.finditer(shader_source):
            uniform_info = match.groupdict()
            # Convert GLSL default value syntax to a more general format if necessary
            uniform_info['default'] = ShaderUtils.convert_glsl_default(uniform_info['default'])
            # Remove 'name' from the dict and use it as the key in the uniforms dict
            name = uniform_info.pop('name')
            uniforms[name] = uniform_info
        return uniforms
    
    @staticmethod
    def convert_glsl_default(glsl_default_value: str) -> Any:
        """Converts a GLSL default value string to a more general format, such as
        Python scalars, lists, or NumPy arrays for vectors and matrices.

        Args:
            glsl_default_value (str): The GLSL default value string.

        Returns:
            Any: The converted default value in a more general format.
        """
        # Remove whitespaces for cleaner parsing
        glsl_default_value = glsl_default_value.replace(' ', '')

        # Match for vectors (vec2, vec3, vec4)
        vector_match = re.match(r'vec(\d)\((.*)\)', glsl_default_value)
        if vector_match:
            size, values_str = vector_match.groups()
            values = [float(val) for val in values_str.split(',')]
            if len(values) == int(size):  # Ensure the number of values matches the vector size
                return values

        # Match for matrices (mat2, mat3, mat4)
        matrix_match = re.match(r'mat(\d)\((.*)\)', glsl_default_value)
        if matrix_match:
            size, values_str = matrix_match.groups()
            values = [float(val) for val in values_str.split(',')]
            size = int(size)
            if len(values) == size * size:  # Ensure the total number matches the matrix size
                return np.array(values).reshape((size, size))

        # Match for scalar floats
        scalar_match = re.match(r'([-+]?[0-9]*\.?[0-9]+)', glsl_default_value)
        if scalar_match:
            return float(scalar_match.group(0))

        # If no known format is matched, return the original string
        return glsl_default_value

    @staticmethod
    def get_active_uniforms(shader_program):
        # Retrieve the number of active uniforms
        num_uniforms = GL.glGetProgramiv(shader_program, GL.GL_ACTIVE_UNIFORMS)

        uniforms = {}
        for i in range(num_uniforms):
            # Get the name, size, and type of the ith uniform
            name, size, uniform_type = GL.glGetActiveUniform(shader_program, i)

            # Convert the type to a more readable format (optional)
            type_name = ShaderUtils.convert_gl_type_to_string(uniform_type)

            # Store uniform information
            uniforms[name] = {'size': size, 'type': type_name}

        return uniforms

    @staticmethod
    def convert_gl_type_to_string(gl_type):
        # Use the class constant dictionary for conversion
        return ShaderUtils.GL_TYPE_TO_STRING.get(gl_type, 'unknown')


if __name__ == '__main__':
    # Example usage
    shader_source = """
        uniform vec3 lightColor = vec3(1.0, 1.0, 1.0);
        uniform float ambientStrength = 0.1;
        // Other uniforms and shader code...
    """

    uniforms = ShaderUtils.extract_uniforms(shader_source)
    print(uniforms)
