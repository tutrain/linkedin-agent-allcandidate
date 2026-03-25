# BUGFIX PROMPT — Round 2: Card View HTML, Enrichment Data, Tier Scoring

```
Fix the following bugs in app.py in the hr_candidate_finder/ directory.

## BUG 1 (CRITICAL): Card View renders raw HTML code instead of styled cards

### Problem:
In Card View, the profile cards show raw HTML source code like:
```
<div style="font-size:0.8rem; color:#636e72; margin-top:6px;"> 📍 Jalandhar, Punjab, India, 🔗 500 connections, 🎓 ******* ******* | YouTube</div><div style="margin-top:6px;"><span ...
```

Instead of actually rendering the styled content.

### Root Cause:
The `render_profiles` function builds a HUGE single `st.markdown(...)` call with deeply nested HTML. Streamlit's `unsafe_allow_html=True` has issues rendering very large/complex nested HTML blocks. When the HTML is too large or contains certain characters, Streamlit escapes it and shows raw code.

### Fix:
Rewrite the Card View rendering to use Streamlit's native components (st.container, st.columns, st.markdown) instead of one giant HTML blob. Break the card into small, manageable HTML snippets.

Replace the entire Card View rendering block (inside `if view_mode == "📇 Card View":`) with this approach:

```python
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

            # Row 2: Role + Company
            if role_display and org_display:
                st.markdown(f"**{role_display}** at **{org_display}**")
            elif headline_display:
                st.markdown(f"*{headline_display}*")
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
                st.link_button("View Profile →", url)

            # Row 7: Recruiter Note (Tier A/B only)
            if recruiter_note and tier in ["A", "B"]:
                st.info(f"📝 {recruiter_note[:200]}")
```

This approach:
- Uses `st.container(border=True)` for each card (native Streamlit, always renders correctly)
- Uses `st.columns` for layout instead of CSS flex
- Uses small markdown snippets instead of one huge HTML blob
- Uses Streamlit native components: `st.success`, `st.warning`, `st.error`, `st.caption`, `st.link_button`, `st.info`
- Skills shown as inline code blocks with backticks
- NO raw HTML needed — everything is native Streamlit

---

## BUG 2: Enriched profiles missing Company, Role, Connections data

### Problem:
Looking at the CSV output and Table View:
- Most enriched profiles have empty Company, Role, Email, Phone columns
- Company shows as "******* *******" (asterisks/censored) for some profiles
- Connections shows 0 or 500 for most profiles
- The GetLeads Apify actor (`get-leads/linkedin-scraper`) returns data via SERP (Google/Brave/Yahoo) scraping, NOT direct LinkedIn scraping. This means it returns limited fields.

### Root Cause:
The GetLeads actor returns a different data schema than expected. Looking at the Apify logs:
```
Profile extracted from SERP! {"name":"Surbhi Verma","headline":"Product Manager @ Google | Stanford GSB "}
```
It primarily returns: name, headline, about (snippet). It does NOT reliably return: current_company, current_role, skills (as array), connections, experience array, education array.

The `_parse_apify_profile_item` function doesn't fully handle the GetLeads actor's schema — it expects fields like `companyName`, `position`, `experience[]` which this actor may not provide.

### Fix:
Add a POST-ENRICHMENT data extraction step. After merging Apify data, extract missing fields from the headline and about text using simple parsing.

Add this function and call it after enrichment:

```python
def _post_enrich_extract(profile: dict) -> dict:
    """Extract missing fields from headline/about text when Apify returns limited data."""
    
    # --- Extract company and role from headline ---
    # LinkedIn headlines are usually: "Role at Company" or "Role | Company" or "Role - Company"
    headline = profile.get("headline", "")
    if headline and not profile.get("current_company"):
        # Try "at" pattern: "Product Manager at Google"
        if " at " in headline:
            parts = headline.split(" at ", 1)
            if len(parts) == 2:
                if not profile.get("current_role"):
                    profile["current_role"] = parts[0].strip()
                profile["current_company"] = parts[1].strip().split("|")[0].strip().split("·")[0].strip()
        # Try " | " pattern: "Product Manager | Google"
        elif " | " in headline:
            parts = headline.split(" | ", 1)
            if len(parts) == 2:
                if not profile.get("current_role"):
                    profile["current_role"] = parts[0].strip()
                profile["current_company"] = parts[1].strip()
        # Try " - " pattern: "Product Manager - Google"
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
            # Look for "Skills:" section in about
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
        conn = conn.replace("+", "").replace(",", "").strip()
        try:
            profile["connections"] = int(conn)
        except ValueError:
            profile["connections"] = 0
    
    return profile
```

Call this function in `enrich_discovered_profiles` right before returning:

```python
    # Post-enrichment: extract missing fields from text
    for p in result:
        p = _post_enrich_extract(p)
    
    return result
```

Also call it in the deep search loop for serper_only profiles:

```python
    # For serper_only profiles, also extract from headline/snippet
    for p in round_profiles:
        if p.get("enrichment_status") == "serper_only":
            p = _post_enrich_extract(p)
```

---

## BUG 3: Tier scoring too strict — 0 Tier A, 0 Tier B for all searches

### Problem:
Every search returns 0 Tier A and 0 Tier B candidates. Looking at the data:
- Most candidates get fit_score 55-65 with "partial_match" 
- Almost no one has direct contact info (email/phone)
- Tier A requires: fit >= 75 AND direct contact AND recommended → almost impossible
- Tier B requires: fit >= 60 AND (direct contact OR strong_match) → rare because most are "partial_match" and no direct contact

### Fix:
Relax the tier thresholds slightly so that the tool is actually useful for HR:

```python
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
```

This makes tiers more practical:
- Tier A: Score 70+ with contact OR 80+ without (worth pursuing regardless)
- Tier B: Score 60+ with good match OR 50+ with direct contact
- Tier C: Score 35+ (was 40+)
- Tier D: Rest

---

## BUG 4: "Download Tier A+B" button missing when 0 Tier A/B candidates

### Problem:
The export section only shows "Download All (CSV)" button when there are no Tier A/B candidates. The Tier A+B button disappears completely.

### Fix:
Always show the Tier A+B download button but disable it / show count:

```python
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
```

---

## BUG 5: Gemini prompt sometimes returns "maybe" as recommendation but Tier logic doesn't recognize it

### Problem:
Gemini returns `"hire_recommendation": "maybe"` for most candidates, but the old tier logic only checked for `"strongly_recommended"` and `"recommended"` for Tier A and B. So "maybe" candidates never get Tier B even if their fit_score is 60+.

### Fix:
Already addressed in BUG 3 fix above — `"maybe"` is now included in Tier B criteria.

---

## VERIFICATION AFTER ALL FIXES:

1. Card View should render clean native Streamlit components — NO raw HTML visible
2. Company and Role columns should be populated (extracted from headline when Apify doesn't return them)
3. Tier A and Tier B should have some candidates for good keyword matches
4. Download buttons should always be visible
5. Search "Python Developer" should return some Tier B candidates
6. Search "whatsapp youtube manager" should show properly rendered cards

Do NOT add any API key input fields to the frontend.
Do NOT change the Serper.dev or Apify integration logic.
Do NOT change the ApifyKeyManager class.
```
