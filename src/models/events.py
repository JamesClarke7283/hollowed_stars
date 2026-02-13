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
# Quest-critical events (triggered by special_tag objects)
# ---------------------------------------------------------------------------

def _earth_events() -> list[Event]:
    """Events triggered when surveying Earth (special_tag='earth')."""
    return [
        Event(
            title="The Dead World",
            description=(
                "Earth. The birthplace of humanity lies below — a wasteland of grey oceans "
                "and dead continents. But in orbit, you detect it: the Signal of Dawn, the "
                "old federation's flagship, still intact after 5,000 years. Its ancient "
                "defense fleet stirs, detecting your approach. Automated weapons power up. "
                "If you want the flagship, you must fight for it."
            ),
            choices=[
                EventChoice(
                    "Engage the Earth defense fleet",
                    EventOutcome(
                        EventOutcomeType.COMBAT,
                        "You commit to the most dangerous battle of your journey.",
                        combat_danger=5,
                        combat_is_federation=True,
                        quest_flag="defeated_earth_defense",
                    ),
                ),
                EventChoice(
                    "Hold position and observe",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "Your sensors gather invaluable data on federation technology.",
                        lore_text=(
                            "The Signal of Dawn — flagship of the old federation. "
                            "Your scans reveal weapon systems beyond comprehension."
                        ),
                        quest_flag="discovered_earth",
                    ),
                ),
                EventChoice(
                    "Retreat — this fight is too dangerous",
                    EventOutcome(
                        EventOutcomeType.NOTHING,
                        "You pull back. Earth will wait.",
                    ),
                ),
            ],
        ),
    ]


def _gateway_events() -> list[Event]:
    """Events triggered when surveying the Gateway (special_tag='gateway')."""
    return [
        Event(
            title="The Trans-Galactic Gateway",
            description=(
                "The gateway is enormous — a ring of ancient metal spanning thousands of "
                "kilometres, pulsing with dormant energy. As your Class 1 Identification "
                "Code activates, the gateway roars to life. But something stirs on the "
                "other side. Something ancient. Something that has been sleeping for 5,000 "
                "years. Ninurta awakens."
            ),
            choices=[
                EventChoice(
                    "Enter the Gateway and face Ninurta",
                    EventOutcome(
                        EventOutcomeType.COMBAT,
                        "There is no turning back. For humanity. For everything.",
                        combat_danger=5,
                        combat_is_federation=False,
                        quest_flag="defeated_ninurta",
                    ),
                ),
                EventChoice(
                    "Prepare further before entering",
                    EventOutcome(
                        EventOutcomeType.NOTHING,
                        "You back away from the gateway. The god sleeps... for now.",
                        quest_flag="reached_gateway",
                    ),
                ),
            ],
        ),
    ]


def _federation_encounter_events() -> list[Event]:
    """Events for encountering active federation fleets (high-danger derelicts)."""
    return [
        Event(
            title="Federation Ghost Fleet",
            description=(
                "Your sensors scream warnings. A fully active old federation "
                "fleet emerges from behind the wreckage — automated warships "
                "running on 5,000-year-old combat protocols. They are "
                "impossibly advanced and impossibly dangerous. But if you "
                "defeat them, their navigation database could contain "
                "something priceless."
            ),
            choices=[
                EventChoice(
                    "Engage the federation fleet",
                    EventOutcome(
                        EventOutcomeType.COMBAT,
                        "You move to intercept. Victory here could change everything.",
                        combat_danger=4,
                        combat_is_federation=True,
                        quest_flag="class_4_id_code",
                    ),
                ),
                EventChoice(
                    "Run — this is suicide",
                    EventOutcome(
                        EventOutcomeType.HULL_DAMAGE,
                        "You flee, taking glancing hits from pursuit drones.",
                        hull_change=-300,
                    ),
                ),
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Lore-enriched event variants (drop lore fragments alongside normal rewards)
# ---------------------------------------------------------------------------

def _lore_derelict_events() -> list[Event]:
    """Derelict events that discover lore fragments."""
    return [
        Event(
            title="The Captain's Archive",
            description=(
                "Deep in the wreck you find a sealed vault. Inside, a captain's "
                "personal archive — holographic recordings that have survived the ages."
            ),
            choices=[
                EventChoice(
                    "Download the archive",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "The recordings speak of the old federation's final days.",
                        lore_text=(
                            "The Federation of Stars spanned thousands of worlds. "
                            "Then, in a single moment, they were gone."
                        ),
                        quest_flag="lore_old_federation",
                        metal=150, energy=80,
                    ),
                ),
                EventChoice(
                    "Salvage the vault's hardware",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "The components are valuable, but the data is lost.",
                        rare=100,
                    ),
                ),
            ],
        ),
        Event(
            title="Prison Station Coordinates",
            description=(
                "A corrupted navigation log contains coordinates and a "
                "classified dossier about a prison station hidden inside a star."
            ),
            choices=[
                EventChoice(
                    "Decrypt the dossier",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "You learn the terrible truth about your ancestors.",
                        lore_text=(
                            "3,000 years before the Fall, dissidents were exiled "
                            "to a station hidden in the corona of a star."
                        ),
                        quest_flag="lore_prison_station",
                    ),
                    success_chance=0.8,
                ),
                EventChoice(
                    "Ignore it",
                    EventOutcome(EventOutcomeType.NOTHING, "Some things are better left buried."),
                ),
            ],
        ),
        Event(
            title="The Gateway Project Files",
            description=(
                "You find intact research files labelled 'PROJECT GATEWAY — "
                "TOP SECRET'. They detail humanity's greatest endeavour."
            ),
            choices=[
                EventChoice(
                    "Study the files",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "The details of the gateway project are staggering.",
                        lore_text=(
                            "The Trans-Galactic Gateway was activated. "
                            "And then something came through from the other side."
                        ),
                        quest_flag="lore_gateway_project",
                        energy=200,
                    ),
                ),
                EventChoice(
                    "Copy and move on",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "You take what's useful and continue.",
                        energy=100,
                    ),
                ),
            ],
        ),
    ]


def _lore_anomaly_events() -> list[Event]:
    """Anomaly events that discover lore fragments."""
    return [
        Event(
            title="Echoes of Ninurta",
            description=(
                "The anomaly pulses with an alien rhythm. Your sensors detect "
                "something... vast. Like a heartbeat in the void. Ancient "
                "fragments of data coalesce into a name: Ninurta."
            ),
            choices=[
                EventChoice(
                    "Analyze the data patterns",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "What you learn chills you to the bone.",
                        lore_text=(
                            "Ninurta — a being from beyond. It consumed the energy "
                            "of an entire civilization and fell into slumber."
                        ),
                        quest_flag="lore_ninurta_origin",
                    ),
                ),
                EventChoice(
                    "Shut down sensors and flee",
                    EventOutcome(
                        EventOutcomeType.NOTHING,
                        "Your crew breathes again once you're clear of the anomaly.",
                    ),
                ),
            ],
        ),
        Event(
            title="The Exiles' Beacon",
            description=(
                "A beacon, impossibly old, broadcasting on a frequency "
                "that matches your mothership's systems. A message from "
                "the station — from YOUR ancestors."
            ),
            choices=[
                EventChoice(
                    "Receive the message",
                    EventOutcome(
                        EventOutcomeType.GAIN_LORE,
                        "The words of the exiles echo across millennia.",
                        lore_text=(
                            "We are the descendants of criminals. But our ancestors "
                            "survived, and they launched the Mothership."
                        ),
                        quest_flag="lore_exiles",
                        energy=100,
                    ),
                ),
                EventChoice(
                    "Record frequency and continue",
                    EventOutcome(
                        EventOutcomeType.GAIN_RESOURCES,
                        "The beacon's components yield some energy.",
                        energy=150,
                    ),
                ),
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Event selection
# ---------------------------------------------------------------------------

_EVENT_POOLS: dict[str, list[Event]] = {
    "derelict": _derelict_events() + _lore_derelict_events() + _federation_encounter_events(),
    "station_ruin": _derelict_events() + _lore_derelict_events(),
    "anomaly": _anomaly_events() + _lore_anomaly_events(),
    "alien_outpost": _alien_events(),
    "planet": _planet_events(),
    "asteroid_field": _planet_events(),
}

# Quest-critical event pools (keyed by special_tag)
_QUEST_EVENT_POOLS: dict[str, list[Event]] = {
    "earth": _earth_events(),
    "gateway": _gateway_events(),
}


def get_event_for_object_type(obj_type_value: str, rng: random.Random | None = None) -> Event | None:
    """Get a random event appropriate for the object type."""
    if rng is None:
        rng = random.Random()

    pool = _EVENT_POOLS.get(obj_type_value, [])
    if not pool:
        return None

    return rng.choice(pool)


def get_quest_event(special_tag: str, rng: random.Random | None = None) -> Event | None:
    """Get a quest-critical event for a special object tag."""
    if rng is None:
        rng = random.Random()

    pool = _QUEST_EVENT_POOLS.get(special_tag, [])
    if not pool:
        return None

    return rng.choice(pool)

