"""Equipment inventory system for Hollowed Stars.

PLAN.md: Weapons are stored in the equipment inventory with other ship modules,
and can be selected to be equipped onto combat ships.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class EquipmentTier(enum.Enum):
    """Quality tier of equipment — determines effectiveness."""

    STANDARD = "standard"       # Player-crafted, baseline stats
    ALIEN = "alien"             # Traded/looted from aliens, usually worse but cheap
    FEDERATION = "federation"   # Salvaged from old federation, superior in every way


@dataclass
class EquipmentItem:
    """A single piece of equipment in the player's inventory."""

    name: str
    item_type: str              # "weapon", "component", "module", "material"
    tier: EquipmentTier = EquipmentTier.STANDARD
    weapon_size: str = ""       # WeaponSize value (if weapon): "small", "medium", etc.
    description: str = ""
    quantity: int = 1

    # Flexible stat storage for different item types
    stats: dict = field(default_factory=dict)

    @property
    def is_weapon(self) -> bool:
        return self.item_type == "weapon"

    @property
    def tier_label(self) -> str:
        return self.tier.value.title()

    @property
    def display_name(self) -> str:
        if self.tier != EquipmentTier.STANDARD:
            return f"{self.name} [{self.tier_label}]"
        return self.name


class Inventory:
    """Unified equipment and material storage for the fleet."""

    def __init__(self) -> None:
        self.items: list[EquipmentItem] = []

    def add_item(self, item: EquipmentItem) -> None:
        """Add an item to inventory. Stacks if same name/tier/type."""
        for existing in self.items:
            if (
                existing.name == item.name
                and existing.tier == item.tier
                and existing.item_type == item.item_type
            ):
                existing.quantity += item.quantity
                return
        self.items.append(item)

    def remove_item(self, name: str, tier: EquipmentTier | None = None, count: int = 1) -> bool:
        """Remove item(s) from inventory. Returns True if successful."""
        for item in self.items:
            if item.name == name and (tier is None or item.tier == tier):
                if item.quantity >= count:
                    item.quantity -= count
                    if item.quantity <= 0:
                        self.items.remove(item)
                    return True
        return False

    def get_weapons(self, size: str = "") -> list[EquipmentItem]:
        """Get all weapons, optionally filtered by weapon size."""
        weapons = [i for i in self.items if i.is_weapon]
        if size:
            weapons = [w for w in weapons if w.weapon_size == size]
        return weapons

    def get_by_tier(self, tier: EquipmentTier) -> list[EquipmentItem]:
        return [i for i in self.items if i.tier == tier]

    def get_by_type(self, item_type: str) -> list[EquipmentItem]:
        return [i for i in self.items if i.item_type == item_type]

    def has_item(self, name: str, tier: EquipmentTier | None = None) -> bool:
        """Check if an item exists in inventory."""
        for item in self.items:
            if item.name == name and (tier is None or item.tier == tier):
                return True
        return False

    def count_item(self, name: str, tier: EquipmentTier | None = None) -> int:
        """Count how many of a specific item we have."""
        for item in self.items:
            if item.name == name and (tier is None or item.tier == tier):
                return item.quantity
        return 0

    @property
    def total_items(self) -> int:
        return sum(i.quantity for i in self.items)

    @property
    def weapon_count(self) -> int:
        return sum(i.quantity for i in self.items if i.is_weapon)

    def to_dict_list(self) -> list[dict]:
        """Serialise inventory for save files."""
        result = []
        for item in self.items:
            result.append({
                "name": item.name,
                "item_type": item.item_type,
                "tier": item.tier.value,
                "weapon_size": item.weapon_size,
                "description": item.description,
                "quantity": item.quantity,
                "stats": item.stats,
            })
        return result

    @classmethod
    def from_dict_list(cls, data: list[dict]) -> "Inventory":
        """Deserialise inventory from save data."""
        inv = cls()
        for d in data:
            inv.items.append(EquipmentItem(
                name=d["name"],
                item_type=d["item_type"],
                tier=EquipmentTier(d.get("tier", "standard")),
                weapon_size=d.get("weapon_size", ""),
                description=d.get("description", ""),
                quantity=d.get("quantity", 1),
                stats=d.get("stats", {}),
            ))
        return inv
