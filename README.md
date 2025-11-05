Results

The RS-DTM was compared to the GSI LiDAR data, using LiDAR survey data as ground-truth reference. Four river width classes were analyzed: 0.5-1 m, 1-2 m, 2-3 m, and 3-5 m. Model performance evaluation was carried out by using Mean Absolute Error (MAE), Root Mean Square Error (RMSE), coefficient of determination (R²), and Nash–Sutcliffe Efficiency (NSE).

Table X and Figure X present the accuracy of both RS-DTM and GSI LiDAR, with R² and NSE mostly above 0.85 for the entire range of river widths. For narrow channels (0.5–1 m), both RS-DTM and GSI LiDAR presented very high correlations (R² = 0.99; NSE = 0.97), although RS-DTM presented a slightly higher MAE of 0.98 m than that of GSI LiDAR at 0.68 m.

For river width classes 1–2 m and 2–3 m, RS-DTM performed consistently better than GSI LiDAR. RS-DTM yielded lower MAE of 1.12 and 1.33 m and lower RMSE of 2.44 and 2.23 m with higher R² (0.96 and 0.94) and NSE (0.92 and 0.95) while GSI LiDAR had R² = 0.91–0.89; NSE = 0.88–0.90.

By contrast, for the 3–5 m river width range, a reduction in the accuracy of both datasets was observed. The RS-DTM recorded an MAE and RMSE of 1.70 and 2.75 m with R² of 0.79 and NSE of 0.65. Correspondingly, GSI LiDAR generated slightly better R² (0.85) and NSE (0.61), but with a less consistent RMSE of 1.51 m.

Overall, RS-DTM achieved robust accuracy across most river width ranges and showed higher statistical performance within narrower channels (<3 m).

5. Discussion

The superior performance of the RS-DTM over GSI LiDAR in most river width ranges reflects its capability to capture fine-scale topographic variations through a combination of optical remote sensing and satellite-derived bathymetry. For instance, RS-DTM showed lower error and stronger correlation with LiDAR survey data in the 1-3 m width range, therefore being highly suitable for mapping small- to medium-scale channels.

Another interesting pattern in the results is that sometimes RS-DTM has a higher MAE but a lower RMSE compared to the GSI LiDAR dataset. The implication is that the RS-DTM errors are generally more homogeneously distributed with fewer outliers, whereas there might be some big local deviations in the GSI LiDAR that inflate the RMSE. Spatial interpolation and surface smoothing commonly used in the generation process of RS-DTM tend to avoid abrupt spikes in elevation but possibly introduce consistent small biases over the surface. The result could therefore be an increased average deviation (MAE) but reduced large errors that would increase RMSE.

As for the width range 0.5–1 m, similar reasons of vegetation interference are applicable, since the RS-DTM generated from the imagery captured on June 2022 falls in a period of high vegetation growth; thus, the vegetation-covered terrain surface is elevated, resulting in consistent positive elevation bias. Therefore, RS-DTM gives a higher MAE of 0.98 m for this width range. However, the LiDAR survey data from November 2024 represent a low-vegetation period, hence captured cleaner ground returns.

The lower R² and NSE values produced in the RS-DTM for the 3–5 m width range, 0.79 and 0.65 respectively, were largely due to the inclusion of bathymetric components derived using the Satellite-Derived Bathymetry method. This method, as explained in the earlier chapter, is optimized for shallow channels that have widths of approximately 3 m. In sections where the river gets wider or deeper, lesser optical penetration and increased turbidity can introduce vertical bias into the result, eventually increasing error values.

However, it is important to note that this comparison is not directly equivalent because the RS-DTM incorporates bathymetric depth information, whereas both the LiDAR survey and GSI LiDAR datasets represent only the water surface elevation. Airborne LiDAR systems—such as those used in the GSI dataset—typically employ near-infrared wavelengths, which cannot penetrate water. Consequently, in river areas, LiDAR returns are limited to the water surface, and regions without returns are commonly interpolated from surrounding elevations or flattened, producing an artificially smooth water surface. In contrast, the RS-DTM captures variations below the water surface through optical inversion, allowing it to represent the true channel bed morphology.

Consequently, the comparatively lower R² and NSE values of the RS-DTM in this range should not be seen as depicting lower accuracy, but rather as a consequence of different physical representations by the two datasets. Further investigations, including direct bathymetric surveys, would be needed to confirm the accuracy of the subaqueous topography provided by the RS-DTM and to establish the reliability of the SDB-derived depth estimates.
