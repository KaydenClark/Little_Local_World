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
