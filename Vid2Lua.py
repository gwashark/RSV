import os, pathlib, cv2, time, shutil

from colorama import Fore
from PIL import Image
from sys import argv

def convert(vidPath: str, config: dict={
    "fps": 60,
    "width": 512,
    "height": 256,
    "tempDir": "V2LTemp",
    "name": "vid2lua"
}):
    try:
        path = pathlib.Path(vidPath)
        tempDir = config["tempDir"] or "V2LTemp"

        if not os.path.isfile(path):
            raise FileNotFoundError("Video Path Doesn't Exist.")
        elif os.path.isdir(path):
            raise IsADirectoryError("Video Path Is A Directory.")
        if not os.path.isdir(tempDir):
            os.mkdir(tempDir)
        elif os.path.isdir(tempDir):
            shutil.rmtree(pathlib.Path(os.getcwd() + "/" +tempDir))
            os.mkdir(tempDir)
        
        cap = cv2.VideoCapture()
        cap.open(str(path))
        if config["fps"] is int:
            cap.set(cv2.CAP_PROP_FPS, config["fps"])
        else:
            cap.set(cv2.CAP_PROP_FPS, 60)
        frame_count = 0
        ret, frame = cap.read()
        os.mkdir(os.path.join(os.getcwd(), tempDir, "frames"))
        frame_interval = int(cap.get(cv2.CAP_PROP_FPS))
        while ret:
            frame_path = os.path.join(os.getcwd(), tempDir, "frames", f"{frame_count}.png")
            cv2.imwrite(frame_path, frame)
            for _ in range(frame_interval - 1):
                ret, _ = cap.read()
                if not ret:
                    break
            ret, frame = cap.read()
            frame_count += 1
        cap.release()

        if config["width"] > 1024 or config["height"] > 1024:
            raise ValueError("Width and Height Can't Be Greater Than 1024.")

        width = config["width"] or 512
        height = config["height"] or 256

        for filename in os.listdir(os.path.join(os.getcwd(), tempDir, "frames")):
            with Image.open(os.path.join(os.getcwd(), tempDir, "frames", filename)) as img:
                img = img.resize((width, height))
                img.save(os.path.join(os.getcwd(), tempDir, "frames", filename))

        IMAGE_SIZE = [1024, 1024]
        LUA_HEADER = """
        local Spritesheet = require(script:FindFirstAncestorWhichIsA("ModuleScript").Spritesheet)

        local {name} = {{}}
        {name}.__index = {name}
        setmetatable({name}, Spritesheet)

        {varibles}

        function {name}.new()
            local new{name} = Spritesheet.new()
            setmetatable(new{name}, {name})

        """

        class node:
            def __init__(self, position, size):
                self.image = None
                self.size = size; self.position = position
                self.down = None
                self.right = None

        def sortImages(images):
            images.sort(key=lambda img: img.size[0] * img.size[1], reverse=True)
        
        def loadImages(path):
            sprites = []
            for file in os.listdir(path):
                file_path = os.path.join(path, file)
                if os.path.isfile(file_path):
                    try:
                        loadedImage = Image.open(file_path)
                        sprites.append(loadedImage)
                    except:
                        pass
            return sprites

        def findTreeSpot(trees, img):
            def findTreeSpotHelper(node, img):
                if node.image is not None:
                    return findTreeSpotHelper(node.right, img) or findTreeSpotHelper(node.down, img)
                elif (node.size[0] >= img.size[0] and node.size[1] >= img.size[1]):
                    return node
                else:
                    return None
            found = None
            for tree in trees:
                found = findTreeSpotHelper(tree, img)
                if found:
                    break
            if found:
                return found
            else:
                found = node([0,0],IMAGE_SIZE[:])
                trees.append(found)
                return found
        
        def getImageSize(current):
            if current is None:
                return [0,0]
            if current.image is None:
                return [0,0]
            right = getImageSize(current.right)
            down = getImageSize(current.down)
            
            curExtent = [current.image.size[0] + current.position[0], current.image.size[1] + current.position[1]]
            return [max(curExtent[0],right[0],down[0]), max(curExtent[1],right[1],down[1])]
        
        def packImagesRecursive(current, spriteSheet):
            if current is None:
                return
            if current.image is None:
                return
            spriteSheet.paste(current.image, box=(current.position[0],current.position[1]))
            packImagesRecursive(current.right, spriteSheet)
            packImagesRecursive(current.down, spriteSheet)

        def getOutputFolder(path):
            name = "/output"
            ext = 0
            while os.path.exists(path + name + str(ext)):
                ext += 1

            os.mkdir(path + name + str(ext))
            return path + name + str(ext)

        def packImages(trees,name,output):
            for idx,tree in enumerate(trees):
                size = getImageSize(tree)
                spriteSheet = Image.new(mode="RGBA", size=(size[0],size[1]))
                packImagesRecursive(tree,spriteSheet)
                if len(trees) == 1:
                    idx = ""
                filePath = output + "/"  + name + str(idx) + ".png"
                spriteSheet.save(filePath)

        def buildTree(trees, sprites):
            for img in sprites:
                if img.size[0] > IMAGE_SIZE[0] or img.size[1] > IMAGE_SIZE[1]:
                    raise Exception("All images must be <= 1024 pixels in both axes" + img.filename + " is too big")
                else:
                    foundNode = findTreeSpot(trees, img)
                    foundNode.image = img
                    foundNode.right = node(
                            [foundNode.position[0] + img.size[0], foundNode.position[1]], #Position
                            [foundNode.size[0] - img.size[0], img.size[1]] #Size
                    ) 
                    foundNode.down = node(
                            [foundNode.position[0], foundNode.position[1] + img.size[1]],#Position
                            [foundNode.size[0], foundNode.size[1] - img.size[1]] #Size
                    )

        def loadSprites(path):
            sprites = loadImages(path)
            sortImages(sprites)
            return sprites

        def getName():
            name = input("Enter a name for the output spritesheet(s) " + Fore.YELLOW + "(Naming your spritesheet is important for referencing it later in lua): ")
            return name if name != "" else "untitled"


        def getSpriteModuleHelper(current,name,idx):
            if current is None:
                return "" 
            if current.image is None:
                return ""
            fileName = os.path.basename(current.image.filename)
            periodPos = fileName.rfind(".")
            fileName = fileName[:periodPos]
            right = getSpriteModuleHelper(current.right, name, idx)
            down = getSpriteModuleHelper(current.down, name, idx)
            return "\tnew{name}:AddSprite(\"{fname}\", Vector2.new({p1}, {p2}), Vector2.new({s1}, {s2}), {name}Sheet{idx})\n".format(
                    name = name, 
                    fname = fileName,
                    p1 = current.position[0],
                    p2 = current.position[1],
                    s1 = current.image.size[0],
                    s2 = current.image.size[1],
                    idx = idx
            ) + right + down

        def genSpriteSheetModule(trees, output, name):
            elements = ""
            for idx,tree in enumerate(trees):
                if len(trees) == 1:
                    idx = ""
                elements += getSpriteModuleHelper(tree, name, str(idx))
            output += elements + "\treturn new{name}\nend\n\nreturn {name}".format(name=name)
            return output

        def imageVariblesGenerate(trees,name):
            output = ""
            for idx,tree in enumerate(trees):
                if len(trees) == 1:
                    idx == ""
                output += "local {name}Sheet{idx} = \"rbxassetid://ID_OF_{upname}{idx}_HERE\"\n".format(name=name, idx=idx, upname=name.upper())
            return output
                
        def generateLua(text,name, outputFolder):
            try:
                outputFile = open(outputFolder+ "/" + name + ".lua", "w")
                outputFile.write(text)
                outputFile.close()
            except Exception:
                raise Exception

            filePath = outputFolder+ "/" + name + ".lua"


        def generateLuaOutput(outputType, name, trees, outputFolder):
            outputString = ""
            if outputType == 3:
                return
            if outputType == 1:
                varibles = imageVariblesGenerate(trees, name)
                outputString = LUA_HEADER.format(name=name, varibles=varibles)
                outputString = genSpriteSheetModule(trees, outputString, name) 
            elif outputType == 2:
                outputString += imageVariblesGenerate(trees,name)
                outputString += "\nreturn {\n"
                outputString += generateLuaTableOutput(trees,name)
                outputString += "}"
            generateLua(outputString,name, outputFolder)


        def genLuaTableHelper(current,name,idx):
            if current is None:
                return "" 
            if current.image is None:
                return ""
            fileName = os.path.basename(current.image.filename)
            periodPos = fileName.rfind(".")
            fileName = fileName[:periodPos]
            right = genLuaTableHelper(current.right, name, idx)
            down = genLuaTableHelper(current.down, name, idx)
            return "\t[\"{fname}\"] = {{Sheet = {name}Sheet{idx}, Position = Vector2.new({p1}, {p2}), Size = Vector2.new({s1}, {s2})}};\n".format(
                    name = name, 
                    fname = fileName,
                    p1 = current.position[0],
                    p2 = current.position[1],
                    s1 = current.image.size[0],
                    s2 = current.image.size[1],
                    idx = idx
            ) + right + down


        def generateLuaTableOutput(trees, name):
            output = ""
            for idx, tree in enumerate(trees):
                if len(trees) == 1:
                    idx = ""
                output += genLuaTableHelper(tree, name, idx)
            return output
        name = config["name"]
        size=f"{width}x{height}"
        sprites = loadSprites(tempDir + "/frames/")
        trees = []
        buildTree(trees, sprites)
        outputFolder = getOutputFolder(tempDir)
        packImages(trees, name, '.')
        generateLuaOutput(1, name, trees, outputFolder)
        source_code = outputFolder + "/" + name + ".lua"
        with open(source_code, "r") as f:
            code = f.read()

        code = code.replace(f"), Vector2.new({size}, {size}), ", "), ")
        code = code.replace(f"setmetatable(new{name}, {name})", "")
        code = code.replace(f"{name}.__index = {name}\nsetmetatable({name}, Spritesheet)", "")
        code = code.replace(f"new{name}:AddSprite(", f"Video.addFrame({name}, ")
        code = code.replace(
            f"local new{name} = Spritesheet.new()\n",
            f"local {name} = Video.new(Vector2.new({size}, {size}))",
        )
        code = code.replace(f"return new{name}", f"return {name}")
        code = code.replace(
            'local Spritesheet = require(script:FindFirstAncestorWhichIsA("ModuleScript").Spritesheet)',
            "local Video = require(script.Parent.Parent.Video)",
        )

        with open(f"{name}.luau", "w") as f:
            f.write(code)
        shutil.rmtree(os.getcwd() + "/" + tempDir)
        return pathlib.Path(f"{name}.luau")
    except Exception as Error:
        if os.path.exists(os.getcwd() + "/" + tempDir):
            shutil.rmtree(os.getcwd() + "/" + tempDir)
        raise Error
    
if __name__ == "__main__":
    args = argv[1:]
    if len(args) != 1:
        print("Usage: python3 Vid2Lua.py <path to video> ")
        exit(1)
    videoPath = args[0]
    res = convert(videoPath)
    if not res == None:
        print("Your Script is ready!")
        print(f"Your script is located at {res}")
    else:
        print("Something went wrong!")