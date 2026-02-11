# Agent Team Configuration

## Team Structure: Minimal Viable Agent Team
- **Lead (Orchestrator/Planner):** Plans work, creates tasks, coordinates
- **builder:** Implements code changes from task specs
- **tester:** Validates, tests, and quality-checks completed work

## Task Flow
1. Lead analyzes the request and creates a plan
2. Lead creates tasks with dependencies (test tasks depend on build tasks)
3. Builder picks up implementation tasks
4. Tester picks up validation tasks once build tasks complete
5. Lead synthesizes results and reports back

## Communication Protocol
- Builder sends message to Lead when implementation complete
- Tester sends message to Lead with test results
- Lead coordinates any rework needed

## E2B Sandbox Usage (Free Tier)
- Use sandboxes sparingly — free tier has limited minutes
- Prefer local execution for simple tasks
- Reserve sandboxes for: untrusted code execution, full-stack testing, isolation needs
