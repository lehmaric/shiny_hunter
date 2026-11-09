# Context

Glossary for the shiny hunter bot. Terms only — no implementation detail.

## Capture Card

The external USB device carrying the Nintendo Switch's HDMI output into the host. Identified by its V4L2 card name, never by a node number: the number it receives depends on what else is attached and when.

Distinct from the host's built-in camera, which also presents as V4L2 devices and is not a Capture Card.

## Capture Node

The device node through which frames are actually read from a Capture Card.

A Capture Card claims more than one node. Only one of them carries video; see [[Metadata Node]]. "The capture device" is ambiguous between the card and this node — prefer the specific term.

## Metadata Node

A sibling node claimed by a Capture Card that carries no video frames. It reports the same card name as the Capture Node, so a name alone cannot tell them apart.

## Bluetooth Adapter

The host radio used to impersonate a Pro Controller. Reached through BlueZ, and never as a device node — there is no node for it to pass through. Its presence is visible as an adapter name rather than a file.

## Discovery

Resolving which Capture Node currently belongs to the Capture Card, at the moment capture starts. Answers "which node do I read from now?", not "which node existed at startup".

## Hotplug Visibility

Whether a device attached *after* the container started can be seen from inside it. Independent of [[Discovery]]: discovery can identify a card that the container cannot reach, and a reachable card can still be unidentified.

## Override

An explicitly configured Capture Node that suppresses [[Discovery]] entirely. An escape hatch for debugging, not a fallback — it is never consulted when discovery fails, because silently reading the wrong device is worse than stopping.

## Encounter Start

The moment a wild encounter begins while walking: the screen goes black for the transition. What the `encounter` sequence event detects.

Distinct from [[Encounter Loaded]]: one is a dark screen, the other a bright one, and the two are easy to confuse.

## Encounter Loaded

The battle scene has faded in after the [[Encounter Start]] transition and the Pokémon is visible. Waited for before any shiny check runs.

## Block Direction

A direction that is never pressed inside a `loop` block, so the character cannot walk out of the grass.
