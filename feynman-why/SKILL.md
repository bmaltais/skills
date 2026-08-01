---
name: feynman-why
description: Explain why without cheating — name the floor the answer stands on, then go one rung past it. Use when the user asks why or how something works, asks for an ELI5, or when an explanation is reaching for a metaphor.
categories: [explanation, teaching]
agents: [claude]
metadata:
  scope: global
  source: custom
---

# Feynman Why

From Feynman on the magnets. Moves 1–4 run in order; move 5 fires whenever it's available.

## 1. Pin the question

"What is the *feeling* between the magnets?" is not a question yet. Feynman refused it twice before answering.

When the ask hides an unexamined word — *feeling*, *really*, *actually*, *under the hood* — reflect one question back: "how the force works, or why it feels unlike other pushes?" Then answer. Done when a specific question is on the table, whether it arrived that way or you got it there in one exchange.

## 2. Set the floor

Every why-answer is an answer only inside a set of things the asker already accepts. Aunt Minnie is in hospital because she slipped on ice — satisfying only to someone who already grants that broken hips mean hospitals, that husbands call ambulances, that ice is slippery. Without a floor the regress runs forever: ice is slippery → pressure-melting → water expands on freezing → why.

State the floor out loud before explaining: "taking the magnetic field as given —", "assuming request/response is familiar —".

Three kinds of floor, and the differences matter:

- **Chosen** — you could go deeper and are electing not to. Say so and leave the door open: *"Ice is slippery" is a fine stopping point; there's a real answer underneath about pressure melting it — want it?*
- **Forced** — the explanation genuinely bottoms out. "That's one of the elements of the world — there are electrical forces, magnetic, gravitational, and those are some of the parts." Say it plainly, then say what *is* known around it: magnetism and electricity are intimately related; gravity's relation to them is unknown. An honest engineering floor sounds the same: "the kernel scheduler decides; from here it's a black box we treat as given."
- **Yours** — the subject has more, you don't have it. "There's a real answer below this and I'd be guessing at it" — then name where it lives: the source, the file, the person to ask.

Keep each floor in its own clothes: your limit reported as yours leaves the asker digging, reported as the world's stops them at a wall that isn't there. Inventing a deeper layer to avoid admitting a forced floor is move 4's failure in disguise.

Done when the floor is stated out loud and you know which of the three it is.

## 3. Pick a depth and label it

One question has many correct answers at different depths — "depends on whether you're a student of physics, or an ordinary person."

Choose the level that fits the asker, name which one you chose, and offer the next: *"That's the working answer. There's a level below involving X — want it?"* Both the label and the offer, every time; an unlabelled simplification reads as the whole truth.

**Then take one rung past the offer, if that rung is surprising.** Feynman doesn't stop at "ice is slippery" — he descends: pressure momentarily melts it, because water is the substance that *expands* when it freezes, and most others crack instead. Nobody asked for three layers; he went because each turned over something the asker didn't know they'd find.

A rung earns the descent by surprising, not by being lower — one that only adds vocabulary, or a mechanism the asker can't act on, is the recitation [The tell](#the-tell) catches. Take the interesting rung, then stop.

## 4. Don't cheat

Magnets are *not* rubber bands, and Feynman calls reaching for that "cheating you." Two failures, both fatal:

1. **It's untrue in a way that bites later.** Nothing connects the magnets; the asker builds on fiction.
2. **It's circular.** Rubber bands pull back *because of* electrical forces — the very thing being explained.

Run both checks on an analogy before it ships: where does it break, and does explaining the analogy need the thing it explains? A stated limit rescues one that survives: "like a rubber band, except nothing connects them and it doesn't weaken with stretching." One that fails either check gets replaced by a plain description of the real behaviour.

## 5. Route through what they already accept

Usually the opening. The asker is disturbed by magnets and untroubled by a chair refusing their hand — same electrical repulsion. That reframing beats any metaphor, because it's true.

Find the thing they already accept without question that is the same phenomenon, and the question inverts productively: not "why do magnets repel" but "why does this one reach across a gap" — which has a real answer, aligned electron spins. The route relocates the mystery: what looked strange turns out to be something they've lived with all day, and what's left is sharp enough to answer.

## The tell

The deeper you go, the more interesting it gets. An explanation that gets *duller* as it descends is recitation, not explanation — go back to move 2 and find the real floor.

## Shape of the answer

The moves are how you think; the answer is prose. Feynman's is conversational start to finish — the machinery stays underneath it.

Three things surface, each as a clause inside a sentence: the floor, the depth label, the offer of the next rung. Everything around them reads as continuous explanation.

## Worked example

> **"Why is our Docker build slow?"**
>
> *(move 1, one exchange: "slow" is the unexamined word — cold-start slow, or every-time slow? Every time.)*
>
> Taking the layer cache as given, every build is a stack of layers, and a layer is reused only if nothing above it changed. Your `COPY . .` sits before `npm install`, so touching any source file invalidates the copy layer and everything below it rebuilds — including the install. You're not reinstalling because dependencies changed. You're reinstalling because a comment moved.
>
> That's the working answer, and it's the one that fixes the build: copy `package*.json`, install, then copy the rest.
>
> One rung down is the surprising part — the cache key isn't a timestamp, it's a hash of the layer's content and its parent's key, which is why invalidation is *positional*: a change can only bust layers below it, never above. Reordering a Dockerfile is a real technique, not superstition.
>
> Below that I'd be guessing — what exactly BuildKit hashes for a `COPY` (mode bits? mtime?) I don't know; it's in the BuildKit docs under cache keys.
