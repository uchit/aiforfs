# Troubleshooting

## Missing dependencies

Create a virtual environment and install the starter requirements:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Missing API key

Copy `.env.template` to `.env` and set `OPENAI_API_KEY`.

## Test execution

Run:

```bash
.venv/bin/python -m pytest tests -q
```

## No SAR output generated

The workflow will only generate SAR files when the human review gate approves the case.

