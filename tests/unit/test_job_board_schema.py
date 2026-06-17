import pytest
from packages.contracts.schemas.job_board import JobListing, JobLocation, JobCompensation

def test_job_listing_schema():
    job_data = {
        "url": "https://indeed.com/job/123",
        "title": "Senior Software Engineer",
        "company_name": "Tech Corp",
        "description": "We are looking for a senior engineer.",
        "source": "Indeed",
        "location": {
            "city": "San Francisco",
            "state": "CA",
            "remote": True
        },
        "compensation": {
            "min_salary": 150000,
            "max_salary": 200000,
            "currency": "USD",
            "period": "YEARLY"
        }
    }

    job = JobListing(**job_data)
    assert job.title == "Senior Software Engineer"
    assert job.company_name == "Tech Corp"
    assert job.location.city == "San Francisco"
    assert job.location.remote is True
    assert job.compensation.min_salary == 150000.0

def test_job_listing_validation_error():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        JobListing(
            title="Missing URL and other fields"
        )
