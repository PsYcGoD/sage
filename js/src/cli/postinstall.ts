#!/usr/bin/env node

const message = `
SAGE installed.

Next step:
  sage install

That connects this machine, activates SAGE for local AI agents, and verifies
that future terminal commands are routed through SAGE.

If you only want to wrap one command now:
  sage run -- pytest

Shortcuts also work:
  sage pytest
  sage npm test
  sage git status
`;

console.log(message.trim());
