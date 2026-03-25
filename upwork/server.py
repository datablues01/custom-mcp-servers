"""
Upwork MCP Server
=================
Exposes Upwork GraphQL API endpoints:
  - User & organization info
  - Job search (marketplace) & own job postings
  - Contracts & offers
  - Freelancer search
  - Time reports
  - Messages (rooms & stories)
  - Transaction history
  - Proposals
  - Freelancer profile

Env vars:
  UPWORK_CLIENT_ID       - OAuth2 client ID
  UPWORK_CLIENT_SECRET   - OAuth2 client secret
  UPWORK_TOKEN_FILE      - Path to saved token JSON (default: token.json in this dir)
  UPWORK_ORG_ID          - Organization/tenant ID (optional, auto-detected if not set)
  UPWORK_INSTANCE_NAME   - Instance label for MCP (default: "upwork")

First run: execute auth.py to complete the OAuth2 flow and save tokens.
"""

import os
import json
from pathlib import Path

import httpx
from mcp.server.fastmcp import FastMCP

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
CLIENT_ID = os.environ.get("UPWORK_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("UPWORK_CLIENT_SECRET", "")
TOKEN_FILE = os.environ.get("UPWORK_TOKEN_FILE", str(SCRIPT_DIR / "token.json"))
ORG_ID = os.environ.get("UPWORK_ORG_ID", "")
INSTANCE_NAME = os.environ.get("UPWORK_INSTANCE_NAME", "upwork")

GRAPHQL_URL = "https://api.upwork.com/graphql"
TOKEN_URL = "https://www.upwork.com/api/v3/oauth2/token"

# ── Server init ─────────────────────────────────────────────────────────────
mcp = FastMCP(INSTANCE_NAME)

# ── Token state ─────────────────────────────────────────────────────────────
_token: dict = {}


def _load_token() -> dict:
    global _token
    if not _token and os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            _token = json.load(f)
    return _token


def _save_token(data: dict):
    global _token
    _token = data
    with open(TOKEN_FILE, "w") as f:
        json.dump(data, f, indent=2)


async def _refresh_token():
    """Refresh the access token using the refresh token."""
    token = _load_token()
    if not token.get("refresh_token"):
        raise RuntimeError("No refresh token available. Run auth.py first.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": token["refresh_token"],
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            },
        )
        resp.raise_for_status()
        new_token = resp.json()
        if "refresh_token" not in new_token and "refresh_token" in token:
            new_token["refresh_token"] = token["refresh_token"]
        _save_token(new_token)


# ── Helpers ─────────────────────────────────────────────────────────────────
async def _graphql(query: str, variables: dict | None = None, retry: bool = True) -> dict:
    """Execute a GraphQL query against the Upwork API."""
    token = _load_token()
    if not token.get("access_token"):
        raise RuntimeError("No access token. Run auth.py first.")

    headers = {
        "Authorization": f"Bearer {token['access_token']}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    if ORG_ID:
        headers["X-Upwork-API-TenantId"] = ORG_ID

    body = {"query": query}
    if variables:
        body["variables"] = variables

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(GRAPHQL_URL, json=body, headers=headers)

        if resp.status_code == 401 and retry:
            await _refresh_token()
            return await _graphql(query, variables, retry=False)

        resp.raise_for_status()
        result = resp.json()

        if "errors" in result and result["errors"]:
            for err in result["errors"]:
                if "401" in str(err) or "auth" in str(err).lower():
                    if retry:
                        await _refresh_token()
                        return await _graphql(query, variables, retry=False)

        return result


# ═══════════════════════════════════════════════════════════════════════════
#  TOOLS
# ═══════════════════════════════════════════════════════════════════════════

# ── User & Organization ──────────────────────────────────────────────────
@mcp.tool()
async def get_current_user() -> dict:
    """Get the current authenticated Upwork user's basic info (ID, name, email)."""
    return await _graphql("""
        query {
            user {
                id
                nid
                rid
                email
                name
                photoUrl
                ciphertext
            }
        }
    """)


@mcp.tool()
async def get_freelancer_profile() -> dict:
    """Get the current user's freelancer profile (skills, availability, etc.)."""
    return await _graphql("""
        query {
            user {
                freelancerProfile {
                    fullName
                    firstName
                    lastName
                    personalData {
                        description
                    }
                    availability {
                        capacity
                    }
                    skills {
                        edges {
                            node {
                                prettyName
                            }
                        }
                    }
                    aggregates {
                        totalRevenue
                        totalHours
                        jobsCompleted
                    }
                    countryDetails {
                        name
                    }
                }
            }
        }
    """)


@mcp.tool()
async def get_organization() -> dict:
    """Get the current organization's details (name, type, active status)."""
    return await _graphql("""
        query {
            organization {
                id
                rid
                legacyId
                name
                type
                legacyType
                flag {
                    client
                    vendor
                    agency
                    individual
                }
                active
                hidden
                creationDate
            }
        }
    """)


@mcp.tool()
async def list_organizations() -> dict:
    """List all organizations/companies the user has access to. Useful for finding the org ID."""
    return await _graphql("""
        query {
            companySelector {
                items {
                    title
                    organizationId
                    organizationRid
                    organizationType
                    organizationLegacyType
                    typeTitle
                }
            }
        }
    """)


# ── Job Search (Marketplace) ────────────────────────────────────────────
@mcp.tool()
async def search_jobs(
    search_term: str,
    first: int = 20,
) -> dict:
    """
    Search for jobs on the Upwork marketplace.

    Args:
        search_term: Keywords to search for (e.g. 'python developer', 'data analyst')
        first: Max results to return (default 20)
    """
    return await _graphql("""
        query($searchTerm: String!) {
            marketplaceJobPostingsSearch(
                marketPlaceJobFilter: {
                    searchExpression_eq: $searchTerm
                }
                sortAttributes: [{ field: RECENCY }]
            ) {
                totalCount
                edges {
                    node {
                        id
                        title
                        description
                        ciphertext
                        createdDateTime
                        duration
                        durationLabel
                        engagement
                        experienceLevel
                        category
                        subcategory
                        totalApplicants
                        freelancersToHire
                        applied
                        amount {
                            rawValue
                            displayValue
                            currency
                        }
                        hourlyBudgetMin {
                            rawValue
                            displayValue
                            currency
                        }
                        hourlyBudgetMax {
                            rawValue
                            displayValue
                            currency
                        }
                        skills {
                            name
                            prettyName
                        }
                        client {
                            totalHires
                            totalPostedJobs
                            totalSpent {
                                rawValue
                                displayValue
                                currency
                            }
                            totalReviews
                            totalFeedback
                            verificationStatus
                        }
                    }
                }
            }
        }
    """, {"searchTerm": search_term})


@mcp.tool()
async def get_job(job_id: str) -> dict:
    """
    Get details of a specific job posting by ID.

    Args:
        job_id: The job posting ID (e.g. '~01abcdef1234567890')
    """
    return await _graphql("""
        query($id: ID!) {
            marketplaceJobPosting(id: $id) {
                id
                content {
                    title
                    description
                }
                classification {
                    category {
                        id
                        preferredLabel
                    }
                    subCategory {
                        id
                        preferredLabel
                    }
                    skills {
                        id
                        prettyName
                        preferredLabel
                    }
                }
                contractTerms {
                    contractType
                    experienceLevel
                    contractStartDate
                    contractEndDate
                    personsToHire
                    onSiteType
                }
                activityStat {
                    applicationsBidStats {
                        totalApplications
                    }
                }
                clientCompanyPublic {
                    name
                }
                canClientReceiveContractProposal
            }
        }
    """, {"id": job_id})


# ── Contracts ────────────────────────────────────────────────────────────
@mcp.tool()
async def get_contract(contract_id: str) -> dict:
    """
    Get details of a specific contract.

    Args:
        contract_id: The contract ID
    """
    return await _graphql("""
        query($id: ID!) {
            contractDetails(id: $id) {
                id
                title
                status
                deliveryModel
                kind
                createDate
                modifyDate
                startDate
                endDate
                freelancer {
                    id
                    rid
                    name
                }
                vendorOrganization {
                    id
                    name
                }
                clientOrganization {
                    id
                    name
                }
                hiringManager {
                    id
                    name
                }
            }
        }
    """, {"id": contract_id})


@mcp.tool()
async def list_contracts(contract_ids: str = "") -> dict:
    """
    List contracts by IDs. If no IDs provided, returns all accessible contracts.

    Args:
        contract_ids: Comma-separated contract IDs (optional, e.g. '123,456')
    """
    ids = [i.strip() for i in contract_ids.split(",") if i.strip()] if contract_ids else None
    return await _graphql("""
        query($ids: [ID]) {
            contractList(ids: $ids) {
                id
                title
                contractType
                status
                createdDateTime
                startDateTime
                endDateTime
                paused
                freelancer {
                    fullName
                    firstName
                    lastName
                }
                clientCompany {
                    name
                }
                weeklyHoursLimit
            }
        }
    """, {"ids": ids})


# ── Offers ───────────────────────────────────────────────────────────────
@mcp.tool()
async def get_offer(offer_id: str) -> dict:
    """
    Get details of a specific offer.

    Args:
        offer_id: The offer ID
    """
    return await _graphql("""
        query($id: ID!) {
            offer(id: $id) {
                id
                title
                status
            }
        }
    """, {"id": offer_id})


# ── Freelancer Search ────────────────────────────────────────────────────
@mcp.tool()
async def search_freelancers(keyword: str, first: int = 20) -> dict:
    """
    Search for freelancers on the Upwork talent marketplace.

    Args:
        keyword: Search keyword (e.g. 'react developer', 'data scientist')
        first: Max results to return (default 20)
    """
    return await _graphql("""
        query($filter: FreelancerProfileSearchFilter!, $pagination: Pagination!) {
            freelancerProfileSearchRecords(
                searchFilter: $filter
                pagination: $pagination
            ) {
                totalCount
                edges {
                    node {
                        id
                        name
                        photoUrl
                        publicUrl
                        ciphertext
                    }
                }
            }
        }
    """, {
        "filter": {
            "userType": "FREELANCER",
            "keyword": keyword,
        },
        "pagination": {
            "first": first,
            "after": None,
        },
    })


@mcp.tool()
async def get_freelancer_by_profile_key(profile_key: str) -> dict:
    """
    Get a freelancer's profile by their profile key (ciphertext like ~01abc...).

    Args:
        profile_key: The freelancer profile key (e.g. '~013c695dd60c19c334')
    """
    return await _graphql("""
        query($profileKey: String!) {
            freelancerProfileByProfileKey(profileKey: $profileKey) {
                fullName
                firstName
                lastName
                personalData {
                    description
                }
                skills {
                    edges {
                        node {
                            prettyName
                        }
                    }
                }
                countryDetails {
                    name
                }
                availability {
                    capacity
                }
                aggregates {
                    totalRevenue
                    totalHours
                    jobsCompleted
                }
            }
        }
    """, {"profileKey": profile_key})


# ── Time Reports ─────────────────────────────────────────────────────────
@mcp.tool()
async def get_time_report(
    start_date: str,
    end_date: str,
    first: int = 500,
) -> dict:
    """
    Get time reports for the organization within a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        first: Max results (default 500)
    """
    org_id = ORG_ID
    if not org_id:
        org_result = await _graphql("query { organization { id } }")
        org_id = org_result.get("data", {}).get("organization", {}).get("id", "")

    return await _graphql("""
        query($filter: TimeReportFilter, $pagination: Pagination) {
            contractTimeReport(filter: $filter, pagination: $pagination) {
                totalCount
                edges {
                    node {
                        dateWorkedOn
                        weekWorkedOn
                        monthWorkedOn
                        yearWorkedOn
                        freelancer {
                            id
                            nid
                            rid
                            name
                        }
                        team {
                            id
                            rid
                            name
                        }
                        contract {
                            id
                            title
                            status
                            deliveryModel
                            createDate
                            startDate
                            endDate
                        }
                        task
                        taskDescription
                        memo
                        totalHoursWorked
                        totalCharges
                        totalOnlineHoursWorked
                        totalOnlineCharge
                        totalOfflineHoursWorked
                        totalOfflineCharge
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    """, {
        "filter": {
            "organizationId_eq": org_id,
            "timeReportDate_bt": {
                "startDate": start_date,
                "endDate": end_date,
            },
        },
        "pagination": {
            "first": first,
            "after": None,
        },
    })


# ── Messages ─────────────────────────────────────────────────────────────
@mcp.tool()
async def list_rooms(first: int = 50) -> dict:
    """
    List message rooms (conversations) the user is part of.

    Args:
        first: Max rooms to return (default 50)
    """
    return await _graphql("""
        query($pagination: Pagination) {
            roomList(pagination: $pagination, sortOrder: DESC) {
                edges {
                    node {
                        id
                        roomName
                        topic
                        roomType
                        numUnread
                        favorite
                        hidden
                        muted
                        createdAtDateTime
                        latestStory {
                            id
                            message
                            createdDateTime
                            user {
                                id
                                name
                            }
                        }
                        roomUsers {
                            id
                            name
                        }
                        numUsers
                    }
                }
            }
        }
    """, {"pagination": {"first": first}})


@mcp.tool()
async def get_room_messages(room_id: str, first: int = 50) -> dict:
    """
    Get messages in a specific room/conversation.

    Args:
        room_id: The room ID (from list_rooms)
        first: Max messages to return (default 50)
    """
    return await _graphql("""
        query($roomId: ID!) {
            room(id: $roomId) {
                id
                roomName
                topic
                roomType
                stories {
                    edges {
                        node {
                            id
                            message
                            createdDateTime
                            updatedDateTime
                            user {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
    """, {"roomId": room_id})


@mcp.tool()
async def send_message(room_id: str, message: str) -> dict:
    """
    Send a message in a room/conversation.

    Args:
        room_id: The room ID (from list_rooms)
        message: Message text to send
    """
    return await _graphql("""
        mutation($input: RoomStoryCreateInputV2!) {
            createRoomStoryV2(input: $input) {
                id
                message
                createdDateTime
                user {
                    id
                    name
                }
            }
        }
    """, {"input": {"roomId": room_id, "message": message}})


# ── Proposals ────────────────────────────────────────────────────────────
@mcp.tool()
async def get_client_proposals(job_posting_id: str, first: int = 50) -> dict:
    """
    Get proposals received for a job posting (client view).

    Args:
        job_posting_id: The job posting ID
        first: Max results (default 50)
    """
    return await _graphql("""
        query($jobPostingId: ID!, $pagination: Pagination) {
            clientProposals(jobPostingId: $jobPostingId, pagination: $pagination) {
                totalCount
                edges {
                    node {
                        id
                        status
                        freelancer {
                            id
                            name
                        }
                    }
                }
            }
        }
    """, {"jobPostingId": job_posting_id, "pagination": {"first": first}})


# ── Financials ───────────────────────────────────────────────────────────
@mcp.tool()
async def get_transaction_history(
    start_date: str,
    end_date: str,
) -> dict:
    """
    Get transaction history (payments, charges) for a date range.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    """
    # Need accounting entity IDs first
    ace_result = await _graphql("query { accountingEntity { id } }")
    ace_id = ace_result.get("data", {}).get("accountingEntity", {}).get("id", "")

    return await _graphql("""
        query($filter: TransactionHistoryFilter!) {
            transactionHistory(transactionHistoryFilter: $filter) {
                transactionDetail {
                    transactionHistoryRow {
                        recordId
                        type
                        description
                        descriptionUI
                        transactionCreationDate
                        transactionAmount {
                            rawValue
                            displayValue
                            currency
                        }
                        amountCreditedToUser {
                            rawValue
                            displayValue
                            currency
                        }
                        accountingSubtype
                        assignmentDeveloperName
                        assignmentCompanyName
                        paymentStatus
                    }
                }
            }
        }
    """, {
        "filter": {
            "aceIds_any": [ace_id] if ace_id else [],
            "transactionDateTime_bt": {
                "rangeStart": start_date,
                "rangeEnd": end_date,
            },
        },
    })


# ── Work Diary ───────────────────────────────────────────────────────────
@mcp.tool()
async def get_work_diary(
    contract_id: str,
    date: str,
) -> dict:
    """
    Get work diary snapshots for a contract on a specific date.

    Args:
        contract_id: The contract ID
        date: Date to get snapshots for (YYYY-MM-DD)
    """
    return await _graphql("""
        query($input: WorkDiaryContractInput!) {
            workDiaryContract(workDiaryContractInput: $input) {
                totalTrackedTime
                cells {
                    cellDateTime
                    trackedTime
                    screenshots {
                        url
                        hasScreenshot
                    }
                }
            }
        }
    """, {"input": {"contractId": contract_id, "date": date}})


# ── Raw GraphQL ──────────────────────────────────────────────────────────
@mcp.tool()
async def run_graphql(query: str, variables: str = "") -> dict:
    """
    Execute a raw GraphQL query against the Upwork API.
    Use this for any queries not covered by the other tools.

    Args:
        query: The GraphQL query or mutation string
        variables: JSON string of variables (optional, e.g. '{"id": "123"}')
    """
    vars_dict = json.loads(variables) if variables else None
    return await _graphql(query, vars_dict)


# ── Run ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run()
