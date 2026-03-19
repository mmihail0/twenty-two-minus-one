import pygame
import sys

WIDTH,  HEIGHT = 960, 540
BTN_W,  BTN_H  = 200,  60
BTN_GAP        = 24    # vertical gap between buttons

BLACK    = (0,   0,   0)
WHITE    = (255, 255, 255)
RED      = (180,  30,  30)
RED_HOV  = (220,  50,  50)
DIM      = ( 80,  80,  80)
YELLOW   = (220, 190,  50)
GREY     = (100, 100, 100)

RULES_TEXT = [
    "RULES",
    "",
    "Both players start with 2 cards.",
    "On your turn: Hit to draw a card, Stand to end your turn.",
    "First to exceed the MAX value (default 21) busts and loses.",
    "If both players bust, the higher total loses.",
    "Ties give both players 1 ability card.",
    "",
    "ABILITY CARDS",
    "",
    "Max 17 / 24 / 27  —  change the bust limit for both players.",
    "Reset Deck        —  clear your hand and redraw 2 cards.",
    "Exchange          —  swap your last card with the enemy's last card.",
    "Friendship        —  both players gain 2 random abilities.",
    "Force Draw        —  enemy must immediately draw a card.",
    "Perfect Draw      —  draw the exact card needed to hit the max.",
    "",
    "Lose 3 rounds in a row and the game is over.",
    "",
    "[ESC]  Back to menu",
]


def run_menu():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("twenty two minus one")
    clock  = pygame.time.Clock()

    font_title  = pygame.font.Font("assets/fonts/MedievalSharp-Regular.ttf", 42)
    font_btn    = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 14)
    font_rules  = pygame.font.SysFont("couriernew", 22)
    font_head   = pygame.font.SysFont("couriernew", 26, bold=True)

    btn_default = None
    btn_hover   = None

    # button rects - centred, stacked
    cx = WIDTH  // 2
    cy = HEIGHT // 2

    play_rect  = pygame.Rect(cx - BTN_W//2, cy - BTN_H - BTN_GAP//2, BTN_W, BTN_H)
    rules_rect = pygame.Rect(cx - BTN_W//2, cy + BTN_GAP//2,          BTN_W, BTN_H)

    state = "menu"   # "menu", "rules"

    while True:
        mouse_pos = pygame.mouse.get_pos()
        play_hov  = play_rect.collidepoint(mouse_pos)
        rules_hov = rules_rect.collidepoint(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and state == "rules":
                    state = "menu"

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state == "menu":
                    if play_rect.collidepoint(event.pos):
                        return "play"
                    if rules_rect.collidepoint(event.pos):
                        state = "rules"
                elif state == "rules":
                    state = "menu"

        screen.fill(BLACK)

        if state == "menu":
            _draw_menu(screen, font_title, font_btn,
                       play_rect, rules_rect,
                       play_hov, rules_hov,
                       btn_default, btn_hover)

        elif state == "rules":
            _draw_rules(screen, font_rules, font_head)

        pygame.display.flip()
        clock.tick(30)


def _draw_button(surface, rect, label, font, hovered, btn_default, btn_hover):
    """Draw a button sprite (or fallback rect) with centred label."""
    sprite = (btn_hover if hovered else btn_default)
    if sprite:
        scaled = pygame.transform.scale(sprite, (rect.width, rect.height))
        surface.blit(scaled, rect.topleft)
    else:
        border_col = (220, 210, 190) if hovered else (160, 30, 30)
        pygame.draw.rect(surface, (10, 8, 8), rect)
        pygame.draw.rect(surface, border_col, rect, 2)

    text_col = WHITE if hovered else RED
    txt = font.render(label, True, text_col)
    surface.blit(txt, (rect.centerx - txt.get_width()//2,
                        rect.centery - txt.get_height()//2))


def _draw_menu(surface, font_title, font_btn,
               play_rect, rules_rect, play_hov, rules_hov,
               btn_default, btn_hover):
    # title - centred above buttons
    title     = font_title.render("TWENTY TWO MINUS ONE", True, WHITE)
    title_x   = WIDTH//2 - title.get_width()//2
    title_y   = play_rect.top - title.get_height() - 48
    # shadow
    shadow    = font_title.render("TWENTY TWO MINUS ONE", True, (40, 40, 40))
    surface.blit(shadow, (title_x + 2, title_y + 2))
    surface.blit(title,  (title_x,     title_y))

    _draw_button(surface, play_rect,  "PLAY",  font_btn, play_hov,  btn_default, btn_hover)
    _draw_button(surface, rules_rect, "RULES", font_btn, rules_hov, btn_default, btn_hover)

    # footer
    footer_font = pygame.font.SysFont("couriernew", 16)
    footer      = footer_font.render("click anywhere on the rules screen to return", True, DIM)
    surface.blit(footer, (WIDTH//2 - footer.get_width()//2, HEIGHT - 20))


def _draw_rules(surface, font_rules, font_head):
    pad    = 60
    y      = 40
    line_h = 30

    for line in RULES_TEXT:
        if line == "RULES" or line == "ABILITY CARDS":
            txt = font_head.render(line, True, YELLOW)
        elif line == "":
            y += line_h // 2
            continue
        elif line.startswith("["):
            txt = font_rules.render(line, True, GREY)
        else:
            txt = font_rules.render(line, True, WHITE)
        surface.blit(txt, (pad, y))
        y += line_h


if __name__ == "__main__":
    result = run_menu()
    print(f"Menu returned: {result}")