"""Pydantic schemas for standardizing Job Board listings."""

from typing import Optional, List
from pydantic import BaseModel, Field

class JobLocation(BaseModel):
    city: Optional[str] = Field(None, description="City where the job is located")
    state: Optional[str] = Field(None, description="State or province")
    country: Optional[str] = Field(None, description="Country of the job location")
    remote: bool = Field(False, description="Whether the job is remote")
    hybrid: bool = Field(False, description="Whether the job is hybrid")

class JobCompensation(BaseModel):
    min_salary: Optional[float] = Field(None, description="Minimum salary offered")
    max_salary: Optional[float] = Field(None, description="Maximum salary offered")
    currency: Optional[str] = Field(None, description="Currency of the compensation (e.g., USD, EUR)")
    period: Optional[str] = Field(None, description="Period of compensation (e.g., YEARLY, HOURLY, MONTHLY)")
    equity_offered: bool = Field(False, description="Whether equity or options are included")

class JobListing(BaseModel):
    """Normalized schema for a Job Board listing (Indeed, LinkedIn Jobs, Glassdoor, etc.)."""
    id: Optional[str] = Field(None, description="Unique identifier for the job post")
    url: str = Field(..., description="Direct URL to apply or view the job listing")
    title: str = Field(..., description="Job title")
    company_name: str = Field(..., description="Name of the hiring company")
    company_url: Optional[str] = Field(None, description="URL of the hiring company")

    location: JobLocation = Field(default_factory=JobLocation, description="Location details of the job")
    compensation: JobCompensation = Field(default_factory=JobCompensation, description="Salary and compensation details")

    employment_type: Optional[str] = Field(None, description="FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP")
    seniority_level: Optional[str] = Field(None, description="JUNIOR, MID, SENIOR, EXECUTIVE, LEAD")

    description: str = Field(..., description="Full text description of the job")
    requirements: List[str] = Field(default_factory=list, description="List of required skills or qualifications")
    benefits: List[str] = Field(default_factory=list, description="List of benefits offered")

    posted_at: Optional[str] = Field(None, description="ISO 8601 date when the job was posted")
    scraped_at: Optional[str] = Field(None, description="ISO 8601 date when the job was scraped")
    source: str = Field(..., description="The job board from which the listing was scraped (e.g., Indeed, LinkedIn)")
