# game of the year 2026

asdabefabgeonafoubergjnergn 👍👍👍👀👀👍

if you want to run it then load all the files into some ide and run pygamevl.py

# rules
1. classic blackjack rules; go up to 21 or go bust by going over 21 <br>
2. trump cards impact the game and the players <br>
2.1 some trump cards change value needed to win from 21 to 17, 24 or 27; you can override this change by placing another trump card of the same kind <br>
3. the player can hit however much they want during their turn <br>
3.1 the enemy's round starts once the player chooses to stay by pressing SHIFT<br>
3.2 the player can un-stay by pressing SHIFT again <br>
3.3 the player can use their trump cards at any point throughout the round
# UI
<img width="566" height="450" alt="image psd" src="https://github.com/user-attachments/assets/6d20ecdb-cb8a-4981-a208-96bc572c775b" />

# controls
SPACE — hit <br>
SHIFT — stand / un-stand <br>
TAB — inventory <br>
ARROW KEYS — scroll in the inventory <br>
ENTER — start the next round / select a trump card in inventory <br>
R — start another match after losing a certain amount in a row

# trump cards
*de facto called "trump cards", named "abilities" in the code* <br>
*the enemy can also use trump cards*
``max24`` — sets blackjack value to 24 <br>
``max17`` — sets blackjack value to 17 <br>
``max27`` — sets blackjack value to 27 <br>
``reset_deck`` — clears the players deck and draws 2 new cards <br>
``swap_last`` — swaps the last drawn cards of the player and enemy <br>
``friendship`` — gives 2 trump cards each to the player and enemy <br>
``force_draw`` — forces the enemy to draw a random card <br>
``draw_specific`` — player draws a 4 or 6 (subject to change) <br>
``perfect_draw`` — draws the needed card to reach the blackjack value, caps out at drawing an 11 <br>
