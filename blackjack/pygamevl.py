import pygame
import sys
from game_logic import (
    GameState, deal_opening_hands, player_hit, player_stand,
    draw_card, resolve_round, distribute_trumps, enemy_should_stand
)
from trump import run_enemy_trumps, use_trump

# screen and timing
WIDTH, HEIGHT       = 960, 540
FPS                 = 30

# card dimensions and layout
CARD_W, CARD_H      = 64, 90
TRUMP_W, TRUMP_H    = 48, 67
CARD_GAP            = 14
PLAYER_HAND_Y       = HEIGHT - 150
ENEMY_HAND_Y        = 55
HAND_START_X        = 36

# timing constants in milliseconds
ENEMY_STEP_DELAY    = 1000
TRUMP_TEMP_DURATION = 1000
CARD_ANIM_DURATION  = 150

# max cards are persistent on the table, all others disappear after a second
PERSISTENT_TRUMPS   = {"max17", "max24", "max27"}

# inventory panel layout, computed once to avoid repeating every frame
_PANEL_COLS = 3
_PANEL_GAP  = 8
_PANEL_PAD  = 10
PANEL_W = _PANEL_COLS * TRUMP_W + (_PANEL_COLS - 1) * _PANEL_GAP + _PANEL_PAD * 2

# colours
BLACK       = (0,   0,   0)
WHITE       = (255, 255, 255)
DARK_BG     = (15,  15,  20)
PANEL_BG    = (25,  25,  35)
CARD_COL    = (220, 210, 190)
CARD_HIDDEN = (60,  60,  80)
CARD_OUT    = (60,  60,  80)
RED         = (200, 40,  40)
GREEN       = (60,  180, 80)
YELLOW      = (220, 190, 50)
GREY        = (100, 100, 120)
DIM         = (60,  60,  75)
ORANGE      = (220, 130, 40)

# maps trump card names to their sprite filenames (without extension)
TRUMP_SPRITE_NAMES = {
    "max17":        "gofor17",
    "max24":        "gofor24",
    "max27":        "gofor27",
    "reset_deck":   "reset_deck",
    "exchange":     "exchange",
    "friendship":   "friendship",
    "force_draw":   "force_draw",
    "perfect_draw": "perfect_draw",
}

# sprite dicts are empty at import time and filled inside run() after
# the display is initialised, since convert() requires an active display
CARD_SPRITES       = {}
CARD_HIDDEN_SPRITE = None
TRUMP_SPRITES      = {}
BG_SPRITE          = None

# fonts
pygame.init()
FONT_XS      = pygame.font.SysFont("couriernew", 11)
FONT_SM      = pygame.font.SysFont("couriernew", 16)
FONT_BOOK_SM = pygame.font.SysFont("couriernew", 16, bold=True)
FONT_MD      = pygame.font.SysFont("couriernew", 20, bold=True)
FONT_XL      = pygame.font.SysFont("couriernew", 46, bold=True)


def render_with_shadow(surface, font, text, colour, x, y, shadow_col=(0, 0, 0)):
    # blits text twice: once offset in shadow colour, then on top in the real colour
    surface.blit(font.render(text, True, shadow_col), (x + 1, y + 1))
    surface.blit(font.render(text, True, colour),     (x,     y))


def spawn_card_anim(card_anims, owner, hand, now):
    # the new card starts just to the right of where the deck currently ends
    # so it never spawns on top of an existing card
    index    = len(hand) - 1
    target_x = HAND_START_X + index * (CARD_W + CARD_GAP)
    card_anims.append({
        "owner":    owner,
        "index":    index,
        "start_x":  target_x + CARD_W + CARD_GAP + 20,
        "target_x": target_x,
        "start_t":  now,
    })


def _reset_round_state(game):
    # clears hands, redeals opening cards, and resets the cursor position
    # called on round over and game restart to avoid duplicating this block
    game.reset_round()
    deal_opening_hands(game)
    game.inventory_index = 0


def draw_card_rect(surface, value, x, y, highlight=False, hidden=False):
    if hidden:
        # show the hidden card sprite if loaded, otherwise draw a placeholder rect
        if CARD_HIDDEN_SPRITE:
            surface.blit(CARD_HIDDEN_SPRITE, (x, y))
        else:
            pygame.draw.rect(surface, CARD_HIDDEN, (x, y, CARD_W, CARD_H), border_radius=3)
            pygame.draw.rect(surface, GREY,        (x, y, CARD_W, CARD_H), 1, border_radius=3)
            txt = FONT_MD.render("?", True, GREY)
            surface.blit(txt, (x + CARD_W//2 - txt.get_width()//2,
                                y + CARD_H//2 - txt.get_height()//2))
        return

    if value in CARD_SPRITES:
        surface.blit(CARD_SPRITES[value], (x, y))
        if highlight:
            # yellow tint overlay marks the most recently drawn card
            tint = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
            tint.fill((220, 190, 50, 80))
            surface.blit(tint, (x, y))
    else:
        # fallback rect with the card number, used when sprites are missing
        col = YELLOW if highlight else CARD_COL
        pygame.draw.rect(surface, col,      (x, y, CARD_W, CARD_H), border_radius=3)
        pygame.draw.rect(surface, CARD_OUT, (x, y, CARD_W, CARD_H), 1, border_radius=3)
        txt = FONT_MD.render(str(value), True, BLACK)
        surface.blit(txt, (x + CARD_W//2 - txt.get_width()//2,
                            y + CARD_H//2 - txt.get_height()//2))


def draw_trump_card(surface, trump_name, x, y):
    if trump_name in TRUMP_SPRITES:
        surface.blit(TRUMP_SPRITES[trump_name], (x, y))
    else:
        # fallback rect with a shortened label when the sprite file is missing
        pygame.draw.rect(surface, PANEL_BG, (x, y, TRUMP_W, TRUMP_H), border_radius=3)
        pygame.draw.rect(surface, GREY,     (x, y, TRUMP_W, TRUMP_H), 1, border_radius=3)
        txt = FONT_XS.render(trump_name[:6], True, WHITE)
        surface.blit(txt, (x + TRUMP_W//2 - txt.get_width()//2,
                           y + TRUMP_H//2 - txt.get_height()//2))


def draw_active_trumps(surface, active_list, hand_y, is_enemy=False):
    # enemy trumps appear below their deck, player trumps appear above theirs
    if not active_list:
        return
    row_y = hand_y + CARD_H + 6 if is_enemy else hand_y - 30 - TRUMP_H - 6
    for i, (trump_name, _) in enumerate(active_list):
        draw_trump_card(surface, trump_name, HAND_START_X + i * (TRUMP_W + 6), row_y)


def draw_hand(surface, hand, y, label, is_enemy=False, reveal=False, card_anims=None):
    col = RED if is_enemy else GREEN
    # enemy label sits below the deck to leave room above for the trump display
    label_y = y + CARD_H + 4 if is_enemy else y - 20
    render_with_shadow(surface, FONT_SM, label, col, HAND_START_X, label_y)

    owner = "enemy" if is_enemy else "player"
    # cards currently mid-animation are skipped here and drawn separately on top
    animating = {a["index"] for a in (card_anims or []) if a["owner"] == owner}
    for i, card in enumerate(hand):
        if i in animating:
            continue
        x      = HAND_START_X + i * (CARD_W + CARD_GAP)
        hidden = is_enemy and i == 0 and not reveal
        draw_card_rect(surface, int(card.value), x, y,
                       highlight=(i == len(hand) - 1), hidden=hidden)


def draw_book_hud(surface, game, reveal=False):
    # text is blitted directly onto the open book sprite in the background image
    # coordinates match the page positions in map1_casino.png
    INK       = (30,  18,  10)
    INK_RED   = (140, 20,  15)
    INK_GREEN = (15,  80,  25)
    lx, rx    = 344, 496
    ty, by, lh = 194, 294, 22

    visible_sum = sum(int(c.value) for c in game.enemy_hand[1:]) if len(game.enemy_hand) > 1 else 0
    enemy_str = f"ENEMY: {game.enemy_total}" if reveal else f"ENEMY: ?+{visible_sum}"

    for text, col, x, y in [
        (enemy_str,                      INK_RED,   lx, ty),
        (f"PLAYER: {game.player_total}", INK_GREEN, lx, by),
        (f"MAX: {game.current_max}",     INK,       rx, ty),
        (f"ROUND: {game.round_number}",  INK,       rx, ty + lh),
        (f"WINS: {game.consecutive_wins}", INK,     rx, ty + lh*2),
    ]:
        surface.blit(FONT_BOOK_SM.render(text, True, col), (x, y))


def draw_state_label(surface, game, player_stood, can_unstand):
    if game.state == "player_turn":
        text, col = "Your Turn  [Space] Hit   [Shift] Stand   [Tab] Inventory", WHITE
    elif game.state == "enemy_turn":
        text, col = ("Enemy Turn  [Shift] Un-stand   [Tab] Inventory", ORANGE) if can_unstand \
                    else ("Enemy Turn...  [Tab] Inventory", GREY)
    elif game.state == "round_over":
        result = game.round_result.replace("_", " ").upper() if game.round_result else ""
        text, col = f"ROUND OVER  {result}   [ENTER] continue", YELLOW
    elif game.state == "game_over":
        text, col = "Game Over   [R] Restart", RED
    else:
        text, col = "", WHITE
    txt = FONT_SM.render(text, True, col)
    surface.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT - 48))


def draw_inventory(surface, game, inv_x):
    ox = int(inv_x)
    # clip prevents the panel from drawing outside its bounds while sliding
    surface.set_clip(pygame.Rect(ox, 0, PANEL_W, HEIGHT))

    panel = pygame.Surface((PANEL_W, HEIGHT), pygame.SRCALPHA)
    panel.fill((10, 10, 20, 220))
    surface.blit(panel, (ox, 0))
    pygame.draw.line(surface, YELLOW, (ox, 0), (ox, HEIGHT), 2)

    render_with_shadow(surface, FONT_MD, "TRUMP CARDS", YELLOW, ox + _PANEL_PAD, 8)
    pygame.draw.line(surface, YELLOW, (ox, 28), (ox + PANEL_W, 28), 1)

    if not game.player_inventory:
        surface.blit(FONT_SM.render("(empty)", True, GREY), (ox + _PANEL_PAD, 40))
    else:
        for i, trump in enumerate(game.player_inventory[:15]):
            col = i % _PANEL_COLS
            row = i // _PANEL_COLS
            x = ox + _PANEL_PAD + col * (TRUMP_W + _PANEL_GAP)
            y = 36 + row * (TRUMP_H + _PANEL_GAP)
            draw_trump_card(surface, trump, x, y)
            if i == game.inventory_index:
                pygame.draw.rect(surface, YELLOW,
                                 (x-2, y-2, TRUMP_W+4, TRUMP_H+4), 2, border_radius=3)

        selected = game.player_inventory[game.inventory_index]
        render_with_shadow(surface, FONT_SM,
                           selected.replace("_", " ").upper(), YELLOW,
                           ox + _PANEL_PAD, HEIGHT - 46)

    surface.blit(FONT_SM.render("[Enter] Use", True, GREY), (ox + _PANEL_PAD, HEIGHT - 30))
    surface.blit(FONT_SM.render("[Tab] Close", True, GREY), (ox + _PANEL_PAD, HEIGHT - 16))
    surface.set_clip(None)


def draw_round_over_banner(surface, game):
    if game.state not in ("round_over", "game_over"):
        return
    if game.state == "game_over":
        msg, col = "GAME OVER", RED
    elif game.round_result == "player_win":
        msg, col = "YOU WIN",   GREEN
    elif game.round_result == "enemy_win":
        msg, col = "YOU LOSE",  RED
    else:
        msg, col = "DRAW",      YELLOW
    txt = FONT_XL.render(msg, True, col)
    x, y = WIDTH//2 - txt.get_width()//2, HEIGHT//2 - txt.get_height()//2
    pad  = 8
    pygame.draw.rect(surface, PANEL_BG,
                     (x-pad, y-pad, txt.get_width()+pad*2, txt.get_height()+pad*2),
                     border_radius=4)
    surface.blit(txt, (x, y))


def prune_expired_trumps(active_list, now):
    # removes temporary trumps whose display timer has run out
    return [(n, e) for n, e in active_list if e is None or now < e]


def add_trump_to_display(active_list, trump_name, now, other_list=None):
    is_persistent = trump_name in PERSISTENT_TRUMPS
    if is_persistent:
        # max cards are mutually exclusive so the old one is removed from both
        # sides before the new one is added, since current_max is shared
        active_list = [(n, e) for n, e in active_list if n not in PERSISTENT_TRUMPS]
        if other_list is not None:
            other_list[:] = [(n, e) for n, e in other_list if n not in PERSISTENT_TRUMPS]
    expiry = None if is_persistent else now + TRUMP_TEMP_DURATION
    active_list.append((trump_name, expiry))
    return active_list


def run():
    global CARD_SPRITES, CARD_HIDDEN_SPRITE, TRUMP_SPRITES, BG_SPRITE

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("twenty two minus one")

    try:
        BG_SPRITE = pygame.image.load("assets/maps/map1_casino.png").convert()
        print("Background loaded OK")
    except FileNotFoundError:
        print("Background not found, using fill colour")

    try:
        for i in range(1, 12):
            raw = pygame.image.load(f"assets/cards/card_{i:02d}.png").convert_alpha()
            CARD_SPRITES[i] = pygame.transform.scale(raw, (CARD_W, CARD_H))
        raw = pygame.image.load("assets/cards/card_hidden.png").convert_alpha()
        CARD_HIDDEN_SPRITE = pygame.transform.scale(raw, (CARD_W, CARD_H))
        print("Card sprites loaded OK")
    except FileNotFoundError as e:
        print(f"Card sprite not found: {e}")

    for name, filename in TRUMP_SPRITE_NAMES.items():
        try:
            raw = pygame.image.load(f"assets/trumpcards/{filename}.png").convert_alpha()
            TRUMP_SPRITES[name] = pygame.transform.scale(raw, (TRUMP_W, TRUMP_H))
        except FileNotFoundError:
            pass
    print(f"Trump sprites loaded: {list(TRUMP_SPRITES.keys())}")

    clock = pygame.time.Clock()
    game  = GameState()
    deal_opening_hands(game)

    enemy_timer          = 0
    enemy_used_trump     = False
    player_stood         = False
    player_active_trumps = []
    enemy_active_trumps  = []
    inv_x                = float(WIDTH)
    card_anims           = []

    while True:
        now = pygame.time.get_ticks()

        # lerp the inventory panel towards its target position each frame
        target_x = WIDTH - PANEL_W if game.state == "inventory" else WIDTH
        inv_x += (target_x - inv_x) * 0.18
        if abs(inv_x - target_x) < 1:
            inv_x = target_x

        player_active_trumps = prune_expired_trumps(player_active_trumps, now)
        enemy_active_trumps  = prune_expired_trumps(enemy_active_trumps,  now)
        card_anims           = [a for a in card_anims
                                 if now - a["start_t"] < CARD_ANIM_DURATION]

        can_unstand = game.state == "enemy_turn" and player_stood

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:

                if game.state == "inventory":
                    inv_len = len(game.player_inventory)
                    if event.key == pygame.K_TAB:
                        game.state = "player_turn" if not player_stood else "enemy_turn"
                    elif event.key == pygame.K_LEFT:
                        game.inventory_index = max(0, game.inventory_index - 1)
                    elif event.key == pygame.K_RIGHT:
                        game.inventory_index = min(inv_len - 1, game.inventory_index + 1)
                    elif event.key == pygame.K_UP:
                        game.inventory_index = max(0, game.inventory_index - _PANEL_COLS)
                    elif event.key == pygame.K_DOWN:
                        game.inventory_index = min(inv_len - 1, game.inventory_index + _PANEL_COLS)
                    elif event.key == pygame.K_RETURN and game.player_inventory:
                        trump_card = game.player_inventory[game.inventory_index]
                        print(use_trump(game, trump_card, "player"))
                        player_active_trumps = add_trump_to_display(
                            player_active_trumps, trump_card, now,
                            other_list=enemy_active_trumps)
                        game.inventory_index = max(0, game.inventory_index - 1)
                        game.state = "player_turn" if not player_stood else "enemy_turn"

                elif game.state == "player_turn":
                    if event.key == pygame.K_SPACE:
                        player_hit(game)
                        spawn_card_anim(card_anims, "player", game.player_hand, now)
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        player_stand(game)
                        player_stood     = True
                        enemy_timer      = now + ENEMY_STEP_DELAY
                        enemy_used_trump = False
                    elif event.key == pygame.K_TAB:
                        game.state = "inventory"

                elif game.state == "enemy_turn":
                    if event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT) and can_unstand:
                        game.state   = "player_turn"
                        player_stood = False
                    elif event.key == pygame.K_TAB:
                        game.state = "inventory"

                elif game.state == "round_over":
                    if event.key == pygame.K_RETURN:
                        distribute_trumps(game)
                        _reset_round_state(game)
                        player_stood         = False
                        enemy_used_trump     = False
                        player_active_trumps = []
                        enemy_active_trumps  = []
                        card_anims           = []
                        inv_x                = float(WIDTH)

                elif game.state == "game_over":
                    if event.key == pygame.K_r:
                        game = GameState()
                        deal_opening_hands(game)
                        player_stood         = False
                        enemy_used_trump     = False
                        player_active_trumps = []
                        enemy_active_trumps  = []
                        card_anims           = []
                        inv_x                = float(WIDTH)

        if game.state == "enemy_turn" and now >= enemy_timer:
            if not enemy_used_trump:
                # snapshot the inventory before the AI acts so we can detect which
                # trump was used and add it to the active display
                inv_before = list(game.enemy_inventory)
                result = run_enemy_trumps(game)
                if result:
                    print(result)
                    used = [a for a in inv_before if a not in game.enemy_inventory]
                    if used:
                        enemy_active_trumps = add_trump_to_display(
                            enemy_active_trumps, used[0], now,
                            other_list=player_active_trumps)
                enemy_used_trump = True
                enemy_timer      = now + ENEMY_STEP_DELAY
            elif game.enemy_total > game.current_max or enemy_should_stand(game):
                resolve_round(game)
            else:
                draw_card(game, "enemy")
                spawn_card_anim(card_anims, "enemy", game.enemy_hand, now)
                enemy_timer = now + ENEMY_STEP_DELAY

        reveal = game.state in ("round_over", "game_over")

        if BG_SPRITE:
            screen.blit(BG_SPRITE, (0, 0))
        else:
            screen.fill(DARK_BG)

        draw_active_trumps(screen, enemy_active_trumps,  ENEMY_HAND_Y,  is_enemy=True)
        draw_active_trumps(screen, player_active_trumps, PLAYER_HAND_Y, is_enemy=False)
        draw_hand(screen, game.enemy_hand,  ENEMY_HAND_Y,  "ENEMY",
                  is_enemy=True,  reveal=reveal, card_anims=card_anims)
        draw_hand(screen, game.player_hand, PLAYER_HAND_Y, "PLAYER",
                  is_enemy=False, reveal=True,   card_anims=card_anims)

        # animating cards are drawn last so they appear on top of everything
        for a in card_anims:
            t      = min(1.0, (now - a["start_t"]) / CARD_ANIM_DURATION)
            t_ease = 1 - (1 - t) ** 2
            ax     = int(a["start_x"] + (a["target_x"] - a["start_x"]) * t_ease)
            hand   = game.enemy_hand if a["owner"] == "enemy" else game.player_hand
            hand_y = ENEMY_HAND_Y   if a["owner"] == "enemy" else PLAYER_HAND_Y
            if a["index"] < len(hand):
                hidden    = a["owner"] == "enemy" and a["index"] == 0 and not reveal
                highlight = a["index"] == len(hand) - 1
                draw_card_rect(screen, int(hand[a["index"]].value),
                               ax, hand_y, highlight, hidden)

        draw_book_hud(screen, game, reveal=reveal)
        draw_state_label(screen, game, player_stood, can_unstand)
        draw_round_over_banner(screen, game)

        if int(inv_x) < WIDTH:
            draw_inventory(screen, game, inv_x)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    run()