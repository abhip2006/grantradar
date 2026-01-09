# NIH Reporter API Integration Research

## Overview

The NIH Reporter API provides programmatic access to scientific awards data from NIH and other federal agencies. This document outlines how to use the API to build a grant success rate prediction model.

**Key Fact**: The API provides access to approximately 2.6M funded projects in the database going back to fiscal year 1985, with approximately 70-100K projects added annually.

## API Endpoints

### Main Endpoint
- **Base URL**: `https://api.reporter.nih.gov/`
- **Primary Endpoint**: `POST https://api.reporter.nih.gov/v2/projects/search`
- **Authentication**: None required (public API)

### Available Endpoints
1. **Project API (V2)** - Query funded projects with detailed payload criteria
2. **Publication API** - Query publications linked to funded projects

## Query Structure

### Basic JSON Payload Format

```json
{
  "criteria": {
    "fiscal_years": [2023, 2022],
    "funding_mechanism": ["R01", "R21"],
    "include_active_projects": false,
    "exclude_subprojects": false,
    "use_relevance": false
  },
  "include_fields": [
    "ProjectNum",
    "ProjectTitle",
    "FiscalYear",
    "AwardAmount",
    "DirectCostAmount",
    "IndirectCostAmount",
    "FundingMechanism",
    "ActivityCode",
    "ICCode",
    "PrincipalInvestigators",
    "Organization",
    "StartDate",
    "EndDate"
  ],
  "offset": 0,
  "limit": 500
}
```

### Key Query Parameters

#### Funding Mechanism Filtering
- **Parameter Name**: `funding_mechanism`
- **Supported Values**:
  - `R01`, `R21`, `R03`, `R33`, `R34` (Research Project Grants)
  - `K08`, `K23`, `K01`, `K02` (Career Development/K Awards)
  - `F30`, `F31`, `F32` (Fellowships)
  - `T32`, `T15` (Training Grants)
  - `P01`, `P50`, `P60` (Program Projects/Centers)
  - `SB` (Small Business)
  - `Other` (Combined mechanisms: UK, OT, CP)

#### Activity Codes
- **Parameter Name**: `activity_codes`
- **Format**: 3-character codes identifying grant type (e.g., R01, F32, K08)
- **Example**: `["R01", "R21", "K08"]`

#### Time-Based Filtering
- **Parameter Name**: `fiscal_years`
- **Format**: Array of integers
- **Example**: `[2023, 2022, 2021]`
- **Important**: Limited to single fiscal years for broad searches due to 10K record limit

#### Organization Filtering
- **Parameter Name**: `org_names`
- **Format**: Array of strings (institution names)
- **Example**: `["Stanford University", "MIT"]`

#### Financial Filtering
- **Parameter Name**: `award_amount_range`
- **Format**: Object with min/max values
- **Example**: `{"min": 100000, "max": 500000}`

#### Other Useful Parameters
- `include_active_projects`: Include ongoing projects (boolean)
- `multi_pi_only`: Only projects with multiple PIs (boolean)
- `newly_added_projects_only`: Only recently added projects (boolean)
- `sub_project_only`: Only sub-projects (boolean)

## Response Data Structure

### Project Object Fields

Financial Data:
- `AwardAmount`: Total award amount
- `DirectCostAmount`: Direct costs (FY 2012+)
- `IndirectCostAmount`: Indirect costs (FY 2012+)
- **Note**: Costs not available for SBIR/STTR awards

Project Identification:
- `ProjectNum`: Full project number (e.g., "5R01DK102815-05")
- `ProjectNumSplit`: Parsed project number components
  - `ApplTypeCode`: Application type
  - `ActivityCode`: Activity code (R01, K08, etc.)
  - `ICCode`: Institute/Center code
  - `SerialNum`: Serial number
  - `SupportYear`: Support year suffix

Temporal Data:
- `FiscalYear`: Fiscal year of award
- `StartDate`: Project start date
- `EndDate`: Project end date
- `BudgetStart`: Budget period start
- `BudgetEnd`: Budget period end
- `AwardNoticeDate`: Date award was announced

Organization & Personnel:
- `Organization`: Awardee organization details
  - `OrgName`
  - `OrgCity`, `OrgState`, `OrgCountry`
  - `DUNS`, `UEI` (unique identifiers)
  - `DeptType`
- `PrincipalInvestigators`: Array of PI information
  - `Name`, `ProfileId`, `Role`
- `ProgramOfficerContact`: Program officer details

Classification Data:
- `FundingMechanism`: Mechanism name
- `ActivityCode`: 3-character activity code
- `ICCode`: Institute/Center code
- `StudySectionCode`: Study section for review

Study Information:
- `ProjectTitle`: Grant title
- `AbstractText`: Project abstract
- `Terms`: Keywords/MeSH terms
- `RCDC`: Research, Condition, and Disease Categorization

Special Indicators:
- `CovidResponse`: COVID-19 funding indicator
  - Values: "C4", "C5", "C6" for different relief acts
- `ARRAFunding`: American Recovery Act funding flag

## Example API Calls

### Query 1: Get All R01 Grants for a Specific Year

```bash
curl -X POST https://api.reporter.nih.gov/v2/projects/search \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": {
      "fiscal_years": [2023],
      "activity_codes": ["R01"],
      "include_active_projects": false,
      "exclude_subprojects": true
    },
    "include_fields": [
      "ProjectNum",
      "ProjectTitle",
      "AwardAmount",
      "DirectCostAmount",
      "FiscalYear",
      "PrincipalInvestigators",
      "Organization"
    ],
    "offset": 0,
    "limit": 500
  }'
```

### Query 2: Compare R01 vs R21 Award Amounts and Rates

```bash
curl -X POST https://api.reporter.nih.gov/v2/projects/search \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": {
      "fiscal_years": [2020, 2021, 2022, 2023],
      "activity_codes": ["R01", "R21"],
      "exclude_subprojects": true
    },
    "include_fields": [
      "ProjectNum",
      "AwardAmount",
      "DirectCostAmount",
      "IndirectCostAmount",
      "FiscalYear",
      "ActivityCode",
      "Organization",
      "ICCode"
    ],
    "offset": 0,
    "limit": 500
  }'
```

### Query 3: Get K Award Career Development Grants

```bash
curl -X POST https://api.reporter.nih.gov/v2/projects/search \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": {
      "fiscal_years": [2023],
      "activity_codes": ["K01", "K08", "K23", "K99"],
      "exclude_subprojects": true
    },
    "include_fields": [
      "ProjectNum",
      "ProjectTitle",
      "AwardAmount",
      "FiscalYear",
      "PrincipalInvestigators",
      "Organization",
      "ActivityCode"
    ],
    "offset": 0,
    "limit": 500
  }'
```

### Query 4: Organization-Based Query (Stanford R01s)

```bash
curl -X POST https://api.reporter.nih.gov/v2/projects/search \
  -H "Content-Type: application/json" \
  -d '{
    "criteria": {
      "fiscal_years": [2023],
      "org_names": ["Stanford"],
      "activity_codes": ["R01"],
      "exclude_subprojects": true
    },
    "include_fields": [
      "ProjectNum",
      "ProjectTitle",
      "AwardAmount",
      "PrincipalInvestigators",
      "Organization"
    ],
    "offset": 0,
    "limit": 500
  }'
```

## Response Example

```json
{
  "meta": {
    "total": 5234,
    "limit": 500,
    "offset": 0
  },
  "results": [
    {
      "project_num": "5R01AI098108-08",
      "fiscal_year": 2023,
      "award_amount": 412500,
      "direct_cost_amount": 275000,
      "indirect_cost_amount": 137500,
      "activity_code": "R01",
      "ic_code": "AI",
      "funding_mechanism": "Research Project Grant",
      "project_title": "Novel approaches to vaccine development",
      "organization": {
        "org_name": "Stanford University",
        "org_city": "Stanford",
        "org_state": "CA"
      },
      "principal_investigators": [
        {
          "name": "John Smith",
          "profile_id": "1234567",
          "role": "Contact PI"
        }
      ],
      "abstract_text": "This project aims to develop...",
      "terms": ["vaccine", "immunology", "infectious disease"],
      "start_date": "2023-04-01",
      "end_date": "2028-03-31"
    }
  ]
}
```

## Data Available for Win Probability Modeling

### Direct Indicators
1. **Award Counts by Mechanism and Year** - Calculate historical success rates
2. **Award Amounts by Mechanism** - Model funding level expectations
3. **Organization Patterns** - Track which institutions succeed most
4. **PI Information** - Identify successful investigator patterns
5. **Activity Code Distribution** - Understand mechanism-specific trends

### Calculated Metrics
1. **Success Rate Calculation**:
   - Number of funded projects per mechanism per year
   - Can be combined with NIH success rate page data for actual application counts

2. **Award Trend Analysis**:
   - Average award amounts by mechanism
   - Award amount trends over time
   - Award amount ranges (min/max/median)

3. **Organization Success**:
   - Count of funded projects by organization
   - Average award amounts by organization
   - Success concentration (top 10/20/50 organizations)

4. **Temporal Patterns**:
   - Year-over-year funding trends by mechanism
   - Seasonal patterns in awards
   - Multi-year award patterns

### Limitations for Win Probability
- **No Application Data**: The API only returns funded projects, not submission/application data
- **No Rejection Information**: Cannot directly see which applications were rejected
- **Success Rate Source**: Must supplement with NIH's official success rate page at https://report.nih.gov/funding/nih-budget-and-spending-data-past-fiscal-years/success-rates
- **Historical Only**: API returns completed/funded projects, not predictive indicators

## Official Success Rate Data Source

NIH publishes official success rate statistics at:
**https://report.nih.gov/funding/nih-budget-and-spending-data-past-fiscal-years/success-rates**

Available metrics:
- Success rates by mechanism (R01, R21, K awards, etc.)
- Success rates by Institute/Center (IC)
- Success rates by submission type (new, competing renewal, etc.)
- Historical data back to 1970
- Detailed breakdowns by organization type and department

Success Rate Formula:
```
Success Rate = (Number of competing applications funded) / (Total competing applications reviewed) × 100%
```

Note: Excludes reimbursable funding, computed on fiscal year basis.

## Pagination and Limitations

### Hard Limits
- **Maximum Records Per Query**: 10,000 records
- **Maximum Offset**: 9,999 (can retrieve up to record 10,000)
- **Default Limit Per Page**: 500 records (maximum)
- **Database Size**: ~2.6M total projects (FY 1985 - present)
- **Annual Additions**: 70-100K new projects per fiscal year

### Rate Limiting
- **Recommended Rate**: No more than 1 request per second
- **Optimal Query Time**: 9:00 PM - 5:00 AM EST on weekdays, or weekends
- **Enforcement**: IP blocking for non-compliance

### Pagination Strategy

For queries that return more than 10,000 results:

**Strategy 1: Fiscal Year Segmentation**
```
- Query FY 2023: Offset 0, Limit 500 (multiple requests)
- Query FY 2022: Offset 0, Limit 500 (multiple requests)
- Query FY 2021: Offset 0, Limit 500 (multiple requests)
- etc.
```

**Strategy 2: Mechanism Segmentation**
```
- Query R01 only: Offset 0, Limit 500 (paginate with offset)
- Query R21 only: Offset 0, Limit 500 (paginate with offset)
- Query K awards: Offset 0, Limit 500 (paginate with offset)
```

**Strategy 3: Quantile-Based Segmentation**
For very large result sets:
1. Get sample (e.g., first 5,000 records)
2. Calculate quantiles on a field like `award_amount`
3. Query within each quantile range to ensure <10K results per query

Example pagination code structure:
```python
def paginate_results(criteria, limit=500):
    offset = 0
    all_results = []

    while True:
        response = query_api({
            "criteria": criteria,
            "offset": offset,
            "limit": limit
        })

        all_results.extend(response['results'])

        # Stop if we've reached the total or hit max possible records
        if offset + limit >= response['meta']['total'] or offset >= 9500:
            break

        offset += limit
        time.sleep(1)  # Rate limiting: 1 request per second

    return all_results
```

## Database Update Frequency

- **Weekly Updates**: The database is updated on a weekly basis
- **Revisions**: Updates include not just new projects but revisions to prior awards
  - Changes to grantee institution
  - Revised award amounts
  - Other project modifications

## Implementation Considerations

### For Win Probability Model

**Data Collection Phase**:
1. Query all R01, R21, R03 awards for past 5-10 years
2. Query all K awards (K01, K08, K23, K99, etc.)
3. Query all P awards for program projects
4. Collect organization and PI success patterns

**Feature Engineering**:
- Historical success rate by mechanism
- Average award amounts by mechanism
- Organization prestige/success rate
- PI publication/funding history
- Time trends and seasonal patterns
- Institute/Center funding trends

**Model Training**:
- Use funded project data as positive examples
- Supplement with application rejection data from other sources
- Calculate success probabilities by mechanism type
- Weight recent years more heavily (policy changes occur)

**Limitations to Address**:
- API only shows funded projects (survivorship bias)
- Need to combine with official NIH success rate data
- Application success rates ≠ award prediction (different populations)
- Success rates change year-to-year with funding levels

## Alternative Data Sources

1. **ExPORTER Bulk Download**
   - Annual extracts available at: https://exporter.nih.gov/
   - More complete historical data
   - Downloadable in bulk format

2. **NIH Data Book (NDB)**
   - Summary statistics and trends
   - Already-calculated success rates
   - Available at: https://report.nih.gov/

3. **R Package: repoRter.nih**
   - CRAN package: https://cran.r-project.org/web/packages/repoRter.nih/
   - Convenient R interface to API
   - Handles pagination and rate limiting

4. **Python Package: pynih**
   - GitHub: https://github.com/neonwatty/pynih
   - Python wrapper for API

## Contact & Support

- **Official API Page**: https://api.reporter.nih.gov/
- **Support Email**: RePORT@mail.nih.gov
- **Interactive API Explorer**: https://api.reporter.nih.gov/ (try endpoint functionality)

## Key Takeaways for Model Development

1. **Data Available**: Complete information on all funded projects with award amounts, mechanisms, organizations, and PIs
2. **Success Rates**: Must supplement API data with official NIH success rate page for accurate baseline rates
3. **Mechanisms Supported**: All major NIH mechanisms (R01, R21, K awards, etc.) are directly queryable
4. **Scale**: ~70-100K projects annually makes this suitable for statistical modeling
5. **Rate Limiting**: Must respect 1 request/second limit and 10K record limits for large queries
6. **Access**: No authentication required, completely public API

---

**Last Updated**: January 2026
**Sources**:
- [NIH Reporter API Official Documentation](https://api.reporter.nih.gov/)
- [NIH Success Rates Data](https://report.nih.gov/funding/nih-budget-and-spending-data-past-fiscal-years/success-rates)
- [repoRter.nih R Package](https://cran.r-project.org/web/packages/repoRter.nih/)
- [GitHub Examples and Implementations](https://github.com/)
