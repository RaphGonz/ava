## Requirements Summary (English) — “Nexus” Hybrid AI Companion 

### 1) Product definition and vision

* **Goal:** a multi-platform software agent (desktop + mobile, with messaging channels like WhatsApp/Discord) combining:

  * **“Jarvis” mode (Standard):** proactive assistant (planning, reminders), professional/friendly tone, **sexually neutral**.
  * **“Her” mode (Intimate):** activated by a **user-defined safe word**, emotionally proactive companion, **adult (NSFW) roleplay**, with optional media generation (images; short videos as beta).
* **Core principle:** strict dual-mode separation controlled by the user.

### 2) User journey and UX/UI

**Installation & onboarding**

* “One-click” installation for desktop + mobile app pairing via **QR code**.
* **Conversational calibration** instead of forms: preferred name, voice, visual attraction preferences.
* **Avatar creation:** user describes ideal look or selects archetypes (realistic/stylized/anime), then the system generates a **reference image** validated by the user.
* **Orientation setting:** hetero/gay/bi to adapt language and image generation.
* **Safe word configuration:** custom phrase to enter intimate mode.

**Safe word mechanism**

* On detection, UI shifts subtly (e.g., color/ambience), and routing switches from assistant behavior to roleplay/adult mode.
* Exit via another keyword or inactivity timeout.

**Interaction features**

* **Long-term memory** (preferences, names, past conversations) to maintain continuity.
* **Streaming text** (word-by-word typing effect) to reduce perceived latency.
* **“Reality check”** prompts if usage exceeds thresholds to reduce dependency risk.

### 3) Multimedia capabilities

* **Text:** persistent memory and continuity.
* **Images (“selfies”):**

  * Triggered by user request or system initiative.
  * **Consistency requirement:** face/body remain consistent across generations.
* **Video (nice-to-have / beta):**

  * 3–5 second loops (GIF/MP4), simple actions (smile, wink, kiss) to control cost and artifacts.

### 4) Technical architecture (scalability & maintainability)

**Modular, cloud-first**

* “Brain” runs in the cloud; clients (desktop/mobile/web) are interfaces.

**Suggested stack**

* **Backend:** Python (FastAPI or Django).
* **Desktop:** Electron.
* **Mobile:** Flutter or React Native.
* **Datastores:** PostgreSQL for users/billing; **vector DB** (e.g., Pinecone/Milvus) for memory.

**AI pipeline (“orchestrator”)**

* **Router/guardian module:** classifies input and dispatches:

  * system commands → assistant module
  * emotional chat → conversation module
  * safe word detection → toggles NSFW flag / roleplay mode
  * illegal content detection → block
* **LLM layer:** robust hosted models (including open-source options), with roleplay tuning implied.
* **Image generation:** SDXL/Flux-style pipeline with **LoRA** to lock character identity.

### 5) Safety, compliance, and security

**Hard filters**

* **Pre-processing:** block disallowed content categories before any generation step.
* **Post-processing:** analyze generated images as an additional safety layer.

**Legal / terms**

* Explicitly state the user is interacting with AI; disclaim responsibility for advice.
* Prohibit jailbreak attempts and misuse.
* Clarify all media is synthetic.

**Age gating**

* Access to intimate mode and NSFW media restricted to adults via robust **age verification (KYC)**.

**GDPR (sensitive data)**

* Explicit, granular opt-in for sensitive data processing.
* **“Panic / wipe”**: immediate deletion of account data (SQL + vector DB).
* Retention policy for inactive accounts.
* Data portability (download archive).
* Host infrastructure in GDPR-compatible jurisdictions (prefer EU for EU users).

**Security measures**

* TLS in transit; encryption at rest for databases.
* Strong auth (e.g., JWT), rate limiting/throttling.
* Input validation against SQLi/XSS.
* Network isolation (VPC); strict IAM; MFA for ops.

### 6) Business model and maintenance

**SaaS tiers**

* Tier 1: unlimited chat, standard + intimate (text only).
* Tier 2: images, priority access, expanded memory.
* Tier 3: video beta, high-res generation.

**Maintenance**

* Cloud architecture enables model updates without client reinstall; client updates mainly for UI changes.

### 7) Risks and mitigations

* **Hallucinations:** use retrieval/memory checks (RAG) to ground outputs.
* **Visual inconsistency:** LoRA per-character.
* **Latency:** dedicated GPUs + streamed text.
* **Emotional dependency:** reality-check prompts based on usage patterns.

### 8) MVP options (recommended path in the document)

**MVP Scenario 1 — “Lab” Web App (technical validation)**

* PWA web chat + memory (vector DB) + image generation to validate **identity consistency**.
* Pros: avoids app-store NSFW constraints; direct billing; platform ownership.
* Cons: acquisition friction; immediate GDPR obligations.

**MVP Scenario 2 — “Fortress” (compliance-first)**

* Web app plus heavy compliance/security and integrations.
* WhatsApp Business for **SFW assistant notifications only** (intimate mode excluded).
* Adds KYC + panic wipe + GDPR consent from day 1.
* Pros: reduces legal/payment risk; premium trust positioning.
* Cons: higher build cost; KYC friction hurts conversion.

### 9) Marketing approach tied to MVP (SFW-first virality)

* NSFW content cannot be shown on mainstream platforms; marketing must rely on **suggestion, humor, contrast, and high-quality SFW visuals**.
* Viral features proposed:

  1. **Shareable SFW avatar portrait** (“Instagrammable”) + share card.
  2. **Jarvis vs Her contrast meme generator** (kept SFW).
  3. **Waitlist / referral gating** to create exclusivity (“velvet rope”).

**Public brand posture options presented**

* A) Chic insinuation (luxury/perfume-style).
* B) Humor/self-deprecation (memes about the duality).
* C) Provocative “anti-censorship tech” stance.
