"""
The structured environmental state schema. This is the canonical shape
referenced throughout the system (conversation memory, reasoning engine,
API request/response bodies). Every field is optional because the whole
point of the conversational layer is to progressively fill this in.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class SoilState(BaseModel):
    ph: Optional[float] = None
    organic_carbon: Optional[float] = Field(
        default=None, description="Soil organic carbon, percent"
    )
    moisture: Optional[float] = Field(default=None, description="Percent volumetric")
    nutrients: Optional[str] = None


class BiodiversityState(BaseModel):
    species_richness: Optional[str] = None  # low | moderate | high, or a count
    habitat_diversity: Optional[str] = None
    pollinator_diversity: Optional[str] = None
    vegetation_diversity: Optional[str] = None


class ClimateState(BaseModel):
    temperature: Optional[str] = None
    rainfall: Optional[str] = None  # low | moderate | high, or mm/year
    seasonality: Optional[str] = None


class HumanImpactState(BaseModel):
    pollution: Optional[str] = None
    deforestation: Optional[str] = None
    fragmentation: Optional[str] = None
    agricultural_pressure: Optional[str] = None
    urbanization: Optional[str] = None


class LocationState(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    region: Optional[str] = None


class EnvironmentalState(BaseModel):
    soil: SoilState = Field(default_factory=SoilState)
    land_use: Optional[str] = None
    crop: Optional[str] = None
    biodiversity: BiodiversityState = Field(default_factory=BiodiversityState)
    climate: ClimateState = Field(default_factory=ClimateState)
    human_impact: HumanImpactState = Field(default_factory=HumanImpactState)
    location: LocationState = Field(default_factory=LocationState)

    class Config:
        extra = "ignore"


# Fields considered "core" for triggering multi-metric reasoning. Missing
# information detection prioritizes these first.
CORE_FIELDS: List[str] = [
    "soil.organic_carbon",
    "climate.rainfall",
    "land_use",
    "location.region",
]

ALL_TRACKED_FIELDS: List[str] = CORE_FIELDS + [
    "soil.ph",
    "soil.moisture",
    "crop",
    "biodiversity.species_richness",
    "biodiversity.habitat_diversity",
    "biodiversity.pollinator_diversity",
    "biodiversity.vegetation_diversity",
    "climate.temperature",
    "climate.seasonality",
    "human_impact.pollution",
    "human_impact.deforestation",
    "human_impact.fragmentation",
    "human_impact.agricultural_pressure",
    "human_impact.urbanization",
]

FIELD_QUESTIONS = {
    "soil.organic_carbon": "Soil organic carbon (%)",
    "soil.ph": "Soil pH",
    "soil.moisture": "Soil moisture (%)",
    "climate.rainfall": "Rainfall pattern (low / moderate / high, or mm/year)",
    "climate.temperature": "Typical temperature range",
    "land_use": "Current land use / land cover",
    "crop": "Current crop or vegetation cover",
    "location.region": "Region or approximate coordinates",
    "biodiversity.species_richness": "Observed species richness (low / moderate / high)",
    "biodiversity.habitat_diversity": "Habitat diversity on the land",
    "human_impact.fragmentation": "Degree of habitat fragmentation nearby",
    "human_impact.agricultural_pressure": "Agricultural intensity (e.g. monoculture vs. rotation)",
}
