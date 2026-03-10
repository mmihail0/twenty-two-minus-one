import pygame
import sys
from game_logic import (
    GameState, deal_opening_hands, player_hit, player_stand,
    run_enemy_turn, resolve_round, distribute_abilities
)

WIDTH, HEIGHT = 960, 540
FPS           = 30

# colours
BLACK      = (0,   0,   0)
WHITE      = (255, 255, 255)
DARK_BG    = (15,  15,  20)
PANEL_BG   = (25,  25,  35)
CARD_COL   = (220, 210, 190)
CARD_OUT   = (60,  60,  80)
RED        = (200, 40,  40)
GREEN      = (60,  180, 80)
YELLOW     = (220, 190, 50)
GREY       = (100, 100, 120)
DIM        = (60,  60,  75)

# card and layout sizes
CARD_W, CARD_H = 56, 78
CARD_GAP       = 14
PLAYER_HAND_Y  = HEIGHT - 150
ENEMY_HAND_Y   = 55
HAND_START_X   = 36

pygame.init()
FONT_SM  = pygame.font.SysFont("couriernew", 16)
FONT_MD  = pygame.font.SysFont("couriernew", 20, bold=True)
FONT_LG  = pygame.font.SysFont("couriernew", 28, bold=True)
FONT_XL  = pygame.font.SysFont("couriernew", 46, bold=True)


def draw_card_rect(surface, value, x, y, highlight=False):
    # most recently drawn card gets highlighted yellow
    colour = YELLOW if highlight else CARD_COL
    pygame.draw.rect(surface, colour, (x, y, CARD_W, CARD_H), border_radius=3)
    pygame.draw.rect(surface, CARD_OUT, (x, y, CARD_W, CARD_H), 1, border_radius=3)
    txt = FONT_MD.render(str(value), True, BLACK)
    surface.blit(txt, (x + CARD_W // 2 - txt.get_width() // 2,
                        y + CARD_H // 2 - txt.get_height() // 2))


def draw_hand(surface, hand, y, label, total, is_enemy=False):
    col = RED if is_enemy else GREEN
    lbl = FONT_SM.render(f"{label}  total: {total}", True, col)
    surface.blit(lbl, (HAND_START_X, y - 14))
    for i, card in enumerate(hand):
        x = HAND_START_X + i * (CARD_W + CARD_GAP)
        highlight = (i == len(hand) - 1)
        draw_card_rect(surface, card.value, x, y, highlight)


def draw_hud(surface, game):
    # top-right corner: bust limit, round number, loss streak
    max_txt    = FONT_SM.render(f"MAX: {game.current_max}", True, YELLOW)
    round_txt  = FONT_SM.render(f"ROUND: {game.round_number}", True, WHITE)
    losses_txt = FONT_SM.render(f"LOSSES IN A ROW: {game.consecutive_losses}/2", True, RED)
    surface.blit(max_txt,    (WIDTH - 100, 10))
    surface.blit(round_txt,  (WIDTH - 100, 24))
    surface.blit(losses_txt, (WIDTH - 150, 38))


def draw_state_label(surface, game):
    # bottom centre hint text changes depending on what state we're in
    if game.state == "player_turn":
        text, colour = "YOUR TURN  [SPACE] hit   [SHIFT] stand   [TAB] inventory", WHITE
    elif game.state == "enemy_turn":
        text, colour = "ENEMY TURN...", GREY
    elif game.state == "round_over":
        result_str   = game.round_result.replace("_", " ").upper() if game.round_result else ""
        text, colour = f"ROUND OVER  {result_str}   [ENTER] continue", YELLOW
    elif game.state == "game_over":
        text, colour = "GAME OVER   [R] restart", RED
    else:
        text, colour = "", WHITE
    txt = FONT_SM.render(text, True, colour)
    surface.blit(txt, (WIDTH // 2 - txt.get_width() // 2, HEIGHT - 16))


def draw_inventory(surface, game):
    # semi-transparent panel slides in from the right when TAB is pressed
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
    # big centred win/lose/draw message, only shown at end of round
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
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("21 — RE7 Blackjack")
    clock  = pygame.time.Clock()

    game = GameState()
    game.inventory_index = 0
    deal_opening_hands(game)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:

                if game.state == "inventory":
                    if event.key == pygame.K_TAB:
                        game.state = "player_turn"
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
                            game.inventory_index = max(0, game.inventory_index - 1)
                            game.state = "player_turn"

                elif game.state == "player_turn":
                    if event.key == pygame.K_SPACE:
                        player_hit(game)
                    elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                        player_stand(game)
                        run_enemy_turn(game)
                    elif event.key == pygame.K_TAB:
                        game.state = "inventory"

                elif game.state == "round_over":
                    if event.key == pygame.K_RETURN:
                        distribute_abilities(game)
                        start_round(game)

                elif game.state == "game_over":
                    if event.key == pygame.K_r:
                        game = GameState()
                        game.inventory_index = 0
                        deal_opening_hands(game)

        screen.fill(DARK_BG)
        draw_hand(screen, game.enemy_hand,  ENEMY_HAND_Y,  "ENEMY",  game.enemy_total,  is_enemy=True)
        draw_hand(screen, game.player_hand, PLAYER_HAND_Y, "PLAYER", game.player_total, is_enemy=False)
        draw_hud(screen, game)
        draw_state_label(screen, game)
        draw_round_over_banner(screen, game)
        if game.state == "inventory":
            draw_inventory(screen, game)
        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    run()