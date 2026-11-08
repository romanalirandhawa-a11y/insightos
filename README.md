# InsightOS - AI Business Intelligence Platform

InsightOS is a Streamlit-based business analytics dashboard built for a
Business Analytics student portfolio. It turns raw business data into
decisions.

## Phase 1 - Foundation

This release lays the groundwork only. No analytics are implemented yet.

Features in Phase 1:

- Streamlit page configuration (wide layout, title, icon)
- Header with app name and tagline
- Sidebar navigation: Upload Data, Dashboard, AI Analyst, What-If Simulator
- Page tracking via `st.session_state`
- Placeholder KPI cards: Revenue, Profit, Orders, Growth
- Sample dataset: `data/sample_sales.csv` (200 rows)
- Clean dark theme via `.streamlit/config.toml`

## Project Structure

```
insightos/
├── app.py                      # Entry point: page config, header, KPI cards
├── README.md                   # This file
├── requirements.txt            # Python dependencies (do not modify)
├── .streamlit/
│   └── config.toml             # Streamlit theme configuration
├── core/
│   ├── __init__.py
│   ├── loader.py               # Data loading stubs
│   ├── cleaner.py              # Data cleaning stubs
│   ├── kpi.py                  # KPI calculation stubs
│   └── ai_analyst.py           # AI analyst stubs
├── ui/
│   ├── __init__.py
│   ├── layout.py               # Sidebar navigation
│   └── charts.py               # Charting stubs
├── data/
│   └── sample_sales.csv        # Sample sales dataset (200 rows)
└── assets/
    └── screenshots/            # App screenshots (add your own)
```

## Run Instructions

1. Open a terminal in the project folder:

   ```powershell
   cd C:\Users\C_2_D\Desktop\insightos
   ```

2. Activate the existing virtual environment (do not modify `venv` or
   `requirements.txt`):

   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

3. Run the app:

   ```powershell
   streamlit run app.py
   ```

4. Open the URL shown in the terminal (typically
   `http://localhost:8501`) in your browser.

## Next Phases (Planned)

- Phase 2: CSV upload, data cleaning, and validation
- Phase 3: KPI calculations and interactive charts
- Phase 4: AI analyst with natural-language Q&A
- Phase 5: What-If simulator
