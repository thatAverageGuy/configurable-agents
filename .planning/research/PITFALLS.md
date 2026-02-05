# Pitfalls Research: v1.1 Core UX Polish

**Domain:** UX improvements to existing developer tools
**Project:** Configurable Agent Orchestration Platform (v1.1)
**Researched:** 2026-02-04
**Overall confidence:** HIGH

## Executive Summary

This research identifies critical pitfalls when adding **single-command startup, auto-initialization, navigation redesign, unified workspace, and status dashboards** to existing developer tools. Unlike greenfield development, UX improvements to working tools carry unique risks: breaking muscle memory of existing users, hiding power features behind "simplified" interfaces, and creating performance degradation through "unified" approaches.

Key insight from muscle memory research: **"Major changes to a known interface can disrupt ingrained user habits, leading to temporary declines in user efficiency"** (Wikipedia redesign study, MDPI 2025). The 2023 Figma UI redesign backlash demonstrated that **even beneficial changes face fierce resistance when they disrupt established workflows**.

Most dangerous category for v1.1: **Navigation redesign** that breaks existing user mental models, followed closely by **status dashboard overload** (alert fatigue) and **silent auto-initialization failures** that corrupt state.

---

## Critical Pitfalls

### Pitfall 1: Breaking Muscle Memory with Navigation Redesign

**What goes wrong:**
Navigation changes disrupt users' ingrained habits, causing immediate productivity loss. Users conditioned by existing workflows don't just "look elsewhere" — they actively resist, complain, and may abandon the tool. Research shows navigation changes cause "temporary declines in user efficiency" that can last **months**, not weeks.

**Why it happens:**
Teams redesign navigation based on "better" information architecture without respecting existing user mental models. What seems logical to designers conflicts with habits formed through hundreds of interactions. The **"Cost of Disrupting Muscle Memory"** analysis of Figma's UI redesign illustrates how even improvements face backlash when they disrupt automatic behaviors.

**Consequences:**
- 20-40% temporary productivity loss for existing users
- Support ticket spikes from confused users ("where did X go?")
- Feature requests to "add back the old way"
- Negative sentiment in forums and issue trackers
- Potential user migration to competitor tools

**Prevention:**

1. **Preserve key navigation paths:** Keep at least 80% of primary workflows intact
2. **Progressive disclosure:** Add new navigation without removing old paths immediately
3. **Transition period:** Run both navigation patterns in parallel for 1-2 releases
4. **User testing with actual users:** Test with power users, not just new users
5. **Migration guide:** Document "old path → new path" mappings
6. **Opt-out option:** Allow users to revert to classic navigation temporarily

**Detection:**
- User surveys asking "where do you find X?"
- Analytics showing decreased usage of previously popular features
- Support tickets about "missing" features that still exist
- Community discussions about navigation changes

**Phase to address:** Phase 03-03 (Navigation Redesign) — Critical. Must plan transition strategy before shipping changes.

**Real-world examples:**
- **Figma UI redesign (2023):** Major backlash due to disrupted muscle memory. Users had to relearn automatic behaviors, causing temporary productivity loss.
- **Wikipedia redesign (2023):** MDPI study found "major changes to a known interface can disrupt ingrained user habits, leading to temporary declines in user efficiency."

---

### Pitfall 2: Silent Auto-Initialization Failures Corrupting State

**What goes wrong:**
Auto-initialization (databases, MLFlow backend, storage) fails silently or creates corrupted state. Users don't see explicit errors, so they proceed with workflows that fail mysteriously later. Worse: partial initialization leaves the system in an undefined state that's hard to recover from.

**Why it happens:**
Auto-initialization is designed to "just work," so failures are treated as "try again later" rather than blocking errors. Database creation might succeed but table creation fails. MLFlow might start but backend connection fails. File permissions might allow SQLite creation but not writes.

**Consequences:**
- "Why is my data not saving?" — user discovers hours later that initialization failed
- SQLite databases created with wrong schema, requiring manual deletion
- MLFlow runs silently failing to log, breaking observability
- Hard-to-debug errors: "Table 'workflow_runs' doesn't exist" appears mid-execution
- User loses trust in "auto" features, manually initializes everything anyway

**Prevention:**

1. **Health check on first startup:** Verify all components initialized, show clear status
2. **Blocking errors for critical failures:** Don't proceed if database/MLFlow initialization fails
3. **Idempotent initialization:** Running twice should be safe, not cause conflicts
4. **Clear error messages with action items:** "Failed to create database: /data is not writable. Fix permissions or set AGENTS_DB_PATH to a writable location."
5. **Initialization status command:** `agents status --verbose` shows initialization state
6. **Safe mode fallback:** If auto-init fails, provide manual setup instructions

**Detection:**
- Support tickets about "data not saving" or "MLFlow not showing runs"
- Users asking "do I need to run something first?"
- Empty databases despite workflow runs completing
- MLFlow UI showing "no experiments" despite successful runs

**Phase to address:** Phase 03-01 (Auto-Initialization) — Critical. Must have health checks and clear error states before shipping.

---

### Pitfall 3: Alert Fatigue from Status Dashboard Overload

**What goes wrong:**
Status dashboards show too much information, causing alert fatigue. Users stop paying attention because everything looks important, so nothing is. Enterprise cybersecurity research shows **"dashboard overload"** is a recognized problem where dozens of tools create separate alert streams leading to decision overload.

**Why it happens:**
Teams add "everything" to the status dashboard: active workflows, agent status, recent runs, MLFlow status, webhook status, memory usage, token counts, costs, errors, warnings. Without prioritization, users see a wall of status indicators.

**Consequences:**
- Users ignore dashboard entirely (too noisy)
- Critical alerts missed in the noise
- "Dashboard fatigue" — users disable notifications
- Increased support burden ("why is this red?")
- Paradox: more visibility → less actionable insight

**Prevention:**

1. **Tiered status display:** Critical (always visible), Warning (collapsible), Info (on-demand)
2. **Signal-to-noise ratio:** Show only 3-5 key metrics by default
3. **Smart alerting:** Only alert on state changes, not continuous status
4. **Action-oriented status:** Each status indicator has a "what to do" action
5. **Customizable dashboard:** Users choose what matters to them
6. **Alert aggregation:** Group related alerts (e.g., "3 workflows failed" not 3 separate alerts)

**Detection:**
- Users ignoring dashboard (analytics: dashboard views decreasing over time)
- Support tickets asking "what does this status mean?"
- Users requesting "simplify" or "hide" features
- Alert fatigue symptoms: users muting/disabling notifications

**Phase to address:** Phase 03-04 (Key Status Visibility) — Important. Must implement tiered status before adding more indicators.

**Real-world examples:**
- **Cybersecurity tools:** "Enterprise organizations deploy dozens of security tools, each generating separate alert streams, leading to decision overload" ([Design Bootcamp](https://medium.com/design-bootcamp/alert-fatigue-and-dashboard-overload-why-cybersecurity-needs-better-ux-1f3bd32ad81c))
- **DevOps monitoring:** AWS Well-Architected Framework specifically addresses "optimize alerts to prevent fatigue" ([AWS Docs](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/o.cm.9-optimize-alerts-to-prevent-fatigue-and-minimize-monitoring-costs.html))

---

### Pitfall 4: Single-Command Startup Hiding Diagnostic Information

**What goes wrong:**
Single-command startup (e.g., `agents up`) hides the complexity of what's being started. When things go wrong, users have no visibility into what failed or why. The command just "doesn't work" with unclear error messages.

**Why it happens:**
Single-command abstraction is designed to simplify, but that simplicity hides diagnostic information. Docker compose errors, port conflicts, MLFlow startup failures, and database initialization issues all get collapsed into "failed to start."

**Consequences:**
- Users can't debug startup failures (no logs, no error details)
- "It worked yesterday, today it doesn't" — no visibility into what changed
- Support burden increases (every startup failure requires manual debugging)
- Users abandon single-command for manual multi-step process
- False confidence: "it started" but MLFlow isn't actually running

**Prevention:**

1. **Verbose mode:** `agents up --verbose` shows startup steps
2. **Health check output:** Show what started and what failed
3. **Port conflict detection:** Clear error if ports 5000/8000 are in use
4. **Dependency checking:** Verify Docker is running before attempting startup
5. **Startup timeout:** Don't hang forever if MLFlow never starts
6. **Partial success reporting:** "Dashboard started (port 8000) but MLFlow failed to start"

**Detection:**
- Support tickets: "`agents up` doesn't work"
- Users manually running individual components
- Forum posts asking "how do I debug startup?"
- Confusion about what the single command actually does

**Phase to address:** Phase 03-01 (Single-Command Startup) — Important. Must have verbose mode and clear error reporting.

---

### Pitfall 5: Unified Workspace Performance Degradation

**What goes wrong:**
"Unifying" Gradio Chat UI, HTMX Dashboard, and MLFlow into one workspace creates performance issues. Each UI component has different update patterns: Gradio streams responses, HTMX uses SSE for real-time updates, MLFlow loads large experiment lists. Combining them creates resource contention.

**Why it happens:**
Unified workspace often means "load everything at once" or "embed iframes." MLFlow UI embedded via iframe loads its own JavaScript. Gradio maintains WebSocket connections. HTMX dashboard polls or uses SSE. Browser tabs consume hundreds of MB of memory.

**Consequences:**
- Browser tab consumes 1-2GB memory
- Page load times exceed 10 seconds
- Real-time updates lag or fail
- Browser crashes on lower-spec machines
- Users prefer separate tabs/windows for performance
- Defeats the purpose of "unified" workspace

**Prevention:**

1. **Lazy loading:** Load UI components on-demand, not all at startup
2. **Separate tabs:** Keep Gradio, Dashboard, MLFlow as separate routes (not one page)
3. **Resource limits:** Cap memory usage, stream large datasets
4. **Connection pooling:** Reuse WebSocket/SSE connections, don't open new ones per component
5. **Performance budgets:** Set targets (e.g., <3s initial load, <500ms subsequent navigation)
6. **Optional embedding:** Make MLFlow iframe optional, not required

**Detection:**
- Browser DevTools showing 1GB+ memory usage
- Page load times >5 seconds on decent hardware
- Users complaining about slowness or crashes
- Preference for opening components in separate tabs

**Phase to address:** Phase 03-05 (Unified Workspace) — Important. Must measure performance before unifying components.

---

### Pitfall 6: Hiding Power Features Behind "Simplified" UI

**What goes wrong:**
In pursuit of "simplified" UX, power features become hidden or removed. Advanced users who relied on these features feel the tool has been "dumbed down." The clear entry point for new users becomes a barrier for power users.

**Why it happens:**
UX improvements often target new users, assuming power users will "figure it out." Advanced features get moved to sub-menus, hidden behind "advanced" toggles, or removed entirely to "simplify" the interface.

**Consequences:**
- Power users migrate to more flexible tools
- "I can't find X anymore" support tickets
- Feature requests to restore hidden functionality
- Reputation: "v1.1 is good for beginners, but power users should stay on v1.0"
- Loss of advanced user community contributions

**Prevention:**

1. **Progressive disclosure:** Simple by default, powerful when needed
2. **Preserve all v1.0 features:** No feature removal in v1.1
3. **Advanced mode toggle:** Let users opt into complex UI
4. **Keyboard shortcuts:** Preserve power user efficiencies
5. **CLI access:** Advanced features always available via CLI even if hidden in UI
6. **Document migration:** Where did v1.0 features go in v1.1?

**Detection:**
- Power users requesting "classic mode" or v1.0 behavior
- Negative feedback in advanced user communities
- Workarounds being shared to access hidden features
- Decreased usage of advanced features (analytics)

**Phase to address:** All UX phases — Continuous. Review each change for impact on power users.

**Real-world examples:**
- **Figma redesign:** Advanced features hidden behind new UI, power users complained about lost efficiencies
- **Many developer tools:** "Simplified" releases often alienate early adopters who made the tool popular

---

### Pitfall 7: MLFlow Auto-Start Blocking Entire Dashboard

**What goes wrong:**
MLFlow auto-start is integrated into dashboard startup. If MLFlow fails to start (port conflict, dependency issue), the entire dashboard becomes unusable. Users can't access workflow management because observability is down.

**Why it happens:**
MLFlow is treated as a hard dependency rather than an optional component. Dashboard startup sequence waits for MLFlow before serving. This creates unnecessary coupling.

**Consequences:**
- Dashboard unavailable if MLFlow port 5000 is in use
- Users forced to stop other services to run the platform
- "I just want to manage workflows, why do I need MLFlow?"
- Development workflow disrupted if MLFlow isn't needed
- False impression: platform is broken when it's just MLFlow

**Prevention:**

1. **Graceful degradation:** Dashboard works without MLFlow, shows "observability disabled"
2. **Start MLFlow asynchronously:** Don't block dashboard on MLFlow startup
3. **Clear status indicator:** Show "MLFlow: not running" with start button
4. **Optional observability:** Allow running without MLFlow for development
5. **Port auto-selection:** If 5000 is in use, try 5001, 5002, etc.
6. **Separate health checks:** Dashboard health != MLFlow health

**Detection:**
- Users asking "why can't I access dashboard?"
- Port 5000 conflicts preventing dashboard use
- Development environments where MLFlow isn't desired
- Confusion about which component is actually failing

**Phase to address:** Phase 03-07 (Graceful MLFlow Handling) — Critical. Must implement graceful degradation before auto-start.

---

### Pitfall 8: FastAPI + HTMX Navigation State Loss

**What goes wrong:**
HTMX-based navigation loses application state when switching views. Browser back button doesn't work as expected. Refreshing the page loses current context. This breaks user expectations of web navigation.

**Why it happens:**
HTMX updates DOM fragments without changing browser URL by default. Without proper history management, the browser back button returns to the previous website, not the previous dashboard view. State is stored in server-side session, lost on refresh.

**Consequences:**
- Back button exits dashboard instead of going to previous view
- Refresh returns to home page, losing user's place
- Users can't bookmark specific dashboard views
- Navigation feels "broken" compared to modern web apps
- Support burden: "how do I get back to X?"

**Prevention:**

1. **HTMX history management:** Use `hx-push-url="true"` for all navigable views
2. **RESTful URLs:** Each view has a unique URL (`/workflows`, `/agents`, `/observability`)
3. **State in URL:** Encode view state in query params when appropriate
4. **Back button testing:** Verify back/forward work in each navigation change
5. **Bookmarkable views:** Deep links should restore full view state
6. **Progressive enhancement:** Ensure navigation works without JavaScript

**Detection:**
- Users complaining that back button doesn't work
- Inability to bookmark specific dashboard pages
- State loss on page refresh
- Navigation testing reveals URL doesn't change

**Phase to address:** Phase 03-03 (Navigation Redesign) — Important. HTMX history management is non-negotiable.

**Sources:**
- [HTMX Navigation Methods](https://www.adharsh.in/blogs/tech/ui/htmx/htmx-navigation/) - Covers history API integration
- [Best practice for handling routes with HTMX](https://www.reddit.com/r/htmx/comments/1dt4gum/best_practice_for_handling_routes_with_htmx_and/) - Community patterns

---

### Pitfall 9: Gradio Chat UI Session Loss in Unified Workspace

**What goes wrong:**
When integrating Gradio Chat UI into a unified workspace, session persistence breaks. Conversations that persisted in standalone Gradio are lost when accessed through the unified interface. User's config generation progress disappears.

**Why it happens:**
Gradio's session storage uses file-based backend by default. Unified workspace may run Gradio with different storage configuration, or session files aren't properly mounted between standalone and integrated modes.

**Consequences:**
- Users lose conversation history when switching interfaces
- "I was chatting with the config generator, where did it go?"
- Loss of trust in session persistence
- Users revert to standalone Gradio to avoid data loss
- Unified workspace feels like a downgrade

**Prevention:**

1. **Shared session storage:** Ensure Gradio session path is consistent across modes
2. **Session migration:** Migrate standalone sessions to unified workspace
3. **Clear session UI:** Show conversation history prominently
4. **Export/import:** Allow users to save and load conversations
5. **Session continuity:** Same URL (`/gradio` and `/workspace/gradio`) share sessions
6. **Documentation:** Explain session persistence behavior

**Detection:**
- Users reporting lost conversations
- Inconsistent session behavior between standalone and integrated
- Confusion about where sessions are stored

**Phase to address:** Phase 03-05 (Unified Workspace) — Important. Session continuity must be verified before integration.

---

### Pitfall 10: Entry Point Tutorial That Never Completes

**What goes wrong:**
"Clear entry point" guided onboarding tutorial is too long, complex, or buggy. Users start it, get stuck halfway, and never complete it. The tutorial becomes a barrier rather than an on-ramp.

**Why it happens:**
Onboarding tutorials often cover every feature instead of the happy path. They require users to have API keys configured, MLFlow running, and example configs ready. If any dependency is missing, the tutorial fails.

**Consequences:**
- Users abandon the tutorial mid-way
- "I'll figure it out myself" — tutorial never used again
- Tutorial bugs create negative first impression
- Users skip valuable onboarding and miss core concepts
- Tutorial maintenance burden (keeps breaking)

**Prevention:**

1. **Short tutorial (<5 minutes):** Cover only the happy path
2. **Mock mode:** Tutorial works without real API keys (uses mock responses)
3. **Skip button:** Users can exit tutorial at any point
4. **Resume capability:** Tutorial progress is saved
5. **Focus on core value:** Demonstrate one end-to-end workflow, not every feature
6. **Progressive:** Advanced concepts in follow-up tutorials, not initial onboarding

**Detection:**
- Analytics: tutorial completion rate <50%
- Users starting tutorial but not finishing
- Negative feedback about tutorial complexity
- Support tickets: "stuck in tutorial step X"

**Phase to address:** Phase 03-06 (Clear Entry Point) — Important. Tutorial completion rate is key metric.

---

## Moderate Pitfalls

Mistakes that cause delays or technical debt but are recoverable.

### Pitfall 11: Docker Port Conflicts on Single-Command Startup

**What goes wrong:**
`agents up` fails silently because ports 5000 (MLFlow) or 8000 (Dashboard) are already in use. Error message is unclear or suggests wrong fix.

**Prevention:** Detect port conflicts before starting services, suggest alternative ports or stop conflicting services.

**Detection:** Users reporting "`agents up` doesn't work" with no clear error.

**Phase:** Phase 03-01

---

### Pitfall 12: SQLite Database File Permission Errors on Auto-Init

**What goes wrong:**
Auto-initialization tries to create SQLite database in directory without write permissions. Error message is unclear about permission issue.

**Prevention:** Check directory writability before attempting database creation. Fall back to user home directory with clear message.

**Detection:** "Failed to create database" errors that are actually permission issues.

**Phase:** Phase 03-01

---

### Pitfall 13: Status Dashboard Polling Overloading Backend

**What goes wrong:**
HTMX dashboard polls backend every 1-2 seconds for status updates. With multiple users, this creates unnecessary load.

**Prevention:** Use Server-Sent Events (SSE) for real-time updates instead of polling. Implement polling only as fallback.

**Detection:** Backend CPU usage spikes with multiple dashboard users.

**Phase:** Phase 03-04

---

## Minor Pitfalls

Mistakes that cause annoyance but are fixable.

### Pitfall 14: Inconsistent Terminology Between Old and New UI

**What goes wrong:** Navigation changes rename concepts ("Agents" becomes "Workflows") without updating all references. Users can't find things.

**Prevention:** Create terminology glossary, search for old terms when renaming.

**Phase:** All UX phases

---

### Pitfall 15: Dark Mode Color Contrast Issues in Unified Workspace

**What goes wrong:** Unifying components with different dark mode implementations creates inconsistent appearance and contrast issues.

**Prevention:** Standardize color palette, test contrast ratios across all components.

**Phase:** Phase 03-05

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **03-01: Single-command startup** | Silent failures, hiding diagnostic info | Verbose mode, health checks, clear error messages |
| **03-01: Auto-initialization** | Silent state corruption, permission errors | Blocking errors, idempotent init, status command |
| **03-03: Navigation redesign** | Muscle memory disruption | Preserve 80% of paths, transition period, opt-out |
| **03-04: Status visibility** | Alert fatigue, dashboard overload | Tiered status, max 5 key metrics, smart alerting |
| **03-05: Unified workspace** | Performance degradation, session loss | Lazy loading, shared session storage, perf budgets |
| **03-06: Clear entry point** | Tutorial abandonment | Short tutorial (<5 min), mock mode, skip button |
| **03-07: MLFlow handling** | Dashboard blocked by MLFlow failure | Graceful degradation, async start, optional observability |

---

## Pitfall-to-Feature Mapping

Each v1.1 planned change has specific pitfalls to address:

| v1.1 Feature | Critical Pitfalls | Moderate | Minor |
|--------------|-------------------|----------|-------|
| **UX-01: Single command startup** | Pitfall 4 (hiding diagnostics), Pitfall 11 (port conflicts) | - | - |
| **UX-02: Auto-initialization** | Pitfall 2 (silent failures), Pitfall 12 (permissions) | - | - |
| **UX-03: Navigation redesign** | Pitfall 1 (muscle memory), Pitfall 8 (HTMX state loss) | Pitfall 14 (terminology) | - |
| **UX-04: Status visibility** | Pitfall 3 (alert fatigue), Pitfall 13 (polling overload) | - | - |
| **UX-05: Unified workspace** | Pitfall 5 (performance), Pitfall 9 (session loss) | - | Pitfall 15 (dark mode) |
| **UX-06: Clear entry point** | Pitfall 10 (tutorial abandonment) | - | - |
| **UX-07: MLFlow handling** | Pitfall 7 (blocking dashboard) | - | - |

---

## Integration-Specific Pitfalls: FastAPI + HTMX + Gradio

The v1.0 stack (FastAPI + HTMX for dashboard, Gradio for chat UI) has unique integration challenges:

### HTMX-Specific Pitfalls

1. **History management not configured:** Browser back button breaks navigation
   - **Fix:** Add `hx-push-url="true"` to all navigation links

2. **SSE vs polling confusion:** Real-time updates implemented via polling instead of SSE
   - **Fix:** Use HTMX's SSE extension for status updates

3. **Partial update complexity:** HTMX partial updates conflict with full page renders
   - **Fix:** Standardize on fragment updates, use `hx-boost` for navigation

### Gradio Integration Pitfalls

1. **Mount path conflicts:** Gradio mounted at `/gradio` conflicts with dashboard routes
   - **Fix:** Use `/chat` or `/config-generator` to avoid conflicts

2. **Session storage isolation:** Gradio sessions not shared between standalone and integrated
   - **Fix:** Ensure `root_path` and session storage path are consistent

3. **CORS issues:** Gradio app under FastAPI has CORS problems
   - **Fix:** Configure FastAPI CORS middleware correctly

### FastAPI Integration Pitfalls

1. **Route naming collisions:** Dashboard routes conflict with Gradio routes
   - **Fix:** Namespace routes clearly (`/dashboard/*`, `/api/*`, `/chat/*`)

2. **Startup sequence dependency:** Dashboard depends on Gradio being ready
   - **Fix:** Async startup with health checks, not hard dependency

3. **Template context pollution:** Shared Jinja2 context causes variable conflicts
   - **Fix:** Use context processors, isolate template contexts per component

**Sources:**
- [Building Real-Time Dashboards with FastAPI and HTMX](https://medium.com/codex/building-real-time-dashboards-with-fastapi-and-htmx-01ea458673cb)
- [FastAPI App with Gradio Client](https://www.gradio.app/guides/fastapi-app-with-the-gradio-client)
- [Gradio FastAPI Conductor Dashboard Pattern](https://gist.github.com/ruvnet/1863854d9cb84b09531217bbc410270f)

---

## Success Criteria for v1.1 UX Improvements

Each pitfall has corresponding success criteria:

| Pitfall | Success Criteria | How to Measure |
|---------|------------------|----------------|
| **1. Muscle memory disruption** | <20% productivity loss for existing users | Survey: "How long to find feature X?" vs baseline |
| **2. Silent auto-init failures** | 0% silent failures, all failures block with clear error | Test: Init failures in various scenarios |
| **3. Alert fatigue** | <5 status indicators shown by default, users can customize | Heuristic review, user testing |
| **4. Hidden diagnostics** | Verbose mode shows all startup steps, all errors actionable | Test: `agents up --verbose` output quality |
| **5. Performance degradation** | <3s page load, <500MB memory usage for unified workspace | Performance tests on reference hardware |
| **6. Hidden power features** | 100% of v1.0 features accessible, documented migration | Feature audit, power user survey |
| **7. MLFlow blocking dashboard** | Dashboard works without MLFlow, graceful degradation shown | Test: Start with MLFlow port blocked |
| **8. HTMX navigation state loss** | Back button works, refresh preserves state, URLs bookmarkable | Browser testing, navigation test suite |
| **9. Session loss in unified workspace** | Sessions persist across standalone and integrated modes | Test: Chat in standalone, open integrated, verify history |
| **10. Tutorial abandonment** | >70% completion rate for first-time users | Analytics: tutorial start vs complete |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces for UX improvements:

- [ ] **Single-command startup:** Often missing verbose mode and clear error messages — verify `agents up --verbose` shows diagnostic steps, verify port conflicts are detected
- [ ] **Auto-initialization:** Often missing health checks and error recovery — verify initialization failures are blocking, verify idempotent re-initialization
- [ ] **Navigation redesign:** Often missing transition period and opt-out — verify old navigation paths still work, verify users can revert to classic mode
- [ ] **Status visibility:** Often missing tiered status and smart alerting — verify only 3-5 metrics shown by default, verify alerts are actionable
- [ ] **Unified workspace:** Often missing performance budgets and session continuity — verify memory usage under control, verify sessions persist across modes
- [ ] **Clear entry point:** Often missing skip button and resume capability — verify tutorial is <5 minutes, verify users can exit at any point
- [ ] **MLFlow handling:** Often missing graceful degradation — verify dashboard works without MLFlow, verify status indicator is clear
- [ ] **HTMX navigation:** Often missing history management — verify back button works, verify URLs are bookmarkable
- [ ] **Gradio integration:** Often missing session storage continuity — verify sessions work in both standalone and integrated modes
- [ ] **Error messages:** Often missing action items — verify every error suggests next step

---

## Sources

### Muscle Memory & Navigation Redesign

- [The Cost of Disrupting Muscle Memory: Figma UI Redesign](https://medium.com/@shafihireholi/the-cost-of-disrupting-muscle-memory-a-look-at-figmas-ui-redesign-through-real-world-analogies-c8174d341eae) — Real-world consequences of disrupting user habits
- [The Impact of the 2023 Wikipedia Redesign on User Experience](https://www.mdpi.com/2227-9709/12/3/97) — Research-backed evidence of navigation change impact (MDPI 2025)
- [How to Redesign a Legacy UI Without Losing Users](https://xbsoftware.com/blog/legacy-app-ui-redesign-mistakes/) — Practical guidance on legacy redesigns (August 2025)
- [Human Memory and UX Design: Preventing Cognitive Overload](https://fireart.studio/blog/human-memory-and-ux-design-how-to-prevent-user-cognitive-overload/) — Memory principles for UX

### Alert Fatigue & Status Dashboard Overload

- [Alert Fatigue and Dashboard Overload: Why Cybersecurity Needs Better UX](https://medium.com/design-bootcamp/alert-fatigue-and-dashboard-overload-why-cybersecurity-needs-better-ux-1f3bd32ad81c) — Enterprise dashboard overload patterns
- [Alert Fatigue Solutions for DevOps Teams in 2025](https://incident.io/blog/alert-fatigue-solutions-for-dev-ops-teams-in-2025-what-works) — What's working for alert management
- [AWS Well-Architected: Optimize Alerts to Prevent Fatigue](https://docs.aws.amazon.com/wellarchitected/latest/devops-guidance/o.cm.9-optimize-alerts-to-prevent-fatigue-and-minimize-monitoring-costs.html) — Official AWS guidance on alert optimization
- [Tool Overload Driving Alert Fatigue](https://mspaa.net/report-reveals-tool-overload-driving-alert-fatigue-and-missed-threats-in-msps/) — Tool sprawl impact analysis

### FastAPI + HTMX + Gradio Integration

- [Building Real-Time Dashboards with FastAPI and HTMX](https://medium.com/codex/building-real-time-dashboards-with-fastapi-and-htmx-01ea458673cb) — Dashboard patterns with this stack
- [HTMX Navigation Methods](https://www.adharsh.in/blogs/tech/ui/htmx/htmx-navigation/) — History management and URL updates
- [Best Practice for HTMX Routes](https://www.reddit.com/r/htmx/comments/1dt4gum/best_practice_for_handling_routes_with_htmx_and/) — Community routing patterns
- [FastAPI App with Gradio Client](https://www.gradio.app/guides/fastapi-app-with-the-gradio-client) — Official Gradio integration docs
- [Gradio FastAPI Conductor Pattern](https://gist.github.com/ruvnet/1863854d9cb84b09531217bbc410270f) — Unified workspace pattern

### MLFlow & Observability

- [MLflow Automatic Logging Documentation](https://mlflow.org/docs/latest/ml/tracking/autolog/) — Official autolog patterns
- [MLflow UI Performance Issue #1517](https://github.com/mlflow/mlflow/issues/1517) — Real-world performance problems with MLflow UI
- [MLflow CLI Documentation](https://mlflow.org/docs/latest/cli.html) — Command-line interface for startup

### Developer Tool UX Patterns

- [7 Modern CLI Tools You Must Try in 2026](https://aashishkumar12376.medium.com/7-modern-cli-tools-you-must-try-in-2026-18e54106224e) — Modern CLI UX patterns
- [Top 8 Observability Tools for 2026](https://www.groundcover.com/blog/observability-tools) — Current state of observability UX
- [Website Navigation Best Practices](https://www.wearetenet.com/blog/website-navigation-best-practices) — General navigation principles

---

*Pitfalls research for: v1.1 Core UX Polish*
*Researched: 2026-02-04*
*Confidence: HIGH - Findings based on UX research, real-world redesign case studies, and authoritative sources on developer tool UX*
