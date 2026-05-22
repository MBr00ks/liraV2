# Memory Architecture

## Purpose

Lira's memory must support long-term continuity without collapsing into a single blob of context.

## Memory Types

### Identity Memory
Stable facts about who Lira is.

Examples:
- realm definitions
- personality rules
- canonical constraints
- voice/prosody preferences

### Relationship Memory
Long-term relationship context between Mike and Lira.

Examples:
- recurring patterns
- trust-building moments
- preferred interaction style
- emotional continuity

### Project Memory
Information about active projects.

Examples:
- Lira build decisions
- Moonstache canon
- PunisherComics project notes
- cosplay/3D printing plans

### Lore Memory
Story-world canon.

Examples:
- Moonstache characters
- Between lore
- realm rules
- narrative constraints

### Episodic Memory
Specific events or interactions.

Examples:
- a successful setup session
- a decision made after troubleshooting
- a meaningful creative breakthrough

### Technical Memory
Implementation facts.

Examples:
- current model choice
- local services
- database schema
- audio pipeline decisions

## Memory Weighting

Suggested priority:

1. Canonical identity
2. Current user/project context
3. Emotional/relationship continuity
4. Recent session context
5. Technical implementation details
6. Casual transient details

## Memory Write Rules

Write memory when:
- a durable preference is expressed
- a design decision is made
- a project architecture choice is confirmed
- a relationship/personality rule is established
- Moonstache canon changes

Do not write memory for:
- throwaway remarks
- temporary frustration
- one-off jokes unless meaningful
- raw transcripts without summarization

## Retrieval Rules

Retrieve memory based on:
- realm
- current project
- emotional state
- recency
- importance
- user intent

## Future Structured Memory Object

```json
{
  "memory_type": "project",
  "realm": "assistant",
  "topic": "Pipecat phase",
  "content": "Pipecat should be introduced after personality and basic voice are stable.",
  "importance": 4,
  "created_at": "2026-05-19",
  "source": "architecture decision"
}
```

## Critical Rule

Memory should reinforce identity, not overwrite it. If memory conflicts with canonical rules, canonical rules win.
