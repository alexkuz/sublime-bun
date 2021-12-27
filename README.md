# sublime-bun
Bun binary files viewer and other Bun-related stuff

## Installation

Plugin is not publushed yet on [Package Control](https://packagecontrol.io/), to install it follow these steps:

- run `Package Control: Add Repository` command, add `https://github.com/alexkuz/sublime-bun` there;
- find and select `sublime-bun` package in `Install Package` menu.

## Settings

- `bun_path` - path to Bun executable (required for `bun.lockb` files processing), `~/.bun/bin` by default;
- `bun_binary_files` - a list of syntax definitions for binary files output;
  - `pattern` - pattern to match file name;
  - `syntax` - ST syntax definition that should be applied for that file;
  - `pretty` - indicates if prettifier should be applied (works for JS/TS files);
- `prettify_options` - pretifier options (see [Configuration struct](https://github.com/dprint/dprint-plugin-typescript/blob/64064984dc24339249c6425a1401f93d94887967/src/configuration/types.rs#L258) for full list)