# SurveyDesigner Project Governance

<!-- TOC -->

* [Triagers](#triagers)
* [Collaborators](#collaborators)
  * [Collaborator activities](#collaborator-activities)
* [The SurveyDesigner maintainers team](#the-surveydesigner-maintainers-team)
* [Decision-making](#decision-making)
* [Collaborator nominations](#collaborator-nominations)
  * [Who can nominate Collaborators?](#who-can-nominate-collaborators)
  * [Ideal Nominees](#ideal-nominees)
  * [Nominating a new Collaborator](#nominating-a-new-collaborator)
  * [Onboarding](#onboarding)
* [Consensus seeking process](#consensus-seeking-process)

<!-- /TOC -->

## Triagers

Triagers assess newly-opened issues in the [survey-designer][] repository and [project](https://github.com/orgs/wfp/projects/11). The GitHub team for survey-designer triagers is @wfp/surveydesigner.
Triagers are given the "Triage" GitHub role and have:

* Ability to label issues and pull requests
* Ability to comment, close, and reopen issues and pull requests

See:

* [A guide for contributors](./CONTRIBUTING.md)

## Collaborators

SurveyDesigner core collaborators maintain the [survey-designer](https://github.com/wfp/surveydesigner) GitHub repository.
The GitHub team for SurveyDesigner core collaborators is @wfp/surveydesigner.
Collaborators have:

* Commit access to the [survey-designer](https://github.com/wfp/surveydesigner) repository
* Access to the SurveyDesigner continuous integration (CI) jobs

Both collaborators and non-collaborators may propose changes to the SurveyDesigner
source code. The mechanism to propose such a change is a GitHub pull request.
Collaborators review and merge (_land_) pull requests.

Two collaborators must approve a pull request before the pull request can land.
(One collaborator approval is enough if the pull request has been open for more
than 7 days.) Approving a pull request indicates that the collaborator accepts
responsibility for the change. Approval must be from collaborators who are not
authors of the change.

If a collaborator opposes a proposed change, then the change cannot land.
Usually the opposition is resolved through discussion or further changes. If the
maintainers cannot reach consensus, the project admin makes the final call (see
[Decision-making](#decision-making)).

See:

* [A guide for contributors](./CONTRIBUTING.md)
* [The onboarding guide for new collaborators](./ONBOARDING.md)

### Collaborator activities

* Helping users and novice contributors
* Contributing code and documentation changes that improve the project
* Reviewing and commenting on issues and pull requests
* Participation in working groups
* Merging pull requests

The maintainers team can remove inactive collaborators or provide them with
_emeritus_ status. Emeriti may request that the maintainers team restore them to
active status.

A collaborator is automatically made emeritus (and removed from active
collaborator status) if it has been more than 12 months since the collaborator
has authored or approved a commit that has landed.

## The SurveyDesigner maintainers team

The project is governed by **the SurveyDesigner maintainers team** — the
collaborators in the [@wfp/surveydesigner GitHub team](https://github.com/orgs/wfp/teams/surveydesigner).
There is no separate steering committee; the maintainers team holds final
authority over the project, including:

* Technical direction
* Project governance and process (including this policy)
* Contribution policy
* GitHub repository hosting
* Conduct guidelines
* Maintaining the list of collaborators

One maintainer acts as the project **admin**. The admin is responsible for
organization-level administration (repository and team settings, access
management) and breaks ties when the maintainers cannot reach consensus.

Changes to this governance policy are proposed as pull requests and follow the
[Consensus seeking process](#consensus-seeking-process). Changes that affect the
project's relationship with its host department also require approval by the
director of the department managing the solution.

## Decision-making

The maintainers team makes decisions by **consensus**:

* Most decisions are made directly on GitHub through pull request review and
  issue discussion. Routine changes do not need any special process beyond the
  normal two-approval rule described under [Collaborators](#collaborators).
* When a decision cannot be made through normal review — for example a
  disagreement about direction or an issue at an impasse — any maintainer may
  open an issue describing the question and mention the maintainers team. The
  proposal is adopted if, after a reasonable period (typically 72 hours), there
  is support from the maintainers and no sustained, unresolved opposition.
* If consensus still cannot be reached, the **admin makes the final decision**
  and records the rationale in the relevant issue or pull request.

Any community member can open a GitHub issue asking the maintainers team to
review something.

## Collaborator nominations

### Who can nominate Collaborators?

Existing Collaborators can nominate someone to become a Collaborator.

### Ideal Nominees

Nominees should have significant and valuable contributions across the SurveyDesigner
organization.

Contributions can be:

* Opening pull requests.
* Comments and reviews.
* Opening new issues.
* Participation in other projects, teams, and working groups related to SurveyDesigner.

Collaborators should be people volunteering to do unglamorous work because it's
the right thing to do, they find the work itself satisfying, and they care about
SurveyDesigner and its users. People should get collaborator status because they're
doing work and are likely to continue doing work where having the abilities that
come with collaborator status are helpful (abilities like starting CI jobs,
reviewing and approving PRs, etc.). That will usually--but, very importantly, not
always--be work involving committing to the `survey-designer` repository. For an example
of an exception, someone working primarily on the website might benefit from being
able to start CI jobs to test changes to documentation tooling. That,
along with signals indicating commitment to SurveyDesigner, personal integrity, etc.,
should be enough for a successful nomination.

It is important to understand that potential collaborators may have vastly
different areas and levels of expertise, interest, and skill. The SurveyDesigner
project, although not large, presents complexities in governance and for its evolution, and it is not expected that every collaborator
will have the same level of expertise in every area of the project. The
complexity or "sophistication" of an individual’s contributions, or even their
relative engineering "skill" level, are not primary factors in determining
whether they should be a collaborator. The primary factors do include the quality
of their contributions (do the contributions make sense, do they add value, do
they follow documented guidelines, are they authentic and well-intentioned,
etc.), their commitment to the project, can their judgement be trusted, and do
they have the ability to work well with others.

#### The Authenticity of Contributors

The SurveyDesigner project does not require that contributors use their legal names or
provide any personal information verifying their identity.

It is not uncommon for malicious actors to attempt to gain commit access to
open-source projects in order to inject malicious code or for other nefarious
purposes. The SurveyDesigner project has a number of mechanisms in place to prevent
this, but it is important to be vigilant. If you have concerns about the
authenticity of a contributor, please raise them with the maintainers team.
Anyone nominating a new collaborator should take reasonable steps to verify that
the contributions of the nominee are authentic and made in good faith. This is
not always easy, but it is important.

### Nominating a new Collaborator

To nominate a new Collaborator:

1. **Optional but strongly recommended**: open a
   [discussion in the survey-designer](https://github.com/wfp/surveydesigner/) repository. Provide a summary of
   the nominee's contributions (see below for an example).
2. **Optional but strongly recommended**: After sufficient wait time (e.g. 72
   hours), if the nomination proposal has received some support and no explicit
   block, and any questions/concerns have been addressed, add a comment in the
   private discussion stating you're planning on opening a public issue, e.g.
   "I see a number of approvals and no block, I'll be opening a public
   nomination issue if I don't hear any objections in the next 72 hours".
3. **Optional but strongly recommended**: Privately contact the nominee to make
   sure they're comfortable with the nomination.
4. Link relevant issues from the [survey-designer](https://github.com/wfp/surveydesigner/) repository. Provide a summary of
   the nominee's contributions (see below for an example). Mention
   collaborators in the issue to notify other collaborators about
   the nomination.

The _Optional but strongly recommended_ steps are optional in the sense that
skipping them would not invalidate the nomination, but it could put the nominee
in a very awkward situation if a nomination they didn't ask for pops out of
nowhere only to be rejected. Do not skip those steps unless you're absolutely
certain the nominee is fine with the public scrutiny.

Example of list of contributions:

* Commits in the [survey-designer](https://github.com/wfp/surveydesigner/) repository.
  * Use the link `https://github.com/wfp/surveydesigner/commits?author=GITHUB_ID`
* Pull requests and issues opened in the [survey-designer](https://github.com/wfp/surveydesigner/) repository.
  * Use the link `https://github.com/wfp/surveydesigner/issues?q=author:GITHUB_ID`
* Comments on pull requests and issues in the [survey-designer](https://github.com/wfp/surveydesigner/) repository
  * Use the link `https://github.com/wfp/surveydesigner/issues?q=commenter:GITHUB_ID`
* Reviews on pull requests in the [survey-designer](https://github.com/wfp/surveydesigner/) repository
  * Use the link `https://github.com/wfp/surveydesigner/pulls?q=reviewed-by:GITHUB_ID`
* Help provided to end-users and novice contributors
* Pull requests and issues opened throughout the SurveyDesigner projects
  * Use the link  `https://github.com/search?q=author:GITHUB_ID+org:wfp`
* Comments on pull requests and issues throughout the SurveyDesigner projects
  * Use the link `https://github.com/search?q=commenter:GITHUB_ID+org:wfp`
* Participation in other projects, teams, and working groups of the SurveyDesigner
  organization
* Other participation in the wider SurveyDesigner community

The nomination passes if no collaborators oppose it (as described in the
following section) after one week. In the case of an objection, the maintainers
team is responsible for working with the individuals involved and finding a
resolution. Following the [Consensus seeking process](#consensus-seeking-process),
the maintainers team may choose to advance a nomination that has otherwise
failed to reach a natural consensus or clear path forward even if there are
outstanding objections. The maintainers team may also choose to prevent a
nomination from advancing if it determines that any objections have not been
adequately addressed.

#### How to review a collaborator nomination

A collaborator nomination can be reviewed in the same way one would review a PR
adding a feature:

* If you see the nomination as something positive to the project, say so!
* If you are neutral, or feel you don't know enough to have an informed opinion,
  it's certainly OK to not interact with the nomination.
* If you think the nomination was made too soon, or can be detrimental to the
  project, share your concerns. See the section "How to oppose a collaborator
  nomination" below.

Our goal is to keep gate-keeping at a minimal, but it cannot be zero since being
a collaborator requires trust (collaborators can start CI jobs, use their veto,
push commits, etc.), so what's the minimal amount is subjective, and there will
be cases where collaborators disagree on whether a nomination should move
forward.

Refrain from discussing or debating aspects of the nomination process
itself directly within a nomination private discussion or public issue.
Such discussions can derail and frustrate the nomination causing unnecessary
friction. Move such discussions to a separate issue or discussion thread.

##### How to oppose a collaborator nomination

An important rule of thumb is that the nomination process is intended to be
biased strongly towards implicit approval of the nomination. This means
discussion and review around the proposal should be more geared towards "I have
reasons to say no..." as opposed to "Give me reasons to say yes...".

Given that there is no "Request for changes" feature in discussions and issues,
try to be explicit when your comment is expressing a blocking concern.
Similarly, once the blocking concern has been addressed, explicitly say so.

Explicit opposition would typically be signaled as some form of clear
and unambiguous comment like, "I don't believe this nomination should pass".
Asking clarifying questions or expressing general concerns is not the same as
explicit opposition; however, a best effort should be made to answer such
questions or addressing those concerns before advancing the nomination.

Opposition does not need to be public. Ideally, the comment showing opposition,
and any discussion thereof, should be done in the private discussion _before_
the public issue is opened. Opposition _should_ be paired with clear suggestions
for positive, concrete, and unambiguous next steps that the nominee can take to
overcome the objection and allow it to move forward. While such suggestions are
technically optional, they are _strongly encouraged_ to prevent the nomination
from stalling indefinitely or objections from being overridden by the maintainers
team.

Remember that all private discussions about a nomination will be visible to
the nominee once they are onboarded.

### Onboarding

After the nomination passes, a member of the maintainers team onboards the new
collaborator. See [the onboarding guide][] for details of the onboarding
process.

## Consensus seeking process

The SurveyDesigner maintainers team follows a [Consensus Seeking][]
decision-making model: the team seeks consensus first, and where consensus
cannot be reached the project admin breaks the tie, as described under
[Decision-making](#decision-making).

[Consensus Seeking]: https://en.wikipedia.org/wiki/Consensus-seeking_decision-making
[survey-designer]: https://github.com/wfp/surveydesigner
[the onboarding guide]: ./ONBOARDING.md
