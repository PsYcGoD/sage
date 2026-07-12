#!/usr/bin/env node
// npm/npx SAGE launcher.
//
// The Python package `psycgod-sage` is the canonical SAGE implementation.
// This npm package exists for Node users who prefer:
//   npx -y psycgod-sage run -- <command>
//
// To keep PyPI and npm behavior identical, every CLI invocation is forwarded
// to `python -m sage` after ensuring the Python core is installed.
import { runPythonSage } from '../python/bridge.js';

const args = process.argv.slice(2);
const exitCode = runPythonSage(args);
process.exit(exitCode);
