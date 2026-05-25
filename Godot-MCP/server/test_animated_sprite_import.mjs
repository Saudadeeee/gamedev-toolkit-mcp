import fs from 'fs';
import path from 'path';

function buildFrameList(data) {
  const frames = data.frames;
  let entries = [];

  if (Array.isArray(frames)) {
    entries = frames;
  } else if (frames && typeof frames === 'object') {
    entries = Object.entries(frames).map(([name, entry]) => ({
      ...entry,
      _frame_name: name,
    }));
  } else {
    throw new Error("frames must be an array or object");
  }

  entries.sort((a, b) => {
    const aName = String(a.filename ?? a._frame_name ?? '');
    const bName = String(b.filename ?? b._frame_name ?? '');
    return aName.localeCompare(bName, undefined, { numeric: true, sensitivity: 'base' });
  });

  return entries
    .map((entry) => entry.frame)
    .filter((frame) => frame && frame.w > 0 && frame.h > 0);
}

const sampleMetadata = {
  frames: {
    walk_02: { frame: { x: 16, y: 0, w: 16, h: 16 } },
    walk_01: { frame: { x: 0, y: 0, w: 16, h: 16 } },
    walk_03: { frame: { x: 32, y: 0, w: 16, h: 16 } }
  }
};

const tempPath = path.join(process.cwd(), 'tmp_animated_sprite_metadata.json');
fs.writeFileSync(tempPath, JSON.stringify(sampleMetadata, null, 2), 'utf8');

try {
  const loaded = JSON.parse(fs.readFileSync(tempPath, 'utf8'));
  const frames = buildFrameList(loaded);

  if (frames.length !== 3) {
    throw new Error(`Expected 3 frames, got ${frames.length}`);
  }

  if (frames[0].x !== 0 || frames[1].x !== 16 || frames[2].x !== 32) {
    throw new Error(`Frame ordering failed: ${JSON.stringify(frames)}`);
  }

  console.log('animated sprite metadata import logic OK');
} finally {
  fs.unlinkSync(tempPath);
}
