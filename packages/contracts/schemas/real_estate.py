"""Pydantic schemas for standardizing Real Estate listings."""

from typing import Optional, List
from pydantic import BaseModel, Field

class PropertyAddress(BaseModel):
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State or province")
    zip_code: Optional[str] = Field(None, description="Postal or ZIP code")
    country: Optional[str] = Field(None, description="Country")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")

class PropertyFeatures(BaseModel):
    bedrooms: Optional[float] = Field(None, description="Number of bedrooms (can be half)")
    bathrooms: Optional[float] = Field(None, description="Number of bathrooms (can be half)")
    square_feet: Optional[float] = Field(None, description="Total square footage/meters of the property")
    lot_size: Optional[float] = Field(None, description="Size of the lot in square feet or acres")
    year_built: Optional[int] = Field(None, description="Year the property was built")
    property_type: Optional[str] = Field(None, description="e.g., Single Family, Condo, Townhouse, Multi-Family")

class RealEstateListing(BaseModel):
    """Normalized schema for a Real Estate listing (Zillow, Realtor.com, Redfin, etc.)."""
    id: Optional[str] = Field(None, description="Unique identifier for the property listing")
    url: str = Field(..., description="Direct URL to view the property listing")
    title: str = Field(..., description="Title of the listing")

    price: Optional[float] = Field(None, description="Current listing price")
    currency: Optional[str] = Field("USD", description="Currency of the price")
    status: Optional[str] = Field(None, description="e.g., For Sale, For Rent, Pending, Sold")

    address: PropertyAddress = Field(default_factory=PropertyAddress, description="Address details of the property")
    features: PropertyFeatures = Field(default_factory=PropertyFeatures, description="Key features of the property")

    description: str = Field(..., description="Full text description of the property")
    images: List[str] = Field(default_factory=list, description="List of image URLs")
    agent_name: Optional[str] = Field(None, description="Name of the listing agent")
    agent_phone: Optional[str] = Field(None, description="Phone number of the listing agent or agency")
    agency_name: Optional[str] = Field(None, description="Name of the real estate agency")

    days_on_market: Optional[int] = Field(None, description="Number of days the property has been listed")
    scraped_at: Optional[str] = Field(None, description="ISO 8601 date when the property was scraped")
    source: str = Field(..., description="The real estate platform from which the listing was scraped (e.g., Zillow, Redfin)")
