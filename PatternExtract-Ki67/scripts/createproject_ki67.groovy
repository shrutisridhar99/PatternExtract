/*****************************************************************************************
 * build_qupath_project.groovy
 *
 * PURPOSE
 *   Batch-import all images from a user-chosen directory into a new (or existing)
 *   QuPath project, handling multi-scene images and generating thumbnails.
 *
 * USAGE
 *   Run from QuPath (Groovy script runner) or via CLI:
 *       qupath script build_qupath_project.groovy "D:/WSI_to_import"
 *
 *   If no CLI argument is supplied, the script opens a folder-picker dialog.
 *
 *****************************************************************************************/

// -------------------- Imports -----------------------------------------------------------
import groovy.io.FileType
import java.awt.image.BufferedImage
import qupath.lib.images.servers.ImageServerProvider
import qupath.lib.gui.commands.ProjectCommands
import qupath.lib.gui.tools.GuiTools
import qupath.lib.gui.images.stores.DefaultImageRegionStore
import qupath.lib.gui.images.stores.ImageRegionStoreFactory
import qupath.lib.io.GsonTools
import static qupath.lib.scripting.QP.*   // QuPath scripting helpers

// -------------------- 1. Select input directory -----------------------------------------
File selectedDir
if (args.size() > 0) {
    // Directory path passed via command-line argument
    selectedDir = new File(args[0])
} else {
    // Fallback: open a GUI dialog
    selectedDir = Dialogs.promptForDirectory(null)
}
if (selectedDir == null)          // user cancelled
    return

// -------------------- 2. Define/prepare project folder ----------------------------------
File directory = new File("C:/Users/siddh/Downloads/New folder/Project/ki67")
if (!directory.exists()) {
    println "No project directory found — creating one!"
    directory.mkdirs()
}

// -------------------- 3. Create (or open) a QuPath project ------------------------------
def project = Projects.createProject(directory, BufferedImage.class)

// -------------------- 4. Initialise tile-cache (better performance) ---------------------
def imageRegionStore = ImageRegionStoreFactory.createImageRegionStore(
        QuPathGUI.getTileCacheSizeBytes()
)

// -------------------- 5. Recursively add images to project ------------------------------
selectedDir.eachFileRecurse(FileType.FILES) { file ->
    def imagePath = file.getCanonicalPath()

    // Skip files that are *inside* the project directory itself
    if (imagePath.startsWith(directory.getCanonicalPath() + File.separator))
        return

    // Ask QuPath if it can read this file format
    def support = ImageServerProvider.getPreferredUriImageSupport(BufferedImage.class, imagePath)
    if (support == null)
        return   // Unsupported filetype → skip

    // For multi-scene formats (e.g. some .svs) iterate over each scene
    support.builders.eachWithIndex { builder, i ->

        // Derive a display name
        String sceneName = file.getName()
        if (support.builders.size() > 1)
            sceneName += " - Scene #" + (i + 1)

        // Add to project & get entry handle
        def entry = project.addImage(builder)

        // Read image metadata (can fail for corrupt images)
        try {
            def imageData = entry.readImageData()
            imageData.setImageType(ImageData.ImageType.BRIGHTFIELD_OTHER)   // generic brightfield
            entry.saveImageData(imageData)                                  // persist changes
            entry.setThumbnail(ProjectCommands.getThumbnailRGB(imageData.getServer()))
            entry.setImageName(sceneName)
        } catch (Exception ex) {
            println "$sceneName -- Error reading image data: $ex"
            project.removeImage(entry, true)                               // clean up bad entry
        }
    }
}

// -------------------- 6. Flush all changes to disk --------------------------------------
project.syncChanges()
println "✔ Project updated: ${directory}"
