# Load relevant libraries
library(spatstat)
library(alphahull)
library(tidyverse)
library(sp)
library(maptools)
library(PBSmapping)
library(sf)
library(geojsonio)
##########################################################################
# This script will read and plot the RDS file
files <- list.files(path="C:/Users/siddh/Downloads/Ki67/CSV", full.names=TRUE)

for (i in 1:length(files)){
  read.file  <- read.csv(files[i] , sep="\t")
  name_file <- str_split(files[i] , "/")[[1]][7]
  print(name_file)
  df <- data.frame( x= read.file$Centroid.X.µm , y =read.file$Centroid.Y.µm, label=read.file$Class)
  w <- convexhull.xy(df$x, df$y)
  pp <- as.ppp(df , W=w , marks=data.frame(df$label))
  plot(pp , cex = 0.2, main="")
  title(name_file)
  # Saving the point patterns as RDS objects using an approximate convex window.plotted above
  saveRDS(pp, file = paste0("C:/Users/siddh/Downloads/R_ki67/RDS/" ,name_file, ".RDS"))
  
}
############################################################################
# After QuPath annotation and saving geojson annotations for each image...

geojson.list <- list.files("C:/Users/siddh/Downloads/Ki67/geoJSON/", full.names = TRUE)
scount1 <- 0
scount5 <- 0
for (j in geojson.list) {
  #print(basename(j))
  eq <- geojson_read(j, what='sp')
  y <- as(eq, "SpatialPolygons")
  p <- slot(y, "polygons")
  v <- lapply(p, function(z) { SpatialPolygons(list(z)) })
  winlist <- lapply(v, as.owin)
  win <- winlist[[1]]
  if (length(winlist) > 1) {
    for (i in seq(2, length(winlist))) {
      win <- union.owin(win, winlist[[i]])
    }
  }
  # identifying the image names and fetching corresponding RDS objects
  rds <- tools::file_path_sans_ext(j)
  rds.name <- basename(rds)
  filename <-  basename(rds)
  rds.fullpath <- paste("C:/Users/siddh/Downloads/R_ki67/RDS/", rds.name, ".RDS", sep="")
  pp <- readRDS(rds.fullpath)
  
  x.win <- pp$x *2
  y.win <- pp$y *2
  
  new.owin.pp <- ppp(x = x.win, y=y.win, window = win)
  # new.owin.ppp is the new point pattern. Convex window replaced with annotations from geojson. 
  new.owin.ppp <- ppp(x = x.win, y=y.win, window = win , marks=pp$marks)
  points.outside <- pp$n-npoints(new.owin.pp)
  print(paste(filename, "Total points:", pp$n,"Points outside:", points.outside,
              "Percentage of points lying outside", round((points.outside/pp$n)*100,2)))
  tiff.name <- paste("C:/Users/siddh/Downloads/R_ki67/Images/",filename,".tiff",sep = "")
  tiff(tiff.name, compression = "lzw")
  plot.ppp(new.owin.pp, main = filename , cex=0.3)
  dev.off()
  cat(paste(filename, "Total points:", pp$n,"Points outside:", points.outside,
            "Percentage of points lying outside", round((points.outside/pp$n)*100,2) , "\n"),file="C:/Users/siddh/Downloads/ki67_R_Data.txt",append=TRUE)
  
  if (((points.outside/pp$n)*100) > 1){
    scount1 = scount1 + 1
    cat(paste(filename, "Total points:", pp$n,"Points outside:", points.outside,
              "Percentage of points lying outside", round((points.outside/pp$n)*100,2) , "\n"),file="C:/Users/siddh/Downloads/ki67_R_Data_1p.txt",append=TRUE)}
  if (((points.outside/pp$n)*100) > 5){
    scount5 = scount5 + 1
    cat(paste(filename, "Total points:", pp$n,"Points outside:", points.outside,
              "Percentage of points lying outside", round((points.outside/pp$n)*100,2) , "\n"),file="C:/Users/siddh/Downloads/ki67_R_Data_5p.txt",append=TRUE)}
  
  # save new.owin.pp for further spatial analysis
  saveRDS(new.owin.ppp, file = paste0("C:/Users/siddh/Downloads/R_ki67/final/" ,strsplit(basename(j) , ".geojson")[[1]], ".RDS"))
}
print(scount1)
print(scount5)