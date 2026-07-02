# SignalDeck

SignalDeck is a local terminal intelligence layer for AI coding assistants.

It runs shell commands, keeps the useful parts of the output, remembers failures
in a local SQLite database, and gives Claude, Codex, or another assistant a
clean explanation of what happened.

## Why This Exists

AI coding tools often run commands that produce huge logs. Huge logs waste
context and make it harder for the assistant to see the real problem.

SignalDeck turns noisy command output into a smaller signal:

```text
command -> output -> important errors -> local memory -> clean explanation
```

## First Commands

Run a command through SignalDeck:

```powershell
signaldeck run -- python --version
```

Run tests in a project:

```powershell
signaldeck run -- python -m unittest
```

Explain the most recent command:

```powershell
signaldeck explain
```

Show recent command history:

```powershell
signaldeck history
```

Create an instruction file for AI assistants:

```powershell
signaldeck init
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

## Vision

SignalDeck is not only a token saver. The goal is to become a local memory and
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
