###############################################################################
# generate_point_patterns.R
#
# PURPOSE:
#   1. Convert QuPath-exported CSV detections of Ki67-positive cells into
#      spatstat `ppp` objects, using a convex-hull window.
#   2. Replace the crude convex hull with manual QuPath annotations
#      provided as GeoJSON files, giving a more accurate observation window.
#   3. Quantify how many points fall outside the annotated window,
#      create diagnostic TIFF plots, and save clean `ppp` objects (.RDS)
#      for downstream spatial statistics.
#
# DEPENDENCIES  ---------------------------------------------------------------
# Install with:
#   install.packages(c("spatstat", "alphahull", "tidyverse",
#                      "sp", "maptools", "PBSmapping", "sf", "geojsonio"))
library(spatstat)   # core spatial point-pattern toolkit
library(alphahull)  # convex-hull helper
library(tidyverse)  # data wrangling
library(sp)         # spatial classes
library(maptools)   # spatial utilities
library(PBSmapping) # extra spatial tools
library(sf)         # modern simple-feature API
library(geojsonio)  # read/write GeoJSON
###############################################################################

## ----------------------------- USER PATHS ----------------------------------#
csv_dir      <- "C:/Users/siddh/Downloads/Ki67/CSV"        # raw CSV centroids
rds_out_dir  <- "C:/Users/siddh/Downloads/R_ki67/RDS/"     # initial ppp RDS
geojson_dir  <- "C:/Users/siddh/Downloads/Ki67/geoJSON/"   # QuPath annotations
final_rdsdir <- "C:/Users/siddh/Downloads/R_ki67/final/"   # cleaned ppp RDS
img_out_dir  <- "C:/Users/siddh/Downloads/R_ki67/Images/"  # diagnostic TIFFs
log_txt      <- "C:/Users/siddh/Downloads/ki67_R_Data.txt" # overall log
log_1p       <- "C:/Users/siddh/Downloads/ki67_R_Data_1p.txt" # >1 % outside
log_5p       <- "C:/Users/siddh/Downloads/ki67_R_Data_5p.txt" # >5 % outside
## ---------------------------------------------------------------------------#

###############################################################################
# PART 1 – CSV → initial ppp object (convex-hull window)
###############################################################################

csv_files <- list.files(path = csv_dir, full.names = TRUE)

for (file_path in csv_files) {

  # --------- read detections -------------------------------------------------
  raw        <- read.csv(file_path, sep = "\t")
  sample_id  <- str_split(file_path, "/")[[1]][7]   # assumes fixed depth
  message("Processing: ", sample_id)

  # --------- build data frame of centroids ----------------------------------
  df <- tibble(
    x     = raw$Centroid.X.µm,
    y     = raw$Centroid.Y.µm,
    label = raw$Class
  )

  # --------- create convex-hull window and ppp ------------------------------
  win <- convexhull.xy(df$x, df$y)
  pp  <- as.ppp(df, W = win, marks = data.frame(df$label))

  # --------- quick visual check ---------------------------------------------
  plot(pp, cex = 0.2, main = sample_id)

  # --------- save initial RDS -----------------------------------------------
  saveRDS(pp, file = paste0(rds_out_dir, sample_id, ".RDS"))
}

###############################################################################
# PART 2 – Replace window with precise GeoJSON annotation
###############################################################################

geojson_files <- list.files(geojson_dir, full.names = TRUE)
scount1 <- 0  # counter: >1 % points outside
scount5 <- 0  # counter: >5 % points outside

for (gj in geojson_files) {

  filename <- basename(gj)                   # e.g. "NUH_6.geojson"
  message("Annotating: ", filename)

  # --------- read GeoJSON and merge polygons --------------------------------
  poly_sp <- geojson_read(gj, what = "sp")            # SpatialPolygonsDataFrame
  poly_list <- slot(as(poly_sp, "SpatialPolygons"), "polygons")
  winlist   <- lapply(poly_list, function(z) as.owin(SpatialPolygons(list(z))))
  win       <- Reduce(union.owin, winlist)            # merged window

  # --------- fetch matching ppp object --------------------------------------
  rds_path <- file.path(rds_out_dir,
                        paste0(tools::file_path_sans_ext(filename), ".RDS"))
  pp <- readRDS(rds_path)

  # --------- rescale coordinates (×2) to match annotation units -------------
  new_pp <- ppp(x = pp$x * 2,
                y = pp$y * 2,
                window = win,
                marks  = pp$marks)

  # --------- QC: how many points fell outside? ------------------------------
  outside <- pp$n - npoints(new_pp)
  pct_out <- round(outside / pp$n * 100, 2)
  msg <- paste(filename,
               "Total points:", pp$n,
               "Points outside:", outside,
               "Percentage:", pct_out)
  message(msg)
  cat(msg, "\n", file = log_txt, append = TRUE)

  # --------- threshold logs --------------------------------------------------
  if (pct_out > 1) { scount1 <- scount1 + 1
    cat(msg, "\n", file = log_1p, append = TRUE) }
  if (pct_out > 5) { scount5 <- scount5 + 1
    cat(msg, "\n", file = log_5p, append = TRUE) }

  # --------- diagnostic TIFF -------------------------------------------------
  tiff(file = file.path(img_out_dir,
                        paste0(tools::file_path_sans_ext(filename), ".tiff")),
       compression = "lzw")
  plot.ppp(new_pp, main = filename, cex = 0.3)
  dev.off()

  # --------- save clean ppp --------------------------------------------------
  saveRDS(new_pp,
          file = file.path(final_rdsdir,
                           paste0(tools::file_path_sans_ext(filename), ".RDS")))
}

# --------------------------------------------------------------------------- #
# Summary counters
print(paste(">1% outside:", scount1, "samples"))
print(paste(">5% outside:", scount5, "samples"))
###############################################################################
