import pytest
from packages.contracts.schemas.real_estate import RealEstateListing, PropertyAddress, PropertyFeatures

def test_real_estate_listing_schema():
    property_data = {
        "url": "https://zillow.com/homedetails/123",
        "title": "Beautiful Family Home",
        "description": "A wonderful 4 bed 3 bath home.",
        "source": "Zillow",
        "price": 450000,
        "status": "For Sale",
        "address": {
            "street": "123 Elm St",
            "city": "Springfield",
            "state": "IL",
            "zip_code": "62701"
        },
        "features": {
            "bedrooms": 4,
            "bathrooms": 3.5,
            "square_feet": 2500,
            "property_type": "Single Family"
        },
        "images": ["http://img1.jpg", "http://img2.jpg"]
    }

    listing = RealEstateListing(**property_data)
    assert listing.title == "Beautiful Family Home"
    assert listing.price == 450000.0
    assert listing.address.city == "Springfield"
    assert listing.features.bedrooms == 4.0
    assert listing.features.bathrooms == 3.5
    assert len(listing.images) == 2

def test_real_estate_listing_validation_error():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RealEstateListing(
            title="Missing URL and other fields"
        )
