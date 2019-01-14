# PyHedrals [![Build Status](https://travis-ci.org/StarlitGhost/pyhedrals.svg?branch=master)](https://travis-ci.org/StarlitGhost/pyhedrals)

A library for evaluating tabletop dice roll expressions.

Used in the Mastodon bot [DiceCat](https://github.com/StarlitGhost/DiceCat), and the IRC bot [DesertBot](https://github.com/DesertBot/DesertBot)

### Usage Overview

Sample usage:
`5d6!>4 + (5d(2d10)dl - d10) * (d20 / 2) # for an unnecessarily complicated roll`

Sample output:
`84 for an unnecessarily complicated roll`

There is also a verbose mode that outputs every individual die roll, that output looks like this:
`[2d10: 2,5 (7) | 5d7: -1-,6,2,4,5 (17) | 1d10: 3 (3) | 1d20: 9 (9) | 5d6: 2,2,3,*5*,*5*,2,*5*,4 (28)] 84 for an unnecessarily complicated roll`

### Supported Operators
* Arithmetic: `+` `-` `*` `/` `%` `^` `()` (addition, subtraction, multiplication, division, modulus, exponent, parentheses)
* Dice: `#d#` (eg, `3d6`, `d20`)
  * Rolls the left number of dice with the right number of sides. `3d6` rolls 3 six-sided dice
  * The first number is optional and defaults to 1 if omitted
* Dice modifiers:
  * Keep/Drop Highest/Lowest: `kh#` `kl#` `dh#` `dl#`
    * Keeps/Drops only the # highest/lowest dice rolls. Any that are either not kept or dropped are removed from the total
    * The number is optional and defaults to 1 if omitted
  * Exploding: `!` `!#` `!>#` `!>=#` `!<#` `!<=#`
    * Each die that rolls maximum (`!`), or a specific number (`!#`), or over/under a threshold (`!>#` `!>=#` `!<#` `!<=#`), adds an additional die to the pool
      * This repeats for each die added to the pool
  * Reroll: `r` `r#` `r>#` `r>=#` `r<#` `r<=#`
    * Drops and rerolls each die that rolls minimum (`r`), or a specific number (`r#`), or over/under a threshold (`r>#` `r>=#` `r<#` `r<=#`)
      * This repeats for each die rerolled. You can make it only reroll each die once with `ro` instead of `r`
  * Count: `c` `c#` `c>#` `c>=#` `c<#` `c<=#`
    * Counts the number of dice that roll maximum (`c`), or a specific number (`c#`), or over/under a threshold (`c>#` `c>=#` `c<#` `c<=#`)
  * Sorting: `s` `sa` `sd`
    * Sorts the dice rolls in ascending (`s` `sa`) or descending (`sd`) order
    * This still applies in non-verbose mode but you won't see any visible effect
* Comments: `# your comment here`
  * Adds a comment to the end of the output, so you can describe what the roll is for. eg: `d20+5 # for initiative`
  * The `#` is a literal hash, not a number this time :)

If you have more ideas for operators, suggestions and pull requests are welcome!
