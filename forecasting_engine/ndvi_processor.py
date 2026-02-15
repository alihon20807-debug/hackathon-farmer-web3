"""
NDVI Satellite Data Processor
==============================
Extracts weekly mean NDVI statistics from multi-band GeoTIFF files
(Nashik onion growing region) and produces a clean CSV for the
forecasting engine.

Each TIF has 52 bands (one per ISO week).  Two spatial tiles per year
are averaged together to produce a single regional mean.

Output: ndvi_weekly_nashik.csv  (ds, ndvi_mean, ndvi_std, ndvi_anomaly)
"""

import os
import glob
import warnings
import numpy as np
import pandas as pd
import torch

warnings.filterwarnings("ignore")

try:
    import rasterio
except ImportError:
    raise ImportError("rasterio is required — run: pip install rasterio")

# ---------- paths ----------
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
NDVI_DIR   = os.path.join(BASE_DIR, "..", "NVDI satellite Onion")
OUTPUT_CSV = os.path.join(BASE_DIR, "ndvi_weekly_nashik.csv")

YEARS = [2023, 2024, 2025]


# Check for CUDA availability at module level
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Using device for NDVI processing: {device}")

def _band_stats(dataset, band_idx: int) -> tuple:
    """Read a single band and compute mean / std over valid NDVI pixels.

    Excludes:
    - NaN values
    - Values outside [-1, 1] (invalid NDVI)
    - Values very close to 0.0 (cloud-mask fill — real vegetation NDVI > 0.01)
    """
    data = dataset.read(band_idx)             # shape (H, W), float32
    
    # Convert to tensor and move to device
    try:
        tensor_data = torch.from_numpy(data).to(device)
    except Exception as e:
        print(f"Error moving to GPU: {e}")
        return np.nan, np.nan
    
    # Create masks on GPU
    # Exclude NaN, values outside [-1, 1], and small values near 0 (cloud mask checks)
    # Note: isnan is available in torch. 
    # Logic: (~isnan) & (>= -1) & (<= 1) & (abs > 0.01)
    
    mask = (
        (~torch.isnan(tensor_data)) &
        (tensor_data >= -1.0) & 
        (tensor_data <= 1.0) &
        (torch.abs(tensor_data) > 0.01)
    )
    
    valid_pixels = tensor_data[mask]
    
    if valid_pixels.numel() < 100:   # too few pixels = unreliable
        return np.nan, np.nan
        
    # Compute stats on GPU
    mean_val = torch.mean(valid_pixels).item()
    std_val = torch.std(valid_pixels).item()
    
    return float(mean_val), float(std_val)


def _iso_week_start(year: int, week: int) -> pd.Timestamp:
    """Return the Monday of a given ISO year / week number."""
    # pd.Timestamp.fromisocalendar needs (year, week, day)
    return pd.Timestamp.fromisocalendar(year, max(week, 1), 1)


def extract_year(year: int) -> pd.DataFrame:
    """Process all tiles for one year and return a DataFrame of weekly stats."""
    year_dir = os.path.join(NDVI_DIR, str(year))
    tif_files = sorted(glob.glob(os.path.join(year_dir, "*.tif")))

    if not tif_files:
        print(f"  ⚠ No TIF files found for {year} in {year_dir}")
        return pd.DataFrame()

    print(f"  Found {len(tif_files)} tile(s) for {year}")

    # Collect stats from every tile, then average
    # Each tile has the same 52 bands
    num_bands = None
    tile_means = []   # list of arrays, one per tile
    tile_stds  = []

    for tif_path in tif_files:
        fname = os.path.basename(tif_path)
        print(f"    Reading {fname} …")
        with rasterio.open(tif_path) as ds:
            if num_bands is None:
                num_bands = ds.count
            means = np.full(ds.count, np.nan)
            stds  = np.full(ds.count, np.nan)
            for b in range(1, ds.count + 1):      # rasterio bands are 1-indexed
                m, s = _band_stats(ds, b)
                means[b - 1] = m
                stds[b - 1]  = s
        tile_means.append(means)
        tile_stds.append(stds)

    # Average across tiles (weighted equally — they are spatial tiles of
    # the same region, just horizontally split)
    all_means = np.nanmean(np.stack(tile_means, axis=0), axis=0)   # (52,)
    all_stds  = np.nanmean(np.stack(tile_stds,  axis=0), axis=0)

    # Build DataFrame with weekly dates
    rows = []
    for week_idx in range(num_bands):
        iso_week = week_idx + 1        # bands 0–51 → ISO weeks 1–52
        try:
            ds_date = _iso_week_start(year, iso_week)
        except ValueError:
            continue
        rows.append({
            "ds":        ds_date,
            "ndvi_mean": round(all_means[week_idx], 6),
            "ndvi_std":  round(all_stds[week_idx], 6),
        })

    return pd.DataFrame(rows)


def compute_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    """Add ndvi_anomaly = deviation from multi-year weekly climatology."""
    df = df.copy()
    df["iso_week"] = df["ds"].dt.isocalendar().week.astype(int)
    climatology = df.groupby("iso_week")["ndvi_mean"].mean()
    df["ndvi_anomaly"] = df.apply(
        lambda r: round(r["ndvi_mean"] - climatology.get(r["iso_week"], r["ndvi_mean"]), 6),
        axis=1,
    )
    df.drop(columns=["iso_week"], inplace=True)
    return df


def main():
    print("=" * 60)
    print("NDVI Satellite Data Processor")
    print("=" * 60)

    all_dfs = []
    for year in YEARS:
        print(f"\n📡 Processing year {year} …")
        year_df = extract_year(year)
        if not year_df.empty:
            all_dfs.append(year_df)
            print(f"  ✅ {len(year_df)} weeks extracted (NDVI mean range: "
                  f"{year_df['ndvi_mean'].min():.4f} – {year_df['ndvi_mean'].max():.4f})")

    if not all_dfs:
        print("\n❌ No data extracted.  Check that NVDI satellite Onion/ exists.")
        return

    combined = pd.concat(all_dfs, ignore_index=True).sort_values("ds").reset_index(drop=True)

    # Interpolate missing/NaN weeks (cloudy monsoon periods)
    n_missing = combined['ndvi_mean'].isna().sum()
    if n_missing > 0:
        print(f"\n🔧 Interpolating {n_missing} cloud-affected weeks…")
        combined['ndvi_mean'] = combined['ndvi_mean'].interpolate(method='linear').bfill().ffill()
        combined['ndvi_std']  = combined['ndvi_std'].interpolate(method='linear').bfill().ffill()

    # Anomaly: deviation from multi-year weekly climatology
    combined = compute_anomaly(combined)

    # Save
    combined.to_csv(OUTPUT_CSV, index=False)
    print(f"\n💾 Saved {len(combined)} rows → {OUTPUT_CSV}")
    print(f"  NDVI mean range: {combined['ndvi_mean'].min():.4f} – {combined['ndvi_mean'].max():.4f}")
    print(f"  Zero rows remaining: {(combined['ndvi_mean'] == 0).sum()}")
    print(combined.head(10).to_string(index=False))
    print("…")
    print(combined.tail(5).to_string(index=False))
    print("\nDone!")


if __name__ == "__main__":
    main()
