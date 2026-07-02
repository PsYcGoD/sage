# Human Touch Checklist

Use this checklist before publishing S.A.G.E or any other project. It is meant to make the project feel reviewed, owned, tested, and maintained by a real human maintainer.

## 1. Product Clarity

- Write a one-sentence explanation of what the project does.
- Write a one-paragraph explanation for non-technical readers.
- Make sure the README explains who the project is for.
- Remove exaggerated claims such as "production ready" unless fully verified.
- Replace placeholder links, emails, usernames, and repository URLs.
- Make sure screenshots, examples, and commands match the real project.

## 2. Human Review

- Read every public document from top to bottom.
- Remove private notes, rough drafts, and temporary implementation summaries.
- Remove tool-specific workflow notes that do not belong in public docs.
- Keep release notes factual and dated.
- Check grammar, spelling, and formatting manually.
- Make sure the tone sounds professional and calm.

## 3. Code Ownership

- Review all generated or copied code before committing.
- Rename unclear variables and files.
- Add comments only where they genuinely help.
- Remove dead code, duplicate folders, and unused experiments.
- Keep examples small and runnable.
- Make sure public APIs and CLI commands have clear names.

## 4. Safety And Security

- Search for secrets before every push.
- Never commit `.env`, tokens, private keys, passwords, or local credentials.
- Keep `.env.example` safe and empty.
- Add dangerous files to `.gitignore`.
- Run dependency checks when possible.
- Be clear about limitations, risks, and warranty.

## 5. Testing

- Run the full test suite.
- Run the main CLI commands manually.
- Test install instructions on a clean folder when possible.
- Verify examples in the README.
- Record what was tested in a short release note.
- Do not claim full coverage unless measured.

## 6. Documentation

- README should include:
  - project name
  - short description
  - features
  - installation
  - quick start
  - examples
  - limitations
  - license
  - support/contact path
- Keep advanced internals in separate docs.
- Keep private workflow instructions outside public docs.

## 7. Release Checklist

- Confirm `git status` is clean.
- Confirm the correct GitHub account and remote.
- Confirm the default branch is correct.
- Confirm license is present.
- Confirm README renders correctly on GitHub.
- Tag releases only after testing.

## 8. Public Presentation

- Use project-focused language.
- Credit the human maintainer or organization.
- Avoid naming private tools used during development.
- Avoid claims that cannot be demonstrated.
- Show what the software does today, not only future plans.

## 9. Final Human Pass

Before publishing, answer these:

- Would I understand this project if I saw it for the first time?
- Can a developer install and run it from the README?
- Are the limitations honest?
- Are secrets protected?
- Is the repo clean enough to show publicly?
- Does the project feel maintained, not dumped?

If any answer is no, fix that before pushing.
