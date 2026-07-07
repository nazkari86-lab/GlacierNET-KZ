# Contributing to GlacierNET-KZ

Thank you for your interest in contributing! This project monitors glacier retreat in Kazakhstan's Ili Alatau using deep learning.

**English README:** [README.en.md](README.en.md) · **Citation:** [CITATION.cff](CITATION.cff) · **Reproducibility:** [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) · **Code of Conduct:** [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/nicklaua/GlacierNET-KZ.git
cd GlacierNET-KZ

# Install dependencies
pip install -r requirements.txt

# Run the smoke test (no GEE auth needed)
python notebooks/_synthetic_smoke_test.py
```

## Development Setup

### Prerequisites
- Python 3.10+
- Google Earth Engine account (for data download)
- 8+ GB RAM (for U-Net training)
- GPU optional but recommended for training

### Code Style
- **Python**: ruff (lint + format), type hints encouraged
- **Comments**: Mix of Russian and English (matching existing code)
- **Docstrings**: Google-style for public functions
- **Tests**: pytest, aim for >80% coverage on new code

### Running Checks
```bash
ruff check src/ glacierkz-api/app/   # Lint
ruff format src/ glacierkz-api/app/  # Format
pytest tests/ glacierkz-api/tests/ -v -m "not experimental"  # Tests
pyright                              # Type check

# Optional: install pre-commit hooks for automatic checks before commit
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## Project Structure

```
src/              # Core ML modules
├── config.py     # All constants, paths, hyperparameters
├── data_loader.py
├── preprocessing.py
├── models.py     # U-Net, RF, NDSI, ensemble
├── metrics.py    # F1/IoU, trend, forecast, WGMS validation
└── visualization.py

notebooks/        # Jupyter notebooks (01-06)
scripts/          # Standalone scripts (generate_figures.py)
paper/            # Scientific paper (Markdown)
results/          # Output figures and tables
```

## How to Contribute

### Good First Issues
- Fix typos in documentation
- Add unit tests for utility functions
- Improve error messages
- Add docstrings to undocumented functions

### Medium Complexity
- Add new spectral indices (NDMI, NDGI)
- Implement data augmentation transforms
- Create Colab notebook version
- Add Web UI for interactive visualization

### Advanced
- Train U-Net on multi-year data
- Implement U-Net++ or DeepLabv3+ comparison
- Add SAM (Segment Anything) baseline
- Deploy to HuggingFace Spaces with Gradio

## Submitting Changes

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-change`
3. Make your changes with tests
4. Run checks: `ruff check src/ && pytest tests/ -v`
5. Commit with a descriptive message
6. Open a PR with a clear description

## Data Note

The `data/` directory is not in the repo (too large). To download data:
1. Follow instructions in `notebooks/01_data_download.ipynb`
2. Requires Google Earth Engine authentication
3. See `docs/` for data sources and references

## Questions?

Open a GitHub Issue or start a Discussion. We welcome contributions from glaciologists, ML engineers, and anyone interested in Central Asian climate science.
