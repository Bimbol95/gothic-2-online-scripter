# Modified Squirrel reference

Authoritative source: <https://gothic-online.gitlab.io/dependencies/squirrel/differences/index.html>

Gothic 2 Online uses a modified Squirrel 3.2. The source documents these differences.

## Language features

- local class expressions;
- `_get` behavior used by the `in` operator;
- `foreach` support for class instances;
- enum values that auto-increment after the previous integer;
- retrieving an enum as a table;
- the `classof` operator;
- JavaScript-like string interpolation using backtick-delimited strings and `${...}` placeholders;
- null coalescing with `??`;
- optional chaining with `?.`;
- optional indexed access with `?[]`.

## String interpolation

The fork documents string interpolation with this form:

```js
local greeting = `Hello there ${user_name}!`
```

Use backticks around the interpolated string and `${...}` around the inserted value. The documented changelog example establishes this syntax. Do not assume additional interpolation semantics that are not established by the fork documentation.

## Added functionality

- `geterrorhandler`, `getdefaultdelegate`, `getreleasehook`, and `setreleasehook`;
- `getstacktop` and `getstacksize` for debugging;
- `rawstring`, `dump`, `min`, `max`, `clamp`, `lerp`, `round`, `random`, `randomseed`, and `runningthread`;
- `file.read` and `file.write`;
- `blob.read`, `blob.write`, and `blob.tostring`;
- `function.vcall` and `function.pvcall`;
- `thread.acall`;
- `regexp.captureall`;
- `.toblob`.

## Changed behavior

- regular expressions use the C++ standard-library regex implementation;
- optional regex groups return `null` in capture results;
- `clock` is consistent across platforms.

Do not assume other upstream Squirrel features or fork differences. Consult the supplied source page when exact syntax or semantics matter.

