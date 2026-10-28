# Contributing

Thanks for your interest in improving ESP32 Flash Tool.

## Development Setup

Requires Python 3.10+.

```bash
pip install -r requirements.txt
python flash_tool.py            # run the GUI from source
```

## Running Tests

```bash
python -m unittest discover -s tests -v
```

Tests must pass before submitting a pull request. CI runs them on every
push and PR.

## Code Conventions

- Match the existing code style; comments and commit messages in English;
- **UI strings**: add every new user-visible string to BOTH the `en` and
  `zh` tables in `esp32flash/i18n.py` (a unit test enforces key parity);
- **Documentation**: keep `README.md` and `README.zh-CN.md` in sync;
  detailed topics belong in `docs/`, not in the README;
- Never commit firmware binaries, `dist/`, or `build/` artifacts.

## Testing with Real Hardware

Changes to the flashing pipeline (`esptool_job.py`, `serialboot.py`,
`manifest.py`) should be verified with a real device when possible:
chip detect → flash → boot-version verification. Note the chip model
and firmware source in your PR description.

## Packaging Changes

If you modify `ESP32FlashTool.spec` or the frozen-mode esptool
forwarding in `flash_tool.py`, verify the built exe on a clean Windows
machine without Python — see the acceptance checklist in
[docs/packaging.md](docs/packaging.md).

## Reporting Bugs

Use the bug-report Issue template and include the full log area
content, your OS, chip model, and firmware source.
