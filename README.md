You are an expert Python developer with geospatial analysis experience (rasterio, NumPy, pandas, matplotlib).

I already have a working Python script that performs Monte Carlo-based volumetric change analysis using multi-temporal DTM rasters.

Please EXTEND the existing code to include **cut and fill volume analysis**, while keeping the current structure clean and modular.

---

### NEW REQUIREMENTS: CUT & FILL ANALYSIS

#### 1. Definitions

* **Fill volume** = sum of positive DoD values
* **Cut volume** = sum of negative DoD values (report as positive magnitude)
* **Net volume** = fill − cut (already exists)

---

#### 2. Modify volume computation

Update or extend the volume computation function so that for each DoD it returns:

* net_volume
* cut_volume
* fill_volume

Use efficient NumPy operations:

* Fill → DoD > 0
* Cut → DoD < 0

---

#### 3. Monte Carlo output

During Monte Carlo simulation, store for each simulation and timestep:

* net_volume
* cut_volume
* fill_volume

Structure:

```text
simulation_id, time, net_volume, cut_volume, fill_volume
```

---

#### 4. Summary statistics

At the end, compute for each timestep:

* mean_net_volume

* std_net_volume

* min_net_volume

* max_net_volume

* mean_cut_volume

* std_cut_volume

* mean_fill_volume

* std_fill_volume

Output CSV format:

```text
time,
mean_net_volume,std_net_volume,min_net_volume,max_net_volume,
mean_cut_volume,std_cut_volume,
mean_fill_volume,std_fill_volume
```

---

#### 5. Plots

Add the following plots:

### (A) Net volume time series (already exists)

* Mean line
* ± standard deviation shaded band

### (B) Cut and Fill time series (NEW)

* Two lines:

  * Fill volume
  * Cut volume
* Optional: add ± std shading for both

### (C) Optional (preferred)

* Combined plot:

  * Net, Cut, Fill in one figure

### (D) Histogram (existing)

* Final timestep distribution (net volume)

---

#### 6. Code structure

* Keep functions modular:

  * compute_volume → extend or create new function (compute_cut_fill)
  * run_monte_carlo → store all 3 metrics
  * summarize_results → include all statistics

* Avoid pixel-wise loops (use NumPy masking)

---

#### 7. Output files

Save:

* volume_summary.csv (extended with cut/fill)
* volume_detailed.csv (extended structure)
* volume_timeseries_uncertainty.png
* cut_fill_timeseries.png (NEW)
* optional combined plot

---

#### 8. Maintain compatibility

* Do NOT break existing functionality
* Keep argument structure the same
* Ensure backward compatibility

---

### GOAL

The final script should support:

✔ Net volume
✔ Cut & fill volumes
✔ Uncertainty propagation (Monte Carlo)
✔ Publication-ready outputs (CSV + plots)

---

Please provide:

1. Updated Python code
2. Explanation of new functions/changes
3. Example outputs
