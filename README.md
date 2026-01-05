# Mashing Data Analysis Tool - Streamlit

A multi-page Streamlit application for analyzing mashing process data in brewing/distilling operations.

## Features

- **7-Phase Process Visualization**: Automatic detection and visualization of brewing phases
- **Sensory Notes Filtering**: Filter batches by sensory notes intensity (0-3)
- **Multi-Batch Comparison**: Overlay multiple batches for comparison
- **Phase Analysis**: Detailed plots for each processing phase
- **Statistical Analysis**: Multi-batch statistical comparison with interpretation guides

## Installation

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
streamlit run v3.py
```

## Deployment to Streamlit Cloud

1. Push this repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Sign in and click "New App"
4. Select your repository and `v3.py` as the main file
5. Deploy!

## File Structure

```
Streamlit/
├── v3.py                    # Main application
├── pages/
│   ├── 1_Phase_Analysis.py  # Detailed phase visualizations
│   └── 2_Statistics.py      # Batch statistics
├── data/                    # Data files (not in repo - add your own)
│   ├── combined_mashing_data_all.csv
│   ├── Audi_parametric_data.csv
│   └── Diageo_ Data_Available_Report (1).xlsx
├── requirements.txt
└── README.md
```

## Data Files

The app expects the following data files in the `data/` directory:

| File | Description |
|------|-------------|
| `combined_mashing_data_all.csv` | Time-series mashing process data |
| `Audi_parametric_data.csv` | Batch parametric data |
| `Diageo_ Data_Available_Report (1).xlsx` | Good/Bad batch classification |
| `AuDi_Sensory Output File.xlsx - TC Consensus Score-FMS.csv` | (Optional) Sensory notes data |

## Embedding in SharePoint

After deploying to Streamlit Cloud:

1. Copy your app URL (e.g., `https://your-app.streamlit.app`)
2. In SharePoint, edit your page
3. Add an "Embed" web part
4. Paste the URL
5. Publish the page
