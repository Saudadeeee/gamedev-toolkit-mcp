import { Resource, ResourceTemplate } from 'fastmcp';
import { getGodotConnection } from '../utils/godot_connection.js';
import { z } from 'zod';

/**
 * Resource that provides the content of a specific script
 * Note: As a Resource (not ResourceTemplate), it cannot handle dynamic paths
 */
export const scriptResource: Resource = {
    uri: 'godot/script',
    name: 'Godot Script Content',
    mimeType: 'text/plain',
    async load() {
        const godot = getGodotConnection();
        
        try {
            // Without parameters, this can only load a predefined script
            // You would need to hardcode the script path here
            const scriptPath = 'res://default_script.gd';
            
            const result = await godot.sendCommand('get_script', {
                path: scriptPath
            });
            
            return {
                text: result.content,
                metadata: {
                    path: result.script_path,
                    language: scriptPath.endsWith('.gd') ? 'gdscript' : 
                                     scriptPath.endsWith('.cs') ? 'csharp' : 'unknown'
                }
            };
        } catch (error) {
            console.error('Error fetching script content:', error);
            throw error;
        }
    }
};

/**
 * Resource that provides a list of all scripts in the project
 */
export const scriptListResource: Resource = {
  uri: 'godot/scripts',
  name: 'Godot Script List',
  mimeType: 'application/json',
  async load() {
    const godot = getGodotConnection();
    
    try {
      // Call a command on the Godot side to list all scripts
      const result = await godot.sendCommand('list_project_files', {
        extensions: ['.gd', '.cs']
      });
      
      if (result && result.files) {
        return {
          text: JSON.stringify({
            scripts: result.files,
            count: result.files.length,
            gdscripts: result.files.filter((f: string) => f.endsWith('.gd')),
            csharp_scripts: result.files.filter((f: string) => f.endsWith('.cs'))
          })
        };
      } else {
        return {
          text: JSON.stringify({
            scripts: [],
            count: 0,
            gdscripts: [],
            csharp_scripts: []
          })
        };
      }
    } catch (error) {
      console.error('Error fetching script list:', error);
      throw error;
    }
  }
};

/**
 * Resource that provides metadata for a specific script, including classes and methods
 */
export const scriptMetadataResource: Resource = {
    uri: 'godot/script/metadata',
    name: 'Godot Script Metadata',
    mimeType: 'application/json',
    async load() {
        const godot = getGodotConnection();
        
        // Use a fixed script path
        let scriptPath = 'res://default_script.gd';
        
        try {
            // Call a command on the Godot side to get script metadata
            const result = await godot.sendCommand('get_script_metadata', {
                path: scriptPath
            });
            
            return {
                text: JSON.stringify(result)
            };
        } catch (error) {
            console.error('Error fetching script metadata:', error);
            throw error;
        }
    }
};
