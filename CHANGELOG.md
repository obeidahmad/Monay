# Changelog

All notable changes to Monay are documented here. This project adheres to
[Semantic Versioning](https://semver.org/) and the
[Keep a Changelog](https://keepachangelog.com/) format.

## [1.0.1] — 2026-06-14

### Fixed

- **Standalone binaries crashed on first launch** with
  `no such table: profiles`. The frozen PyInstaller binary discovered database
  migrations from the filesystem, which finds nothing inside a bundled one-file
  app, so the schema was never created. Migrations are now registered via a
  static import, and the release self-check exercises the database so this
  can't silently regress.

## [1.0.0] — 2026-06-14

### Added

- Initial release. A keyboard-driven terminal budget app with:
  - user-defined **pre/post sections**, **fields** with finite or infinite
    rollover caps, and **pockets** (per-account "should hold" counters);
  - monthly **close & rollover** (pots carry forward, section RESTs route to
    income / themselves / another section), borrowing modeled honestly, and
    arithmetic expressions for any amount;
  - multiple independent **profiles**, a **Textual** TUI with five tabs, and a
    pure, fully-tested budgeting engine.
- Standalone **Linux and Windows** binaries (x86_64 + arm64), built and
  published with checksums by GitHub Actions.

[1.0.1]: https://github.com/obeidahmad/monay/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/obeidahmad/monay/releases/tag/v1.0.0