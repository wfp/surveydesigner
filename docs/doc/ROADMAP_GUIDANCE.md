# Roadmap Guidance

The Survey Designer roadmap communicates the direction of the project: what the
maintainers intend to work on, in what rough order, and why. It helps
contributors and users understand where the project is heading and where they
can help.

## Where the roadmap lives

The roadmap is tracked through the project board in the WFP GitHub
organization:

* [Survey Designer project board](https://github.com/orgs/wfp/projects/11)

Issues on the board follow the hierarchy enforced by the
[Issue Hierarchy Validator](../../.github/workflows/issue-hierarchy-validator.yml)
workflow: **Epic → Feature → User Story → Task**. Roadmap-level planning is
expressed primarily through Epics and Features.

## How items get onto the roadmap

1. Ideas are captured as issues using the templates in
   [`.github/ISSUE_TEMPLATE`](../../.github/ISSUE_TEMPLATE) (Epic, Feature,
   User Story, Task, Bug).
2. Larger initiatives are grouped under an Epic, broken down into Features and
   User Stories, and prioritized on the project board.
3. Direction and prioritization are set by the collaborators and, for matters at
   an impasse, by the SurveyDesigner maintainers team following the
   [consensus-seeking process](../GOVERNANCE.md#consensus-seeking-process).

## Relationship to releases

Roadmap delivery is reflected in releases, which follow the
[Release Management & Tagging Strategy](contributing/RELEASE_MANAGEMENT.md).
Major roadmap milestones typically correspond to `MINOR` or `MAJOR` version
increments under Semantic Versioning.

## Contributing to the roadmap

Anyone may propose roadmap items by opening an issue and, optionally, raising it
for discussion in [GitHub Discussions](https://github.com/wfp/surveydesigner/discussions)
or the [WFP Slack Community](https://wfp.slack.com/). See
[CONTRIBUTING.md](../CONTRIBUTING.md) for the full contribution workflow.
