# Multi-Agent Claude Code Setup Guide
## P6PlanningIntegration — Minimal Viable Agent Team

**Target Project:** `C:\Users\ckr_4\01 Projects\P6PlanningIntegration`  
**Agent Team:** Orchestrator/Planner → Builder → Tester/Validator  
**Based on:** Indy Dev Dan's multi-agent observability pattern + Claude Code Agent Teams

---

## ⚠️ Critical Windows Compatibility Note

**Split-pane mode (tmux) does NOT work natively on Windows Terminal.** You have two options:

| Option | Pros | Cons |
|--------|------|------|
| **WSL (Recommended)** | Full tmux support, split panes, see all agents | Requires WSL setup |
| **In-Process Mode** | Works in any terminal, zero setup | Tab between agents with Shift+Up/Down, no simultaneous view |

**Recommendation:** Use WSL for the full experience with tmux split panes. If you want to get started fast, in-process mode works immediately.

---

## Phase 1: Prerequisites Setup

### 1.1 Install WSL (for tmux support)

Open PowerShell as Administrator:
```powershell
wsl --install
```
Restart your computer, then open WSL (Ubuntu) and run:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install tmux -y
```

### 1.2 Install Claude Code (inside WSL)

```bash
# Install Node.js (required for Claude Code)
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Verify
claude --version
```

### 1.3 Install Required Tools (inside WSL)

```bash
# Install Bun (for observability server)
curl -fsSL https://bun.sh/install | bash
source ~/.bashrc

# Install Astral uv (for hook scripts)
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Install Python 3.12+
sudo apt install python3 python3-pip -y

# Verify all tools
bun --version
uv --version
python3 --version
```

### 1.4 Set Up API Keys

Create/edit `~/.bashrc` in WSL:
```bash
# Add these lines to ~/.bashrc
export ANTHROPIC_API_KEY="sk-ant-your-key-here"
export E2B_API_KEY="sbx_your-e2b-key-here"
export ENGINEER_NAME="CKR"

# Enable Agent Teams (experimental)
export CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1
```
Then: `source ~/.bashrc`

---

## Phase 2: Project Directory Setup

### 2.1 Access Windows Project from WSL

Your Windows project path maps to WSL as:
```bash
# Your project in WSL
cd /mnt/c/Users/ckr_4/01\ Projects/P6PlanningIntegration

# Create a symlink for convenience
ln -s "/mnt/c/Users/ckr_4/01 Projects/P6PlanningIntegration" ~/p6project
```

### 2.2 Clone Required Repos

```bash
# Working directory for setup resources
cd /mnt/c/Users/ckr_4/01\ Projects

# Clone the observability system
git clone https://github.com/disler/claude-code-hooks-multi-agent-observability.git

# Clone the sandbox skill
git clone https://github.com/disler/agent-sandbox-skill.git
```

---

## Phase 3: Agent Teams Configuration

### 3.1 Enable Agent Teams

Create/edit the global Claude settings:
```bash
mkdir -p ~/.claude
cat > ~/.claude/settings.json << 'EOF'
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "permissions": {
    "allow": [
      "Bash(find:*)",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(grep:*)",
      "Bash(head:*)",
      "Bash(tail:*)",
      "Bash(wc:*)",
      "Bash(git:*)",
      "Bash(npm:*)",
      "Bash(node:*)",
      "Bash(python*:*)",
      "Bash(uv:*)",
      "Bash(mkdir:*)",
      "Bash(cp:*)",
      "Bash(mv:*)",
      "Bash(touch:*)",
      "Bash(echo:*)",
      "Read",
      "Write",
      "Edit",
      "MultiEdit"
    ]
  }
}
EOF
```

### 3.2 Set Up Project-Level CLAUDE.md

Create `CLAUDE.md` in your P6PlanningIntegration project root. This is what all agents (lead + teammates) will read:

```bash
cat > ~/p6project/CLAUDE.md << 'CLAUDEEOF'
# P6 Planning Integration — Agent Instructions

## Project Overview
This project integrates with Primavera P6 planning/scheduling software. 
[Add your specific project description here]

## Architecture
[Describe your project structure, key files, tech stack]

## Conventions
- [Your coding conventions]
- [File naming patterns]
- [Branch strategy]

## Agent Team Roles
When working as part of an agent team:

### Orchestrator/Planner (Lead)
- Creates implementation plans before delegating work
- Breaks tasks into independent, parallelizable units
- Reviews completed work before marking tasks done
- Does NOT implement code directly — delegates to Builder

### Builder Agent
- Implements code changes based on task specifications
- Follows project conventions strictly
- Writes clean, documented code
- Reports completion with summary of changes

### Tester/Validator Agent
- Writes and runs tests for completed features
- Validates code quality and conventions
- Reports issues back to lead with specific file/line references
- Runs linting, type checks, and integration tests

## Key Files
[List your important files and their purposes]

## Dependencies
[List project dependencies]
CLAUDEEOF
```

### 3.3 Create AGENTS.md (Agent-Specific Context)

```bash
cat > ~/p6project/AGENTS.md << 'AGENTSEOF'
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
AGENTSEOF
```

---

## Phase 4: Observability System Setup

### 4.1 Install and Configure Observability

```bash
cd /mnt/c/Users/ckr_4/01\ Projects/claude-code-hooks-multi-agent-observability

# Install dependencies
cd apps/server && bun install
cd ../client && bun install
cd ../..

# Copy .env sample
cp .env.sample .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 4.2 Copy Hooks to Your Project

```bash
# Copy the .claude hooks directory to your project
cp -R .claude ~/p6project/.claude-hooks-backup  # backup if exists
cp -R .claude ~/p6project/.claude/

# Update source-app name in your project's hooks
cd ~/p6project
sed -i 's/cc-hooks-observability/p6-planning/g' .claude/settings.json
```

### 4.3 Merge Settings (Hooks + Agent Teams)

Edit `~/p6project/.claude/settings.json` to include BOTH the hooks AND agent teams config:

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  },
  "permissions": {
    "allow": [
      "Bash(find:*)", "Bash(ls:*)", "Bash(cat:*)", "Bash(grep:*)",
      "Bash(git:*)", "Bash(npm:*)", "Bash(node:*)", "Bash(python*:*)",
      "Bash(uv:*)", "Bash(mkdir:*)", "Bash(cp:*)", "Bash(mv:*)",
      "Read", "Write", "Edit", "MultiEdit"
    ]
  },
  "hooks": {
    "PreToolUse": [{
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "uv run .claude/hooks/pre_tool_use.py"
        },
        {
          "type": "command",
          "command": "uv run .claude/hooks/send_event.py --source-app p6-planning --event-type PreToolUse --summarize"
        }
      ]
    }],
    "PostToolUse": [{
      "matcher": "",
      "hooks": [
        {
          "type": "command",
          "command": "uv run .claude/hooks/post_tool_use.py"
        },
        {
          "type": "command",
          "command": "uv run .claude/hooks/send_event.py --source-app p6-planning --event-type PostToolUse --summarize"
        }
      ]
    }],
    "Notification": [{
      "hooks": [{
        "type": "command",
        "command": "uv run .claude/hooks/send_event.py --source-app p6-planning --event-type Notification --summarize"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run .claude/hooks/send_event.py --source-app p6-planning --event-type Stop --summarize"
      }]
    }],
    "SubagentStop": [{
      "hooks": [{
        "type": "command",
        "command": "uv run .claude/hooks/send_event.py --source-app p6-planning --event-type SubagentStop --summarize"
      }]
    }]
  }
}
```

**Important:** After setting up hooks, run this inside Claude Code to convert relative paths to absolute:
```
/convert_paths_absolute
```

---

## Phase 5: E2B Sandbox Setup (Optional — Free Tier)

### 5.1 Install E2B CLI

```bash
# Inside your project, set up the sandbox skill
cp -R /mnt/c/Users/ckr_4/01\ Projects/agent-sandbox-skill/.claude/skills ~/p6project/.claude/skills

# Install sandbox CLI dependencies
cd ~/p6project/.claude/skills/agent-sandboxes/sandbox_cli
uv sync
```

### 5.2 Configure E2B

```bash
# Create .env in project root
echo "E2B_API_KEY=sbx_your-key-here" >> ~/p6project/.env
```

### 5.3 Free Tier Strategy

With the free tier, be strategic about sandbox usage:
- **Orchestrator/Planner:** Never needs a sandbox (pure coordination)
- **Builder:** Use local execution primarily, sandbox only for risky operations
- **Tester:** Use sandbox for integration tests that need isolation

---

## Phase 6: Running Your Agent Team

### 6.1 Start the Observability Dashboard

In a separate terminal:
```bash
cd /mnt/c/Users/ckr_4/01\ Projects/claude-code-hooks-multi-agent-observability
./scripts/start-system.sh

# Dashboard available at: http://localhost:5173
# Server runs on: http://localhost:4000
```

### 6.2 Start tmux and Launch Claude Code

```bash
# Start a tmux session
tmux new-session -s p6agents

# Navigate to project
cd ~/p6project

# Launch Claude Code
claude
```

### 6.3 Prompt to Create Your Agent Team

Once inside Claude Code, use this prompt to spin up your 3-agent team:

```
I need to work on the P6 Planning Integration project. Create an agent team 
with the following structure:

1. You (lead) act as the Orchestrator/Planner — you plan work, create tasks 
   with dependencies, and coordinate. Do NOT implement code yourself.

2. Spawn a teammate called "builder" — responsible for all code implementation. 
   Give them full context about the project from CLAUDE.md and AGENTS.md.

3. Spawn a teammate called "tester" — responsible for writing tests, running 
   validation, checking code quality. Their tasks should depend on the builder's 
   tasks completing first.

Start by reading CLAUDE.md and AGENTS.md, then analyze the current project 
state and create an initial task plan for: [DESCRIBE YOUR CURRENT TASK HERE]
```

### 6.4 tmux Navigation Cheatsheet

| Action | Keys |
|--------|------|
| Switch between panes | `Ctrl+B` then arrow keys |
| Zoom into a pane | `Ctrl+B` then `Z` |
| Scroll in a pane | `Ctrl+B` then `[` (then arrows/PgUp/PgDn, `q` to exit) |
| New window | `Ctrl+B` then `C` |
| List sessions | `tmux ls` |
| Kill team session | `tmux kill-session -t p6agents` |
| Detach (keep running) | `Ctrl+B` then `D` |
| Reattach | `tmux attach -t p6agents` |

### 6.5 In-Process Mode Navigation (if not using tmux)

| Action | Keys |
|--------|------|
| Switch between teammates | `Shift+Up` / `Shift+Down` |
| View teammate session | `Enter` |
| Interrupt teammate | `Escape` |
| Toggle task list | `Ctrl+T` |
| Toggle delegate mode | `Shift+Tab` |

---

## Phase 7: Recommended Workflow

### Daily Workflow

```
1. Open WSL terminal
2. Start observability:    cd claude-code-hooks-multi-agent-observability && ./scripts/start-system.sh
3. Open browser:           http://localhost:5173
4. Start tmux:             tmux new-session -s p6agents
5. Navigate to project:    cd ~/p6project
6. Launch Claude Code:     claude
7. Create team and assign work
8. Monitor via dashboard + tmux panes
9. When done: let lead clean up the team
10. Kill tmux:             tmux kill-session -t p6agents
```

### Tips for Your 3-Agent Setup

1. **Use Delegate Mode** — Press `Shift+Tab` after creating the team so the lead only coordinates and doesn't start coding itself.

2. **Pre-approve permissions** — The settings.json above pre-approves common operations. This prevents permission prompts from interrupting teammates.

3. **Keep tasks independent** — Structure builder tasks so each touches different files. Two agents editing the same file = conflicts.

4. **Task dependency chain** — Always make tester tasks depend on builder tasks:
   ```
   Task 1: [Builder] Implement feature X
   Task 2: [Tester] Test feature X (blocked by Task 1)
   ```

5. **Rich spawn prompts** — Teammates start with blank context. Include project details, conventions, and specific goals in spawn prompts.

6. **Monitor the dashboard** — The observability dashboard shows real-time events from all agents. Filter by session to inspect individual agent behavior.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Hooks not firing | Run `/convert_paths_absolute` in Claude Code |
| Observability server not receiving events | Check server is running on port 4000: `curl http://localhost:4000/events/recent` |
| tmux panes not appearing | Verify tmux is installed: `which tmux`. Ensure you started inside a tmux session |
| Agent Teams not available | Verify env var: `echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` should output `1` |
| Teammates stopping on errors | Send instructions via lead, or spawn replacement |
| Lead finishing too early | Tell lead: "Wait for all teammates to finish before proceeding" |
| E2B sandbox timeout | Free tier has time limits; use local execution when possible |
| Permission prompts blocking teammates | Add more operations to `permissions.allow` in settings.json |

---

## File Structure After Setup

```
C:\Users\ckr_4\01 Projects\
├── P6PlanningIntegration/           ← Your project
│   ├── .claude/
│   │   ├── settings.json            ← Hooks + Agent Teams + Permissions
│   │   ├── hooks/                   ← Observability hook scripts
│   │   │   ├── send_event.py
│   │   │   ├── pre_tool_use.py
│   │   │   ├── post_tool_use.py
│   │   │   └── ...
│   │   └── skills/                  ← E2B sandbox skill (optional)
│   │       └── agent-sandboxes/
│   ├── CLAUDE.md                    ← Project instructions (all agents read this)
│   ├── AGENTS.md                    ← Agent team configuration
│   ├── .env                         ← API keys (gitignored)
│   └── [your project files]
│
├── claude-code-hooks-multi-agent-observability/  ← Dashboard
│   ├── apps/server/                 ← Bun server (port 4000)
│   ├── apps/client/                 ← Vue dashboard (port 5173)
│   └── scripts/start-system.sh
│
└── agent-sandbox-skill/             ← E2B reference (skills copied to project)
```
