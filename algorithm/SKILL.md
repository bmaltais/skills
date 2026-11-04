---
name: algorithm
description: Run a task through the five-step Algorithm (question, delete, simplify, accelerate, automate), in that order.
disable-model-invocation: true
---

# The Algorithm

Finish the task with fewer parts, fewer steps, faster loops, and automation only at the end. Based on the five-step Algorithm Elon Musk describes in Isaacson's biography.

Passes run in order: **question → delete → simplify → accelerate → automate**. Each pass ends on a number or a file, which gates the next.

## Inputs

Take these from the request: task, deliverable and path, acceptance checks, requirements (each with an owner), scope you may change, budget. Ask one question only when a missing field changes the outcome; otherwise start.

## 1. Question

List every requirement with its owner. A requirement without a name is dropped. For each, write what breaks if it goes; mark the ones where the honest answer is "nothing". Build nothing yet.

Done when: every requirement has an owner or a mark.

## 2. Delete

Remove every marked requirement, step, file and tool call. Log each removal in `delete.log`, one line of reasoning each. Run the checks on what is left.

Done when: fewer than 10% of deletions had to come back. Beyond that, delete more.

## 3. Simplify

Cut what survived to the shortest version that still passes the checks. One file where there were three, one call where there were several; merge steps that always run together.

Done when: the checks pass on the shortest version.

## 4. Accelerate

Measure the full cycle, input to verified output, and write the number to `cycle.md`. Remove waits, retries and handoffs the checks never needed. Measure again.

Done when: the new number is lower. Revert any change that did not lower it.

## 5. Automate

Wrap the loop so it runs unattended. Every automated step keeps its check; whatever failed a check in passes 1 to 4 stays out.

## Order

Each pass needs the number or file named above before the next begins: deleting precedes optimizing, simplifying precedes automating, and no requirement exists without an owner.

## Stop

Stop when every check passes, the budget is reached, or a deletion needs human approval. Return the deliverable, `delete.log`, `cycle.md` (before and after times), and the surviving requirements with their owners.
