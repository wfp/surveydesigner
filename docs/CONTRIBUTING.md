# Contributing to Survey Designer 📊

Thank you for your interest in contributing to **Survey Designer**! To keep our development organized and our codebase secure, please follow the workflow outlined below.

## ⚖️ License

By contributing to this project, you agree that your contributions will be licensed under the **GNU Affero General Public License v3 (AGPL-3.0)**.

---

## 🛡️ Security Protocol

**IMPORTANT: DO NOT open a public issue for security vulnerabilities.**

If you discover a security-related bug:

1. **Do not** create a GitHub issue.
2. **Email:** Send a detailed report to **leandro.bravo@wfp.org**.
3. **Template:** Please use the standard security reporting template in your email.

---

## 🔄 Contribution Workflow

We use a **monorepo** structure and follow **trunk-based development**. All new work should be branched directly from the main trunk. For a comprehensive guide on our technical runtimes, services, and core architectural alignment, refer to our [Technical Values & Development Principles](doc/contributing/TECHNICAL_VALUES.md) document. Please follow this specific process for all features and non-security bug fixes:

### 1. Identify the Need

- **Check existing issues:** Search the Issue Tracker first.
- **If it exists:** **Contact the Admin** directly to coordinate. Do not open a duplicate.
- **If it does not exist:** Create a new issue using the provided **Bug** or **Feature** templates.

### 2. Issue Validation

- Every issue must be **detailed**.
- If a maintainer requests more information, please **add comments** to the issue.
- Once the issue is detailed and confirmed, you may proceed to create a new branch.
- **Branch Naming Standard:** Create your branch with a prefix referencing the GitHub issue number and a short description. We recommend using formats like `issue/<issue-number>-<short-description>` (e.g., `issue/42-fix-login`) or `feature/<issue-number>-<feature-name>`.

### 3. Development & PR

1. **Develop:** Work on your changes within your designated branch.
2. **Pull Request:** Create a PR targeting the main trunk. **Crucial:** Ensure the PR description **contains a direct link to the relevant GitHub issue** and explicitly mentions your branch name.
3. **Testing & Security:** We require manual testing before submitting a PR.
   - **Frontend:** Run `pnpm test:ci` to execute the frontend tests.
   - **Backend:** Run `docker compose run api test-ci` to execute the backend tests.
   - **Security:** Run a Trivy scan to ensure there are no security vulnerabilities.
   - **Note:** You must fix any failing tests or security issues before your PR can be merged.
4. **Approval:** Maintainers will review the code. If changes are requested, add comments and push updates to your branch.

### 4. Merging

- Once the PR is **Approved**, it will be merged into the target branch by a maintainer.
- All code changes follow our semantic versioning and Git tagging standards. See the [Release Management & Tagging Strategy](doc/contributing/RELEASE_MANAGEMENT.md) for details on release criteria and tagging naming rules.

---

## 💻 Technical Guidelines

### 🎨 Frontend Developers (React)

- Follow the project's UI/UX patterns.
- Ensure all new components are documented.
- **AGPL-3.0 Compliance**: Ensure that any new frontend dependencies, libraries, or React components introduced are compatible with the GNU Affero General Public License v3 (AGPL-3.0).

### ⚙️ Backend Developers (Django)

- Ensure API changes are reflected in the documentation.
- **AGPL-3.0 Compliance**: Maintain strict AGPL-3.0 compliance for all third-party Python/Django packages. Any new backend service or module must be licensed under or compatible with AGPL-3.0.

### 🧪 Testers & QA

- Verify that the PR actually solves the linked issue.
- Provide clear reproduction steps if a **TEST Job** fails.

---

## 💬 Communication

If you have questions about the workflow or need to contact an admin regarding an existing issue, please use this project's issues or reach out to **global.surveydesigner@wfp.org**.

**Thank you for helping us make Survey Designer better!**
