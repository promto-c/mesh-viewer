from typing import Any
from OpenGL import GL

class BaseShader:
    def __init__(self, vertex_shader_file: str, fragment_shader_file: str) -> None:
        self.vertex_shader_source = self.load_shader_from_file(vertex_shader_file)
        self.fragment_shader_source = self.load_shader_from_file(fragment_shader_file)
        self.program: GL.GLuint = None

    @staticmethod
    def load_shader_from_file(file_path: str) -> str:
        """Reads shader source code from a file.

        Args:
            file_path: The path to the shader file.

        Returns:
            The shader source code as a string.
        """
        with open(file_path, 'r') as file:
            return file.read()

    def compile_shader(self, source: str, shader_type: GL.GLenum) -> GL.GLuint:
        """Compiles a shader from given source code.

        Args:
            source: The source code of the shader.
            shader_type: The type of the shader (GL.GL_VERTEX_SHADER, GL.GL_FRAGMENT_SHADER, etc.).

        Returns:
            The compiled shader ID.

        Raises:
            RuntimeError: If shader compilation fails.
        """
        shader: GL.GLuint = GL.glCreateShader(shader_type)
        if not shader:
            raise RuntimeError("Error creating shader.")

        GL.glShaderSource(shader, source)
        GL.glCompileShader(shader)

        # Check for compilation errors
        compile_status: GL.GLint = GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS)
        if not compile_status:
            error: bytes = GL.glGetShaderInfoLog(shader)
            GL.glDeleteShader(shader)
            raise RuntimeError(f"Shader compilation failed: {error.decode()}")

        return shader

    def create_shader_program(self) -> None:
        """Creates a shader program by compiling and linking vertex and fragment shaders.

        Raises:
            RuntimeError: If linking the program fails.
        """
        # Compile shaders
        vertex_shader: GL.GLuint = self.compile_shader(self.vertex_shader_source, GL.GL_VERTEX_SHADER)
        fragment_shader: GL.GLuint = self.compile_shader(self.fragment_shader_source, GL.GL_FRAGMENT_SHADER)

        # Create program and attach shaders
        self.program: GL.GLuint = GL.glCreateProgram()
        if not self.program:
            raise RuntimeError("Error creating shader program.")

        GL.glAttachShader(self.program, vertex_shader)
        GL.glAttachShader(self.program, fragment_shader)

        # Link the program and check for errors
        GL.glLinkProgram(self.program)
        link_status: GL.GLint = GL.glGetProgramiv(self.program, GL.GL_LINK_STATUS)
        if not link_status:
            error: bytes = GL.glGetProgramInfoLog(self.program)
            GL.glDeleteProgram(self.program)
            raise RuntimeError(f"Linking program failed: {error.decode()}")

        # Shaders can be detached and deleted after linking
        GL.glDetachShader(self.program, vertex_shader)
        GL.glDetachShader(self.program, fragment_shader)
        GL.glDeleteShader(vertex_shader)
        GL.glDeleteShader(fragment_shader)

    def use(self) -> None:
        """Activates this shader program for use in the rendering pipeline."""
        GL.glUseProgram(self.program)


    def set_uniform(self, name: str, value: Any) -> None:
        """Sets a uniform value in the shader program, inferring the type from the value.

        Args:
            name: The name of the uniform variable in the shader.
            value: The value to set the uniform to, type is inferred from the value.

        Raises:
            ValueError: If the uniform name is not found or if the value type is unsupported.
        """
        location = GL.glGetUniformLocation(self.program, name)
        if location == -1:
            raise ValueError(f"Uniform '{name}' not found in shader.")

        if isinstance(value, int):
            GL.glUniform1i(location, value)
        elif isinstance(value, float):
            GL.glUniform1f(location, value)
        elif isinstance(value, tuple) or isinstance(value, list):
            if len(value) == 2:
                GL.glUniform2f(location, *value)
            elif len(value) == 3:
                GL.glUniform3f(location, *value)
            elif len(value) == 4:
                GL.glUniform4f(location, *value)
            elif len(value) == 9:
                GL.glUniformMatrix3fv(location, 1, GL.GL_FALSE, value)
            elif len(value) == 16:
                GL.glUniformMatrix4fv(location, 1, GL.GL_FALSE, value)
            else:
                raise ValueError(f"Unsupported uniform array length: {len(value)} for '{name}'.")
        else:
            raise ValueError(f"Unsupported uniform type for '{name}': {type(value)}.")

    def release(self) -> None:
        """Deactivates the shader program."""
        GL.glUseProgram(0)
