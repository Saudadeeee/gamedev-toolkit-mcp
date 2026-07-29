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
  private steamLibraryCache: string[] | null = null;

  /**
   * Every Steam library folder on this machine.
   *
   * Guessing at `C:\Program Files (x86)\Steam` misses any non-default
   * install — Steam lets you put the client anywhere and add libraries on
   * other drives. The registry knows where the client is; libraryfolders.vdf
   * lists the rest.
   */
  private steamLibraries(): string[] {
    if (this.steamLibraryCache) return this.steamLibraryCache;

    const roots: string[] = [];

    if (this.platform === 'win32') {
      const keys = [
        'HKCU\\Software\\Valve\\Steam',
        'HKLM\\SOFTWARE\\WOW6432Node\\Valve\\Steam',
        'HKLM\\SOFTWARE\\Valve\\Steam',
      ];
      for (const key of keys) {
        for (const value of ['SteamPath', 'InstallPath']) {
          try {
            const out = execSync(`reg query "${key}" /v ${value}`, {
              encoding: 'utf8',
              timeout: 5000,
              stdio: ['ignore', 'pipe', 'ignore'],
            });
            const match = out.match(/REG_SZ\s+(.+)/);
            if (match) {
              const dir = match[1].trim();
              if (fs.existsSync(dir)) roots.push(dir);
            }
          } catch {
            /* key or value absent */
          }
        }
      }
    }

    for (const relative of [
      '.local/share/Steam',
      '.steam/steam',
      'Library/Application Support/Steam',
    ]) {
      roots.push(path.join(os.homedir(), relative));
    }

    const libraries: string[] = [];
    const seen = new Set<string>();
    const remember = (dir: string) => {
      if (!dir || !this.pathExists(dir)) return;
      // The registry returns the same folder in different casings, which
      // would otherwise make every lookup run twice.
      const key = path.resolve(dir).toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      libraries.push(dir);
    };

    for (const root of roots) {
      remember(root);

      const vdf = path.join(root, 'steamapps', 'libraryfolders.vdf');
      if (!this.pathExists(vdf)) continue;
      try {
        const contents = fs.readFileSync(vdf, 'utf8');
        const pattern = /"path"\s+"([^"]+)"/g;
        let match: RegExpExecArray | null;
        while ((match = pattern.exec(contents)) !== null) {
          remember(match[1].replace(/\\\\/g, '\\'));
        }
      } catch {
        /* unreadable config */
      }
    }

    this.steamLibraryCache = libraries;
    return libraries;
  }

  /** Expand app-relative paths against every Steam library. */
  private steamApps(...relatives: string[]): string[] {
    return this.steamLibraries().flatMap((library) =>
      relatives.map((relative) => path.join(library, 'steamapps', 'common', relative))
    );
  }

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
        'C:\\Games\\Godot*\\Godot_v4*.exe',
        'D:\\Games\\Godot*\\Godot_v4*.exe',
        `${process.env.LOCALAPPDATA ?? ''}\\Programs\\Godot\\Godot_v4*.exe`,
        // Steam ships the editor as godot.windows.opt.tools.64.exe -- nothing
        // like the Godot_v4* name the official downloads use, so a
        // name-pattern-only search never finds a Steam install.
        ...this.steamApps(
          'Godot Engine\\godot.windows.opt.tools.64.exe',
          'Godot Engine\\godot.windows.opt.tools.*.exe',
          'Godot Engine\\Godot*.exe'
        ),
      ];

      result = this.firstGodot4(candidates);

      // Check PATH
      if (!result) {
        result = this.which('godot4.exe') || this.which('godot.exe');
      }
    } else if (this.platform === 'darwin') {
      result = this.firstGodot4([
        '/Applications/Godot_mono.app/Contents/MacOS/Godot',
        '/Applications/Godot.app/Contents/MacOS/Godot',
        ...this.steamApps('Godot Engine/Godot.app/Contents/MacOS/Godot'),
      ]);
      result = result || this.which('godot4') || this.which('godot');
    } else {
      // Linux
      result =
        this.which('godot4') ||
        this.which('godot') ||
        this.firstGodot4([
          ...this.steamApps(
            'Godot Engine/godot.x11.opt.tools.64',
            'Godot Engine/godot.linuxbsd.opt.tools.*'
          ),
        ]);
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
        'C:\\Program Files (x86)\\Aseprite\\Aseprite.exe',
        'D:\\Program Files\\Aseprite\\Aseprite.exe',
        `${process.env.LOCALAPPDATA ?? ''}\\Programs\\Aseprite\\Aseprite.exe`,
        // Real Steam libraries, read from the registry, rather than a guess at
        // where Steam might have been installed.
        ...this.steamApps('Aseprite\\Aseprite.exe'),
        'C:\\Games\\Aseprite*\\Aseprite.exe',
        'D:\\Games\\Aseprite*\\Aseprite.exe',
        // Source builds land several levels deeper than an installer copy.
        'C:\\Games\\Aseprite*\\*\\build\\bin\\aseprite.exe',
        'D:\\Games\\Aseprite*\\*\\build\\bin\\aseprite.exe',
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

      if (!result) {
        result = this.which('aseprite.exe');
      }
    } else if (this.platform === 'darwin') {
      const candidates = [
        '/Applications/Aseprite.app/Contents/MacOS/aseprite',
        '/Applications/Aseprite.app/Contents/MacOS/Aseprite',
        ...this.steamApps('Aseprite/Aseprite.app/Contents/MacOS/aseprite'),
      ];
      for (const p of candidates) {
        if (this.pathExists(p)) {
          result = p;
          break;
        }
      }
    } else {
      // Linux
      result =
        this.which('aseprite') ||
        this.steamApps('Aseprite/aseprite').find((p) => this.pathExists(p)) ||
        null;
    }

    this.cache.set(cacheKey, result);
    return result;
  }

  /**
   * First candidate that resolves *and* reports Godot 4.
   *
   * Steam and several distro packages use the same filename for Godot 3 and
   * 4, so the name proves nothing. This server targets Godot 4 only; handing
   * back a 3.x binary produces failures far from here.
   */
  private firstGodot4(candidates: string[]): string | null {
    for (const candidate of candidates) {
      const found = candidate.includes('*')
        ? this.glob(candidate)
        : this.pathExists(candidate)
          ? candidate
          : null;
      if (!found) continue;

      const version = this.getExecutableVersion(found);
      if (version === null || version.startsWith('4.')) return found;
    }
    return null;
  }

  /**
   * Get version of an executable.
   */
  private getExecutableVersion(exePath: string): string | null {
    try {
      const output = execSync(`"${exePath}" --version`, {
        encoding: 'utf8',
        timeout: 5000,
        // Discard the child's stderr: this server speaks MCP over stdio and
        // logs to stderr, so a probe's diagnostics would land in the log.
        stdio: ['ignore', 'pipe', 'ignore'],
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
        // `where` writes "Could not find files" to stderr on a miss, which
        // would otherwise show up as a server log line on every lookup.
        stdio: ['ignore', 'pipe', 'ignore'],
      }).trim();
      const first = output.split('\n')[0]?.trim();
      return first && this.pathExists(first) ? first : null;
    } catch {
      return null;
    }
  }

  /**
   * Expand a path pattern that may contain `*` in any component.
   *
   * Globbing only the basename — the obvious approach — silently returns
   * nothing whenever the wildcard sits in a directory component, because
   * `existsSync` is then asked about a literal path containing `*`. This walks
   * segment by segment instead, branching wherever a segment has a wildcard.
   *
   * Returns the most recently modified match so a machine with several
   * installed versions gets the newest one.
   */
  private glob(pattern: string): string | null {
    try {
      const segments = pattern.split(/[\\/]+/).filter((s) => s.length > 0);
      if (segments.length === 0) return null;

      // On Windows the first segment is a drive ("D:"); it needs the separator
      // back or path.join treats it as a relative name.
      let frontier: string[] = [/^[a-zA-Z]:$/.test(segments[0]) ? segments[0] + path.sep : segments[0]];

      for (const segment of segments.slice(1)) {
        if (frontier.length === 0) return null;

        if (!segment.includes('*')) {
          frontier = frontier
            .map((base) => path.join(base, segment))
            .filter((p) => this.pathExists(p));
          continue;
        }

        const regex = new RegExp(`^${segment.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*')}$`, 'i');
        const next: string[] = [];
        for (const base of frontier) {
          let entries: string[];
          try {
            entries = fs.readdirSync(base);
          } catch {
            continue;
          }
          for (const entry of entries) {
            if (regex.test(entry)) next.push(path.join(base, entry));
          }
        }
        frontier = next;
      }

      const files = frontier.filter((p) => {
        try {
          return fs.statSync(p).isFile();
        } catch {
          return false;
        }
      });
      if (files.length === 0) return null;

      return files.sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
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