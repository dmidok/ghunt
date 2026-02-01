# ghunt

Find available GitHub usernames using LLM suggestions (Ollama). Uses your prompt to generate candidate usernames, checks them on GitHub, and keeps asking the LLM (excluding already-checked names) until you have enough available. Token required; no anonymous API usage.

## Setup

1. **Clone and install**

```bash
git clone https://github.com/dmitriy-dokshin/ghunt.git && cd ghunt
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -e .
```

2. **GitHub token (required)**  
   Create a token at [github.com/settings/tokens](https://github.com/settings/tokens) (no scopes). Put it in `token.txt` (gitignored) or set `GITHUB_TOKEN`:

```powershell
# Windows
$env:GITHUB_TOKEN = Get-Content -Raw token.txt
```

```bash
# Unix
export GITHUB_TOKEN=$(cat token.txt)
```

3. **Ollama**  
   Install from [ollama.com](https://ollama.com), then run in a separate terminal:

```bash
ollama serve
```

On Windows, if `ollama` is not in PATH:

```powershell
$env:Path += ";$env:LOCALAPPDATA\Programs\Ollama"
```

## Usage

```bash
python main.py
# Defaults: prompt "short, memorable, developer", min-length 4, max-length 4, limit 50

python main.py -p "cyberpunk hacker" --min-length 4 -l 6 -n 10
# Your prompt, usernames between 4 and 6 characters, find 10 available
```

Already-checked usernames are stored in `ghunt_checked.txt` (gitignored) so each run avoids re-checking and can ask the LLM for new suggestions.

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `-p`, `--prompt` | short, memorable, developer | Prompt for the LLM |
| `--min-length` | 4 | Minimum username length (characters) |
| `-l`, `--max-length` | 4 | Maximum username length (characters) |
| `-n`, `--limit` | 50 | Number of available usernames to find |
| `-t`, `--token` | — | GitHub token (or set `GITHUB_TOKEN`) |
| `--exclude-file` | ghunt_checked.txt | File with already-checked usernames to exclude |
| `--model` | llama3.2 | Ollama model |
| `--ollama-host` | http://localhost:11434 | Ollama API host |

## Library

```python
from ghunt import find_available_from_llm, is_username_available, get_token

token = get_token()  # or pass token="..."

# Find available usernames (Ollama must be running)
available = find_available_from_llm(
    prompt="tech",
    min_length=4,
    max_length=4,
    limit=50,
    token=token,
    exclude_file="ghunt_checked.txt",
)

# Check a single username
is_username_available("octocat", token=token)  # False
```

## Testing

```bash
pip install -e ".[dev]"
pytest tests/ -v -m integration
```

`test_real_github_check` hits the real GitHub API and **fails** if `GITHUB_TOKEN` is not set. Set the token to have all tests pass.

## License

MIT
