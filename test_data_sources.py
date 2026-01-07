#!/usr/bin/env python3
"""
Test script to verify all grant data sources are working.
Tests data fetching and parsing without requiring Redis/Docker.
"""

import asyncio
import io
import sys
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx


async def test_nsf_api():
    """Test NSF Award Search API."""
    print("\n" + "="*60)
    print("Testing NSF Award Search API")
    print("="*60)

    api_url = "https://www.research.gov/awardapi-service/v1/awards.json"

    params = {
        "dateStart": "01/01/2025",
        "dateEnd": datetime.now().strftime("%m/%d/%Y"),
        "rpp": 5,  # 5 results for test
        "printFields": "id,title,abstractText,fundsObligatedAmt,agency,startDate,expDate",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(api_url, params=params)
            response.raise_for_status()

            data = response.json()
            awards = data.get("response", {}).get("award", [])
            total = data.get("response", {}).get("metadata", {}).get("totalCount", 0)

            print(f"[OK] API returned {total} total awards")
            print(f"[OK] Fetched {len(awards)} sample awards")

            for award in awards[:3]:
                print(f"  - {award.get('id')}: {award.get('title', 'N/A')[:50]}...")
                print(f"    Amount: ${award.get('fundsObligatedAmt', 'N/A')}")

            return True

        except Exception as e:
            print(f"[FAILED] {type(e).__name__}: {e}")
            return False


async def test_grants_gov_xml():
    """Test Grants.gov XML Extract download and parsing."""
    print("\n" + "="*60)
    print("Testing Grants.gov XML Extract")
    print("="*60)

    # Try today, then yesterday
    dates_to_try = [
        datetime.now(timezone.utc),
        datetime.now(timezone.utc).replace(day=datetime.now().day - 1),
    ]

    base_url = "https://prod-grants-gov-chatbot.s3.amazonaws.com/extracts"

    async with httpx.AsyncClient(timeout=300.0) as client:
        for date in dates_to_try:
            date_str = date.strftime("%Y%m%d")
            url = f"{base_url}/GrantsDBExtract{date_str}v2.zip"

            print(f"Trying: {url}")

            try:
                response = await client.get(url)
                if response.status_code == 404:
                    print(f"  Not found, trying previous day...")
                    continue

                response.raise_for_status()

                size_mb = len(response.content) / 1024 / 1024
                print(f"[OK] Downloaded {size_mb:.1f} MB")

                # Parse the ZIP
                with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
                    xml_files = [f for f in zf.namelist() if f.endswith('.xml')]
                    print(f"[OK] Found XML file: {xml_files[0]}")

                    with zf.open(xml_files[0]) as xml_file:
                        # Parse first opportunities
                        count = 0
                        sample_opps = []

                        context = ET.iterparse(xml_file, events=('end',))
                        for event, elem in context:
                            # Handle namespaced tags
                            tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                            if tag_name == 'OpportunitySynopsisDetail_1_0':
                                count += 1
                                if len(sample_opps) < 3:
                                    # Find child elements with namespace handling
                                    opp_id = None
                                    title = None
                                    for child in elem:
                                        child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                                        if child_tag == 'OpportunityID':
                                            opp_id = child.text
                                        elif child_tag == 'OpportunityTitle':
                                            title = child.text
                                    if opp_id and title:
                                        sample_opps.append({
                                            'id': opp_id,
                                            'title': title[:50] if title else 'N/A'
                                        })
                                elem.clear()

                                # Stop after counting 1000 for speed
                                if count >= 1000:
                                    break

                print(f"[OK] Parsed {count}+ opportunities")
                for opp in sample_opps:
                    print(f"  - {opp['id']}: {opp['title']}...")

                return True

            except Exception as e:
                print(f"[FAILED] {type(e).__name__}: {e}")
                return False

    return False


async def test_nih_page():
    """Test NIH funding page accessibility."""
    print("\n" + "="*60)
    print("Testing NIH Funding Page")
    print("="*60)

    url = "https://grants.nih.gov/funding/searchguide/"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()

            print(f"[OK] Page accessible (status {response.status_code})")
            print(f"[OK] Content length: {len(response.text)} bytes")

            # Check for grant-related content
            if 'funding' in response.text.lower() or 'grant' in response.text.lower():
                print("[OK] Contains funding/grant content")
            else:
                print("[WARN] May not contain expected content")

            # Note about Playwright requirement
            print("\n[INFO] Full scraping requires Playwright for JavaScript rendering")
            print("[INFO] Install with: playwright install chromium")

            return True

        except Exception as e:
            print(f"[FAILED] {type(e).__name__}: {e}")
            return False


async def test_nih_reporter_api():
    """Test NIH Reporter API as alternative data source."""
    print("\n" + "="*60)
    print("Testing NIH Reporter API (Alternative)")
    print("="*60)

    api_url = "https://api.reporter.nih.gov/v2/projects/search"

    # Simple search for recent projects
    payload = {
        "criteria": {
            "fiscal_years": [2025],
        },
        "limit": 5,
        "offset": 0,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(api_url, json=payload)
            response.raise_for_status()

            data = response.json()
            projects = data.get("results", [])
            total = data.get("meta", {}).get("total", 0)

            print(f"[OK] API returned {total} total projects")
            print(f"[OK] Fetched {len(projects)} sample projects")

            for project in projects[:3]:
                print(f"  - {project.get('project_num', 'N/A')}: {project.get('project_title', 'N/A')[:50]}...")

            return True

        except Exception as e:
            print(f"[FAILED] {type(e).__name__}: {e}")
            return False


async def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# GRANT DATA SOURCE VERIFICATION")
    print("#"*60)

    results = {}

    results['NSF API'] = await test_nsf_api()
    results['Grants.gov XML'] = await test_grants_gov_xml()
    results['NIH Page'] = await test_nih_page()
    results['NIH Reporter API'] = await test_nih_reporter_api()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    all_passed = True
    for source, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{status} {source}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n[SUCCESS] All data sources are working!")
        return 0
    else:
        print("\n[WARNING] Some data sources failed. Check output above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
