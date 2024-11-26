# Data Types

Bianca comes with a few **data types** that are useful for
creating your game. \
The data types include:
* **Strings**     (ex: `"Hello, World!"` or `"My name is ${chosen_girl}."`)
* **Integers**    (ex: `1`)
* **Floats**      (ex: `3.33`)
* **Variables**   (ex: `my_var`)
* **Characters**  (ex: `Wumpus`)
* **Sprites**     (ex: `happy`)
* **Backgrounds** (ex: `courtyard_day`)

Additionally, you may insert **comments** into your script.

## Strings, Integers, and Floats

Bianca treats these data types much in the same way other compilers do.
Some important information on how they're handled is described here.

### Strings

Strings can be started with single quotes (`'`)
or double quotes (`"`) like so:
```
"This is a string"
```

Bianca also has **formatted strings**, where a variable can be embedded using
`${}` like so:
```
"While I like ${char1}, I like ${char2} more."
```

Strings also have **escaping**, with a backslash (`\`) as the prefix. \
Here are examples of each possible escape sequence:
```
"this is my \"string\" and it's very nice"
'this is my \'second string\' and it\'s also nice'
"escape sequences start with a \\ backslash"
"my variable \${foo} is escaped"
```

### Integers

Bianca only supports decimal integers and the negative sign (`-`). \
You may use numbers `0` - `9` in your script, but not numbers like `⅛` or `³`.

Here are examples of valid integers:
```
1
10
-5
```

### Floats

Floating-point numbers are supported in Bianca. Like with integers, you may
use decimal numbers, the negative sign, and a decimal point (`.`)

Here are examples of valid floats:
```
1.0
10.13672
-5.5
```

## Variables

You might need variables in your game for basic arithmetic,
responding to the player's choices, or to make your script more readable.

> Bianca interprets your script line-by-line, and like many scripting languages,
> `.dvn` script uses **duck typing**.
{style="note"}

> Bianca limits the total size of your variables to 5 kilobytes.
{style="warning"}

### Setting a variable

To **set a variable**, you may simply type
```
var my_name = "John Doe"
```
where `var` initializes the variable, `my_name` is the variable name,
and `"John Doe"` is the data you want to store in it.

### Arithmetic with variables

Thus far, Bianca supports basic operations for arithmetic:
* **Addition**       (`add`)
* **Subtraction**    (`sub`)
* **Multiplication** (`mul`)
* **Division**       (`div`)

> As Bianca is written in Python, operations will obey **Python type rules**.
> Whatever you can do in Python is what can be done in Bianca.
{style="note"}

For example, if you have a variable named `score` with value `4` and you want
to add `6` to it, you may type:
```
add score 6
```
where `add` is the desired operation, `score` is the name of the variable
you'd like to operate on, and `6` is the value that will be used for the
operation. As such, the new value of `score` is `10`.

For another example, if you have variable `my_sentence` with value
`"I love "`, you may type:
```
add my_sentence "Wumpus"
```
and the new value of `my_sentence` is `"I love Wumpus"`.

> The left operand must **always be a variable**, in which the result
> will be stored.
{style="warning"}

## Characters

Assuming you have different characters in your game (writing a VN would be
hard without some), you will end up creating character data types.

Within Bianca, all characters are given a type in which their data (like their
name, their sprite names and sprite image links) are stored.

Typically, the characters will be created for you when you add a sprite
to your script, and there is rarely a reason to **initialize one manually**. \
If, however, you find yourself needing to do this (perhaps for debugging),
you may type:
```
make Wumpus
```
where `Wumpus` is the character's name.

> It should be mentioned that you will **always refer to this name**
> when you need to do something, like add a new sprite,
> make the character appear on screen,
> or make them say some dialogue.
{style="note"}

## Sprites

Sprites are, as the name implies, the images used for your character when they
need to express a certain emotion. You might have a `happy` sprite,
a `sad` sprite, or a `silly_pose` sprite.

Bianca currently accepts image links from two websites:
**Imgur** and **Image Chest**. Bianca will accept CDN links from both
(these links start with `i.imgur.com` and `cdn.imgchest.com` respectively).

> The maximum size of any image must be less than 8 megabytes.
{style="warning"}

To **add a sprite to your script**, you may type:
```
sprite Wumpus happy https://i.imgur.com/ydxsD9I.png
```
where `Wumpus` is the name of the character the sprite will be added to,
`happy` is the sprite name, and `https://i.imgur.com/ydxsD9I.png` is the
link to the sprite image.

## Backgrounds

Backgrounds can be added much in the same way sprites can, except they are
not stored inside a character. \
To **add a background**, you may type:
```
bg park_day https://i.imgur.com/ZXzmLwf.jpeg
```
where `park_day` is the name of the background and
`https://i.imgur.com/ZXzmLwf.jpeg` is the link to the background image.

## Comments

While not exactly a data type, comments may be inserted into your script
with a hashtag (`#`). Comments may be put on a single line or in-line
following an expression and a space. \
Below examples are valid comments:
```
var myVar = 1.02 # Set myVar to 1.02

# This is our dialogue
say Wumpus "Goodbye, Cruel World!"
```
> In-line comments without a space (`add myVar 1# comment`)
> will result in an error.
{style="warning"}