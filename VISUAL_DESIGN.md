# Local Agent Town - Visual Design

**Last reviewed:** 2026-06-27
**Status:** active
**Design stance:** Age of Empires-first settlement readability with RimWorld simulation clarity

This project should stop behaving like a dark workbench with game pieces on top. The visual baseline is now built around the Kenney assets in `src\agent_town\assets\kenney` and the kind of top-down readability that makes RimWorld and Age of Empires easy to scan for hours.

## North Star

Local Agent Town starts as a small RTS-readable colony simulation, not a decorative life-sim scene.

The first playable feeling should be:

- **Age of Empires settlement shape:** outdoor village planning, roads, farms, resource patches, water, trees, stone plazas, and roofed building silhouettes should define the first impression.
- **RimWorld clarity:** agent intent, needs, jobs, rooms, routes, and incidents are readable at a glance.
- **RimWorld interior flavor:** visible room logic, stockpiles, work zones, and agent state should support the simulation without making the whole game feel like a flat room blueprint.
- **Future cozy layer:** personality, home decoration, gardening, gifting, and seasonal tone can arrive later, but they should sit on top of strong simulation readability.

If a visual choice does not help the player understand who is doing what, where pressure is building, or what changed recently, it is secondary.

## Asset Foundation

Runtime assets are the selected Kenney sprite sheets:

| Runtime file | Source zip | Source entry | Use |
|---|---|---|---|
| `characters.png` | `kenney_roguelike-characters.zip` | `Spritesheet/roguelikeChar_transparent.png` | agent bodies |
| `rpg_tiles.png` | `kenney_roguelike-rpg-pack.zip` | `Spritesheet/roguelikeSheet_transparent.png` | places, terrain, structures, props |
| `emotes.png` | `kenney_emotes-pack.zip` | `Spritesheets/pixel_style1.png` | thought and activity bubbles |
| `emotes.xml` | `kenney_emotes-pack.zip` | `Spritesheets/pixel_style1.xml` | emote atlas coordinates |

Rules:

- Keep the root Kenney zip files as source assets.
- Use `scripts\prepare-kenney-assets.ps1` to verify or prepare the canonical runtime files.
- Do not hand-pick colors before checking whether the Kenney sheets already solve the visual need.
- Prefer sprites, tile composition, outlines, and spatial grouping over ornamental panels.
- Keep licensing notes near the assets. These packs are CC0, but crediting Kenney is still good practice.

## External Asset Sourcing

Do not spend project time hand-building art when a suitable free asset already exists.

Default workflow:

- Search for a free, game-ready asset first.
- Prefer CC0 or public domain sources. Use CC-BY only when attribution is practical and recorded next to the asset.
- Confirm the source URL, license, author, and whether commercial use and modification are allowed before import.
- Keep the original download untouched, then generate any runtime crops, sheets, or resized files from that source.
- Avoid non-commercial, unclear, share-alike, or franchise-derived assets unless the user explicitly approves the tradeoff.

Style filter:

- Medieval fantasy settlement first: timber, stone, thatch, carts, wells, market stalls, farms, roads, walls, towers, workshops, and readable village silhouettes.
- Use classic fantasy adventure games as taste references, but do not copy protected franchise assets.
- If unsure, choose Age of Empires-style RTS readability over painterly decoration.

Starter sources:

| Source | Use first for | License notes |
|---|---|---|
| `https://opengameart.org/content/isometric-medieval-buildings` | isometric fantasy buildings | listed as CC0 |
| `https://opengameart.org/content/cc0-isometric` | broad isometric asset search | collection is CC0-oriented, but verify each item |
| `https://opengameart.org/content/isometric-medieval-city-sim-assets` | city-sim buildings, citizens, sounds | listed as CC-BY 3.0; attribution required |
| `https://screamingbrainstudios.com/downloads/` | CC0/Public Domain free game assets and tools | site states packs are CC0/Public Domain |
| `https://www.summerengine.com/asset-store/pack/isometric-medieval-town` | isometric medieval town tiles | page describes the pack as Free CC0 |

## Screen Priorities

The first screen is the game. No landing page, dashboard, or marketing shell.

Priority order:

1. **Map:** terrain, rooms, buildings, paths, resources, and danger or attention areas.
2. **Agents:** identity, current task, destination, need pressure, conversation state, and selected route.
3. **Events:** recent incidents, social moments, failed needs, queued suggestions, and local model state.
4. **Commands:** suggestion input, selection cycling, pause, speed, and later build or assign tools.

The map should own most of the window. Panels exist to explain the simulation, not to become the main visual object.

## Map Language

The town should read like a functional settlement:

- Use tile-aligned placement even if the simulation stores free positions.
- Make paths and doorways obvious so movement feels intentional.
- Group locations into readable zones: homes, work, food, social, knowledge, quiet/recovery.
- Reserve strong contrast for interactable objects, selected agents, warnings, and recent events.
- Avoid large flat empty regions; empty space should imply fields, roads, yards, water, storage, or future expansion.
- Add visible boundaries for rooms, farms, stockpiles, workshops, and common areas before adding decorative detail.

The visual promise is "I can understand this little society from above."

## Agent Readability

Agents are the game.

Each agent needs:

- a distinct body sprite or tint;
- a compact nameplate only when useful at current zoom;
- a selected outline and destination line;
- a short-lived emote or thought bubble for state changes;
- visible job/activity feedback when idle, hungry, tired, social, studying, working, or moving.

Do not let labels and bubbles cover each other. At zoomed-out views, reduce text first and keep selection, direction, and alert markers.

## UI Layer

Use a restrained simulation HUD:

- **Top pawn roster:** compact colonist cards with portrait, name, mood dot, and
  selected border so the operator can scan the colony like a RimWorld pawn bar.
- **Right inspection panel:** selected pawn, task, status, needs, skills, traits,
  and later memories, relationships, suggestions, and local model detail.
- **Bottom event strip:** recent incidents and social events, compact and timestamped.
- **Top-left sim controls:** pause, speed, tick/day, population, and later storage or food counts.
- **Future minimap:** useful only after the world is larger than one screen.
- **Future tool belt:** build, assign, zone, inspect, and priority tools with icon-first controls.

Panel styling should stay flat and low-contrast. The sprites and map state should carry the mood.

The current build-1 viewer uses a pawn-sheet layout: top roster, right-side
status/needs/skills/traits sheet, and bottom command/status strip. Future UI
work should extend those surfaces with real controls and event history rather
than returning to a plain text inspector.

## Color Use

Do not maintain a broad custom color palette. Use colors for function:

- **Selection:** one consistent outline color.
- **Warning:** hunger, exhaustion, blocked path, failed work, or social conflict.
- **Positive state:** recovered need, successful task, useful conversation, completed work.
- **Muted text:** historical or secondary details.

Everything else should come from the Kenney assets, tile composition, lighting, and contrast.

## Near-Term Visual Work

The next useful design upgrades are:

1. Build a small tile legend from `rpg_tiles.png` for terrain, walls, floors, homes, food, work, knowledge, and social spaces.
2. Replace circular place markers with tile clusters that look like actual rooms or landmarks.
3. Add route and selection feedback that stays readable at multiple zoom levels.
4. Add a compact event strip so social and need changes do not vanish into the inspector.
5. Give each agent a stable silhouette, home, job site, and routine path so the world feels authored before it becomes larger.

Do these before adding richer cozy decoration. A pretty settlement with unclear jobs is weaker than a plain settlement where every agent's intent is legible.
