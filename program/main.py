import os, sys, requests, discord
from discord import app_commands
from dotenv import load_dotenv
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from PIL import Image
from io import BytesIO, StringIO

# Compiler Version
VERSION = "1.1"

# Basic info required for loading the game/rendering frames
class Compile_Data:
    def __init__(self):
        self.OUT_NAME = None
        self.OUT_TEXT = ""
        self.OUT_CHOICE = None
        self.OUT_BACKGROUND = "" #
        self.OUT_SPRITES = {} #

        self.LINE_NUM = 0
        self.BOOLS = [] #
        self.LABEL = ""
        self.IS_EMPTY_LABEL = False
        self.WAIT = False

# Where all variables and images will go
class Asset_Tree:
    def __init__(self):
        self.vars = {} #
        self.sprites = {} #
        self.backgrounds = {} #

    # Arguments may be:
    # item : type of asset we're going to add/set
    # char : if adding a sprite, which character it will belong to
    # name : the name of the asset that can be called in the script
    # val  : the value of the asset
    # raw  : the url used in the line of code (for save file gen.)
    def set(self, **kwargs):
        item = kwargs.get("item", None)
        char = kwargs.get("char", None)
        name = kwargs.get("name", None)
        val = kwargs.get("val", None)
        raw = kwargs.get("raw", None)
        
        match item:
            case "var":
                self.vars[name] = val

            case "character":
                # Does character for this sprite exist? No? Then add them
                if char not in self.sprites:
                    self.sprites[char] = {}
            case "sprite":
                self.sprites[char].update({name : val})
            case "background":
                self.backgrounds[name] = val

# Button bar
class Buttons(discord.ui.View):
    def __init__(self, user_id, timeout: int=3600) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.message = instance[user_id]["message"]
        self.game = instance[user_id]["game"]

    async def interaction_check(self, inter: discord.Interaction) -> bool:
        if inter.user.id == self.user_id:
            return True
        await inter.response.send_message(
            "Instance was created by another user!",
            ephemeral = True
            )
        return False

    async def on_timeout(self) -> None:
        if self.message == instance[self.user_id]["message"]:
            await self.message.edit(
                content="(Instance has been idle for more than an hour.)",
                view=None
                )
            del instance[self.user_id]

    async def disable(self) -> None:
        if self.message:
            await self.message.edit(
                content="(User has opened a new VN instance.)",
                view=None
                )

    async def add_choices(self, choices) -> None:
        self.add_item(Select(self.user_id, choices))

    @discord.ui.button(label="Save", style=discord.ButtonStyle.gray)
    async def save(self, inter: discord.Interaction,
                      button: discord.ui.Button) -> None:
        save_file = await gen_save_file(self.user_id)
        await inter.response.send_message(file=save_file, ephemeral=True)

    @discord.ui.button(label="Load", style=discord.ButtonStyle.gray)
    async def load(self, inter: discord.Interaction,
                      button: discord.ui.Button) -> None:
        await inter.response.send_modal(LoadModal())

    @discord.ui.button(label="Next", style=discord.ButtonStyle.green)
    async def next(self, inter: discord.Interaction,
                      button: discord.ui.Button) -> None:
        await inter.response.defer(thinking=False)
        self.game.WAIT = False
        await run(self.user_id)

# Select menu for making choices
class Select(discord.ui.Select):
    def __init__(self, user_id, choices) -> None:
        self.user_id = user_id
        self.buttons = instance[user_id]["buttons"]
        self.game = instance[user_id]["game"]
        self.next_button = self.buttons.children[2]
        self.next_button.disabled = True
        super().__init__(
            placeholder="Select an option",
            max_values = 1,
            min_values = 1,
            options=choices
            )

    # When choice is made
    async def callback(self, inter: discord.Interaction) -> None:
        await inter.response.defer(thinking=False)
        self.selector = self.buttons.children[3]
        set_var(self.user_id, "selected", self.values[0], override=True)
        self.next_button.disabled = False
        self.buttons.remove_item(self.selector)
        self.game.WAIT = False
        await run(self.user_id)

# Modal for loading from a save code/(potentially) text input
class BaseModal(discord.ui.Modal):
    _interaction: discord.Interaction | None = None

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        self._interaction = interaction
        self.stop()

    @property
    def interaction(self) -> discord.Interaction | None:
        return self._interaction

class LoadModal(BaseModal, title="Load Game"):
    file = discord.ui.TextInput(
            label="Save File",
            placeholder="discord.com/channels/123/456/789"
            )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        user_id = interaction.user.id
        message = instance[user_id]["message"]
        await super().on_submit(interaction)
        await message.edit(
        content="Loading...",
        embeds=[],
        view=None,
        attachments=[]
        )
        await load_save_file(user_id, self.file.value, interaction)
        
# Error handling
def throw(sev, user_id, reason, **kwargs):
    message = instance[user_id]["message"]
    script = instance[user_id]["script"]
    game = instance[user_id]["game"]
    
    if "content" not in kwargs:
        line = script[game.LINE_NUM].decode("utf-8")
        line = line.strip()
    else:
        line = kwargs["content"]

    title = "Woops!"
    if game.LINE_NUM < len(script):
        title += " " + f"(line {game.LINE_NUM + 1})"
    
    # Exceptions
    if sev == "e":
        raise Exception(f"{title}\n{line}\n{reason}")

def remove_comments(line):
    # Divide into words
    word = line.split()

    # Remove comments if present
    is_str = False
    quote = ""
    w = 0
    while w < len(word):
        if word[w][0] in ('"', "'"):
            is_str = True
            quote = word[w][0]
        elif word[w][-1] == quote:
            is_str = False
            quote = ""
        if word[w][0] == "#" and not is_str:
            word = word[:w]
            line = " ".join(word)

        w += 1
    if len(word) == 0:
        word = [""]

    return (line, word)

# Get the value's type
def get_type(user_id, val):
    # Integer
    if val.replace("-", "").isdecimal():
        return "int"
    # String
    elif val[0] == val[-1] and val[0] in ('"', "'"):
        return "str"
    # Float
    elif val.replace("-", "").replace(".", "").isdecimal():
        return "float"
    # Variable
    elif val.replace("_", "").isalnum() and val[0].isalpha():
        return "var"
    # Invalid type
    else:
        return "None"

# Get the value in its correct type, if any
def clean_type(user_id, val):
    tree = instance[user_id]["tree"]
    match get_type(user_id, val):
        # Valid integer
        case "int":
            return int(val)
        # Valid string
        case "str":
            return parse_str(user_id, str(val[1:-1]), val[0])
        # Valid float
        case "float":
            return float(val)
        # Valid var
        case "var":
            val = tree.vars.get(val, None)
            if val != None:
                return(val)
            else:
                throw("e", user_id, f"var `{val}` does not exist")
        # Invalid type
        case "None":
            throw("e", user_id, f"invalid type for `{val}`")

# Variables may be inserted into strings using ${}
# Example: "the number is ${my_num}" -> "the number is 4"
# Escaping is also handled here
def parse_str(user_id, string, quote):
    tree = instance[user_id]["tree"]
    var = tree.vars
    escaped = False
    is_var = False
    n = 0
    new_string = ""
    parsed = ""
    while n < len(string):
        if string[n] == "\\":
            escaped = not escaped
            if escaped == False:
                new_string += "\\"
        elif "".join(string[n:n+2]) == "${" and not escaped:
            is_var = True
            n += 1
        elif is_var:
            if string[n] != "}":
                parsed += string[n]
            else:
                val = var.get(parsed, None)
                if val != None:
                    new_string += str(val)
                    is_var = False
                    parsed = ""
                else:
                    throw("e", user_id, f"var `{parsed}` does not exist")
        elif string[n] == quote and not escaped:
            throw("e", user_id,
                  f"invalid syntax (did you mean to use `\\{quote}`?)")
        else:
            new_string += string[n]
            escaped = False
        n += 1
    if escaped:
        throw("e", user_id,
              'invalid syntax (did you mean to use `"\\\\"`?)')
    elif is_var:
        throw("e", user_id, f"missing closing bracket")
    else:
        return new_string

# Validate arguments and return cleaned
# TODO: Replace this with more descriptive errors for each expression(?)
# TODO: A lexer would be preferable at this point
def validate_args(user_id, arg, **kwargs):
    num = kwargs.get("num", None)
    # num wasn't specified:
    if num == None:
        num = len(arg)

    # Check length
    if len(arg) < num or len(arg) == 0:
        throw("e", user_id, "missing argument(s)")
    elif len(arg) > num:
        throw("e", user_id, "too many arguments")

    for n in range(len(arg)):
        arg[n] = arg[n].strip()
        # Check argument for null value
        # (for expressions with a delimiter)
        if arg[n] == "":
            throw("e", user_id, "null argument(s) provided")
            
    return arg

ACCEPTED_SCRIPTS = ("dvn")
ACCEPTED_SAVE_FILES = ("dsav")
async def validate_message(user_id, name, val, accepted):
    # Thus far, the compiler only supports loading scripts and saves from
    # Discord itself through a message link
    host = "{uri.netloc}".format(uri=urlparse(val))
    path = urlparse(val).path.split("/")
    
    if host != "discord.com":
        throw("e", user_id,
              f"`{name}` link must come from discord.com")
    elif path[1] != "channels" or not get_type(user_id, path[2]) == "int":
        throw("e", user_id,
              f"`{name}` message link must be from a server")

    # We should make sure we can actually grab the contents of this message
    # If it's not reachable (bot not in server, message deleted, etc.
    # throw an error
    guild = client.get_guild(clean_type(user_id, path[2]))
    if guild == None:
        throw("e", user_id,
              f"server for `{name}` message cannot be reached")
    try:
        channel = guild.get_channel_or_thread(clean_type(user_id, path[3]))
        message = await channel.fetch_message(clean_type(user_id, path[4]))
    except:
        throw("e", user_id,
              f"server `{guild}` exists, " +
              f"but `{name}` message cannot be reached")

    attachment = message.attachments
    if len(attachment) != 1:
        throw("e", user_id,
              f"`{name}` message must have 1 attachment")
    else:
        attachment = attachment[0]

    file_ext = attachment.filename.split(".")[-1]
    if file_ext not in accepted:
        throw("e", user_id, f"file type .{file_ext} is not accepted")
    
    # Although we load files directly into memory, there's still a reasonable
    # limit to the amount of memory one may use
    # Let's give the user about 8 megabytes
    if attachment.size > 8000000:
        throw("e", user_id, f"file `{val}` larger than 8 megabytes")

    return attachment.url

USER_AGENT = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}
ACCEPTED_IMAGE_URLS = ("i.imgur.com", "cdn.imgchest.com")
ACCEPTED_IMAGES = ("image/png", "image/jpeg", "image/webp", "image/bmp")
async def validate_image(user_id, name, val):
    # To avoid having to handle images ourselves, we'll just use free services
    # to do it for us
    # Imgur is the primary source and imgchest is an alternative
    host = "{uri.netloc}".format(uri=urlparse(val))
    if host not in ACCEPTED_IMAGE_URLS:
        throw("e", user_id,
              f"`{name}` file url must come from i.imgur.com or " +
               "cdn.imgchest.com")

    response = requests.head(val, headers=USER_AGENT)
    mime = response.headers["content-type"].split(";")[0]
    if mime not in ACCEPTED_IMAGES:
        # The server will return {type}/{name} and we only want the {name}
        mime_name = mime.split("/")[1]
        throw("e", user_id, f"file type {mime_name} is not accepted")

    size = response.headers["content-length"]
    if int(size) > 8000000:
        throw("e", user_id, f"file `{val}` larger than 8 megabytes")

    return val

RESERVED_WORDS = (
    "eq", "ne", "in", "gt", "lt", "ge", "le",
    "choice", "var", "add", "sub", "mul", "div",
    "if", "sprite", "bg", "scene", "show", "hide",
    "clear", "say", "see"
)
# Set variable
def set_var(user_id, name, val, **kwargs):
    override = kwargs.get("override", False)
    tree = instance[user_id]["tree"]
    if name in RESERVED_WORDS and not override:
        throw("e", user_id, f"var name `{name}` cannot be a reserved word")
    elif get_type(user_id, name) != "var":
        throw("e", user_id, f"invalid var name `{name}`")
    else:
        tree.set(item="var", name=name, val=val)

# Add character (if nonexistent)
def add_char(user_id, char):
    tree = instance[user_id]["tree"]
    if get_type(user_id, char) == "var":
        tree.set(item="character", char=char)
    else:
        throw("e", user_id, f"invalid char name `{char}`")

# Add sprite
async def add_sprite(user_id, char, name, val):
    tree = instance[user_id]["tree"]
    url = await validate_image(user_id, name, val)
    # Make character if nonexistent
    add_char(user_id, char)
    # Add sprite to their table
    tree.set(item="sprite", char=char, name=name, val=url, raw=val)

# Add background to table
async def add_bg(user_id, name, val):
    tree = instance[user_id]["tree"]
    url = await validate_image(user_id, name, val)
    tree.set(item="background", name=name, val=url, raw=val)

def bin_op(user_id, op, word):
    tree = instance[user_id]["tree"]
    # We need to store the output in a variable, namely the one used
    # in the first argument
    var = tree.vars
    # Attempt to access the first argument (variable)
    arg1 = var.get(word[1], None)
    if arg1 == None:
        throw("e", user_id, f"first argument must be an initialized var")
    # Attempt to access the second argument (any)
    if len(word) >= 3:
        arg2 = clean_type(user_id, word[2])
    else:
        throw("e", user_id, f"missing second argument")

    # After cleaning the arguments, run the operation
    # If types cannot be operated on (in Python), throw an error
    # To prevent memory overload, we will limit the user's var table to
    # 5 kilobytes (which should be more than enough)
    result = False
    match op:
        case "+":
            try:
                result = arg1 + arg2
            except:
                throw("e", user_id,
                      f"`{arg1}` and `{arg2}` type(s) cannot be added")
        case "-":
            try:
                result = arg1 - arg2
            except:
                throw("e", user_id,
                      f"`{arg1}` and `{arg2}` type(s) cannot be subtracted")
        case "*":
            try:
                result = arg1 * arg2
            except:
                throw("e", user_id,
                      f"`{arg1}` and `{arg2}` type(s) cannot be multiplied")
        case "/":
            try:
                result = arg1 / arg2
            except:
                throw("e", user_id,
                      f"`{arg1}` and `{arg2}` type(s) cannot be divided")

    # Check var table size
    if sys.getsizeof(result) + sys.getsizeof(var) <= 5000:
        # Assign the result to the first argument (var)
        set_var(user_id, word[1], result)
    else:
        throw("e", user_id,
              f"total memory used for variables has exceeded 5 kilobytes")

# Conditional if statement with compare ops
ACCEPTED_COMPS = ("eq", "ne", "in", "gt", "lt", "ge", "le")
def cond_if(user_id, line):
    game = instance[user_id]["game"]
    word = line.split()
    is_str = False
    quote = ""
    comp = ""
    w = 0
    while w < len(word) and comp == "":
        if word[w][0] in ('"', "'"):
            is_str = True
            quote = word[w][0]
        elif word[w][-1] == quote:
            is_str = False
            quote= ""
        elif word[w] in ACCEPTED_COMPS and not is_str:
            comp = word[w]
        w += 1

    if comp == "":
        throw("e", user_id, f"invalid syntax")
    word = line[len(word[0]):].split(comp, 1)
    arg1 = clean_type(user_id, word[0].strip())
    arg2 = clean_type(user_id, word[1].strip())
    boolean = None
    try:
        match comp:
            case "eq":
                boolean = arg1 == arg2
            case "ne":
                boolean = arg1 != arg2
            case "in":
                boolean = arg1 in arg2
            case "gt":
                boolean = arg1 > arg2
            case "lt":
                boolean = arg1 < arg2
            case "ge":
                boolean = arg1 >= arg2
            case "le":
                boolean = arg1 <= arg2
    except:
        throw("e", user_id,
              f"`{arg1}` and `{arg2}` type(s) cannot be compared with `{comp}`")

    game.BOOLS.append(boolean)

# TODO: Make a lexer at this point because this is getting hacky
async def choice(user_id, val):
    buttons = instance[user_id]["buttons"]
    choices = []
    is_str = False
    quote = ""
    n = 0
    while n < len(val):
        if val[n] in ('"', "'") and not is_str:
            is_str = True
            quote = val[n]
        elif val[n] == quote and val[n-1] != "\\":
            is_str = False
            quote = ""
        if val[n] == "|" or n == len(val)-1 and not is_str:
            if val[n] == "|":
                end = n
            else:
                end = n+1
            choice = val[:end].strip()
            
            if get_type(user_id, choice) == "str":
                choices.append(
                    discord.SelectOption(label=clean_type(user_id, choice))
                    )
                val = val[end+1:]
                n = -1
                quote = ""
            else:
                throw("e", user_id, f"`{val[:n]}` is not a string")

        n += 1

    if is_str:
        throw("e", user_id, f"`{quote}` was never closed")
    elif len(choices) == 0:
        throw("e", user_id, "no choices given")
            
    await buttons.add_choices(choices)

# Set current background in frame
def set_bg(user_id, name):
    game = instance[user_id]["game"]
    tree = instance[user_id]["tree"]
    found = tree.backgrounds.get(name, None)
    if found != None:
        game.OUT_BACKGROUND = name
    else:
        throw("e", user_id, f"background `{name}` does not exist")

# Add/change a sprite in frame
def show_sprite(user_id, char, name, pos):
    game = instance[user_id]["game"]
    tree = instance[user_id]["tree"]

    # Make sure the entry for this sprite is valid
    char_valid = tree.sprites.get(char, None)
    url = char_valid.get(name, None)
    if char_valid == None:
        throw("e", user_id, f"character `{char}` does not exist")
    elif url == None:
        throw("e", user_id, f"sprite `{name}` does not exist")

    # Add sprite and pos info to OUT_SPRITES
    on_screen = game.OUT_SPRITES.get(char, None)
    if len(pos) == 2:
        if get_type(user_id, pos[0]) == "int" and \
           get_type(user_id, pos[1]) == "int":
            x = clean_type(user_id, pos[0])
            y = clean_type(user_id, pos[1])
            game.OUT_SPRITES[char] = (name, (x, y))
        else:
            throw("e", user_id, f"both coordinates must be integers")
    elif len(pos) == 0:
        if on_screen == None:
            game.OUT_SPRITES[char] = (name, (0, 0))
        else:
            game.OUT_SPRITES[char] = (name, on_screen[1])
    else:
        throw("e", user_id, f"incorrect number of position arguments")

# Remove a sprite from frame
def hide_sprite(user_id, chars):
    game = instance[user_id]["game"]
    tree = instance[user_id]["tree"]
    if type(chars) != list:
        chars = list(chars)
    for char in chars:
        char_valid = tree.sprites.get(char, None)
        if char_valid == None:
            throw("e", user_id, f"character `{char}` does not exist")
        else:
            game.OUT_SPRITES.pop(char)

# Remove all sprites
def clear_sprites(user_id):
    game = instance[user_id]["game"]
    game.OUT_SPRITES.clear()

# Generate save file
async def gen_save_file(user_id):
    game = instance[user_id]["game"]
    tree = instance[user_id]["tree"]
    backgrounds = tree.backgrounds
    sprites = tree.sprites
    out_sprites = game.OUT_SPRITES

    file = []
    
    file.append("#!resume line " + str(game.LINE_NUM-1))
    for key in tree.vars:
        if type(tree.vars[key]) == str:
            file.append("var " + key + " = " +
                        '"' + tree.vars[key].replace("${", "\\${") + '"')
        else:
            file.append("var " + key + " = " + str(tree.vars[key]))
    for key in backgrounds:
        file.append("bg " + key + " = " + backgrounds[key])
    for char in sprites:
        file.append("make " + char)
        for key in sprites[char]:
            file.append("sprite " + char + " " + key + " = " +
                        sprites[char][key])
            
    file.append("scene " + game.OUT_BACKGROUND)
    for char in out_sprites:
        vals = out_sprites[char]
        pos = vals[1]
        file.append(f"show {char} {vals[0]} {pos[0]} {pos[1]}")
    for true in game.BOOLS:
        if true:
            file.append("if 0 eq 0")
        else:
            file.append("if 0 ne 0")

    out = ""
    for line in file:
        out += line + "\n"
    out = StringIO(out)
    return discord.File(fp=out, filename="save.dsav")

# Load the files we generated above
async def load_save_file(user_id, file, interaction):
    game = instance[user_id]["game"]
    try:
        url = await validate_message(
            user_id, "save file", file, ACCEPTED_SAVE_FILES
            )
    # If invalid file, throw error
    except:
        await interaction.followup.send(
            content="Invalid save file url! " +
            "Valid input should be a link to a message " +
            "with a single .dsav file attached.",
            ephemeral=True
            )
        return
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    savedata = urlopen(req).readlines()

    shebang = savedata[0].decode("utf-8").strip()
    shargs = shebang.split()
    if shargs[:2] == ["#!resume", "line"] and shargs[2].isdecimal():
        resume = int(shargs[2])
        old_script = instance[user_id]["script"]
        
        instance[user_id]["game"] = Compile_Data()
        instance[user_id]["tree"] = Asset_Tree()
        instance[user_id]["buttons"] = Buttons(user_id)
        game = instance[user_id]["game"]
        
        instance[user_id]["script"] = savedata
        await run(user_id, cutoff=False)

        instance[user_id]["script"] = old_script
        game.WAIT = False
        game.LINE_NUM = resume
        await run(user_id)
    else:
        await interaction.followup.send(
            content="Invalid shebang! " +
            "Please do not modify save file content.",
            ephemeral=True
            )
        return

# Register dialogue and output
async def say(user_id, word):
    game = instance[user_id]["game"]
    tree = instance[user_id]["tree"]
    arg = word[1:]
    arg = validate_args(user_id, arg)
    if arg[0] in tree.sprites:
        char = arg[0]
        start = 1
    else:
        char = None
        start = 0
    val = " ".join(arg[start:])
    
    if get_type(user_id, val) == "str":
        game.OUT_NAME = char
        game.OUT_TEXT = clean_type(user_id, val)
    else:
        throw("e", user_id, f"`{val}` is not a string")
    await out(user_id)

# Output process
# Note: the "see" expression will call this directly, using whatever
# happens to be in our Compile_Data at present
async def out(user_id):
    message = instance[user_id]["message"]
    game = instance[user_id]["game"]
    tree = instance[user_id]["tree"]
    frame = instance[user_id]["frame"]
    dialogue_box = instance[user_id]["dialogue_box"]
    buttons = instance[user_id]["buttons"]

    # Make sure we have at least something to render
    if game.OUT_BACKGROUND != "":
        bg_url = tree.backgrounds[game.OUT_BACKGROUND]
        background = Image.open(requests.get(
            bg_url, stream=True, headers=USER_AGENT
            ).raw)
    else:
        throw("e", user_id, "no background set")

    # Render the frame
    for char in game.OUT_SPRITES:
        name = game.OUT_SPRITES[char][0]
        pos = game.OUT_SPRITES[char][1]
        sprite_url = tree.sprites[char][name]
        sprite = Image.open(requests.get(
            sprite_url, stream=True, headers=USER_AGENT
            ).raw)
        sprite = sprite.convert("RGBA")
        background.paste(sprite, pos, sprite)

    # Attach the image to embed
    with BytesIO() as image_binary:
        background = background.convert("RGB")
        background.save(image_binary, "JPEG")
        image_binary.seek(0)
        file = discord.File(fp=image_binary, filename="frame.jpg")
        frame.set_image(url="attachment://frame.jpg")

    # Add dialogue
    dialogue_box.title = game.OUT_NAME
    dialogue_box.description = f"```ansi\n{game.OUT_TEXT}\n```"

    # Make sure dialogue embed is full-width (hacky)
    full_width = discord.File("./full_width.png", filename="full_width.png")
    dialogue_box.set_image(url="attachment://full_width.png")

    if game.OUT_TEXT != "":
        await message.edit(
            content="",
            embeds=[frame, dialogue_box],
            view=buttons,
            attachments=[file, full_width]
            )
    else:
        await message.edit(
            content="",
            embed=frame,
            view=buttons,
            attachments=[file]
            )

    # Wait for user to click the next button
    game.WAIT = True

    # Since there's something for the player to click, this label is not useless
    game.IS_EMPTY_LABEL = False

# TODO: Move all argument parsing to their respective functions
# instead of processing them here
async def parse(user_id, line):
    # Weak overload protection
    if sys.getsizeof(line) > 5000:
        throw("e", user_id, f"line size is too large for parsing")
    # Clean our line
    line = line.strip()
    # Remove comments
    r = remove_comments(line)
    line = r[0]
    word = r[1]

    # If we're inside an if statement:
    game = instance[user_id]["game"]
    if len(game.BOOLS) > 0:
        # If it has ended then we should take it off our list
        if word[0] == "end":
            game.BOOLS.pop(-1)
            return
        # If we're inside a false if statement, append any child ifs as False
        elif word[0] == "if" and not game.BOOLS[-1]:
            game.BOOLS.append(False)
            return
        # Skip if we're inside an if statement that was not triggered
        elif not game.BOOLS[-1]:
            return

    # If we're looking for a label:
    if game.LABEL != "":
        if word[0] == "label":
            arg = word[1:]
            arg = validate_args(user_id, arg, num=1)
            name = arg[0]
            if name == game.LABEL:
                game.LABEL = ""
        else:
            return
            
    match word[0]:
        # External file-related expressions
        case "import":
            pass
            #arg = word[1:]
            #name = arg[0]
            #set_bg(user_id, name)

        # Control-flow-related expressions
        case "label":
            arg = word[1:]
            arg = validate_args(user_id, arg, num=1)
            name = arg[0]
            if name.replace("_", "").isalnum():
                game.IS_EMPTY_LABEL = True
            else:
                throw("e", user_id, "invalid label name")
        case "jump":
            arg = word[1:]
            arg = validate_args(user_id, arg, num=1)
            name = arg[0]
            if name.replace("_", "").isalnum():
                if not game.IS_EMPTY_LABEL:
                    game.LABEL = name
                    game.LINE_NUM = 0
                else:
                    throw("e", user_id, "malformed label body")
            else:
                throw("e", user_id, "invalid label name")
            
        # Variable-related expressions
        case "var":
            arg = line[len(word[0]):].split("=", 1)
            arg = validate_args(user_id, arg, num=2)
            name = arg[0]
            val = arg[1]
            set_var(user_id, name, clean_type(user_id, val))
        case "add":
            bin_op(user_id, "+", word)
        case "sub":
            bin_op(user_id, "-", word)
        case "mul":
            bin_op(user_id, "*", word)
        case "div":
            bin_op(user_id, "/", word)
        case "if":
            cond_if(user_id, line)

        # Image-related expressions
        case "make":
            char = word[1]
            add_char(user_id, char)
        case "sprite":
            arg = line[len(word[0]):].split("=", 1)
            arg = validate_args(user_id, arg, num=2)
            char = arg[0].split()[0]
            name = arg[0].split()[1]
            val = arg[1]
            if name.replace("_", "").isalnum():
                await add_sprite(user_id, char, name, val)
            else:
                pass
        case "bg":
            arg = line[len(word[0]):].split("=", 1)
            arg = validate_args(user_id, arg, num=2)
            name = arg[0]
            val = arg[1]
            if get_type(user_id, name) == "var":
                await add_bg(user_id, name, val)
            else:
                pass
        case "scene":
            arg = word[1:]
            arg = validate_args(user_id, arg, num=1)
            name = arg[0]
            set_bg(user_id, name)
        case "show":
            arg = word[1:]
            arg = validate_args(user_id, arg)
            char = arg[0]
            name = arg[1]
            pos = []
            if len(word) > 3:
                pos = word[3:]
            show_sprite(user_id, char, name, pos)
        case "hide":
            arg = line[len(word[0]):].split(",")
            arg = validate_args(user_id, arg)
            chars = arg
            hide_sprite(user_id, chars)
        case "clear":
            clear_sprites(user_id)

        # Output-related expressions
        case "say":
            await say(user_id, word)
        case "see":
            await out(user_id)
        case "choice":
            val = line[len(word[0]):].strip()
            await choice(user_id, val)

        # When the line isn't a valid piece of code
        case _ if len(line) > 0:
            throw("e", user_id, "invalid syntax")

# Run each line of the script until output is sent,
# then wait for the next button to be clicked to continue
async def run(user_id, **kwargs):
    cutoff = kwargs.get("cutoff", True)
    message = instance[user_id]["message"]
    script = instance[user_id]["script"]
    game = instance[user_id]["game"]
    n = game.LINE_NUM

    try:
        while not game.WAIT and n < len(script):
            line = script[n].decode("utf-8")
            await parse(user_id, line)
            n = game.LINE_NUM + 1
            game.LINE_NUM = n

        if n == len(script):
            if game.LABEL != "":
                throw("e", user_id, f"label does not exist",
                      content=f"jump {game.LABEL}")
            elif cutoff:
                await message.edit(view=None)
                del instance[user_id]
            
    except Exception as e:
        arg = str(e).split("\n")
        embed = discord.Embed(
            title=arg[0],
            description="\t" + f"```{arg[1]}```" + "\n" + arg[2],
            color=discord.Color.red()
        )
        await message.edit(
            content="",
            embed=embed,
            view=None,
            attachments=[]
            )
        del instance[user_id]

# All VN instances will go here
# Each instance is denoted by the author's ID
instance = {}

# Grab the discord bot token
load_dotenv()
TOKEN = os.getenv("TOKEN")

# Some initialization
client = discord.Client(intents=discord.Intents.default())
client.tree = app_commands.CommandTree(client)
discord.Intents.message_content = True # Allows us to actually read messages

# When we come online:
@client.event
async def on_ready() -> None:
    print(f"Bot online as {client.user}")

    # Were our commands synced with Discord?
    try:
        synced = await client.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@client.tree.command(
    name="play",
    description="Play a novel from a script"
    )
@app_commands.describe(
    script="Message link (script must be an attachment)"
    )
async def play(interaction: discord.Interaction, script: str) -> None:
    # Initialize Instance
    user_id = interaction.user.id
    
    if instance.get(user_id, None) != None:
        await instance[user_id]["buttons"].disable()
        
    instance[user_id] = {}
    instance[user_id]["game"] = Compile_Data()
    instance[user_id]["tree"] = Asset_Tree()

    # Grab Script
    instance[user_id]["script"] = b"INIT"
    try:
        url = await validate_message(
            user_id, "script", script, ACCEPTED_SCRIPTS
            )
    # If invalid file, throw error and end
    except:
        await interaction.response.send_message(
            content="Invalid script url! " +
            "Valid input should be a link to a message " +
            "with a single .dvn file attached.",
            ephemeral=True
            )
        del instance[user_id]
        return
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    script = urlopen(req).readlines()
    instance[user_id]["script"] = script

    # Initialize Message
    await interaction.response.send_message(
        content="Loading..."
        )
    original_response = await interaction.original_response()
    instance[user_id]["message"] = await original_response.fetch()

    # Initialize Embeds
    instance[user_id]["frame"] = discord.Embed(
        color=discord.Color.blurple()
    )
    instance[user_id]["dialogue_box"] = discord.Embed(
        title="test",
        description="test",
        color=discord.Color.blurple()
    )

    # Initialize Buttons
    instance[user_id]["buttons"] = Buttons(user_id)

    print(f"{interaction.user} ({user_id}) " +
          f"has started instance #{len(instance)}")

    await run(user_id)

    # DEBUG
    #tree = instance[user_id]["tree"]
    #game = instance[user_id]["game"]
    #print(tree.vars)
    #print(tree.backgrounds)
    #print()
    #print(game.OUT_NAME)
    #print(game.OUT_TEXT)
    #print(game.OUT_BACKGROUND)
    #print(game.OUT_SPRITES)

client.run(TOKEN)
