import pymeshlab
import pickle
import numpy as np

def load_mesh(file_path: str):
    """Loads a mesh from the given file path and returns the combined vertices, faces, and normals.
    
    Args:
        file_path: str, the path to the mesh file.
    
    Returns:
        tuple of np.ndarray: combined vertices, faces, and normals of the mesh.
    """
    # Initialize MeshSet and load the specified mesh file
    mesh_set = pymeshlab.MeshSet()
    mesh_set.load_new_mesh(file_path)

    # Check if the mesh set is empty
    if mesh_set.mesh_number() == 0:
        raise ValueError("No meshes found in the file.")

    # Use list comprehension for efficiency and readability
    meshes = [mesh_set.mesh(i) for i in range(mesh_set.mesh_number())]

    # Combine arrays
    combined_vertices = np.concatenate([m.vertex_matrix() for m in meshes])
    combined_faces = np.concatenate([m.face_matrix() + sum([v.vertex_matrix().shape[0] for v in meshes[:i]]) for i, m in enumerate(meshes)])
    combined_normals = np.concatenate([m.vertex_normal_matrix() for m in meshes])

    return combined_vertices, combined_faces, combined_normals

def save_combined_mesh_data(file_path, mesh_data):
    # Use a context manager to safely write the mesh data to a file
    with open(file_path, 'wb') as outfile:
        pickle.dump(mesh_data, outfile)

if __name__ == "__main__":
    # Specify the path to the mesh file
    mesh_file_path = 'head.stl'
    mesh_data = load_mesh(mesh_file_path)

    # Specify the output file path for the combined mesh data
    output_file_path = 'mesh_data.pkl'
    save_combined_mesh_data(output_file_path, mesh_data)
