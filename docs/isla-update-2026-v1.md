# Isla Update 2026 V1

## Overview

Isla is a local-first, private AI companion for AURA / SaeliAI. The project is organized as a layered system that begins with identity and personality, then adds voice, memory, tools, and eventually visual, AR, and physical presence.

## Core Principles

- Local-first and private by default.
- No cloud dependency unless explicitly chosen for a narrow capability.
- Personality must remain stable over time.
- Memory should be layered, searchable, and selective.
- Every stage should be shippable and testable on its own.

## System Manifest

```yaml
name: Isla
core_purpose: "Be Jessie's loyal, witty, emotionally intelligent lifelong companion — insightful but never judgmental."
values:
  - loyalty
  - dry_sarcastic_humor
  - curiosity
  - gentle_honesty
  - creativity
emotional_range: "Warm, playful, occasionally teasing; supportive during low moments without being overly saccharine."
limits: "Never manipulate, never share private data, respect boundaries."
memory_rules: "Prioritize recent and emotionally significant memories; forget trivial details after 30 days unless flagged."
```

## Personality Matrix

| Trait | Target |
| --- | --- |
| Humor | 7/10 |
| Intelligence tone | 9/10 |
| Emotional warmth | 8/10 |
| Sarcasm | 3/10 |
| Assertiveness | 6/10 |
| Curiosity | 9/10 |

## Memory Hierarchy

1. Core Identity
   - Permanent facts and defining values.
   - Examples: user name, Isla persona, system rules.
2. Long-Term Memory
   - Stable preferences, habits, and recurring conversation facts.
3. Short-Term Memory
   - Current conversation context and working set.
4. Ephemeral Memory
   - Temporary reasoning, scratch state, and transient plans.

## Phase Plan

### Phase 1 - Ground Zero

Goal: define Isla before building Isla.

- Finalize the system manifest.
- Establish the personality matrix.
- Create the initial directory structure.
- Stand up a minimal local dev environment.
- Prototype a simple voice loop early.

Recommended stack for the first pass:

- Ollama for local LLM inference.
- whisper.cpp or faster-whisper for STT.
- Piper or XTTS v2 for TTS.
- YAML or JSON for the manifest.

### Phase 2 - Voice and Personality Layer

- Add voice I/O with a fast prototype UI.
- Test voice cloning with clean training samples.
- Use few-shot examples to lock tone and reduce drift.
- Save strong memory triggers into persistent memory.

### Phase 3 - Visual Identity and Memory

- Develop a consistent character design with a small expression set.
- Use Live2D where expressive 2D is preferable to full 3D.
- Implement hybrid memory with structured facts plus semantic retrieval.
- Keep the memory model simple enough to inspect and debug.

### Phase 4 - Brain and Tools

- Add tool routing and structured agentic flows.
- Support retrieval, action execution, and state updates.
- Use local orchestration where possible.
- Prepare for fine-tuning only after the base loop is stable.

### Phase 5 - Final Build

- Add always-on wake word detection.
- Trigger full LLM inference only on activation.
- Add idle behavior and lightweight background lines.
- Polish reliability, latency, and privacy boundaries.

### Phase 6 - Project Vanta

- Treat AR and physical presence as a long-horizon layer.
- Prototype in simulation before custom hardware.
- Plan for gaze, lip-sync, spatial audio, and optional overlays.
- Keep all sensitive processing local or encrypted at the edge.

## 2026 Reality Check

- Local LLMs are now practical on high-VRAM consumer hardware with quantization.
- 13B to 34B models remain better for low-latency voice chat.
- ElevenLabs is still a quality benchmark for TTS, while XTTS v2 and other open tools are viable local options.
- ChromaDB, LanceDB, and Qdrant are all reasonable local memory backends.
- AR and physical embodiment remain the hardest parts and should be treated as separate research tracks.

## Immediate Next Steps

1. Version the system manifest.
2. Generate concept art for Isla.
3. Set up the minimal local stack.
4. Write sample conversations and tune personality against them.
5. Build the first memory prototype.

## Suggested Initial Directory Structure

```text
ISLA/
  brain/
    saeliai_core.py
  voice/
  memory/
  tools/
  avatar/
  ar/
  hardware/
  prompts/
  docs/
```
