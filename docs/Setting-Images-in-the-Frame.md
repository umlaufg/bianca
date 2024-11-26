# Setting Images in the Frame

For a Visual Novel to be *visual*, a frame needs to be rendered alongside some
character's dialogue. The expressions used to manipulate backgrounds and
sprites will be described here.

## Setting the background

Bianca will not allow output until a background is loaded. \
In order to **set a background**, you may type:
```
scene wumpus_house
```
where `wumpus_house` is the name of the background you want to use.
> See [here](http://localhost:63342/Bianca/preview/data-types.html#backgrounds)
> on how to add a background to your script.

## Adding a character to the frame

You may have as many characters as you like on screen at once.
An x and y position relative to the background may be specified as well. \
Below are valid ways to **join a character to the frame**:
```
show Wumpus happy
show Tux bashful 100 200
```
where `bashful` is the name of the sprite you want the character to appear
with, and `100` is the x offset and `200` is the y offset.

> In this case, position `0 0` will be in the top left corner of the frame.
{style="note"}

> Specifying only one coordinate will result in an error.
{style="warning"}

After a character is joined to the frame, you can change their sprite without 
the need to specify the coordinates again.

> See [here](http://localhost:63342/Bianca/preview/data-types.html#sprites)
> on how to add a sprite to your script.

## Removing characters from the frame

**Removing a character** is very similar to adding a character. \
To do so, you may type:
```
hide Wumpus
```
Bianca also allows **multiple characters** to be removed from the screen
at once, where the name of each character to be removed must be separated
by a space:
```
hide Wumpus Tux Eileen Monika
```
Of course, instead of removing characters one-by-one, you may remove
**all of them at once**:
```
clear
```