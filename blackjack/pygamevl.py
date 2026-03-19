import pygame
import sys
from game_logic import (
    GameState, deal_opening_hands, player_hit, player_stand,
    draw_card, resolve_round, distribute_abilities, enemy_should_stand
)
from trump import run_enemy_abilities

WIDTH, HEIGHT = 960, 540
FPS           = 30

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

CARD_W, CARD_H       = 64, 90
ABILITY_W, ABILITY_H = 48, 67
CARD_GAP             = 14
PLAYER_HAND_Y        = HEIGHT - 150
ENEMY_HAND_Y         = 55
HAND_START_X         = 36

ENEMY_STEP_DELAY      = 1000
ABILITY_TEMP_DURATION = 1000
CARD_ANIM_DURATION    = 150
PERSISTENT_ABILITIES  = {"max17", "max24", "max27"}

ABILITY_SPRITE_NAMES = {
    "max17":        "gofor17",
    "max24":        "gofor24",
    "max27":        "gofor27",
    "reset_deck":   "reset_deck",
    "exchange":     "exchange",
    "friendship":   "friendship",
    "force_draw":   "force_draw",
    "perfect_draw": "perfect_draw",
}

# placeholders — populated inside run() after display is set
CARD_SPRITES       = {}
CARD_HIDDEN_SPRITE = None
ABILITY_SPRITES    = {}
BG_SPRITE          = None

pygame.init()
FONT_SM      = pygame.font.SysFont("couriernew", 16)
FONT_BOOK_SM = pygame.font.SysFont("couriernew", 16, bold=True)
FONT_CTRL    = pygame.font.SysFont("couriernew", 18, bold=True)
FONT_XS = pygame.font.SysFont("couriernew", 11)
FONT_MD = pygame.font.SysFont("couriernew", 20, bold=True)
FONT_LG = pygame.font.SysFont("couriernew", 28, bold=True)
FONT_XL = pygame.font.SysFont("couriernew", 46, bold=True)


def render_with_shadow(surface, font, text, colour, x, y, shadow_offset=1, shadow_col=(0, 0, 0)):
    shadow = font.render(text, True, shadow_col)
    surface.blit(shadow, (x + shadow_offset, y + shadow_offset))
    txt = font.render(text, True, colour)
    surface.blit(txt, (x, y))


def spawn_card_anim(card_anims, owner, hand, now):
    """Start a slide-in animation for the most recently added card."""
    index    = len(hand) - 1
    target_x = HAND_START_X + index * (CARD_W + CARD_GAP)
    start_x  = target_x + CARD_W + CARD_GAP + 20   # just right of current deck
    card_anims.append({
        "owner":    owner,
        "index":    index,
        "start_x":  start_x,
        "target_x": target_x,
        "start_t":  now,
    })


def draw_card_rect(surface, value, x, y, highlight=False, hidden=False):
    if hidden:
        if CARD_HIDDEN_SPRITE:
            surface.blit(CARD_HIDDEN_SPRITE, (x, y))
            return
        pygame.draw.rect(surface, CARD_HIDDEN, (x, y, CARD_W, CARD_H), border_radius=3)
        pygame.draw.rect(surface, GREY, (x, y, CARD_W, CARD_H), 1, border_radius=3)
        txt = FONT_MD.render("?", True, GREY)
        surface.blit(txt, (x + CARD_W//2 - txt.get_width()//2,
                            y + CARD_H//2 - txt.get_height()//2))
        return
    if value in CARD_SPRITES:
        sprite = CARD_SPRITES[value]
        if highlight:
            tint = pygame.Surface((CARD_W, CARD_H), pygame.SRCALPHA)
            tint.fill((220, 190, 50, 80))
            surface.blit(sprite, (x, y))
            surface.blit(tint, (x, y))
        else:
            surface.blit(sprite, (x, y))
        return
    colour = YELLOW if highlight else CARD_COL
    pygame.draw.rect(surface, colour, (x, y, CARD_W, CARD_H), border_radius=3)
    pygame.draw.rect(surface, CARD_OUT, (x, y, CARD_W, CARD_H), 1, border_radius=3)
    txt = FONT_MD.render(str(value), True, BLACK)
    surface.blit(txt, (x + CARD_W//2 - txt.get_width()//2,
                        y + CARD_H//2 - txt.get_height()//2))


def draw_ability_card(surface, ability_name, x, y):
    if ability_name in ABILITY_SPRITES:
        surface.blit(ABILITY_SPRITES[ability_name], (x, y))
    else:
        pygame.draw.rect(surface, PANEL_BG, (x, y, ABILITY_W, ABILITY_H), border_radius=3)
        pygame.draw.rect(surface, GREY, (x, y, ABILITY_W, ABILITY_H), 1, border_radius=3)
        txt = FONT_XS.render(ability_name[:6], True, WHITE)
        surface.blit(txt, (x + ABILITY_W//2 - txt.get_width()//2,
                           y + ABILITY_H//2 - txt.get_height()//2))


def draw_active_abilities(surface, active_list, hand_y, is_enemy=False):
    if not active_list:
        return
    row_y = hand_y + CARD_H + 6 if is_enemy else hand_y - 30 - ABILITY_H - 6
    for i, (ability_name, _expiry) in enumerate(active_list):
        x = HAND_START_X + i * (ABILITY_W + 6)
        draw_ability_card(surface, ability_name, x, row_y)


def prune_expired_abilities(active_list, now):
    return [(name, expiry) for name, expiry in active_list
            if expiry is None or now < expiry]


def add_ability_to_display(active_list, ability_name, now, other_list=None):
    is_persistent = ability_name in PERSISTENT_ABILITIES
    if is_persistent:
        active_list = [(n, e) for n, e in active_list if n not in PERSISTENT_ABILITIES]
        if other_list is not None:
            other_list[:] = [(n, e) for n, e in other_list if n not in PERSISTENT_ABILITIES]
    expiry = None if is_persistent else now + ABILITY_TEMP_DURATION
    active_list.append((ability_name, expiry))
    return active_list


def draw_hand(surface, hand, y, label, total, is_enemy=False, reveal=False, card_anims=None):
    col = RED if is_enemy else GREEN
    if is_enemy:
        render_with_shadow(surface, FONT_SM, label, col, HAND_START_X, y + CARD_H + 4)
    else:
        render_with_shadow(surface, FONT_SM, label, col, HAND_START_X, y - 20)
    owner = "enemy" if is_enemy else "player"
    animating_indices = {a["index"] for a in (card_anims or []) if a["owner"] == owner}
    for i, card in enumerate(hand):
        if i in animating_indices:
            continue   # drawn by animation system instead
        x = HAND_START_X + i * (CARD_W + CARD_GAP)
        highlight = (i == len(hand) - 1)
        hidden = (is_enemy and i == 0 and not reveal)
        draw_card_rect(surface, int(card.value), x, y, highlight, hidden=hidden)


def draw_book_hud(surface, game, reveal=False):
    # Open book coordinates (match map1_gothic.png)
    # Left page x=334-474, right page x=486-626, y=182-342
    INK       = (30,  18,  10)
    INK_RED   = (140, 20,  15)
    INK_GREEN = (15,  80,  25)
    left_x, right_x = 344, 496
    page_top, page_bot, line_h = 194, 294, 22

    if reveal:
        enemy_str = f"ENEMY: {game.enemy_total}"
    else:
        visible_sum = sum(int(c.value) for c in game.enemy_hand[1:]) if len(game.enemy_hand) > 1 else 0
        enemy_str = f"ENEMY: ?+{visible_sum}"
    surface.blit(FONT_BOOK_SM.render(enemy_str, True, INK_RED), (left_x, page_top))
    surface.blit(FONT_BOOK_SM.render(f"PLAYER: {game.player_total}", True, INK_GREEN), (left_x, page_bot))
    surface.blit(FONT_BOOK_SM.render(f"MAX: {game.current_max}", True, INK), (right_x, page_top))
    surface.blit(FONT_BOOK_SM.render(f"ROUND: {game.round_number}", True, INK), (right_x, page_top + line_h))
    surface.blit(FONT_BOOK_SM.render(f"WINS: {game.consecutive_wins}", True, INK), (right_x, page_top + line_h*2))


def draw_state_label(surface, game, player_stood, can_unstand):
    if game.state == "player_turn":
        text, colour = "Your Turn  [Space] Hit   [Shift] Stand   [Tab] Inventory", WHITE
    elif game.state == "enemy_turn":
        if can_unstand:
            text, colour = "Enemy Turn  [Shift] Un-stand   [Tab] Inventory", ORANGE
        else:
            text, colour = "Enemy Turn...  [Tab] Inventory", GREY
    elif game.state == "round_over":
        result_str = game.round_result.replace("_", " ").upper() if game.round_result else ""
        text, colour = f"ROUND OVER  {result_str}   [ENTER] continue", YELLOW
    elif game.state == "game_over":
        text, colour = "Game Over   [R] Restart", RED
    else:
        text, colour = "", WHITE
    txt = FONT_SM.render(text, True, colour)
    surface.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT - 48))


def draw_inventory(surface, game, inv_x=None):
    cols    = 3
    gap     = 8
    pad     = 10
    panel_w = cols * ABILITY_W + (cols - 1) * gap + pad * 2
    ox      = int(inv_x) if inv_x is not None else WIDTH - panel_w  # panel left edge

    # clip drawing to avoid spillover when sliding
    surface.set_clip(pygame.Rect(ox, 0, panel_w, HEIGHT))

    panel = pygame.Surface((panel_w, HEIGHT), pygame.SRCALPHA)
    panel.fill((10, 10, 20, 220))
    surface.blit(panel, (ox, 0))

    # gold left edge line
    pygame.draw.line(surface, YELLOW, (ox, 0), (ox, HEIGHT), 2)

    render_with_shadow(surface, FONT_MD, "INVENTORY", YELLOW, ox + pad, 8)
    pygame.draw.line(surface, YELLOW, (ox, 28), (ox + panel_w, 28), 1)

    if not game.player_inventory:
        none_txt = FONT_SM.render("(empty)", True, GREY)
        surface.blit(none_txt, (ox + pad, 40))
    else:
        for i, ability in enumerate(game.player_inventory[:15]):
            col = i % cols
            row = i // cols
            x = ox + pad + col * (ABILITY_W + gap)
            y = 36 + row * (ABILITY_H + gap)
            draw_ability_card(surface, ability, x, y)
            if i == game.inventory_index:
                pygame.draw.rect(surface, YELLOW,
                                 (x - 2, y - 2, ABILITY_W + 4, ABILITY_H + 4), 2, border_radius=3)

    if game.player_inventory:
        selected = game.player_inventory[game.inventory_index]
        render_with_shadow(surface, FONT_SM, selected.replace("_", " ").upper(), YELLOW, ox + pad, HEIGHT - 46)
    hint  = FONT_SM.render("[Enter] Use", True, GREY)
    hint2 = FONT_SM.render("[Tab] Close", True, GREY)
    surface.blit(hint,  (ox + pad, HEIGHT - 30))
    surface.blit(hint2, (ox + pad, HEIGHT - 16))

    surface.set_clip(None)


def draw_round_over_banner(surface, game):
    if game.state not in ("round_over", "game_over"):
        return
    if game.state == "game_over":
        msg, col = "GAME OVER", RED
    elif game.round_result == "player_win":
        msg, col = "YOU WIN", GREEN
    elif game.round_result == "enemy_win":
        msg, col = "YOU LOSE", RED
    else:
        msg, col = "DRAW", YELLOW
    txt = FONT_XL.render(msg, True, col)
    x   = WIDTH//2  - txt.get_width()//2
    y   = HEIGHT//2 - txt.get_height()//2
    pad = 8
    pygame.draw.rect(surface, PANEL_BG,
                     (x - pad, y - pad, txt.get_width() + pad*2, txt.get_height() + pad*2),
                     border_radius=4)
    surface.blit(txt, (x, y))


def start_round(game):
    game.reset_round()
    deal_opening_hands(game)
    game.inventory_index = 0


def run():
    global CARD_SPRITES, CARD_HIDDEN_SPRITE, ABILITY_SPRITES, BG_SPRITE

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("21 — RE7 Blackjack")

    # load background map
    try:
        BG_SPRITE = pygame.image.load("assets/maps/map1_casino.png").convert()
        print("Background loaded OK")
    except FileNotFoundError:
        print("Background not found, using fill colour")

    # load card sprites
    try:
        for i in range(1, 12):
            raw = pygame.image.load(f"assets/cards/card_{i:02d}.png").convert_alpha()
            CARD_SPRITES[i] = pygame.transform.scale(raw, (CARD_W, CARD_H))
        raw_hidden = pygame.image.load("assets/cards/card_hidden.png").convert_alpha()
        CARD_HIDDEN_SPRITE = pygame.transform.scale(raw_hidden, (CARD_W, CARD_H))
        print("Card sprites loaded OK")
    except FileNotFoundError as e:
        print(f"Card sprite not found, using fallback rects: {e}")

    # load ability sprites — silently skip missing ones
    for ability_name, filename in ABILITY_SPRITE_NAMES.items():
        try:
            raw = pygame.image.load(f"assets/abilities/{filename}.png").convert_alpha()
            ABILITY_SPRITES[ability_name] = pygame.transform.scale(raw, (ABILITY_W, ABILITY_H))
        except FileNotFoundError:
            pass
    print(f"Ability sprites loaded: {list(ABILITY_SPRITES.keys())}")

    clock = pygame.time.Clock()

    game = GameState()
    game.inventory_index = 0
    deal_opening_hands(game)

    enemy_timer             = 0
    enemy_used_ability      = False
    player_stood            = False
    player_active_abilities = []
    enemy_active_abilities  = []
    inv_x               = WIDTH
    card_anims          = []   # active card slide animations      # current x position of inventory panel (slides in from right)

    while True:
        now = pygame.time.get_ticks()

        # slide inventory panel in/out
        cols    = 3
        gap     = 8
        pad     = 10
        panel_w = cols * ABILITY_W + (cols - 1) * gap + pad * 2
        target_x = WIDTH - panel_w if game.state == "inventory" else WIDTH
        inv_x += (target_x - inv_x) * 0.18
        if abs(inv_x - target_x) < 1:
            inv_x = target_x


        player_active_abilities = prune_expired_abilities(player_active_abilities, now)
        enemy_active_abilities  = prune_expired_abilities(enemy_active_abilities, now)

        can_unstand = (game.state == "enemy_turn" and player_stood)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:

                if game.state == "inventory":
                    if event.key == pygame.K_TAB:
                        game.state = "player_turn" if not player_stood else "enemy_turn"
                    elif event.key == pygame.K_LEFT:
                        game.inventory_index = max(0, game.inventory_index - 1)
                    elif event.key == pygame.K_RIGHT:
                        game.inventory_index = min(
                            len(game.player_inventory) - 1,
                            game.inventory_index + 1)
                    elif event.key == pygame.K_UP:
                        game.inventory_index = max(0, game.inventory_index - 3)
                    elif event.key == pygame.K_DOWN:
                        game.inventory_index = min(
                            len(game.player_inventory) - 1,
                            game.inventory_index + 3)
                    elif event.key == pygame.K_RETURN:
                        if game.player_inventory:
                            from trump import use_ability
                            ability = game.player_inventory[game.inventory_index]
                            result = use_ability(game, ability, "player")
                            print(result)
                            player_active_abilities = add_ability_to_display(
                                player_active_abilities, ability, now,
                                other_list=enemy_active_abilities)
                            game.inventory_index = max(0, game.inventory_index - 1)
                            game.state = "player_turn" if not player_stood else "enemy_turn"

                elif game.state == "player_turn":
                    if event.key == pygame.K_SPACE:
                        player_hit(game)
                        spawn_card_anim(card_anims, "player", game.player_hand, now)
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        player_stand(game)
                        player_stood       = True
                        enemy_timer        = now + ENEMY_STEP_DELAY
                        enemy_used_ability = False
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
                        distribute_abilities(game)
                        start_round(game)
                        player_stood            = False
                        enemy_used_ability      = False
                        player_active_abilities = []
                        enemy_active_abilities  = []
                        card_anims              = []
                        inv_x                   = WIDTH

                elif game.state == "game_over":
                    if event.key == pygame.K_r:
                        game = GameState()
                        game.inventory_index = 0
                        deal_opening_hands(game)
                        player_stood            = False
                        enemy_used_ability      = False
                        player_active_abilities = []
                        enemy_active_abilities  = []
                        card_anims              = []
                        inv_x                   = WIDTH

        # enemy acts one step per second
        if game.state == "enemy_turn" and now >= enemy_timer:
            if not enemy_used_ability:
                inv_before = list(game.enemy_inventory)
                result = run_enemy_abilities(game)
                if result:
                    print(result)
                    used = [a for a in inv_before if a not in game.enemy_inventory]
                    if used:
                        enemy_active_abilities = add_ability_to_display(
                            enemy_active_abilities, used[0], now,
                            other_list=player_active_abilities)
                enemy_used_ability = True
                enemy_timer = now + ENEMY_STEP_DELAY
            else:
                if game.enemy_total > game.current_max or enemy_should_stand(game):
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
        draw_active_abilities(screen, enemy_active_abilities,  ENEMY_HAND_Y,  is_enemy=True)
        draw_active_abilities(screen, player_active_abilities, PLAYER_HAND_Y, is_enemy=False)
        draw_hand(screen, game.enemy_hand,  ENEMY_HAND_Y,  "ENEMY",  game.enemy_total,  is_enemy=True,  reveal=reveal, card_anims=card_anims)
        draw_hand(screen, game.player_hand, PLAYER_HAND_Y, "PLAYER", game.player_total, is_enemy=False, reveal=True,  card_anims=card_anims)

        # draw animating cards on top
        for a in card_anims:
            t = min(1.0, (now - a["start_t"]) / CARD_ANIM_DURATION)
            # ease out: decelerate as it arrives
            t_ease = 1 - (1 - t) ** 2
            ax = int(a["start_x"] + (a["target_x"] - a["start_x"]) * t_ease)
            hand_y = ENEMY_HAND_Y if a["owner"] == "enemy" else PLAYER_HAND_Y
            hand   = game.enemy_hand if a["owner"] == "enemy" else game.player_hand
            if a["index"] < len(hand):
                card    = hand[a["index"]]
                hidden  = (a["owner"] == "enemy" and a["index"] == 0 and not reveal)
                highlight = (a["index"] == len(hand) - 1)
                draw_card_rect(screen, int(card.value), ax, hand_y, highlight, hidden=hidden)
        draw_book_hud(screen, game, reveal=reveal)
        draw_state_label(screen, game, player_stood, can_unstand)
        draw_round_over_banner(screen, game)
        if game.state == "inventory" or int(inv_x) < WIDTH:
            draw_inventory(screen, game, inv_x)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    run()