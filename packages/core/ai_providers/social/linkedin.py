"""
LinkedIn platform-specific extractor.

Extracts structured data from LinkedIn pages by parsing:
1. JSON-LD (application/ld+json) — structured data for profiles, jobs, companies
2. <code> tags with embedded JSON — LinkedIn's client-side data store
3. __INITIAL_STATE__ — serialized page state
4. Meta tags — fallback for title, description, images

Supports: profiles, job listings, company pages, posts/articles

NOTE: LinkedIn is a hard-target — always routes through Camoufox.
Session continuity requires li_at and li_fat_id cookies.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

from packages.core.ai_providers.social.base import (
    deep_get,
    extract_json_from_script,
    extract_meta_tags,
    extract_title,
    find_key_recursive,
    parse_count,
    parse_timestamp,
)

logger = logging.getLogger(__name__)

# Domains this extractor handles
LINKEDIN_DOMAINS = ["linkedin.com", "www.linkedin.com"]


class LinkedInExtractor:
    """Extract structured data from LinkedIn HTML pages."""

    DOMAINS = LINKEDIN_DOMAINS

    def extract(self, html: str, url: str) -> list[dict]:
        """Route to the appropriate extraction method based on URL pattern."""
        path = urlparse(url).path.lower().rstrip("/")

        if "/in/" in path:
            return self._extract_profile(html, url)
        elif "/jobs/view/" in path or "/jobs/search/" in path:
            return self._extract_job(html, url)
        elif "/company/" in path:
            return self._extract_company(html, url)
        elif "/posts/" in path or "/feed/" in path or "/pulse/" in path:
            return self._extract_post(html, url)
        else:
            # Fallback: try profile, then generic
            result = self._extract_profile(html, url)
            if result and result[0].get("name"):
                return result
            return self._extract_generic(html, url)

    # -------------------------------------------------------------------
    # Profile extraction
    # -------------------------------------------------------------------

    def _extract_profile(self, html: str, url: str) -> list[dict]:
        """Extract professional profile data from a LinkedIn profile page."""
        json_ld = self._get_json_ld(html, expected_type="Person")
        initial_state = self._get_initial_state(html)
        code_data = self._get_code_embedded_data(html)
        meta = extract_meta_tags(html)

        profile: dict[str, Any] = {"profile_url": url}

        # --- From JSON-LD ---
        if json_ld:
            profile["name"] = json_ld.get("name")
            profile["headline"] = json_ld.get("jobTitle") or json_ld.get("headline")
            profile["location"] = self._extract_location_from_jsonld(json_ld)
            profile["about"] = json_ld.get("description")
            profile["profile_image"] = json_ld.get("image", {}).get("contentUrl") if isinstance(json_ld.get("image"), dict) else json_ld.get("image")

            # Work experience from JSON-LD
            work_list = json_ld.get("worksFor", [])
            if isinstance(work_list, dict):
                work_list = [work_list]
            if work_list:
                first_work = work_list[0] if work_list else {}
                profile["current_company"] = (
                    first_work.get("name")
                    or deep_get(first_work, "organization", "name")
                )

            # Education from JSON-LD
            alumni_of = json_ld.get("alumniOf", [])
            if isinstance(alumni_of, dict):
                alumni_of = [alumni_of]
            if alumni_of:
                profile["education"] = [
                    {
                        "institution": item.get("name")
                        or deep_get(item, "organization", "name"),
                        "url": item.get("url"),
                    }
                    for item in alumni_of
                    if item.get("name") or deep_get(item, "organization", "name")
                ]

        # --- From __INITIAL_STATE__ / code-embedded data ---
        merged = {**(initial_state or {}), **(code_data or {})}
        if merged:
            profile_data = (
                find_key_recursive(merged, "publicProfileTopCardV2")
                or find_key_recursive(merged, "profileTopCard")
                or find_key_recursive(merged, "profileView")
                or find_key_recursive(merged, "profile")
                or {}
            )

            if not profile.get("name"):
                first = profile_data.get("firstName", "")
                last = profile_data.get("lastName", "")
                full = f"{first} {last}".strip()
                if full:
                    profile["name"] = full

            if not profile.get("headline"):
                profile["headline"] = profile_data.get("headline")

            if not profile.get("location"):
                profile["location"] = (
                    profile_data.get("locationName")
                    or profile_data.get("geoLocationName")
                    or deep_get(profile_data, "location", "basicLocation", "countryCode")
                )

            if not profile.get("about"):
                profile["about"] = profile_data.get("summary")

            if not profile.get("current_title"):
                profile["current_title"] = profile_data.get("headline")

            # Connections
            connections = (
                profile_data.get("connections")
                or profile_data.get("connectionsCount")
                or find_key_recursive(merged, "connectionCount")
            )
            if connections is not None:
                profile["connections"] = parse_count(str(connections))

            # Experience list
            experience_section = (
                find_key_recursive(merged, "experienceView")
                or find_key_recursive(merged, "experience")
            )
            if isinstance(experience_section, dict):
                elements = experience_section.get("elements", experience_section.get("positions", []))
                if isinstance(elements, list):
                    exp_list = []
                    for elem in elements[:10]:
                        exp_entry = {
                            "title": elem.get("title"),
                            "company": (
                                elem.get("companyName")
                                or deep_get(elem, "company", "name")
                            ),
                            "location": elem.get("locationName"),
                            "start_date": self._format_date_range(elem.get("timePeriod", {}).get("startDate")),
                            "end_date": self._format_date_range(elem.get("timePeriod", {}).get("endDate")),
                        }
                        exp_entry = {k: v for k, v in exp_entry.items() if v is not None}
                        if exp_entry.get("title") or exp_entry.get("company"):
                            exp_list.append(exp_entry)
                    if exp_list:
                        profile["experience"] = exp_list
                        if not profile.get("current_company") and exp_list:
                            profile["current_company"] = exp_list[0].get("company")
                        if not profile.get("current_title") and exp_list:
                            profile["current_title"] = exp_list[0].get("title")

            # Skills list
            skills_section = find_key_recursive(merged, "skillView") or find_key_recursive(merged, "skills")
            if isinstance(skills_section, dict):
                skill_elements = skills_section.get("elements", skills_section.get("skills", []))
                if isinstance(skill_elements, list):
                    skills = [
                        s.get("name") or s.get("skill", {}).get("name")
                        for s in skill_elements
                        if s.get("name") or s.get("skill", {}).get("name")
                    ]
                    if skills:
                        profile["skills"] = skills[:25]

            # Education list (if not already from JSON-LD)
            if not profile.get("education"):
                edu_section = find_key_recursive(merged, "educationView") or find_key_recursive(merged, "education")
                if isinstance(edu_section, dict):
                    edu_elements = edu_section.get("elements", edu_section.get("educations", []))
                    if isinstance(edu_elements, list):
                        edu_list = []
                        for elem in edu_elements[:10]:
                            edu_entry = {
                                "institution": (
                                    elem.get("schoolName")
                                    or deep_get(elem, "school", "name")
                                ),
                                "degree": elem.get("degreeName"),
                                "field": elem.get("fieldOfStudy"),
                            }
                            edu_entry = {k: v for k, v in edu_entry.items() if v is not None}
                            if edu_entry.get("institution"):
                                edu_list.append(edu_entry)
                        if edu_list:
                            profile["education"] = edu_list

        # --- Fallback to meta tags ---
        if not profile.get("name"):
            og_title = meta.get("og:title") or extract_title(html) or ""
            # LinkedIn titles are usually "Name - Title | LinkedIn"
            profile["name"] = og_title.split(" - ")[0].split(" | ")[0].strip() or None
        if not profile.get("about"):
            profile["about"] = meta.get("og:description") or meta.get("description")
        if not profile.get("profile_image"):
            profile["profile_image"] = meta.get("og:image")

        # Clean None values
        profile = {k: v for k, v in profile.items() if v is not None}

        return [profile] if profile.get("name") else []

    # -------------------------------------------------------------------
    # Job listing extraction
    # -------------------------------------------------------------------

    def _extract_job(self, html: str, url: str) -> list[dict]:
        """Extract job listing data from a LinkedIn job page."""
        json_ld = self._get_json_ld(html, expected_type="JobPosting")
        initial_state = self._get_initial_state(html)
        code_data = self._get_code_embedded_data(html)
        meta = extract_meta_tags(html)

        job: dict[str, Any] = {"job_url": url}

        # --- From JSON-LD (most reliable for job postings) ---
        if json_ld:
            job["title"] = json_ld.get("title")
            job["description"] = json_ld.get("description")
            job["posted_date"] = json_ld.get("datePosted")
            job["employment_type"] = json_ld.get("employmentType")

            # Company info
            hiring_org = json_ld.get("hiringOrganization", {})
            if isinstance(hiring_org, dict):
                job["company"] = hiring_org.get("name")

            # Location
            job_location = json_ld.get("jobLocation", {})
            if isinstance(job_location, dict):
                address = job_location.get("address", {})
                if isinstance(address, dict):
                    parts = [
                        address.get("addressLocality"),
                        address.get("addressRegion"),
                        address.get("addressCountry"),
                    ]
                    job["location"] = ", ".join(p for p in parts if p) or None

            # Salary
            salary = json_ld.get("baseSalary", {})
            if isinstance(salary, dict):
                value = salary.get("value", {})
                if isinstance(value, dict):
                    min_val = value.get("minValue")
                    max_val = value.get("maxValue")
                    currency = salary.get("currency", "")
                    if min_val and max_val:
                        job["salary_range"] = f"{currency} {min_val} - {max_val}".strip()
                    elif min_val:
                        job["salary_range"] = f"{currency} {min_val}+".strip()

        # --- From __INITIAL_STATE__ / code-embedded data ---
        merged = {**(initial_state or {}), **(code_data or {})}
        if merged:
            job_data = (
                find_key_recursive(merged, "jobPostingData")
                or find_key_recursive(merged, "decoratedJobPosting")
                or find_key_recursive(merged, "jobPosting")
                or {}
            )

            if not job.get("title"):
                job["title"] = job_data.get("title")
            if not job.get("company"):
                job["company"] = (
                    job_data.get("companyName")
                    or deep_get(job_data, "companyDetails", "name")
                )
            if not job.get("location"):
                job["location"] = (
                    job_data.get("formattedLocation")
                    or job_data.get("locationName")
                )
            if not job.get("description"):
                job["description"] = (
                    job_data.get("description", {}).get("text")
                    if isinstance(job_data.get("description"), dict)
                    else job_data.get("description")
                )

            # Seniority level
            seniority = (
                job_data.get("seniorityLevel")
                or find_key_recursive(merged, "experienceLevel")
            )
            if seniority:
                job["seniority_level"] = seniority

            # Applicants
            applicants = (
                job_data.get("applicantCount")
                or find_key_recursive(merged, "numApplicants")
            )
            if applicants is not None:
                job["applicants"] = parse_count(str(applicants))

            # Skills required
            skills = find_key_recursive(merged, "skillMatchStatuses") or find_key_recursive(merged, "requiredSkills")
            if isinstance(skills, list):
                skill_names = []
                for s in skills:
                    name = s.get("name") or s.get("localizedSkillDisplayName") or s.get("skill", {}).get("name") if isinstance(s, dict) else str(s)
                    if name:
                        skill_names.append(name)
                if skill_names:
                    job["skills_required"] = skill_names

        # --- Fallback to meta tags ---
        if not job.get("title"):
            og_title = meta.get("og:title") or extract_title(html) or ""
            # LinkedIn job titles: "Title at Company | LinkedIn"
            job["title"] = og_title.split(" | ")[0].strip() or None
        if not job.get("description"):
            job["description"] = meta.get("og:description") or meta.get("description")

        # Clean None values
        job = {k: v for k, v in job.items() if v is not None}

        return [job] if job.get("title") else []

    # -------------------------------------------------------------------
    # Company page extraction
    # -------------------------------------------------------------------

    def _extract_company(self, html: str, url: str) -> list[dict]:
        """Extract company page data from a LinkedIn company page."""
        json_ld = self._get_json_ld(html, expected_type="Organization")
        initial_state = self._get_initial_state(html)
        code_data = self._get_code_embedded_data(html)
        meta = extract_meta_tags(html)

        company: dict[str, Any] = {"company_url": url}

        # --- From JSON-LD ---
        if json_ld:
            company["name"] = json_ld.get("name")
            company["website"] = json_ld.get("url")
            company["industry"] = json_ld.get("industry")
            company["founded"] = json_ld.get("foundingDate")

            # Address / headquarters
            address = json_ld.get("address", {})
            if isinstance(address, dict):
                parts = [
                    address.get("addressLocality"),
                    address.get("addressRegion"),
                    address.get("addressCountry"),
                ]
                hq = ", ".join(p for p in parts if p)
                if hq:
                    company["headquarters"] = hq

            # Number of employees
            num_employees = json_ld.get("numberOfEmployees", {})
            if isinstance(num_employees, dict):
                value = num_employees.get("value")
                if value:
                    company["company_size"] = str(value)

            company["tagline"] = json_ld.get("slogan") or json_ld.get("description")

        # --- From __INITIAL_STATE__ / code-embedded data ---
        merged = {**(initial_state or {}), **(code_data or {})}
        if merged:
            org_data = (
                find_key_recursive(merged, "organizationView")
                or find_key_recursive(merged, "companyPageData")
                or find_key_recursive(merged, "organization")
                or {}
            )

            if not company.get("name"):
                company["name"] = org_data.get("name") or org_data.get("universalName")
            if not company.get("tagline"):
                company["tagline"] = org_data.get("tagline")
            if not company.get("industry"):
                company["industry"] = (
                    org_data.get("companyIndustries", [{}])[0].get("localizedName")
                    if isinstance(org_data.get("companyIndustries"), list) and org_data.get("companyIndustries")
                    else org_data.get("industry")
                )
            if not company.get("company_size"):
                staff = org_data.get("staffCount") or org_data.get("staffCountRange")
                if isinstance(staff, dict):
                    company["company_size"] = f"{staff.get('start', '')} - {staff.get('end', '')}".strip(" -")
                elif staff is not None:
                    company["company_size"] = str(staff)

            if not company.get("headquarters"):
                hq = org_data.get("headquarter") or org_data.get("headquarters") or {}
                if isinstance(hq, dict):
                    parts = [hq.get("city"), hq.get("geographicArea"), hq.get("country")]
                    hq_str = ", ".join(p for p in parts if p)
                    if hq_str:
                        company["headquarters"] = hq_str

            if not company.get("founded"):
                company["founded"] = org_data.get("foundedOn", {}).get("year") if isinstance(org_data.get("foundedOn"), dict) else org_data.get("foundedYear")

            if not company.get("website"):
                company["website"] = org_data.get("companyPageUrl") or org_data.get("website")

            # Specialties
            specialties = org_data.get("specialities") or org_data.get("specialties") or org_data.get("tagline")
            if isinstance(specialties, list):
                company["specialties"] = specialties
            elif isinstance(specialties, str) and "," in specialties:
                company["specialties"] = [s.strip() for s in specialties.split(",") if s.strip()]

            # Followers
            followers = (
                org_data.get("followingInfo", {}).get("followerCount")
                if isinstance(org_data.get("followingInfo"), dict)
                else org_data.get("followerCount")
            )
            if followers is not None:
                company["followers"] = parse_count(str(followers))

            # Employees on LinkedIn
            employees_on_li = org_data.get("staffCount") or find_key_recursive(merged, "employeeCountRange")
            if employees_on_li is not None:
                company["employees_on_linkedin"] = parse_count(str(employees_on_li)) if not isinstance(employees_on_li, dict) else None

        # --- Fallback to meta tags ---
        if not company.get("name"):
            og_title = meta.get("og:title") or extract_title(html) or ""
            company["name"] = og_title.split(" | ")[0].strip() or None
        if not company.get("tagline"):
            company["tagline"] = meta.get("og:description") or meta.get("description")

        # Clean None values
        company = {k: v for k, v in company.items() if v is not None}

        return [company] if company.get("name") else []

    # -------------------------------------------------------------------
    # Post/article extraction
    # -------------------------------------------------------------------

    def _extract_post(self, html: str, url: str) -> list[dict]:
        """Extract post or article data from a LinkedIn post page."""
        json_ld = self._get_json_ld(html, expected_type="Article")
        initial_state = self._get_initial_state(html)
        code_data = self._get_code_embedded_data(html)
        meta = extract_meta_tags(html)

        post: dict[str, Any] = {"post_url": url}

        # --- From JSON-LD ---
        if json_ld:
            post["author"] = (
                json_ld.get("author", {}).get("name")
                if isinstance(json_ld.get("author"), dict)
                else json_ld.get("author")
            )
            post["text"] = json_ld.get("articleBody") or json_ld.get("description")
            post["timestamp"] = json_ld.get("datePublished") or json_ld.get("dateCreated")
            # Media
            image = json_ld.get("image")
            if image:
                if isinstance(image, list):
                    post["media_urls"] = image
                elif isinstance(image, str):
                    post["media_urls"] = [image]

        # --- From __INITIAL_STATE__ / code-embedded data ---
        merged = {**(initial_state or {}), **(code_data or {})}
        if merged:
            post_data = (
                find_key_recursive(merged, "updateV2")
                or find_key_recursive(merged, "feedUpdate")
                or find_key_recursive(merged, "activity")
                or {}
            )

            if not post.get("author"):
                actor = post_data.get("actor", {})
                if isinstance(actor, dict):
                    post["author"] = (
                        deep_get(actor, "name", "text")
                        or actor.get("name")
                    )

            if not post.get("text"):
                commentary = (
                    deep_get(post_data, "commentary", "text", "text")
                    or deep_get(post_data, "commentary", "text")
                    or post_data.get("text")
                )
                if commentary:
                    post["text"] = commentary

            if not post.get("timestamp"):
                post["timestamp"] = parse_timestamp(
                    post_data.get("createdAt") or post_data.get("publishedAt")
                )

            # Engagement metrics
            social_detail = (
                post_data.get("socialDetail")
                or find_key_recursive(merged, "socialDetail")
                or {}
            )
            if isinstance(social_detail, dict):
                likes = social_detail.get("totalSocialActivityCounts", {}).get("numLikes") if isinstance(social_detail.get("totalSocialActivityCounts"), dict) else social_detail.get("likes")
                if likes is not None:
                    post["likes"] = parse_count(str(likes))

                comments = social_detail.get("totalSocialActivityCounts", {}).get("numComments") if isinstance(social_detail.get("totalSocialActivityCounts"), dict) else social_detail.get("comments")
                if comments is not None:
                    post["comments"] = parse_count(str(comments))

                shares = social_detail.get("totalSocialActivityCounts", {}).get("numShares") if isinstance(social_detail.get("totalSocialActivityCounts"), dict) else social_detail.get("shares")
                if shares is not None:
                    post["shares"] = parse_count(str(shares))

            # Media URLs from content
            if not post.get("media_urls"):
                content = post_data.get("content", {})
                if isinstance(content, dict):
                    media_urls = []
                    images = find_key_recursive(content, "images") or []
                    if isinstance(images, list):
                        for img in images:
                            img_url = deep_get(img, "attributes", "0", "vectorImage", "rootUrl") if isinstance(img, dict) else None
                            if img_url:
                                media_urls.append(img_url)
                    video_url = deep_get(content, "videoComponent", "video", "progressiveStreams", "0", "streamingLocations", "0", "url")
                    if video_url:
                        media_urls.append(video_url)
                    if media_urls:
                        post["media_urls"] = media_urls

        # --- Fallback to meta tags ---
        if not post.get("text"):
            post["text"] = meta.get("og:description") or meta.get("description")
        if not post.get("author"):
            og_title = meta.get("og:title") or extract_title(html) or ""
            # LinkedIn post titles are often "Author on LinkedIn: text..."
            if " on LinkedIn" in og_title:
                post["author"] = og_title.split(" on LinkedIn")[0].strip()
        if not post.get("media_urls"):
            og_image = meta.get("og:image")
            if og_image:
                post["media_urls"] = [og_image]

        # Clean None values
        post = {k: v for k, v in post.items() if v is not None}

        return [post] if post.get("text") or post.get("author") else []

    # -------------------------------------------------------------------
    # Generic extraction (fallback for any LinkedIn page)
    # -------------------------------------------------------------------

    def _extract_generic(self, html: str, url: str) -> list[dict]:
        """Fallback extraction using meta tags for any LinkedIn page."""
        meta = extract_meta_tags(html)
        result: dict[str, Any] = {"url": url}

        result["title"] = meta.get("og:title") or extract_title(html)
        result["description"] = meta.get("og:description") or meta.get("description")
        result["image"] = meta.get("og:image")

        result = {k: v for k, v in result.items() if v is not None}
        return [result] if result.get("title") else []

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _get_json_ld(self, html: str, expected_type: str | None = None) -> dict | None:
        """Extract JSON-LD data from <script type="application/ld+json"> tags.

        Args:
            html: Raw HTML content.
            expected_type: If specified, only return JSON-LD matching this @type.

        Returns:
            Parsed JSON-LD dict, or None.
        """
        pattern = re.compile(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            try:
                data = json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                continue

            # Handle @graph arrays
            if isinstance(data, dict) and "@graph" in data:
                for item in data["@graph"]:
                    if expected_type and isinstance(item, dict):
                        item_type = item.get("@type", "")
                        if isinstance(item_type, list):
                            if expected_type in item_type:
                                return item
                        elif item_type == expected_type:
                            return item
                continue

            if isinstance(data, list):
                for item in data:
                    if expected_type and isinstance(item, dict):
                        item_type = item.get("@type", "")
                        if isinstance(item_type, list):
                            if expected_type in item_type:
                                return item
                        elif item_type == expected_type:
                            return item
                # If no type match, return first
                if not expected_type and data:
                    return data[0] if isinstance(data[0], dict) else None
                continue

            if isinstance(data, dict):
                if expected_type:
                    item_type = data.get("@type", "")
                    if isinstance(item_type, list):
                        if expected_type in item_type:
                            return data
                    elif item_type == expected_type:
                        return data
                else:
                    return data

        # If no type-matched JSON-LD found, return any JSON-LD available
        if expected_type:
            return self._get_json_ld(html, expected_type=None)

        return None

    def _get_initial_state(self, html: str) -> dict | None:
        """Extract __INITIAL_STATE__ data from LinkedIn page HTML."""
        # LinkedIn embeds state as: window.__INITIAL_STATE__ = {...};
        data = extract_json_from_script(html, var_name="__INITIAL_STATE__")
        if data:
            return data

        # Alternative pattern used by some LinkedIn pages
        pattern = re.compile(
            r'<!--\s*(\{.+?"included".+?\})\s*-->',
            re.DOTALL,
        )
        match = pattern.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return None

    def _get_code_embedded_data(self, html: str) -> dict | None:
        """Extract data from LinkedIn's <code> tags with embedded JSON.

        LinkedIn stores client-side data in <code> tags with specific IDs,
        encoded as HTML entities or raw JSON.
        """
        # Pattern: <code id="bpr-guid-XXXX" style="display: none"><!--{...}--></code>
        code_pattern = re.compile(
            r'<code[^>]*><!--({.*?})--></code>',
            re.DOTALL,
        )

        merged: dict[str, Any] = {}
        for match in code_pattern.finditer(html):
            try:
                data = json.loads(match.group(1))
                if isinstance(data, dict):
                    # LinkedIn wraps included entities in an "included" array
                    included = data.get("included", [])
                    if isinstance(included, list):
                        for item in included:
                            if isinstance(item, dict) and "$type" in item:
                                type_name = item["$type"].split(".")[-1]
                                merged[type_name] = item
                    # Also merge top-level data
                    merged.update(data.get("data", data))
            except json.JSONDecodeError:
                continue

        return merged if merged else None

    def _extract_location_from_jsonld(self, json_ld: dict) -> str | None:
        """Extract location string from JSON-LD data."""
        address = json_ld.get("address", {})
        if isinstance(address, dict):
            parts = [
                address.get("addressLocality"),
                address.get("addressRegion"),
                address.get("addressCountry"),
            ]
            loc = ", ".join(p for p in parts if p)
            return loc if loc else None
        if isinstance(address, str):
            return address
        return None

    @staticmethod
    def _format_date_range(date_obj: dict | None) -> str | None:
        """Format a LinkedIn date object (with month/year) into a string."""
        if not date_obj or not isinstance(date_obj, dict):
            return None
        year = date_obj.get("year")
        month = date_obj.get("month")
        if year and month:
            return f"{year}-{month:02d}"
        if year:
            return str(year)
        return None
