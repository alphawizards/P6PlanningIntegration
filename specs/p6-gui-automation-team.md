# Plan: P6 GUI Automation Team

## Task Description
Develop a hierarchical AI agent team to control Oracle Primavera P6 via local GUI automation. The system will enable users to prompt for complex schedule changes (e.g., "Extending all engineering tasks by 2 weeks") which are then executed by a dedicated GUI automation agent and verified by an analysis agent.

## Objective
Enable natural language control of the P6 desktop application using `pywinauto`-based GUI automation, orchestrated by a "Team" of specialized agents.

## Problem Statement
Current AI integration (`src.ai`) is primarily read-only or uses "proposals" via database/API access. It lacks the ability to directly drive the P6 UI for operations that require visual confirmation or are not exposed via the SQLite/API layer (e.g., specific layout applications, printing, complex UI workflows). The user wants a system that "clicks buttons" to ensure changes are made exactly as a human would.

## Solution Approach
Implement a multi-agent system using the `plan_w_team` pattern:
1.  **Orchestrator (Lead)**: Parses user prompts, plans the workflow, and delegates tasks.
2.  **GUI Driver (Executor)**: Exposes `src.automation` modules as tools to perform click/type actions.
3.  **Analyst (Verifier)**: Uses `src.dao` to verify data integrity and schedule health before/after changes.

## Relevant Files
Use these files to complete the task:
- `src/ai/agent.py`: Existing agent (to be refactored or wrapped).
- `src/ai/tools.py`: Existing tools (to be split/expanded).
- `src/automation/*.py`: Existing GUI automation modules (to be exposed as tools).
- `specs/p6-gui-automation-team.md`: This plan.

## Implementation Phases
### Phase 1: Foundation
- Create `src/ai/team/` directory structure.
- Define `TeamMember` interfaces.
- Create `P6GUITools` wrapper around `src.automation` classes (`P6ActivityManager`, etc.).

### Phase 2: Core Implementation
- **Driver Agent**: Implement an agent with access to `P6GUITools`.
- **Analyst Agent**: Implement an agent with access to `P6Tools` (read-only/analysis).
- **Orchestrator**: Implement the main router that calls Driver/Analyst based on the plan.

### Phase 3: Integration & Polish
- Implement "Human-in-the-loop" confirmation for critical GUI actions.
- Add visual feedback (highlighting elements before clicking).
- Create a "Plan -> Execute -> Verify" loop.

## Team Orchestration
- **Lead**: `P6-Orchestrator` (Deep Thinker/Planner)
- **Members**:
    - `P6-Driver`: specialized in `pywinauto` interaction.
    - `P6-Verifier`: specialized in rigorous post-action validation.
    - `P6-Analyst`: specialized in high-level data query and schedule health checks.

### Team Members
- Builder
  - Name: **P6-Driver**
  - Role: Executes GUI commands (clicks, typing).
  - Agent Type: `general-purpose` (with GUI tools context)
  
- Builder
  - Name: **P6-Verifier**
  - Role: Validates outcomes of Driver actions by querying the DB.
  - Agent Type: `general-purpose` (with DB tools context)

- Builder
  - Name: **P6-Analyst**
  - Role: High-level schedule intelligence (health checks, impact analysis).
  - Agent Type: `general-purpose` (with DB tools context)

## Step by Step Tasks

### 1. Create Team Directory Structure
- **Task ID**: setup-team-structure
- **Depends On**: none
- **Assigned To**: P6-Driver
- **Parallel**: false
- Create `src/ai/team/__init__.py`.
- Create `src/ai/team/base.py` for agent interfaces.

### 2. Implement GUI Tools Wrapper
- **Task ID**: implement-gui-tools
- **Depends On**: setup-team-structure
- **Assigned To**: P6-Driver
- **Parallel**: false
- Create `src/ai/tools/gui_tools.py`.
- Wrap `P6ActivityManager` methods (select, edit, delete, add).
- Wrap `P6ScheduleManager` (F9).
- Ensure all tools have proper error handling and timeouts.

### 3. Implement Verification Logic
- **Task ID**: implement-verification
- **Depends On**: none
- **Assigned To**: P6-Verifier
- **Parallel**: true
- Create `src/ai/team/verifier.py`.
- Implement specific validation functions (e.g., `verify_activity_field`, `verify_schedule_log`).
- These functions must be independent of the Driver's logic (trust but verify via DB).

### 4. Implement Execution Loop
- **Task ID**: implement-execution-loop
- **Depends On**: implement-gui-tools, implement-verification
- **Assigned To**: P6-Driver
- **Parallel**: false
- Create `src/ai/team/driver.py`.
- Implement `execute_plan` that takes a list of actions.
- **CRITICAL**: Every action must be followed by a call to `P6-Verifier`.

### 5. Final Integration
- **Task ID**: integrate-system
- **Depends On**: implement-execution-loop
- **Assigned To**: P6-Orchestrator
- **Parallel**: false
- Update `main.py` to support `--team` mode.
- Connect User Input -> Orchestrator -> Driver -> Verifier Loop.

## Acceptance Criteria
- [ ] User can say "Change activity A100 duration to 5 days".
- [ ] System plans: Select A100 -> Edit Duration -> 5 -> Verify.
- [ ] System executes: `P6ActivityManager` types keys to edit.
- [ ] System verifies: Reads DB to confirm duration is 5.
- [ ] System reports success.

## Validation Commands
- `python main.py --team --chat`
