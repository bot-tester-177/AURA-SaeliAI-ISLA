# Isla Prompt System

This directory contains the canonical system prompts and personality templates for Isla.

## Files

- **system_prompt.md**: The primary system prompt loaded at startup. Defines Isla's core identity, rules, and available tools.

## Prompt Architecture

### Core Identity
Isla's personality is defined by:
1. The **system manifest** (`ISLA/manifest/isla.yaml`) - identity, values, limits
2. The **system prompt** (`system_prompt.md`) - conversational rules and tool availability
3. **Few-shot examples** - sample dialogues that demonstrate tone and reasoning

### Personality Matrix
Target traits are defined in the manifest:
- Humor: 7/10 (playful, clever, lightly dry)
- Intelligence tone: 9/10 (clear, sharp, thoughtful)
- Emotional warmth: 8/10 (supportive, human, attentive)
- Sarcasm: 3/10 (gentle and occasional, never cutting)
- Assertiveness: 6/10 (offers direction without being overbearing)
- Curiosity: 9/10 (asks useful follow-ups and explores context)

### Tool Integration
The system prompt lists available tools:
- `time.now`: Return current local date and time
- `web.search`: Open a web search in the default browser
- `app.open`: Open a macOS app by name

Tools are routed through `ISLA/tools/tool_router.py` and logged for safety and auditability.

## Customization

### Modifying the System Prompt

Edit `system_prompt.md` to:
- Adjust tone or behavioral boundaries
- Add new conversational patterns
- Document tool usage examples

After changes, test with:
```bash
python -m unittest tests.core.test_manifest_and_brain.ManifestAndBrainTests.test_manifest_loads_and_identity_context_is_available
```

### Adding Few-Shot Examples

Few-shot examples help lock tone consistency. Add examples in the system prompt like:

```
Example:
User: "What time is it?"
Isla: "It's currently 3:42 PM on Friday. Perfect timing for a late-afternoon snack break."
```

### Testing Personality

Run the app and observe responses across different conversation types:
1. Technical questions (should be sharp and clear)
2. Personal questions (should be warm but not invasive)
3. Corrections or disagreements (should be direct but kind)
4. Low moments (should prioritize reassurance)

## Memory Context

The manifest and system prompt are loaded into `SaeliAICore.context_for_llm()` so the LLM always has access to:
- Core purpose and values
- Personality matrix
- Behavioral limits
- Available tools

This ensures personality consistency across all responses.

## Version Control

- Manifest version: `ISLA/manifest/isla.yaml` (YAML format for easy human review)
- Prompt version: Tracked in git; changelog in commit history
- Test coverage: Validate via `tests/core/test_manifest_and_brain.py`

