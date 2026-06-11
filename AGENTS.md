# Agent validation checklist

If you modified any `strategies/<name>/main.py`, run these before finishing:

1. **Parse-check** (always):
   ```bash
   python -c "import ast; ast.parse(open('strategies/<name>/main.py').read())"
   ```

2. **Local backtest** (if `lean` is installed and Docker is running with data):
   ```bash
   lean backtest strategies/<name> --open
   ```
   Catches runtime errors and confirms the strategy runs end-to-end without
   consuming the QC free-plan quota.

3. **Cloud backtest fallback** (if Docker / data not available):
   ```bash
   lean cloud backtest strategies/<name> --open
   ```
   Uses QC cloud compute and the daily free-plan quota.

4. **Format check** (if the user will paste into the QC IDE):
   ```bash
   python tools/format_for_qc.py strategies/<name>/main.py --clipboard
   ```
   Confirms the file is clean of local-only imports and ready to paste.

Do not commit secrets, `.lean/` cache files, or anything under `data/`.
