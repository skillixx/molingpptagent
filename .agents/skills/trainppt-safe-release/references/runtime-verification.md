# Runtime verification

Use fresh evidence after the final process change.

## Local minimum

- expected local and remote Git commit;
- Main API health and release identity;
- database read-only query;
- persistent Worker process and expected commit/config evidence;
- Outline and Content Agent Cards;
- PersonalDB health;
- frontend entry and API proxy;
- template list uniqueness;
- target template JSON, cover, and referenced assets;
- unauthenticated `/auth/me` boundary;
- no-ticket `/enter` boundary.

Discover paths and ports from current config. Candidate defaults are useful for probing but are not proof.

## Result states

- `PASS`: every required, in-scope check succeeded with current evidence.
- `FAIL`: at least one required check produced negative evidence.
- `INCONCLUSIVE`: a required check could not run or ownership/release identity is unknown.

`INCONCLUSIVE` is not healthy. Report the missing evidence and do not make an end-to-end completion claim.
