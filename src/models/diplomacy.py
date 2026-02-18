"""Diplomacy system — alien factions, relations, and diplomatic actions.

PLAN.md: Alien civilisations can be communicated with via a diplomacy system.
Interactions with locals may improve or damage relations with the broader
civilisation they belong to.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class FactionDisposition(enum.Enum):
    """Current attitude toward the player."""

    HOSTILE = "hostile"          # Will attack on sight
    WARY = "wary"               # Suspicious, may attack if provoked
    NEUTRAL = "neutral"         # Indifferent
    FRIENDLY = "friendly"       # Willing to trade and cooperate
    ALLIED = "allied"           # Full alliance, mutual defense


class FactionTrait(enum.Enum):
    """Cultural traits that influence faction behaviour."""

    XENOPHOBIC = "xenophobic"       # Distrusts all outsiders
    MILITANT = "militant"           # Favours aggression and expansion
    MERCANTILE = "mercantile"       # Values trade above all
    PEACEFUL = "peaceful"           # Avoids conflict when possible
    RELIGIOUS = "religious"         # Views precursors with awe or fear
    ISOLATIONIST = "isolationist"   # Prefers to be left alone


class DiplomacyAction(enum.Enum):
    """Actions the player can take during diplomacy."""

    TRADE = "trade"
    DEMAND_TRIBUTE = "demand_tribute"
    SHARE_TECHNOLOGY = "share_technology"
    THREATEN = "threaten"
    OFFER_ALLIANCE = "offer_alliance"
    REQUEST_PASSAGE = "request_passage"


# ---------------------------------------------------------------------------
# Relation thresholds → disposition
# ---------------------------------------------------------------------------

_DISPOSITION_THRESHOLDS: list[tuple[int, FactionDisposition]] = [
    (-60, FactionDisposition.HOSTILE),
    (-20, FactionDisposition.WARY),
    (20, FactionDisposition.NEUTRAL),
    (60, FactionDisposition.FRIENDLY),
    (100, FactionDisposition.ALLIED),
]


def _relation_to_disposition(relation: int) -> FactionDisposition:
    """Convert a numeric relation (-100..+100) to a disposition."""
    for threshold, disposition in _DISPOSITION_THRESHOLDS:
        if relation <= threshold:
            return disposition
    return FactionDisposition.ALLIED


# ---------------------------------------------------------------------------
# Faction
# ---------------------------------------------------------------------------

@dataclass
class Faction:
    """An alien civilisation the player can interact with."""

    id: str
    name: str
    species_name: str
    description: str
    traits: list[FactionTrait] = field(default_factory=list)
    relation: int = 0        # -100 (hostile) to +100 (allied)
    tech_level: int = 2      # 1–5 relative to player (player is ~5)
    known: bool = False       # Discovered through exploration
    systems_owned: list[int] = field(default_factory=list)  # StarSystem IDs

    @property
    def disposition(self) -> FactionDisposition:
        return _relation_to_disposition(self.relation)

    def adjust_relation(self, delta: int) -> None:
        """Change relation, clamped to [-100, +100]."""
        self.relation = max(-100, min(100, self.relation + delta))


# ---------------------------------------------------------------------------
# Diplomacy resolution
# ---------------------------------------------------------------------------

@dataclass
class DiplomacyResult:
    """Outcome of a diplomatic action."""

    success: bool
    description: str
    relation_change: int = 0
    metal_gained: int = 0
    energy_gained: int = 0
    rare_gained: int = 0
    colonists_gained: int = 0
    triggers_combat: bool = False


def resolve_diplomacy_action(
    action: DiplomacyAction,
    faction: Faction,
    rng: random.Random | None = None,
) -> DiplomacyResult:
    """Resolve a player's diplomatic action against a faction."""
    if rng is None:
        rng = random.Random()

    disp = faction.disposition
    is_mercantile = FactionTrait.MERCANTILE in faction.traits
    is_militant = FactionTrait.MILITANT in faction.traits
    is_xenophobic = FactionTrait.XENOPHOBIC in faction.traits
    is_religious = FactionTrait.RELIGIOUS in faction.traits
    is_peaceful = FactionTrait.PEACEFUL in faction.traits

    if action == DiplomacyAction.TRADE:
        # Mercantile factions love trade; hostile factions refuse
        if disp == FactionDisposition.HOSTILE:
            return DiplomacyResult(
                False,
                f"The {faction.species_name} refuse all contact. "
                f"Their comm channels crackle with threats.",
                relation_change=-5,
            )
        bonus = 1.5 if is_mercantile else 1.0
        metal = int(rng.randint(150, 400) * bonus)
        energy = int(rng.randint(100, 300) * bonus)
        return DiplomacyResult(
            True,
            f"The {faction.species_name} are willing to trade. "
            f"Their merchants exchange alien-manufactured goods for "
            f"samples of your ancient technology.",
            relation_change=10 if is_mercantile else 5,
            metal_gained=metal,
            energy_gained=energy,
        )

    elif action == DiplomacyAction.SHARE_TECHNOLOGY:
        if disp in (FactionDisposition.HOSTILE, FactionDisposition.WARY):
            return DiplomacyResult(
                False,
                f"The {faction.species_name} are too distrustful to accept "
                f"your offer. They suspect a trap.",
                relation_change=5,  # Slight warming even on failure
            )
        rel_boost = 25 if is_religious else 15
        rare = rng.randint(50, 150)
        return DiplomacyResult(
            True,
            f"The {faction.species_name} are awed by the precursor knowledge "
            f"you share. Their scientists study your data with reverence. "
            f"In return, they offer rare materials from their homeworld.",
            relation_change=rel_boost,
            rare_gained=rare,
        )

    elif action == DiplomacyAction.DEMAND_TRIBUTE:
        # Works better with high relation or militant weakness
        if disp in (FactionDisposition.FRIENDLY, FactionDisposition.ALLIED):
            metal = rng.randint(300, 600)
            energy = rng.randint(200, 400)
            return DiplomacyResult(
                True,
                f"The {faction.species_name} comply with your demands, "
                f"though resentment simmers beneath the surface.",
                relation_change=-15,
                metal_gained=metal,
                energy_gained=energy,
            )
        elif is_militant or is_xenophobic:
            return DiplomacyResult(
                False,
                f"The {faction.species_name} interpret your demand as an "
                f"act of war. Their fleet powers up weapons.",
                relation_change=-30,
                triggers_combat=True,
            )
        else:
            return DiplomacyResult(
                False,
                f"The {faction.species_name} reject your demand with cold "
                f"formality. Diplomatic channels remain open, barely.",
                relation_change=-20,
            )

    elif action == DiplomacyAction.THREATEN:
        if is_peaceful:
            return DiplomacyResult(
                True,
                f"The {faction.species_name} cower before your ancient "
                f"warships. They offer tribute to avoid destruction.",
                relation_change=-25,
                metal_gained=rng.randint(200, 500),
                energy_gained=rng.randint(100, 300),
            )
        elif is_militant:
            return DiplomacyResult(
                False,
                f"The {faction.species_name} meet your threats with their "
                f"own. A fleet of alien warships emerges from behind "
                f"the station.",
                relation_change=-35,
                triggers_combat=True,
            )
        else:
            return DiplomacyResult(
                False,
                f"The {faction.species_name} are unimpressed by your posturing. "
                f"Relations have deteriorated.",
                relation_change=-15,
            )

    elif action == DiplomacyAction.OFFER_ALLIANCE:
        if disp == FactionDisposition.FRIENDLY:
            return DiplomacyResult(
                True,
                f"The {faction.species_name} accept your alliance with "
                f"great ceremony. Your fleets are now bound together against "
                f"the darkness of this dead galaxy.",
                relation_change=30,
            )
        elif disp == FactionDisposition.ALLIED:
            return DiplomacyResult(
                True,
                f"Your alliance with the {faction.species_name} is already "
                f"strong. They reaffirm their commitment.",
                relation_change=5,
            )
        else:
            return DiplomacyResult(
                False,
                f"The {faction.species_name} are not yet ready for such a "
                f"commitment. Build trust through trade and cooperation first.",
                relation_change=0,
            )

    elif action == DiplomacyAction.REQUEST_PASSAGE:
        if disp in (FactionDisposition.HOSTILE,):
            return DiplomacyResult(
                False,
                f"The {faction.species_name} deny you passage through their "
                f"territory. Their patrol ships shadow your fleet menacingly.",
                relation_change=-5,
            )
        else:
            return DiplomacyResult(
                True,
                f"The {faction.species_name} grant you safe passage through "
                f"their territory. Their navigators transmit approved "
                f"transit corridors.",
                relation_change=3,
            )

    # Fallback
    return DiplomacyResult(False, "Nothing happens.", 0)


# ---------------------------------------------------------------------------
# Faction generation
# ---------------------------------------------------------------------------

_FACTION_NAMES = [
    ("Vek'tai Dominion", "Vek'tai", "A warrior caste empire that conquered their home system through "
     "sheer martial prowess. They respect strength above all else."),
    ("Luminari Compact", "Luminari", "Bioluminescent beings who communicate through patterns of light. "
     "They are deeply spiritual and view the precursors as divine."),
    ("Grath Collective", "Grath", "An insectoid hive-mind that has spread across several systems. "
     "They value efficiency and see your technology as the ultimate resource."),
    ("Solari Trading Houses", "Solari", "A mercantile confederation of avian traders. They have no "
     "homeworld — their vast trading fleets are their civilisation."),
    ("Kethrani Imperium", "Kethrani", "A militant empire ruled by genetically engineered nobles. "
     "They view aliens with suspicion and expand aggressively."),
    ("Thal'nok Assembly", "Thal'nok", "Silicon-based beings who process information communally. "
     "They are methodical, patient, and intensely curious about precursor ruins."),
    ("Drenn Wanderers", "Drenn", "Nomadic spacefaring molluscs who drift between stars in great "
     "bio-organic arks. They trade freely but commit to nothing."),
    ("Ashkari Theocracy", "Ashkari", "Reptilian beings governed by a priestly caste. They believe "
     "the old federation's fall was divine punishment."),
    ("Nexari Federation", "Nexari", "A multi-species alliance modelled, unknowingly, on the old "
     "federation. They seek unity among the galaxy's peoples."),
    ("Voidborn Enclave", "Voidborn", "Beings adapted to life in deep space, rarely setting foot on "
     "worlds. Isolationist and mysterious."),
]

_TRAIT_SETS: list[list[FactionTrait]] = [
    [FactionTrait.MILITANT, FactionTrait.XENOPHOBIC],
    [FactionTrait.RELIGIOUS, FactionTrait.PEACEFUL],
    [FactionTrait.MERCANTILE],
    [FactionTrait.MERCANTILE, FactionTrait.PEACEFUL],
    [FactionTrait.MILITANT, FactionTrait.XENOPHOBIC],
    [FactionTrait.PEACEFUL, FactionTrait.ISOLATIONIST],
    [FactionTrait.MERCANTILE, FactionTrait.ISOLATIONIST],
    [FactionTrait.RELIGIOUS, FactionTrait.XENOPHOBIC],
    [FactionTrait.PEACEFUL, FactionTrait.MERCANTILE],
    [FactionTrait.ISOLATIONIST],
]


def generate_factions(
    num_factions: int = 6,
    rng: random.Random | None = None,
) -> list[Faction]:
    """Generate a set of alien factions for the galaxy."""
    if rng is None:
        rng = random.Random()

    num_factions = min(num_factions, len(_FACTION_NAMES))
    selected = rng.sample(range(len(_FACTION_NAMES)), num_factions)

    factions: list[Faction] = []
    for i, idx in enumerate(selected):
        name, species, description = _FACTION_NAMES[idx]
        traits = _TRAIT_SETS[idx]

        # Starting relation based on traits
        base_relation = 0
        if FactionTrait.PEACEFUL in traits or FactionTrait.MERCANTILE in traits:
            base_relation = rng.randint(5, 20)
        elif FactionTrait.XENOPHOBIC in traits or FactionTrait.MILITANT in traits:
            base_relation = rng.randint(-30, -10)
        elif FactionTrait.ISOLATIONIST in traits:
            base_relation = rng.randint(-10, 5)
        elif FactionTrait.RELIGIOUS in traits:
            base_relation = rng.randint(0, 15)

        factions.append(Faction(
            id=f"faction_{i}",
            name=name,
            species_name=species,
            description=description,
            traits=traits,
            relation=base_relation,
            tech_level=rng.randint(1, 4),
        ))

    return factions
