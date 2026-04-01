# snoopy

This repository contains two complementary tools:

1. Instagram Scraper  
Extracts raw user lists (followers or following)

2. Instagram Enricher  
Takes scraped users and enriches them with additional metadata (bio, links, etc.)

--------------------------------------------------

Core Difference

Instagram Scraper (Data Collection)
- Purpose: Get lists of users
- Output: Raw JSON of followers or following
- Scripts:
  - main.py
  - Get_Followers.py
  - Get_Following.py

This tool answers:
Who follows this account?

Instagram Enricher (Data Enhancement)
- Purpose: Add depth to each user
- Output: Structured CSV with enriched profile data
- Script:
  - Async_Account_scraper_new.py

This tool answers:
Who are these users?

--------------------------------------------------

Workflow Overview

1. Scraper → get users
2. Enricher → enrich users

--------------------------------------------------

Instagram Scraper

Files
- main.py → CLI interface
- Get_Followers.py → follower extraction
- Get_Following.py → following extraction
- Sessions_Manager.py → session management

Setup

1. Add sessions

Run:
python main.py

Select:
[1] Session Manager

Add:
- Instagram username
- sessionid (from browser cookies)

Sessions are stored in:
session_file.txt

--------------------------------------------------

Usage

Run:
python main.py

Options:
[2] Follower Scraper
[3] Following Scraper

--------------------------------------------------

Input

You provide:
- Target username
- Number of users to scrape

--------------------------------------------------

Output

Data is saved to:
FOLLOWERS DATA/<username>/followers.json

Format:
[
  {
    "id": "123456",
    "username": "example_user",
    "full_name": "Example Name",
    "is_private": false
  }
]

--------------------------------------------------

Key Features

- Resume scraping via temp.json
- Deduplicates users by id
- Handles pagination (next_max_id)
- Session-based authentication

--------------------------------------------------

Instagram Enricher

File
- Async_Account_scraper_new.py

--------------------------------------------------

Purpose

Takes user lists and enriches them with:
- Bio
- External links
- Follower / following counts
- Verification status
- Profile metadata

--------------------------------------------------

Input

Place JSON file inside:
DATA/

Accepted Formats

Format 1 (Standard)
[
  {
    "id": "123",
    "username": "example_user"
  }
]

Format 2 (Yuremane-style)
[
  {
    "string_list_data": [
      {
        "value": "example_user",
        "href": "https://instagram.com/example_user"
      }
    ]
  }
]

--------------------------------------------------

Usage

Run:
python Async_Account_scraper_new.py

If multiple files exist:
Select JSON file from DATA/

--------------------------------------------------

Output

Saved to:
Results/<input_filename>.csv

--------------------------------------------------

Output Fields

id
username
full_name
is_private
is_verified
biography
follower_count
following_count
media_count
external_url
is_business
category_name
profile_pic_url

--------------------------------------------------

Proxy Configuration

Create a .env file:

PROXY_USERNAME=your_username
PROXY_PASSWORD=your_password
PROXY_HOST=gate.decodo.com

--------------------------------------------------

Directory Structure

.
├── DATA/
├── Results/
├── Processed Files/
├── FOLLOWERS DATA/
├── session_file.txt

--------------------------------------------------

Expected Pipeline

Step 1 — Scrape users
python main.py

Step 2 — Enrich
python Async_Account_scraper_new.py

--------------------------------------------------

Notes

- Scraper uses session-based auth
- Enricher uses proxy-based requests
- Missing fields are handled safely
- JSON files are moved after processing

--------------------------------------------------

Common Issues

1. All users already processed
- CSV already contains usernames

2. Proxy errors (407)
- Invalid credentials or config

3. Missing id
- Enricher requires both username and id

--------------------------------------------------

Summary

Tool: Scraper
Input: username
Output: JSON
Purpose: collect users

Tool: Enricher
Input: JSON
Output: CSV
Purpose: enrich users
