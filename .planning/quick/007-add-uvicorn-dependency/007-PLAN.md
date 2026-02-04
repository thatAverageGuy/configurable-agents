---
phase: 007-add-uvicorn-dependency
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [pyproject.toml]
autonomous: true
---

<objective>
Add uvicorn dependency to pyproject.toml
Purpose: Ensure uvicorn is declared as a required dependency for the dashboard service
Output: pyproject.toml with uvicorn>=0.30.0 added to dependencies
</objective>

<execution_context>
@C:\Users\ghost\.claude\get-shit-done\workflows\execute-plan.md
</execution_context>

<tasks>

<task type="auto">
  <name>Add uvicorn dependency to pyproject.toml</name>
  <files>pyproject.toml</files>
  <action>
  1. Read pyproject.toml to identify the correct location for web dependencies
  2. Add uvicorn>=0.30.0 to the dependencies section after line 36 (where rich is listed)
  3. Ensure proper formatting and maintain alphabetical order if needed
  4. Verify the syntax is valid TOML
  </action>
  <verify>pyproject.toml --check should pass without syntax errors</verify>
  <done>uvicorn>=0.30.0 is present in the dependencies section of pyproject.toml</done>
</task>

</tasks>

<verification>
Confirm pyproject.toml has uvicorn>=0.30.0 in dependencies and TOML syntax is valid
</verification>

<success_criteria>
uvicorn is properly declared as a project dependency
</success_criteria>

<output>
After completion, create `.planning/quick/007-add-uvicorn-dependency/007-01-SUMMARY.md`
</output>