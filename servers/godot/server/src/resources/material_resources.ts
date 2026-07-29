import { Resource } from 'fastmcp';

export const materialResource: Resource = {
  uri: 'godot/material/info',
  name: 'Material Info',
  description: 'Get material information for a node (use get_material_properties tool with specific node_path)',
  mimeType: 'application/json',
  async load() {
    return {
      text: JSON.stringify({
        message: 'To get material properties, use get_material_properties tool with node_path and surface_index',
        example: 'get_material_properties with node_path="MeshInstance3D" and surface_index=0'
      }, null, 2)
    };
  },
};
