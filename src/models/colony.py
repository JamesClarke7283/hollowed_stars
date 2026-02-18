"""Colony management system for Hollowed Stars.

PLAN.md: Colonisation requires terraforming a world over the course of an
entire game — the player must return repeatedly to invest resources and
advance through stages before a colony is established.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class ColonyStage(enum.Enum):
    """Progressive stages of colony development."""

    SURVEYED = "surveyed"           # Planet flagged as potential colony site
    LANDING = "landing"             # Initial landing party deployed
    INFRASTRUCTURE = "infrastructure"  # Building foundational structures
    TERRAFORMING = "terraforming"   # Atmospheric/environmental modification
    ESTABLISHED = "established"     # Self-sustaining colony


# Resources required *per advancement* (current_stage → next_stage)
_STAGE_COSTS: dict[ColonyStage, dict[str, int]] = {
    ColonyStage.SURVEYED: {
        "metal": 1500, "energy": 800, "colonists": 20_000,
    },
    ColonyStage.LANDING: {
        "metal": 3000, "energy": 2000, "colonists": 50_000,
    },
    ColonyStage.INFRASTRUCTURE: {
        "metal": 5000, "energy": 3500, "colonists": 80_000,
    },
    ColonyStage.TERRAFORMING: {
        "metal": 3000, "energy": 2500, "colonists": 50_000,
    },
}

_STAGE_ORDER = [
    ColonyStage.SURVEYED,
    ColonyStage.LANDING,
    ColonyStage.INFRASTRUCTURE,
    ColonyStage.TERRAFORMING,
    ColonyStage.ESTABLISHED,
]

_STAGE_DESCRIPTIONS: dict[ColonyStage, str] = {
    ColonyStage.SURVEYED: (
        "Deep survey complete. The landing zone has been identified and "
        "geological samples confirm viability. A forward team must be "
        "deployed to begin the arduous work of carving a foothold."
    ),
    ColonyStage.LANDING: (
        "The first prefab shelters dot the surface like metal seeds. "
        "Life support is jury-rigged and the team is surviving but not "
        "thriving. Infrastructure must be built before the colony can "
        "grow beyond a desperate campsite."
    ),
    ColonyStage.INFRASTRUCTURE: (
        "Power grids hum beneath freshly poured foundations. Water "
        "treatment, hydroponics bays, and ore refineries are taking shape. "
        "The colony is functional but the planet's atmosphere remains "
        "hostile. Terraforming must begin to make this world truly liveable."
    ),
    ColonyStage.TERRAFORMING: (
        "Atmospheric processors churn day and night, belching engineered "
        "gases into the thin sky. The temperature is rising, ice is melting, "
        "and the first clouds have begun to form. One final push of "
        "resources will see this world bloom."
    ),
    ColonyStage.ESTABLISHED: (
        "Against all odds, life finds a way. Fields of engineered crops "
        "stretch to the horizon under an alien sun. Children born on this "
        "world will never know the cold of space. Humanity endures."
    ),
}


@dataclass
class Colony:
    """A player colony under development on a planet."""

    colony_id: str              # Unique identifier
    system_id: int              # StarSystem containing this colony
    planet_name: str            # Name of the planet
    stage: ColonyStage = ColonyStage.SURVEYED
    total_invested_metal: int = 0
    total_invested_energy: int = 0
    total_invested_colonists: int = 0
    turn_founded: int = 0

    @property
    def stage_index(self) -> int:
        return _STAGE_ORDER.index(self.stage)

    @property
    def is_established(self) -> bool:
        return self.stage == ColonyStage.ESTABLISHED

    @property
    def description(self) -> str:
        return _STAGE_DESCRIPTIONS.get(self.stage, "")

    @property
    def next_stage(self) -> ColonyStage | None:
        idx = self.stage_index
        if idx + 1 < len(_STAGE_ORDER):
            return _STAGE_ORDER[idx + 1]
        return None

    @property
    def advancement_cost(self) -> dict[str, int] | None:
        """Resources needed to advance to the next stage."""
        if self.stage in _STAGE_COSTS:
            return dict(_STAGE_COSTS[self.stage])
        return None  # Already established

    def can_advance(self, metal: int, energy: int, colonists: int) -> bool:
        """Check if the player has enough resources to advance."""
        cost = self.advancement_cost
        if cost is None:
            return False
        return (
            metal >= cost["metal"]
            and energy >= cost["energy"]
            and colonists >= cost["colonists"]
        )

    def advance(self) -> str:
        """Advance to the next stage. Returns a narrative description."""
        nxt = self.next_stage
        if nxt is None:
            return "This colony is already fully established."
        cost = self.advancement_cost
        if cost:
            self.total_invested_metal += cost["metal"]
            self.total_invested_energy += cost["energy"]
            self.total_invested_colonists += cost["colonists"]
        self.stage = nxt
        return _STAGE_DESCRIPTIONS.get(nxt, "The colony advances.")

    def to_dict(self) -> dict:
        """Serialise for save files."""
        return {
            "colony_id": self.colony_id,
            "system_id": self.system_id,
            "planet_name": self.planet_name,
            "stage": self.stage.value,
            "total_invested_metal": self.total_invested_metal,
            "total_invested_energy": self.total_invested_energy,
            "total_invested_colonists": self.total_invested_colonists,
            "turn_founded": self.turn_founded,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Colony":
        """Deserialise from save data."""
        return cls(
            colony_id=data["colony_id"],
            system_id=data["system_id"],
            planet_name=data["planet_name"],
            stage=ColonyStage(data.get("stage", "surveyed")),
            total_invested_metal=data.get("total_invested_metal", 0),
            total_invested_energy=data.get("total_invested_energy", 0),
            total_invested_colonists=data.get("total_invested_colonists", 0),
            turn_founded=data.get("turn_founded", 0),
        )


class ColonyManager:
    """Tracks all active colonies across the galaxy."""

    def __init__(self) -> None:
        self.colonies: list[Colony] = []
        self._next_id: int = 1

    def start_colony(
        self, system_id: int, planet_name: str, turn: int = 0,
    ) -> Colony:
        """Begin a new colony at SURVEYED stage."""
        colony = Colony(
            colony_id=f"colony_{self._next_id}",
            system_id=system_id,
            planet_name=planet_name,
            turn_founded=turn,
        )
        self._next_id += 1
        self.colonies.append(colony)
        return colony

    def get_colony_at(self, system_id: int) -> Colony | None:
        """Get the active colony in a system, if any."""
        for c in self.colonies:
            if c.system_id == system_id:
                return c
        return None

    @property
    def established_count(self) -> int:
        return sum(1 for c in self.colonies if c.is_established)

    @property
    def active_count(self) -> int:
        return len(self.colonies)

    def to_dict_list(self) -> list[dict]:
        """Serialise for save files."""
        return [c.to_dict() for c in self.colonies]

    @classmethod
    def from_dict_list(cls, data: list[dict]) -> "ColonyManager":
        """Deserialise from save data."""
        mgr = cls()
        for d in data:
            mgr.colonies.append(Colony.from_dict(d))
        if mgr.colonies:
            max_id = max(
                int(c.colony_id.split("_")[1]) for c in mgr.colonies
            )
            mgr._next_id = max_id + 1
        return mgr
