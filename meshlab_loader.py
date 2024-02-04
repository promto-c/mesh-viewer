import pymeshlab
import pickle
import numpy as np

def load_and_combine_meshes(file_path):
    # Initialize MeshSet and load the specified mesh file
    mesh_set = pymeshlab.MeshSet()
    mesh_set.load_new_mesh(file_path)

    # Initialize lists to store mesh data from all meshes
    vertices_list = []
    faces_list = []
    normals_list = []

    # Initialize face offset for correctly indexing faces in combined mesh
    face_offset = 0

    # Iterate through each mesh in the MeshSet
    for i in range(mesh_set.mesh_number()):
        mesh_set.set_current_mesh(i)
        current_mesh = mesh_set.current_mesh()

        # Extract vertices, faces, and normals from the current mesh
        vertices = current_mesh.vertex_matrix()
        faces = current_mesh.face_matrix() + face_offset  # Adjust face indices based on the offset
        normals = current_mesh.vertex_normal_matrix()

        # Append current mesh data to the lists
        vertices_list.append(vertices)
        faces_list.append(faces)
        normals_list.append(normals)

        # Update the face offset for the next mesh
        face_offset += vertices.shape[0]

    # Combine all mesh data into single arrays if there are multiple meshes
    if mesh_set.mesh_number() > 1:
        combined_vertices = np.vstack(vertices_list)
        combined_faces = np.vstack(faces_list)
        combined_normals = np.vstack(normals_list)
    else:
        combined_vertices, combined_faces, combined_normals = vertices_list[0], faces_list[0], normals_list[0]

    return combined_vertices, combined_faces, combined_normals

def save_combined_mesh_data(file_path, mesh_data):
    # Use a context manager to safely write the mesh data to a file
    with open(file_path, 'wb') as outfile:
        pickle.dump(mesh_data, outfile)

if __name__ == "__main__":
    # Specify the path to the mesh file
    mesh_file_path = 'meshviewer\example_models\Room.obj'
    combined_mesh_data = load_and_combine_meshes(mesh_file_path)

    # Specify the output file path for the combined mesh data
    output_file_path = 'mesh_data.pkl'
    save_combined_mesh_data(output_file_path, combined_mesh_data)
