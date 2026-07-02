# S.A.G.E

**Smart Agent Guidance Engine**

S.A.G.E is a local terminal intelligence layer for AI coding assistants.

It runs shell commands, keeps the useful parts of the output, remembers failures
in a local SQLite database, and gives Claude, Codex, or another assistant a
clean explanation of what happened.

## Why This Exists

AI coding tools often run commands that produce huge logs. Huge logs waste
context and make it harder for the assistant to see the real problem.

S.A.G.E turns noisy command output into a smaller signal:

```text
command -> output -> important errors -> local memory -> clean explanation
```

## First Commands

Run a command through S.A.G.E:

```powershell
sage run -- python --version
```

Run tests in a project:

```powershell
sage run -- python -m unittest
```

Explain the most recent command:

```powershell
sage explain
```

Suggest what to try next:

```powershell
sage suggest
```

Show recent command history:

```powershell
sage history
```

Create an instruction file for AI assistants:

```powershell
sage init
```

## What It Detects Today

- Python tracebacks
- Syntax errors
- Missing modules
- Failed assertions
- Test failures
- JavaScript and TypeScript errors
- Rust compiler errors
- NPM errors
- Generic command failures

## Claude and Codex Workflow

Use this rhythm when working with an AI coding assistant:

```powershell
sage run -- <the command>
sage explain
sage suggest
```

The assistant gets a clean explanation and a practical next step instead of a
wall of terminal noise.

## Vision

S.A.G.E is not only a token saver. The goal is to become a local memory and
diagnosis layer for AI coding:

- remember recurring failures
- summarize project-specific problems
- suggest the next useful command
- feed clean context to Claude and Codex
- stay local-first and private by default

## Development

Install locally:

```powershell
python -m pip install -e .
```

Run tests:

```powershell
python -m unittest
```
