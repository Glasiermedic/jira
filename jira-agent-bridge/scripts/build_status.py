#!/usr/bin/env python3
import os, json, datetime, requests
from collections import defaultdict

BASE = os.environ["JIRA_BASE"]
EMAIL = os.environ["JIRA_EMAIL"]
TOKEN = os.environ["JIRA_API_TOKEN"]
PROJ_KEYS = [k.strip() for k in os.environ.get("JIRA_PROJECT_KEYS","").split(",") if k.strip()]
JQLS = [j.strip() for j in os.environ.get("JIRA_JQLS","").split(",") if j.strip()]
EXTRA = [f.strip() for f in os.environ.get("JIRA_FIELDS_EXTRA","").split(",") if f.strip()]
STORY_FIELD = os.environ.get("JIRA_STORY_POINTS_FIELD")  # e.g., customfield_10016
SPRINT_FIELD = os.environ.get("JIRA_SPRINT_FIELD","sprint")
INCLUDE_CHANGELOG = os.environ.get("INCLUDE_CHANGELOG","false").lower() == "true"

CORE_FIELDS = ["summary","status","issuetype","priority","labels","duedate","customfield_10011","parent","assignee","updated"]
FIELDS = ",".join(CORE_FIELDS + EXTRA + ([SPRINT_FIELD] if SPRINT_FIELD else []) + ([STORY_FIELD] if STORY_FIELD else []))

auth = (EMAIL, TOKEN)

def search_jql(jql, start=0, max_results=100, expand=None):
    url = f"{BASE}/rest/api/3/search"
    params = {"jql": jql, "startAt": start, "maxResults": max_results, "fields": FIELDS}
    if expand: params["expand"] = expand
    r = requests.get(url, params=params, auth=auth)
    r.raise_for_status()
    return r.json()

def fetch_all(jql, expand=None):
    start, issues = 0, []
    while True:
        data = search_jql(jql, start=start, expand=expand)
        issues.extend(data.get("issues", []))
        if start + data.get("maxResults", 0) >= data.get("total", 0):
            break
        start += data.get("maxResults", 0)
    return issues

def story_points(fields):
    if STORY_FIELD and STORY_FIELD in fields:
        return fields[STORY_FIELD]
    return None

def sprint_name(fields):
    s = fields.get(SPRINT_FIELD)
    if isinstance(s, list) and s: return s[-1].get("name")
    if isinstance(s, dict): return s.get("name")
    return None

def simplify(base, issue):
    f = issue["fields"]
    epic_name = f.get("customfield_10011")
    if not epic_name and f.get("parent") and f["parent"].get("fields",{}).get("issuetype",{}).get("name") == "Epic":
        epic_name = f["parent"]["key"]
    return {
        "key": issue["key"],
        "link": f"{base}/browse/{issue['key']}",
        "summary": f.get("summary"),
        "type": (f.get("issuetype") or {}).get("name"),
        "status": (f.get("status") or {}).get("name"),
        "priority": (f.get("priority") or {}).get("name"),
        "labels": f.get("labels") or [],
        "assignee": (f.get("assignee") or {}).get("displayName"),
        "due": f.get("duedate"),
        "epic": epic_name,
        "updated": f.get("updated"),
        "sprint": sprint_name(f),
        "story_points": story_points(f)
    }

def group_by_epic(issues):
    d = defaultdict(list)
    for it in issues:
        d[it.get("epic") or "No Epic"].append(it)
    return d

def build_markdown(snapshot):
    lines = [f"# Project Status — {snapshot['generated_at']}"]
    for blk in snapshot["blocks"]:
        lines += [f"\n## {blk['title']}", f"_JQL_: `{blk['jql']}`  \n_Total_: **{blk['total']}**"]
        for epic, items in group_by_epic(blk["issues"]).items():
            lines.append(f"\n### Epic: {epic}")
            for it in items:
                due = f" (due {it['due']})" if it.get("due") else ""
                sp = f" · {it['story_points']}pt" if it.get("story_points") is not None else ""
                lines.append(f"- **[{it['key']}]({it['link']})** [{it['status']}] {it['summary']}{sp}{due}")
    if snapshot.get("changes"):
        lines.append("\n## Changes (last 24h)")
        lines += [f"- {x}" for x in snapshot["changes"]]
    return "\n".join(lines)

def recent_changes(issues):
    now = datetime.datetime.utcnow()
    cutoff = now - datetime.timedelta(hours=24)
    out = []
    for it in issues:
        try:
            ts = datetime.datetime.fromisoformat(it["updated"].replace("Z","+00:00"))
            if ts >= cutoff:
                out.append(f"{it['key']} updated {it['updated']} — {it['summary']}")
        except Exception:
            pass
    return out

def main():
    blocks, all_items = [], []
    if JQLS:
        for j in JQLS:
            items = [simplify(BASE, x) for x in fetch_all(j, expand="changelog" if INCLUDE_CHANGELOG else None)]
            blocks.append({"title": "Custom", "jql": j, "total": len(items), "issues": items})
            all_items += items
    else:
        for key in PROJ_KEYS:
            j = f"project = {key} ORDER BY Rank ASC"
            items = [simplify(BASE, x) for x in fetch_all(j, expand="changelog" if INCLUDE_CHANGELOG else None)]
            blocks.append({"title": f"Project {key}", "jql": j, "total": len(items), "issues": items})
            all_items += items

    snapshot = {"generated_at": datetime.datetime.utcnow().isoformat() + "Z", "jira_base": BASE, "blocks": blocks}
    if INCLUDE_CHANGELOG: snapshot["changes"] = recent_changes(all_items)

    os.makedirs("docs", exist_ok=True)
    with open("docs/status.json","w") as f: json.dump(snapshot, f, indent=2)
    with open("docs/status.md","w") as f: f.write(build_markdown(snapshot))
    print("OK")
if __name__ == "__main__":
    main()
