from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path


@dataclass(frozen=True)
class KenneyAssetManifest:
    tile_size: int
    margin: int
    characters_path: Path
    tiles_path: Path
    emotes_path: Path
    emotes_xml_path: Path


def load_kenney_manifest() -> KenneyAssetManifest:
    root = files("agent_town").joinpath("assets", "kenney")
    return KenneyAssetManifest(
        tile_size=16,
        margin=1,
        characters_path=Path(str(root.joinpath("characters.png"))),
        tiles_path=Path(str(root.joinpath("rpg_tiles.png"))),
        emotes_path=Path(str(root.joinpath("emotes.png"))),
        emotes_xml_path=Path(str(root.joinpath("emotes.xml"))),
    )


# Civilization sprite set (authored for the civilization viewer, milestone I3). 25px base
# tiles plus larger prop/building sprites anchored bottom-centre on a tile.
CIVILIZATION_TILE_SIZE = 25

CIVILIZATION_SPRITE_FILES = {
    # terrain (one tile each)
    "grass": "tile_grass.png",
    "dirt": "tile_dirt.png",
    "pavement": "tile_pavement.png",
    # scenery / props
    "tree": "tree.png",
    "tree2": "tree2.png",
    "wall": "wall.png",
    "gate": "gate.png",
    "crate": "crate.png",
    "barrel": "barel.png",
    # buildings (stand-ins until per-kind art lands)
    "house": "house.png",
    "house2": "house2.png",
    "house3": "house3.png",
}

# Pawn sprites (``pawn_*.png``) are discovered by glob rather than listed here,
# so the set scales without manifest churn. They are the CC0 "Tiny Characters
# Set" by Fleurman (based on GrafxKid), sliced from All.png.
CIVILIZATION_PAWN_GLOB = "pawn_*.png"


@dataclass(frozen=True)
class CivilizationAssetManifest:
    tile_size: int
    directory: Path
    sprite_files: dict[str, str]

    def path(self, name: str) -> Path:
        return self.directory.joinpath(self.sprite_files[name])


def load_civilization_manifest() -> CivilizationAssetManifest:
    root = files("agent_town").joinpath("assets", "colony")
    return CivilizationAssetManifest(
        tile_size=CIVILIZATION_TILE_SIZE,
        directory=Path(str(root)),
        sprite_files=dict(CIVILIZATION_SPRITE_FILES),
    )
