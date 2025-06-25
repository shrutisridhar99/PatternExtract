import qupath.lib.io.GsonTools

import static qupath.lib.scripting.QP.*;

setImageType('BRIGHTFIELD_OTHER')
setColorDeconvolutionStains('{"Name" : "H-DAB default", "Stain 1" : "Hematoxylin", "Values 1" : "0.65111 0.70119 0.29049", "Stain 2" : "DAB", "Values 2" : "0.26917 0.56824 0.77759", "Background" : " 255 255 255"}')
resetSelection()

def json = """
{
  "pixel_classifier_type": "OpenCVPixelClassifier",
  "metadata": {
    "inputPadding": 0,
    "inputResolution": {
      "pixelWidth": {
        "value": 1.0,
        "unit": "px"
      },
      "pixelHeight": {
        "value": 1.0,
        "unit": "px"
      },
      "zSpacing": {
        "value": 1.0,
        "unit": "z-slice"
      },
      "timeUnit": "SECONDS",
      "timepoints": []
    },
    "inputWidth": 512,
    "inputHeight": 512,
    "inputNumChannels": 3,
    "outputType": "CLASSIFICATION",
    "outputChannels": [],
    "classificationLabels": {
      "0": {
        "name": "Region*",
        "colorRGB": -16777036
      },
      "1": {}
    }
  },
  "op": {
    "type": "data.op.channels",
    "colorTransforms": [
      {
        "stains": {
          "name": "H-DAB default",
          "stain1": {
            "r": 0.6511078297640718,
            "g": 0.7011930397459234,
            "b": 0.2904942598947397,
            "name": "Hematoxylin",
            "isResidual": false
          },
          "stain2": {
            "r": 0.2691668699565374,
            "g": 0.5682411699082456,
            "b": 0.7775931898744414,
            "name": "DAB",
            "isResidual": false
          },
          "stain3": {
            "r": 0.6330435352304447,
            "g": -0.7128599063057326,
            "b": 0.3018056269931407,
            "name": "Residual",
            "isResidual": true
          },
          "maxRed": 255.0,
          "maxGreen": 255.0,
          "maxBlue": 255.0
        },
        "stainNumber": 3
      }
    ],
    "op": {
      "type": "op.core.sequential",
      "ops": [
        {
          "type": "op.filters.gaussian",
          "sigmaX": 5.0,
          "sigmaY": 5.0
        },
        {
          "type": "op.threshold.constant",
          "thresholds": [
            -0.01
          ]
        }
      ]
    }
  }
}
"""
def thresholder = GsonTools.getInstance().fromJson(json, qupath.lib.classifiers.pixel.PixelClassifier.class)
createAnnotationsFromPixelClassifier(thresholder, 5000, 200, "INCLUDE_IGNORED")
runPlugin('qupath.lib.plugins.objects.FillAnnotationHolesPlugin', '{}')

def imageName = getCurrentServer().getMetadata().getName()
String name = imageName.split(".tiff")[0]
exportAllObjectsToGeoJson("C:/Users/siddh/Downloads/Ki67/geoJSON/" + name +".geojson", "EXCLUDE_MEASUREMENTS", "PRETTY_JSON", "FEATURE_COLLECTION")
