"""
Demo/Development Seed Data Script for GrantRadar
Creates demo users, sample grants, applications, teams, and notifications.

This script is idempotent - it can be run multiple times safely.
Existing demo data will be skipped (not duplicated).

Usage:
    python -m backend.scripts.seed_data [options]

Options:
    --clean         Wipe existing demo data before seeding
    --dry-run       Print what would be seeded without making changes
    --verbose       Enable verbose output
"""
import argparse
import asyncio
import logging
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from passlib.context import CryptContext
from sqlalchemy import select, delete, and_, or_

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo user email prefixes to identify demo data
DEMO_EMAILS = [
    "admin@grantradar.com",
    "researcher@example.com",
    "team_lead@university.edu",
]

# Demo grant external ID prefix
DEMO_GRANT_PREFIX = "DEMO-GRANT-"

# Demo team name
DEMO_TEAM_NAME = "Demo Research Lab"


def get_password_hash(password: str) -> str:
    """Hash a password for storage."""
    return pwd_context.hash(password)


# =============================================================================
# Sample Grant Data
# =============================================================================

SAMPLE_GRANTS = [
    # NIH Grants - Biomedical
    {
        "source": "nih",
        "external_id": f"{DEMO_GRANT_PREFIX}NIH-001",
        "title": "Advancing Precision Medicine Through Multi-Omic Integration",
        "description": "This funding opportunity supports innovative research approaches that integrate multiple omics data types (genomics, transcriptomics, proteomics, metabolomics) to advance precision medicine. Proposals should demonstrate novel computational methods or experimental designs that leverage multi-omic data to improve disease diagnosis, prognosis, or treatment selection.",
        "agency": "National Institutes of Health",
        "amount_min": 250000,
        "amount_max": 500000,
        "deadline_days": 45,
        "categories": ["biomedical", "precision medicine", "genomics", "computational biology"],
        "eligibility": {
            "institution_types": ["university", "research_institute", "nonprofit"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university", "research_institute", "nonprofit"],
        "award_type": "grant",
        "award_duration_min_months": 24,
        "award_duration_max_months": 60,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },
    {
        "source": "nih",
        "external_id": f"{DEMO_GRANT_PREFIX}NIH-002",
        "title": "Novel Therapeutic Approaches for Alzheimer's Disease",
        "description": "The National Institute on Aging seeks proposals for innovative therapeutic interventions targeting Alzheimer's disease pathology. Research may focus on amyloid-beta clearance, tau aggregation inhibition, neuroinflammation modulation, or novel targets identified through recent genetic studies.",
        "agency": "National Institutes of Health - NIA",
        "amount_min": 500000,
        "amount_max": 2000000,
        "deadline_days": 30,
        "categories": ["biomedical", "neuroscience", "therapeutics", "aging"],
        "eligibility": {
            "institution_types": ["university", "research_institute"],
            "career_stages": ["mid_career", "senior"],
            "citizenship": ["us_citizen", "permanent_resident", "no_restriction"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["mid_career", "senior"],
        "citizenship_requirements": ["us_citizen", "permanent_resident", "no_restriction"],
        "eligible_institution_types": ["university", "research_institute"],
        "award_type": "grant",
        "award_duration_min_months": 36,
        "award_duration_max_months": 60,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },
    {
        "source": "nih",
        "external_id": f"{DEMO_GRANT_PREFIX}NIH-003",
        "title": "NIGMS R35 Maximizing Investigators' Research Award (MIRA) - Early Stage Investigators",
        "description": "MIRA provides support for the overall research program in an investigator's laboratory, rather than a specific project. This opportunity is for Early Stage Investigators who have not received substantial NIH support previously. Awards provide stable funding to encourage investigators to pursue creative research directions.",
        "agency": "National Institutes of Health - NIGMS",
        "amount_min": 250000,
        "amount_max": 250000,
        "deadline_days": 60,
        "categories": ["biomedical", "basic research"],
        "eligibility": {
            "institution_types": ["university", "research_institute"],
            "career_stages": ["early_career"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True,
            "requirements": "Must be Early Stage Investigator (within 10 years of terminal degree)"
        },
        "eligible_career_stages": ["early_career"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university", "research_institute"],
        "award_type": "grant",
        "award_duration_min_months": 60,
        "award_duration_max_months": 60,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },
    {
        "source": "nih",
        "external_id": f"{DEMO_GRANT_PREFIX}NIH-004",
        "title": "Cancer Immunotherapy Combination Strategies",
        "description": "This initiative supports research on rational combination strategies for cancer immunotherapy. Proposals should investigate combinations of immunotherapeutic agents with each other or with conventional therapies, with emphasis on understanding mechanisms of synergy and resistance.",
        "agency": "National Cancer Institute",
        "amount_min": 400000,
        "amount_max": 1500000,
        "deadline_days": 14,  # Urgent deadline
        "categories": ["biomedical", "oncology", "immunology", "therapeutics"],
        "eligibility": {
            "institution_types": ["university", "research_institute", "hospital"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["no_restriction"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["no_restriction"],
        "eligible_institution_types": ["university", "research_institute", "hospital"],
        "award_type": "grant",
        "award_duration_min_months": 36,
        "award_duration_max_months": 60,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },

    # NSF Grants - Engineering & Science
    {
        "source": "nsf",
        "external_id": f"{DEMO_GRANT_PREFIX}NSF-001",
        "title": "NSF CAREER: Faculty Early Career Development Program",
        "description": "The CAREER Program supports early-career faculty who have the potential to serve as academic role models in research and education and to lead advances in the mission of their department or organization. Activities pursued by early-career faculty should build a firm foundation for a lifetime of leadership in integrating education and research.",
        "agency": "National Science Foundation",
        "amount_min": 400000,
        "amount_max": 700000,
        "deadline_days": 90,
        "categories": ["science", "engineering", "education", "career development"],
        "eligibility": {
            "institution_types": ["university"],
            "career_stages": ["early_career"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True,
            "requirements": "Must hold tenure-track (or equivalent) position"
        },
        "eligible_career_stages": ["early_career"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university"],
        "award_type": "grant",
        "award_duration_min_months": 60,
        "award_duration_max_months": 60,
        "geographic_scope": "national",
        "is_limited_submission": True,
        "indirect_cost_policy": "full_rate",
    },
    {
        "source": "nsf",
        "external_id": f"{DEMO_GRANT_PREFIX}NSF-002",
        "title": "Artificial Intelligence for Accelerating Scientific Discovery",
        "description": "This program supports fundamental research in artificial intelligence and machine learning methods with high potential to accelerate scientific discovery across NSF-supported disciplines. Proposals should demonstrate transformative approaches that go beyond incremental improvements to existing methods.",
        "agency": "National Science Foundation",
        "amount_min": 500000,
        "amount_max": 1200000,
        "deadline_days": 75,
        "categories": ["computer science", "artificial intelligence", "machine learning"],
        "eligibility": {
            "institution_types": ["university", "research_institute"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university", "research_institute"],
        "award_type": "grant",
        "award_duration_min_months": 36,
        "award_duration_max_months": 48,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },
    {
        "source": "nsf",
        "external_id": f"{DEMO_GRANT_PREFIX}NSF-003",
        "title": "Sustainable Chemistry, Engineering and Materials (SusChEM)",
        "description": "SusChEM supports research that addresses the interrelated challenges of sustainable development in chemical processes. Projects should focus on replacing rare, expensive, or toxic reagents with earth-abundant, inexpensive, and benign alternatives; developing efficient synthetic methods; or designing sustainable materials.",
        "agency": "National Science Foundation",
        "amount_min": 200000,
        "amount_max": 450000,
        "deadline_days": 120,
        "categories": ["chemistry", "engineering", "sustainability", "materials science"],
        "eligibility": {
            "institution_types": ["university", "research_institute"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university", "research_institute"],
        "award_type": "grant",
        "award_duration_min_months": 36,
        "award_duration_max_months": 48,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },
    {
        "source": "nsf",
        "external_id": f"{DEMO_GRANT_PREFIX}NSF-004",
        "title": "Quantum Computing and Information Science",
        "description": "This initiative supports research advancing the theoretical foundations and practical implementation of quantum computing and quantum information science. Topics include quantum algorithms, error correction, hardware development, and applications to computational problems intractable for classical computers.",
        "agency": "National Science Foundation",
        "amount_min": 300000,
        "amount_max": 800000,
        "deadline_days": 7,  # Very urgent
        "categories": ["physics", "computer science", "quantum computing"],
        "eligibility": {
            "institution_types": ["university", "research_institute"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university", "research_institute"],
        "award_type": "grant",
        "award_duration_min_months": 36,
        "award_duration_max_months": 48,
        "geographic_scope": "national",
        "is_limited_submission": True,
        "indirect_cost_policy": "full_rate",
    },

    # DOE Grants - Energy
    {
        "source": "doe",
        "external_id": f"{DEMO_GRANT_PREFIX}DOE-001",
        "title": "Advanced Battery Technologies for Electric Vehicles",
        "description": "The Department of Energy seeks proposals for next-generation battery technologies that can enable widespread electric vehicle adoption. Research should focus on increasing energy density, reducing costs, improving safety, or extending cycle life of battery systems.",
        "agency": "Department of Energy",
        "amount_min": 500000,
        "amount_max": 3000000,
        "deadline_days": 55,
        "categories": ["energy", "materials science", "engineering", "transportation"],
        "eligibility": {
            "institution_types": ["university", "research_institute", "industry"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university", "research_institute", "industry"],
        "award_type": "grant",
        "award_duration_min_months": 24,
        "award_duration_max_months": 36,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },
    {
        "source": "doe",
        "external_id": f"{DEMO_GRANT_PREFIX}DOE-002",
        "title": "Nuclear Energy Advanced Concepts",
        "description": "This program supports innovative research in nuclear energy technologies, including advanced reactor designs, fuel cycle improvements, and nuclear waste management solutions. Projects should demonstrate potential for significant advances in safety, efficiency, or economics of nuclear power.",
        "agency": "Department of Energy - Office of Nuclear Energy",
        "amount_min": 400000,
        "amount_max": 2000000,
        "deadline_days": 85,
        "categories": ["energy", "nuclear", "engineering"],
        "eligibility": {
            "institution_types": ["university", "research_institute", "national_lab"],
            "career_stages": ["mid_career", "senior"],
            "citizenship": ["us_citizen"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["mid_career", "senior"],
        "citizenship_requirements": ["us_citizen"],
        "eligible_institution_types": ["university", "research_institute", "national_lab"],
        "award_type": "grant",
        "award_duration_min_months": 36,
        "award_duration_max_months": 48,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },
    {
        "source": "doe",
        "external_id": f"{DEMO_GRANT_PREFIX}DOE-003",
        "title": "Solar Energy Innovation Fund",
        "description": "Support for transformational research in photovoltaic and solar thermal technologies. Projects should address fundamental limitations in current solar energy systems and propose innovative solutions with potential for significant cost reduction or efficiency improvement.",
        "agency": "Department of Energy - Solar Energy Technologies Office",
        "amount_min": 150000,
        "amount_max": 600000,
        "deadline_days": -15,  # Past deadline
        "categories": ["energy", "solar", "materials science", "engineering"],
        "eligibility": {
            "institution_types": ["university", "research_institute", "industry", "nonprofit"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university", "research_institute", "industry", "nonprofit"],
        "award_type": "grant",
        "award_duration_min_months": 24,
        "award_duration_max_months": 36,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },

    # Foundation Grants
    {
        "source": "foundation",
        "external_id": f"{DEMO_GRANT_PREFIX}FOUND-001",
        "title": "Gates Foundation Global Health Discovery",
        "description": "The Bill & Melinda Gates Foundation supports innovative research addressing major global health challenges. Priority areas include infectious diseases affecting developing countries, maternal and child health, and vaccine development.",
        "agency": "Bill & Melinda Gates Foundation",
        "amount_min": 100000,
        "amount_max": 2000000,
        "deadline_days": 100,
        "categories": ["global health", "infectious disease", "vaccines", "public health"],
        "eligibility": {
            "institution_types": ["university", "research_institute", "nonprofit", "government"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["no_restriction"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["no_restriction"],
        "eligible_institution_types": ["university", "research_institute", "nonprofit", "government"],
        "award_type": "grant",
        "award_duration_min_months": 24,
        "award_duration_max_months": 48,
        "geographic_scope": "international",
        "is_limited_submission": False,
        "indirect_cost_policy": "capped",
    },
    {
        "source": "foundation",
        "external_id": f"{DEMO_GRANT_PREFIX}FOUND-002",
        "title": "Howard Hughes Medical Institute Early Career Scientist Program",
        "description": "HHMI selects outstanding early-career scientists and provides substantial, flexible funding to support their research programs. Investigators are chosen based on their potential to make significant contributions to science.",
        "agency": "Howard Hughes Medical Institute",
        "amount_min": 800000,
        "amount_max": 5000000,
        "deadline_days": 180,
        "categories": ["biomedical", "basic research", "career development"],
        "eligibility": {
            "institution_types": ["university", "research_institute"],
            "career_stages": ["early_career"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True,
            "requirements": "Faculty position for 2-7 years, exceptional scientific track record"
        },
        "eligible_career_stages": ["early_career"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university", "research_institute"],
        "award_type": "fellowship",
        "award_duration_min_months": 60,
        "award_duration_max_months": 84,
        "geographic_scope": "national",
        "is_limited_submission": True,
        "indirect_cost_policy": "capped",
    },
    {
        "source": "foundation",
        "external_id": f"{DEMO_GRANT_PREFIX}FOUND-003",
        "title": "Sloan Research Fellowships",
        "description": "The Sloan Research Fellowships seek to stimulate fundamental research by early-career scientists and scholars of outstanding promise. Candidates must be tenure-track faculty at a U.S. or Canadian institution and must hold a Ph.D. or equivalent degree.",
        "agency": "Alfred P. Sloan Foundation",
        "amount_min": 75000,
        "amount_max": 75000,
        "deadline_days": 150,
        "categories": ["science", "basic research", "career development"],
        "eligibility": {
            "institution_types": ["university"],
            "career_stages": ["early_career"],
            "citizenship": ["us_citizen", "permanent_resident", "visa_holder"],
            "pi_eligible": True,
            "requirements": "Tenure-track position, within 6 years of Ph.D."
        },
        "eligible_career_stages": ["early_career"],
        "citizenship_requirements": ["us_citizen", "permanent_resident", "visa_holder"],
        "eligible_institution_types": ["university"],
        "award_type": "fellowship",
        "award_duration_min_months": 24,
        "award_duration_max_months": 24,
        "geographic_scope": "national",
        "is_limited_submission": True,
        "indirect_cost_policy": "not_allowed",
    },
    {
        "source": "foundation",
        "external_id": f"{DEMO_GRANT_PREFIX}FOUND-004",
        "title": "Simons Foundation Collaboration Grants for Mathematicians",
        "description": "Collaboration Grants provide funds to mathematicians at U.S. institutions to foster collaborations with colleagues, especially those far from their home institution. Funds may be used for travel and collaboration.",
        "agency": "Simons Foundation",
        "amount_min": 8400,
        "amount_max": 42000,
        "deadline_days": 45,
        "categories": ["mathematics", "basic research"],
        "eligibility": {
            "institution_types": ["university"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["no_restriction"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["no_restriction"],
        "eligible_institution_types": ["university"],
        "award_type": "grant",
        "award_duration_min_months": 60,
        "award_duration_max_months": 60,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "not_allowed",
    },

    # State Grants
    {
        "source": "state",
        "external_id": f"{DEMO_GRANT_PREFIX}STATE-001",
        "title": "California Climate Action Research Program",
        "description": "California funds research supporting state climate goals. Projects should address greenhouse gas reduction, climate adaptation, or resilience strategies relevant to California communities and ecosystems.",
        "agency": "California Air Resources Board",
        "amount_min": 100000,
        "amount_max": 500000,
        "deadline_days": 65,
        "categories": ["climate", "environmental science", "policy"],
        "eligibility": {
            "institution_types": ["university", "research_institute", "nonprofit"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["no_restriction"],
            "pi_eligible": True,
            "requirements": "Research must benefit California"
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["no_restriction"],
        "eligible_institution_types": ["university", "research_institute", "nonprofit"],
        "award_type": "grant",
        "award_duration_min_months": 24,
        "award_duration_max_months": 36,
        "geographic_scope": "state",
        "geographic_regions": ["California"],
        "is_limited_submission": False,
        "indirect_cost_policy": "capped",
    },
    {
        "source": "state",
        "external_id": f"{DEMO_GRANT_PREFIX}STATE-002",
        "title": "New York State Health Research Science Board",
        "description": "The Empire State Stem Cell Fund supports stem cell research and regenerative medicine in New York. Projects should advance basic or translational stem cell research with potential therapeutic applications.",
        "agency": "New York State Department of Health",
        "amount_min": 200000,
        "amount_max": 750000,
        "deadline_days": 21,
        "categories": ["biomedical", "stem cells", "regenerative medicine"],
        "eligibility": {
            "institution_types": ["university", "research_institute", "hospital"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["no_restriction"],
            "pi_eligible": True,
            "requirements": "Institution must be in New York State"
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["no_restriction"],
        "eligible_institution_types": ["university", "research_institute", "hospital"],
        "award_type": "grant",
        "award_duration_min_months": 24,
        "award_duration_max_months": 36,
        "geographic_scope": "state",
        "geographic_regions": ["New York"],
        "is_limited_submission": False,
        "indirect_cost_policy": "capped",
    },

    # Social Sciences
    {
        "source": "foundation",
        "external_id": f"{DEMO_GRANT_PREFIX}SOC-001",
        "title": "Russell Sage Foundation Social Inequality Research",
        "description": "The foundation supports rigorous empirical research on the causes and consequences of social inequality in the United States. Projects may address economic inequality, racial disparities, immigration, or related topics.",
        "agency": "Russell Sage Foundation",
        "amount_min": 50000,
        "amount_max": 175000,
        "deadline_days": 110,
        "categories": ["social sciences", "economics", "sociology", "policy"],
        "eligibility": {
            "institution_types": ["university", "research_institute", "nonprofit"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["no_restriction"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["no_restriction"],
        "eligible_institution_types": ["university", "research_institute", "nonprofit"],
        "award_type": "grant",
        "award_duration_min_months": 12,
        "award_duration_max_months": 24,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "capped",
    },
    {
        "source": "nsf",
        "external_id": f"{DEMO_GRANT_PREFIX}SOC-002",
        "title": "NSF Social, Behavioral and Economic Sciences Directorate",
        "description": "Support for fundamental research to advance understanding of human behavior, social and economic systems, and organizations. Projects may employ quantitative, qualitative, or mixed methods approaches.",
        "agency": "National Science Foundation - SBE",
        "amount_min": 100000,
        "amount_max": 350000,
        "deadline_days": -30,  # Past deadline
        "categories": ["social sciences", "behavioral science", "economics"],
        "eligibility": {
            "institution_types": ["university", "research_institute"],
            "career_stages": ["early_career", "mid_career", "senior"],
            "citizenship": ["us_citizen", "permanent_resident"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "mid_career", "senior"],
        "citizenship_requirements": ["us_citizen", "permanent_resident"],
        "eligible_institution_types": ["university", "research_institute"],
        "award_type": "grant",
        "award_duration_min_months": 24,
        "award_duration_max_months": 36,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "full_rate",
    },

    # Small/Pilot Grants
    {
        "source": "foundation",
        "external_id": f"{DEMO_GRANT_PREFIX}PILOT-001",
        "title": "Pilot Project Awards for Junior Investigators",
        "description": "Small pilot grants to support preliminary studies that will generate data for larger grant applications. Ideal for junior faculty establishing independent research programs.",
        "agency": "Research Foundation",
        "amount_min": 10000,
        "amount_max": 25000,
        "deadline_days": 35,
        "categories": ["pilot study", "junior investigator", "seed funding"],
        "eligibility": {
            "institution_types": ["university"],
            "career_stages": ["early_career", "postdoc"],
            "citizenship": ["no_restriction"],
            "pi_eligible": True
        },
        "eligible_career_stages": ["early_career", "postdoc"],
        "citizenship_requirements": ["no_restriction"],
        "eligible_institution_types": ["university"],
        "award_type": "grant",
        "award_duration_min_months": 12,
        "award_duration_max_months": 18,
        "geographic_scope": "national",
        "is_limited_submission": False,
        "indirect_cost_policy": "not_allowed",
    },
]


# =============================================================================
# Demo User Data
# =============================================================================

DEMO_USERS = [
    {
        "email": "admin@grantradar.com",
        "password": "DemoAdmin123!",
        "name": "Dr. Sarah Mitchell",
        "institution": "Stanford University",
        "phone": "+1-650-555-0101",
        "role": "admin",
        "lab_profile": {
            "research_areas": ["biomedical engineering", "drug delivery", "nanotechnology"],
            "methods": ["nanoparticle synthesis", "cell culture", "in vivo imaging"],
            "career_stage": "senior",
            "citizenship_status": "us_citizen",
            "institution_type": "r1_university",
            "is_pi_eligible": True,
            "institution": "Stanford University",
            "department": "Bioengineering",
            "keywords": ["nanomedicine", "targeted therapy", "cancer treatment"],
        }
    },
    {
        "email": "researcher@example.com",
        "password": "DemoResearch123!",
        "name": "Dr. James Chen",
        "institution": "MIT",
        "phone": "+1-617-555-0102",
        "role": "user",
        "lab_profile": {
            "research_areas": ["machine learning", "computer vision", "medical imaging"],
            "methods": ["deep learning", "image analysis", "clinical validation"],
            "career_stage": "early_career",
            "citizenship_status": "permanent_resident",
            "institution_type": "r1_university",
            "is_pi_eligible": True,
            "institution": "MIT",
            "department": "Computer Science and Artificial Intelligence Laboratory",
            "keywords": ["AI diagnostics", "radiology AI", "neural networks"],
        }
    },
    {
        "email": "team_lead@university.edu",
        "password": "DemoTeamLead123!",
        "name": "Dr. Maria Rodriguez",
        "institution": "UC Berkeley",
        "phone": "+1-510-555-0103",
        "role": "team_admin",
        "lab_profile": {
            "research_areas": ["climate science", "environmental engineering", "sustainability"],
            "methods": ["climate modeling", "field studies", "data analysis"],
            "career_stage": "mid_career",
            "citizenship_status": "us_citizen",
            "institution_type": "r1_university",
            "is_pi_eligible": True,
            "institution": "UC Berkeley",
            "department": "Environmental Science, Policy, and Management",
            "keywords": ["climate change", "carbon sequestration", "ecosystem services"],
        }
    },
]


# =============================================================================
# Seeding Functions
# =============================================================================

async def clean_demo_data(session, dry_run: bool = False) -> dict:
    """Remove all demo data from the database."""
    from backend.models import (
        User, Grant, GrantApplication, Match, LabProfile,
        LabMember, TeamActivityLog, Notification, ApplicationActivity
    )

    counts = {
        "users": 0,
        "grants": 0,
        "applications": 0,
        "matches": 0,
        "lab_profiles": 0,
        "lab_members": 0,
        "team_activity_logs": 0,
        "notifications": 0,
    }

    if dry_run:
        # Count what would be deleted
        for email in DEMO_EMAILS:
            result = await session.execute(select(User).where(User.email == email))
            if result.scalar_one_or_none():
                counts["users"] += 1

        result = await session.execute(
            select(Grant).where(Grant.external_id.startswith(DEMO_GRANT_PREFIX))
        )
        counts["grants"] = len(result.scalars().all())

        logger.info(f"[DRY RUN] Would delete: {counts}")
        return counts

    # Delete demo grants (cascades to matches, applications)
    result = await session.execute(
        select(Grant).where(Grant.external_id.startswith(DEMO_GRANT_PREFIX))
    )
    demo_grants = result.scalars().all()
    counts["grants"] = len(demo_grants)
    for grant in demo_grants:
        await session.delete(grant)

    # Delete demo users (cascades to profiles, matches, applications, notifications, etc.)
    for email in DEMO_EMAILS:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            counts["users"] += 1
            await session.delete(user)

    await session.commit()
    logger.info(f"Cleaned demo data: {counts}")
    return counts


async def seed_demo_users(session, dry_run: bool = False) -> list:
    """Create demo users with lab profiles."""
    from backend.models import User, LabProfile

    created_users = []

    for user_data in DEMO_USERS:
        # Check if user already exists
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"  User {user_data['email']} already exists, skipping")
            created_users.append(existing)
            continue

        if dry_run:
            logger.info(f"  [DRY RUN] Would create user: {user_data['email']}")
            continue

        # Create user
        user = User(
            email=user_data["email"],
            password_hash=get_password_hash(user_data["password"]),
            name=user_data["name"],
            institution=user_data["institution"],
            phone=user_data.get("phone"),
            email_notifications=True,
            sms_notifications=False,
            digest_frequency="daily",
            minimum_match_score=0.6,
        )
        session.add(user)
        await session.flush()
        await session.refresh(user)

        # Create lab profile
        profile_data = user_data.get("lab_profile", {})
        lab_profile = LabProfile(
            user_id=user.id,
            research_areas=profile_data.get("research_areas", []),
            methods=profile_data.get("methods", []),
            career_stage=profile_data.get("career_stage"),
            citizenship_status=profile_data.get("citizenship_status"),
            institution_type=profile_data.get("institution_type"),
            is_pi_eligible=profile_data.get("is_pi_eligible", False),
            institution=profile_data.get("institution"),
            department=profile_data.get("department"),
            keywords=profile_data.get("keywords", []),
        )
        session.add(lab_profile)

        created_users.append(user)
        logger.info(f"  Created user: {user.email}")

    if not dry_run:
        await session.commit()

    return created_users


async def seed_demo_grants(session, dry_run: bool = False) -> list:
    """Create sample grants."""
    from backend.models import Grant

    created_grants = []
    now = datetime.now(timezone.utc)

    for grant_data in SAMPLE_GRANTS:
        # Check if grant already exists
        result = await session.execute(
            select(Grant).where(Grant.external_id == grant_data["external_id"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"  Grant {grant_data['external_id']} already exists, skipping")
            created_grants.append(existing)
            continue

        if dry_run:
            logger.info(f"  [DRY RUN] Would create grant: {grant_data['title'][:50]}...")
            continue

        # Calculate deadline
        deadline_days = grant_data.pop("deadline_days", 30)
        deadline = now + timedelta(days=deadline_days)

        grant = Grant(
            source=grant_data["source"],
            external_id=grant_data["external_id"],
            title=grant_data["title"],
            description=grant_data["description"],
            agency=grant_data["agency"],
            amount_min=grant_data.get("amount_min"),
            amount_max=grant_data.get("amount_max"),
            deadline=deadline,
            posted_at=now - timedelta(days=30),  # Posted 30 days ago
            url=f"https://grants.example.com/{grant_data['external_id']}",
            eligibility=grant_data.get("eligibility"),
            categories=grant_data.get("categories"),
            eligible_career_stages=grant_data.get("eligible_career_stages"),
            citizenship_requirements=grant_data.get("citizenship_requirements"),
            eligible_institution_types=grant_data.get("eligible_institution_types"),
            award_type=grant_data.get("award_type"),
            award_duration_min_months=grant_data.get("award_duration_min_months"),
            award_duration_max_months=grant_data.get("award_duration_max_months"),
            geographic_scope=grant_data.get("geographic_scope"),
            geographic_regions=grant_data.get("geographic_regions"),
            is_limited_submission=grant_data.get("is_limited_submission", False),
            indirect_cost_policy=grant_data.get("indirect_cost_policy"),
        )
        session.add(grant)
        created_grants.append(grant)

    if not dry_run:
        await session.flush()
        for grant in created_grants:
            if grant.id:
                await session.refresh(grant)
        await session.commit()
        logger.info(f"  Created {len([g for g in created_grants if g.id])} grants")

    return created_grants


async def seed_demo_applications(session, users: list, grants: list, dry_run: bool = False) -> list:
    """Create sample applications in different stages."""
    from backend.models import GrantApplication, Match, ApplicationActivity, ApplicationStage

    if dry_run:
        logger.info("  [DRY RUN] Would create sample applications")
        return []

    if not users or not grants:
        logger.warning("  No users or grants available for applications")
        return []

    created_apps = []
    now = datetime.now(timezone.utc)

    # Application configurations for each user
    app_configs = [
        # User 1 (admin) - various stages
        {"user_idx": 0, "grant_idx": 0, "stage": ApplicationStage.RESEARCHING, "priority": "high", "match_score": 0.92},
        {"user_idx": 0, "grant_idx": 1, "stage": ApplicationStage.WRITING, "priority": "high", "match_score": 0.85},
        {"user_idx": 0, "grant_idx": 2, "stage": ApplicationStage.SUBMITTED, "priority": "medium", "match_score": 0.78},
        {"user_idx": 0, "grant_idx": 3, "stage": ApplicationStage.AWARDED, "priority": "high", "match_score": 0.88},

        # User 2 (researcher) - focused on AI grants
        {"user_idx": 1, "grant_idx": 5, "stage": ApplicationStage.RESEARCHING, "priority": "high", "match_score": 0.95},
        {"user_idx": 1, "grant_idx": 7, "stage": ApplicationStage.WRITING, "priority": "high", "match_score": 0.82},
        {"user_idx": 1, "grant_idx": 0, "stage": ApplicationStage.RESEARCHING, "priority": "medium", "match_score": 0.75},

        # User 3 (team lead) - climate/environment focused
        {"user_idx": 2, "grant_idx": 16, "stage": ApplicationStage.WRITING, "priority": "high", "match_score": 0.90},
        {"user_idx": 2, "grant_idx": 8, "stage": ApplicationStage.RESEARCHING, "priority": "medium", "match_score": 0.72},
        {"user_idx": 2, "grant_idx": 10, "stage": ApplicationStage.SUBMITTED, "priority": "high", "match_score": 0.80},
    ]

    for config in app_configs:
        if config["user_idx"] >= len(users) or config["grant_idx"] >= len(grants):
            continue

        user = users[config["user_idx"]]
        grant = grants[config["grant_idx"]]

        if not user.id or not grant.id:
            continue

        # Check if application already exists
        result = await session.execute(
            select(GrantApplication).where(
                and_(
                    GrantApplication.user_id == user.id,
                    GrantApplication.grant_id == grant.id
                )
            )
        )
        if result.scalar_one_or_none():
            continue

        # Create match first
        match = Match(
            grant_id=grant.id,
            user_id=user.id,
            match_score=config["match_score"],
            vector_similarity=config["match_score"] - 0.05,
            llm_match_score=config["match_score"] * 100,
            reasoning=f"Strong alignment between researcher's expertise and grant focus areas. Good fit for {grant.agency} funding priorities.",
            key_strengths=["Research area alignment", "Strong methodology fit", "Appropriate career stage"],
            concerns=["Competitive funding cycle", "Timeline may be tight"],
            predicted_success=config["match_score"] * 0.85,
            user_action="saved",
        )
        session.add(match)
        await session.flush()
        await session.refresh(match)

        # Create application
        app = GrantApplication(
            user_id=user.id,
            grant_id=grant.id,
            match_id=match.id,
            stage=config["stage"],
            notes=f"Working on application for {grant.title[:50]}...",
            target_date=grant.deadline - timedelta(days=7) if grant.deadline else None,
            priority=config["priority"],
            position=len(created_apps),
        )
        session.add(app)
        await session.flush()
        await session.refresh(app)

        # Create activity entry
        activity = ApplicationActivity(
            application_id=app.id,
            user_id=user.id,
            action="created",
            details={"initial_stage": config["stage"].value},
        )
        session.add(activity)

        created_apps.append(app)

    await session.commit()
    logger.info(f"  Created {len(created_apps)} applications with matches")
    return created_apps


async def seed_demo_team(session, users: list, dry_run: bool = False) -> dict:
    """Create sample team (Demo Research Lab) with members."""
    from backend.models import LabMember, TeamActivityLog

    if dry_run:
        logger.info("  [DRY RUN] Would create demo team")
        return {}

    if len(users) < 3:
        logger.warning("  Not enough users for team setup")
        return {}

    result = {
        "members": [],
        "activities": [],
    }

    # User 3 (team_lead) is the lab owner
    team_lead = users[2]
    if not team_lead.id:
        return result

    # Add other users as team members
    member_configs = [
        {"user": users[0], "role": "admin"},
        {"user": users[1], "role": "member"},
    ]

    for config in member_configs:
        member_user = config["user"]
        if not member_user.id:
            continue

        # Check if already a member
        result_check = await session.execute(
            select(LabMember).where(
                and_(
                    LabMember.lab_owner_id == team_lead.id,
                    LabMember.member_email == member_user.email
                )
            )
        )
        if result_check.scalar_one_or_none():
            continue

        # Create lab member
        member = LabMember(
            lab_owner_id=team_lead.id,
            member_email=member_user.email,
            member_user_id=member_user.id,
            role=config["role"],
            invitation_status="accepted",
            accepted_at=datetime.now(timezone.utc) - timedelta(days=30),
            permissions={
                "can_view": True,
                "can_edit": config["role"] == "admin",
                "can_create": config["role"] == "admin",
                "can_delete": False,
                "can_invite": config["role"] == "admin",
            }
        )
        session.add(member)
        result["members"].append(member)

        # Create team activity log
        activity = TeamActivityLog(
            lab_owner_id=team_lead.id,
            actor_id=team_lead.id,
            action_type="member_joined",
            entity_type="member",
            entity_name=member_user.name,
            metadata_={"role": config["role"], "email": member_user.email}
        )
        session.add(activity)
        result["activities"].append(activity)

    await session.commit()
    logger.info(f"  Created team with {len(result['members'])} members")
    return result


async def seed_demo_notifications(session, users: list, dry_run: bool = False) -> list:
    """Create sample notifications for demo users."""
    from backend.models import Notification

    if dry_run:
        logger.info("  [DRY RUN] Would create sample notifications")
        return []

    if not users:
        return []

    notifications = []
    now = datetime.now(timezone.utc)

    notification_configs = [
        # For admin user
        {
            "user_idx": 0,
            "type": "grant_match",
            "title": "New Grant Match: 92% compatibility",
            "message": "A new NIH grant opportunity matches your research profile with 92% compatibility. Review it now.",
            "read": False,
            "action_url": "/grants",
        },
        {
            "user_idx": 0,
            "type": "deadline_reminder",
            "title": "Deadline in 14 days",
            "message": "The NIH R01 application deadline is in 14 days. Make sure to complete your submission.",
            "read": True,
            "action_url": "/deadlines",
        },
        # For researcher
        {
            "user_idx": 1,
            "type": "grant_match",
            "title": "New Grant Match: AI Research",
            "message": "NSF Artificial Intelligence program matches your ML expertise. 95% match score.",
            "read": False,
            "action_url": "/grants",
        },
        {
            "user_idx": 1,
            "type": "team_invite",
            "title": "Team Invitation",
            "message": "Dr. Maria Rodriguez has invited you to join Demo Research Lab.",
            "read": True,
            "action_url": "/team",
        },
        # For team lead
        {
            "user_idx": 2,
            "type": "member_joined",
            "title": "New Team Member",
            "message": "Dr. James Chen has accepted your team invitation.",
            "read": True,
            "action_url": "/team",
        },
        {
            "user_idx": 2,
            "type": "application_update",
            "title": "Application Status Update",
            "message": "Your California Climate Action application has moved to 'Submitted' stage.",
            "read": False,
            "action_url": "/applications",
        },
    ]

    for config in notification_configs:
        if config["user_idx"] >= len(users):
            continue

        user = users[config["user_idx"]]
        if not user.id:
            continue

        notif = Notification(
            user_id=user.id,
            type=config["type"],
            title=config["title"],
            message=config["message"],
            read=config["read"],
            read_at=now - timedelta(hours=2) if config["read"] else None,
            action_url=config["action_url"],
        )
        session.add(notif)
        notifications.append(notif)

    await session.commit()
    logger.info(f"  Created {len(notifications)} notifications")
    return notifications


# =============================================================================
# Main Execution
# =============================================================================

async def run_seed(clean: bool = False, dry_run: bool = False, verbose: bool = False):
    """Run the complete seed process."""
    from backend.database import get_async_session

    print("\n" + "=" * 60)
    print("GrantRadar Demo Data Seeding")
    print("=" * 60)

    if dry_run:
        print("\n[DRY RUN MODE - No changes will be made]\n")

    async with get_async_session() as session:
        # Step 1: Clean existing demo data if requested
        if clean:
            print("\n[Step 1/5] Cleaning existing demo data...")
            await clean_demo_data(session, dry_run)
        else:
            print("\n[Step 1/5] Skipping cleanup (use --clean to wipe first)")

        # Step 2: Create demo users
        print("\n[Step 2/5] Creating demo users...")
        users = await seed_demo_users(session, dry_run)
        print(f"  Demo users: {len(users)}")

        # Step 3: Create sample grants
        print("\n[Step 3/5] Creating sample grants...")
        grants = await seed_demo_grants(session, dry_run)
        print(f"  Sample grants: {len(grants)}")

        # Step 4: Create sample applications
        print("\n[Step 4/5] Creating sample applications...")
        apps = await seed_demo_applications(session, users, grants, dry_run)
        print(f"  Sample applications: {len(apps)}")

        # Step 5: Create team and notifications
        print("\n[Step 5/5] Creating team and notifications...")
        team = await seed_demo_team(session, users, dry_run)
        notifications = await seed_demo_notifications(session, users, dry_run)
        print(f"  Team members: {len(team.get('members', []))}")
        print(f"  Notifications: {len(notifications)}")

    # Summary
    print("\n" + "=" * 60)
    print("SEEDING SUMMARY")
    print("=" * 60)
    print(f"\nDemo Users Created: {len(users)}")
    for user_data in DEMO_USERS:
        print(f"  - {user_data['email']} (password: {user_data['password']})")
    print(f"\nSample Grants: {len(grants)}")
    print(f"Sample Applications: {len(apps)}")
    print(f"Team Members: {len(team.get('members', []))}")
    print(f"Notifications: {len(notifications)}")
    print("\n" + "=" * 60)

    if not dry_run:
        print("\nDemo data seeded successfully!")
        print("\nYou can now log in with any demo user account.")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Seed the GrantRadar database with demo/development data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m backend.scripts.seed_data              # Seed demo data
  python -m backend.scripts.seed_data --clean      # Wipe and re-seed
  python -m backend.scripts.seed_data --dry-run    # Preview what would be seeded
        """
    )
    parser.add_argument(
        "--clean", "-c",
        action="store_true",
        help="Wipe existing demo data before seeding"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Print what would be seeded without making changes"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        asyncio.run(run_seed(
            clean=args.clean,
            dry_run=args.dry_run,
            verbose=args.verbose
        ))
    except KeyboardInterrupt:
        print("\n\nSeeding interrupted by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Seeding failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
