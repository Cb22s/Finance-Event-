# Guide character model

Drop a VRM model here named exactly **`mira.vrm`**:

```
frontend/assets/mira.vrm
```

## Where to get one (free, 5 minutes)

**Option A — VRoid Hub** (https://hub.vroid.com)
Filter by "Downloadable". Check the licence allows redistribution/commercial-ish
use — most free models allow use in a non-commercial student project, but READ IT.
Download the `.vrm` and rename to `mira.vrm`.

**Option B — VRoid Studio** (free desktop app)
Build your own character in ~15 minutes, export as VRM. No licence worries at
all because you made it. Best option for a college event.

## Size matters

Keep the file **under ~8 MB**. Event-day wifi is the constraint, not your laptop.
In VRoid Studio, export with texture size 1024 (not 2048) and "reduce materials"
enabled. A 20 MB model on shared conference wifi will take 30+ seconds to appear.

## If the file is absent

Nothing breaks. `mascot3d.js` fails quietly and the hand-drawn 2D character in
`mascot.js` stays on screen. Check the browser console for `[Mira]` messages:

- `[Mira] 3D model loaded.`      → working
- `[Mira] Model not loaded (…)`  → file missing or wrong path
- `[Mira] No WebGL`              → browser/machine can't do 3D; 2D is showing
- `[Mira] Not a VRM file`        → it's a plain .glb, not a VRM export

## Both VRM 0.x and 1.0 work

`VRMUtils.rotateVRM0()` handles the older models that face backwards.
