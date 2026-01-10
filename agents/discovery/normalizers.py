"""
Grant Data Normalizers
Utilities for normalizing grant data from different sources to a consistent format.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
import re


class GrantNormalizer:
    """Base class for grant data normalization utilities."""

    # Standard date formats to try when parsing
    DATE_FORMATS = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%m/%d/%Y",
        "%m-%d-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]

    # Agency name mappings for standardization
    AGENCY_MAPPINGS = {
        # NSF
        "nsf": "National Science Foundation",
        "national science foundation": "National Science Foundation",
        # NIH and institutes
        "nih": "National Institutes of Health",
        "national institutes of health": "National Institutes of Health",
        "nci": "National Cancer Institute",
        "national cancer institute": "National Cancer Institute",
        "nimh": "National Institute of Mental Health",
        "niaid": "National Institute of Allergy and Infectious Diseases",
        "nhlbi": "National Heart, Lung, and Blood Institute",
        "ninds": "National Institute of Neurological Disorders and Stroke",
        "niddk": "National Institute of Diabetes and Digestive and Kidney Diseases",
        "nia": "National Institute on Aging",
        "nichd": "Eunice Kennedy Shriver National Institute of Child Health and Human Development",
        "niehs": "National Institute of Environmental Health Sciences",
        "nigms": "National Institute of General Medical Sciences",
        "nei": "National Eye Institute",
        "nidcd": "National Institute on Deafness and Other Communication Disorders",
        "nida": "National Institute on Drug Abuse",
        "niaaa": "National Institute on Alcohol Abuse and Alcoholism",
        # DOE
        "doe": "Department of Energy",
        "department of energy": "Department of Energy",
        # DARPA
        "darpa": "Defense Advanced Research Projects Agency",
        # NASA
        "nasa": "National Aeronautics and Space Administration",
        # Other common agencies
        "usda": "U.S. Department of Agriculture",
        "epa": "Environmental Protection Agency",
        "noaa": "National Oceanic and Atmospheric Administration",
        "cdc": "Centers for Disease Control and Prevention",
    }

    @staticmethod
    def parse_amount(value: Any) -> Optional[int]:
        """
        Parse various amount formats to integer cents.

        Handles:
        - Integers and floats
        - Decimal objects
        - Strings with currency symbols and commas
        - Strings with K/M suffixes

        Args:
            value: Amount value in various formats

        Returns:
            Integer amount in dollars, or None if unparseable
        """
        if value is None:
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, Decimal):
            return int(value)

        if isinstance(value, str):
            try:
                # Remove currency symbols and whitespace
                cleaned = value.strip()
                cleaned = re.sub(r"[,$\s]", "", cleaned)

                # Handle empty string
                if not cleaned:
                    return None

                # Handle K/M suffixes (e.g., "500K", "1.5M")
                multiplier = 1
                if cleaned.upper().endswith("K"):
                    multiplier = 1000
                    cleaned = cleaned[:-1]
                elif cleaned.upper().endswith("M"):
                    multiplier = 1000000
                    cleaned = cleaned[:-1]

                # Parse as float then convert to int
                amount = float(cleaned) * multiplier
                return int(amount)

            except (ValueError, InvalidOperation):
                return None

        return None

    @classmethod
    def parse_date(cls, value: Any, formats: Optional[list[str]] = None) -> Optional[str]:
        """
        Parse date from various formats to ISO format string.

        Args:
            value: Date value (string or datetime)
            formats: Optional list of formats to try (uses defaults if None)

        Returns:
            ISO format date string (YYYY-MM-DD), or None if unparseable
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return value.date().isoformat()

        if not isinstance(value, str):
            return None

        value = value.strip()
        if not value:
            return None

        # Try each format
        formats_to_try = formats or cls.DATE_FORMATS

        for fmt in formats_to_try:
            try:
                # Handle ISO with timezone
                date_str = (
                    value.split("T")[0] if "T" in value and fmt.startswith("%Y-%m-%d") and "T" not in fmt else value
                )
                dt = datetime.strptime(date_str, fmt.split("T")[0] if "T" not in fmt else fmt)
                return dt.date().isoformat()
            except ValueError:
                continue

        return None

    @classmethod
    def normalize_agency(cls, agency: Optional[str], institute: Optional[str] = None) -> str:
        """
        Normalize agency name to full standardized form.

        Args:
            agency: Agency name or abbreviation
            institute: Optional institute/sub-agency name

        Returns:
            Standardized agency name
        """
        if not agency:
            return "Unknown Agency"

        # Check mappings (case-insensitive)
        agency_lower = agency.lower().strip()
        if agency_lower in cls.AGENCY_MAPPINGS:
            base_agency = cls.AGENCY_MAPPINGS[agency_lower]
        else:
            # Use the original agency name if not in mappings
            base_agency = agency.strip()

        # Add institute if provided and different from agency
        if institute:
            institute_lower = institute.lower().strip()
            if institute_lower in cls.AGENCY_MAPPINGS:
                institute_name = cls.AGENCY_MAPPINGS[institute_lower]
                if institute_name != base_agency:
                    return f"{base_agency} / {institute_name}"

        return base_agency

    @staticmethod
    def clean_text(text: Optional[str], max_length: Optional[int] = None) -> Optional[str]:
        """
        Clean and normalize text content.

        - Strips whitespace
        - Normalizes unicode
        - Optionally truncates to max length

        Args:
            text: Text to clean
            max_length: Optional maximum length

        Returns:
            Cleaned text or None
        """
        if not text:
            return None

        # Strip and normalize whitespace
        cleaned = " ".join(text.split())

        # Truncate if needed
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[: max_length - 3] + "..."

        return cleaned if cleaned else None

    @staticmethod
    def extract_categories(
        keywords: Optional[str] = None,
        program_name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> list[str]:
        """
        Extract research categories from grant metadata.

        Uses keyword matching to identify relevant research areas.

        Args:
            keywords: Comma-separated keywords
            program_name: Program or fund name
            description: Grant description

        Returns:
            List of matched category strings
        """
        # Category keyword mappings
        CATEGORY_KEYWORDS = {
            "biomedical": ["health", "medical", "disease", "clinical", "patient", "therapy", "treatment"],
            "cancer": ["cancer", "oncology", "tumor", "carcinoma", "leukemia", "lymphoma"],
            "neuroscience": ["brain", "neural", "neuro", "cognitive", "psychology", "mental"],
            "genomics": ["genome", "genomic", "genetic", "dna", "rna", "sequencing", "crispr"],
            "climate": ["climate", "environment", "sustainability", "carbon", "emissions"],
            "ai_ml": ["artificial intelligence", "machine learning", "deep learning", "neural network", "nlp"],
            "engineering": ["engineering", "robotics", "automation", "manufacturing"],
            "chemistry": ["chemistry", "chemical", "molecular", "synthesis"],
            "physics": ["physics", "quantum", "particle", "astronomy", "astrophysics"],
            "social_sciences": ["social", "sociology", "economics", "policy", "behavioral"],
        }

        # Combine all text sources
        text_sources = []
        if keywords:
            text_sources.append(keywords.lower())
        if program_name:
            text_sources.append(program_name.lower())
        if description:
            text_sources.append(description.lower())

        combined_text = " ".join(text_sources)

        if not combined_text:
            return []

        # Find matching categories
        categories = []
        for category, keywords_list in CATEGORY_KEYWORDS.items():
            for keyword in keywords_list:
                if keyword in combined_text:
                    categories.append(category)
                    break  # Only add category once

        return categories


class NSFNormalizer(GrantNormalizer):
    """Normalizer for NSF Award Search API data."""

    DATE_FORMAT = "%m/%d/%Y"

    @classmethod
    def normalize(cls, award: dict) -> dict:
        """
        Convert NSF award data to normalized grant format.

        Args:
            award: Raw NSF award data dictionary

        Returns:
            Normalized grant dictionary matching Grant model
        """
        # Parse amount
        amount = cls.parse_amount(award.get("fundsObligatedAmt"))

        # Parse dates
        cls.parse_date(award.get("startDate"), [cls.DATE_FORMAT])
        end_date = cls.parse_date(award.get("expDate"), [cls.DATE_FORMAT])
        posted_date = cls.parse_date(award.get("date"), [cls.DATE_FORMAT])

        # Build PI name
        pi_parts = []
        if award.get("piFirstName"):
            pi_parts.append(award["piFirstName"])
        if award.get("piMiddeInitial"):
            pi_parts.append(award["piMiddeInitial"])
        if award.get("piLastName"):
            pi_parts.append(award["piLastName"])
        " ".join(pi_parts) if pi_parts else None

        # Extract categories
        categories = cls.extract_categories(
            keywords=award.get("cfdaNumber"),
            program_name=award.get("fundProgramName") or award.get("primaryProgram"),
            description=award.get("abstractText"),
        )

        return {
            "external_id": award.get("id"),
            "source": "nsf",
            "title": cls.clean_text(award.get("title")),
            "description": cls.clean_text(award.get("abstractText")),
            "agency": cls.normalize_agency("NSF"),
            "amount_min": amount,
            "amount_max": amount,
            "deadline": end_date,  # Use expiration as deadline
            "posted_at": posted_date,
            "url": f"https://www.nsf.gov/awardsearch/showAward?AWD_ID={award.get('id')}",
            "categories": categories,
            "eligibility": None,  # NSF doesn't provide in award data
            "raw_data": award,
        }


class NIHReporterNormalizer(GrantNormalizer):
    """Normalizer for NIH Reporter API data."""

    @classmethod
    def normalize(cls, project: dict) -> dict:
        """
        Convert NIH Reporter project data to normalized grant format.

        Args:
            project: Raw NIH Reporter project data dictionary

        Returns:
            Normalized grant dictionary matching Grant model
        """
        # Parse amount
        amount = cls.parse_amount(project.get("award_amount"))

        # Parse dates
        start_date = cls.parse_date(project.get("project_start_date"))
        end_date = cls.parse_date(project.get("project_end_date"))
        posted_date = cls.parse_date(project.get("award_notice_date"))

        # Get agency info
        agency_info = project.get("agency_ic_admin", {}) or {}
        agency_name = agency_info.get("name") or agency_info.get("abbreviation") or "NIH"
        agency = cls.normalize_agency("NIH", agency_name)

        # Get PI info
        pis = project.get("principal_investigators", []) or []
        if pis:
            primary_pi = pis[0]
            pi_parts = []
            if primary_pi.get("first_name"):
                pi_parts.append(primary_pi["first_name"])
            if primary_pi.get("middle_name"):
                pi_parts.append(primary_pi["middle_name"])
            if primary_pi.get("last_name"):
                pi_parts.append(primary_pi["last_name"])
            " ".join(pi_parts) if pi_parts else None
            primary_pi.get("email")

        # Get organization info
        org = project.get("organization", {}) or {}

        # Extract categories
        categories = cls.extract_categories(
            keywords=project.get("terms"),
            program_name=project.get("activity_code"),
            description=project.get("abstract_text") or project.get("phr_text"),
        )

        return {
            "external_id": project.get("project_num"),
            "source": "nih_reporter",
            "title": cls.clean_text(project.get("project_title")),
            "description": cls.clean_text(project.get("abstract_text") or project.get("phr_text")),
            "agency": agency,
            "amount_min": amount,
            "amount_max": amount,
            "deadline": end_date,  # Use project end as deadline
            "posted_at": posted_date or start_date,
            "url": f"https://reporter.nih.gov/project-details/{project.get('project_num')}",
            "categories": categories,
            "eligibility": {
                "institution": org.get("org_name"),
                "institution_city": org.get("org_city"),
                "institution_state": org.get("org_state"),
            }
            if org
            else None,
            "raw_data": project,
        }


class GrantsGovNormalizer(GrantNormalizer):
    """Normalizer for Grants.gov API data."""

    @classmethod
    def normalize(cls, opportunity: dict) -> dict:
        """
        Convert Grants.gov opportunity data to normalized grant format.

        Args:
            opportunity: Raw Grants.gov opportunity data dictionary

        Returns:
            Normalized grant dictionary matching Grant model
        """
        # Parse amounts
        amount_min = cls.parse_amount(opportunity.get("award_floor") or opportunity.get("awardFloor"))
        amount_max = cls.parse_amount(opportunity.get("award_ceiling") or opportunity.get("awardCeiling"))

        # Parse dates - handle various field names
        deadline = cls.parse_date(
            opportunity.get("close_date") or opportunity.get("closeDate") or opportunity.get("applicationsDueDate")
        )
        posted_date = cls.parse_date(opportunity.get("posted_date") or opportunity.get("postedDate"))

        # Get agency
        agency_name = (
            opportunity.get("agency_name")
            or opportunity.get("agencyName")
            or opportunity.get("agency_code")
            or opportunity.get("agencyCode")
            or "Unknown Agency"
        )
        agency = cls.normalize_agency(agency_name)

        # Build eligibility
        eligible_applicants = opportunity.get("eligible_applicants") or opportunity.get("eligibleApplicants")
        eligibility = None
        if eligible_applicants:
            if isinstance(eligible_applicants, list):
                eligibility = {"applicant_types": eligible_applicants}
            else:
                eligibility = {"applicant_types": [eligible_applicants]}

        # Extract categories
        categories = cls.extract_categories(
            keywords=",".join(opportunity.get("cfda_numbers", []) or []),
            program_name=opportunity.get("category_of_funding") or opportunity.get("categoryOfFunding"),
            description=opportunity.get("description") or opportunity.get("synopsis"),
        )

        # Build URL
        opp_id = opportunity.get("opportunity_id") or opportunity.get("opportunityId")
        url = f"https://www.grants.gov/search-results-detail/{opp_id}" if opp_id else None

        return {
            "external_id": opp_id,
            "source": "grants_gov",
            "title": cls.clean_text(
                opportunity.get("title") or opportunity.get("opportunityTitle") or opportunity.get("opportunity_title")
            ),
            "description": cls.clean_text(opportunity.get("description") or opportunity.get("synopsis")),
            "agency": agency,
            "amount_min": amount_min,
            "amount_max": amount_max,
            "deadline": deadline,
            "posted_at": posted_date,
            "url": url,
            "categories": categories,
            "eligibility": eligibility,
            "raw_data": opportunity,
        }
