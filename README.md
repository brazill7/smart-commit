# fm-smart-commit

**AI-powered Git commit generation running *100% locally* on your Mac using Apple Intelligence.**

fm-smart-commit is a lightweight CLI tool that analyzes your staged Git changes and generates concise, professional [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `refactor:`, etc.).

Because it runs completely on-device using the Apple Foundation Models SDK, it offers massive advantages over cloud-based AI tools:

* **Privacy-First:** Your codebase never leaves your machine. Perfect for enterprise, proprietary, or sensitive code.
* **Zero API Costs:** No OpenAI API keys or GitHub Copilot subscriptions required. It uses the AI already built into your Mac.
* **Fast:** Powered natively by Apple Silicon neural engines for instant inference.
* **Multi-Pass Analysis:** Default mode runs parallel agents for better commit messages.

---

## Prerequisites

Before installing, ensure your machine meets the hardware and software requirements for local Apple Intelligence:
* **Hardware:** Apple Silicon Mac (M1 chip or newer).
* **OS:** macOS 15.0 (Sequoia) or newer.
* **Settings:** Apple Intelligence must be enabled on your Mac.

---

## Installation

### Via pip (Recommended)

```bash
pip3 install fm-smart-commit
```

### Updating

To update to the latest version of fm-smart-commit, run:

```bash
pip3 install --upgrade fm-smart-commit
```

### From Source

```bash
# Clone the repository
git clone https://github.com/brazill7/smart-commit.git
cd smart-commit

# Install in development mode
pip3 install -e .
```

---

## Usage

Make sure you have staged your changes (`git add .`) before running the tool.

### Quick Mode (Fast, Single-Pass)

```bash
fm-smart-commit -q
```

### Detailed Mode (Default, Multi-Pass Analysis)

```bash
fm-smart-commit
```

### With Custom Context

Provide context to guide the AI:

```bash
fm-smart-commit -c "fixes ticket #123"
fm-smart-commit -q -c "race condition on login"
```

### Options

| Flag | Description |
|------|-------------|
| `-q`, `--quick` | Use quick single-pass mode (faster but less detailed) |
| `-c`, `--context` | Additional context to include in the commit message |

### Git Alias (Optional)

If you want to use this tool natively within Git:

```bash
git config --global alias.sc '!fm-smart-commit'
git config --global alias.smart '!fm-smart-commit'
```

Then use:
```bash
git sc
git smart
```

---

## Example Output

```
$ fm-smart-commit
Analyzing diff (detailed mode - 3 parallel agents)...
  Scope: src/auth.py, login component...
  Intent: Improve user authentication...
  Changes: added hashPassword function...
Synthesizing results...

Suggested commit: fix: add hashPassword function for secure authentication
Accept commit? (y/n/r): y
Committed successfully!
```

### Prompt Options

- `y` - Accept and commit
- `n` - Abort
- `r` - Retry (infinite retries, automatically uses context from the last 3 rejected messages)

---

## Features

- **Conventional Commits:** Generates properly formatted commit messages
- **Privacy-First:** All processing happens locally on your Mac
- **Zero Config:** Works out of the box with Apple Intelligence
- **Two Modes:** Quick (fast) or Detailed (multi-pass parallel analysis)
- **Smart Retries:** Infinite retries that learn from your rejections to improve the next suggestion

---

## Requirements

- macOS 15.0+ (Sequoia)
- Apple Silicon Mac (M1+)
- Apple Intelligence enabled
- Python 3.10+

---

## License

MIT
