# BUGFIX PROMPT — Round 3: Role Data Corruption, Location Filter, Target Count, Card View

```
Fix the following bugs in app.py in the hr_candidate_finder/ directory. These are the REMAINING issues after previous fixes.

## BUG 1 (ROOT CAUSE): current_role contains raw Python dicts instead of role title string

### Problem:
In the CSV export and Card View, the "Role" column shows raw Python list/dict data like:
```
[{'companyId': None, 'companyLinkedinUrl': None, 'companyName': 'London Academy', 'dateRange': {'start': {'month': 8, 'year': 2025, 'day': None}, 'end': {'month': 11, 'year': 2025, 'day': None}}}]
```

This corrupted data appears in:
- Card View (shows the raw dict string instead of a clean role title)
- Table View (Role column shows dict dumps)
- CSV export (Role column has dict dumps)

### Root Cause:
In the `_parse_apify_profile_item` function, when parsing the experience array, `current_role` is being set to the raw experience dict or list object, not to the "title" string field WITHIN that dict. The GetLeads actor returns experience as a list of dicts, and the code is assigning the entire dict or list to `current_role` instead of extracting `dict.get("title", "")`.

Also, `_post_enrich_extract` checks `if not profile.get("current_role")` — but `current_role` IS set (to the raw dict), so the headline-parsing fallback never triggers.

### Fix:
Add a data sanitization step that runs AFTER `_parse_apify_profile_item` and AFTER `_post_enrich_extract`. This catches any field that contains a list or dict instead of a string.

Add this function:

```python
def _sanitize_profile_fields(profile: dict) -> dict:
    """Ensure all display fields are clean strings, not raw dicts/lists.
    This is the LAST step before a profile is used for display/export."""
    
    # --- Fix current_role if it's a list/dict ---
    role = profile.get("current_role", "")
    if isinstance(role, (list, dict)):
        # It's a raw experience array — extract title from first entry
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
        # If current_role is empty after sanitization, parse from headline
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
```

### Where to call _sanitize_profile_fields:

Call it in THREE places to ensure ALL profiles are clean:

1. At the END of `_parse_apify_profile_item`, just before the return:
```python
    # ... existing code ...
    result = {
        "url": linkedin_url,
        # ... all fields ...
    }
    return _sanitize_profile_fields(result)
```

2. At the END of `enrich_discovered_profiles`, after the existing `_post_enrich_extract` loop:
```python
    # Post-enrichment: sanitize all fields
    for p in result:
        _post_enrich_extract(p)
        _sanitize_profile_fields(p)
    
    return result
```

3. In the deep search loop (`smart_candidate_search`), right before adding profiles to `all_profiles`:
```python
    # ---- Collect approved profiles ----
    for p in round_profiles:
        _sanitize_profile_fields(p)  # Ensure clean data before storing
        st.session_state.setdefault("all_discovered_urls", set()).add(p["url"])
        all_profiles.append(p)
```

---

## BUG 2: Target count not respected — set to 5 but got 24 profiles

### Problem:
User sets target to 5 candidates but gets 24. The deep search loop adds ALL profiles from a round before checking the target count.

### Root Cause:
In `smart_candidate_search`, the target check `if len(all_profiles) >= target_count: break` is at the TOP of the round loop, so it only stops BEFORE starting a new round. Within a round, ALL discovered+filtered+analyzed profiles are added, even if only 2 more were needed.

### Fix:
Add a target count check when collecting approved profiles, inside the "Collect approved profiles" section:

Replace this block in `smart_candidate_search`:
```python
                # ---- Collect approved profiles ----
                for p in round_profiles:
                    st.session_state.setdefault("all_discovered_urls", set()).add(p["url"])
                    all_profiles.append(p)
```

With this:
```python
                # ---- Collect approved profiles (respect target count) ----
                for p in round_profiles:
                    if len(all_profiles) >= target_count:
                        break  # Stop adding once target is reached
                    _sanitize_profile_fields(p)
                    st.session_state.setdefault("all_discovered_urls", set()).add(p["url"])
                    all_profiles.append(p)
```

Also, limit the batch size sent to enrichment/analysis to avoid wasting API credits:

In the STEP 3 (Enrich) section, limit how many profiles we process:
```python
                # ---- STEP 3: Enrich via Apify ----
                # Limit to only what we need (don't waste Apify credits)
                remaining_needed = target_count - len(all_profiles)
                if len(round_profiles) > remaining_needed * 2:
                    round_profiles = round_profiles[:remaining_needed * 2]  # 2x buffer for filter losses
```

Add this right BEFORE the Apify enrichment step.

---

## BUG 3: Location filter not working — getting profiles outside Rajasthan

### Problem:
User selects "North India" > "Rajasthan" > "All Cities" but gets profiles from Mumbai, Delhi, Bengaluru, etc.

### Root Cause:
TWO issues:

**Issue A**: The `_filter_location` function gives "benefit of doubt" to profiles with empty locations. Since the GetLeads Apify actor often doesn't return location data, most profiles have empty locations and pass the filter.

**Issue B**: The Google dorking queries use CITIES_LIST (all cities) when "All Cities" is selected in the dropdown, instead of using only cities from the selected state (Rajasthan). The query generator ignores the hierarchical region→state→city selection.

### Fix for Issue A:
Make the location filter STRICTER when the user has explicitly selected a state/region. If the user selected specific states, empty-location profiles should be penalized, not passed.

In `_filter_location`, change the "unknown location" logic:

```python
def _filter_location(profile: dict, selected_cities: list) -> tuple[bool, str]:
    """Filter 3: Location matching with alias support."""
    if not selected_cities or "All Cities" in selected_cities:
        # Check if there are state-level restrictions via session_state
        restricted_states = st.session_state.get("_location_filter_states", [])
        if not restricted_states:
            return True, ""  # No filter at all
        
        # State-level filter is active — check location against state cities
        location = (profile.get("location") or "").strip().lower()
        if not location:
            # Unknown location with state filter active → REJECT (don't give benefit of doubt)
            return False, "Unknown location (state filter active)"
        
        # Check if location matches any city in the restricted states
        all_state_cities = st.session_state.get("_location_filter_cities", [])
        for city in all_state_cities:
            if city.lower() in location or location in city.lower():
                return True, ""
        
        # Check common state names
        for state in restricted_states:
            if state.lower() in location:
                return True, ""
        
        # Also check "india" broadly if state filter is set
        # (some profiles just say "India" with no city)
        return False, f"Location '{location[:30]}' not in selected states"
    
    # City-level filter
    location = (profile.get("location") or "").strip().lower()
    if not location:
        return False, "Unknown location (city filter active)"
    
    for city in selected_cities:
        city_lower = city.lower()
        if city_lower in location or location in city_lower:
            return True, ""
        aliases = CITY_ALIASES.get(city_lower, [])
        for alias in aliases:
            if alias in location:
                return True, ""
    
    return False, f"Location mismatch ({location[:30]})"
```

### Fix for Issue B:
Pass the actual selected cities (from the hierarchical filter) to the query generator, not "All Cities".

In the search execution section, BEFORE calling `smart_candidate_search`, resolve the city list:

```python
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
```

Then pass `actual_search_cities` instead of `city_filter` to `smart_candidate_search`:

```python
        all_profiles = smart_candidate_search(
            search_keyword=clean_keyword,
            experience_filter=experience_filter,
            industry_filter=industry_filter,
            city_filter=actual_search_cities if actual_search_cities else city_filter,
            # ... rest of params ...
        )
```

This ensures:
- When user picks "Rajasthan" → only Rajasthan cities are used in search queries
- When user picks "All Cities" under "Rajasthan" → the filter still restricts to Rajasthan cities
- Profiles with unknown locations are REJECTED when a state/city filter is active

---

## BUG 4: Card View still showing raw dict data in role/experience fields

### Problem:
Even after the previous Card View fix (switching to native Streamlit components), the cards show raw Python dict strings because `current_role` contains the raw experience list.

### Root Cause:
This is the SAME root cause as BUG 1. Once `_sanitize_profile_fields` is in place (BUG 1 fix), the Card View will automatically show clean data because it reads from `current_role` which will now be a clean string.

### Additional Card View Improvement:
After BUG 1 is fixed, also clean up the Card View to be more concise. The current cards show too much information. Make them scannable:

In the Card View section, update the role display (Row 2) to truncate long text:

```python
            # Row 2: Role + Company (truncated for readability)
            role_text = (role_display[:80] + "...") if len(role_display) > 80 else role_display
            if role_text and org_display:
                st.markdown(f"**{role_text}** at **{org_display}**")
            elif headline_display:
                headline_short = (headline_display[:100] + "...") if len(headline_display) > 100 else headline_display
                st.markdown(f"*{headline_short}*")
            elif org_display:
                st.markdown(f"🏢 {org_display}")
```

---

## BUG 5: Table View "Role" column also shows raw dicts

### Same root cause as BUG 1 — fixed by _sanitize_profile_fields.

But also add a safety check in the Table View data builder:

```python
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
                    "Rec": {"strongly_recommended": "🟢", "recommended": "🟡", "maybe": "🟠", "not_recommended": "🔴"}.get(analysis.get("hire_recommendation", ""), "⚪"),
                    "Name": p.get("name", "Unknown"),
                    "Role": str(role_val)[:80] if role_val else "",
                    "Company": str(company_val)[:60] if company_val else "",
                    "Email": contacts.get("emails", [""])[0] if contacts.get("emails") else "",
                    "Phone": contacts.get("phones", [""])[0] if contacts.get("phones") else "",
                    "Contact": CONTACTABILITY_DISPLAY.get(p.get("contactability", ""), ""),
                    "LinkedIn URL": p.get("url", ""),
                })
```

---

## SUMMARY OF ALL CHANGES:

1. **Add `_sanitize_profile_fields()` function** — cleans all dict/list fields to strings
2. **Call it in 3 places**: after Apify parsing, after enrichment, before adding to results
3. **Fix target count**: Break when `len(all_profiles) >= target_count` during collection
4. **Fix location filter**: Reject unknown-location profiles when state filter is active
5. **Resolve hierarchical cities**: Pass actual state cities to search, not "All Cities"
6. **Truncate long text** in Card View and Table View role/headline fields

## VERIFICATION:
1. Search "digital marketing executive" with Rajasthan filter → ONLY Rajasthan profiles
2. Set target to 5 → get exactly 5 (or fewer if search exhausts)
3. Card View shows clean role titles, not raw Python dicts
4. Table View Role column shows clean text
5. CSV export Role column shows clean text

Do NOT add API key inputs to the frontend.
Do NOT change the ApifyKeyManager class.
Do NOT change the Serper.dev API integration.
```
