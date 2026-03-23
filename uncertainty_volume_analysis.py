#!/usr/bin/env python3
"""
Uncertainty-aware volumetric change analysis for multi-temporal DTM rasters.

This script:
1) Loads and validates a time-ordered stack of DTM GeoTIFF files.
2) Reads per-raster uncertainty (sigma) values from CSV.
3) Runs Monte Carlo perturbations with Gaussian noise.
4) Computes cumulative DoD and volume relative to first timestep.
5) Saves detailed and summary CSV outputs.
6) Generates:
   - time series plot with uncertainty band (+/- 1 std)
   - histogram of final timestep volume distribution
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import Affine


DATE_PATTERN = re.compile(r"^(\d{8})_.*\.tif$", re.IGNORECASE)


@dataclass(frozen=True)
class RasterInfo:
    """Container for one raster timestep."""

    path: Path
    date: datetime
    filename: str


def parse_date_from_filename(filename: str) -> datetime:
    """Extract YYYYMMDD date from filename and return a datetime object."""
    match = DATE_PATTERN.match(filename)
    if not match:
        raise ValueError(
            f"Filename '{filename}' does not match expected pattern YYYYMMDD_XXXXX.tif"
        )
    return datetime.strptime(match.group(1), "%Y%m%d")


def load_sigma_csv(csv_path: Path) -> Dict[str, float]:
    """
    Load sigma values from CSV and return a mapping: filename -> sigma.

    Required CSV columns:
      - filename
      - sigma
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Sigma CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required_cols = {"filename", "sigma"}
    if not required_cols.issubset(df.columns):
        raise ValueError(
            f"Sigma CSV must contain columns {required_cols}, got {set(df.columns)}"
        )

    df["filename"] = df["filename"].astype(str)
    df["sigma"] = pd.to_numeric(df["sigma"], errors="coerce")

    if df["sigma"].isna().any():
        bad_rows = df[df["sigma"].isna()]["filename"].tolist()
        raise ValueError(f"Invalid sigma values for files: {bad_rows}")

    if (df["sigma"] < 0).any():
        bad_rows = df[df["sigma"] < 0]["filename"].tolist()
        raise ValueError(f"Negative sigma values are not allowed. Files: {bad_rows}")

    sigma_map = dict(zip(df["filename"], df["sigma"]))
    return sigma_map


def _collect_raster_files(raster_dir: Path) -> List[RasterInfo]:
    """Find GeoTIFF files in folder and sort by date from filename."""
    if not raster_dir.exists():
        raise FileNotFoundError(f"Raster folder not found: {raster_dir}")

    tif_paths = sorted(raster_dir.glob("*.tif"))
    if not tif_paths:
        raise FileNotFoundError(f"No .tif files found in folder: {raster_dir}")

    rasters: List[RasterInfo] = []
    for p in tif_paths:
        d = parse_date_from_filename(p.name)
        rasters.append(RasterInfo(path=p, date=d, filename=p.name))

    rasters.sort(key=lambda r: r.date)
    return rasters


def load_rasters(
    raster_dir: Path,
    sigma_map: Dict[str, float],
) -> Tuple[np.ndarray, List[datetime], List[str], np.ndarray, float]:
    """
    Load raster stack and validate consistency.

    Returns
    -------
    stack : np.ndarray
        Shape (T, H, W), float64 with nodata represented as np.nan.
    times : list[datetime]
        Sorted timestep dates.
    filenames : list[str]
        Sorted file names corresponding to stack.
    sigmas : np.ndarray
        Sigma value per timestep, shape (T,).
    pixel_area : float
        Pixel area from affine transform (in CRS units squared).
    """
    rasters = _collect_raster_files(raster_dir)

    missing_sigma = [r.filename for r in rasters if r.filename not in sigma_map]
    if missing_sigma:
        raise ValueError(
            "Missing sigma values for raster files: "
            + ", ".join(missing_sigma)
            + ". Add them to sigma CSV."
        )

    arrays: List[np.ndarray] = []
    times: List[datetime] = []
    filenames: List[str] = []
    sigmas: List[float] = []

    ref_shape = None
    ref_crs = None
    ref_transform: Affine | None = None
    ref_res = None

    for idx, rinfo in enumerate(rasters):
        with rasterio.open(rinfo.path) as ds:
            if ds.count != 1:
                raise ValueError(f"Raster must be single-band: {rinfo.path}")

            data = ds.read(1).astype(np.float64)
            nodata = ds.nodata

            if nodata is not None:
                data[data == nodata] = np.nan
            else:
                # Preserve pre-existing NaN values if any.
                data[~np.isfinite(data)] = np.nan

            if idx == 0:
                ref_shape = ds.shape
                ref_crs = ds.crs
                ref_transform = ds.transform
                ref_res = ds.res
            else:
                if ds.shape != ref_shape:
                    raise ValueError(
                        f"Shape mismatch for {rinfo.filename}: {ds.shape} != {ref_shape}"
                    )
                if ds.crs != ref_crs:
                    raise ValueError(
                        f"CRS mismatch for {rinfo.filename}: {ds.crs} != {ref_crs}"
                    )
                if ds.transform != ref_transform:
                    raise ValueError(
                        f"Transform mismatch for {rinfo.filename}: "
                        f"{ds.transform} != {ref_transform}"
                    )
                if ds.res != ref_res:
                    raise ValueError(
                        f"Resolution mismatch for {rinfo.filename}: {ds.res} != {ref_res}"
                    )

            arrays.append(data)
            times.append(rinfo.date)
            filenames.append(rinfo.filename)
            sigmas.append(float(sigma_map[rinfo.filename]))

    if ref_transform is None:
        raise RuntimeError("No rasters loaded.")

    pixel_area = abs(ref_transform.a * ref_transform.e)
    stack = np.stack(arrays, axis=0)
    return stack, times, filenames, np.array(sigmas, dtype=np.float64), pixel_area


def compute_volume(dod: np.ndarray, pixel_area: float) -> float:
    """Compute volume as sum(DoD * pixel_area), ignoring NaN cells."""
    return float(np.nansum(dod) * pixel_area)


def run_monte_carlo(
    stack: np.ndarray,
    sigmas: np.ndarray,
    pixel_area: float,
    n_simulations: int,
    random_seed: int | None = None,
    progress: bool = True,
) -> np.ndarray:
    """
    Run Monte Carlo perturbation and volume time-series extraction.

    Parameters
    ----------
    stack : np.ndarray
        DTM stack of shape (T, H, W), with np.nan as nodata.
    sigmas : np.ndarray
        Sigma per timestep, shape (T,).
    pixel_area : float
        Cell area.
    n_simulations : int
        Number of Monte Carlo realizations.
    random_seed : int | None
        Optional random seed for reproducibility.
    progress : bool
        If True, print periodic progress updates.

    Returns
    -------
    volumes : np.ndarray
        Shape (n_simulations, T). Volume at each timestep, per simulation.
    """
    if n_simulations <= 0:
        raise ValueError("n_simulations must be > 0")
    if stack.ndim != 3:
        raise ValueError(f"Expected stack shape (T, H, W), got {stack.shape}")
    if stack.shape[0] != sigmas.shape[0]:
        raise ValueError("Number of timesteps in stack and sigmas must match")

    rng = np.random.default_rng(seed=random_seed)
    n_time, n_rows, n_cols = stack.shape
    volumes = np.zeros((n_simulations, n_time), dtype=np.float64)
    valid_masks = np.isfinite(stack)

    for sim in range(n_simulations):
        # Perturb baseline once per simulation.
        base = stack[0]
        base_mask = valid_masks[0]
        base_noise = rng.normal(0.0, sigmas[0], size=(n_rows, n_cols))
        base_perturbed = np.where(base_mask, base + base_noise, np.nan)
        volumes[sim, 0] = 0.0  # DoD against itself

        for t in range(1, n_time):
            dtm = stack[t]
            mask_t = valid_masks[t]
            noise_t = rng.normal(0.0, sigmas[t], size=(n_rows, n_cols))
            perturbed_t = np.where(mask_t, dtm + noise_t, np.nan)

            dod = perturbed_t - base_perturbed
            volumes[sim, t] = compute_volume(dod, pixel_area)

        if progress and ((sim + 1) % max(1, n_simulations // 10) == 0 or sim == n_simulations - 1):
            print(f"Simulation progress: {sim + 1}/{n_simulations}")

    return volumes


def summarize_results(
    volumes: np.ndarray, times: Sequence[datetime]
) -> pd.DataFrame:
    """Build summary DataFrame with mean, std, min, and max by timestep."""
    if volumes.shape[1] != len(times):
        raise ValueError("Volume columns must match number of timesteps.")

    summary = pd.DataFrame(
        {
            "time": [t.strftime("%Y-%m-%d") for t in times],
            "mean_volume": volumes.mean(axis=0),
            "std_volume": volumes.std(axis=0, ddof=1),
            "min_volume": volumes.min(axis=0),
            "max_volume": volumes.max(axis=0),
        }
    )
    return summary


def build_detailed_dataframe(
    volumes: np.ndarray, times: Sequence[datetime]
) -> pd.DataFrame:
    """Build long-format detailed simulation results DataFrame."""
    n_sim, n_time = volumes.shape
    time_labels = [t.strftime("%Y-%m-%d") for t in times]

    detailed = pd.DataFrame(
        {
            "simulation_id": np.repeat(np.arange(n_sim), n_time),
            "time": np.tile(time_labels, n_sim),
            "volume": volumes.reshape(-1),
        }
    )
    return detailed


def plot_results(
    summary_df: pd.DataFrame,
    detailed_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Generate and save requested plots."""
    output_dir.mkdir(parents=True, exist_ok=True)

    time_vals = pd.to_datetime(summary_df["time"])
    mean_vals = summary_df["mean_volume"].to_numpy()
    std_vals = summary_df["std_volume"].to_numpy()

    # Plot 1: mean volume time-series with +/- std uncertainty band.
    plt.figure(figsize=(10, 5))
    plt.plot(time_vals, mean_vals, marker="o", linewidth=2, label="Mean volume")
    plt.fill_between(
        time_vals,
        mean_vals - std_vals,
        mean_vals + std_vals,
        alpha=0.25,
        label="±1 std",
    )
    plt.xlabel("Time")
    plt.ylabel("Volume")
    plt.title("Volume Change Time Series with Uncertainty")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "volume_timeseries_uncertainty.png", dpi=150)
    plt.close()

    # Plot 2: histogram of final timestep volume across simulations.
    final_time = summary_df["time"].iloc[-1]
    final_vols = detailed_df.loc[detailed_df["time"] == final_time, "volume"].to_numpy()
    plt.figure(figsize=(8, 5))
    plt.hist(final_vols, bins=30, edgecolor="black", alpha=0.75)
    plt.xlabel("Volume")
    plt.ylabel("Frequency")
    plt.title(f"Final Timestep Volume Distribution ({final_time})")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / "final_timestep_volume_histogram.png", dpi=150)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Uncertainty-aware volumetric change analysis using Monte Carlo simulation."
    )
    parser.add_argument(
        "--raster-dir",
        type=Path,
        required=True,
        help="Folder containing DTM .tif files named YYYYMMDD_XXXXX.tif",
    )
    parser.add_argument(
        "--sigma-csv",
        type=Path,
        required=True,
        help="CSV with columns: filename,sigma",
    )
    parser.add_argument(
        "--n-simulations",
        type=int,
        default=200,
        help="Number of Monte Carlo simulations (default: 200)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs"),
        help="Directory for CSV and plot outputs (default: ./outputs)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional random seed for reproducibility",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress printing",
    )

    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading sigma CSV...")
    sigma_map = load_sigma_csv(args.sigma_csv)

    print("Loading rasters...")
    stack, times, filenames, sigmas, pixel_area = load_rasters(args.raster_dir, sigma_map)
    print(f"Loaded {len(filenames)} rasters.")
    print(f"Pixel area: {pixel_area:.6f}")

    print("Running Monte Carlo simulation...")
    volumes = run_monte_carlo(
        stack=stack,
        sigmas=sigmas,
        pixel_area=pixel_area,
        n_simulations=args.n_simulations,
        random_seed=args.seed,
        progress=not args.no_progress,
    )

    print("Building output tables...")
    summary_df = summarize_results(volumes, times)
    detailed_df = build_detailed_dataframe(volumes, times)

    summary_csv = args.output_dir / "volume_summary.csv"
    detailed_csv = args.output_dir / "volume_detailed.csv"
    summary_df.to_csv(summary_csv, index=False)
    detailed_df.to_csv(detailed_csv, index=False)

    print("Generating plots...")
    plot_results(summary_df, detailed_df, args.output_dir)

    print("Done.")
    print(f"Summary CSV:  {summary_csv}")
    print(f"Detailed CSV: {detailed_csv}")
    print(f"Plots:        {args.output_dir / 'volume_timeseries_uncertainty.png'}")
    print(f"              {args.output_dir / 'final_timestep_volume_histogram.png'}")


if __name__ == "__main__":
    main()
