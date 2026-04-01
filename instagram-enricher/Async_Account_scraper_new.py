import os
import sys
import asyncio
import csv
import json
import time
import random
from typing import List, Dict, Optional, Set
from collections import defaultdict
from dotenv import load_dotenv
from curl_cffi.requests import AsyncSession
from parsel import Selector
from fake_useragent import UserAgent

# Load environment variables
load_dotenv()

# Create necessary directories if they don't exist
os.makedirs('DATA', exist_ok=True)
os.makedirs('Results', exist_ok=True)
os.makedirs('Processed Files', exist_ok=True)

# Proxy settings from environment variables
PROXY_USERNAME = 'spo5lcrz41'
PROXY_PASSWORD = 'joEp15da6SdbY7T_hy'
PROXY_HOST = 'gate.decodo.com'

# Port range configuration
MIN_PORT = 10002
MAX_PORT = 30000

MIN_CONCURRENT_REQUESTS = 20
MAX_CONCURRENT_REQUESTS = 40
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2  # Maximum retries per username with different proxies

# Core fields we want to capture
CORE_FIELDNAMES = [
    'id', 'username', 'full_name', 'is_private', 'is_verified',
    'biography', 'follower_count', 'following_count', 'media_count',
    'external_url', 'is_business', 'category_name', 'profile_pic_url'
]

# ================== Helper functions ==================
def safe_get(dictionary, *keys):
    """Safely get a value from a nested dictionary with list support."""
    current = dictionary
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list) and isinstance(key, int) and 0 <= key < len(current):
            current = current[key]
        else:
            return None
    return current

def get_data(user):
    """Extract only the specific data we want from a user dictionary."""
    return {
        'id': safe_get(user, 'id'),
        'username': safe_get(user, 'username'),
        'full_name': safe_get(user, 'full_name') or safe_get(user, 'fullname') or None,
        'is_private': safe_get(user, 'is_private'),
        'is_verified': safe_get(user, 'is_verified'),
        'biography': safe_get(user, 'biography'),
        "follower_count": safe_get(user, "follower_count"),
        "following_count": safe_get(user, "following_count"),
        "media_count": safe_get(user, "media_count"),
        "external_url": safe_get(user, "external_url"),
        "is_business": safe_get(user, "is_business"),
        "category_name": safe_get(user, "category"),
        "profile_pic_url": safe_get(user, "profile_pic_url"),
    }

def extract_user_from_response(json_data):
    """Extract user dictionary from the GraphQL response."""
    # Try the most common structure: data.user
    user = safe_get(json_data, 'data', 'user')
    if user:
        return user
    # Fallback to the whole response if needed
    return json_data.get('user') or json_data

# ================== Proxy Manager ==================
class ProxyManager:
    def __init__(self):
        self.proxy_stats = {}
        self.proxy_usage_count = defaultdict(int)
        self.failed_proxies = set()
        self.available_ports = list(range(MIN_PORT, MAX_PORT + 1))
        self.validate_env_variables()
        random.shuffle(self.available_ports)

    def validate_env_variables(self):
        if not all([PROXY_USERNAME, PROXY_PASSWORD, PROXY_HOST]):
            missing_vars = []
            if not PROXY_USERNAME:
                missing_vars.append('PROXY_USERNAME')
            if not PROXY_PASSWORD:
                missing_vars.append('PROXY_PASSWORD')
            if not PROXY_HOST:
                missing_vars.append('PROXY_HOST')
            print(f"Missing required environment variables: {', '.join(missing_vars)}")
            sys.exit(1)
        print(f"Proxy configuration loaded: {PROXY_USERNAME}@{PROXY_HOST}")
        print(f"Port range: {MIN_PORT} - {MAX_PORT} ({len(self.available_ports)} available ports)")

    def get_random_proxy(self, exclude_ports: Set[int] = None) -> Optional[Dict]:
        """Return a dict with 'proxy_string' and 'key' for a random port."""
        exclude_ports = exclude_ports or set()
        available_ports = [
            port for port in self.available_ports
            if port not in self.failed_proxies and port not in exclude_ports
        ]
        if not available_ports:
            self.failed_proxies.clear()
            available_ports = [port for port in self.available_ports if port not in exclude_ports]
        if not available_ports:
            return None

        port = random.choice(available_ports)
        proxy_key = f"{PROXY_HOST}:{port}"
        self.proxy_usage_count[proxy_key] += 1
        if proxy_key not in self.proxy_stats:
            self.proxy_stats[proxy_key] = {
                'success': 0,
                'failed': 0,
                'avg_response_time': 0,
                'total_requests': 0
            }
        proxy_string = f"http://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_HOST}:{port}"
        return {'proxy_string': proxy_string, 'key': proxy_key, 'port': port}

    def mark_proxy_failed(self, proxy_key: str):
        """Mark a proxy port as temporarily failed."""
        try:
            port = int(proxy_key.split(':')[1])
            self.failed_proxies.add(port)
        except (ValueError, IndexError):
            pass

    def update_proxy_stats(self, proxy_dict: Dict, success: bool, response_time: float):
        if not proxy_dict:
            return
        proxy_key = proxy_dict['key']
        stats = self.proxy_stats.setdefault(proxy_key, {
            'success': 0, 'failed': 0, 'avg_response_time': 0, 'total_requests': 0
        })
        stats['total_requests'] += 1
        if success:
            stats['success'] += 1
            try:
                port = int(proxy_key.split(':')[1])
                self.failed_proxies.discard(port)
            except (ValueError, IndexError):
                pass
        else:
            stats['failed'] += 1
        if stats['total_requests'] == 1:
            stats['avg_response_time'] = response_time
        else:
            stats['avg_response_time'] = (
                (stats['avg_response_time'] * (stats['total_requests'] - 1) + response_time)
                / stats['total_requests']
            )

    def get_proxy_stats_summary(self) -> Dict:
        return {
            'total_ports': len(self.available_ports),
            'failed_ports': len(self.failed_proxies),
            'usage_distribution': dict(self.proxy_usage_count),
            'unique_ports_used': len(self.proxy_usage_count)
        }

# ================== New API Calls ==================
async def get_token(session: AsyncSession, username: str, proxy: Optional[str]) -> Optional[str]:
    """Retrieve CSRF token from the user's profile page."""
    url = f'https://www.instagram.com/{username}/'
    try:
        response = await session.get(url, impersonate='chrome', proxy=proxy, timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            return None
        selector = Selector(text=response.text)
        for jsons in selector.css('script[type="application/json"]::text').getall():
            if 'service_worker_uri' in jsons:
                json_data = json.loads(jsons)
                for item in safe_get(json_data, 'require', 0, 3,0, '__bbox', 'define') or []:
                    if 'InstagramSecurityConfig' in item:
                        return safe_get(item, 2, 'csrf_token')
        return None
    except Exception:
        return None

async def fetch_user_data(session: AsyncSession, username: str, user_id: str, token: str, proxy: Optional[str]) -> Optional[Dict]:
    """Make the GraphQL request to get user data."""
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.7',
        'cache-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://www.instagram.com',
        'pragma': 'no-cache',
        'priority': 'u=1, i',
        'referer': f'https://www.instagram.com/{username}/',
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
        'sec-ch-ua-full-version-list': '"Not)A;Brand";v="8.0.0.0", "Chromium";v="138.0.0.0", "Brave";v="138.0.0.0"',
        'sec-gpc': '1',
        'user-agent':  UserAgent().random,#'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'x-ig-app-id': '936619743392459',
        'x-csrftoken': token,
    }
    variables = {
        "enable_integrity_filters": True,
        "id": user_id,
        "render_surface": "PROFILE",
        "__relay_internal__pv__PolarisProjectCannesEnabledrelayprovider": True,
        "__relay_internal__pv__PolarisProjectCannesLoggedInEnabledrelayprovider": True,
        "__relay_internal__pv__PolarisCannesGuardianExperienceEnabledrelayprovider": True,
        "__relay_internal__pv__PolarisCASB976ProfileEnabledrelayprovider": False,
        "__relay_internal__pv__PolarisRepostsConsumptionEnabledrelayprovider": False,
    }
    data = {
        'fb_api_caller_class': 'RelayModern',
        'fb_api_req_friendly_name': 'PolarisProfilePageContentQuery',
        'server_timestamps': 'true',
        'variables': json.dumps(variables),
        'doc_id': '25585291164389315',
    }
    try:
        response = await session.post(
            'https://www.instagram.com/graphql/query',
            headers=headers,
            data=data,
            proxy=proxy,
            timeout=REQUEST_TIMEOUT
        )
        if response.status_code == 200:
            json_data = response.json()
            user = extract_user_from_response(json_data)
            if user:
                return user
        return None
    except Exception:
        return None

# ================== Main Processing Logic ==================
async def fetch_user_data_with_proxy(session: AsyncSession, username: str, user_id: str, proxy_dict: Dict) -> tuple[Optional[Dict], bool, float]:
    """Fetch user data using a specific proxy – returns (data, success, response_time)."""
    start_time = time.time()
    try:
        proxy_string = proxy_dict['proxy_string'] if proxy_dict else None
        token = await get_token(session, username, proxy_string)
        if not token:
            return None, False, time.time() - start_time
        user = await fetch_user_data(session, username, user_id, token, proxy_string)
        if user:
            return user, True, time.time() - start_time
        else:
            return None, False, time.time() - start_time
    except Exception as e:
        print(f"Error in fetch_user_data_with_proxy for {username}: {e}")
        return None, False, time.time() - start_time

async def fetch_user_data_with_retry(session: AsyncSession, username: str, user_id: str, proxy_manager: ProxyManager) -> Optional[Dict]:
    """Retry with different proxies."""
    used_ports = set()
    for attempt in range(MAX_RETRIES + 1):
        proxy_dict = proxy_manager.get_random_proxy(exclude_ports=used_ports)
        if not proxy_dict:
            print(f"No available proxy ports for {username} on attempt {attempt + 1}")
            break
        used_ports.add(proxy_dict['port'])
        data, success, response_time = await fetch_user_data_with_proxy(session, username, user_id, proxy_dict)
        proxy_manager.update_proxy_stats(proxy_dict, success, response_time)
        if success and data:
            return data
        if not success:
            proxy_manager.mark_proxy_failed(proxy_dict['key'])
            print(f"Attempt {attempt + 1} failed for {username} with proxy {proxy_dict['key']}")
    print(f"All retry attempts failed for {username}")
    return None

async def process_single_user(session: AsyncSession, user: Dict, proxy_manager: ProxyManager,
                              csv_file: str, processed_usernames: Set[str], semaphore: asyncio.Semaphore,
                              progress_counter: Dict[str, int]):
    """Process one user with concurrency control."""
    async with semaphore:
        username = user.get('username')
        user_id = user.get('id')
        if not username or not user_id:
            print(f"Skipping user: missing username or id -> {user}")
            progress_counter['failed'] += 1
            return

        try:
            result = await fetch_user_data_with_retry(session, username, user_id, proxy_manager)
            if result:
                extracted = get_data(result)
                if extracted.get('username'):
                    with open(csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                        writer = csv.DictWriter(csvfile, fieldnames=CORE_FIELDNAMES)
                        writer.writerow(extracted)
                    processed_usernames.add(username)
                    progress_counter['processed'] += 1
                    print(f"✓ Processed {progress_counter['processed']}/{progress_counter['total']} users - {username}")
                else:
                    progress_counter['failed'] += 1
                    print(f"✗ No username in result for {username}")
            else:
                progress_counter['failed'] += 1
                print(f"✗ Failed to process {username} after {MAX_RETRIES + 1} attempts")
            await asyncio.sleep(random.uniform(0.5, 2))
        except Exception as e:
            progress_counter['failed'] += 1
            print(f"Error processing {username}: {str(e)}")

# ================== CSV & File Helpers ==================
def get_user_ids():
    """Read all user data from a JSON file in DATA folder."""
    json_files = [f for f in os.listdir('DATA') if f.endswith('.json')]
    if not json_files:
        print('No JSON files found in DATA folder.')
        sys.exit(1)
    elif len(json_files) > 1:
        print('Multiple JSON files found. Please select one:')
        for i, file in enumerate(json_files, 1):
            print(f"{i}. {file}")
        selection = int(input("Enter the number of the file you want to use: ")) - 1
        ids_json_file = os.path.join('DATA', json_files[selection])
    else:
        ids_json_file = os.path.join('DATA', json_files[0])

    try:
        with open(ids_json_file, 'r') as f:
            user_data = json.load(f)
        return user_data if isinstance(user_data, list) else [user_data], ids_json_file
    except Exception as e:
        print(f"Error reading user data: {e}")
        return [], None

def initialize_csv(csv_file: str):
    if not os.path.exists(csv_file):
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CORE_FIELDNAMES)
            writer.writeheader()

def get_processed_usernames(csv_file: str) -> Set[str]:
    processed = set()
    if os.path.exists(csv_file):
        with open(csv_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if row.get('username'):
                    processed.add(row['username'])
    return processed

def move_processed_json(json_file: str):
    processed_path = os.path.join('Processed Files', os.path.basename(json_file))
    os.rename(json_file, processed_path)

# ================== Main ==================
async def main():
    data, ids_json_file = get_user_ids()
    if not data:
        return

    csv_filename = os.path.splitext(os.path.basename(ids_json_file))[0] + '.csv'
    data_csv_file = os.path.join('Results', csv_filename)
    initialize_csv(data_csv_file)
    processed_usernames = get_processed_usernames(data_csv_file)

    proxy_manager = ProxyManager()

    # Filter out already processed users and those missing required fields
    unprocessed_users = []
    for user in data:
        username = user.get('username')
        user_id = user.get('id')
        if username and user_id and username not in processed_usernames:
            unprocessed_users.append(user)
        elif username and not user_id:
            print(f"Warning: User '{username}' has no 'id' field; skipping.")

    total_users = len(data)
    unprocessed_count = len(unprocessed_users)
    print(f"Starting processing. Total: {total_users}, Remaining: {unprocessed_count}")
    print(f"Max retries per username: {MAX_RETRIES}")

    if unprocessed_count == 0:
        print("All users already processed.")
        return

    # Determine concurrency based on available ports
    available_ports = len(proxy_manager.available_ports)
    concurrent_requests = min(
        random.randint(MIN_CONCURRENT_REQUESTS, MAX_CONCURRENT_REQUESTS),
        max(1, available_ports // 10)
    )
    print(f"Using {concurrent_requests} concurrent requests with {available_ports} available ports")

    # Create a single AsyncSession for all requests
    async with AsyncSession() as session:
        progress_counter = {
            'processed': 0,
            'failed': 0,
            'total': unprocessed_count
        }
        semaphore = asyncio.Semaphore(concurrent_requests)

        tasks = []
        for user in unprocessed_users:
            task = asyncio.create_task(
                process_single_user(session, user, proxy_manager, data_csv_file,
                                    processed_usernames, semaphore, progress_counter)
            )
            tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    # Final summary
    print(f"\nFinished processing:")
    print(f"Successfully processed: {progress_counter['processed']}")
    print(f"Failed: {progress_counter['failed']}")
    print(f"Total attempted: {progress_counter['processed'] + progress_counter['failed']}")

    # Move JSON file if all users are done
    final_processed = get_processed_usernames(data_csv_file)
    all_usernames = [u.get('username') for u in data if u.get('username')]
    if all(u in final_processed for u in all_usernames):
        move_processed_json(ids_json_file)
        print("All users processed. JSON file moved to Processed Files folder.")

    # Proxy stats
    print("\nProxy Usage Statistics:")
    stats_summary = proxy_manager.get_proxy_stats_summary()
    print(f"Total available ports: {stats_summary['total_ports']}")
    print(f"Failed ports: {stats_summary['failed_ports']}")
    print(f"Unique ports used: {stats_summary['unique_ports_used']}")
    print("\nDetailed Proxy Stats:")
    for proxy_key, stats in proxy_manager.proxy_stats.items():
        if stats['total_requests'] > 0:
            success_rate = (stats['success'] / stats['total_requests']) * 100
            usage_count = proxy_manager.proxy_usage_count[proxy_key]
            print(f"{proxy_key}: {usage_count} uses, {stats['total_requests']} requests, "
                  f"{success_rate:.1f}% success, {stats['avg_response_time']:.2f}s avg time")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)