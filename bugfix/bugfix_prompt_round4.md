# BUGFIX PROMPT — Round 4: Location Filter Too Strict + Queries Not Using Selected Cities

```
Fix the following bugs in app.py in the hr_candidate_finder/ directory.

## BUG 1: Search queries don't include selected cities in Round 0 and Round 1

### Problem:
When user selects Rajasthan state, the query generator still uses generic queries in rounds 0-1:
```
Round 0: site:linkedin.com/in/ "digital marketing executive" India
Round 1: site:linkedin.com/in/ "digital marketing executive" "years of experience"
```
These find profiles from ALL over India. Only rounds 2-5 use city-based queries. By then, the Serper query limit (50) is nearly exhausted.

### Fix:
When `actual_search_cities` is provided (user selected specific states/cities), inject those cities into rounds 0 and 1 as well. Modify `generate_candidate_queries`:

```python
def generate_candidate_queries(keyword: str, experience_levels: list, industries: list, cities: list, round_num: int) -> tuple:
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
```

This ensures that when the user selects Rajasthan, every single query includes Rajasthan city names like "Jaipur", "Jodhpur", "Kota", etc.

---

## BUG 2: Location filter rejects profiles with empty/unknown locations

### Problem:
The location filter was made TOO strict in Round 3. Now it rejects ANY profile whose location field is empty or generic (like "India") when a state filter is active. But the GetLeads Apify actor often returns empty location fields — even for candidates who ARE in Rajasthan. Result: 100% of profiles get rejected.

### Fix:
The location filter should be SMART, not just strict:
1. If profile was found via a city-specific Google query (e.g., query contained "Jaipur"), it's likely from that city → PASS
2. If location field contains a matching city/state → PASS
3. If headline or about text mentions a matching city/state → PASS
4. If location is completely empty AND none of the above → Give 50% benefit of doubt (pass if enriched, reject if serper-only)
5. If location clearly shows a DIFFERENT city (e.g., "Mumbai") → REJECT

Replace `_filter_location` with:

```python
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
```

This is much smarter:
- Checks location, headline, AND about text for city/state mentions
- Enriched profiles with unknown location get benefit of doubt (likely found via city-specific query)
- Only rejects when location CLEARLY shows a different city
- Serper-only profiles with truly unknown location are rejected

---

## BUG 3: No warning about extreme filter values

### Problem:
User set Min Connections = 500 and Skip Big Companies = checked. Together with the strict Rajasthan filter, this eliminates virtually everyone. The UI doesn't warn about this.

### Fix:
Add a warning when filter combination is very restrictive. In the search execution block, right after validation:

```python
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
```

---

## BUG 4: Connection filter runs BEFORE location filter — wastes Apify credits

### Problem:
The filter order is: Completeness → Keyword → Location → Connections → Blacklist.
But connections are checked AFTER enrichment. If a profile has 0 connections (unknown), it passes. Then location filter rejects it. This means we enriched profiles for nothing.

### Fix:
Move the connection filter AFTER location in the filter chain is already correct. But the real issue is that we're enriching 20 profiles per round even when most will be filtered by location.

Add a PRE-ENRICHMENT location check using just the Serper snippet/title data:

In `smart_candidate_search`, right AFTER deduplication and BEFORE enrichment, add:

```python
                # ---- PRE-FILTER: Quick location check before spending Apify credits ----
                if actual_search_cities or st.session_state.get("_location_filter_states"):
                    pre_filtered = []
                    for p in round_profiles:
                        # Check if any city/state term appears in name, headline, snippet, or organization
                        combined = f"{p.get('name', '')} {p.get('headline', '')} {p.get('snippet', '')} {p.get('organization', '')}".lower()
                        valid_terms = [c.lower() for c in (actual_search_cities or st.session_state.get("_location_filter_cities", []))]
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
```

This saves Apify credits by not enriching profiles that are obviously from the wrong location (e.g., snippet says "Mumbai, Maharashtra").

---

## SUMMARY:

1. **Query generator now uses selected cities in ALL rounds** (not just rounds 2-5)
2. **Location filter checks headline + about text** too (not just the location field)
3. **Enriched profiles with unknown location get benefit of doubt** (they were found via city-specific queries)
4. **Pre-enrichment location check** saves Apify credits
5. **Warning shown** when filter combination is very restrictive

## VERIFICATION:
1. Search "digital marketing executive" with Rajasthan filter → queries should include "Jaipur", "Jodhpur", etc.
2. Should find SOME profiles (not 0) from Rajasthan
3. Profiles from Mumbai/Delhi should be rejected
4. Enriched profiles with empty location should pass (found via Rajasthan city queries)
5. Warning should appear when Min Connections is 300+

Do NOT add API key inputs to the frontend.
Do NOT change the ApifyKeyManager class.
```
