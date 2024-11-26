# Choices and Conditionals

A linear story with no user interaction can make for a boring VN.
Bianca currently supports **choices**, where you may provide some sort of
selection to the player that can then be handled within the script.
Of course, it would be difficult to do much other than output the choice
the player made earlier without **`if` statements**.
Both will be covered in this topic.

## Choices

Choices are essentially a big line of strings separated by pipes (`|`).
When the interpreter finds a line with the `choice` keyword, **it will provide
the player with a dropdown menu once a `see` or `say` statement is used**. \
In order to **create a choice**, you may type:
```
choice "Pet Wumpus" | "Pet ${animal2}" | "Don't pet any animal"
```
where `"Pet Wumpus"`, `"Pet ${animal2}"` and `"Don't pet any animal"`
are the choices.

The choice the player picks will then be stored in the reserved variable
`selected`, and it can be used like a regular variable in your script.

## Conditionals

`if` statements are the basic way to compare values to each other within a
`.dvn` script. Bianca comes with its own special set of **compare operators**:
* **Equal to**                 (`eq`)
* **Not equal to**             (`ne`)
* **Greater than**             (`gt`)
* **Less than**                (`lt`)
* **Greater than or equal to** (`ge`)
* **Less than or equal to**    (`le`)

In order to **begin an if statement**, you may type:
```
if "thing1" eq thing2
```
where `"thing1"` is the first operand (in this case, a string)
and `thing2` is the second (in this case, a variable).
Beneath this line, we can tell the interpreter to do something else only
when the comparison is true.

In order to **end your if statement**, you may type:
```
end
```

Below is an example of a proper if statement:
```
if my_score gt 5
    var player_won = 1
    say Wumpus "You won!"
    say Tux "Your score is ${score}"
end
```

> **Spacing is required** between the operands and the operator.
> Using two-letter words instead of symbols was an attempt to distinguish
> this behavior from the `=` sign used when setting images and variables.
{style="warning"}

> If we put a choice and some if statements together, we can **create a story with
> multiple paths** like so:
> ```
> # Allow the player to choose which poem to read
> choice "Sayori" | "Natsuki" | "Yuri"
> say "Whose poem should I read first?"
> 
> # Chain of if statements for each possible choice
> if selected eq "Sayori"                 # Sayori's poem
>     say "Sayori's poem is very happy"
> end
> if selected eq "Natsuki"                # Natsuki's poem
>     say "Natsuki's poem is very cutesy"
> end
> if selected eq "Yuri"                   # Yuri's poem
>     say "Yuri's poem is very refined"
> end
> ```