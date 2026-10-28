---
title: A Basic Attack that plays a montage and deals damage on the hit
project: LSGI
lesson: lsgi-06-basic-attack-ability
created: 2026-10-27
target: Alvi
---

By the end you have a Basic Attack the turn-based fight can pick: a Blueprint ability `GA_Shark_BasicAttack` that plays `AM_Test_Combo` and deals the action's damage when the punch lands, plus an action asset tagged `BasicAttack` in the test kit. What the screenshots cannot show comes from the LSGI code, and each step says which file.

## Step 1: Find the montage the attack will play
shot: shots/step-001-after.png
callout: 0.094,0.671,0.270,0.687 | Content Browser search: AM_Test
callout: 0.079,0.697,0.107,0.810 | AM_Test_Combo, the montage the attack plays
instruction:
  In the Content Browser, search `AM_Test` and double-click `AM_Test_Combo` to open it in the montage editor.
  It lives in `Content/LSGI/System/Combat/Test`, next to `GA_TestSharkAttackSequence`, the test ability that already plays it.
why:
  The ability you build is only as good as the montage under it. Reading the montage first tells you when the hit happens, which is the moment damage must land, not the moment the ability starts.
expected:
  The montage editor is open on `AM_Test_Combo`, with the Notifies track visible under the timeline.

## Step 2: Read the hit event the montage sends
shot: shots/step-001-after.png
callout: 0.457,0.512,0.474,0.529 | Click this first Ability marker
callout: 0.652,0.076,0.751,0.405 | Its Event Tag appears here, in Details
instruction:
  On the Notifies track there are three markers labelled `Ability`, one per punch. Click the first one. The Details panel on the right then shows that notify's settings.
  These markers are `AN_GameplayEvent` notifies: each one sends a gameplay event to the character's ability system when the animation reaches it.
why:
  The montage task in your ability listens only for the tags you give it (`GASAbilityTask_PlayMontageAndWaitForEvent` registers exactly that tag container). Give it the wrong tag and the punch lands with no damage and no error. And there are three markers, so the same event arrives three times; step 8 makes damage land once.
expected:
  The first marker turns blue, and Details shows sections such as Anim Notify, Trigger Settings and Event.

## Step 3: The marker has no Event Tag, because the notify owns it
shot: shots/step-003-after.png
callout: 0.708,0.453,0.988,0.562 | Not the tag: Event here holds timing settings every notify has
callout: 0.708,0.190,0.988,0.270 | Where a per-marker Event Tag would appear: nothing here
instruction:
  Scroll the whole Details panel: there is no Event Tag. The **Event** section under Category holds Trigger Weight Threshold, Montage Tick Type and Can be Filtered Via Request, which every notify has.
  The tag is set once, on the notify class `AN_GameplayEvent`, and every marker of that class sends the same one. The montage file stores no tag value at all; the name `Ability` appears only inside `AN_GameplayEvent` (read from both asset files).
why:
  When a value you expect per instance is missing from Details, it usually lives on the class instead, and every placement shares it. That matters later: change the tag on `AN_GameplayEvent` and every montage using it changes too.
expected:
  You know the tag is read from `AN_GameplayEvent`, not from the montage.

## Step 4: Read the tag on the notify class
shot: shots/step-004-after.png
callout: 0.319,0.073,0.377,0.102 | Class Defaults: the values every placement of this notify uses
callout: 0.752,0.217,0.995,0.241 | Event Tag = Ability
callout: 0.005,0.308,0.150,0.329 | Event Tag variable, eye closed: not editable per marker
callout: 0.268,0.411,0.450,0.640 | GetNotifyName returns the tag's name: why the markers read "Ability"
instruction:
  In the Content Browser search `AN_GameplayEvent`, open it, and click **Class Defaults** in the toolbar. Details shows **Event Tag: Ability**.
  In My Blueprint, the `Event Tag` variable has a closed eye: it is not Instance Editable, which is why the montage's Details had no tag to show. The graph open on `GetNotifyName` returns the tag's name, which is the label you saw on each marker.
why:
  This is the tag your ability's montage task must listen for. And because it lives on the class, every montage that places `AN_GameplayEvent` sends `Ability`: if a later montage needs a different hit tag, it needs a different notify (or this variable made Instance Editable), not a change here.
expected:
  You can say the hit tag is `Ability`, and why the marker had no field for it.

## Step 5: Create the ability Blueprint on GASGameplayAbility
shot: shots/step-005-before.png
callout: 0.024,0.630,0.931,0.664 | Search All Classes: GASGa is enough
callout: 0.013,0.742,0.987,0.778 | GASGameplayAbility, under GameplayAbility: pick this one
callout: 0.086,0.848,0.516,0.883 | Lookalike: an effect calculation, not an ability
callout: 0.735,0.942,0.849,0.978 | Then Select
instruction:
  In `Content/LSGI/System/Combat/Test`, right-click an empty spot and choose **Blueprint Class**. In **Pick Parent Class**, expand **All Classes**, search `GASGa`, click **GASGameplayAbility**, then **Select**. Name the new asset `GA_Shark_BasicAttack`.
  `GASGameplayAbility` is AgateGAS's ability base. It sits under the engine's `GameplayAbility`, as the tree shows.
why:
  The parent decides which events and nodes the graph offers. The search also matches `GASGameplayEffectExecutionCalculation`; that one computes effect numbers and has no ability events, so picking it gives you a graph that cannot play a montage. Not `LSGICombatAttackAbility` either: its C++ deals the damage and ends the ability the instant it starts (`LSGICombatAttackAbility.cpp`), which would cut the montage off before the punch.
expected:
  A new `GA_Shark_BasicAttack` asset in the Test folder, and opening it shows **Parent class: GAS Gameplay Ability** in the top-right.

## Step 6: Start from the event that carries the action
shot: shots/step-006-before.png
callout: 0.897,0.044,0.993,0.062 | Parent class: GASGameplay Ability, the check for step 5
callout: 0.447,0.387,0.528,0.452 | Not this one: Event ActivateAbility has no Event Data
callout: 0.575,0.375,0.750,0.524 | Right-click here and search ActivateAbilityFromEvent
instruction:
  The graph opens with two greyed-out events. Leave them. Right-click an empty spot, search `ActivateAbilityFromEvent`, and add **Event ActivateAbilityFromEvent**.
  Then drag from its **Event Data** pin, choose **Promote to Variable**, and name the variable `SavedEventData`. Wire the event's white execution pin into the new Set node.
why:
  The turn flow starts this ability with a gameplay event whose payload holds the targets and the chosen action (`LSGITurnBasedCombatSubsystem_Phases.cpp`: `TriggerAbilityFromGameplayEvent` with `Payload.TargetData` and `Payload.OptionalObject`). Only the FromEvent version hands you that payload. You save it because the damage happens later, on the punch, and the montage's own events carry a different payload with no action in it.
expected:
  Event ActivateAbilityFromEvent is wired into a Set SavedEventData node, and My Blueprint lists SavedEventData under Variables.

## Step 7: Play the montage and listen for the hit
shot: shots/step-006-after.png
callout: 0.074,0.428,0.209,0.452 | SavedEventData, the check for step 6
callout: 0.672,0.434,0.684,0.457 | Drag from the Set node's white output pin
callout: 0.690,0.412,0.760,0.574 | Drop here and search PlayMontageAndWaitForEvent
instruction:
  Drag from the white output pin of the **SET** node, release on empty space, and search `PlayMontageAndWaitForEvent`. Pick the one that has an **Event Tags** input (AgateGAS's `GASAbilityTask_PlayMontageAndWaitForEvent`), not the engine's plain `PlayMontageAndWait`.
  On the new node set **Montage To Play** to `AM_Test_Combo`, and add `Ability` to **Event Tags**.
why:
  The plain `PlayMontageAndWait` tells you when the montage finishes, but not when the punch lands. The Event version also fires **Event Received** for each gameplay event whose tag is in Event Tags, which is how the `Ability` notify from step 4 reaches your graph. With Event Tags empty, nothing arrives and the attack deals no damage, silently.
expected:
  A PlayMontageAndWaitForEvent node after SET, Montage To Play is AM_Test_Combo, Event Tags holds Ability, and the node shows output pins including On Completed, On Interrupted, On Cancelled and Event Received.

## Step 8: Deal the damage once, on the first punch
shot: shots/step-007-after.png
callout: 0.615,0.628,0.646,0.644 | Drag from Event Received
callout: 0.665,0.587,0.760,0.749 | Place Do Once, then ApplyActionDamage, here
callout: 0.074,0.428,0.209,0.452 | Drag SavedEventData in as a Get for the Payload
instruction:
  Drag from **Event Received**, drop on empty space, and add a **Do Once** node. From Do Once's **Completed** output, add **Apply Action Damage** (category LSGI | Combat | Damage).
  Its **Ability** input already means Self. **Payload** needs the data you saved in step 6, so you read the variable back:
  - In My Blueprint, under **Variables**, press and hold on `SavedEventData`, drag it onto an empty spot in the graph, and let go. A small menu pops up with **Get SavedEventData** and **Set SavedEventData**: pick **Get**. (Holding Ctrl while you drop skips the menu and makes a Get straight away.)
  - A small node appears with one blue pin on its right. Drag from that pin to the **Payload** pin on Apply Action Damage.
  - Do not use the **Event Data** pin on the montage node. That one is the punch's own data, not the action's.
why:
  `AM_Test_Combo` has three `Ability` markers, so Event Received fires three times. Each `ApplyActionDamage` call deals the action's full formula damage and rolls its own crit (`LSGICombatDamageLibrary`), so without Do Once one Basic Attack hits three times. And the payload must be the saved one: the montage's event carries the notify's data, with no targets and no action, so damage would find nothing to hit.
  Do Once only resets when the ability object is new. AgateGAS abilities default to **Instanced Per Actor**, one object kept and reused for every turn, so the Do Once would stay closed after the first turn and the unit would never deal damage again. Step 9 sets the ability to a fresh object per use.
expected:
  Event Received → Do Once → Apply Action Damage, with SavedEventData (Get) wired into Payload.

## Step 9: End the ability when the montage stops, then compile
shot: shots/step-008-after.png
callout: 0.590,0.568,0.635,0.597 | SavedEventData (Get) into Payload, the check for step 8
callout: 0.505,0.357,0.535,0.441 | Wire On Completed, On Interrupted, On Cancelled (skip On Blend Out)
callout: 0.545,0.225,0.665,0.375 | Add End Ability here; all three wires go into it
callout: 0.122,0.077,0.155,0.106 | Then Compile, and Save
instruction:
  Right-click an empty spot and add **End Ability**. Drag a wire from **On Completed** into its white input pin, then do the same from **On Interrupted** and **On Cancelled**. One input pin takes all three wires.
  Leave **On Blend Out** and the white output of Apply Action Damage unconnected.
  Click **Class Defaults** in the toolbar and set **Instancing Policy** to **Instanced Per Execution**, so every turn gets a fresh ability and a fresh Do Once (step 8 says why). Then click **Compile** and save (Ctrl+S).
why:
  The turn does not move on until this ability ends: the turn flow waits for the ability system's ended signal before the next combatant acts (`HandleAbilityEnded` in `LSGITurnBasedCombatSubsystem_Phases.cpp`). An ability that never calls End Ability leaves the battle stuck on this turn. Wiring only On Completed is not enough either: a montage that is interrupted or cancelled never completes.
expected:
  Compile shows a green tick with no errors, and the tab title loses its asterisk after saving.

## Step 10: Check the finished ability
shot: shots/step-009-after.png
callout: 0.595,0.228,0.655,0.310 | End Ability, fed by Completed, Interrupted and Cancelled
callout: 0.505,0.378,0.536,0.395 | On Blend Out: hollow pin, left unconnected
callout: 0.218,0.821,0.670,0.843 | Compile ... successful
callout: 0.285,0.041,0.370,0.062 | No asterisk: saved
callout: 0.880,0.963,0.920,0.984 | 1 Unsaved left: AN_GameplayEvent, which should not be saved
instruction:
  Read the graph left to right: the turn's event is saved, the montage plays, the first `Ability` hit deals damage once, and any way the montage stops ends the ability.
  A filled pin has a wire, a hollow pin does not; that is how you check On Blend Out is empty without tracing lines.
why:
  A Blueprint that compiles is not proof it works, only that its wiring is legal. The checks that matter here are the ones a compiler cannot see: damage behind Do Once with Instancing Policy set to Instanced Per Execution, Payload from the saved variable, and every montage ending routed to End Ability.
expected:
  Compiler Results says successful, the tab has no asterisk, and the only unsaved asset is one you did not mean to change.

## Step 11: Create the action asset
shot: shots/step-011-before.png
callout: 0.024,0.319,0.931,0.429 | Search LSGICombatActio
callout: 0.013,0.442,0.987,0.545 | LSGICombat Action Definition: pick this one
callout: 0.013,0.551,0.987,0.651 | Lookalike: a different class, not an action
callout: 0.735,0.824,0.849,0.934 | Then Select
instruction:
  In `Content/LSGI/Pack/Base/System/Combat` (next to `DA_CombatAction_Test_ActionA`), right-click an empty spot, choose **Miscellaneous > Data Asset**, search `LSGICombatActio`, pick **LSGICombat Action Definition**, then **Select**. Name it `DA_CombatAction_Shark_BasicAttack`.
why:
  The ability is *how* the attack plays; this asset is *what* the menu offers. A combatant's kit lists action definitions, not abilities (`LSGICombatAbilitySet.h`: "the set lists combat actions rather than raw ability classes"), so an ability with no action pointing at it is never granted and never offered.
expected:
  A new `DA_CombatAction_Shark_BasicAttack` asset next to `DA_CombatAction_Test_ActionA`.

## Step 12: Point the action at the ability and tag it Basic Attack
shot: shots/step-012-before.png
callout: 0.406,0.216,0.449,0.236 | Ability Class: pick GA_Shark_BasicAttack
callout: 0.005,0.246,0.400,0.264 | Expand Presentation: Display Name and Category are inside
callout: 0.406,0.396,0.464,0.446 | Action Value 1.0 and Stat Factor Attack: already right
callout: 0.406,0.484,0.464,0.504 | Target Rule One Enemy: already right
callout: 0.009,0.074,0.019,0.097 | Save
instruction:
  Set **Ability Class** to `GA_Shark_BasicAttack`. Expand **Presentation**, set **Display Name** to `Basic Attack`, and set **Category** to `Combat.LSGI.Action.Category.BasicAttack`. Then save.
  Leave the rest: **Action Value** 1.0, **Stat Factor** Attack and **Target Rule** One Enemy are already what a basic attack needs, and Is Bonus Action stays off.
why:
  Category is not decoration. It is how the game tells a Basic Attack from a Skill, a Burst or an Item: menu grouping, the fallback icon, and the option-loss rules all read it (`LSGICombatTags.ini`: "What kind of action it is. Drives menu grouping and the fallback icon."). The existing test action is tagged Skill, which is why it was not a basic attack. And damage is `floor(Attack x Action Value x C / (C + Defense))`, minimum 1 (`LSGIDamageExecution`), so Action Value 1.0 means one times the attacker's Attack before defense.
expected:
  Ability Class shows GA_Shark_BasicAttack, Category shows BasicAttack, and the tab loses its asterisk.

## Step 13: Check the action, and save it for real
shot: shots/step-012-after.png
callout: 0.406,0.216,0.470,0.236 | Ability Class: GA_Shark_BasicAttack
callout: 0.406,0.274,0.520,0.293 | Display Name: Basic Attack
callout: 0.406,0.334,0.511,0.354 | Category: Combat.LSGI.Action.Category.BasicAttack
callout: 0.045,0.038,0.160,0.059 | The asterisk: changed but not saved yet
callout: 0.009,0.074,0.019,0.097 | Click Save (or Ctrl+S with this window focused)
instruction:
  Check the three values you set. Then look at the tab title: an asterisk after the name means the change exists only in memory. Click **Save** and watch the asterisk disappear.
why:
  Unreal keeps edits in memory until you save, and the status bar's Unsaved count is the honest number. An unsaved action works in this editor session and is gone after a restart or a teammate's pull, which looks exactly like "it worked yesterday".
expected:
  The tab title has no asterisk, and the Unsaved count dropped by one.

## Step 14: Put the Basic Attack in the combatant's kit
shot: shots/step-014-after.png
callout: 0.405,0.215,0.445,0.234 | Actions: 1 Array element
callout: 0.433,0.246,0.533,0.266 | Index [0]: DA_CombatAction_Shark_BasicAttack
callout: 0.045,0.037,0.125,0.059 | No asterisk: saved
instruction:
  Open `DA_AbilitySet_Test` (in `Content/LSGI/Pack/Base/System/Combat`), expand **Actions**, and set **Index [0]** to `DA_CombatAction_Shark_BasicAttack`. This replaces the old test action, `DA_CombatAction_Test_ActionA`, so every turn this combatant takes is a damaging Basic Attack. Save.
  Saving asks you to **Check Out** the asset: every `.uasset` here is a Git LFS lockable file (`.gitattributes`), and checking out takes the lock in your name so teammates cannot save over you. Pick **Check Out Selected**, not Make Writable.
why:
  This list is the combatant's whole menu and also what gets granted to its ability system: the set grants one ability per listed action (`LSGICombatAbilitySet.h`). The turn flow then looks up the granted ability by the action's Ability Class (`FindAbilitySpecFromClass` in `LSGITurnBasedCombatSubsystem_Phases.cpp`), so an action that is not in this list cannot run even if everything else is right. Replacing the old action also makes the test unambiguous: the old one was tagged Skill and dealt no damage.
expected:
  Actions shows 1 Array element, Index [0] is DA_CombatAction_Shark_BasicAttack, and the tab has no asterisk.
