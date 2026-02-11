"""Event system for Hollowed Stars.

PLAN.md: Surveying objects triggers events with choices and outcomes.
Events can yield equipment, blueprints, materials, lore, or combat.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field


class EventOutcomeType(enum.Enum):
    """What happens as a result of an event choice."""

    GAIN_RESOURCES = "gain_resources"
    LOSE_RESOURCES = "lose_resources"
    GAIN_COLONISTS = "gain_colonists"
    LOSE_COLONISTS = "lose_colonists"
    COMBAT = "combat"
    GAIN_LORE = "gain_lore"
    NOTHING = "nothing"
    HULL_DAMAGE = "hull_damage"
    HULL_REPAIR = "hull_repair"
    QUEST_FLAG = "quest_flag"


@dataclass
class EventOutcome:
    """Result of choosing an event option."""

    outcome_type: EventOutcomeType
    description: str
    metal: int = 0
    energy: int = 0
    rare: int = 0
    colonists: int = 0
    hull_change: int = 0
    lore_text: str = ""
    quest_flag: str = ""
    combat_danger: int = 0
    combat_is_federation: bool = False


@dataclass
class EventChoice:
    """A choice the player can make during an event."""

    text: str
    outcome: EventOutcome
    success_chance: float = 1.0  # 0.0–1.0, for risky choices


@dataclass
class Event:
    """A narrative event triggered by exploration."""

    title: str
    description: str
    choices: list[EventChoice] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Event pools
# ---------------------------------------------------------------------------

def _derelict_events() -> list[Event]:
    """Events triggered when surveying derelicts."""
    return [
        Event(
            title="Silent Hulk",
            description=(
                "Your probe enters the derelict and finds the corridors dark and silent. "
                "Emergency power flickers in some sections. There are signs of a hasty evacuation."
            ),
            choices=[
                EventChoice(
                    "Send a salvage team",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "Your team strips useful materials from the wreck.",
                        metal=300, energy=150, rare=30,
                    ),
                ),
                EventChoice(
                    "Search the computer core",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "Fragmented logs reveal coordinates of a nearby supply cache.",
                        lore_text="Log Entry 7741: Supply depot at sector 7-G still operational.",
                        metal=100, energy=50,
                    ),
                    success_chance=0.7,
                ),
                EventChoice(
                    "Leave it alone",
                    EventOutcome(EventOutcomeType.NOTHING, "You move on."),
                ),
            ],
        ),
        Event(
            title="Not So Dead",
            description=(
                "As your probe scans the wreck, automated defense turrets activate! "
                "The derelict's combat AI is still functional and considers you hostile."
            ),
            choices=[
                EventChoice(
                    "Engage the defenses",
                    EventOutcome(
                        EventOutcomeType.COMBAT,
                        "You move to neutralize the automated defenders.",
                        combat_danger=2,
                        combat_is_federation=True,
                    ),
                ),
                EventChoice(
                    "Retreat immediately",
                    EventOutcome(
                        EventOutcomeType.HULL_DAMAGE,
                        "You pull back, but not before taking some fire.",
                        hull_change=-200,
                    ),
                ),
                EventChoice(
                    "Try to override the AI",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "Your hackers manage to shut down the AI and claim everything.",
                        metal=500, energy=300, rare=80,
                    ),
                    success_chance=0.4,
                ),
            ],
        ),
        Event(
            title="Survivors",
            description=(
                "Incredibly, you detect life signs. A small group of humans in cryo-sleep, "
                "preserved for thousands of years. Their pods are failing."
            ),
            choices=[
                EventChoice(
                    "Rescue the survivors",
                    EventOutcome(
                        EventOutcomeType.GAIN_COLONISTS,
                        "You save 2,000 souls from certain death. They are grateful beyond words.",
                        colonists=2000,
                    ),
                ),
                EventChoice(
                    "Salvage the cryo-tech instead",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "The advanced cryo-components will be useful... if you can live with the choice.",
                        rare=120,
                    ),
                ),
            ],
        ),
    ]


def _anomaly_events() -> list[Event]:
    """Events triggered when surveying anomalies."""
    return [
        Event(
            title="Spatial Tear",
            description=(
                "A rift in space-time shimmers before your fleet. "
                "Exotic particles stream from the opening, and your sensors detect "
                "incredible energy readings from within."
            ),
            choices=[
                EventChoice(
                    "Send a probe through",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "The probe returns with samples of exotic matter!",
                        rare=200, energy=500,
                    ),
                    success_chance=0.6,
                ),
                EventChoice(
                    "Study from a safe distance",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "Your scientists learn much about space-time mechanics.",
                        lore_text="The rift's energy signature matches old federation gateway technology.",
                        energy=100,
                    ),
                ),
                EventChoice(
                    "Avoid it entirely",
                    EventOutcome(EventOutcomeType.NOTHING, "Some mysteries are best left alone."),
                ),
            ],
        ),
        Event(
            title="The Whisper",
            description=(
                "Your comms array picks up a repeating signal. It's not any known language, "
                "but your AI translation matrix detects patterns. Something is trying to communicate."
            ),
            choices=[
                EventChoice(
                    "Respond to the signal",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "The signal leads to coordinates — ancient data about the old federation's fall.",
                        lore_text="They opened the door. Something came through. It was hungry.",
                    ),
                ),
                EventChoice(
                    "Trace the signal source",
                    EventOutcome(
                        EventOutcomeType.COMBAT,
                        "The signal was a lure. You've been ambushed!",
                        combat_danger=3,
                    ),
                ),
                EventChoice(
                    "Jam the signal and leave",
                    EventOutcome(EventOutcomeType.NOTHING, "Better safe than sorry."),
                ),
            ],
        ),
    ]


def _alien_events() -> list[Event]:
    """Events triggered when interacting with alien outposts."""
    return [
        Event(
            title="First Contact",
            description=(
                "An alien vessel hails you. Their translation is rough but understandable: "
                "'You are the old ones? We thought you dead. We trade? Or you threaten?'"
            ),
            choices=[
                EventChoice(
                    "Propose trade",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "The aliens exchange raw materials for some of your technology.",
                        metal=400, energy=200,
                    ),
                ),
                EventChoice(
                    "Demand tribute",
                    EventOutcome(
                        EventOutcomeType.COMBAT,
                        "The aliens take offense and attack!",
                        combat_danger=2,
                    ),
                ),
                EventChoice(
                    "Share technology peacefully",
                    EventOutcome(
                        EventOutcomeType.GAIN_COLONISTS,
                        "The aliens are overwhelmed by your generosity. Some wish to join your fleet.",
                        colonists=500, metal=200,
                    ),
                    success_chance=0.8,
                ),
            ],
        ),
        Event(
            title="Ambush!",
            description=(
                "What appeared to be a trading post was a trap! Alien warships emerge "
                "from behind the station, weapons hot."
            ),
            choices=[
                EventChoice(
                    "Fight your way out",
                    EventOutcome(
                        EventOutcomeType.COMBAT,
                        "No choice but to engage.",
                        combat_danger=3,
                    ),
                ),
                EventChoice(
                    "Emergency FTL jump",
                    EventOutcome(
                        EventOutcomeType.HULL_DAMAGE,
                        "You take hits as you charge the FTL drive, but escape.",
                        hull_change=-400,
                    ),
                ),
            ],
        ),
    ]


def _planet_events() -> list[Event]:
    """Events triggered when surveying planets."""
    return [
        Event(
            title="Resource Deposit",
            description=(
                "Scans reveal significant mineral deposits on the planet's surface. "
                "Mining would be straightforward but time-consuming."
            ),
            choices=[
                EventChoice(
                    "Deploy mining drones",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "The drones extract valuable minerals.",
                        metal=250, rare=40,
                    ),
                ),
                EventChoice(
                    "Quick surface grab",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "A hasty collection yields some materials.",
                        metal=100,
                    ),
                ),
            ],
        ),
        Event(
            title="Habitable World",
            description=(
                "Against all odds, this world has a breathable atmosphere and liquid water. "
                "It could support a small colony... but is it safe?"
            ),
            choices=[
                EventChoice(
                    "Establish a colony",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "A beacon of hope. You leave behind 10,000 colonists to start anew.",
                        lore_text="Colony established. Humanity endures in more than one place now.",
                        colonists=-10000,
                    ),
                ),
                EventChoice(
                    "Harvest resources only",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "You gather water, organic materials, and rare minerals.",
                        metal=200, energy=300, rare=60,
                    ),
                ),
                EventChoice(
                    "Mark location and continue",
                    EventOutcome(EventOutcomeType.NOTHING, "Perhaps you'll return someday."),
                ),
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Event selection
# ---------------------------------------------------------------------------

_EVENT_POOLS: dict[str, list[Event]] = {
    "derelict": _derelict_events(),
    "station_ruin": _derelict_events(),
    "anomaly": _anomaly_events(),
    "alien_outpost": _alien_events(),
    "planet": _planet_events(),
    "asteroid_field": _planet_events(),
}


def get_event_for_object_type(obj_type_value: str, rng: random.Random | None = None) -> Event | None:
    """Get a random event appropriate for the object type."""
    if rng is None:
        rng = random.Random()

    pool = _EVENT_POOLS.get(obj_type_value, [])
    if not pool:
        return None

    return rng.choice(pool)
