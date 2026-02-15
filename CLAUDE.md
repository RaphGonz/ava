# CLAUDE.md — Nexus (AVA) Project

## Project Overview

Nexus (codename AVA) is a hybrid AI companion with two modes:
- **Jarvis mode (Standard):** proactive assistant — planning, reminders, professional tone, sexually neutral.
- **Her mode (Intimate):** emotionally proactive companion with adult roleplay and media generation, activated via a user-defined safe word.

The full specification lives in `CdC.md`.

## Architecture

- **Backend:** Python (FastAPI or Django), cloud-first
- **Desktop client:** Electron
- **Mobile client:** Flutter or React Native
- **Databases:** PostgreSQL (users/billing), vector DB (Pinecone/Milvus) for long-term memory
- **AI pipeline:** orchestrator module that routes inputs to assistant, conversation, or roleplay modules
- **Image generation:** SDXL/Flux pipeline with LoRA for character identity consistency

## Key Concepts

- **Safe word mechanism:** user-defined phrase toggles between Jarvis and Her modes. UI shifts visually on activation. Exit via keyword or inactivity timeout.
- **Router/guardian module:** classifies every input — system commands go to assistant, emotional chat to conversation module, safe word triggers NSFW flag, illegal content is blocked.
- **Long-term memory:** vector DB stores preferences, names, past conversations for continuity across sessions.
- **Reality check:** usage-threshold prompts to reduce emotional dependency risk.

## Safety & Compliance Rules

- Hard content filters: pre-processing blocks disallowed categories before generation, post-processing analyzes generated images.
- Age verification (KYC) required for intimate mode and NSFW media.
- GDPR compliance: explicit opt-in, panic/wipe feature, data portability, retention policy, EU hosting for EU users.
- All media must be clearly labeled as synthetic/AI-generated.
- Security: TLS, encryption at rest, JWT auth, rate limiting, input validation (SQLi/XSS), VPC isolation, IAM, MFA for ops.

## Business Model

Three SaaS tiers:
1. Unlimited chat, standard + intimate (text only)
2. Images, priority access, expanded memory
3. Video beta, high-res generation

## MVP Strategy

Two paths considered:
- **Scenario 1 "Lab":** PWA web chat + memory + image generation for technical validation.
- **Scenario 2 "Fortress":** compliance-first web app with KYC, GDPR, and WhatsApp Business (SFW only).

## Development Guidelines

- Keep Jarvis and Her modes strictly separated in code — no leaking of NSFW behavior into standard mode.
- All user inputs must pass through the router/guardian before reaching any generation module.
- Character identity consistency is critical — always use LoRA-based generation for avatar images.
- Prefer streaming responses (word-by-word) to reduce perceived latency.
- Never store unencrypted sensitive data. Follow GDPR deletion requirements in all data layer code.
- Test content filters on both input and output paths.