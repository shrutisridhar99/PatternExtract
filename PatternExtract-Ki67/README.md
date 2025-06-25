# PatternExtract ‒ Ki67 Spatial Point Pattern Pipeline

**PatternExtract** is an automated pipeline to extract and convert detections from whole‑slide images or tissue microarrays into spatial point pattern (`ppp`) objects using OpenCV, QuPath, and R's `spatstat`.

## Workflow
1. Pre‑process images in Python (OpenCV)
2. Create GeoJSON in QuPath (Groovy)
3. Build `ppp` objects in R


See `Full_program_run_Ki67.ipynb` for a runnable notebook.

## Requirements
* Python ≥ 3.9 — install with `pip install -r requirements.txt`
* R ≥ 4.2 with `spatstat`
* QuPath ≥ 0.3.x

## Quick start
```bash
jupyter nbconvert --to notebook --execute Full_program_run_Ki67.ipynb
```

## License
MIT © 2025
