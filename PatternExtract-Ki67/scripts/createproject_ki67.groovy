import groovy.io.FileType
import java.awt.image.BufferedImage
import qupath.lib.images.servers.ImageServerProvider
import qupath.lib.gui.commands.ProjectCommands
import qupath.lib.gui.tools.GuiTools
import qupath.lib.gui.images.stores.DefaultImageRegionStore
import qupath.lib.gui.images.stores.ImageRegionStoreFactory
import qupath.lib.io.GsonTools
import static qupath.lib.scripting.QP.*


//Did we receive a string via the command line args keyword?
if (args.size() > 0)
    selectedDir = new File(args[0])
else
    selectedDir = Dialogs.promptForDirectory(null)

if (selectedDir == null)
    return

File directory = new File("C:/Users/siddh/Downloads/New folder/Project/ki67")


if (!directory.exists())
{
    println "No project directory, creating one!"
    directory.mkdirs()
}

// Create project
def project = Projects.createProject(directory , BufferedImage.class)

// Set up cache
def imageRegionStore = ImageRegionStoreFactory.createImageRegionStore(QuPathGUI.getTileCacheSizeBytes());


// Add files to the project
selectedDir.eachFileRecurse (FileType.FILES) { file ->
    def imagePath = file.getCanonicalPath()

    // Skip the project directory itself
    if (file.getCanonicalPath().startsWith(directory.getCanonicalPath() + File.separator))
        return


    // Is it a file we know how to read?
    def support = ImageServerProvider.getPreferredUriImageSupport(BufferedImage.class, imagePath)
    if (support == null)
        return

    // iterate through the scenes contained in the image file
    support.builders.eachWithIndex { builder, i ->
        sceneName = file.getName()
        if (support.builders.size() > 1)
            sceneName += " - Scene #" + (i+1)

        entry = project.addImage(builder)

        try {
            imageData = entry.readImageData()
        } catch (Exception ex) {
            println sceneName +" -- Error reading image data " + ex
            project.removeImage(entry, true)
            return
        }


        imageData.setImageType(ImageData.ImageType.BRIGHTFIELD_OTHER)

        // Adding image data to the project entry
        entry.saveImageData(imageData)

        // Write a thumbnail if we can
        entry.setThumbnail(ProjectCommands.getThumbnailRGB(imageData.getServer()))

        // Add an entry name (the filename)
        entry.setImageName(sceneName)
    }
}

// Changes should now be reflected in the project directory
project.syncChanges()