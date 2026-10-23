# Frozen Odin SMO reference

**Bonneton resume platform, camera turned to face the Odyssey; not the open town area; FPS may be optimistic versus open-area play.**

Temporary native guest P1 → Korri Seat P2 is used for the bench and soak. The shipped default remains Seat P1. The account's permanent, native-UI-configured Seat P1 mapping is restored afterward.

The user's real save resumes with **1242 coins and 3 health**. Mario does not move. The distinct admitted Bluetooth-matched bench pad sends Nintendo A (`BTN_EAST`, 305) at 45 seconds, releases it after 200 ms, then holds right-stick -X for 1.5 seconds at 60 seconds and releases it. No keyboard input, seat impersonation, InputPlumber policy change or rumble is used.

The 8-second confirmation used during preparation arrived too early in three fresh launches; those screenshots remained at Resume. They are not gameplay or FPS evidence. The corrected 45-second confirmation reaches gameplay.

The frozen ship view was checked through three fresh real library launches:

| Backend selection | Launch | Reference |
|---|---|---|
| Native-default NCE | `4331d9cd8fcfda70f9a3ef9672047794` | `camera-nce-1.png` |
| Explicit Dynarmic | `5dab2a5f68dd1a0cf01359205a4ef54a` | `camera-dynarmic.png` |
| Native-default NCE | `5155d0734dc93670cb6d86644f527efd` | `camera-nce-2.png` |

The Odyssey stairs, globe, flag and platform match. Fog, the globe animation and Mario's idle pose vary. Every measured run must independently show this view before its warmup ends. The collector's automatic PASS alone does not accept navigation.

`bonneton-reference.evemu` SHA256: `ddb89a3782bfdee6b8fd3ae808861993ab337fbeb70c8878f915caf87d496135`.

Screenshots use XGetImage on the actual presenting Eden window as its runtime UID in its mount namespace. They are application-image evidence, not an independent physical-panel scanout test. Backend selection plus agreeing runtime mappings and no refusal is **inferred**, not direct instruction-execution proof.

`bubblewrap: absent — core gap #184`

Public reference: [full-resolution encoded reference](reference.jpg). This is an
encoded derivative, not the original PNG. See [encoder/settings and both hashes](REFERENCE-ENCODING.json).
The three original reference images and measured-run images remain private;
[their hashes](ARCHIVE.sha256) identify the untouched archive bytes.
