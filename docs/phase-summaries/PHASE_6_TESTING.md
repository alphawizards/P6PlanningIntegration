# Phase 6: Real AI Integration & Schema Patch - Testing Guide

**Project:** P6PlanningIntegration  
**Repository:** https://github.com/alphawizards/P6PlanningIntegration  
**Phase:** 6 - Real AI Integration & Schema Patch  
**Status:** ✅ IMPLEMENTATION COMPLETE - READY FOR TESTING  

---

## Prerequisites

### 1. Install Dependencies

```bash
cd /home/ubuntu/P6PlanningIntegration
pip3 install -r requirements.txt
```

This will install:
- `litellm>=1.0.0` - LLM integration library
- `openpyxl>=3.0.0` - Excel export support

### 2. Configure LLM API Key

Edit `.env` file and add:

```bash
# AI/LLM Configuration
LLM_PROVIDER=anthropic
LLM_API_KEY=your_actual_api_key_here
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_TEMPERATURE=0.0
LLM_MAX_TOKENS=4096
```

**Get your API key from:**
- **Anthropic (Claude):** https://console.anthropic.com/
- **OpenAI (GPT):** https://platform.openai.com/api-keys
- **Google (Gemini):** https://makersuite.google.com/app/apikey

### 3. Verify P6 Connection

Ensure your P6 database credentials are configured in `.env`:

```bash
P6_LIB_DIR=/path/to/p6/lib
P6_DB_TYPE=standalone
P6_USER=your_p6_username
P6_PASS=your_p6_password
```

---

## Test Plan

### Test 1: Schema Verification (TotalFloat & ProjectObjectId)

**Objective:** Verify that the new fields are fetched from P6.

**Steps:**
1. Run the database connection test:
   ```bash
   python main.py
   ```

2. **Expected Output:**
   - Activities DataFrame should include `TotalFloat` and `ProjectObjectId` columns
   - Check the output: `print(activities_df.columns)`
   - Should see: `['ObjectId', 'Id', 'Name', 'Status', 'PlannedDuration', 'StartDate', 'FinishDate', 'TotalFloat', 'ProjectObjectId']`

3. **Verification:**
   - ✅ TotalFloat column present
   - ✅ ProjectObjectId column present
   - ✅ Values are not all None (if P6 data has these fields)

**Troubleshooting:**
- If TotalFloat is all None: P6 may not have calculated float yet (run schedule in P6)
- If columns missing: Check `src/core/definitions.py` - ACTIVITY_FIELDS should include both fields

---

### Test 2: AI Client Initialization

**Objective:** Verify LLM client can be initialized.

**Steps:**
1. Create test script `test_llm_client.py`:
   ```python
   from src.ai.llm_client import LLMClient, is_ai_enabled
   from src.config import settings
   
   print(f"AI Enabled: {is_ai_enabled()}")
   print(f"LLM Provider: {settings.LLM_PROVIDER}")
   print(f"LLM Model: {settings.LLM_MODEL}")
   
   if is_ai_enabled():
       try:
           client = LLMClient()
           print("✅ LLM Client initialized successfully")
       except Exception as e:
           print(f"❌ Error: {e}")
   else:
       print("❌ AI not enabled - check LLM_API_KEY in .env")
   ```

2. Run:
   ```bash
   python test_llm_client.py
   ```

3. **Expected Output:**
   ```
   AI Enabled: True
   LLM Provider: anthropic
   LLM Model: claude-3-5-sonnet-20241022
   ✅ LLM Client initialized successfully
   ```

**Verification:**
- ✅ AI Enabled shows True
- ✅ LLM Client initializes without errors
- ✅ API key is set in environment

**Troubleshooting:**
- If "AI not enabled": Check `.env` file has `LLM_API_KEY` set
- If "litellm not installed": Run `pip3 install litellm`
- If API key error: Verify key is valid and has credits

---

### Test 3: Simple LLM Call (Without Tools)

**Objective:** Verify basic LLM communication.

**Steps:**
1. Create test script `test_simple_llm.py`:
   ```python
   from src.ai.llm_client import LLMClient
   
   client = LLMClient()
   
   messages = [
       {"role": "user", "content": "Say 'Hello from P6 Integration' in exactly those words."}
   ]
   
   response = client.chat(messages)
   print(f"LLM Response: {response}")
   ```

2. Run:
   ```bash
   python test_simple_llm.py
   ```

3. **Expected Output:**
   ```
   LLM Response: Hello from P6 Integration
   ```

**Verification:**
- ✅ LLM responds with correct text
- ✅ No errors in communication
- ✅ Response is coherent

**Troubleshooting:**
- If timeout: Check internet connection
- If API error: Verify API key and account status
- If rate limit: Wait and retry

---

### Test 4: Function Calling (Tool Execution)

**Objective:** Verify LLM can call tools correctly.

**Steps:**
1. Create test script `test_function_calling.py`:
   ```python
   from src.ai.llm_client import LLMClient
   
   client = LLMClient()
   
   # Define a simple test tool
   tools = [
       {
           "name": "get_weather",
           "description": "Get current weather for a location",
           "parameters": {
               "type": "object",
               "properties": {
                   "location": {
                       "type": "string",
                       "description": "City name"
                   }
               },
               "required": ["location"]
           }
       }
   ]
   
   messages = [
       {"role": "user", "content": "What's the weather in San Francisco?"}
   ]
   
   text_response, tool_calls = client.chat_with_tools(messages, tools)
   
   print(f"Text Response: {text_response}")
   print(f"Tool Calls: {tool_calls}")
   
   if tool_calls:
       print(f"✅ LLM requested tool: {tool_calls[0]['name']}")
       print(f"   Arguments: {tool_calls[0]['arguments']}")
   else:
       print("❌ No tool calls - LLM should have called get_weather")
   ```

2. Run:
   ```bash
   python test_function_calling.py
   ```

3. **Expected Output:**
   ```
   Text Response: None
   Tool Calls: [{'id': 'toolu_...', 'name': 'get_weather', 'arguments': {'location': 'San Francisco'}}]
   ✅ LLM requested tool: get_weather
      Arguments: {'location': 'San Francisco'}
   ```

**Verification:**
- ✅ LLM returns tool_calls (not text response)
- ✅ Tool name is correct: `get_weather`
- ✅ Arguments are parsed correctly: `{'location': 'San Francisco'}`

**Troubleshooting:**
- If no tool calls: LLM may have returned text instead - check model supports function calling
- If wrong tool: Check tool descriptions are clear
- If parsing error: Check litellm version

---

### Test 5: Chat Mode (Mock - AI Disabled)

**Objective:** Verify chat mode works without AI (fallback mode).

**Steps:**
1. Temporarily disable AI by commenting out `LLM_API_KEY` in `.env`

2. Run chat mode:
   ```bash
   python main.py --chat
   ```

3. Try commands:
   ```
   You: help
   You: status
   You: list projects
   You: exit
   ```

4. **Expected Output:**
   - Help text displayed
   - Status shows "AI Enabled: ❌ No"
   - Projects listed (if P6 connection works)
   - Graceful exit

**Verification:**
- ✅ Chat mode starts without crashing
- ✅ Mock responses work
- ✅ Commands execute correctly
- ✅ Exit works cleanly

---

### Test 6: Chat Mode (AI Enabled - ReAct Loop)

**Objective:** Verify full ReAct loop with real LLM.

**Steps:**
1. Ensure `LLM_API_KEY` is set in `.env`

2. Run chat mode with a project:
   ```bash
   python main.py --chat --project 12345
   ```
   (Replace 12345 with actual project ObjectId)

3. Try queries:
   ```
   You: What is this project about?
   You: Show me all activities
   You: Find critical activities
   You: Show activity ACT-001
   You: Can we delay activity ACT-001 by 2 days?
   ```

4. **Expected Behavior:**
   - LLM receives project context
   - LLM calls appropriate tools (search_activities, get_activity_details, etc.)
   - Agent executes tools
   - LLM generates natural language response
   - Conversation flows naturally

**Verification:**
- ✅ Project context loaded
- ✅ LLM calls correct tools
- ✅ Tool results returned to LLM
- ✅ LLM generates coherent responses
- ✅ SAFE_MODE warnings appear for write operations
- ✅ Conversation memory works (multi-turn)

**Example Expected Output:**
```
You: Show me all activities

AI: Let me fetch the activities for this project.

[Agent calls search_activities tool]

AI: I found 45 activities in the project. Here are some key activities:

1. **Drill Blast Holes - Level 1** (ACT-001)
   - Status: In Progress
   - Duration: 16.0 hours
   - Total Float: 0.0 hours ⚠️ CRITICAL

2. **Load Explosives** (ACT-002)
   - Status: Not Started
   - Duration: 4.0 hours
   - Total Float: 2.0 hours

[... more activities ...]

Would you like me to focus on critical path activities or search for specific types of work?
```

**Troubleshooting:**
- If LLM doesn't call tools: Check system prompt injection
- If tool execution fails: Check logs for errors
- If responses are generic: Verify project context is loaded
- If conversation memory fails: Check message history building

---

### Test 7: Critical Path Identification (TotalFloat)

**Objective:** Verify TotalFloat field enables critical path analysis.

**Steps:**
1. In chat mode, ask:
   ```
   You: Show me critical activities
   ```

2. **Expected Behavior:**
   - LLM calls `get_critical_activities` tool
   - Tool filters activities where `TotalFloat <= 0`
   - LLM presents critical activities with warnings

**Verification:**
- ✅ Critical activities identified correctly
- ✅ TotalFloat values displayed
- ✅ LLM adds ⚠️ warnings for critical items
- ✅ Advice about critical path protection

**Example Expected Output:**
```
AI: I've identified the critical path activities (Total Float ≤ 0 hours):

🚨 **Critical Path Activities** (12 activities)

1. **Drill Blast Holes - Level 1** (ACT-001)
   - Total Float: 0.0 hours
   - Duration: 16.0 hours
   - Status: In Progress
   ⚠️ Any delay will impact project completion

2. **Load Explosives** (ACT-002)
   - Total Float: 0.0 hours
   - Duration: 4.0 hours
   - Status: Not Started
   ⚠️ Critical - must start on time

[... more critical activities ...]

**Recommendations:**
- Monitor these activities closely
- Ensure resources are available
- Consider adding float to non-critical activities as buffer
```

---

### Test 8: Relationship Queries (ProjectObjectId)

**Objective:** Verify ProjectObjectId enables relationship queries.

**Steps:**
1. In chat mode, ask:
   ```
   You: What are the predecessors of activity ACT-001?
   ```

2. **Expected Behavior:**
   - LLM calls `get_activity_details` to get ObjectId
   - LLM calls `get_activity_relationships` with ObjectId
   - Tool uses ProjectObjectId to fetch relationships efficiently
   - LLM presents predecessor/successor information

**Verification:**
- ✅ Activity found by ID
- ✅ Relationships fetched
- ✅ Predecessors and successors displayed
- ✅ Relationship types shown (FS, SS, FF, SF)

**Example Expected Output:**
```
AI: Let me check the relationships for activity ACT-001.

**Activity:** Drill Blast Holes - Level 1 (ACT-001)

**Predecessors:**
1. Survey Drill Pattern (ACT-000)
   - Type: Finish-to-Start (FS)
   - Lag: 0 hours

**Successors:**
2. Load Explosives (ACT-002)
   - Type: Finish-to-Start (FS)
   - Lag: 0 hours

3. Blast Execution (ACT-003)
   - Type: Finish-to-Start (FS)
   - Lag: 4 hours (ventilation clearance)

This activity is part of the critical path. Any delay will impact downstream activities.
```

---

### Test 9: Change Proposal (SAFE_MODE Protection)

**Objective:** Verify SAFE_MODE prevents execution of changes.

**Steps:**
1. Ensure `SAFE_MODE=true` in `.env`

2. In chat mode, ask:
   ```
   You: Can we extend activity ACT-001 by 8 hours?
   ```

3. **Expected Behavior:**
   - LLM calls `propose_schedule_change` tool
   - Tool returns proposal (NOT executed)
   - LLM presents proposal with SAFE_MODE warning
   - No actual changes made to P6

**Verification:**
- ✅ Change proposal generated
- ✅ Current vs proposed values shown
- ✅ SAFE_MODE warning displayed
- ✅ Confirmation command provided
- ✅ No actual changes made

**Example Expected Output:**
```
AI: I can propose extending activity ACT-001 by 8 hours. Let me analyze this change.

💡 **Proposed Schedule Change**

**Activity:** Drill Blast Holes - Level 1 (ACT-001)

**Current Values:**
- Planned Duration: 16.0 hours

**Proposed Changes:**
- Planned Duration: 24.0 hours (+8 hours)

**Impact Assessment:**
- ⚠️ This activity is on the critical path (Total Float: 0.0 hours)
- Project completion will be delayed by 8 hours
- 3 downstream activities will be affected

**Rationale:**
User requested 8-hour extension

🔒 **SAFE_MODE is ENABLED**

This change has NOT been applied. To execute this change:
1. Set SAFE_MODE=false in .env file
2. Restart the application
3. Confirm the change

Would you like me to analyze alternative approaches that don't impact the critical path?
```

---

## Verification Checklist

### Schema Patch
- [ ] TotalFloat field added to ACTIVITY_FIELDS
- [ ] ProjectObjectId field added to ACTIVITY_FIELDS
- [ ] Fields fetched from P6 database
- [ ] Values are not all None (if data exists)

### LLM Integration
- [ ] litellm installed successfully
- [ ] LLM client initializes without errors
- [ ] Simple chat works (without tools)
- [ ] Function calling works (with tools)
- [ ] Tool schemas converted correctly

### ReAct Loop
- [ ] System prompt injected
- [ ] Project context loaded
- [ ] LLM calls tools correctly
- [ ] Tools execute and return results
- [ ] Results sent back to LLM
- [ ] LLM generates final response
- [ ] Conversation memory works

### Critical Path Analysis
- [ ] TotalFloat enables critical path identification
- [ ] Critical activities filtered correctly
- [ ] LLM provides appropriate warnings
- [ ] Recommendations are mining-specific

### Relationship Queries
- [ ] ProjectObjectId enables efficient queries
- [ ] Predecessors fetched correctly
- [ ] Successors fetched correctly
- [ ] Relationship types displayed

### SAFE_MODE Protection
- [ ] Change proposals generated (not executed)
- [ ] SAFE_MODE warnings displayed
- [ ] Confirmation commands provided
- [ ] No actual changes made to P6

---

## Known Issues & Limitations

### 1. TotalFloat May Be None
**Issue:** P6 may not have calculated float yet  
**Solution:** Run schedule calculation in P6 before testing

### 2. LLM API Costs
**Issue:** Each query costs money  
**Solution:** Use cheaper models for testing (claude-3-haiku, gpt-3.5-turbo)

### 3. Rate Limits
**Issue:** API providers have rate limits  
**Solution:** Add delays between requests, handle rate limit errors

### 4. Context Window Limits
**Issue:** Large projects may exceed context window  
**Solution:** Implement pagination, summarization, or filtering

### 5. Tool Execution Errors
**Issue:** P6 connection issues may cause tool failures  
**Solution:** Check logs, verify P6 connection, handle errors gracefully

---

## Troubleshooting

### Error: "litellm not installed"
```bash
pip3 install litellm
```

### Error: "LLM_API_KEY not configured"
1. Edit `.env` file
2. Add `LLM_API_KEY=your_key_here`
3. Restart application

### Error: "API key invalid"
1. Verify key is correct
2. Check account has credits
3. Verify provider matches key (anthropic key for anthropic provider)

### Error: "Tool not found"
1. Check tool name in LLM response
2. Verify tool exists in P6Tools
3. Check tool schema format

### Error: "TotalFloat is None"
1. Run schedule calculation in P6
2. Verify P6 API version supports TotalFloat
3. Check field name is exactly "TotalFloat"

### Error: "ProjectObjectId is None"
1. Verify P6 API version supports ProjectObjectId
2. Check field name is exactly "ProjectObjectId"
3. Verify activities are linked to projects

---

## Success Criteria

Phase 6 is considered successful when:

1. ✅ TotalFloat and ProjectObjectId fields are fetched from P6
2. ✅ LLM client initializes and communicates successfully
3. ✅ Function calling works (LLM calls tools)
4. ✅ ReAct loop completes (tool results sent back to LLM)
5. ✅ Critical path activities identified using TotalFloat
6. ✅ Relationship queries work using ProjectObjectId
7. ✅ SAFE_MODE prevents change execution
8. ✅ Conversation memory works across multiple turns
9. ✅ System prompt is injected correctly
10. ✅ Natural language responses are coherent and domain-specific

---

## Next Steps After Testing

Once Phase 6 is verified:

1. **Phase 6.1:** Advanced Analysis Tools
   - Implement `calculate_critical_path()` tool
   - Add `identify_bottlenecks()` tool
   - Add `optimize_schedule()` tool

2. **Phase 6.2:** Change Confirmation Workflow
   - Implement `execute_change()` tool
   - Add confirmation dialog
   - Implement rollback mechanism

3. **Phase 6.3:** Visualization
   - Generate Gantt charts
   - Create network diagrams
   - Add critical path visualization

4. **Phase 6.4:** Multi-Project Support
   - Add portfolio-level tools
   - Implement cross-project analysis
   - Add resource sharing analysis

---

**Testing Status:** 🟡 READY FOR TESTING  
**Implementation Status:** ✅ COMPLETE  
**Documentation Status:** ✅ COMPLETE
