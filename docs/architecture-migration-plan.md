# Architecture Deconstruction & Migration Plan
## Codex Vitae (GCP) → Darwinian Agent Engine (AWS)

---

## Legacy System Flow (GCP)

```
User Chat → Specialist Agent (Cloud Run)
              ↓ (calls LLM API, responds to user)
              ↓ (sends feedback to Orchestrator)
           Orchestrator (Python Script)
              ↓ (deploys Specialist on request)
              ↓ (receives feedback from Specialist)
              ↓ (passes feedback + genome to Feedback Agent)
           Feedback Agent (Cloud Run)
              ↓ (analyzes feedback + genome)
              ↓ (decides what to update in genome)
              ↓ (sends suggestion back to Orchestrator)
           Orchestrator
              ↓ (if auto_mutation=ON: apply fix to genome, deploy new version)
              ↓ (if auto_mutation=OFF: store suggestion in database)
```

---

## Target System Flow (AWS)

```
User Chat → API Gateway → Proxy Agent (Lambda)
                            ↓ (calls LLM API via Bedrock)
                            ↓ (stores chat in DynamoDB)
                            ↓ (triggers Critic Agent)
                            ↓ (responds to user)
                         Critic Agent (Lambda)
                            ↓ (checks chat for errors/wrong responses)
                            ↓ (if error found: triggers Step Function)
                         Step Function (evolution_loop.asl.json)
                            ↓ Mutator Agent (uses DSPy for prompt generation)
                            ↓ Judge Agent (validates mutation)
                            ↓ Supervisor Agent (applies/retries)

User Feedback → API Gateway → Feedback Agent (Lambda)
                                ↓ (creates suggestion ticket)
                                ↓ (stores in DynamoDB as ticket)
```

---

## Migration Strategy Table

| Legacy Component (GCP) | Migration Type | Deconstruction Strategy | Target AWS Component(s) | Q Developer Task |
|------------------------|----------------|------------------------|-------------------------|------------------|
| **Specialist Agent (Cloud Run)** | **TRANSFERABLE** | **Port Core Logic** | Proxy Agent (Lambda) | Port LLM API call logic from Specialist to Proxy. Replace HTTP server with Lambda handler. Add DynamoDB chat storage. Add EventBridge event emission to trigger Critic. Convert Vertex AI calls to Bedrock. |
| **Specialist - Chat Handling** | **TRANSFERABLE** | **Direct Port** | Proxy Agent Lambda Handler | Extract chat processing function. Adapt input/output format for API Gateway. Maintain LLM prompt engineering logic. Add CloudWatch logging. |
| **Specialist - LLM Integration** | **TRANSFERABLE** | **API Swap** | Proxy Agent + Bedrock | Replace GCP Vertex AI SDK with AWS Bedrock SDK. Port model configuration (temperature, max_tokens). Maintain prompt templates. Handle streaming responses if needed. |
| **Feedback Agent (Cloud Run)** | **TRANSFERABLE** | **Logic Port + Storage Swap** | Feedback Agent (Lambda) | Port genome analysis logic from GCP Feedback Agent. Replace "send to Orchestrator" with "store ticket in DynamoDB". Remove deployment logic (now handled by Step Functions). Keep suggestion generation algorithm. |
| **Feedback Agent - Genome Analysis** | **TRANSFERABLE** | **Core Logic Port** | Feedback Agent Lambda | Port the "decide what to update in genome" logic. Adapt input format (feedback + genome). Output suggestion as DynamoDB ticket item. Remove return-to-Orchestrator callback. |
| **Orchestrator (Python Script)** | **NOT TRANSFERABLE** | **Discard & Rebuild** | EventBridge + Step Functions + Critic Agent | **DO NOT PORT**. Orchestrator logic is replaced by AWS-native services. Routing → EventBridge rules. Deployment → Step Functions. Auto-mutation decision → Critic Agent. State management → DynamoDB. |
| **Orchestrator - Deployment Logic** | **BUILD FROM SCRATCH** | **Rebuild as Workflow** | Step Functions (evolution_loop.asl.json) | Manually code ASL state machine. Define Mutator → Judge → Supervisor flow. Implement retry logic in ASL. Add conditional branching for auto_mutation flag. |
| **Orchestrator - Routing Logic** | **BUILD FROM SCRATCH** | **Rebuild as Event Rules** | EventBridge Event Bus | Manually create event patterns. Define rules: `chat.completed` → Critic, `feedback.received` → Feedback Agent, `mutation.required` → Step Function. No code to port. |
| **Orchestrator - Auto-Mutation Decision** | **BUILD FROM SCRATCH** | **Rebuild as Critic Logic** | Critic Agent (Lambda) | Manually code error detection logic. Decide when to trigger Step Function. Replace "if auto_mutation=ON" with Critic's decision logic. Store auto_mutation flag in DynamoDB config. |
| **Mutator Agent** | **BUILD FROM SCRATCH** | **New Component** | Mutator Agent (Lambda) + DSPy | Manually code DSPy integration for prompt generation. Receive genome + suggestion from Step Function. Generate mutation using DSPy. Pass to Judge Agent. No legacy equivalent. |
| **Judge Agent** | **BUILD FROM SCRATCH** | **New Component** | Judge Agent (Lambda) | Manually code validation logic. Evaluate mutation quality. Decide: approve, reject, or retry. No legacy equivalent. |
| **Supervisor Agent** | **BUILD FROM SCRATCH** | **New Component** | Supervisor Agent (Lambda) | Manually code genome application logic. Apply approved mutations to genome. Deploy new agent version (replace Orchestrator deployment). Store version history in DynamoDB. |
| **API Gateway** | **BUILD FROM SCRATCH** | **New Infrastructure** | API Gateway REST/HTTP API | Manually configure routes: `/chat` → Proxy, `/feedback` → Feedback Agent. Set up Lambda integrations. Configure CORS, authentication. No legacy equivalent. |
| **DynamoDB Tables** | **BUILD FROM SCRATCH** | **New Storage Layer** | DynamoDB (chats, tickets, genomes, config) | Manually design table schemas. Create indexes for queries. Replace Cloud SQL/Firestore. Define partition/sort keys. |

---

## Gap Analysis: Why We're Abandoning the Orchestrator

### What's Actually Transferable

**ONLY 2 COMPONENTS CAN BE PORTED:**

1. **Specialist Agent → Proxy Agent**
   - ✅ LLM API call logic
   - ✅ Chat processing logic
   - ✅ Prompt engineering
   - ❌ Deployment logic (moved to Supervisor)
   - ❌ Feedback sending (replaced by EventBridge)

2. **Feedback Agent → Feedback Agent (Lambda)**
   - ✅ Genome analysis logic ("decide what to update")
   - ✅ Suggestion generation algorithm
   - ❌ Return-to-Orchestrator callback (replaced by DynamoDB ticket storage)
   - ❌ Direct genome mutation (now handled by Mutator → Judge → Supervisor)

**EVERYTHING ELSE IS NEW CODE:**

### Orchestrator Responsibilities → AWS Replacements

| Orchestrator Function | Legacy Implementation | AWS Replacement | Migration Type |
|----------------------|----------------------|-----------------|----------------|
| **Deploy Specialist on Request** | Python script calls Cloud Run API | Supervisor Agent applies genome + deploys | **BUILD FROM SCRATCH** |
| **Receive Feedback from Specialist** | HTTP callback to Orchestrator | Proxy emits event → EventBridge routes | **BUILD FROM SCRATCH** |
| **Pass Feedback to Feedback Agent** | Direct function call | EventBridge rule triggers Feedback Lambda | **BUILD FROM SCRATCH** |
| **Receive Suggestion from Feedback Agent** | Return value from function | Feedback Agent writes ticket to DynamoDB | **BUILD FROM SCRATCH** |
| **Auto-Mutation Decision** | `if auto_mutation == True:` | Critic Agent decides if error warrants mutation | **BUILD FROM SCRATCH** |
| **Apply Fix to Genome** | Orchestrator modifies genome dict | Mutator (DSPy) → Judge → Supervisor pipeline | **BUILD FROM SCRATCH** |
| **Deploy New Version** | Orchestrator calls Cloud Run deploy | Supervisor Agent deploys via AWS APIs | **BUILD FROM SCRATCH** |
| **Store Suggestion in Database** | Orchestrator writes to Cloud SQL | Feedback Agent writes ticket to DynamoDB | **BUILD FROM SCRATCH** |

### Why the Orchestrator Cannot Be Ported

The Orchestrator is fundamentally incompatible with AWS event-driven architecture:

1. **Synchronous Blocking**: Orchestrator waits for Feedback Agent response → AWS uses async events
2. **Centralized State**: Orchestrator holds deployment state in memory → AWS uses DynamoDB + Step Functions
3. **Direct Function Calls**: Orchestrator calls agents directly → AWS uses EventBridge routing
4. **Monolithic Logic**: Routing + deployment + mutation decision in one script → AWS splits into Critic, Mutator, Judge, Supervisor

### The New Components (No Legacy Equivalent)

| Component | Purpose | Why It Didn't Exist in GCP |
|-----------|---------|---------------------------|
| **Critic Agent** | Decides if chat response has errors → triggers mutation | Orchestrator made this decision implicitly |
| **Mutator Agent** | Uses DSPy to generate genome mutations | Feedback Agent suggested fixes, but didn't use DSPy |
| **Judge Agent** | Validates mutation quality before applying | No validation in legacy system (auto-applied) |
| **Supervisor Agent** | Applies genome changes + deploys new version | Orchestrator did this inline |
| **EventBridge** | Routes events between agents | Orchestrator routed via direct calls |
| **Step Functions** | Orchestrates Mutator → Judge → Supervisor flow | Orchestrator did this sequentially in Python |

### Auto-Mutation Logic Migration

**Legacy (GCP):**
```python
# In Orchestrator
suggestion = feedback_agent.analyze(feedback, genome)
if auto_mutation:
    genome = apply_fix(genome, suggestion)
    deploy_new_version(genome)
else:
    database.store_suggestion(suggestion)
```

**Target (AWS):**
```
Proxy Agent → emits chat.completed event
   ↓
Critic Agent → checks for errors
   ↓ (if error found)
Step Function starts:
   ↓
Mutator Agent → generates mutation using DSPy
   ↓
Judge Agent → validates mutation
   ↓
Supervisor Agent → applies to genome + deploys
   
(If auto_mutation=OFF, Critic doesn't trigger Step Function)
```

**Key Difference**: The "auto-mutation decision" moves from Orchestrator to Critic Agent. The "apply fix" logic moves from Orchestrator to the Mutator → Judge → Supervisor pipeline.

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2) - **BUILD FROM SCRATCH**
- Deploy API Gateway with `/chat` and `/feedback` routes
- Create DynamoDB tables: `chats`, `tickets`, `genomes`, `config`
- Deploy EventBridge event bus
- Define event schemas: `chat.completed`, `feedback.received`, `mutation.required`
- Set up CloudWatch Logs and X-Ray tracing

### Phase 2: Port Existing Agents (Week 3-4) - **TRANSFERABLE CODE**
- **Port Specialist → Proxy Agent**:
  - Extract LLM call logic from GCP Specialist
  - Replace Vertex AI with Bedrock
  - Add DynamoDB chat storage
  - Add EventBridge event emission
  - Remove deployment logic
- **Port Feedback Agent**:
  - Extract genome analysis logic from GCP Feedback Agent
  - Replace "return to Orchestrator" with DynamoDB ticket write
  - Keep suggestion generation algorithm
  - Remove direct mutation logic

### Phase 3: Build New Components (Week 5-7) - **BUILD FROM SCRATCH**
- **Critic Agent**: Code error detection logic, decide when to trigger Step Function
- **Mutator Agent**: Integrate DSPy, generate genome mutations
- **Judge Agent**: Code validation logic for mutations
- **Supervisor Agent**: Code genome application + deployment logic (port from Orchestrator's deploy function)

### Phase 4: Workflow Orchestration (Week 8-9) - **BUILD FROM SCRATCH**
- Build Step Functions state machine (evolution_loop.asl.json)
- Define Mutator → Judge → Supervisor flow in ASL
- Add retry/error handling in Step Functions
- Create EventBridge rules:
  - `chat.completed` → Critic Agent
  - `feedback.received` → Feedback Agent
  - `mutation.required` → Step Function

### Phase 5: Orchestrator Retirement (Week 10)
- Run parallel systems (GCP + AWS) with traffic split
- Validate event flows match Orchestrator behavior
- **Decommission Orchestrator** (no code to port, just shut down)
- Archive GCP resources

---

## Code Reuse Summary

### Transferable Code (Port from GCP)
- **Specialist Agent → Proxy Agent**: ~60-70% of code reusable
  - LLM API call logic ✅
  - Chat processing ✅
  - Prompt templates ✅
  - Response formatting ✅
  
- **Feedback Agent → Feedback Agent**: ~40-50% of code reusable
  - Genome analysis algorithm ✅
  - Suggestion generation ✅
  - Feedback parsing ✅

### Non-Transferable (Build from Scratch)
- **Orchestrator**: 0% reusable (discard entirely)
- **Critic Agent**: 100% new code
- **Mutator Agent**: 100% new code (DSPy integration)
- **Judge Agent**: 100% new code
- **Supervisor Agent**: ~20% reusable (port deployment logic from Orchestrator)
- **EventBridge Rules**: 100% new configuration
- **Step Functions**: 100% new ASL definition
- **API Gateway**: 100% new infrastructure
- **DynamoDB**: 100% new schema design

### Estimated Code Distribution
- **Port from GCP**: 30%
- **Build from Scratch**: 70%

---

## Success Metrics

| Metric | Legacy (GCP) | Target (AWS) |
|--------|-------------|--------------|
| **Components to Port** | 2 agents (Specialist, Feedback) | 2 agents (Proxy, Feedback) |
| **Components to Build** | 0 | 6 (Critic, Mutator, Judge, Supervisor, EventBridge, Step Functions) |
| **Orchestrator Migration** | N/A | Discard (0% code reuse) |
| **End-to-End Latency** | ~5-10s (sequential) | ~2-4s (parallel) |
| **Agent Coupling** | High (Orchestrator-centric) | None (event-driven) |
| **Failure Recovery** | Manual restart | Automatic (Step Functions retry) |
| **Observability** | Log parsing | Visual workflow + X-Ray traces |
| **Cost per Request** | $0.05 (always-on Cloud Run) | $0.01 (Lambda pay-per-use) |

---

## Conclusion

This is **30% migration, 70% new development**. Only the Specialist and Feedback Agent logic can be ported. The Orchestrator must be discarded and its responsibilities distributed across EventBridge, Step Functions, Critic, Mutator, Judge, and Supervisor.

**Critical Insight**: The Orchestrator is not "migrated" - it's **deconstructed**. Its routing becomes EventBridge rules. Its deployment logic becomes the Supervisor Agent. Its auto-mutation decision becomes the Critic Agent. Its workflow state becomes Step Functions.

**Next Step**: Begin Phase 1 by building the AWS foundation (API Gateway, DynamoDB, EventBridge), then port the Specialist and Feedback Agent logic in Phase 2.
