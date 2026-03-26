"""
HR LinkedIn Candidate Finder — Phase 1
AI-Powered LinkedIn Talent Discovery via Serper.dev Google Dorking

IMPORTANT:
- Uses Serper.dev (NOT SerpAPI) for Google search
- All API keys loaded from .streamlit/secrets.toml (NO frontend inputs)
- Uses `requests` library for Serper.dev API calls
"""

import streamlit as st
import requests
import re
import time
import pandas as pd
import io
import json
from apify_client import ApifyClient
import google.generativeai as genai

# ============================================================
# PAGE CONFIG & STYLING
# ============================================================

st.set_page_config(page_title="HR Candidate Finder", page_icon="🎯", layout="wide")

st.markdown("""
<style>
/* ---- Import Google Font ---- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

* { font-family: 'Inter', sans-serif; }

/* ---- Main Header ---- */
.main-header {
    background: linear-gradient(135deg, #6C5CE7 0%, #341f97 50%, #2d3436 100%);
    padding: 2rem 2.5rem; border-radius: 16px; margin-bottom: 1.8rem;
    box-shadow: 0 8px 32px rgba(108,92,231,0.3);
    position: relative; overflow: hidden;
}
.main-header::before {
    content: ''; position: absolute; top: -50%; right: -20%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    border-radius: 50%;
}
.main-header::after {
    content: ''; position: absolute; bottom: -30%; left: -10%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(108,92,231,0.3) 0%, transparent 70%);
    border-radius: 50%;
}
.main-header h1 { color: #fff !important; font-size: 2rem; position: relative; z-index: 1; margin-bottom: 0.3rem; }
.main-header p  { color: #dfe6e9 !important; font-size: 1.1rem; position: relative; z-index: 1; margin: 0; }

/* ---- Metric Cards ---- */
.metric-card {
    background: linear-gradient(135deg, #f8f9fa 0%, #fff 100%);
    padding: 18px 20px; border-radius: 12px;
    border-left: 4px solid #6C5CE7;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.metric-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0,0,0,0.1);
}
.metric-title { font-size: 0.8rem; color: #636e72; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.metric-value { font-size: 2rem; color: #2d3436; font-weight: 800; margin-top: 4px; }

/* ---- Search Input ---- */
div[data-testid="stTextInput"] input {
    border-radius: 12px !important; border: 2px solid #dfe6e9 !important;
    padding: 12px 16px !important; font-size: 1.05rem !important;
    transition: all 0.3s ease;
}
div[data-testid="stTextInput"] input:focus {
    border-color: #6C5CE7 !important;
    box-shadow: 0 0 0 3px rgba(108,92,231,0.15) !important;
}

/* ---- Status Card ---- */
.status-card {
    background: linear-gradient(135deg, #f0f0f7 0%, #fafbfc 100%);
    padding: 14px 16px; border-radius: 10px;
    border: 1px solid #e0e0e8;
    margin: 8px 0;
}

/* ---- Profile Card ---- */
.profile-card {
    background: #fff;
    border: 1px solid #e8e8f0;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: all 0.25s ease;
}
.profile-card:hover {
    border-color: #6C5CE7;
    box-shadow: 0 4px 16px rgba(108,92,231,0.12);
    transform: translateY(-1px);
}
.profile-name {
    font-size: 1.1rem; font-weight: 700; color: #2d3436;
    margin-bottom: 4px;
}
.profile-headline {
    font-size: 0.9rem; color: #636e72; margin-bottom: 6px;
}
.profile-org {
    font-size: 0.85rem; color: #6C5CE7; font-weight: 600;
}

/* ---- Welcome Card ---- */
.welcome-card {
    background: linear-gradient(135deg, #f8f7ff 0%, #f0eeff 100%);
    border: 1px solid #e0dcf5;
    border-radius: 16px;
    padding: 28px 24px;
    text-align: center;
    transition: transform 0.2s ease;
}
.welcome-card:hover { transform: translateY(-3px); }
.welcome-icon { font-size: 2.5rem; margin-bottom: 10px; }
.welcome-title { font-size: 1.1rem; font-weight: 700; color: #2d3436; margin-bottom: 6px; }
.welcome-desc { font-size: 0.88rem; color: #636e72; line-height: 1.5; }

/* ---- Buttons ---- */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6C5CE7 0%, #5a4bd1 100%) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; padding: 12px 24px !important;
    font-weight: 700 !important; font-size: 1rem !important;
    box-shadow: 0 4px 15px rgba(108,92,231,0.3) !important;
    transition: all 0.3s ease !important;
}
div.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 25px rgba(108,92,231,0.45) !important;
}

/* ---- Hide Streamlit defaults ---- */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ---- Header ----
st.markdown("""
<div class="main-header">
    <h1>🎯 HR Candidate Finder</h1>
    <p>AI-Powered LinkedIn Talent Discovery — Find the perfect candidates in minutes, not days</p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# CONSTANTS
# ============================================================

SEARCH_PRESETS = {
    "-- Custom Search --": "",
    "Software Engineer": "software engineer developer",
    "Data Scientist": "data scientist machine learning",
    "Product Manager": "product manager",
    "Marketing Manager": "marketing manager digital",
    "UI/UX Designer": "UI UX designer",
    "DevOps Engineer": "devops engineer cloud",
    "Sales Manager": "sales manager B2B",
    "HR Manager": "HR manager talent acquisition",
    "Financial Analyst": "financial analyst",
    "Business Analyst": "business analyst",
    "Full Stack Developer": "full stack developer",
    "Mobile Developer": "mobile developer iOS Android",
    "Content Writer": "content writer copywriter",
    "Graphic Designer": "graphic designer",
    "Project Manager": "project manager PMP",
    "Operations Manager": "operations manager",
    "Supply Chain Manager": "supply chain logistics manager",
    "Mechanical Engineer": "mechanical engineer",
    "Civil Engineer": "civil engineer",
    "CA / Accountant": "chartered accountant CA",
}

# ---- Hierarchical Location Data: Region → State → Cities ----
INDIA_REGIONS = {
    "North India": {
        "Rajasthan": [
            "Jaipur", "Jodhpur", "Kota", "Udaipur", "Ajmer", "Bikaner", "Alwar",
            "Bhilwara", "Sikar", "Pali", "Tonk", "Bharatpur", "Sri Ganganagar",
            "Hanumangarh", "Jhunjhunu", "Churu", "Nagaur", "Barmer", "Jaisalmer",
            "Chittorgarh", "Bundi", "Jhalawar", "Baran", "Sawai Madhopur",
            "Karauli", "Dausa", "Rajsamand", "Dungarpur", "Banswara",
            "Pratapgarh", "Sirohi", "Dholpur", "Mount Abu", "Pushkar",
            "Beawar", "Kishangarh", "Neemrana", "Bhiwadi",
        ],
        "Delhi NCR": [
            "New Delhi", "Noida", "Gurgaon", "Ghaziabad", "Faridabad",
            "Greater Noida", "Dwarka", "Rohini", "Saket",
        ],
        "Uttar Pradesh": [
            "Lucknow", "Kanpur", "Agra", "Varanasi", "Prayagraj", "Meerut",
            "Bareilly", "Aligarh", "Moradabad", "Gorakhpur", "Jhansi",
            "Mathura", "Firozabad", "Muzaffarnagar", "Saharanpur",
        ],
        "Haryana": [
            "Gurugram", "Faridabad", "Panipat", "Ambala", "Karnal",
            "Hisar", "Rohtak", "Sonipat", "Yamunanagar", "Panchkula",
        ],
        "Punjab": [
            "Chandigarh", "Ludhiana", "Amritsar", "Jalandhar", "Patiala",
            "Bathinda", "Mohali", "Pathankot", "Hoshiarpur",
        ],
        "Himachal Pradesh": [
            "Shimla", "Dharamshala", "Kullu", "Manali", "Solan", "Mandi",
        ],
        "Uttarakhand": [
            "Dehradun", "Haridwar", "Rishikesh", "Haldwani", "Roorkee", "Nainital",
        ],
        "Jammu & Kashmir": [
            "Srinagar", "Jammu", "Anantnag", "Baramulla",
        ],
    },
    "West India": {
        "Maharashtra": [
            "Mumbai", "Pune", "Nagpur", "Nashik", "Thane", "Navi Mumbai",
            "Aurangabad", "Solapur", "Kolhapur", "Sangli", "Amravati",
            "Akola", "Latur", "Jalgaon", "Dhule", "Pimpri-Chinchwad",
        ],
        "Gujarat": [
            "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar",
            "Bhavnagar", "Jamnagar", "Junagadh", "Anand", "Mehsana",
            "Morbi", "Navsari", "Bharuch", "Valsad", "GIFT City",
        ],
        "Goa": [
            "Panaji", "Margao", "Vasco da Gama", "Mapusa",
        ],
    },
    "South India": {
        "Karnataka": [
            "Bangalore", "Mysore", "Hubli", "Mangalore", "Belgaum",
            "Dharwad", "Gulbarga", "Bellary", "Shimoga", "Davangere",
        ],
        "Tamil Nadu": [
            "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem",
            "Tirunelveli", "Erode", "Vellore", "Tiruppur", "Thoothukudi",
        ],
        "Telangana": [
            "Hyderabad", "Warangal", "Nizamabad", "Karimnagar", "Khammam",
            "Secunderabad", "Cyberabad",
        ],
        "Andhra Pradesh": [
            "Visakhapatnam", "Vijayawada", "Guntur", "Tirupati", "Nellore",
            "Rajahmundry", "Kakinada", "Kurnool", "Amaravati",
        ],
        "Kerala": [
            "Kochi", "Thiruvananthapuram", "Kozhikode", "Thrissur",
            "Kollam", "Palakkad", "Kannur", "Alappuzha",
        ],
    },
    "East India": {
        "West Bengal": [
            "Kolkata", "Howrah", "Durgapur", "Siliguri", "Asansol",
            "Kharagpur", "Salt Lake City",
        ],
        "Odisha": [
            "Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur",
        ],
        "Bihar": [
            "Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga",
        ],
        "Jharkhand": [
            "Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Hazaribagh",
        ],
    },
    "Central India": {
        "Madhya Pradesh": [
            "Bhopal", "Indore", "Gwalior", "Jabalpur", "Ujjain",
            "Sagar", "Dewas", "Rewa", "Satna",
        ],
        "Chhattisgarh": [
            "Raipur", "Bilaspur", "Bhilai", "Korba", "Durg",
        ],
    },
    "North-East India": {
        "Assam": ["Guwahati", "Dibrugarh", "Silchar", "Jorhat"],
        "Meghalaya": ["Shillong"],
        "Manipur": ["Imphal"],
        "Tripura": ["Agartala"],
        "Nagaland": ["Dimapur", "Kohima"],
        "Mizoram": ["Aizawl"],
        "Arunachal Pradesh": ["Itanagar"],
        "Sikkim": ["Gangtok"],
    },
    "International": {
        "Middle East": ["Dubai", "Abu Dhabi", "Riyadh", "Doha", "Kuwait City", "Muscat"],
        "Southeast Asia": ["Singapore", "Bangkok", "Kuala Lumpur", "Jakarta"],
        "Europe": ["London", "Berlin", "Amsterdam", "Dublin", "Paris"],
        "North America": ["New York", "San Francisco", "Toronto", "Chicago", "Seattle"],
        "Oceania": ["Sydney", "Melbourne"],
    },
}

# Flatten all cities for backward compatibility with query generator
def _flatten_all_cities():
    cities = []
    for region in INDIA_REGIONS.values():
        for state_cities in region.values():
            cities.extend(state_cities)
    return cities

CITIES_LIST = _flatten_all_cities()

# Helper: get all states for a region
def get_states_for_region(region_name):
    return list(INDIA_REGIONS.get(region_name, {}).keys())

# Helper: get cities for a state within a region
def get_cities_for_state(region_name, state_name):
    return INDIA_REGIONS.get(region_name, {}).get(state_name, [])

EXPERIENCE_KEYWORDS = {
    "Entry Level (0-2 yrs)": ["fresher", "junior", "entry level", "intern", "trainee", "graduate"],
    "Mid Level (3-5 yrs)": ["3+ years", "4+ years", "5+ years", "mid level", "associate"],
    "Senior (5-10 yrs)": ["senior", "lead", "5+ years", "7+ years", "experienced"],
    "Lead/Staff (10+ yrs)": ["principal", "staff", "director", "head", "vp", "10+ years"],
}

INDUSTRY_KEYWORDS = {
    "IT/Software": ["software", "technology", "IT", "tech", "saas", "cloud"],
    "Finance/Banking": ["finance", "banking", "fintech", "investment"],
    "Healthcare": ["healthcare", "hospital", "pharma", "medical"],
    "Education": ["education", "edtech", "school", "university"],
    "E-commerce": ["ecommerce", "e-commerce", "marketplace", "retail"],
    "Manufacturing": ["manufacturing", "production", "factory"],
    "Consulting": ["consulting", "advisory", "strategy"],
    "Media/Advertising": ["media", "advertising", "marketing agency"],
    "FMCG": ["fmcg", "consumer goods"],
    "Automotive": ["automotive", "automobile", "EV"],
    "Pharma": ["pharmaceutical", "pharma", "clinical"],
    "Telecom": ["telecom", "telecommunications"],
    "Real Estate": ["real estate", "property", "construction"],
    "Government/PSU": ["government", "PSU", "public sector"],
}

COMPANY_BLACKLIST = [
    'Google', 'Microsoft', 'Amazon', 'Meta', 'Facebook', 'Apple', 'Netflix',
    'Infosys', 'TCS', 'Wipro', 'HCL', 'Cognizant', 'Accenture', 'Deloitte',
    'PwC', 'KPMG', 'EY', 'McKinsey', 'BCG', 'Bain',
]

MAX_SERPER_QUERIES = 50
MAX_APIFY_SCRAPES = 300
MAX_GEMINI_CALLS = 300

# System pages to exclude from LinkedIn profile parsing
SYSTEM_PAGES = [
    'login', 'signup', 'jobs', 'feed', 'mynetwork', 'messaging',
    'notifications', 'learning', 'pulse', 'posts', 'company', 'company/login',
    'search', 'groups', 'events', 'premium', 'business', 'talent', 'sales',
    'help', 'accessibility', 'legal',
]

_INDIVIDUAL_RE = re.compile(r'linkedin\.com/in/([a-zA-Z0-9_-]+)', re.IGNORECASE)


# ============================================================
# API KEY MANAGEMENT (Backend Only)
# ============================================================

def load_api_keys():
    """Load all API keys from st.secrets. Returns dict of keys and list of missing ones."""
    keys = {}
    missing = []

    required = {
        "SERPER_API_KEY": "Serper.dev (Google Search)",
        "GOOGLE_API_KEY": "Google Gemini AI",
    }

    for key_name, label in required.items():
        try:
            val = st.secrets.get(key_name, "")
            if val and val.strip():
                keys[key_name] = val.strip()
            else:
                missing.append(label)
        except Exception:
            missing.append(label)

    # Apify keys — load all 4, order matters for cost optimization
    # KEY PRIORITY: Free keys first (2,3,4), Paid key last (1)
    apify_key_order = ["APIFY_KEY_2", "APIFY_KEY_3", "APIFY_KEY_4", "APIFY_KEY_1"]
    apify_keys = []
    for ak in apify_key_order:
        try:
            val = st.secrets.get(ak, "")
            if val and val.strip():
                apify_keys.append({"key": val.strip(), "name": ak, "is_paid": ak == "APIFY_KEY_1"})
        except Exception:
            pass

    if not apify_keys:
        missing.append("Apify (at least 1 key)")

    keys["APIFY_KEYS"] = apify_keys
    return keys, missing


# ============================================================
# SERPER.DEV SEARCH (NOT SerpAPI!)
# ============================================================

def serper_search(query: str, api_key: str, num_results: int = 20, page: int = 1) -> list:
    """
    Execute a Google search via Serper.dev API.
    Returns list of organic results.

    IMPORTANT: This is serper.dev, NOT serpapi.com
    Endpoint: POST https://google.serper.dev/search
    Auth: X-API-KEY header
    """
    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "q": query,
        "num": num_results,
        "gl": "in",      # India
        "hl": "en",
        "page": page,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("organic", [])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise ValueError("Invalid Serper.dev API key")
        elif e.response.status_code == 429:
            raise ValueError("Serper.dev rate limit reached")
        raise
    except Exception as e:
        raise ValueError(f"Serper.dev error: {str(e)}")


# ============================================================
# LINKEDIN URL PARSER
# ============================================================

def extract_linkedin_info_from_url(url: str, snippet: str = "", title: str = "") -> dict | None:
    """Parse a Serper.dev result into a profile dict. Only individual profiles."""
    url = (url or "").strip()
    if not url:
        return None

    match = _INDIVIDUAL_RE.search(url)
    if not match:
        return None

    username = match.group(1).lower()
    if username in SYSTEM_PAGES:
        return None

    normalized_url = f"https://www.linkedin.com/in/{username}"

    name, headline, organization = "", "", ""
    if title:
        title_clean = title.replace(" | LinkedIn", "").replace("| LinkedIn", "").strip()
        parts = [p.strip() for p in title_clean.split(" - ")]
        if len(parts) >= 1:
            name = parts[0]
        if len(parts) >= 2:
            headline = parts[1]
        if len(parts) >= 3:
            organization = parts[2]

    return {
        "url": normalized_url,
        "name": name,
        "headline": headline,
        "organization": organization,
        "profile_type": "individual",
        "snippet": (snippet or "")[:300],
    }


# ============================================================
# QUERY GENERATOR (Google Dorking)
# ============================================================

def generate_candidate_queries(keyword: str, experience_levels: list, industries: list, cities: list, round_num: int) -> tuple:
    """Generate Serper.dev search queries using Google dork syntax.
    Each round produces DIFFERENT queries to avoid duplicate results."""
    queries = []
    
    # Sanitize keyword
    kw = keyword.strip()
    for char in ['&', '+', '/', '\\', '|', ';', ':', ',']:
        kw = kw.replace(char, ' ')
    kw = ' '.join(kw.split())
    
    # Check if we have specific cities to target
    has_specific_cities = cities and "All Cities" not in cities and len(cities) > 0
    
    if round_num == 0:
        if has_specific_cities:
            # When cities are specified, USE THEM in round 0 queries
            # Pick first 5 cities for round 0
            round_cities = cities[:5]
            for city in round_cities:
                queries.append(f'site:linkedin.com/in/ "{kw}" "{city}"')
            # Also add one broad query with the state/region context
            queries.append(f'site:linkedin.com/in/ "{kw}" India')
        else:
            queries = [
                f'site:linkedin.com/in/ "{kw}" India',
                f'site:linkedin.com/in/ "{kw}" "experience" India',
                f'site:linkedin.com/in/ "{kw}" "currently working"',
                f'site:linkedin.com/in/ "{kw}" "open to work"',
                f'site:linkedin.com/in/ "{kw}" "looking for opportunities"',
            ]
    
    elif round_num == 1:
        if has_specific_cities:
            # Use next batch of cities
            round_cities = cities[5:12]
            for city in round_cities:
                queries.append(f'site:linkedin.com/in/ "{kw}" "{city}"')
            if not round_cities:
                # Fewer than 5 cities total — reuse with different query patterns
                for city in cities[:5]:
                    queries.append(f'site:linkedin.com/in/ "{kw}" "experience" {city}')
        else:
            queries = [
                f'site:linkedin.com/in/ "{kw}" "years of experience"',
                f'site:linkedin.com/in/ "{kw}" "skills" "projects"',
                f'site:linkedin.com/in/ "{kw}" "certified" OR "certification"',
                f'site:linkedin.com/in/ "{kw}" "professional" "experienced"',
                f'site:linkedin.com/in/ "{kw}" "resume" OR "portfolio"',
            ]
    
    elif 2 <= round_num <= 5:
        all_cities = cities if has_specific_cities else CITIES_LIST
        start_idx = (round_num - 2) * 6
        round_cities = all_cities[start_idx:start_idx + 6]
        for city in round_cities:
            queries.append(f'site:linkedin.com/in/ "{kw}" "{city}"')
            queries.append(f'site:linkedin.com/in/ "{kw}" "hiring" OR "available" {city}')
    
    elif 6 <= round_num <= 8:
        if has_specific_cities:
            # Re-run city queries with alternate phrasings
            start_idx = (round_num - 6) * 6
            round_cities = cities[start_idx:start_idx + 6]
            for city in round_cities:
                queries.append(f'site:linkedin.com/in/ "{kw}" "executive" {city}')
                queries.append(f'site:linkedin.com/in/ "{kw}" "manager" {city}')
        else:
            industry_terms = []
            for ind in (industries or []):
                if ind != "All Industries" and ind in INDUSTRY_KEYWORDS:
                    industry_terms.extend(INDUSTRY_KEYWORDS[ind][:2])
            if not industry_terms:
                industry_terms = ["technology", "finance", "healthcare", "education"]
            start_idx = (round_num - 6) * 3
            for term in industry_terms[start_idx:start_idx + 3]:
                queries.append(f'site:linkedin.com/in/ "{kw}" "{term}" India')
                queries.append(f'site:linkedin.com/in/ "{kw}" "{term}"')
    
    else:
        page_num = round_num - 8
        if has_specific_cities:
            for city in cities[:3]:
                queries.append(f'site:linkedin.com/in/ "{kw}" "{city}"')
        else:
            queries = [
                f'site:linkedin.com/in/ "{kw}" India',
                f'site:linkedin.com/in/ "{kw}" "experience"',
                f'site:linkedin.com/in/ "{kw}" "currently working"',
            ]
        return queries, page_num
    
    return queries, 1


# ============================================================
# DISCOVERY FUNCTION
# ============================================================

def discover_via_serper(keyword, experience_levels, industries, cities, serper_key, status_container, round_num=0):
    """Execute Serper.dev queries for one round. Returns list of unique profiles."""
    queries, page_num = generate_candidate_queries(keyword, experience_levels, industries, cities, round_num)
    all_profiles = []
    seen_urls = set()

    # Also exclude already-discovered URLs from session state
    if "all_discovered_urls" in st.session_state:
        seen_urls.update(st.session_state["all_discovered_urls"])

    for i, query in enumerate(queries):
        try:
            results = serper_search(query, serper_key, num_results=20, page=page_num)
            status_container.write(f"🔍 Query {i+1}/{len(queries)} → {len(results)} results")

            for item in results:
                # Serper.dev uses "link" not "url"
                profile = extract_linkedin_info_from_url(
                    item.get("link", ""),
                    item.get("snippet", ""),
                    item.get("title", ""),
                )
                if profile and profile["url"] not in seen_urls:
                    seen_urls.add(profile["url"])
                    all_profiles.append(profile)
        except ValueError as e:
            err = str(e).lower()
            if "invalid" in err:
                status_container.write("❌ Serper.dev: Invalid API key.")
                return all_profiles
            if "rate limit" in err:
                status_container.write("⚠️ Serper.dev rate limit. Waiting...")
                time.sleep(5)
                continue
            status_container.write(f"⚠️ {e}")
        except Exception as e:
            status_container.write(f"⚠️ Serper error: {e}")

        time.sleep(1.5)

    status_container.write(f"📊 Round {round_num}: **{len(all_profiles)}** unique profiles discovered")
    return all_profiles


# ============================================================
# DEDUPLICATION SYSTEM
# ============================================================

def load_existing_candidates(uploaded_file):
    """Load previously sourced candidates from CSV for deduplication.
    Returns (urls_set, names_set, count, error)."""
    if uploaded_file is None:
        return set(), set(), 0, None

    try:
        df = pd.read_csv(uploaded_file)
        urls = set()
        names = set()

        # Try common column names for URLs
        url_columns = ["url", "linkedin_url", "profile_url", "LinkedIn URL", "linkedin", "URL", "Link", "link"]
        for col in url_columns:
            if col in df.columns:
                for val in df[col].dropna():
                    url_str = str(val).strip().lower()
                    # Normalize URL
                    match = _INDIVIDUAL_RE.search(url_str)
                    if match:
                        urls.add(f"https://www.linkedin.com/in/{match.group(1).lower()}")
                break

        # Try common column names for names
        name_columns = ["name", "full_name", "Name", "Full Name", "candidate_name", "Candidate Name"]
        for col in name_columns:
            if col in df.columns:
                for val in df[col].dropna():
                    name_str = str(val).strip().lower()
                    if len(name_str) > 2:
                        names.add(name_str)
                break

        return urls, names, len(df), None
    except Exception as e:
        return set(), set(), 0, str(e)


def deduplicate_profiles(profiles, existing_urls, existing_names):
    """Remove profiles that match previously sourced candidates."""
    if not existing_urls and not existing_names:
        return profiles, 0

    unique = []
    duplicates = 0

    for p in profiles:
        url_lower = p["url"].lower()
        name_lower = p.get("name", "").strip().lower()

        if url_lower in existing_urls:
            duplicates += 1
            continue
        if name_lower and len(name_lower) > 4 and name_lower in existing_names:
            duplicates += 1
            continue

        unique.append(p)

    return unique, duplicates


# ============================================================
# PHASE 2: APIFY LINKEDIN PROFILE ENRICHMENT
# ============================================================

class ApifyKeyManager:
    """
    Manages multiple Apify keys with COST OPTIMIZATION:
    Free keys are used first, paid key is last resort.
    Keys are loaded in order: [FREE_2, FREE_3, FREE_4, PAID_1]
    """

    def __init__(self, key_configs: list):
        self.key_configs = [k for k in key_configs if k.get("key")]
        self.current_index = 0
        self.exhausted_keys: set = set()
        self.cost_tracker = {"profiles_scraped": 0, "estimated_cost": 0.0}

    def get_current_key(self) -> str | None:
        while self.current_index < len(self.key_configs):
            if self.current_index not in self.exhausted_keys:
                return self.key_configs[self.current_index]["key"]
            self.current_index += 1
        return None

    def get_current_key_info(self) -> dict | None:
        while self.current_index < len(self.key_configs):
            if self.current_index not in self.exhausted_keys:
                return self.key_configs[self.current_index]
            self.current_index += 1
        return None

    def mark_exhausted(self) -> str | None:
        self.exhausted_keys.add(self.current_index)
        self.current_index += 1
        if self.current_index < len(self.key_configs):
            return self.key_configs[self.current_index]["key"]
        return None

    def get_status(self) -> str:
        if not self.key_configs:
            return "No keys loaded"
        active = len(self.key_configs) - len(self.exhausted_keys)
        current = self.get_current_key_info()
        key_type = ""
        if current:
            key_type = " (💰 paid)" if current["is_paid"] else " (🆓 free)"
        return f"{active}/{len(self.key_configs)} active — using {current['name'] if current else 'none'}{key_type}"

    def add_cost(self, profiles_count: int, cost_per_1k: float = 2.5):
        self.cost_tracker["profiles_scraped"] += profiles_count
        self.cost_tracker["estimated_cost"] += (profiles_count / 1000) * cost_per_1k

    def get_cost_summary(self) -> str:
        return f"~${self.cost_tracker['estimated_cost']:.2f} ({self.cost_tracker['profiles_scraped']} profiles)"

    def has_keys(self) -> bool:
        return len(self.key_configs) > 0

    def is_exhausted(self) -> bool:
        return self.get_current_key() is None

    def is_using_paid_key(self) -> bool:
        info = self.get_current_key_info()
        return info["is_paid"] if info else False


# Multi-Actor Profile Scraping — cheapest first
APIFY_PROFILE_ACTORS = [
    {
        "id": "get-leads/linkedin-scraper",
        "label": "GetLeads ($2.50/1k)",
        "cost_per_1k": 2.50,
        "build_input": lambda urls: {"mode": "profiles", "urls": urls, "maxResults": len(urls)},
    },
    {
        "id": "supreme_coder/linkedin-profile-scraper",
        "label": "SupremeCoder ($3/1k)",
        "cost_per_1k": 3.00,
        "build_input": lambda urls: {"urls": [{"url": u} for u in urls]},
    },
    {
        "id": "curious_coder/linkedin-profile-scraper",
        "label": "CuriousCoder ($3/1k)",
        "cost_per_1k": 3.00,
        "build_input": lambda urls: {"profileUrls": urls},
    },
    {
        "id": "harvestapi/linkedin-profile-scraper",
        "label": "HarvestAPI ($4/1k)",
        "cost_per_1k": 4.00,
        "build_input": lambda urls: {
            "profileScraperMode": "Profile details no email ($4 per 1k)",
            "queries": urls,
        },
    },
]


def _parse_apify_profile_item(item: dict) -> dict:
    """Robust parser handling multiple Apify actor response schemas.
    Extracts standardized profile data from any supported actor."""
    if not item or not isinstance(item, dict):
        return {}

    # --- LinkedIn URL ---
    linkedin_url = ""
    for key in ["linkedinUrl", "linkedin_url", "url", "profileUrl", "profile_url", "linkedInUrl"]:
        val = item.get(key, "")
        if val and "linkedin.com/in/" in str(val):
            match = _INDIVIDUAL_RE.search(str(val))
            if match:
                linkedin_url = f"https://www.linkedin.com/in/{match.group(1).lower()}"
                break

    if not linkedin_url:
        return {}

    # --- Name ---
    full_name = ""
    for key in ["fullName", "full_name", "name", "firstName"]:
        val = item.get(key, "")
        if val and str(val).strip():
            full_name = str(val).strip()
            break
    if not full_name:
        first = item.get("firstName", "")
        last = item.get("lastName", "")
        if first or last:
            full_name = f"{first} {last}".strip()

    # --- Headline ---
    headline = ""
    for key in ["headline", "title", "tagline"]:
        val = item.get(key, "")
        if val and str(val).strip():
            headline = str(val).strip()
            break

    # --- Location ---
    location = ""
    for key in ["location", "addressLocality", "city", "geo"]:
        val = item.get(key, "")
        if isinstance(val, dict):
            location = val.get("city", val.get("full", val.get("name", "")))
        elif val and str(val).strip():
            location = str(val).strip()
            break

    # --- About ---
    about = ""
    for key in ["about", "summary", "description"]:
        val = item.get(key, "")
        if val and str(val).strip():
            about = str(val).strip()[:500]
            break

    # --- Connections & Followers ---
    connections = 0
    for key in ["connections", "connectionsCount", "numberOfConnections"]:
        val = item.get(key)
        if val is not None:
            try:
                connections = int(str(val).replace("+", "").replace(",", "").strip())
            except (ValueError, TypeError):
                pass
            break

    followers = 0
    for key in ["followers", "followersCount", "numberOfFollowers"]:
        val = item.get(key)
        if val is not None:
            try:
                followers = int(str(val).replace("+", "").replace(",", "").strip())
            except (ValueError, TypeError):
                pass
            break

    # --- Current Company & Role ---
    current_company = ""
    current_role = ""
    experience_years = 0

    # Try direct fields first
    for key in ["company", "currentCompany", "companyName", "organizationName"]:
        val = item.get(key, "")
        if val and str(val).strip():
            current_company = str(val).strip()
            break

    for key in ["position", "currentPosition", "jobTitle"]:
        val = item.get(key, "")
        if val and str(val).strip():
            current_role = str(val).strip()
            break

    # Try experience array
    raw_experience = item.get("experience", item.get("experiences", item.get("positions", [])))
    if isinstance(raw_experience, list) and raw_experience:
        first_exp = raw_experience[0] if isinstance(raw_experience[0], dict) else {}
        if not current_company:
            current_company = first_exp.get("company", first_exp.get("companyName", ""))
        if not current_role:
            current_role = first_exp.get("title", first_exp.get("position", first_exp.get("role", "")))
        experience_years = len(raw_experience)
    elif isinstance(raw_experience, str):
        raw_experience = []

    # --- Education ---
    raw_education = item.get("education", item.get("educations", []))
    education = ""
    if isinstance(raw_education, list) and raw_education:
        first_edu = raw_education[0] if isinstance(raw_education[0], dict) else {}
        school = first_edu.get("school", first_edu.get("schoolName", first_edu.get("institution", "")))
        degree = first_edu.get("degree", first_edu.get("degreeName", ""))
        field = first_edu.get("field", first_edu.get("fieldOfStudy", ""))
        parts = [p for p in [degree, field, school] if p]
        education = " | ".join(parts)
    elif isinstance(raw_education, str):
        education = raw_education
        raw_education = []

    # --- Skills ---
    skills_raw = item.get("skills", item.get("skill", []))
    skills = []
    if isinstance(skills_raw, list):
        for s in skills_raw:
            if isinstance(s, dict):
                skills.append(s.get("name", s.get("skill", str(s))))
            elif isinstance(s, str) and s.strip():
                skills.append(s.strip())
    elif isinstance(skills_raw, str) and skills_raw.strip():
        skills = [s.strip() for s in skills_raw.split(",")]

    # --- Certifications ---
    certs_raw = item.get("certifications", item.get("certificates", []))
    certifications = []
    if isinstance(certs_raw, list):
        for c in certs_raw:
            if isinstance(c, dict):
                certifications.append(c.get("name", c.get("title", str(c))))
            elif isinstance(c, str) and c.strip():
                certifications.append(c.strip())

    # --- Languages ---
    langs_raw = item.get("languages", [])
    languages = []
    if isinstance(langs_raw, list):
        for l in langs_raw:
            if isinstance(l, dict):
                languages.append(l.get("name", l.get("language", str(l))))
            elif isinstance(l, str) and l.strip():
                languages.append(l.strip())

    # --- Profile Picture ---
    profile_picture_url = ""
    for key in ["profilePicture", "profilePictureUrl", "profilePic", "avatar", "imageUrl", "img"]:
        val = item.get(key, "")
        if val and str(val).startswith("http"):
            profile_picture_url = str(val)
            break

    result = {
        "url": linkedin_url,
        "name": full_name,
        "headline": headline,
        "location": location,
        "about": about,
        "followers": followers,
        "connections": connections,
        "current_company": current_company,
        "current_role": current_role,
        "organization": current_company,  # backward compat
        "experience_years": experience_years,
        "education": education,
        "skills": skills,
        "certifications": certifications,
        "languages": languages,
        "raw_experience": raw_experience if isinstance(raw_experience, list) else [],
        "raw_education": raw_education if isinstance(raw_education, list) else [],
        "enrichment_status": "enriched",
        "profile_picture_url": profile_picture_url,
        "profile_type": "individual",
    }
    return _sanitize_profile_fields(result)


def scrape_linkedin_profiles(urls: list, apify_manager: ApifyKeyManager, status_container) -> list:
    """Scrape LinkedIn profiles using Apify. Tries cheapest actor first, rotates keys on failure."""
    if not urls or apify_manager.is_exhausted():
        return []

    all_results = []
    batch_size = 15
    # Remember last working actor in session_state
    working_actor_idx = st.session_state.get("_apify_working_actor_idx", 0)

    for batch_start in range(0, len(urls), batch_size):
        batch_urls = urls[batch_start:batch_start + batch_size]
        batch_scraped = False

        if apify_manager.is_exhausted():
            status_container.write("⚠️ All Apify keys exhausted. Remaining profiles will use Serper-only data.")
            break

        # Warn before using paid key
        if apify_manager.is_using_paid_key():
            status_container.write("⚠️ 💰 Now using PAID Apify key (all free keys exhausted)")

        current_key = apify_manager.get_current_key()
        if not current_key:
            break

        # Try actors starting from last working one
        actor_indices = list(range(working_actor_idx, len(APIFY_PROFILE_ACTORS))) + list(range(0, working_actor_idx))

        for actor_idx in actor_indices:
            if batch_scraped:
                break

            actor = APIFY_PROFILE_ACTORS[actor_idx]
            try:
                client = ApifyClient(current_key)
                actor_input = actor["build_input"](batch_urls)

                status_container.write(
                    f"🔄 Batch {batch_start // batch_size + 1} — {actor['label']} — {len(batch_urls)} profiles"
                )

                run = client.actor(actor["id"]).call(
                    run_input=actor_input,
                    timeout_secs=180,
                )

                if run and run.get("status") == "SUCCEEDED":
                    dataset_id = run.get("defaultDatasetId")
                    if dataset_id:
                        items = list(client.dataset(dataset_id).iterate_items())
                        parsed = []
                        for item in items:
                            profile = _parse_apify_profile_item(item)
                            if profile and profile.get("url"):
                                parsed.append(profile)

                        if parsed:
                            all_results.extend(parsed)
                            apify_manager.add_cost(len(parsed), actor["cost_per_1k"])
                            st.session_state["_apify_working_actor_idx"] = actor_idx
                            working_actor_idx = actor_idx
                            batch_scraped = True
                            status_container.write(
                                f"✅ Got {len(parsed)}/{len(batch_urls)} profiles — Cost: {apify_manager.get_cost_summary()}"
                            )
                        else:
                            status_container.write(f"⚪ {actor['label']}: 0 results, trying next actor...")
                else:
                    status_container.write(f"⚠️ {actor['label']}: Run failed, trying next actor...")

            except Exception as e:
                err_str = str(e).lower()
                if "402" in err_str or "quota" in err_str or "payment" in err_str or "limit" in err_str:
                    key_info = apify_manager.get_current_key_info()
                    key_name = key_info["name"] if key_info else "unknown"
                    status_container.write(f"💸 {key_name} quota exhausted. Rotating to next key...")
                    next_key = apify_manager.mark_exhausted()
                    if next_key:
                        current_key = next_key
                        if apify_manager.is_using_paid_key():
                            status_container.write("⚠️ 💰 Switching to PAID Apify key")
                        break  # Retry this batch with new key
                    else:
                        status_container.write("❌ All Apify keys exhausted.")
                        return all_results
                elif "429" in err_str or "rate" in err_str:
                    status_container.write(f"⏳ Rate limited on {actor['label']}. Waiting 30s...")
                    time.sleep(30)
                    break  # Retry this batch
                else:
                    status_container.write(f"⚠️ {actor['label']} error: {str(e)[:100]}. Trying next actor...")
                    continue

        if not batch_scraped and not apify_manager.is_exhausted():
            status_container.write(f"⚠️ Batch {batch_start // batch_size + 1}: All actors failed for this batch.")

        time.sleep(3)  # Delay between batches

    return all_results


def enrich_discovered_profiles(discovered: list, apify_manager: ApifyKeyManager, status_container) -> list:
    """Enrich discovered profiles with full data from Apify.
    Falls back to Serper-only data for profiles that can't be enriched."""
    if not discovered:
        return []

    # Only process individual profiles
    urls_to_enrich = []
    url_to_serper = {}  # Map URL -> original Serper data
    for p in discovered:
        if p.get("profile_type") == "individual" and p.get("url"):
            urls_to_enrich.append(p["url"])
            url_to_serper[p["url"]] = p

    if not urls_to_enrich:
        return discovered

    if not apify_manager.has_keys() or apify_manager.is_exhausted():
        status_container.write("⚠️ No Apify keys available. Using Serper-only data.")
        for p in discovered:
            p["enrichment_status"] = "serper_only"
        return discovered

    status_container.write(f"🔄 Enriching {len(urls_to_enrich)} profiles via Apify...")

    # Scrape profiles
    enriched_items = scrape_linkedin_profiles(urls_to_enrich, apify_manager, status_container)

    # Build URL -> enriched data map
    enriched_map = {}
    for item in enriched_items:
        if item.get("url"):
            enriched_map[item["url"]] = item

    # Merge: enriched data takes priority, fall back to Serper data
    result = []
    enriched_count = 0
    for p in discovered:
        url = p.get("url", "")
        if url in enriched_map:
            merged = {**p, **enriched_map[url]}
            # Keep Serper snippet if enriched about is empty
            if not merged.get("about") and p.get("snippet"):
                merged["about"] = p["snippet"]
            merged["enrichment_status"] = "enriched"
            result.append(merged)
            enriched_count += 1
        else:
            p["enrichment_status"] = "serper_only"
            result.append(p)

    status_container.write(
        f"✅ Enriched {enriched_count}/{len(urls_to_enrich)} profiles — Cost: {apify_manager.get_cost_summary()}"
    )

    # Post-enrichment: extract missing fields from text, then sanitize all fields
    for p in result:
        _post_enrich_extract(p)
        _sanitize_profile_fields(p)

    return result


def _post_enrich_extract(profile: dict) -> dict:
    """Extract missing fields from headline/about text when Apify returns limited data."""

    # --- Extract company and role from headline ---
    headline = profile.get("headline", "")
    if headline and not profile.get("current_company"):
        if " at " in headline:
            parts = headline.split(" at ", 1)
            if len(parts) == 2:
                if not profile.get("current_role"):
                    profile["current_role"] = parts[0].strip()
                profile["current_company"] = parts[1].strip().split("|")[0].strip().split("·")[0].strip()
        elif " | " in headline:
            parts = headline.split(" | ", 1)
            if len(parts) == 2:
                if not profile.get("current_role"):
                    profile["current_role"] = parts[0].strip()
                profile["current_company"] = parts[1].strip()
        elif " - " in headline:
            parts = headline.split(" - ", 1)
            if len(parts) == 2:
                if not profile.get("current_role"):
                    profile["current_role"] = parts[0].strip()
                profile["current_company"] = parts[1].strip()

    # If we still don't have a role, use the full headline
    if not profile.get("current_role") and headline:
        profile["current_role"] = headline[:80]

    # --- Copy organization to current_company if missing ---
    if not profile.get("current_company") and profile.get("organization"):
        profile["current_company"] = profile["organization"]

    # --- Extract skills from about/snippet if skills list is empty ---
    if not profile.get("skills") or len(profile.get("skills", [])) == 0:
        about = profile.get("about", "") or profile.get("snippet", "")
        if about:
            skills_match = re.search(r'(?:skills?|expertise|specialit(?:y|ies))[\s:]+([^\n.]+)', about, re.IGNORECASE)
            if skills_match:
                raw_skills = skills_match.group(1)
                profile["skills"] = [s.strip() for s in re.split(r'[,•·|]', raw_skills) if s.strip() and len(s.strip()) > 2][:8]

    # --- Ensure full_name is set ---
    if not profile.get("full_name"):
        profile["full_name"] = profile.get("name", "Unknown")

    # --- Normalize connections ---
    conn = profile.get("connections", 0)
    if isinstance(conn, str):
        conn_clean = conn.replace("+", "").replace(",", "").strip()
        try:
            profile["connections"] = int(conn_clean)
        except ValueError:
            profile["connections"] = 0

    return profile


def _sanitize_profile_fields(profile: dict) -> dict:
    """Ensure all display fields are clean strings, not raw dicts/lists.
    This is the LAST step before a profile is used for display/export."""

    # --- Fix current_role if it's a list/dict ---
    role = profile.get("current_role", "")
    if isinstance(role, (list, dict)):
        if isinstance(role, list) and role:
            first = role[0] if isinstance(role[0], dict) else {}
            extracted_role = (
                first.get("title", "") or
                first.get("position", "") or
                first.get("role", "") or
                ""
            )
            profile["current_role"] = str(extracted_role).strip()
        elif isinstance(role, dict):
            profile["current_role"] = (
                role.get("title", "") or
                role.get("position", "") or
                role.get("role", "") or
                ""
            )
        else:
            profile["current_role"] = ""
    elif role and not isinstance(role, str):
        profile["current_role"] = str(role)

    # --- Fix current_company if it's a list/dict ---
    company = profile.get("current_company", "")
    if isinstance(company, (list, dict)):
        if isinstance(company, list) and company:
            first = company[0] if isinstance(company[0], dict) else {}
            profile["current_company"] = (
                first.get("companyName", "") or
                first.get("company", "") or
                first.get("name", "") or
                ""
            )
        elif isinstance(company, dict):
            profile["current_company"] = (
                company.get("companyName", "") or
                company.get("company", "") or
                company.get("name", "") or
                ""
            )
        else:
            profile["current_company"] = ""
    elif company and not isinstance(company, str):
        profile["current_company"] = str(company)

    # --- Fix headline if it's a list/dict ---
    headline = profile.get("headline", "")
    if isinstance(headline, (list, dict)):
        profile["headline"] = str(headline)[:200] if headline else ""

    # --- Fix location if it's a dict ---
    location = profile.get("location", "")
    if isinstance(location, dict):
        profile["location"] = (
            location.get("city", "") or
            location.get("full", "") or
            location.get("name", "") or
            location.get("default", "") or
            ""
        )
    elif location and not isinstance(location, str):
        profile["location"] = str(location)

    # --- Fix education if it's a list ---
    education = profile.get("education", "")
    if isinstance(education, (list, dict)):
        if isinstance(education, list) and education:
            first = education[0] if isinstance(education[0], dict) else {}
            school = first.get("school", first.get("schoolName", first.get("institution", "")))
            degree = first.get("degree", first.get("degreeName", ""))
            field = first.get("field", first.get("fieldOfStudy", ""))
            parts = [p for p in [degree, field, school] if p and isinstance(p, str)]
            profile["education"] = " | ".join(parts)
        else:
            profile["education"] = ""

    # --- Fix skills if entries are dicts ---
    skills = profile.get("skills", [])
    if isinstance(skills, list):
        clean_skills = []
        for s in skills:
            if isinstance(s, dict):
                clean_skills.append(s.get("name", s.get("skill", "")))
            elif isinstance(s, str) and s.strip():
                clean_skills.append(s.strip())
        profile["skills"] = [s for s in clean_skills if s]
    elif isinstance(skills, str):
        profile["skills"] = [s.strip() for s in skills.split(",") if s.strip()]

    # --- Fix about if it contains raw data ---
    about = profile.get("about", "")
    if isinstance(about, (list, dict)):
        profile["about"] = str(about)[:500] if about else ""

    # --- After sanitizing, run headline parsing for any still-missing fields ---
    headline = profile.get("headline", "")
    if headline and isinstance(headline, str):
        if not profile.get("current_role"):
            if " at " in headline:
                parts = headline.split(" at ", 1)
                profile["current_role"] = parts[0].strip()[:100]
                if not profile.get("current_company"):
                    profile["current_company"] = parts[1].strip().split("|")[0].strip()[:100]
            elif " | " in headline:
                parts = headline.split(" | ", 1)
                profile["current_role"] = parts[0].strip()[:100]
                if not profile.get("current_company"):
                    profile["current_company"] = parts[1].strip()[:100]
            elif " - " in headline:
                parts = headline.split(" - ", 1)
                profile["current_role"] = parts[0].strip()[:100]
                if not profile.get("current_company"):
                    profile["current_company"] = parts[1].strip()[:100]
            else:
                profile["current_role"] = headline[:100]

    # --- Ensure organization is synced ---
    if not profile.get("current_company") and profile.get("organization"):
        org = profile["organization"]
        if isinstance(org, str):
            profile["current_company"] = org

    return profile


# ============================================================
# PHASE 3: SMART FILTERS (No API calls — local only)
# ============================================================

# City aliases for fuzzy location matching
CITY_ALIASES = {
    "bangalore": ["bengaluru", "blr"],
    "mumbai": ["bombay"],
    "chennai": ["madras"],
    "kolkata": ["calcutta"],
    "gurgaon": ["gurugram"],
    "delhi ncr": ["new delhi", "delhi", "ncr", "noida", "gurgaon", "gurugram", "ghaziabad", "faridabad", "greater noida"],
    "hyderabad": ["cyberabad", "secunderabad"],
    "pune": ["pimpri", "chinchwad", "pimpri-chinchwad"],
    "navi mumbai": ["new mumbai"],
    "kota": ["kota rajasthan"],
    "jaipur": ["pink city"],
    "jodhpur": ["blue city"],
    "udaipur": ["lake city"],
}


def _filter_profile_completeness(profile: dict) -> tuple[bool, str]:
    """Filter 1: Must have name AND (headline OR current_role).
    Benefit of doubt for sparse enriched profiles."""
    name = (profile.get("name") or "").strip()
    headline = (profile.get("headline") or "").strip()
    current_role = (profile.get("current_role") or "").strip()

    if not name or len(name) < 2:
        return False, "No name"

    if not headline and not current_role:
        # Benefit of doubt: enriched profiles with about or skills pass
        if profile.get("enrichment_status") == "enriched":
            if profile.get("about") or profile.get("skills"):
                return True, ""
        return False, "No headline or role"

    return True, ""


def _filter_keyword_relevance(profile: dict, keyword: str) -> tuple[bool, str]:
    """Filter 2: Soft keyword check. Enriched profiles pass even without match."""
    if not keyword or not keyword.strip():
        return True, ""

    kw_lower = keyword.strip().lower()
    kw_parts = kw_lower.split()

    # Build combined text from all profile fields
    combined = " ".join([
        (profile.get("name") or ""),
        (profile.get("headline") or ""),
        (profile.get("current_role") or ""),
        (profile.get("current_company") or ""),
        (profile.get("organization") or ""),
        (profile.get("about") or ""),
        (profile.get("snippet") or ""),
        (profile.get("education") or ""),
        " ".join(profile.get("skills", [])),
    ]).lower()

    # Check if any keyword part appears
    if any(part in combined for part in kw_parts):
        return True, ""

    # Enriched profiles pass — Gemini will review later
    if profile.get("enrichment_status") == "enriched":
        return True, ""

    return False, "Keyword not found"


def _filter_location(profile: dict, selected_cities: list) -> tuple[bool, str]:
    """Location filter — balances strictness with practicality.
    When state/city filter is active, checks multiple signals."""
    
    # No filter at all
    if not selected_cities or "All Cities" in selected_cities:
        restricted_states = st.session_state.get("_location_filter_states", [])
        if not restricted_states:
            return True, ""
        # Fall through to state-level checking below
        selected_cities = st.session_state.get("_location_filter_cities", [])
        if not selected_cities:
            return True, ""
    
    # Build all valid location terms (cities + states + aliases)
    valid_terms = set()
    for city in selected_cities:
        valid_terms.add(city.lower())
        # Add aliases
        for alias_key, alias_list in CITY_ALIASES.items():
            if city.lower() == alias_key or city.lower() in alias_list:
                valid_terms.add(alias_key)
                valid_terms.update(alias_list)
    
    # Add state names as valid terms
    restricted_states = st.session_state.get("_location_filter_states", [])
    for state in restricted_states:
        valid_terms.add(state.lower())
    
    # Combine all searchable text from the profile
    location = (profile.get("location") or "").strip().lower()
    headline = (profile.get("headline") or "").lower()
    about = (profile.get("about") or profile.get("snippet") or "").lower()
    combined_text = f"{location} {headline} {about}"
    
    # Check 1: Does any valid term appear in any profile text?
    for term in valid_terms:
        if len(term) >= 3 and term in combined_text:
            return True, f"Location match: {term}"
    
    # Check 2: If location is empty/generic, give benefit of doubt for enriched profiles
    if not location or location in ["india", "in", ""]:
        if profile.get("enrichment_status") == "enriched":
            return True, "Unknown location — passing enriched profile"
        # For serper-only, check if snippet mentions any city
        snippet = (profile.get("snippet") or "").lower()
        for term in valid_terms:
            if len(term) >= 3 and term in snippet:
                return True, f"City found in snippet: {term}"
        # Truly unknown — reject
        return False, "Unknown location (state filter active)"
    
    # Check 3: Location is present but doesn't match — REJECT
    return False, f"Location mismatch: {location[:30]}"


def _filter_connections(profile: dict, min_connections: int) -> tuple[bool, str]:
    """Filter 4: Connection range. Below min → reject. Above 30k → reject. Zero/unknown → PASS."""
    connections = profile.get("connections", 0)

    # Zero or unknown → benefit of doubt
    if not connections or connections == 0:
        return True, ""

    if connections > 30000:
        return False, f"Too many connections ({connections:,})"

    if min_connections > 0 and connections < min_connections:
        return False, f"Low connections ({connections})"

    return True, ""


def _filter_company_blacklist(profile: dict, skip_big_companies: bool) -> tuple[bool, str]:
    """Filter 5: Optional company blacklist. Only active if HR enables checkbox."""
    if not skip_big_companies:
        return True, ""

    company = (profile.get("current_company") or profile.get("organization") or "").strip().lower()
    if not company:
        return True, ""  # No company info → pass

    for blocked in COMPANY_BLACKLIST:
        if blocked.lower() in company:
            return False, f"Blacklisted company ({blocked})"

    return True, ""


def apply_smart_filters(
    profiles: list,
    keyword: str,
    selected_cities: list,
    min_connections: int,
    skip_big_companies: bool,
    status_container,
) -> list:
    """Master filter: apply all filters in cheapest-first order.
    Completeness → Keyword → Location → Connections → Blacklist.
    No API calls. Always benefit of doubt for missing data."""
    if not profiles:
        return []

    passed = []
    rejections = {
        "completeness": 0,
        "keyword": 0,
        "location": 0,
        "connections": 0,
        "blacklist": 0,
    }

    for p in profiles:
        # Filter 1: Completeness
        ok, reason = _filter_profile_completeness(p)
        if not ok:
            rejections["completeness"] += 1
            p["filter_status"] = f"rejected: {reason}"
            continue

        # Filter 2: Keyword relevance
        ok, reason = _filter_keyword_relevance(p, keyword)
        if not ok:
            rejections["keyword"] += 1
            p["filter_status"] = f"rejected: {reason}"
            continue

        # Filter 3: Location
        ok, reason = _filter_location(p, selected_cities)
        if not ok:
            rejections["location"] += 1
            p["filter_status"] = f"rejected: {reason}"
            continue

        # Filter 4: Connections
        ok, reason = _filter_connections(p, min_connections)
        if not ok:
            rejections["connections"] += 1
            p["filter_status"] = f"rejected: {reason}"
            continue

        # Filter 5: Company blacklist
        ok, reason = _filter_company_blacklist(p, skip_big_companies)
        if not ok:
            rejections["blacklist"] += 1
            p["filter_status"] = f"rejected: {reason}"
            continue

        p["filter_status"] = "passed"
        passed.append(p)

    # Show rejection summary
    total_rejected = sum(rejections.values())
    if total_rejected > 0:
        parts = []
        if rejections["completeness"]:
            parts.append(f"{rejections['completeness']} incomplete")
        if rejections["keyword"]:
            parts.append(f"{rejections['keyword']} keyword mismatch")
        if rejections["location"]:
            parts.append(f"{rejections['location']} location mismatch")
        if rejections["connections"]:
            parts.append(f"{rejections['connections']} connection range")
        if rejections["blacklist"]:
            parts.append(f"{rejections['blacklist']} blacklisted company")
        status_container.write(f"🚧 Filtered: {total_rejected} rejected ({', '.join(parts)}) → {len(passed)} approved")
    else:
        status_container.write(f"✅ All {len(passed)} profiles passed filters")

    return passed


# ============================================================
# PHASE 4: GEMINI AI CANDIDATE ANALYSIS
# ============================================================

MAX_GEMINI_CALLS = 300

GEMINI_HR_PROMPT = """You are an expert HR recruiter analyzing a LinkedIn profile for the role: "{keyword}".

Profile Data:
- Name: {name}
- Headline: {headline}
- Current Role: {current_role}
- Current Company: {current_company}
- Location: {location}
- About: {about}
- Skills: {skills}
- Education: {education}
- Certifications: {certifications}
- Languages: {languages}
- Connections: {connections}
- Experience Positions: {experience_count}

Analyze this candidate and respond with ONLY a valid JSON object (no markdown, no code blocks, no explanation). Use this exact schema:
{{
  "role_match": "strong_match" | "partial_match" | "weak_match" | "no_match",
  "experience_level": "fresher" | "junior" | "mid" | "senior" | "lead" | "executive",
  "key_skills": ["skill1", "skill2", "skill3"],
  "domain_expertise": "description of domain knowledge",
  "current_status": "employed" | "open_to_work" | "freelancer" | "student" | "unknown",
  "education_quality": "premium" | "good" | "average" | "unknown",
  "career_trajectory": "growing" | "stable" | "declining" | "early_career" | "unknown",
  "red_flags": ["flag1"] or [],
  "green_flags": ["flag1"] or [],
  "estimated_experience_years": number,
  "fit_score": number 0-100,
  "hire_recommendation": "strongly_recommended" | "recommended" | "maybe" | "not_recommended",
  "reason": "one-line explanation of the recommendation"
}}

IMPORTANT:
- fit_score 80-100: Excellent match for the role
- fit_score 60-79: Good match, worth considering
- fit_score 40-59: Partial match, needs review
- fit_score 0-39: Weak or no match
- Be generous with benefit of doubt for missing data
- Focus on transferable skills if exact role match is unclear
"""


def _strip_markdown_code_blocks(text: str) -> str:
    """Strip markdown code block wrappers from Gemini response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def analyze_candidate(profile: dict, search_keyword: str, api_key: str) -> dict:
    """Analyze a candidate profile using Gemini 2.0 Flash.
    Returns analysis dict. NEVER crashes — always falls back."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        prompt = GEMINI_HR_PROMPT.format(
            keyword=search_keyword,
            name=profile.get("name", "Unknown"),
            headline=profile.get("headline", "N/A"),
            current_role=profile.get("current_role", "N/A"),
            current_company=profile.get("current_company") or profile.get("organization", "N/A"),
            location=profile.get("location", "N/A"),
            about=(profile.get("about") or profile.get("snippet", "N/A"))[:400],
            skills=", ".join(profile.get("skills", [])) or "N/A",
            education=profile.get("education", "N/A"),
            certifications=", ".join(profile.get("certifications", [])) or "N/A",
            languages=", ".join(profile.get("languages", [])) or "N/A",
            connections=profile.get("connections", 0),
            experience_count=len(profile.get("raw_experience", [])),
        )

        response = model.generate_content(prompt)
        raw_text = response.text
        clean_text = _strip_markdown_code_blocks(raw_text)
        analysis = json.loads(clean_text)

        # Validate required fields
        analysis.setdefault("fit_score", 50)
        analysis.setdefault("hire_recommendation", "maybe")
        analysis.setdefault("reason", "Analysis completed")
        analysis.setdefault("role_match", "partial_match")
        analysis.setdefault("key_skills", [])
        analysis.setdefault("red_flags", [])
        analysis.setdefault("green_flags", [])
        analysis["analysis_source"] = "gemini"

        return analysis

    except json.JSONDecodeError:
        return fallback_analyze(profile, search_keyword)
    except Exception:
        return fallback_analyze(profile, search_keyword)


def fallback_analyze(profile: dict, search_keyword: str) -> dict:
    """Keyword-based scoring when Gemini fails or quota exhausted."""
    score = 30  # Base score
    green_flags = []
    red_flags = []

    kw_lower = search_keyword.lower() if search_keyword else ""
    kw_parts = kw_lower.split()

    # Build combined text
    combined = " ".join([
        (profile.get("name") or ""),
        (profile.get("headline") or ""),
        (profile.get("current_role") or ""),
        (profile.get("about") or ""),
        (profile.get("snippet") or ""),
        " ".join(profile.get("skills", [])),
    ]).lower()

    # Keyword match scoring
    keyword_matches = sum(1 for part in kw_parts if part in combined)
    if keyword_matches == len(kw_parts) and kw_parts:
        score += 25
        green_flags.append("Full keyword match")
    elif keyword_matches > 0:
        score += 15
        green_flags.append("Partial keyword match")

    # Enrichment bonus
    if profile.get("enrichment_status") == "enriched":
        score += 10
        green_flags.append("Enriched profile")

    # Skills bonus
    skills = profile.get("skills", [])
    if len(skills) >= 5:
        score += 10
        green_flags.append(f"{len(skills)} skills listed")
    elif skills:
        score += 5

    # Connections scoring
    connections = profile.get("connections", 0)
    if connections >= 500:
        score += 5
        green_flags.append(f"{connections:,} connections")
    elif connections < 50 and connections > 0:
        red_flags.append("Low connections")

    # Current role/company bonus
    if profile.get("current_role"):
        score += 5
    if profile.get("current_company"):
        score += 5

    # Education bonus
    if profile.get("education"):
        score += 5

    # Clamp score
    score = min(max(score, 0), 100)

    # Determine recommendation
    if score >= 70:
        hire_rec = "recommended"
    elif score >= 50:
        hire_rec = "maybe"
    else:
        hire_rec = "not_recommended"

    return {
        "role_match": "partial_match" if keyword_matches > 0 else "weak_match",
        "experience_level": "unknown",
        "key_skills": skills[:5] if skills else [],
        "domain_expertise": "N/A",
        "current_status": "unknown",
        "education_quality": "unknown",
        "career_trajectory": "unknown",
        "red_flags": red_flags,
        "green_flags": green_flags,
        "estimated_experience_years": profile.get("experience_years", 0),
        "fit_score": score,
        "hire_recommendation": hire_rec,
        "reason": "Keyword-based scoring (Gemini unavailable)",
        "analysis_source": "fallback",
    }


def analyze_candidates_batch(
    profiles: list, search_keyword: str, api_key: str, status_container
) -> list:
    """Analyze a batch of candidates with Gemini AI. Rate-limited."""
    if not profiles:
        return []
    if not api_key:
        status_container.write("⚠️ No Gemini API key. Using fallback scoring.")
        for p in profiles:
            p["analysis"] = fallback_analyze(p, search_keyword)
        return profiles

    gemini_calls = st.session_state.get("_gemini_call_count", 0)
    analyzed_count = 0
    fallback_count = 0

    status_container.write(f"🧠 Analyzing {len(profiles)} candidates with Gemini AI...")

    for i, p in enumerate(profiles):
        if gemini_calls >= MAX_GEMINI_CALLS:
            status_container.write(f"⚠️ Gemini call limit ({MAX_GEMINI_CALLS}) reached. Using fallback for remaining.")
            p["analysis"] = fallback_analyze(p, search_keyword)
            fallback_count += 1
            continue

        analysis = analyze_candidate(p, search_keyword, api_key)
        p["analysis"] = analysis

        if analysis.get("analysis_source") == "gemini":
            gemini_calls += 1
            analyzed_count += 1
        else:
            fallback_count += 1

        # Progress update every 5 profiles
        if (i + 1) % 5 == 0:
            status_container.write(
                f"🧠 Analyzed {i + 1}/{len(profiles)} — "
                f"{analyzed_count} Gemini, {fallback_count} fallback"
            )

        time.sleep(4)  # Rate limiting

    st.session_state["_gemini_call_count"] = gemini_calls
    status_container.write(
        f"✅ Analysis complete: {analyzed_count} Gemini + {fallback_count} fallback"
    )

    return profiles


# ============================================================
# PHASE 6: DEEP SEARCH LOOP — MASTER ORCHESTRATOR
# ============================================================

# Safety Limits
MAX_SERPER_QUERIES = 50
MAX_APIFY_SCRAPES = 300
MAX_ROUNDS = 15
# MAX_GEMINI_CALLS already defined as 300 in Phase 4


def smart_candidate_search(
    search_keyword: str,
    experience_filter: list,
    industry_filter: list,
    city_filter: list,
    min_connections: int,
    skip_big_companies: bool,
    target_count: int,
    serper_key: str,
    gemini_key: str,
    apify_manager,
    dedup_urls: set,
    dedup_names: set,
) -> list:
    """Master orchestrator: Deep Search Loop.
    Per-round pipeline: discover → dedup → enrich → filter → analyze → contacts → tier.
    Continues until target reached, max rounds, consecutive empties, or quota exhausted."""

    all_profiles = []
    total_queries = 0
    consecutive_empty = 0
    max_consecutive_empty = 4
    total_apify_scrapes = 0

    # Initialize Gemini call counter for this search
    st.session_state["_gemini_call_count"] = st.session_state.get("_gemini_call_count", 0)

    # Progress UI
    progress_bar = st.progress(0, text="Starting deep search...")
    status_area = st.container()

    with status_area:
        st.markdown("### \U0001f504 Deep Search Progress")

        for round_num in range(MAX_ROUNDS):
            # ---- Safety checks ----
            if len(all_profiles) >= target_count:
                st.info(f"\u2705 Target of {target_count} candidates reached!")
                break
            if total_queries >= MAX_SERPER_QUERIES:
                st.warning(f"\u26a0\ufe0f Serper.dev query limit reached ({MAX_SERPER_QUERIES})")
                break
            if consecutive_empty >= max_consecutive_empty:
                st.info(f"\u2139\ufe0f No new profiles in {max_consecutive_empty} consecutive rounds. Search exhausted.")
                break
            gemini_calls = st.session_state.get("_gemini_call_count", 0)
            if gemini_calls >= MAX_GEMINI_CALLS:
                st.warning(f"\u26a0\ufe0f Gemini call limit reached ({MAX_GEMINI_CALLS})")
                break

            # ---- Round: wrap in st.status() for clean, collapsible output ----
            with st.status(
                f"\U0001f504 Round {round_num + 1}/{MAX_ROUNDS} \u2014 {len(all_profiles)}/{target_count} candidates",
                expanded=True
            ) as round_status:

                # ---- STEP 1: Discover via Serper.dev ----
                round_profiles = discover_via_serper(
                    search_keyword, experience_filter, industry_filter, city_filter,
                    serper_key, round_status, round_num
                )

                # Track query count
                queries_this_round = len(generate_candidate_queries(
                    search_keyword, experience_filter, industry_filter, city_filter, round_num
                )[0])
                total_queries += queries_this_round

                if not round_profiles:
                    consecutive_empty += 1
                    round_status.write(f"\u26aa Round {round_num + 1}: No new profiles found")
                    round_status.update(
                        label=f"\u26aa Round {round_num + 1} \u2014 No new profiles",
                        state="complete"
                    )
                    progress = min(len(all_profiles) / max(target_count, 1), 1.0)
                    progress_bar.progress(progress, text=f"Found {len(all_profiles)}/{target_count}...")
                    time.sleep(0.5)
                    continue

                consecutive_empty = 0

                # ---- STEP 2: Deduplicate ----
                round_profiles, dedup_count = deduplicate_profiles(round_profiles, dedup_urls, dedup_names)
                if dedup_count:
                    round_status.write(f"\U0001f504 Removed {dedup_count} duplicates")

                # Also dedup against already-found profiles this search
                new_profiles = []
                for p in round_profiles:
                    if p["url"] not in st.session_state.get("all_discovered_urls", set()):
                        new_profiles.append(p)
                round_profiles = new_profiles

                if not round_profiles:
                    round_status.write(f"⚪ Round {round_num + 1}: All profiles were duplicates")
                    round_status.update(
                        label=f"⚪ Round {round_num + 1} — All duplicates",
                        state="complete"
                    )
                    time.sleep(0.5)
                    continue

                # ---- PRE-FILTER: Quick location check before spending Apify credits ----
                if city_filter or st.session_state.get("_location_filter_states"):
                    pre_filtered = []
                    for p in round_profiles:
                        # Check if any city/state term appears in name, headline, snippet, or organization
                        combined = f"{p.get('name', '')} {p.get('headline', '')} {p.get('snippet', '')} {p.get('organization', '')}".lower()
                        valid_terms = [c.lower() for c in (city_filter or st.session_state.get("_location_filter_cities", []))]
                        valid_terms += [s.lower() for s in st.session_state.get("_location_filter_states", [])]
                        
                        # Pass if any city/state term found, OR if no location info (benefit of doubt)
                        has_location_signal = any(term in combined for term in valid_terms if len(term) >= 3)
                        has_any_text = len(combined.strip()) > 10
                        
                        if has_location_signal or not has_any_text:
                            pre_filtered.append(p)
                    
                    if len(pre_filtered) < len(round_profiles):
                        rejected_count = len(round_profiles) - len(pre_filtered)
                        round_status.write(f"🗺️ Pre-filter: {rejected_count} profiles clearly outside target area")
                    round_profiles = pre_filtered
                    
                    if not round_profiles:
                        round_status.write(f"⚪ No profiles in target area from this round")
                        round_status.update(label=f"⚪ Round {round_num + 1} — No profiles in target area", state="complete")
                        continue

                # ---- STEP 3: Enrich via Apify ----
                if apify_manager.has_keys() and not apify_manager.is_exhausted() and total_apify_scrapes < MAX_APIFY_SCRAPES:
                    # Warn before using paid key
                    if apify_manager.is_using_paid_key():
                        round_status.write("\u26a0\ufe0f Now using PAID Apify key. Monitor costs carefully.")

                    # Limit to only what we need (don't waste Apify credits)
                    remaining_needed = target_count - len(all_profiles)
                    if len(round_profiles) > remaining_needed * 2:
                        round_profiles = round_profiles[:remaining_needed * 2]  # 2x buffer for filter losses

                    round_profiles = enrich_discovered_profiles(
                        round_profiles, apify_manager, round_status
                    )
                    total_apify_scrapes += len(round_profiles)
                    round_status.write(f"\U0001f4b0 Apify cost so far: {apify_manager.get_cost_summary()}")
                else:
                    for p in round_profiles:
                        p["enrichment_status"] = "serper_only"
                    # For serper_only profiles, also extract from headline/snippet
                    for p in round_profiles:
                        _post_enrich_extract(p)

                # ---- STEP 4: Smart Filters ----
                round_profiles = apply_smart_filters(
                    round_profiles,
                    search_keyword,
                    city_filter,
                    min_connections,
                    skip_big_companies,
                    round_status,
                )

                if not round_profiles:
                    round_status.write(f"\u26aa Round {round_num + 1}: All profiles filtered out")
                    round_status.update(
                        label=f"\u26aa Round {round_num + 1} \u2014 All filtered out",
                        state="complete"
                    )
                    time.sleep(0.5)
                    continue

                # ---- STEP 5: Gemini AI Analysis ----
                if gemini_key and st.session_state.get("_gemini_call_count", 0) < MAX_GEMINI_CALLS:
                    round_profiles = analyze_candidates_batch(
                        round_profiles, search_keyword, gemini_key, round_status
                    )
                else:
                    for p in round_profiles:
                        p["analysis"] = fallback_analyze(p, search_keyword)

                # ---- STEP 6: Contact Extraction + Tier Scoring ----
                for p in round_profiles:
                    contacts = extract_contacts(p)
                    p["contacts"] = contacts
                    p["contactability"] = compute_contactability(contacts)
                    p["tier"] = compute_tier(p)
                    # Simple recruiter note (full AI notes generated post-search for Tier A/B)
                    name = p.get("name", "Candidate")
                    headline = p.get("headline", "")
                    if headline:
                        p["recruiter_note"] = f"{name} is a {headline}. Discovered for '{search_keyword}'."
                    else:
                        p["recruiter_note"] = f"{name} discovered during LinkedIn search for '{search_keyword}'."

                # ---- Collect approved profiles (respect target count) ----
                for p in round_profiles:
                    if len(all_profiles) >= target_count:
                        break  # Stop adding once target is reached
                    _sanitize_profile_fields(p)  # Ensure clean data before storing
                    st.session_state.setdefault("all_discovered_urls", set()).add(p["url"])
                    all_profiles.append(p)

                # ---- Round summary ----
                tier_a_round = sum(1 for p in round_profiles if p.get("tier") == "A")
                tier_b_round = sum(1 for p in round_profiles if p.get("tier") == "B")
                round_status.write(
                    f"\u2705 Round {round_num + 1}: +{len(round_profiles)} approved "
                    f"(\U0001f7e2 {tier_a_round}A, \U0001f535 {tier_b_round}B) \u2014 "
                    f"Total: {len(all_profiles)}/{target_count}"
                )
                round_status.update(
                    label=f"\u2705 Round {round_num + 1} \u2014 +{len(round_profiles)} candidates "
                          f"(\U0001f7e2 {tier_a_round}A \U0001f535 {tier_b_round}B)",
                    state="complete"
                )

            # Update progress
            progress = min(len(all_profiles) / max(target_count, 1), 1.0)
            progress_bar.progress(progress, text=f"Found {len(all_profiles)}/{target_count} candidates...")
            time.sleep(0.5)

        progress_bar.progress(1.0, text=f"\u2705 Deep search complete \u2014 {len(all_profiles)} candidates found!")

    # ---- Post-search: Generate AI recruiter notes for Tier A/B ----
    if all_profiles and gemini_key:
        tier_ab = [p for p in all_profiles if p.get("tier") in ["A", "B"]]
        if tier_ab:
            with st.container():
                st.markdown("### \U0001f4dd Generating Recruiter Notes")
                note_status = st.empty()
                note_count = 0
                for p in tier_ab:
                    gemini_calls = st.session_state.get("_gemini_call_count", 0)
                    if gemini_calls >= MAX_GEMINI_CALLS:
                        break
                    note = generate_recruiter_note(p, search_keyword, gemini_key)
                    p["recruiter_note"] = note
                    note_count += 1
                    time.sleep(4)
                note_status.write(f"\u2705 Generated {note_count} AI recruiter notes for Tier A/B candidates")

    # ---- Sort: Tier A first, then B, C, D; within tier by fit_score ----
    tier_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    all_profiles.sort(key=lambda x: (
        tier_order.get(x.get("tier", "D"), 3),
        -x.get("analysis", {}).get("fit_score", 0)
    ))

    # ---- Search summary stats ----
    st.session_state["_search_stats"] = {
        "total_queries": total_queries,
        "total_apify_scrapes": total_apify_scrapes,
        "gemini_calls": st.session_state.get("_gemini_call_count", 0),
        "apify_cost": apify_manager.get_cost_summary(),
    }

    return all_profiles


# ============================================================
# PHASE 5: CONTACT EXTRACTION + TIER SCORING
# ============================================================

# Regex patterns for contact extraction
_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', re.IGNORECASE)
_PHONE_RE = re.compile(r'(?:\+?\d{1,3}[\s\-.]?)?\(?\d{2,4}\)?[\s\-.]?\d{3,5}[\s\-.]?\d{3,5}')
_URL_RE = re.compile(r'https?://[^\s<>"\')]+', re.IGNORECASE)

_SOCIAL_PATTERNS = {
    "github": re.compile(r'(?:github\.com/[\w\-]+)', re.IGNORECASE),
    "twitter": re.compile(r'(?:twitter\.com/[\w]+|x\.com/[\w]+)', re.IGNORECASE),
    "instagram": re.compile(r'(?:instagram\.com/[\w.]+)', re.IGNORECASE),
    "youtube": re.compile(r'(?:youtube\.com/(?:@|channel/|c/)[\w\-]+)', re.IGNORECASE),
    "telegram": re.compile(r'(?:t\.me/[\w]+)', re.IGNORECASE),
    "whatsapp": re.compile(r'(?:wa\.me/[\d]+)', re.IGNORECASE),
}


def extract_contacts(profile: dict) -> dict:
    """Extract contact info from about, headline, website, and other text fields."""
    contacts = {
        "emails": [],
        "phones": [],
        "websites": [],
        "github": "",
        "twitter": "",
        "instagram": "",
        "youtube": "",
        "telegram": "",
        "whatsapp": "",
    }

    # Build text corpus from all relevant fields
    text_fields = [
        profile.get("about", ""),
        profile.get("headline", ""),
        profile.get("snippet", ""),
        profile.get("website", ""),
    ]
    combined_text = " ".join(str(f) for f in text_fields if f)

    # Extract emails
    emails = _EMAIL_RE.findall(combined_text)
    # Filter out common false positives
    contacts["emails"] = list(set(
        e for e in emails
        if not e.endswith((".png", ".jpg", ".gif", ".svg"))
        and "example.com" not in e
    ))[:3]  # Max 3 emails

    # Extract phones
    phones = _PHONE_RE.findall(combined_text)
    contacts["phones"] = list(set(
        p.strip() for p in phones if len(p.strip()) >= 10
    ))[:2]  # Max 2 phones

    # Extract social links
    for platform, pattern in _SOCIAL_PATTERNS.items():
        match = pattern.search(combined_text)
        if match:
            contacts[platform] = match.group(0)

    # Extract general websites (non-social)
    urls = _URL_RE.findall(combined_text)
    social_domains = ["linkedin.com", "github.com", "twitter.com", "x.com",
                      "instagram.com", "youtube.com", "t.me", "wa.me", "facebook.com"]
    contacts["websites"] = list(set(
        u for u in urls
        if not any(d in u.lower() for d in social_domains)
    ))[:3]  # Max 3 websites

    return contacts


def compute_contactability(contacts: dict) -> str:
    """Compute contactability score based on available contact info."""
    has_email = bool(contacts.get("emails"))
    has_phone = bool(contacts.get("phones"))
    has_website = bool(contacts.get("websites"))
    has_social = any(contacts.get(k) for k in ["github", "twitter", "instagram", "telegram", "whatsapp"])

    if has_email and has_phone:
        return "highly_reachable"
    elif has_email or has_phone:
        return "reachable"
    elif has_website or has_social:
        return "partially_reachable"
    else:
        return "linkedin_only"


def compute_tier(profile: dict) -> str:
    """Compute candidate tier. Made practical for real-world HR use."""
    analysis = profile.get("analysis", {})
    fit_score = analysis.get("fit_score", 0)
    hire_rec = analysis.get("hire_recommendation", "")
    role_match = analysis.get("role_match", "")
    contactability = profile.get("contactability", "linkedin_only")
    has_direct_contact = contactability in ["highly_reachable", "reachable"]
    has_any_contact = contactability != "linkedin_only"

    # Tier A: Strong fit + some way to reach them
    if fit_score >= 70 and (has_direct_contact or has_any_contact) and hire_rec in ["strongly_recommended", "recommended"]:
        return "A"
    # Tier A (alt): Very high fit even without contact (worth LinkedIn InMail)
    if fit_score >= 80 and hire_rec in ["strongly_recommended", "recommended"]:
        return "A"
    # Tier B: Good fit + recommended/maybe
    if fit_score >= 60 and role_match in ["strong_match", "partial_match"] and hire_rec in ["strongly_recommended", "recommended", "maybe"]:
        return "B"
    # Tier B (alt): Has direct contact + decent fit
    if fit_score >= 50 and has_direct_contact:
        return "B"
    # Tier C: Moderate fit
    if fit_score >= 35 and role_match != "no_match":
        return "C"
    # Tier D: Everything else
    return "D"


TIER_DISPLAY = {
    "A": {"emoji": "\U0001f7e2", "label": "Tier A", "color": "#2E7D32", "bg": "#E8F5E9"},
    "B": {"emoji": "\U0001f535", "label": "Tier B", "color": "#1565C0", "bg": "#E3F2FD"},
    "C": {"emoji": "\U0001f7e1", "label": "Tier C", "color": "#F57F17", "bg": "#FFF8E1"},
    "D": {"emoji": "\U0001f534", "label": "Tier D", "color": "#C62828", "bg": "#FFEBEE"},
}

CONTACTABILITY_DISPLAY = {
    "highly_reachable": "\U0001f4e7 Highly Reachable",
    "reachable": "\U0001f4de Reachable",
    "partially_reachable": "\U0001f310 Partially Reachable",
    "linkedin_only": "\U0001f517 LinkedIn Only",
}


def generate_recruiter_note(profile: dict, search_keyword: str, api_key: str) -> str:
    """Generate a 3-sentence recruiter note for Tier A/B candidates.
    Tier C/D: auto-generate from headline. Counts toward MAX_GEMINI_CALLS."""
    tier = profile.get("tier", "D")
    name = profile.get("name", "Candidate")
    headline = profile.get("headline", "")

    # Tier C/D: simple auto note
    if tier not in ["A", "B"]:
        if headline:
            return f"{name} is a {headline}. Profile discovered via LinkedIn search for '{search_keyword}'."
        return f"{name} was discovered during LinkedIn search for '{search_keyword}'."

    # Tier A/B: AI-generated note
    gemini_calls = st.session_state.get("_gemini_call_count", 0)
    if gemini_calls >= MAX_GEMINI_CALLS or not api_key:
        if headline:
            return f"{name} is a {headline}. Strong match for {search_keyword} role. Recommended for outreach."
        return f"{name} is a strong match for {search_keyword}. Recommended for recruiter outreach."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        analysis = profile.get("analysis", {})
        contacts = profile.get("contacts", {})
        contact_methods = []
        if contacts.get("emails"):
            contact_methods.append("email")
        if contacts.get("phones"):
            contact_methods.append("phone")

        prompt = f"""Write exactly 3 short sentences as a recruiter note for this candidate.

Candidate: {name}
Role searching for: {search_keyword}
Headline: {headline}
Current Role: {profile.get('current_role', 'N/A')}
Company: {profile.get('current_company', 'N/A')}
Fit Score: {analysis.get('fit_score', 0)}/100
Key Skills: {', '.join(analysis.get('key_skills', []))}
Contact Methods: {', '.join(contact_methods) or 'LinkedIn only'}

Sentence 1: Why this candidate is a good fit.
Sentence 2: Their standout qualifications.
Sentence 3: Recommended outreach approach.

Respond with ONLY the 3 sentences, no labels or numbering."""

        response = model.generate_content(prompt)
        st.session_state["_gemini_call_count"] = gemini_calls + 1
        return response.text.strip()[:300]

    except Exception:
        if headline:
            return f"{name} is a {headline}. Strong match for {search_keyword} role. Recommended for outreach."
        return f"{name} is a strong match for {search_keyword}. Recommended for recruiter outreach."


def process_contacts_and_tiers(
    profiles: list, search_keyword: str, api_key: str, status_container
) -> list:
    """Process contacts, contactability, tiers, and recruiter notes for all profiles."""
    if not profiles:
        return []

    status_container.write(f"\U0001f4cb Processing contacts & tiers for {len(profiles)} candidates...")
    notes_generated = 0

    for i, p in enumerate(profiles):
        # Extract contacts
        contacts = extract_contacts(p)
        p["contacts"] = contacts

        # Compute contactability
        p["contactability"] = compute_contactability(contacts)

        # Compute tier
        p["tier"] = compute_tier(p)

        # Generate recruiter note
        note = generate_recruiter_note(p, search_keyword, api_key)
        p["recruiter_note"] = note
        if p["tier"] in ["A", "B"]:
            notes_generated += 1
            time.sleep(4)  # Rate limit for Gemini calls

        # Progress update every 10
        if (i + 1) % 10 == 0:
            status_container.write(f"\U0001f4cb Processed {i + 1}/{len(profiles)} contacts & tiers")

    tier_counts = {}
    for p in profiles:
        t = p.get("tier", "D")
        tier_counts[t] = tier_counts.get(t, 0) + 1

    tier_summary = " | ".join([f"{TIER_DISPLAY[t]['emoji']} {t}: {c}" for t, c in sorted(tier_counts.items())])
    status_container.write(f"\u2705 Tiers assigned: {tier_summary} | {notes_generated} AI recruiter notes")

    return profiles


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("### 📡 System Status")

    keys, missing = load_api_keys()

    if missing:
        st.error(f"⚠️ Missing: {', '.join(missing)}")
        st.caption("Configure in `.streamlit/secrets.toml`")

    serper_ok = "SERPER_API_KEY" in keys
    gemini_ok = "GOOGLE_API_KEY" in keys
    apify_count = len(keys.get("APIFY_KEYS", []))
    apify_free = sum(1 for k in keys.get("APIFY_KEYS", []) if not k["is_paid"])
    apify_paid = sum(1 for k in keys.get("APIFY_KEYS", []) if k["is_paid"])

    st.markdown(f"""
<div class="status-card">
<b>Serper.dev:</b> {'✅ Connected' if serper_ok else '❌ Missing'}<br>
<b>Gemini AI:</b> {'✅ Connected' if gemini_ok else '❌ Missing'}<br>
<b>Apify:</b> {'✅' if apify_count else '❌'} {apify_free} free + {apify_paid} paid keys
</div>
    """, unsafe_allow_html=True)

    if apify_count:
        st.caption("💰 Cost mode: Free keys used first, paid key last")

    st.markdown("---")

    # Deduplication — CSV Upload
    st.markdown("### 📋 Deduplication")
    uploaded_csv = st.file_uploader(
        "Upload Previously Sourced CSV",
        type=["csv"],
        help="Upload a CSV with columns like 'url', 'name', or 'linkedin_url' to skip already-sourced candidates.",
    )

    if uploaded_csv is not None:
        if "dedup_file_name" not in st.session_state or st.session_state["dedup_file_name"] != uploaded_csv.name:
            existing_urls, existing_names, count, error = load_existing_candidates(uploaded_csv)
            if error:
                st.error(f"CSV Error: {error}")
            else:
                st.session_state["dedup_urls"] = existing_urls
                st.session_state["dedup_names"] = existing_names
                st.session_state["dedup_count"] = count
                st.session_state["dedup_file_name"] = uploaded_csv.name
                st.success(f"✅ Loaded {count} candidates ({len(existing_urls)} URLs, {len(existing_names)} names)")
        else:
            st.info(f"📋 {st.session_state.get('dedup_count', 0)} candidates loaded for dedup")
    else:
        st.session_state.pop("dedup_urls", None)
        st.session_state.pop("dedup_names", None)
        st.session_state.pop("dedup_count", None)
        st.session_state.pop("dedup_file_name", None)

    st.markdown("---")

    # Search History
    st.markdown("### 🕐 Recent Searches")
    if "search_history" in st.session_state and st.session_state["search_history"]:
        for item in st.session_state["search_history"][-5:]:
            st.caption(f"🔸 **{item['keyword']}** — {item['count']} found ({item['time']})")
    else:
        st.caption("No searches yet")

    # Apify Cost Tracker
    st.markdown("### 💰 Apify Cost")
    if "apify_manager" in st.session_state:
        mgr = st.session_state["apify_manager"]
        st.markdown(f"""
<div class="status-card">
<b>Status:</b> {mgr.get_status()}<br>
<b>Cost:</b> {mgr.get_cost_summary()}
</div>
        """, unsafe_allow_html=True)
    else:
        st.caption("No enrichment run yet")

    st.markdown("---")

    # Tier Legend
    st.markdown("### \U0001f3af Tier Legend")
    st.markdown("""
<div style="font-size:0.78rem; line-height:1.8;">
\U0001f7e2 <b>Tier A</b> — Top candidate: high fit + reachable + recommended<br>
\U0001f535 <b>Tier B</b> — Good candidate: decent fit + contact or strong match<br>
\U0001f7e1 <b>Tier C</b> — Possible: moderate fit, worth a look<br>
\U0001f534 <b>Tier D</b> — Low priority: weak fit or no data
</div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # About
    st.markdown("### \u2139\ufe0f About")
    st.caption("Built with Serper.dev, Apify, and Gemini 2.0 Flash. Discover, enrich, analyze, and export LinkedIn candidates at scale.")

    st.markdown("""
<div style="text-align:center; opacity:0.6; font-size:0.75rem; padding: 8px;">
    \U0001f3af HR Candidate Finder v1.0<br>
    Phase 7 \u2014 Dashboard & Final UI
</div>
    """, unsafe_allow_html=True)


# ============================================================
# MAIN AREA — SEARCH UI
# ============================================================

# Quick Search Presets
preset_col, _ = st.columns([2, 3])
with preset_col:
    selected_preset = st.selectbox(
        "⚡ Quick Search Presets",
        options=list(SEARCH_PRESETS.keys()),
        index=0,
        help="Select a preset or choose 'Custom Search' to enter your own keywords",
    )

# Search Input
preset_value = SEARCH_PRESETS.get(selected_preset, "")
search_keyword = st.text_input(
    "🔎 Search Keyword",
    value=preset_value if selected_preset != "-- Custom Search --" else "",
    placeholder="Enter job title, skills, or keywords... (e.g., Python Developer, Marketing Manager)",
    help="Type a job title or skill to find matching LinkedIn profiles",
)

# Filters (collapsed by default)
with st.expander("🎛️ Advanced Filters", expanded=False):
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        experience_filter = st.multiselect(
            "📊 Experience Level",
            options=["All Levels", "Entry Level (0-2 yrs)", "Mid Level (3-5 yrs)", "Senior (5-10 yrs)", "Lead/Staff (10+ yrs)"],
            default=["All Levels"],
            help="Filter by experience level",
        )

    with filter_col2:
        industry_filter = st.multiselect(
            "🏢 Industry",
            options=["All Industries"] + list(INDUSTRY_KEYWORDS.keys()),
            default=["All Industries"],
            help="Filter by industry sector",
        )

    # ---- Hierarchical Location Filter: Region → State → Cities ----
    st.markdown("##### 📍 Location Filter")
    loc_col1, loc_col2 = st.columns(2)

    with loc_col1:
        selected_regions = st.multiselect(
            "🌍 Select Region(s)",
            options=["All India"] + list(INDIA_REGIONS.keys()),
            default=["All India"],
            help="Select one or more regions to narrow down states",
        )

    # Build state list based on selected regions
    available_states = []
    if "All India" in selected_regions or not selected_regions:
        for region, states in INDIA_REGIONS.items():
            for state in states:
                available_states.append(f"{state} ({region})")
    else:
        for region in selected_regions:
            if region in INDIA_REGIONS:
                for state in INDIA_REGIONS[region]:
                    available_states.append(f"{state} ({region})")

    with loc_col2:
        selected_states_display = st.multiselect(
            "🏛️ Select State(s)",
            options=["All States"] + sorted(available_states),
            default=["All States"],
            help="Select states to see their cities",
        )

    # Parse selected states (strip region suffix)
    selected_state_names = []
    if "All States" not in selected_states_display:
        for s in selected_states_display:
            # Extract state name from "State (Region)" format
            state_name = s.rsplit(" (", 1)[0]
            selected_state_names.append(state_name)

    # Build city list based on selected states
    available_cities = []
    if "All States" in selected_states_display or not selected_states_display:
        # Show cities from selected regions
        if "All India" in selected_regions or not selected_regions:
            available_cities = CITIES_LIST.copy()
        else:
            for region in selected_regions:
                if region in INDIA_REGIONS:
                    for state_cities in INDIA_REGIONS[region].values():
                        available_cities.extend(state_cities)
    else:
        # Show cities only from selected states
        for region in INDIA_REGIONS.values():
            for state, state_cities in region.items():
                if state in selected_state_names:
                    available_cities.extend(state_cities)

    city_filter = st.multiselect(
        "🏙️ Select Cities",
        options=["All Cities"] + sorted(set(available_cities)),
        default=["All Cities"],
        help="Select specific cities to target in your search",
    )

    # Show summary of location selection
    if city_filter and "All Cities" not in city_filter:
        st.caption(f"📍 Targeting {len(city_filter)} cities: {', '.join(city_filter[:8])}{'...' if len(city_filter) > 8 else ''}")
    elif selected_state_names:
        total_cities = len(available_cities)
        st.caption(f"📍 All {total_cities} cities in: {', '.join(selected_state_names[:5])}{'...' if len(selected_state_names) > 5 else ''}")

    st.markdown("---")

    adv_col1, adv_col2 = st.columns(2)
    with adv_col1:
        min_connections = st.slider(
            "🔗 Min Connections",
            min_value=0, max_value=500, value=50, step=25,
            help="Minimum LinkedIn connections (0 = no filter)",
        )
    with adv_col2:
        skip_big_companies = st.checkbox(
            "🚫 Skip Big Company Employees",
            value=False,
            help=f"Exclude employees from: {', '.join(COMPANY_BLACKLIST[:8])}...",
        )

# Target Count + Search Button
target_col, btn_col = st.columns([1, 2])
with target_col:
    target_count = st.slider(
        "🎯 Target Candidates",
        min_value=5, max_value=100, value=20, step=5,
        help="Number of candidates to find",
    )

with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    search_clicked = st.button("🔍 Find Candidates", type="primary", use_container_width=True)


# ============================================================
# SEARCH EXECUTION
# ============================================================

# Initialize session state
if "discovered_profiles" not in st.session_state:
    st.session_state["discovered_profiles"] = []
if "all_discovered_urls" not in st.session_state:
    st.session_state["all_discovered_urls"] = set()
if "search_history" not in st.session_state:
    st.session_state["search_history"] = []
if "search_running" not in st.session_state:
    st.session_state["search_running"] = False

if search_clicked:
    # Validation
    if not search_keyword or not search_keyword.strip():
        st.error("\u26a0\ufe0f Please enter a search keyword or select a preset.")
    elif not serper_ok:
        st.error("\u26a0\ufe0f Serper.dev API key is missing. Configure it in `.streamlit/secrets.toml`.")
    else:
        # Reset state for new search
        st.session_state["discovered_profiles"] = []
        st.session_state["all_discovered_urls"] = set()
        st.session_state["search_running"] = True

        # Initialize Apify Key Manager
        apify_manager = ApifyKeyManager(keys.get("APIFY_KEYS", []))
        st.session_state["apify_manager"] = apify_manager

        # Load dedup data
        dedup_urls = st.session_state.get("dedup_urls", set())
        dedup_names = st.session_state.get("dedup_names", set())

        serper_key = keys["SERPER_API_KEY"]
        gemini_key = keys.get("GOOGLE_API_KEY", "")

        # Clean search keyword for better Google dorking results
        # (keep original search_keyword for display/history)
        clean_keyword = search_keyword.strip()
        for char in ['&', '+', '/', '\\', '|', ';']:
            clean_keyword = clean_keyword.replace(char, ' ')
        clean_keyword = ' '.join(clean_keyword.split())

        # Resolve actual cities from hierarchical filter
        actual_search_cities = []
        if city_filter and "All Cities" not in city_filter:
            actual_search_cities = city_filter
        elif selected_state_names:
            # "All Cities" selected but state filter is active
            # → use only cities from selected states
            for region in INDIA_REGIONS.values():
                for state, state_cities in region.items():
                    if state in selected_state_names:
                        actual_search_cities.extend(state_cities)
        # else: actual_search_cities stays empty = truly all cities
        
        # Store for the location filter function
        st.session_state["_location_filter_states"] = selected_state_names
        st.session_state["_location_filter_cities"] = actual_search_cities

        # Warn about restrictive filters
        warning_parts = []
        if min_connections >= 300:
            warning_parts.append(f"Min connections ({min_connections}) is very high — most profiles have 100-300")
        if skip_big_companies:
            warning_parts.append("Big company filter active — excludes major employers")
        if actual_search_cities and len(actual_search_cities) < 10:
            warning_parts.append(f"Location restricted to {len(actual_search_cities)} cities")
        
        if len(warning_parts) >= 2:
            st.warning(f"⚠️ Restrictive filters may reduce results: {'; '.join(warning_parts)}")

        # ---- Run Master Orchestrator (Phase 6) ----
        all_profiles = smart_candidate_search(
            search_keyword=clean_keyword,
            experience_filter=experience_filter,
            industry_filter=industry_filter,
            city_filter=actual_search_cities if actual_search_cities else city_filter,
            min_connections=min_connections,
            skip_big_companies=skip_big_companies,
            target_count=target_count,
            serper_key=serper_key,
            gemini_key=gemini_key,
            apify_manager=apify_manager,
            dedup_urls=dedup_urls,
            dedup_names=dedup_names,
        )

        # Store results
        st.session_state["discovered_profiles"] = all_profiles
        st.session_state["search_running"] = False

        # Update search history
        from datetime import datetime
        stats = st.session_state.get("_search_stats", {})
        st.session_state["search_history"].append({
            "keyword": search_keyword,
            "count": len(all_profiles),
            "time": datetime.now().strftime("%H:%M"),
            "queries": stats.get("total_queries", 0),
            "apify_cost": stats.get("apify_cost", "N/A"),
            "gemini_calls": stats.get("gemini_calls", 0),
        })
        # Keep only last 5
        st.session_state["search_history"] = st.session_state["search_history"][-5:]

        # Final summary
        tier_a = sum(1 for p in all_profiles if p.get("tier") == "A")
        tier_b = sum(1 for p in all_profiles if p.get("tier") == "B")
        reachable = sum(1 for p in all_profiles if p.get("contactability") in ["highly_reachable", "reachable"])
        st.success(f"\U0001f389 Found **{len(all_profiles)}** candidates \u2014 \U0001f7e2 {tier_a} Tier A, \U0001f535 {tier_b} Tier B, {reachable} directly reachable")
        st.caption(f"\U0001f4ca Serper: {stats.get('total_queries', 0)} queries | Apify: {stats.get('apify_cost', 'N/A')} | Gemini: {stats.get('gemini_calls', 0)} calls")


# ============================================================
# RESULTS DISPLAY — Phase 7 Dashboard
# ============================================================

profiles = st.session_state.get("discovered_profiles", [])

if profiles:
    st.markdown("---")

    # ---------- KPI Cards ----------
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">👥 Total Candidates</div>
            <div class="metric-value">{len(profiles)}</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        strong_matches = sum(1 for p in profiles if p.get("tier") in ["A", "B"])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">🎯 Strong Matches</div>
            <div class="metric-value">{strong_matches}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        avg_fit = sum(p.get("analysis", {}).get("fit_score", 0) for p in profiles) / max(len(profiles), 1)
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📊 Avg Fit Score</div>
            <div class="metric-value">{avg_fit:.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        reachable_count = sum(1 for p in profiles if p.get("contactability") in ["highly_reachable", "reachable"])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-title">📧 Directly Reachable</div>
            <div class="metric-value">{reachable_count}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- Visualizations (2 tabs) ----------
    import plotly.express as px
    import plotly.graph_objects as go

    viz_tab1, viz_tab2 = st.tabs(["📊 Analysis", "🗺️ Quality Map"])

    with viz_tab1:
        chart_col1, chart_col2, chart_col3 = st.columns(3)

        # Tier Distribution Donut
        with chart_col1:
            tier_counts = {}
            for p in profiles:
                t = p.get("tier", "D")
                tier_counts[t] = tier_counts.get(t, 0) + 1
            tier_labels = list(tier_counts.keys())
            tier_values = list(tier_counts.values())
            tier_colors = [TIER_DISPLAY.get(t, {}).get("color", "#999") for t in tier_labels]

            fig_tier = go.Figure(data=[go.Pie(
                labels=[f"Tier {t}" for t in tier_labels],
                values=tier_values,
                hole=0.55,
                marker=dict(colors=tier_colors),
                textinfo="label+value",
                textfont_size=11,
            )])
            fig_tier.update_layout(
                title=dict(text="Tier Distribution", font=dict(size=14)),
                showlegend=False,
                height=280,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_tier, use_container_width=True)

        # Role Match Donut
        with chart_col2:
            match_counts = {}
            for p in profiles:
                m = p.get("analysis", {}).get("role_match", "unknown")
                m_label = m.replace("_", " ").title()
                match_counts[m_label] = match_counts.get(m_label, 0) + 1
            match_colors = {"Strong Match": "#2E7D32", "Partial Match": "#F57F17", "Weak Match": "#E65100", "No Match": "#C62828", "Unknown": "#999"}

            fig_match = go.Figure(data=[go.Pie(
                labels=list(match_counts.keys()),
                values=list(match_counts.values()),
                hole=0.55,
                marker=dict(colors=[match_colors.get(k, "#999") for k in match_counts.keys()]),
                textinfo="label+value",
                textfont_size=11,
            )])
            fig_match.update_layout(
                title=dict(text="Role Match", font=dict(size=14)),
                showlegend=False,
                height=280,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_match, use_container_width=True)

        # Experience Level Bar Chart
        with chart_col3:
            exp_counts = {}
            for p in profiles:
                exp = p.get("analysis", {}).get("experience_level", "unknown")
                exp_label = exp.replace("_", " ").title() if exp else "Unknown"
                exp_counts[exp_label] = exp_counts.get(exp_label, 0) + 1

            fig_exp = go.Figure(data=[go.Bar(
                x=list(exp_counts.keys()),
                y=list(exp_counts.values()),
                marker_color="#6C5CE7",
                text=list(exp_counts.values()),
                textposition="auto",
            )])
            fig_exp.update_layout(
                title=dict(text="Experience Levels", font=dict(size=14)),
                height=280,
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
            )
            st.plotly_chart(fig_exp, use_container_width=True)

    with viz_tab2:
        # Quality Map: Scatter of fit_score vs connections, colored by tier
        scatter_data = []
        for p in profiles:
            scatter_data.append({
                "Fit Score": p.get("analysis", {}).get("fit_score", 0),
                "Connections": p.get("connections", 0),
                "Tier": f"Tier {p.get('tier', 'D')}",
                "Name": p.get("name", "Unknown"),
                "Role": p.get("current_role", p.get("headline", "")),
            })
        scatter_df = pd.DataFrame(scatter_data)

        color_map = {f"Tier {t}": TIER_DISPLAY[t]["color"] for t in ["A", "B", "C", "D"]}

        fig_scatter = px.scatter(
            scatter_df,
            x="Connections",
            y="Fit Score",
            color="Tier",
            color_discrete_map=color_map,
            hover_data=["Name", "Role"],
            size_max=12,
            title="Candidate Quality Map — Fit Score vs Connections",
        )
        fig_scatter.update_layout(
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
            yaxis=dict(showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------- Tier Filter Tabs ----------
    tier_tab_all, tier_tab_a, tier_tab_b, tier_tab_c, tier_tab_d = st.tabs([
        f"🔘 All ({len(profiles)})",
        f"🟢 Tier A ({sum(1 for p in profiles if p.get('tier') == 'A')})",
        f"🔵 Tier B ({sum(1 for p in profiles if p.get('tier') == 'B')})",
        f"🟡 Tier C ({sum(1 for p in profiles if p.get('tier') == 'C')})",
        f"🔴 Tier D ({sum(1 for p in profiles if p.get('tier') == 'D')})",
    ])

    def render_profiles(filtered_profiles, view_key):
        """Render filtered profiles as card or table view."""
        if not filtered_profiles:
            st.info("No candidates in this tier.")
            return

        view_mode = st.radio(
            "View Mode", ["📇 Card View", "📊 Table View"],
            horizontal=True, label_visibility="collapsed", key=f"view_{view_key}"
        )

        if view_mode == "📇 Card View":
            for i, p in enumerate(filtered_profiles):
                name_display = p.get("name", "Unknown")
                headline_display = p.get("headline", "")
                org_display = p.get("current_company") or p.get("organization", "")
                role_display = p.get("current_role", "")
                location_display = p.get("location", "")
                url = p.get("url", "")
                is_enriched = p.get("enrichment_status") == "enriched"
                skills_list = p.get("skills", [])
                connections = p.get("connections", 0)
                education_display = p.get("education", "")

                analysis = p.get("analysis", {})
                fit_score = analysis.get("fit_score", 0)
                hire_rec = analysis.get("hire_recommendation", "")
                reason = analysis.get("reason", "")
                green_flags = analysis.get("green_flags", [])
                red_flags = analysis.get("red_flags", [])

                tier = p.get("tier", "D")
                tier_info = TIER_DISPLAY.get(tier, TIER_DISPLAY["D"])
                contacts = p.get("contacts", {})
                contactability = p.get("contactability", "linkedin_only")
                recruiter_note = p.get("recruiter_note", "")

                # Use st.container with border for each card
                with st.container(border=True):
                    # Row 1: Name + badges
                    badge_parts = [f"**{name_display}**"]
                    badge_parts.append(f"{'🟢' if tier == 'A' else '🔵' if tier == 'B' else '🟡' if tier == 'C' else '🔴'} Tier {tier}")
                    if is_enriched:
                        badge_parts.append("✨ Enriched")
                    badge_parts.append(f"🎯 {fit_score}/100")
                    badge_parts.append(CONTACTABILITY_DISPLAY.get(contactability, "🔗 LinkedIn Only"))
                    st.markdown(" · ".join(badge_parts))

                    # Row 2: Role + Company (truncated for readability)
                    role_text = (role_display[:80] + "...") if len(role_display) > 80 else role_display
                    if role_text and org_display:
                        st.markdown(f"**{role_text}** at **{org_display}**")
                    elif headline_display:
                        headline_short = (headline_display[:100] + "...") if len(headline_display) > 100 else headline_display
                        st.markdown(f"*{headline_short}*")
                    elif org_display:
                        st.markdown(f"🏢 {org_display}")

                    # Row 3: Location + Connections + Education
                    info_parts = []
                    if location_display:
                        info_parts.append(f"📍 {location_display}")
                    if connections:
                        info_parts.append(f"🔗 {connections:,} connections")
                    if education_display:
                        info_parts.append(f"🎓 {education_display[:60]}")
                    if info_parts:
                        st.caption(" · ".join(info_parts))

                    # Row 4: Skills
                    if skills_list:
                        st.markdown(" ".join([f"`{s}`" for s in skills_list[:6]]))

                    # Row 5: Contact info
                    contact_parts = []
                    if contacts.get("emails"):
                        contact_parts.append(f"📧 {contacts['emails'][0]}")
                    if contacts.get("phones"):
                        contact_parts.append(f"📱 {contacts['phones'][0]}")
                    if contacts.get("github"):
                        contact_parts.append(f"💻 {contacts['github']}")
                    if contacts.get("websites"):
                        contact_parts.append(f"🌐 {contacts['websites'][0][:40]}")
                    if contact_parts:
                        st.markdown(" · ".join(contact_parts))

                    # Row 6: AI Analysis
                    col_score, col_analysis, col_link = st.columns([1, 4, 1])
                    with col_score:
                        if fit_score >= 70:
                            st.success(f"**{fit_score}**/100")
                        elif fit_score >= 50:
                            st.warning(f"**{fit_score}**/100")
                        else:
                            st.error(f"**{fit_score}**/100")

                    with col_analysis:
                        rec_display = hire_rec.replace("_", " ").title() if hire_rec else "Pending"
                        st.markdown(f"**{rec_display}** — {reason[:100]}" if reason else f"**{rec_display}**")
                        flag_text = ""
                        if green_flags:
                            flag_text += " ".join([f"✅ {f}" for f in green_flags[:3]])
                        if red_flags:
                            flag_text += "  " + " ".join([f"⚠️ {f}" for f in red_flags[:2]])
                        if flag_text:
                            st.caption(flag_text)

                    with col_link:
                        if url:
                            st.link_button("View Profile →", url)

                    # Row 7: Recruiter Note (Tier A/B only)
                    if recruiter_note and tier in ["A", "B"]:
                        st.info(f"📝 {recruiter_note[:200]}")

        else:
            # Table View
            df_data = []
            for p in filtered_profiles:
                analysis = p.get("analysis", {})
                contacts = p.get("contacts", {})
                t = p.get("tier", "D")
                t_info = TIER_DISPLAY.get(t, TIER_DISPLAY["D"])
                
                # Safe string extraction (in case sanitization missed something)
                role_val = p.get("current_role", p.get("headline", ""))
                if isinstance(role_val, (list, dict)):
                    role_val = ""
                company_val = p.get("current_company") or p.get("organization", "")
                if isinstance(company_val, (list, dict)):
                    company_val = ""
                
                df_data.append({
                    "Tier": f"{t_info['emoji']} {t}",
                    "Score": analysis.get("fit_score", 0),
                    "Rec": {"strongly_recommended": "\U0001f7e2", "recommended": "\U0001f7e1", "maybe": "\U0001f7e0", "not_recommended": "\U0001f534"}.get(analysis.get("hire_recommendation", ""), "\u26aa"),
                    "Name": p.get("name", "Unknown"),
                    "Role": str(role_val)[:80] if role_val else "",
                    "Company": str(company_val)[:60] if company_val else "",
                    "Email": contacts.get("emails", [""])[0] if contacts.get("emails") else "",
                    "Phone": contacts.get("phones", [""])[0] if contacts.get("phones") else "",
                    "Contact": CONTACTABILITY_DISPLAY.get(p.get("contactability", ""), ""),
                    "LinkedIn URL": p.get("url", ""),
                })

            df = pd.DataFrame(df_data)
            st.dataframe(
                df,
                column_config={
                    "LinkedIn URL": st.column_config.LinkColumn("LinkedIn URL", display_text="Open Profile"),
                    "Score": st.column_config.NumberColumn("Score", format="%d"),
                },
                hide_index=True,
                use_container_width=True,
            )

    with tier_tab_all:
        render_profiles(profiles, "all")
    with tier_tab_a:
        render_profiles([p for p in profiles if p.get("tier") == "A"], "a")
    with tier_tab_b:
        render_profiles([p for p in profiles if p.get("tier") == "B"], "b")
    with tier_tab_c:
        render_profiles([p for p in profiles if p.get("tier") == "C"], "c")
    with tier_tab_d:
        render_profiles([p for p in profiles if p.get("tier") == "D"], "d")

    # ---------- Cost Summary ----------
    stats = st.session_state.get("_search_stats", {})
    if stats:
        st.markdown("---")
        st.markdown("### \U0001f4b0 Search Cost Summary")
        cost_col1, cost_col2, cost_col3, cost_col4 = st.columns(4)
        with cost_col1:
            st.metric("\U0001f50d Serper Queries", stats.get("total_queries", 0), delta=f"of {MAX_SERPER_QUERIES} max")
        with cost_col2:
            st.metric("\u2728 Apify Scrapes", stats.get("total_apify_scrapes", 0), delta=stats.get("apify_cost", "N/A"))
        with cost_col3:
            st.metric("\U0001f9e0 Gemini Calls", stats.get("gemini_calls", 0), delta=f"of {MAX_GEMINI_CALLS} max")
        with cost_col4:
            keys_info = []
            apify_mgr = st.session_state.get("apify_manager")
            if apify_mgr:
                keys_info.append(f"Apify: {apify_mgr.get_status()}")
            st.metric("\U0001f511 API Keys", len(keys_info) if keys_info else "—", delta=keys_info[0] if keys_info else "N/A")

    # ---------- CSV Export ----------
    st.markdown("---")
    export_col1, export_col2, _ = st.columns([1, 1, 3])

    with export_col1:
        export_data = []
        for p in profiles:
            analysis = p.get("analysis", {})
            contacts = p.get("contacts", {})
            export_data.append({
                "Tier": p.get("tier", "D"),
                "Fit Score": analysis.get("fit_score", 0),
                "Recommendation": analysis.get("hire_recommendation", ""),
                "Role Match": analysis.get("role_match", ""),
                "Contactability": p.get("contactability", "linkedin_only"),
                "Name": p.get("name", ""),
                "Headline": p.get("headline", ""),
                "Company": p.get("current_company") or p.get("organization", ""),
                "Role": p.get("current_role", ""),
                "Location": p.get("location", ""),
                "Email": ", ".join(contacts.get("emails", [])),
                "Phone": ", ".join(contacts.get("phones", [])),
                "Website": ", ".join(contacts.get("websites", [])),
                "GitHub": contacts.get("github", ""),
                "Twitter": contacts.get("twitter", ""),
                "LinkedIn URL": p.get("url", ""),
                "About": p.get("about", p.get("snippet", "")),
                "Skills": ", ".join(p.get("skills", [])),
                "Education": p.get("education", ""),
                "Connections": p.get("connections", 0),
                "Green Flags": ", ".join(analysis.get("green_flags", [])),
                "Red Flags": ", ".join(analysis.get("red_flags", [])),
                "AI Reason": analysis.get("reason", ""),
                "Recruiter Note": p.get("recruiter_note", ""),
            })
        export_df = pd.DataFrame(export_data)
        csv_buffer = io.StringIO()
        export_df.to_csv(csv_buffer, index=False)

        st.download_button(
            label="\U0001f4e5 Download All (CSV)",
            data=csv_buffer.getvalue(),
            file_name=f"candidates_{search_keyword.replace(' ', '_') if search_keyword else 'export'}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with export_col2:
        top_tier_data = [p for p in export_data if p.get("Tier") in ["A", "B"]]
        if top_tier_data:
            top_df = pd.DataFrame(top_tier_data)
            csv_buffer2 = io.StringIO()
            top_df.to_csv(csv_buffer2, index=False)
            st.download_button(
                label=f"⭐ Download Tier A+B ({len(top_tier_data)} candidates)",
                data=csv_buffer2.getvalue(),
                file_name=f"top_candidates_{search_keyword.replace(' ', '_') if search_keyword else 'export'}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.button("⭐ Download Tier A+B (0 candidates)", disabled=True, use_container_width=True)
            st.caption("No Tier A or B candidates found. Try broader keywords.")

elif not st.session_state.get("search_running", False):
    # Welcome State
    st.markdown("<br>", unsafe_allow_html=True)

    welcome_col1, welcome_col2, welcome_col3 = st.columns(3)

    with welcome_col1:
        st.markdown("""
        <div class="welcome-card">
            <div class="welcome-icon">\U0001f50d</div>
            <div class="welcome-title">Smart Discovery</div>
            <div class="welcome-desc">AI-powered Google dorking finds LinkedIn profiles matching your exact requirements \u2014 any role, any city.</div>
        </div>
        """, unsafe_allow_html=True)

    with welcome_col2:
        st.markdown("""
        <div class="welcome-card">
            <div class="welcome-icon">\U0001f3af</div>
            <div class="welcome-title">Precision Targeting</div>
            <div class="welcome-desc">Filter by experience, industry, location, and connections. Skip big company employees to find hidden gems.</div>
        </div>
        """, unsafe_allow_html=True)

    with welcome_col3:
        st.markdown("""
        <div class="welcome-card">
            <div class="welcome-icon">\U0001f4ca</div>
            <div class="welcome-title">Export & Analyze</div>
            <div class="welcome-desc">Download discovered profiles as CSV. Upload previous exports to automatically skip already-sourced candidates.</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("\U0001f446 **Get started**: Select a preset or enter a custom keyword above, then click **Find Candidates**.")

