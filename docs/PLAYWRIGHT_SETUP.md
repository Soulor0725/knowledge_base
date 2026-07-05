# Playwright local setup & quick start

This project is primarily Python/Flask. Add these steps to run front-end E2E tests using Playwright.

Local setup (recommended):

1. Install Node (>=16/18) and npm.
2. In repo root, initialize package.json (if not present):
   - npm init -y
3. Install Playwright test runner:
   - npm install -D @playwright/test
4. (Optional) Install Playwright browsers locally:
   - npx playwright install

Create tests under a `tests/` directory, e.g. `tests/example.spec.ts`.

Run tests locally:

- npx playwright test

CI notes:
- A GitHub Actions workflow (.github/workflows/playwright.yml) was added that runs `npx playwright test` on push and pull requests to `main`. Ensure package.json and tests exist before enabling CI.

Tips:
- Keep tests independent of the Python API server where possible; for integration tests that require the backend, run the Flask app in a separate job step or use a service container.
