# Isla Implementation Plan

## Starting Point

The first goal is not to build every subsystem. The first goal is to lock the project shape so later work stays consistent:

1. Define the system manifest.
2. Define the personality matrix.
3. Define the memory hierarchy.
4. Create the initial repository structure.
5. Add a minimal local prototype loop.

## Phase 0 - Project Setup

### Deliverables

- A versioned manifest for Isla's identity and rules.
- A stable folder structure for brain, memory, voice, tools, avatar, ar, hardware, prompts, and docs.
- A small set of sample dialogues used to test tone.
- A minimal local stack that can be run without cloud services.

### Exit Criteria

- The manifest can be loaded by the project.
- The personality settings are visible and editable.
- The memory layers are named and separated.
- The repository layout matches the intended architecture.

## Phase 1 - Identity First

### Tasks

1. Write the core purpose statement.
2. Define tone limits and behavioral boundaries.
3. Set the personality sliders.
4. Add example prompts that preserve voice consistency.
5. Test the model against short dialogue samples.

### Exit Criteria

- Isla sounds like Isla in repeated test runs.
- Personality drift is detectable and easy to adjust.
- The system prompt or manifest is the single source of truth for identity.

## Phase 2 - Voice Prototype

### Tasks

1. Choose the first local STT engine.
2. Choose the first local TTS engine.
3. Add a simple voice loop.
4. Test wake, respond, and speak latency.
5. Record a small set of voice samples if cloning is planned.

### Exit Criteria

- Speech can be captured locally.
- A response can be generated and spoken back.
- The pipeline is simple enough to debug end to end.

## Phase 3 - Memory Prototype

### Tasks

1. Add structured fact storage.
2. Add short-term conversation context.
3. Add semantic retrieval for older context.
4. Define retention rules by memory type.
5. Add a manual flag for important memories.

### Exit Criteria

- Facts persist across sessions.
- Recent context is available during a session.
- Older memories can be recalled by semantic search.

## Phase 4 - Tooling and Brain

### Tasks

1. Add tool routing.
2. Separate reasoning from action execution.
3. Define safe boundaries for tool use.
4. Add logging for decisions and calls.
5. Prepare the system for later model upgrades.

### Exit Criteria

- The system can call tools in a predictable way.
- Actions are logged and reviewable.
- The project can evolve without rewriting the core architecture.

## Phase 5 - Visual and Presence Layers

### Tasks

1. Create concept art or avatar references.
2. Choose the first visual representation format.
3. Define motion and expression requirements.
4. Prototype AR or spatial presence separately from the core assistant.
5. Keep hardware experiments isolated from the main software loop.

### Exit Criteria

- The visual layer can be changed without breaking the core assistant.
- AR and hardware work remain optional add-ons.

## Immediate Next Action

Create the repository skeleton and the manifest files first. That gives every later phase a stable surface to build against.
