"""
CV Parser Service
Extract profile information from CV/resume PDFs using basic text extraction.
No AI required - uses regex patterns and keyword matching.
"""

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_content: bytes) -> Optional[str]:
    """
    Extract text from PDF content using PyMuPDF (fitz).

    Args:
        pdf_content: Raw PDF bytes

    Returns:
        Extracted text or None if extraction fails
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF (fitz) not installed. Install with: pip install pymupdf")
        return None

    try:
        # Open PDF from bytes
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        text_parts = []

        for page in doc:
            text_parts.append(page.get_text())

        doc.close()
        return "\n".join(text_parts)

    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return None


def extract_email(text: str) -> Optional[str]:
    """Extract email address from text."""
    email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    match = re.search(email_pattern, text)
    return match.group(0) if match else None


def extract_name(text: str) -> Optional[str]:
    """
    Extract name from CV text.
    Assumes name is at the beginning, before contact info.
    """
    lines = text.strip().split("\n")

    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        # Skip empty lines and common headers
        if not line or len(line) < 3:
            continue
        if any(
            skip in line.lower()
            for skip in ["curriculum vitae", "cv", "resume", "email", "phone", "address", "http", "www.", "@"]
        ):
            continue

        # Check if it looks like a name (2-4 capitalized words)
        words = line.split()
        if 2 <= len(words) <= 5:
            if all(w[0].isupper() for w in words if w.isalpha()):
                return line

    return None


def extract_institution(text: str) -> Optional[str]:
    """Extract current institution from CV."""
    institution_patterns = [
        r"(?:University|Institute|College|School|Laboratory|Lab)\s+(?:of\s+)?[\w\s]+",
        r"(?:MIT|Stanford|Harvard|Yale|Princeton|Berkeley|Caltech|UCLA|UCSD)",
    ]

    text_lower = text.lower()

    # Look for institution near common markers
    markers = ["affiliation", "institution", "department", "current position"]
    for marker in markers:
        idx = text_lower.find(marker)
        if idx != -1:
            # Search in nearby text
            nearby = text[max(0, idx - 50) : idx + 200]
            for pattern in institution_patterns:
                match = re.search(pattern, nearby, re.IGNORECASE)
                if match:
                    return match.group(0).strip()

    # Fallback: find any university mention
    for pattern in institution_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    return None


def extract_research_interests(text: str) -> list[str]:
    """
    Extract research interests/areas from CV.
    Looks for common section headers and extracts keywords.
    """
    research_areas = set()

    # Common section headers for research interests
    section_headers = [
        r"research\s+(?:interests?|areas?|focus)",
        r"areas?\s+of\s+(?:interest|expertise|specialization)",
        r"expertise",
        r"specialization",
        r"research\s+summary",
    ]

    text_lower = text.lower()

    # Find sections and extract content
    for header_pattern in section_headers:
        match = re.search(header_pattern, text_lower)
        if match:
            # Extract text after header until next section (capitalized line or double newline)
            start = match.end()
            section_text = text[start : start + 500]

            # Extract bullet points or comma-separated items
            items = re.split(r"[•\-\n,;]", section_text)
            for item in items:
                item = item.strip()
                if 3 <= len(item) <= 100 and not item[0].isdigit():
                    # Clean up
                    item = re.sub(r"\s+", " ", item)
                    if item and not any(c.isdigit() for c in item[:3]):
                        research_areas.add(item.lower())

    # Also extract from common research keywords anywhere in text
    common_fields = [
        "machine learning",
        "artificial intelligence",
        "deep learning",
        "natural language processing",
        "computer vision",
        "data science",
        "bioinformatics",
        "genomics",
        "proteomics",
        "computational biology",
        "cancer research",
        "immunology",
        "neuroscience",
        "genetics",
        "molecular biology",
        "cell biology",
        "biochemistry",
        "pharmacology",
        "epidemiology",
        "public health",
        "clinical research",
        "climate science",
        "environmental science",
        "ecology",
        "materials science",
        "nanotechnology",
        "quantum computing",
        "physics",
        "chemistry",
        "mathematics",
        "statistics",
        "psychology",
        "cognitive science",
        "behavioral science",
        "economics",
        "sociology",
        "political science",
    ]

    for field in common_fields:
        if field in text_lower:
            research_areas.add(field)

    return [area.title() for area in list(research_areas)[:15]]


def extract_methods(text: str) -> list[str]:
    """Extract research methods/techniques from CV."""
    methods = set()

    # Common research methods and techniques
    method_keywords = [
        "statistical analysis",
        "regression analysis",
        "machine learning",
        "deep learning",
        "neural networks",
        "nlp",
        "computer vision",
        "survey research",
        "interview methods",
        "ethnography",
        "case study",
        "experimental design",
        "randomized controlled trial",
        "rct",
        "meta-analysis",
        "systematic review",
        "literature review",
        "simulation",
        "computational modeling",
        "mathematical modeling",
        "quantitative methods",
        "qualitative methods",
        "mixed methods",
        "dna sequencing",
        "rna sequencing",
        "mass spectrometry",
        "microscopy",
        "spectroscopy",
        "chromatography",
        "hplc",
        "pcr",
        "qpcr",
        "rt-pcr",
        "elisa",
        "western blot",
        "flow cytometry",
        "crispr",
        "gene editing",
        "cell culture",
        "animal models",
        "clinical trials",
        "cohort study",
        "cross-sectional study",
        "longitudinal study",
        "time series analysis",
        "python",
        "r programming",
        "matlab",
        "spss",
        "stata",
    ]

    text_lower = text.lower()

    for method in method_keywords:
        if method in text_lower:
            methods.add(method)

    return [m.title() for m in list(methods)[:12]]


def extract_publications(text: str) -> list[dict]:
    """
    Extract publications from CV.
    Looks for publication section and parses entries.
    """
    publications = []

    # Find publications section
    pub_headers = [
        r"publications?",
        r"selected\s+publications?",
        r"peer[- ]reviewed\s+publications?",
        r"journal\s+articles?",
        r"papers",
    ]

    text_lower = text.lower()
    pub_start = -1

    for header in pub_headers:
        match = re.search(header, text_lower)
        if match:
            pub_start = match.end()
            break

    if pub_start == -1:
        return publications

    # Extract text until next major section
    pub_section = text[pub_start : pub_start + 5000]

    # Find next section header to limit extraction
    next_section = re.search(
        r"\n\s*(?:grants?|funding|awards?|teaching|service|education|experience)\s*\n", pub_section.lower()
    )
    if next_section:
        pub_section = pub_section[: next_section.start()]

    # Extract individual publications
    # Look for patterns like:
    # - Author, A., Author, B. (Year). Title. Journal.
    # - 1. Title...
    # - • Title...

    # Split by common delimiters
    entries = re.split(r"(?:\n\s*(?:\d+\.|\•|\-)\s*|\n{2,})", pub_section)

    for entry in entries[:20]:  # Limit to 20
        entry = entry.strip()
        if len(entry) < 20:
            continue

        # Try to extract year
        year_match = re.search(r"\(?(19|20)\d{2}\)?", entry)
        year = int(year_match.group(0).strip("()")) if year_match else None

        # Try to extract journal (often italicized or after period)
        journal = None
        journal_match = re.search(r"(?:Journal|Nature|Science|Cell|PNAS|PLoS|BMC|Lancet|JAMA|BMJ)[\w\s&]+", entry)
        if journal_match:
            journal = journal_match.group(0).strip()

        # Title is usually the first substantial text
        # Remove author names (usually have commas and initials)
        title = re.sub(r"^[\w\s,\.]+\(\d{4}\)\.\s*", "", entry)
        title = re.sub(r"\.\s*(?:Journal|Nature|Science).*$", "", title, flags=re.IGNORECASE)
        title = title.strip()[:200]

        if title:
            publications.append(
                {
                    "title": title,
                    "year": year,
                    "journal": journal,
                }
            )

    return publications


def extract_grants(text: str) -> list[dict]:
    """Extract grant history from CV."""
    grants = []

    # Find grants/funding section
    grant_headers = [
        r"grants?\s+(?:and\s+)?(?:funding|awards?)?",
        r"funding\s+(?:history|awards?)?",
        r"research\s+(?:grants?|funding)",
        r"sponsored\s+research",
        r"extramural\s+funding",
    ]

    text_lower = text.lower()
    grant_start = -1

    for header in grant_headers:
        match = re.search(header, text_lower)
        if match:
            grant_start = match.end()
            break

    if grant_start == -1:
        return grants

    # Extract section
    grant_section = text[grant_start : grant_start + 4000]

    # Find next section
    next_section = re.search(
        r"\n\s*(?:publications?|teaching|service|education|experience|awards?)\s*\n", grant_section.lower()
    )
    if next_section:
        grant_section = grant_section[: next_section.start()]

    # Common funders to look for
    funders = [
        "NIH",
        "NSF",
        "DOE",
        "DOD",
        "DARPA",
        "NASA",
        "USDA",
        "National Institutes of Health",
        "National Science Foundation",
        "Department of Energy",
        "Department of Defense",
        "Howard Hughes",
        "Gates Foundation",
        "Wellcome Trust",
        "American Heart Association",
        "American Cancer Society",
    ]

    # Extract entries
    entries = re.split(r"\n\s*(?:\d+\.|\•|\-)\s*|\n{2,}", grant_section)

    for entry in entries[:15]:
        entry = entry.strip()
        if len(entry) < 15:
            continue

        # Find funder
        funder = None
        for f in funders:
            if f.lower() in entry.lower():
                funder = f
                break

        # Find amount
        amount_match = re.search(r"\$[\d,]+(?:\.\d{2})?|\$[\d.]+[MK]", entry)
        amount = amount_match.group(0) if amount_match else None

        # Find years
        years = re.findall(r"(19|20)\d{2}", entry)
        start_year = int(years[0]) if years else None
        end_year = int(years[1]) if len(years) > 1 else None

        # Title is usually after role/PI designation
        title = re.sub(r"^(?:PI|Co-PI|Investigator)[:\s]*", "", entry, flags=re.IGNORECASE)
        title = re.sub(r"\$[\d,]+.*$", "", title)
        title = title.strip()[:200]

        if title and len(title) > 10:
            grants.append(
                {
                    "title": title,
                    "funder": funder,
                    "amount": amount,
                    "start_year": start_year,
                    "end_year": end_year,
                }
            )

    return grants


def extract_career_stage(text: str) -> Optional[str]:
    """Infer career stage from CV."""
    text_lower = text.lower()

    # Check for position titles
    if any(
        title in text_lower
        for title in [
            "full professor",
            "distinguished professor",
            "endowed chair",
            "department chair",
            "dean",
            "director",
        ]
    ):
        return "senior"

    if any(title in text_lower for title in ["associate professor", "senior scientist", "senior researcher"]):
        return "established"

    if any(title in text_lower for title in ["assistant professor", "research scientist", "lecturer"]):
        return "mid_career"

    if any(
        title in text_lower
        for title in [
            "postdoc",
            "post-doc",
            "postdoctoral",
            "research associate",
            "research fellow",
            "graduate student",
            "phd student",
            "phd candidate",
        ]
    ):
        return "early_career"

    return None


async def parse_cv(pdf_content: bytes) -> Optional[dict[str, Any]]:
    """
    Parse CV PDF and extract profile information.

    Args:
        pdf_content: Raw PDF file bytes

    Returns:
        Dict with extracted profile data, or None if parsing fails
    """
    # Extract text
    text = extract_text_from_pdf(pdf_content)
    if not text:
        return None

    # Extract all components
    name = extract_name(text)
    email = extract_email(text)
    institution = extract_institution(text)
    research_areas = extract_research_interests(text)
    methods = extract_methods(text)
    publications = extract_publications(text)
    grants = extract_grants(text)
    career_stage = extract_career_stage(text)

    return {
        "name": name,
        "email": email,
        "institution": institution,
        "research_areas": research_areas,
        "methods": methods,
        "publications": publications,
        "past_grants": grants,
        "career_stage": career_stage,
        "text_length": len(text),
    }
