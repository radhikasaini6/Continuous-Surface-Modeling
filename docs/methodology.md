## Methodology

The tool generates a continuous raster surface through a combination of raster conversion, focal statistics smoothing, and optional point-based refinement.

### 1. Data Preparation
- Input polygons are dissolved based on the selected attribute field.
- Optional point features are converted into buffered raster inputs.


### 2. Raster Conversion
The dissolved polygons (and optional point-derived buffers) are converted into a raster surface.


### 3. Smoothing Workflow

#### Without Point Features
Two focal statistics operations are applied using different window sizes:
- Small window smoothing
- Large window smoothing  

The results are averaged to produce the final surface.


#### With Point Features
When points are included, they are iteratively integrated into the smoothing process:

- Point buffers are merged into the raster at multiple stages
- Focal statistics are applied between these integration steps
- The surface is refined through repeated smoothing and point reinforcement

This approach allows point observations to influence both local and regional surface trends.


### 4. Output
The final raster represents a continuous gradient surface that preserves polygon-based trends while incorporating localized variation where point data is available.

