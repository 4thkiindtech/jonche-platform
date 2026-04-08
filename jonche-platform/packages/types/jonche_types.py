"""
packages/types/jonche_types.py
Shared type definitions (TypedDicts) used across apps.
"""

from typing import TypedDict, Literal


DropStatus = Literal["live", "upcoming", "draft", "sold_out"]
MemberTier = Literal["gold", "silver", "bronze"]
RetailerTier = Literal["premier", "select", "basic"]
RetailerStatus = Literal["active", "pending", "review"]


class Drop(TypedDict):
    id: str
    name: str
    colorway: str
    sizes: str
    price: int
    status: DropStatus
    units: int
    units_sold: int
    emoji: str


class Member(TypedDict):
    id: str
    name: str
    initials: str
    tier: MemberTier
    lifetime_spend: float
    drops: int


class Retailer(TypedDict):
    id: str
    name: str
    tier: RetailerTier
    allocation: int
    status: RetailerStatus


class Certificate(TypedDict):
    id: str
    drop_name: str
    size: int
    run_number: int
    total_run: int
    issued_date: str
    verified: bool


class StatsOverview(TypedDict):
    revenue: int
    revenue_growth: float
    units_dropped: int
    drops_completed: int
    sell_through: float
    vip_members: int
    new_vip_this_week: int
    avg_order_value: int
    repeat_buyer_rate: int
    new_customers: int
    conversion_rate: int
    supply_control_index: int
