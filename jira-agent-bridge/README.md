# Jira Agent Bridge (v2)

Publishes compact Jira status to **GitHub Pages** so GPTs can read one URL.

## Setup (short)
1) Push this repo to GitHub.
2) Enable Pages → Branch `main`, Folder `/docs`.
3) Add repo secrets: `JIRA_BASE`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, plus optional `JIRA_PROJECT_KEYS` or `JIRA_JQLS`.
4) (Optional) `JIRA_FIELDS_EXTRA`, `JIRA_STORY_POINTS_FIELD`, `JIRA_SPRINT_FIELD`, `INCLUDE_CHANGELOG=true`.
5) Run workflow “Jira Status to Pages (v2)”.
