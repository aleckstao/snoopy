# Snoopy

---

## Overview

Snoopy (he/him) is Komune's honorary store pet. Snoopy's birthday is April 6, 2026. Snoopy has two main tools:

1. **instagram-scraper**  
   Extracts raw Instagram user lists from an account’s **followers** or **following**.

2. **instagram-enricher**  
   Takes a list of Instagram usernames and enriches each profile with additional metadata such as bio, website, follower count, following count, category, and more.

In simple terms:

- **instagram-scraper** answers:  
  **“Who follows this account?”** or **“Who does this account follow?”**

- **instagram-enricher** answers:  
  **“Who are these users?”**

---

## High-level workflow

The normal workflow looks like this:

1. Use **instagram-scraper** to collect a raw list of users
2. Optionally reformat json list using the included reformatter
3. Use **instagram-enricher** to extract profile data for each user

---

## Repository structure

snoopy/
├── README.md
├── instagram-scraper/
│   ├── main.py
│   ├── Followers_scraped.txt
│   ├── Following_scraped.txt
│   ├── session_file.txt
│   ├── requirements.txt
│   ├── FOLLOWERS DATA/
│   ├── FOLLOWING DATA/
│   └── modules/
│       ├── Sessions_Manager.py
│       ├── Get_Followers.py
│       └── Get_Following.py
│
└── instagram-enricher/
    ├── Async_Account_scraper_new.py
    ├── requirements.txt
    ├── DATA/
    ├── Results/
    └── Processed Files/

---

## Technical Details

1. **instagram-scraper**  
    - Summary
        - Instagram Followers Scraper Suite is a Python-based toolset designed to extract follower and following data from Instagram profiles. The suite includes three main modules:
            - Session Manager: Handles Instagram session authentication
            - Follower Scraper: Extracts follower data from target profiles
            - Following Scraper: Extracts following data from target profiles
        - The tool uses Instagram's private API endpoints with proper session authentication to gather data efficiently while implementing rate limiting to avoid detection.
    - Features
        - Multi-module architecture for organized functionality
        - Session management for persistent authentication
        - Customizable scraping limits (number of users to scrape)
        - Rate limiting to avoid detection
        - Randomized user agents to mimic organic traffic
        - Duplicate filtering in output data
    - Risks
        - Rate Limiting: The tool implements random delays between requests to avoid triggering Instagram's rate limits. Do not modify these delays to be more aggressive.
        - Session Authentication: You must provide a valid Instagram session ID. Sessions may expire and need to be refreshed periodically
        - Verified Accounts: The tool may not be able to scrape more than 50 followers/following for verified accounts due to Instagram's API limitations.

2.  **instagram-enricher**  
    - Summary
        - Instagram Enricher is a Python-based enrichment tool that takes an existing list of Instagram users and retrieves additional public profile metadata for each account.
        - Rather than discovering users from a target profile, the enricher starts with a pre-existing JSON list of accounts and expands each record with richer profile-level data.
    - Features
        - Asynchronous architecture for faster enrichment of large user lists
        - Supports structured JSON input from prior scraping workflows
        - CSV export
        - Automatic processing of all users in a selected input file
        - Proxy support for large enrichment jobs
        - Retry logic across multiple proxy ports
        - Safe handling of missing fields
    - Risks
        - Proxy authentication: The enricher depends on valid proxy credentials. Incorrect credentials or exhausted proxy credits will cause request failures before the request reaches Instagram.
        - Endpoint instability: The tool relies on Instagram’s internal or semi-private request patterns, which may change over time and require code updates.
        - Input formatting: The enricher expects a specific input structure. If the JSON is malformed or the expected fields are missing, records may be skipped.
        - Large job fragility: Very large enrichment jobs may fail partially due to proxy exhaustion, session issues, or Instagram-side throttling.
        - Incomplete metadata: Not all Instagram accounts expose the same amount of public information. Some fields may be blank depending on the account.