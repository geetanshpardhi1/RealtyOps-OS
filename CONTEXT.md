# RealtyOps OS

A conversion-operations context for real-estate brokerages that turns inbound demand into scheduled property tours through AI execution with human accountability.

## Language

**Lead**:
A prospective buyer or renter entering the brokerage funnel from an intake channel.
_Avoid_: prospect record, inquiry row

**Brokerage Agent**:
The human salesperson accountable for the lead outcome and manual intervention decisions.
_Avoid_: Owner agent, assigned owner, human-in-loop agent

**Partially Qualified**:
A lead state where information is sufficient for human ownership assignment but not sufficient for autonomous booking.
_Avoid_: soft-qualified, half-qualified

**Fully Qualified**:
A lead state where required qualification fields are complete and valid for autonomous booking flow.
_Avoid_: qualified enough

**Assignment Gate**:
The rule that a lead can be assigned to a Brokerage Agent only after reaching Partially Qualified state.
_Avoid_: pre-qualification assignment

**Booking Escalation**:
The rule that low-confidence or borderline leads are routed immediately to human control for booking decisions.
_Avoid_: autonomous booking retry loops on low confidence

**Outreach Continuation**:
The rule that follow-up outreach cadence may continue after booking escalation unless manually paused.
_Avoid_: assuming escalation means all messaging stops

**Cadence Continuity Approval**:
A single control in human-owned mode that enables or disables scheduled outbound follow-up cadence without per-message approvals.
_Avoid_: per-cadence-message approvals

**Human-Owned Lead**:
A lead accountability mode where a Brokerage Agent owns decisions and override rights while AI may still execute allowed operational steps (including slot discovery/proposal) under policy guardrails.
_Avoid_: assuming only humans can send slots or links

**Autonomous Booking Gate**:
The rule that AI may auto-confirm booking only when the lead is Fully Qualified, confidence is at least 0.80, no active escalation flags exist, and calendar event creation succeeds.
_Avoid_: confirming bookings on intent alone

**Identity Merge Rule**:
The policy that exact phone match auto-merges leads, exact email match auto-merges only when phone is missing, and phone-email conflicts require human review.
_Avoid_: blind auto-merge on conflicting identity signals

**Lead Contract**:
The minimal canonical lead record fields that all workflows must share for consistent state transitions and ownership semantics.
_Avoid_: per-module ad hoc lead shapes

## Relationships

- A **Lead** is accountable to exactly one **Brokerage Agent** once assigned
- A **Brokerage Agent** can own many **Leads**
- A **Lead** can move from **Partially Qualified** to **Fully Qualified**
- **Assignment Gate** occurs at **Partially Qualified** and not before
- **Booking Escalation** can occur while **Outreach Continuation** remains active
- **Cadence Continuity Approval** is controlled only by assigned **Brokerage Agent** or admin
- A **Human-Owned Lead** can still receive AI-operated slot proposals and follow-ups when policy allows
- **Autonomous Booking Gate** must pass before booking confirmation is sent
- **Identity Merge Rule** determines whether inbound records are auto-merged or queued for human review
- **Lead Contract** is the shared baseline for intake, qualification, outreach, booking, escalation, and reporting

## Example dialogue

> **Dev:** "Can this lead be auto-booked now?"
> **Domain expert:** "No, it is only **Partially Qualified**; assign a **Brokerage Agent** first."

## Flagged ambiguities

- "owner agent" and "human in the loop" were used interchangeably with **Brokerage Agent** — resolved: use **Brokerage Agent** as canonical term.
- "qualified enough" conflicted with strict qualification language — resolved into **Partially Qualified** and **Fully Qualified**.
- "escalation" was ambiguous between booking control and messaging flow — resolved into **Booking Escalation** plus **Outreach Continuation**.
- "human-owned" was confused with manual-only execution — resolved: it defines accountability and override authority, not channel execution exclusivity.
- "booking confirmation" was ambiguous between accepted intent and confirmed schedule — resolved via **Autonomous Booking Gate**.
- "lead schema" risked fragmenting across parallel tracks — resolved by canonical **Lead Contract**.
