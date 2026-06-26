# Continuous Surface Modeling

An ArcGIS Pro toolbox and Python script for generating a continuous gradient raster from polygon features using user-specified polygon values, with optional point features to locally influence the resulting surface.

## Overview

The **Polygon to Gradient Raster** tool generates a continuous raster from polygon features representing categorical or numeric values. Unlike traditional polygon-to-raster conversion, which produces abrupt transitions at polygon boundaries, this tool applies multiple focal statistics operations to create smoother, more natural transitions while preserving the overall spatial patterns of the source data.
Optional point features can be incorporated to locally influence the modeled surface, allowing known locations or observations to refine the final raster.
The tool is intended for situations where mapped polygon values represent generalized conditions and a continuous surface better reflects real-world transitions.

---

## Features

- Generate continuous gradient rasters from polygon features
- Preserve broad spatial patterns while smoothing polygon boundaries
- Multiple focal statistics operations
- Optional point feature integration
- Automatic output cell size calculation from visualization map scale
- Optional custom output cell size override
- ArcGIS Pro toolbox interface
- Standalone Python implementation included
---

## Repository Contents

| File | Description |
|------|-------------|
| `ContinuousSurfaceModeling.atbx` | ArcGIS Pro toolbox containing the **Polygon to Gradient Raster** tool |
| `PolygonToGradientRaster.py` | Standalone Python implementation |
| `docs/` | Documentation and methodology |
| `examples/` | Sample data and example outputs |
---

## Requirements

- ArcGIS Pro 3.6.4 onwards
- ArcGIS Pro Spatial Analyst Extension
- Python environment included with ArcGIS Pro

---

## Installation

1. Clone or download this repository.
2. Open ArcGIS Pro.
3. Add **ContinuousSurfaceModeling.atbx** to your project.
4. Open **Polygon to Gradient Raster**.

---

## Using the Tool

### Required Parameters

#### Input Polygon Features
Polygon feature layer, feature class, or shapefile containing the values to be modeled.

#### Field
Attribute field used to generate the gradient raster. Supported field types are **Short**, **Long**, **Float**, **Double**, and **Text**. If a **Text** field is used, all records must contain numeric values.

#### Output Raster
Output raster dataset representing the continuous gradient surface generated from the input polygon values and optional point features.

#### Map Scale
The intended visualization scale of the output raster. By default, the output cell size is automatically calculated using the following relationship:

> **Output Cell Size = Map Scale / 2000**

<br>

### Optional Parameters

#### Input Points
Point feature layer, feature class, or shapefile used to locally influence the output raster.

#### Points Value Field
Attribute field containing point values. Supported field types are **Short**, **Long**, **Float**, **Double**, and **Text**. If a **Text** field is used, all records must contain numeric values.

Either a **Points Value Field** or a **Points Value** must be provided.

#### Points Value
Constant numeric value assigned to all input points when a point attribute field is not specified.

#### Use Custom Cell Size
Enables manual specification of the output cell size instead of automatically deriving it from the map scale.

#### Output Cell Size
The output raster cell size in map units.

- When **Use Custom Cell Size** is enabled, the specified cell size is used.
- Otherwise, the output cell size is automatically calculated from the map scale.
- Smaller cell sizes produce finer detail but increase processing time and output file size.

##### Recommended Output Cell Sizes

The recommended output cell size depends on the intended map scale.

| Map Scale | Recommended Cell Size |
|------------|----------------------|
| 1:10,000 | 5 m |
| 1:20,000 | 10 m |
| 1:50,000 | 25 m |

