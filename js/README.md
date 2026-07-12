# SAGE JS - Smart Agent Guidance Engine
[![npm](https://img.shields.io/npm/v/psycgod-sage-js)](https://www.npmjs.com/package/psycgod-sage-js)
**97% token compression for AI coding agents - JavaScript/Node.js version**
## Installation
```bash
npm install -g psycgod-sage-js
Also available in Python (with ML V2):

pip install psycgod-sage
JS vs Python
FeatureJSPython
Core compression (97%)YesYes
MCP ServerYesYes
ML V1 (pattern-based)YesYes
ML V2 (neural embeddings)NoYes
4 AgentsYesYes
7 AgentsNoYes
TUI/GUINoYes
MCP RegistryYesNo
Startup~50ms~300ms
Both share the same database.

Usage
sage run -- npm test
sage history
sage explain --failed
sage suggest --failed
sage predict rm -rf node_modules
MCP Tools
sage_run, sage_read_file, sage_write_file, sage_edit_file, sage_grep, sage_glob, sage_tree, sage_get_history, sage_explain_error, sage_suggest_fix, sage_spawn_agent

Links
Python: https://pypi.org/project/psycgod-sage/
Repo: https://github.com/PsYcGoD/sage
Dashboard: https://sage.api.marketingstudios.in/
License
MIT
