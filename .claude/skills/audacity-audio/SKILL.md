---
name: audacity-audio
description: Game audio with the audacity MCP server — SFX design from generated tones, seamless loops, noise cleanup, mastering levels, and the export formats and channel counts a game engine actually wants. Use for any sound effect, music, or audio cleanup task.
---

# Game Audio with audacity-mcp

Audacity is a destructive waveform editor. Every effect rewrites the samples,
so the working order matters more than it does in a layer-based tool.

The MCP server talks to Audacity over **`mod-script-pipe`**, a named pipe a
running Audacity creates. Audacity must be **open**, with the module enabled
(Edit > Preferences > Modules > `mod-script-pipe` = Enabled, then restart),
and it must be **Audacity 3.x** — 4.x is not supported. Check with
`get_audacity_info` on the `aseprite` server.

## When to activate

- Creating sound effects or music for a game
- Cleaning up recorded audio
- Preparing audio for import into an engine
- Any task whose output is a `.wav`, `.ogg` or `.mp3`

## Destructive editing changes the workflow

There is no layer stack and no undo history you can rely on across calls.

- **Duplicate the track before an experiment.** A track copy is the only cheap
  way back.
- **Select before you affect.** Almost every effect applies to the current
  selection; with nothing selected the behaviour differs per effect, and
  "it did nothing" and "it did everything" look the same afterwards.
- **Read the state back.** Query track and selection state after an operation
  rather than assuming the selection is where you left it.

## A wrong selection freezes Audacity, not just the command

This is the one failure that costs a session. Audacity refuses a generator or
effect that has nothing to work on by opening a **modal dialog** —
`"Tone" requires one or more tracks to be selected.` — and a modal dialog stops
Audacity servicing `mod-script-pipe` at all. The MCP call never returns, and
every later call times out too. Only a human clicking OK releases it.

So a generator needs **both** a selected track and a selected time region.
Either one alone raises the dialog:

```
track_add_mono
select_tracks   track=0 count=1     # the track
select_region   start=0 end=2       # the time range -- not optional
generate_tone   frequency=440 amplitude=0.5 duration=2.0
```

`select_all` is not a substitute on a fresh track: it selects *audio*, and an
empty track has none, so the generator still sees an empty selection. Once a
track holds audio, `select_all` is fine for effects.

If a call stops returning, assume the dialog rather than a dead pipe, and ask
the user to dismiss it — Audacity's own window is disabled while it is up.

## Making a sound effect from nothing

You rarely need a recording. Generated tones plus effects cover most game SFX.

| Sound | Recipe |
|---|---|
| Laser / zap | Tone sweep (square or saw), pitch envelope down, short fade-out |
| Explosion | White noise, low-pass filter sweeping down, fast attack, long decay |
| Pickup / coin | Two short square-wave tones a fourth or fifth apart, back to back |
| Jump | Rising tone, 100–150 ms, slight pitch bend up |
| Footstep | Noise burst, band-pass around 400–800 Hz, ~50 ms, tiny random pitch shift per copy |
| UI click | Very short click or tone, 20–40 ms, hard fade both ends |
| Hurt / damage | Square tone with downward pitch bend plus a noise layer |

Chiptune-style SFX suit pixel art: square and triangle waves, no reverb, short
envelopes. Reverb on a 16-bit-styled game reads as a mismatch.

## Every sound needs an envelope

The single most common defect in generated SFX is a click at the start or end,
caused by cutting the waveform mid-cycle.

- Fade in over at least 5–10 ms, even on a "hard" attack
- Fade out to true silence at the end
- Trim leading and trailing silence *before* the fades, or the file carries
  latency the engine cannot remove

## Seamless loops

For music and ambience that repeats:

1. Cut at a zero crossing at both ends
2. Make the loop length a whole number of bars if it is musical
3. Crossfade the join, or a discontinuity clicks on every repeat
4. Verify by looping it twice and listening to the seam

Do not pad the file with silence to "fix" a loop — that becomes an audible gap.

## Cleanup order

Order matters because each step feeds the next.

```
1. Trim silence          -> less material for everything after
2. Noise reduction       -> profile from a silent section first
3. EQ / filtering        -> remove rumble below ~80 Hz for most game audio
4. Compression           -> even out dynamics
5. Normalise / limit     -> set the final level, last
```

Normalising before compressing wastes the headroom the compressor needs.

## Levels

| Target | Peak | Why |
|---|---|---|
| SFX | −3 to −6 dBFS | leaves room for several sounds at once without clipping |
| Music | −6 to −9 dBFS | sits under SFX and dialogue |
| Voice | −3 dBFS after compression | intelligibility over everything else |

A game mixes many sources at runtime. Mastering each one to −0.1 dBFS
guarantees clipping the moment two play together.

## Export for a game engine

| Format | Use for | Why |
|---|---|---|
| **WAV** (16-bit PCM) | short SFX | no decode latency; size is irrelevant at that length |
| **OGG Vorbis** | music, long ambience | small, and Godot loops it natively |
| **MP3** | avoid | gapless looping is unreliable; decode latency |

**Channels matter more than people expect.** A positional sound must be
**mono** — a stereo file played through a 2D/3D positional node either ignores
the panning or collapses to the centre. Stereo is for music and UI only.

Sample rate: 44100 Hz throughout. Mixing rates in one project forces the engine
to resample at runtime.

Export straight into the Godot project (`game/assets/audio/`), then call
`import_project_assets` on `godot-mcp`.

## Anti-patterns

| Don't | Do |
|---|---|
| Apply an effect with nothing selected | Select the range first — a bad selection opens a modal that freezes the pipe |
| `select_all` before generating on a new track | `select_tracks` + `select_region`; an empty track has no audio to select |
| Experiment on the only copy of a track | Duplicate first — editing is destructive |
| Export SFX in stereo | Mono for anything positional |
| Normalise to −0.1 dBFS | −3 to −6 for SFX; leave mixing headroom |
| Pad a loop with silence | Cut at zero crossings and crossfade the seam |
| Reverb on chiptune-style SFX | Short envelopes, no tail |
| MP3 for looping music | OGG Vorbis |
| Compress after normalising | Normalise last |
