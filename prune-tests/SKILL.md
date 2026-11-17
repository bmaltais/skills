---
name: prune-tests
description: Prune tests that guard no behavior.
argument-hint: "[optional path]"
disable-model-invocation: true
---

Prune every test that guards no behavior. Scope: `$ARGUMENTS`, else the whole repo.

A test is **anchored** when it changes only when the intended behavior changes and fails only when it regresses.

## 1. Judge

Read every test in scope and give each a verdict: keep, rewrite, or delete. Delete a copy when another test already guards the same behavior. Look for tests that depend on:

**The past** — guards code that no longer exists, so nothing can ever make it fail.
- A feature was removed and a test asserts it's gone.
- A module was moved and a test asserts it's absent from its old path.

**Nothing** — no change to the code can make it fail.
- It tests the browser: a `<button>` renders, a click event fires.
- It mocks the unit under test, then asserts what the mock returns.
- It asserts what the type system already guarantees.

**The implementation** — it changes whenever the code does, even when behavior didn't.
- The expected value is derived from the same logic as the code, so a wrong result still passes.
- It asserts private state, internal call order, or which helper was invoked.

Done when every test in scope has a verdict.

## 2. Prune

- Delete each test that isn't anchored.
- Rewrite, against behavior callers see, a test that also covers behavior something relies on.
- Delete the production code that existed only for deleted tests.
- Run the suite after each batch.

## Done

- Every remaining test is anchored: it fails on a regression, and only on one.
- No two tests guard the same behavior.
- No production code exists only for tests.
- The suite is green.

## Example

```diff
--- a/pricing.test.ts
+++ b/pricing.test.ts
@@ rewritten: the expected value repeated the code's logic @@
 test("applies the discount", () => {
-  const price = 100;
-  expect(applyDiscount(price, 0.2)).toBe(price - price * 0.2);
+  expect(applyDiscount(100, 0.2)).toBe(80);
 });
--- a/cart.test.ts
+++ b/cart.test.ts
@@ rewritten against what callers see: it asserted private state @@
 test("adds an item to the cart", () => {
   const cart = new Cart();
   cart.add(book);
-  expect(cart._items.length).toBe(1);
+  expect(cart.total()).toBe(book.price);
 });
@@ deleted: checkout.test.ts already guards the same total @@
-test("total includes tax", () => {
-  expect(cartTotal([book], { tax: 0.1 })).toBe(11);
-});
--- a/export.test.ts
+++ b/export.test.ts
@@ deleted: it guards code that no longer exists @@
-test("legacy exporter is gone", () => {
-  expect(existsSync("src/export/legacy.ts")).toBe(false);
-});
--- a/session.test.ts
+++ b/session.test.ts
@@ deleted, with the production code that only existed for it @@
-test("clears the cache", () => {
-  _resetCacheForTests();
-  expect(_getCacheSize()).toBe(0);
-});
--- a/session.ts
+++ b/session.ts
@@ @@
-export function _resetCacheForTests() { cache.clear(); }
-export function _getCacheSize() { return cache.size; }
```
