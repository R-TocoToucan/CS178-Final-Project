# CS178 Final Project: Green Line Extension Headway Analysis

This project investigates whether the Green Line Extension (GLX) to Tufts behaves differently from the rest of the MBTA Green Line. The analysis focuses on train headways, service regularity, long service gaps, missing data, and terminal-stop behavior.

The project uses a Flask backend, DuckDB database, and D3.js visualizations to compare GLX stops against other Green Line branches and broader MBTA rapid transit service.

## Project Structure

```text
CS178-Final-Project/
  app.py
  setup_db.py
  download_mbta_headways_2025.py
  validate_data_folder.py
  requirements.txt
  static/
  templates/
```

The large data files are not stored directly in GitHub. They are downloaded locally using the provided download script.

## Requirements

Install the required Python packages with:

```powershell
py -m pip install -r requirements.txt
```

## Setup Instructions

### 1. Clone the repository

```powershell
git clone https://github.com/R-TocoToucan/CS178-Final-Project.git
cd CS178-Final-Project
```

### 2. Install dependencies

```powershell
py -m pip install -r requirements.txt
```

### 3. Download the dataset

```powershell
py download_mbta_headways_2025.py
```

This creates a local `data/` folder and downloads the MBTA 2025 headways CSV files into it.

### 4. Validate the data folder

```powershell
py validate_data_folder.py
```

This checks that the expected CSV files are present before building the database.

### 5. Build the DuckDB database

```powershell
py setup_db.py
```

This creates the local database file:

```text
headways.duckdb
```

### 6. Run the Flask app

```powershell
py app.py
```

Open the app in your browser:

```text
http://127.0.0.1:5001
```

## Data Notes

The dataset is too large to store directly in the GitHub repository. Instead, this project includes scripts that download and validate the data locally after cloning.

The following files are generated locally and are not required in the GitHub repository:

```text
data/*.csv
headways.duckdb
```

## Main Features

- Headway distribution visualizations
- GLX vs. non-GLX Green-E comparison
- Missingness analysis
- Terminal-stop filtering
- Hour-of-day breakdowns
- Weekday vs. weekend filtering
- Direction-based comparison
- Long-gap event analysis

## Team

- Minseok Choi: 
- Anamol Kaspal