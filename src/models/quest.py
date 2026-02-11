"""Quest and lore progression for Hollowed Stars.

PLAN.md true ending path:
1. Defeat a federation fleet → get Class 4 ID Code
2. Travel to Earth → defeat ancient defense fleet → unlock Signal of Dawn
3. Signal of Dawn has Class 1 ID Code → reach the gateway
4. Enter the gateway → fight Ninurta (the sleeping eldritch god)
5. Cross through to Andromeda → true ending

Other endings:
- Colony success: establish enough colonies
- Fleet destroyed: all ships lost
- Colonist collapse: colonists < 15,000
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class QuestFlag(enum.Enum):
    """Major quest progression flags."""

    # Federation encounters
    DEFEATED_FEDERATION_FLEET = "defeated_federation_fleet"
    CLASS_4_ID_CODE = "class_4_id_code"

    # Earth questline
    DISCOVERED_EARTH = "discovered_earth"
    DEFEATED_EARTH_DEFENSE = "defeated_earth_defense"
    UNLOCKED_SIGNAL_OF_DAWN = "unlocked_signal_of_dawn"
    CLASS_1_ID_CODE = "class_1_id_code"

    # Gateway & true ending
    REACHED_GATEWAY = "reached_gateway"
    DEFEATED_NINURTA = "defeated_ninurta"
    CROSSED_TO_ANDROMEDA = "crossed_to_andromeda"

    # Lore fragments
    LORE_FRAGMENT_1 = "lore_old_federation"
    LORE_FRAGMENT_2 = "lore_prison_station"
    LORE_FRAGMENT_3 = "lore_gateway_project"
    LORE_FRAGMENT_4 = "lore_ninurta_origin"
    LORE_FRAGMENT_5 = "lore_exiles"


class EndingType(enum.Enum):
    """Possible game endings."""

    COLONY_SUCCESS = "colony_success"        # Established civilization
    FLEET_DESTROYED = "fleet_destroyed"      # All ships lost
    COLONIST_COLLAPSE = "colonist_collapse"  # Below 15,000 colonists
    TRUE_ENDING = "true_ending"              # Defeated Ninurta, crossed gateway


@dataclass
class LoreEntry:
    """A piece of discovered lore."""

    title: str
    text: str
    quest_flag: QuestFlag


@dataclass
class QuestState:
    """Tracks quest progression and discovered lore."""

    flags: set[QuestFlag] = field(default_factory=set)
    lore_entries: list[LoreEntry] = field(default_factory=list)
    colonies_established: int = 0

    def set_flag(self, flag: QuestFlag) -> None:
        self.flags.add(flag)

    def has_flag(self, flag: QuestFlag) -> bool:
        return flag in self.flags

    def add_lore(self, entry: LoreEntry) -> None:
        if entry.quest_flag not in self.flags:
            self.lore_entries.append(entry)
            self.flags.add(entry.quest_flag)

    @property
    def can_reach_earth(self) -> bool:
        return self.has_flag(QuestFlag.CLASS_4_ID_CODE)

    @property
    def can_reach_gateway(self) -> bool:
        return self.has_flag(QuestFlag.CLASS_1_ID_CODE)

    @property
    def has_all_lore(self) -> bool:
        lore_flags = {
            QuestFlag.LORE_FRAGMENT_1, QuestFlag.LORE_FRAGMENT_2,
            QuestFlag.LORE_FRAGMENT_3, QuestFlag.LORE_FRAGMENT_4,
            QuestFlag.LORE_FRAGMENT_5,
        }
        return lore_flags.issubset(self.flags)

    def check_ending(self, colonists: int, fleet_destroyed: bool) -> EndingType | None:
        """Check if any ending condition is met."""
        if self.has_flag(QuestFlag.CROSSED_TO_ANDROMEDA):
            return EndingType.TRUE_ENDING
        if fleet_destroyed:
            return EndingType.FLEET_DESTROYED
        if colonists < 15_000:
            return EndingType.COLONIST_COLLAPSE
        if self.colonies_established >= 3:
            return EndingType.COLONY_SUCCESS
        return None


# ---------------------------------------------------------------------------
# Pre-defined lore entries
# ---------------------------------------------------------------------------

LORE_ENTRIES: dict[QuestFlag, LoreEntry] = {
    QuestFlag.LORE_FRAGMENT_1: LoreEntry(
        "The Old Federation",
        "The Federation of Stars spanned thousands of worlds, united by the gateway "
        "network. Their technology was beyond anything we can replicate. Then, in a "
        "single moment, they were gone. Every station, every ship, every colony — "
        "silenced in an instant.",
        QuestFlag.LORE_FRAGMENT_1,
    ),
    QuestFlag.LORE_FRAGMENT_2: LoreEntry(
        "The Prison Station",
        "3,000 years before the Fall, a group of dissidents were exiled to a station "
        "hidden in the corona of a star. Their crime was so terrible that all records "
        "were purged. Ironically, this prison became humanity's last refuge — the "
        "star shielded them from whatever destroyed everything else.",
        QuestFlag.LORE_FRAGMENT_2,
    ),
    QuestFlag.LORE_FRAGMENT_3: LoreEntry(
        "Project Gateway",
        "The Federation's greatest achievement was to be the Trans-Galactic Gateway — "
        "a device capable of sending ships to the Andromeda galaxy instantaneously. "
        "The first test was scheduled. The gateway was activated. And then something "
        "came through from the other side.",
        QuestFlag.LORE_FRAGMENT_3,
    ),
    QuestFlag.LORE_FRAGMENT_4: LoreEntry(
        "Ninurta",
        "The entity that destroyed the Federation is known only from fragments. "
        "Ancient texts call it Ninurta — a being from beyond our understanding. "
        "It consumed the energy of an entire civilization in one act and then fell "
        "into a deep slumber, exhausted. It sleeps still. If you find it... "
        "you might be able to destroy it while it dreams.",
        QuestFlag.LORE_FRAGMENT_4,
    ),
    QuestFlag.LORE_FRAGMENT_5: LoreEntry(
        "The Exiles' Legacy",
        "We are the descendants of criminals, locked away and forgotten. But our "
        "ancestors survived. They adapted. They built. And when the station could "
        "sustain them no longer, they launched the Mothership — humanity's last "
        "desperate gamble. We carry their hope, their guilt, and their determination.",
        QuestFlag.LORE_FRAGMENT_5,
    ),
}
