/**
 * Auto-detect application paths for game development tools.
 */

import { execSync } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

interface ApplicationInfo {
  path: string;
  version: string;
  found: boolean;
}

interface AllApplicationInfo {
  godot: ApplicationInfo;
  aseprite: ApplicationInfo;
}

class PathResolver {
  private platform: string = os.platform();
  private cache: Map<string, string | null> = new Map();

  /**
   * Get all detected tool paths.
   */
  getAllPaths(): AllApplicationInfo {
    return {
      godot: this.getGodotInfo(),
      aseprite: this.getAsepriteInfo(),
    };
  }

  /**
   * Get Godot 4.x executable path and version.
   */
  getGodotInfo(): ApplicationInfo {
    const exePath = this.findGodot4();

    if (exePath && this.pathExists(exePath)) {
      return {
        path: exePath,
        version: this.getExecutableVersion(exePath) || 'unknown',
        found: true,
      };
    }

    return {
      path: 'Not found',
      version: 'N/A',
      found: false,
    };
  }

  /**
   * Get Aseprite executable path and version.
   */
  getAsepriteInfo(): ApplicationInfo {
    const exePath = this.findAseprite();

    if (exePath && this.pathExists(exePath)) {
      return {
        path: exePath,
        version: this.getExecutableVersion(exePath) || 'unknown',
        found: true,
      };
    }

    return {
      path: 'Not found',
      version: 'N/A',
      found: false,
    };
  }

  /**
   * Find Godot 4.x executable.
   */
  private findGodot4(): string | null {
    const cacheKey = 'godot4';
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey) || null;
    }

    let result: string | null = null;

    if (this.platform === 'win32') {
      const candidates = [
        'C:\\Program Files\\Godot\\Godot_v4*.exe',
        'C:\\Program Files (x86)\\Godot\\Godot_v4*.exe',
        'D:\\Program Files\\Godot\\Godot_v4*.exe',
        'C:\\Godot\\Godot_v4*.exe',
        'D:\\Godot\\Godot_v4*.exe',
      ];

      for (const pattern of candidates) {
        const match = this.glob(pattern);
        if (match && match.includes('Godot_v4')) {
          result = match;
          break;
        }
      }

      // Check PATH
      if (!result) {
        result = this.which('godot4.exe') || this.which('godot.exe');
      }
    } else if (this.platform === 'darwin') {
      const candidates = [
        '/Applications/Godot_mono.app/Contents/MacOS/Godot',
        '/Applications/Godot.app/Contents/MacOS/Godot',
      ];
      for (const p of candidates) {
        if (this.pathExists(p)) {
          result = p;
          break;
        }
      }
    } else {
      // Linux
      result = this.which('godot4') || this.which('godot');
    }

    this.cache.set(cacheKey, result);
    return result;
  }

  /**
   * Find Aseprite executable.
   */
  private findAseprite(): string | null {
    const cacheKey = 'aseprite';
    if (this.cache.has(cacheKey)) {
      return this.cache.get(cacheKey) || null;
    }

    let result: string | null = null;

    if (this.platform === 'win32') {
      const candidates = [
        'C:\\Program Files\\Aseprite\\Aseprite.exe',
        'C:\\Program Files (x86)\\Steam\\steamapps\\common\\Aseprite\\Aseprite.exe',
        'D:\\Program Files\\Aseprite\\Aseprite.exe',
        'D:\\Games\\Aseprite*\\Aseprite.exe',
      ];

      for (const p of candidates) {
        if (p.includes('*')) {
          const match = this.glob(p);
          if (match) {
            result = match;
            break;
          }
        } else if (this.pathExists(p)) {
          result = p;
          break;
        }
      }
    } else if (this.platform === 'darwin') {
      const candidates = [
        '/Applications/Aseprite.app/Contents/MacOS/aseprite',
        '/Applications/Aseprite.app/Contents/MacOS/Aseprite',
      ];
      for (const p of candidates) {
        if (this.pathExists(p)) {
          result = p;
          break;
        }
      }
    } else {
      // Linux
      result = this.which('aseprite');
    }

    this.cache.set(cacheKey, result);
    return result;
  }

  /**
   * Get version of an executable.
   */
  private getExecutableVersion(exePath: string): string | null {
    try {
      const output = execSync(`"${exePath}" --version`, {
        encoding: 'utf8',
        timeout: 5000,
      }).trim();
      return output.split('\n')[0];
    } catch {
      return null;
    }
  }

  /**
   * Find executable in PATH.
   */
  private which(command: string): string | null {
    try {
      const whereCmd = this.platform === 'win32' ? 'where' : 'which';
      const output = execSync(`${whereCmd} ${command}`, {
        encoding: 'utf8',
        timeout: 5000,
      }).trim();
      return output.split('\n')[0] || null;
    } catch {
      return null;
    }
  }

  /**
   * Simple glob for Windows paths with wildcards.
   */
  private glob(pattern: string): string | null {
    try {
      const dir = path.dirname(pattern);
      const filePattern = path.basename(pattern).replace(/\*/g, '.*');

      if (!fs.existsSync(dir)) {
        return null;
      }

      const files = fs.readdirSync(dir);
      const regex = new RegExp(`^${filePattern}$`, 'i');

      for (const file of files) {
        if (regex.test(file)) {
          return path.join(dir, file);
        }
      }

      return null;
    } catch {
      return null;
    }
  }

  /**
   * Check if path exists.
   */
  private pathExists(filePath: string): boolean {
    try {
      return fs.existsSync(filePath);
    } catch {
      return false;
    }
  }
}

// Singleton
const resolver = new PathResolver();

export function getAllApplicationInfo(): AllApplicationInfo {
  return resolver.getAllPaths();
}

export function getGodotInfo(): ApplicationInfo {
  return resolver.getGodotInfo();
}

export function getAsepriteInfo(): ApplicationInfo {
  return resolver.getAsepriteInfo();
}

export function resolveApplicationPath(application: string): ApplicationInfo {
  const app = application.toLowerCase().trim();

  if (['godot', 'godot4', 'godot.exe'].includes(app)) {
    return getGodotInfo();
  } else if (['aseprite', 'aseprite.exe'].includes(app)) {
    return getAsepriteInfo();
  }

  return {
    path: 'Unknown application',
    version: 'N/A',
    found: false,
  };
}

export { ApplicationInfo, AllApplicationInfo };