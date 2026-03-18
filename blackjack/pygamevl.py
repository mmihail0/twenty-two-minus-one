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

CARD_W, CARD_H   = 64, 90
ABILITY_W, ABILITY_H = 32, 45
CARD_GAP         = 14
PLAYER_HAND_Y    = HEIGHT - 150
ENEMY_HAND_Y     = 55
HAND_START_X     = 36

ENEMY_STEP_DELAY = 1000

# ability display constants
ABILITY_TEMP_DURATION = 1000   # ms a temporary ability stays visible
PERSISTENT_ABILITIES  = {"max17", "max24", "max27"}

# sprite name mapping — ability name -> png filename (without extension)
ABILITY_SPRITE_NAMES = {
    "max17":        "gofor17",
    "max24":        "gofor24",
    "max27":        "gofor27",
    "reset_deck":   "reset_deck",
    "exchange":    "exchange",
    "friendship":   "friendship",
    "force_draw":   "force_draw",
    "draw2":        "draw2",
    "draw4":        "draw4",
    "draw6":        "draw6",
    "perfect_draw": "perfect_draw",
}

# placeholders — populated inside run() after display is set
CARD_SPRITES       = {}
CARD_HIDDEN_SPRITE = None
ABILITY_SPRITES    = {}   # ability_name -> scaled surface (32x45)

pygame.init()
FONT_SM = pygame.font.SysFont("couriernew", 16)
FONT_XS = pygame.font.SysFont("couriernew", 11)
FONT_MD = pygame.font.SysFont("couriernew", 20, bold=True)
FONT_LG = pygame.font.SysFont("couriernew", 28, bold=True)
FONT_XL = pygame.font.SysFont("couriernew", 46, bold=True)


def draw_card_rect(surface, value, x, y, highlight=False, hidden=False):
    if hidden:
        if CARD_HIDDEN_SPRITE:
            surface.blit(CARD_HIDDEN_SPRITE, (x, y))
            return
        pygame.draw.rect(surface, CARD_HIDDEN, (x, y, CARD_W, CARD_H), border_radius=3)
        pygame.draw.rect(surface, GREY, (x, y, CARD_W, CARD_H), 1, border_radius=3)
        txt = FONT_MD.render("?", True, GREY)
        surface.blit(txt, (x + CARD_W // 2 - txt.get_width() // 2,
                            y + CARD_H // 2 - txt.get_height() // 2))
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
    surface.blit(txt, (x + CARD_W // 2 - txt.get_width() // 2,
                        y + CARD_H // 2 - txt.get_height() // 2))


def draw_ability_card(surface, ability_name, x, y):
    """Draw a single ability card sprite (or fallback rect) at (x, y)."""
    if ability_name in ABILITY_SPRITES:
        surface.blit(ABILITY_SPRITES[ability_name], (x, y))
    else:
        # fallback: dark rect with abbreviated label
        pygame.draw.rect(surface, PANEL_BG, (x, y, ABILITY_W, ABILITY_H), border_radius=3)
        pygame.draw.rect(surface, GREY, (x, y, ABILITY_W, ABILITY_H), 1, border_radius=3)
        label = ability_name[:6]
        txt = FONT_XS.render(label, True, WHITE)
        surface.blit(txt, (x + ABILITY_W // 2 - txt.get_width() // 2,
                           y + ABILITY_H // 2 - txt.get_height() // 2))


def draw_active_abilities(surface, active_list, hand_y, is_enemy=False):
    """Render active ability cards — below enemy hand, above player hand."""
    if not active_list:
        return
    if is_enemy:
        row_y = hand_y + CARD_H + 6
    else:
        row_y = hand_y - 30 - ABILITY_H - 6
    for i, (ability_name, _expiry) in enumerate(active_list):
        x = HAND_START_X + i * (ABILITY_W + 6)
        draw_ability_card(surface, ability_name, x, row_y)


def prune_expired_abilities(active_list, now):
    """Remove temporary abilities whose display timer has elapsed."""
    return [(name, expiry) for name, expiry in active_list
            if expiry is None or now < expiry]


def add_ability_to_display(active_list, ability_name, now):
    """Add an ability to the display list, handling persistence and max-card replacement."""
    is_persistent = ability_name in PERSISTENT_ABILITIES
    # if it's a max card, remove any existing max card first
    if is_persistent:
        active_list = [(n, e) for n, e in active_list if n not in PERSISTENT_ABILITIES]
    expiry = None if is_persistent else now + ABILITY_TEMP_DURATION
    active_list.append((ability_name, expiry))
    return active_list


def draw_hand(surface, hand, y, label, total, is_enemy=False, reveal=False):
    col = RED if is_enemy else GREEN
    if is_enemy and not reveal:
        visible_sum = sum(int(c.value) for c in hand[1:]) if len(hand) > 1 else 0
        label_txt = f"{label}  total: ? + {visible_sum}"
    else:
        label_txt = f"{label}  total: {total}"
    lbl = FONT_SM.render(label_txt, True, col)
    surface.blit(lbl, (HAND_START_X, y - 30))
    for i, card in enumerate(hand):
        x = HAND_START_X + i * (CARD_W + CARD_GAP)
        highlight = (i == len(hand) - 1)
        hidden = (is_enemy and i == 0 and not reveal)
        draw_card_rect(surface, int(card.value), x, y, highlight, hidden=hidden)


def draw_hud(surface, game):
    max_txt   = FONT_SM.render(f"MAX: {game.current_max}", True, YELLOW)
    round_txt = FONT_SM.render(f"ROUND: {game.round_number}", True, WHITE)
    wins_txt  = FONT_SM.render(f"WINS IN A ROW: {game.consecutive_wins}", True, GREEN)
    surface.blit(max_txt,   (WIDTH - 160, 10))
    surface.blit(round_txt, (WIDTH - 160, 28))
    surface.blit(wins_txt,  (WIDTH - 160, 46))


def draw_state_label(surface, game, player_stood, can_unstand):
    if game.state == "player_turn":
        text, colour = "YOUR TURN  [SPACE] hit   [SHIFT] stand   [TAB] inventory", WHITE
    elif game.state == "enemy_turn":
        if can_unstand:
            text, colour = "ENEMY TURN  [SHIFT] un-stand   [TAB] inventory", ORANGE
        else:
            text, colour = "ENEMY TURN...  [TAB] inventory", GREY
    elif game.state == "round_over":
        result_str = game.round_result.replace("_", " ").upper() if game.round_result else ""
        text, colour = f"ROUND OVER  {result_str}   [ENTER] continue", YELLOW
    elif game.state == "game_over":
        text, colour = "GAME OVER   [R] restart", RED
    else:
        text, colour = "", WHITE
    txt = FONT_SM.render(text, True, colour)
    surface.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT - 16))


def draw_inventory(surface, game):
    panel_w = 160
    panel   = pygame.Surface((panel_w, HEIGHT), pygame.SRCALPHA)
    panel.fill((10, 10, 20, 210))
    surface.blit(panel, (WIDTH - panel_w, 0))
    title = FONT_MD.render("INVENTORY", True, YELLOW)
    surface.blit(title, (WIDTH - panel_w + 8, 10))
    pygame.draw.line(surface, YELLOW, (WIDTH - panel_w, 26), (WIDTH, 26), 1)
    if not game.player_inventory:
        none_txt = FONT_SM.render("(empty)", True, GREY)
        surface.blit(none_txt, (WIDTH - panel_w + 8, 40))
        return
    for i, ability in enumerate(game.player_inventory):
        y     = 38 + i * 18
        col   = WHITE if i == game.inventory_index else DIM
        arrow = "> " if i == game.inventory_index else "  "
        txt   = FONT_SM.render(f"{arrow}{ability}", True, col)
        surface.blit(txt, (WIDTH - panel_w + 6, y))
    hint = FONT_SM.render("[ENTER] use  [TAB] close", True, GREY)
    surface.blit(hint, (WIDTH - panel_w + 4, HEIGHT - 20))


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
    x   = WIDTH  // 2 - txt.get_width()  // 2
    y   = HEIGHT // 2 - txt.get_height() // 2
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
    global CARD_SPRITES, CARD_HIDDEN_SPRITE, ABILITY_SPRITES

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("21 — RE7 Blackjack")

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

    # load ability sprites — silently skip missing ones, fallback rect used instead
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

    enemy_timer          = 0
    enemy_used_ability   = False
    player_stood         = False
    player_active_abilities = []   # list of (ability_name, expiry_ms or None)
    enemy_active_abilities  = []

    while True:
        now = pygame.time.get_ticks()

        # prune expired temporary abilities each frame
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
                    elif event.key == pygame.K_UP:
                        game.inventory_index = max(0, game.inventory_index - 1)
                    elif event.key == pygame.K_DOWN:
                        game.inventory_index = min(
                            len(game.player_inventory) - 1,
                            game.inventory_index + 1
                        )
                    elif event.key == pygame.K_RETURN:
                        if game.player_inventory:
                            from trump import use_ability
                            ability = game.player_inventory[game.inventory_index]
                            result = use_ability(game, ability, "player")
                            print(result)
                            player_active_abilities = add_ability_to_display(
                                player_active_abilities, ability, now)
                            game.inventory_index = max(0, game.inventory_index - 1)
                            game.state = "player_turn" if not player_stood else "enemy_turn"

                elif game.state == "player_turn":
                    if event.key == pygame.K_SPACE:
                        player_hit(game)
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
                        # clear ability display on new round
                        player_active_abilities = []
                        enemy_active_abilities  = []

                elif game.state == "game_over":
                    if event.key == pygame.K_r:
                        game = GameState()
                        game.inventory_index = 0
                        deal_opening_hands(game)
                        player_stood            = False
                        enemy_used_ability      = False
                        player_active_abilities = []
                        enemy_active_abilities  = []

        # enemy acts one step per second
        if game.state == "enemy_turn" and now >= enemy_timer:
            if not enemy_used_ability:
                # snapshot inventory before so we can detect what was used
                inv_before = list(game.enemy_inventory)
                result = run_enemy_abilities(game)
                if result:
                    print(result)
                    # find which ability was consumed
                    inv_after = game.enemy_inventory
                    used = [a for a in inv_before if a not in inv_after]
                    if used:
                        enemy_active_abilities = add_ability_to_display(
                            enemy_active_abilities, used[0], now)
                enemy_used_ability = True
                enemy_timer = now + ENEMY_STEP_DELAY
            else:
                if game.enemy_total > game.current_max or enemy_should_stand(game):
                    resolve_round(game)
                else:
                    draw_card(game, "enemy")
                    enemy_timer = now + ENEMY_STEP_DELAY

        reveal = game.state in ("round_over", "game_over")

        screen.fill(DARK_BG)
        draw_active_abilities(screen, enemy_active_abilities,  ENEMY_HAND_Y,   is_enemy=True)
        draw_active_abilities(screen, player_active_abilities, PLAYER_HAND_Y,  is_enemy=False)
        draw_hand(screen, game.enemy_hand,  ENEMY_HAND_Y,  "ENEMY",  game.enemy_total,  is_enemy=True,  reveal=reveal)
        draw_hand(screen, game.player_hand, PLAYER_HAND_Y, "PLAYER", game.player_total, is_enemy=False, reveal=True)
        draw_hud(screen, game)
        draw_state_label(screen, game, player_stood, can_unstand)
        draw_round_over_banner(screen, game)
        if game.state == "inventory":
            draw_inventory(screen, game)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    run()