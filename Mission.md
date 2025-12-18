# 🛡️ Mission Sita

**Reasoning-Driven Web Exploitability Validation Platform**

> Existing tools detect vulnerabilities.
> **Mission Sita reasons about application behavior to validate real exploit paths**, especially authorization and logic flaws.

---

## 🚀 What is Mission Sita?

Mission Sita is an **internal-first, AI-driven web security platform** that behaves like a **junior pentester guided by senior-level reasoning**.

Instead of blindly scanning for every possible vulnerability, Mission Sita:

1. Understands how an application behaves
2. Builds **attack hypotheses**
3. Validates **real exploitability**
4. Produces **evidence-backed pentest reports**

It focuses on **what actually matters**, not alert noise.

---

## ❌ The Problem We Solve

### Today’s AppSec reality:

* DAST scanners → noisy, shallow, auth-blind
* SAST tools → pre-deployment only
* Manual pentests → expensive & infrequent
* Junior teams → tool-heavy, reasoning-light

Security teams don’t lack tools.
They lack **contextual reasoning**.

---

## ✅ What Mission Sita Solves

* Reduces **false positives**
* Validates **authorization & logic flaws**
* Converts scanner chaos into **clear exploit evidence**
* Helps **junior teams think like senior pentesters**
* Runs **inside company infrastructure** (privacy-first)

---

## 🧠 Core Philosophy (Why We’re Different)

Most tools do this:

```
Input → Scan → Alerts → Dashboard
```

Mission Sita does this:

```
Input → Reason → Hypothesis → Validate → Evidence → Report
```

👉 We **own the reasoning layer** everyone else ignores.

---

## 🏗️ High-Level Architecture

Mission Sita is a **multi-agent system**, where each agent has a strict role.

No agent does everything.
No hallucination-prone design.

```
Target
  ↓
Recon & Context Agent (Facts)
  ↓
Attack Surface Reasoning Agent (Hypotheses)
  ↓
Knowledge Grounding Agent (RAG)
  ↓
Exploit Validation Agent (Controlled Testing)
  ↓
Evidence & Reporting Agent
```

---

# 🧠 Agent-by-Agent Breakdown

---

## 🧠 Agent 1: Recon & Context Agent (NO AI)

**Purpose:**
Collect *facts*, not conclusions.

> “Here is reality.”

### Responsibilities

* Discover endpoints & parameters
* Identify auth mechanisms
* Detect object identifiers
* Observe response behavior
* Identify tech stack

### Inputs

* Target URL
* Optional white-box hints (roles, API docs)

### Outputs (Structured JSON)

```json
{
  "endpoints": ["/api/orders/{id}"],
  "parameters": ["order_id", "user_id"],
  "auth": "JWT",
  "object_identifiers": ["order_id"],
  "tech_stack": ["Node.js", "Express"],
  "response_patterns": {
    "401": "unauthorized",
    "200": "valid access"
  }
}
```

### Tools Used

* `httpx`
* `katana`
* `ffuf`
* `gau`
* `nuclei` (INFO templates only)
* `nmap` (very limited, optional)

⚠️ **No LLM. No attack suggestions.**

---

## 🧠 Agent 2: Attack Surface Reasoning Agent (LLM CORE)

**Purpose:**
Convert recon data into **attack hypotheses**.

This is where scanners fail — and you win.

### Responsibilities

* Identify ownership boundaries
* Reason about roles & access
* Predict where logic may break

### Inputs

* Recon agent output

### Outputs

```json
{
  "hypothesis": "User-owned resources accessed via predictable IDs",
  "attack_class": "IDOR",
  "confidence": "high",
  "required_evidence": "cross-user access to resource"
}
```

### Key Capabilities

* Threat modeling
* Auth & logic-first reasoning
* Context-aware decisions

🚫 No payloads
🚫 No tools
🚫 No execution

---

## 🧠 Agent 3: Knowledge Grounding Agent (RAG)

**Purpose:**
Answer one question:

> “How do real pentesters validate this hypothesis?”

### Responsibilities

* Pull **testing methodology**
* Extract **relevant payload patterns**
* Provide **step-by-step validation logic**

### RAG Sources

* Swissky’s `PayloadsAllTheThings`
* OWASP ASVS
* Bug bounty writeups
* Real-world pentest playbooks

⚠️ **RAG feeds strategy, not payload dumps.**

### Output

```json
{
  "methodology": "Test object ownership by swapping IDs",
  "validation_steps": [
    "Authenticate as User A",
    "Access resource ID belonging to User B",
    "Compare response"
  ]
}
```

---

## 🧠 Agent 4: Exploit Validation Agent (Controlled Execution)

**Purpose:**
Validate — not exploit.

### Responsibilities

* Execute **minimal, safe tests**
* Confirm or reject hypotheses
* Stop immediately after proof

### Rules

* ❌ No brute force
* ❌ No destructive actions
* ❌ No mass payloads
* ✅ Read-only first
* ✅ Rate-limited
* ✅ Evidence-focused

### Example Action

```
GET /api/orders/102
Authenticated as User A
→ Response contains User B’s data
```

That’s validation. Not chaos.

---

## 🧠 Agent 5: Evidence & Reporting Agent

**Purpose:**
Turn findings into something companies actually buy.

### Responsibilities

* Explain what was tested
* Show why it mattered
* Present proof
* Suggest fixes

### Output Sections

* Executive summary
* Attack scenario
* Evidence (requests & responses)
* Business impact
* Remediation guidance

This agent alone beats most scanners.

---

# 🎯 MVP Scope (Focused & Realistic)

### Included

* ✅ IDOR (API-focused)
* ✅ Auth misconfigurations
* ✅ CSRF (state-changing endpoints)
* ✅ Basic reflected XSS
* ✅ Object-level authorization flaws

### Excluded (for MVP)

* ❌ SQLi
* ❌ RCE
* ❌ Zero-days
* ❌ OAuth bypass chains

---

# 🧰 Tech Stack

### Core

* Python
* FastAPI
* LangGraph (agent orchestration)
* Redis (agent state)
* SQLite / PostgreSQL

### AI

* GPT-4 / Claude-class model (reasoning)
* Smaller model for summarization

### RAG

* FAISS / Chroma
* Structured chunking (attack → context → method)

---

# 🏢 Deployment Model

### MVP Focus

* **Internal tool**
* Runs inside company infrastructure
* No data exfiltration
* No SaaS dependency

### Future

* Optional SaaS wrapper
* Bug bounty mode
* CI/CD hooks (later)

---

# 🆚 Competitor Comparison

| Tool             | What They Do           | What We Do                   |
| ---------------- | ---------------------- | ---------------------------- |
| Burp Suite       | Payload-driven testing | Hypothesis-driven validation |
| DAST Scanners    | Pattern matching       | Contextual reasoning         |
| SAST Tools       | Pre-deployment         | Runtime behavior             |
| AI Pentest Tools | Scanner + LLM          | Reasoning + validation       |

---

# 🏆 Why Mission Sita Can Win Imagine Cup

* ✔ Real-world problem
* ✔ Clear differentiation
* ✔ Strong AI reasoning use
* ✔ Security + AI impact
* ✔ Feasible MVP
* ✔ Enterprise relevance

Judges don’t want “AI that scans”.
They want **AI that thinks**.

---

## 🔑 One-Line Pitch (Memorize This)

> “Mission Sita validates real web exploit paths by reasoning about application behavior, reducing security noise and helping teams focus on what is actually exploitable.”

---

