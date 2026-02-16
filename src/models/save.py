"""Save / load game state to JSON.

Uses platformdirs for cross-platform save location:
  Linux:   ~/.local/share/hollowed_stars/save.json
  macOS:   ~/Library/Application Support/hollowed_stars/save.json
  Windows: C:/Users/.../AppData/Local/hollowed_stars/save.json

Galaxy is regenerated from seed; only mutable state is persisted.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from platformdirs import user_data_dir

from .galaxy import Galaxy, ObjectType
from .mothership_systems import (
    Component,
    ComponentQuality,
    ShipSystem,
    SystemType,
    create_default_systems,
)
from .quest import LogEntry, LoreEntry, QuestFlag, QuestState
from .ships import (
    Fleet,
    FleetShip,
    Mothership,
    Resources,
    ShipClass,
    WeaponSize,
    WeaponSlot,
)

SAVE_DIR = Path(user_data_dir("hollowed_stars"))
SAVE_FILE = SAVE_DIR / "save.json"


# ── Serialise helpers ─────────────────────────────────────────────────

def _weapon_slot_to_dict(ws: WeaponSlot) -> dict:
    return {"size": ws.size.value, "equipped": ws.equipped}


def _weapon_slot_from_dict(d: dict) -> WeaponSlot:
    return WeaponSlot(size=WeaponSize(d["size"]), equipped=d.get("equipped"))


def _mothership_to_dict(m: Mothership) -> dict:
    return {
        "name": m.name,
        "description": m.description,
        "lore": m.lore,
        "hull": m.hull,
        "max_hull": m.max_hull,
        "armor": m.armor,
        "power": m.power,
        "max_power": m.max_power,
        "speed": m.speed,
        "sensor_range": m.sensor_range,
        "colonist_capacity": m.colonist_capacity,
        "hangar_capacity": m.hangar_capacity,
        "weapon_slots": [_weapon_slot_to_dict(ws) for ws in m.weapon_slots],
        "special_ability": m.special_ability,
        "special_description": m.special_description,
    }


def _mothership_from_dict(d: dict) -> Mothership:
    return Mothership(
        name=d["name"],
        description=d["description"],
        lore=d["lore"],
        hull=d["hull"],
        max_hull=d["max_hull"],
        armor=d["armor"],
        power=d["power"],
        max_power=d["max_power"],
        speed=d["speed"],
        sensor_range=d["sensor_range"],
        colonist_capacity=d["colonist_capacity"],
        hangar_capacity=d["hangar_capacity"],
        weapon_slots=[_weapon_slot_from_dict(ws) for ws in d.get("weapon_slots", [])],
        special_ability=d.get("special_ability", ""),
        special_description=d.get("special_description", ""),
    )


def _fleet_ship_to_dict(fs: FleetShip) -> dict:
    return {
        "name": fs.name,
        "ship_class": fs.ship_class.value,
        "hull": fs.hull,
        "max_hull": fs.max_hull,
        "armor": fs.armor,
        "weapon_slots": [_weapon_slot_to_dict(ws) for ws in fs.weapon_slots],
        "formation_slot": fs.formation_slot,
    }


def _fleet_ship_from_dict(d: dict) -> FleetShip:
    return FleetShip(
        name=d["name"],
        ship_class=ShipClass(d["ship_class"]),
        hull=d["hull"],
        max_hull=d["max_hull"],
        armor=d["armor"],
        weapon_slots=[_weapon_slot_from_dict(ws) for ws in d.get("weapon_slots", [])],
        formation_slot=d.get("formation_slot", 0),
    )


def _fleet_to_dict(f: Fleet) -> dict:
    return {
        "mothership": _mothership_to_dict(f.mothership),
        "ships": [_fleet_ship_to_dict(s) for s in f.ships],
        "resources": {
            "metal": f.resources.metal,
            "energy": f.resources.energy,
            "rare_materials": f.resources.rare_materials,
        },
        "colonists": f.colonists,
        "weapon_inventory": f.weapon_inventory,
    }


def _fleet_from_dict(d: dict) -> Fleet:
    r = d["resources"]
    return Fleet(
        mothership=_mothership_from_dict(d["mothership"]),
        ships=[_fleet_ship_from_dict(s) for s in d["ships"]],
        resources=Resources(
            metal=r["metal"],
            energy=r["energy"],
            rare_materials=r["rare_materials"],
        ),
        colonists=d["colonists"],
        weapon_inventory=d.get("weapon_inventory", []),
    )


# ── Galaxy mutable state ─────────────────────────────────────────────

def _galaxy_mutable(g: Galaxy) -> dict:
    """Save only the mutable parts — seed lets us regenerate topology."""
    visited = [s.id for s in g.systems if s.visited]
    surveyed: list[dict] = []
    for s in g.systems:
        for obj in s.objects:
            if obj.surveyed:
                surveyed.append({"system_id": s.id, "name": obj.name})
    return {
        "seed": g.seed,
        "num_systems": len(g.systems),
        "current_system_id": g.current_system_id,
        "visited": visited,
        "surveyed": surveyed,
    }


def _galaxy_from_dict(d: dict) -> Galaxy:
    g = Galaxy(num_systems=d.get("num_systems", 40), seed=d["seed"])
    g.current_system_id = d["current_system_id"]
    for sid in d.get("visited", []):
        if 0 <= sid < len(g.systems):
            g.systems[sid].visited = True
    for entry in d.get("surveyed", []):
        sid = entry["system_id"]
        if 0 <= sid < len(g.systems):
            for obj in g.systems[sid].objects:
                if obj.name == entry["name"]:
                    obj.surveyed = True
    return g


# ── Ship systems ──────────────────────────────────────────────────────

def _component_to_dict(c: Component) -> dict:
    return {
        "name": c.name,
        "quality": c.quality.value,
        "condition": c.condition,
        "stats_bonus": c.stats_bonus,
    }


def _component_from_dict(d: dict) -> Component:
    return Component(
        name=d["name"],
        quality=ComponentQuality(d["quality"]),
        condition=d.get("condition", 100.0),
        stats_bonus=d.get("stats_bonus", 0.0),
    )


def _system_to_dict(s: ShipSystem) -> dict:
    return {
        "system_type": s.system_type.value,
        "name": s.name,
        "description": s.description,
        "maintenance_level": s.maintenance_level,
        "upgrade_tier": s.upgrade_tier,
        "components": [_component_to_dict(c) for c in s.components],
        "passive_decay_rate": s.passive_decay_rate,
        "ftl_decay_rate": s.ftl_decay_rate,
    }


def _system_from_dict(d: dict) -> ShipSystem:
    return ShipSystem(
        system_type=SystemType(d["system_type"]),
        name=d["name"],
        description=d["description"],
        maintenance_level=d.get("maintenance_level", 100.0),
        upgrade_tier=d.get("upgrade_tier", 1),
        components=[_component_from_dict(c) for c in d.get("components", [])],
        passive_decay_rate=d.get("passive_decay_rate", 0.1),
        ftl_decay_rate=d.get("ftl_decay_rate", 5.0),
    )


# ── Quest state ───────────────────────────────────────────────────────

def _quest_to_dict(qs: QuestState) -> dict:
    return {
        "flags": [f.value for f in qs.flags],
        "lore_entries": [
            {"title": l.title, "text": l.text, "quest_flag": l.quest_flag.value}
            for l in qs.lore_entries
        ],
        "log_entries": [
            {
                "turn": le.turn,
                "title": le.title,
                "text": le.text,
                "category": le.category,
            }
            for le in qs.log_entries
        ],
        "colonies_established": qs.colonies_established,
        "turn": qs.turn,
    }


def _quest_from_dict(d: dict) -> QuestState:
    qs = QuestState()
    for fv in d.get("flags", []):
        try:
            qs.flags.add(QuestFlag(fv))
        except ValueError:
            pass
    for le in d.get("lore_entries", []):
        try:
            qs.lore_entries.append(
                LoreEntry(title=le["title"], text=le["text"], quest_flag=QuestFlag(le["quest_flag"]))
            )
        except (ValueError, KeyError):
            pass
    for le in d.get("log_entries", []):
        qs.log_entries.append(
            LogEntry(turn=le.get("turn", 0), title=le["title"], text=le["text"], category=le.get("category", "event"))
        )
    qs.colonies_established = d.get("colonies_established", 0)
    qs.turn = d.get("turn", 0)
    return qs


# ── Top-level API ─────────────────────────────────────────────────────

def save_game(
    fleet: Fleet,
    galaxy: Galaxy,
    systems: list[ShipSystem],
    quest_state: QuestState,
) -> Path:
    """Serialize full game state to JSON and return the save path."""
    data = {
        "version": 1,
        "fleet": _fleet_to_dict(fleet),
        "galaxy": _galaxy_mutable(galaxy),
        "systems": [_system_to_dict(s) for s in systems],
        "quest": _quest_to_dict(quest_state),
    }
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    SAVE_FILE.write_text(json.dumps(data, indent=2))
    return SAVE_FILE


def load_game() -> tuple[Fleet, Galaxy, list[ShipSystem], QuestState] | None:
    """Deserialize game state from JSON. Returns None if no save exists."""
    if not SAVE_FILE.exists():
        return None
    try:
        data = json.loads(SAVE_FILE.read_text())
    except (json.JSONDecodeError, IOError):
        return None

    fleet = _fleet_from_dict(data["fleet"])
    galaxy = _galaxy_from_dict(data["galaxy"])
    systems = [_system_from_dict(s) for s in data["systems"]]
    quest_state = _quest_from_dict(data["quest"])
    return fleet, galaxy, systems, quest_state


def has_save() -> bool:
    """Check if a save file exists."""
    return SAVE_FILE.exists()


def delete_save() -> None:
    """Remove the save file if it exists."""
    if SAVE_FILE.exists():
        SAVE_FILE.unlink()
