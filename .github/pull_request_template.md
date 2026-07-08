## Summary

Explain what changed and why.

## Type of change

- [ ] Docs
- [ ] Bug fix
- [ ] Feature
- [ ] Test
- [ ] Refactor
- [ ] Security/privacy

## Test plan

Commands run:

```bash
python -m compileall -q src/sage
python -m pytest -q
```

## Privacy/security checklist

- [ ] Does not upload raw command text/output.
- [ ] Does not weaken secret redaction.
- [ ] Does not reintroduce fake or inflated metrics.
- [ ] Docs match actual behavior.
