"""Window, menus and the main loop (main/Game.java and the screens package)."""

from __future__ import annotations

import pygame

from . import assets as A
from . import config as C
from .level import level_count
from .render import WorldRenderer
from .world import World

T = C.TILES_SIZE
W, H = C.GAME_WIDTH, C.GAME_HEIGHT
WHITE = (255, 255, 255)

# Keys: PINK uses W/A/D like the Java version, DUDE uses the arrow keys.
KEYS = {
    C.PINK: (pygame.K_a, pygame.K_d, pygame.K_w),
    C.DUDE: (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP),
}

INSTRUCTIONS_TEXT = (
    "In this game you are in a cave full of dangers and challenges. Each hero must reach "
    "its own door, but be careful not to touch flames that are not your colour. If you touch "
    "a flame of the wrong colour, you lose.\n"
    "Collect the gems of your colour to raise your score. Gems of the other colour cannot be "
    "collected. Some platforms are moved with levers and buttons. Platforms moved by buttons "
    "go back after a while, so be quick.\n"
    "There are also swings that tilt, so be careful!"
)


def draw_text(surf, text, size, pos, center=False, max_width=None, color=WHITE):
    f = A.font(size)
    if max_width:
        while size > 10 and f.size(text)[0] > max_width:
            size -= 2
            f = A.font(size)
    img = f.render(text, False, color)
    rect = img.get_rect(center=pos) if center else img.get_rect(topleft=pos)
    surf.blit(img, rect)
    return rect


def draw_wrapped(surf, text, size, rect: pygame.Rect, color=WHITE):
    f = A.font(size)
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            test = f"{line} {word}".strip()
            if f.size(test)[0] <= rect.width:
                line = test
            else:
                lines.append(line)
                line = word
        lines.append(line)
    lh = f.get_linesize()
    y = rect.y + max(0, (rect.height - lh * len(lines)) // 2)  # JLabel centres vertically
    for ln in lines:
        surf.blit(f.render(ln, False, color), (rect.x, y))
        y += lh


class Button:
    """gui/Button.java: image button with normal / pressed / hover states."""

    def __init__(self, x, y, text, on_click):
        imgs = A.frames_y(C.P_BUTTONS)
        w = int((imgs[0].get_width() / 3) * 1.7)
        h = int((imgs[0].get_height() / 3) * 1.3)
        self.images = [A.scaled(i, w, h) for i in imgs]
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.on_click = on_click
        self.pressed = False

    def draw(self, surf, mouse):
        hover = self.rect.collidepoint(mouse)
        idx = 1 if (self.pressed and hover) else 2 if hover else 0
        surf.blit(self.images[idx], self.rect)
        draw_text(surf, self.text, 60, self.rect.center, center=True, max_width=self.rect.width + 40)

    def handle(self, event, sound):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was = self.pressed
            self.pressed = False
            if was and self.rect.collidepoint(event.pos):
                sound.play(C.P_SND_BUTTON)
                self.on_click()
                return True
        return False


class Dialog:
    """gui/Dialog.java: a framed panel in the middle of the screen."""

    def __init__(self, width=T * 13, height=T * 13):
        self.w, self.h = width, height
        self.x = W // 2 - width // 2
        self.y = H // 2 - height // 2
        self.img = A.scaled(A.image(C.P_DIALOG), width, height)

    def draw(self, surf):
        surf.blit(self.img, (self.x, self.y))


class App:
    def __init__(self, sound=True, start_level=0, debug=False):
        pygame.init()
        pygame.display.set_caption("Fire and Water")
        self.screen = pygame.display.set_mode((W, H))
        self.clock = pygame.time.Clock()
        self.sound = A.Sound(sound)
        self.debug = debug
        self.menu_bg = A.scaled(A.image(C.P_BACKGROUND_MENU), W, H)
        self.renderer = WorldRenderer()
        self.state = "menu"
        self.world: World | None = None
        self.level_index = start_level
        self.overlay = None  # None, "game_over", "summary", "end"
        self.running = True
        self.dim = pygame.Surface((W, H), pygame.SRCALPHA)
        self.dim.fill((0, 0, 0, 128))
        self._build_screens()

    # screens ---------------------------------------------------------------
    def _build_screens(self):
        d = Dialog(int(W / 1.9), int(W / 1.9))
        bx = d.x + d.w // 4
        self.menu_dialog = d
        self.menu_buttons = [
            Button(bx, d.y + int(d.h / 9), "Play", lambda: self.start_level(self.level_index)),
            Button(bx, d.y + int(d.h / 3.2), "Instructions", lambda: self.go("instructions")),
            Button(bx, d.y + int(d.h / 1.95), "Credits", lambda: self.go("credits")),
            Button(bx, d.y + int(d.h / 1.4), "Quit", self.quit),
        ]
        self.small = Dialog()
        sx = self.small.x + int(self.small.w / 4.2)
        self.credits_buttons = [Button(sx, self.small.y + int(self.small.h / 1.5), "Menu", lambda: self.go("menu"))]
        self.instructions_buttons = [Button(W // 2 - T * 3, H - T * 3, "Menu", lambda: self.go("menu"))]
        self.game_over_buttons = [
            Button(sx, self.small.y + int(self.small.h / 2.5), "Retry", lambda: self.start_level(self.level_index)),
            Button(sx, self.small.y + int(self.small.h / 1.5), "Menu", lambda: self.go("menu")),
        ]
        self.summary_buttons = [Button(sx, self.small.y + int(self.small.h / 1.5), "Continue", self.next_level)]
        self.end_buttons = [Button(sx, self.small.y + int(self.small.h / 1.5), "Menu", lambda: self.go("menu"))]

        keys = A.image(C.P_KEYS)
        pink_xy = [(6, 4), (2, 4), (0, 2), (3, 2)]
        self.key_imgs = [
            [A.scaled(keys.subsurface((x * 16, y * 16, 16, 16)), T * 2, T * 2) for x, y in pink_xy],
            [A.scaled(keys.subsurface((i * 16, 0, 16, 16)), T * 2, T * 2) for i in range(4)],
        ]
        self.portraits = [A.scaled(A.hero_portrait(h), T * 2, T * 2) for h in C.HEROES]

    def go(self, state):
        self.state = state
        self.overlay = None
        if state == "menu":
            self.world = None
            self.level_index = 0

    def quit(self):
        self.running = False

    def start_level(self, index):
        self.level_index = index
        self.world = World(index)
        self.state = "playing"
        self.overlay = None

    def next_level(self):
        if self.level_index + 1 >= level_count():
            self.overlay = "end"
        else:
            self.start_level(self.level_index + 1)

    def buttons(self):
        if self.state == "menu":
            return self.menu_buttons
        if self.state == "credits":
            return self.credits_buttons
        if self.state == "instructions":
            return self.instructions_buttons
        if self.state == "playing":
            return {
                "game_over": self.game_over_buttons,
                "summary": self.summary_buttons,
                "end": self.end_buttons,
            }.get(self.overlay, [])
        return []

    # loop -----------------------------------------------------------------
    def run(self):
        dt_update = 1000.0 / C.UPS
        acc = 0.0
        while self.running:
            acc += self.clock.tick(C.FPS)
            acc = min(acc, 250.0)  # avoid a long catch-up after the window was dragged
            for event in pygame.event.get():
                self.handle_event(event)
            while acc >= dt_update:
                acc -= dt_update
                self.update()
            self.draw()
            pygame.display.flip()
        pygame.quit()

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN and self.state == "playing":
            if event.key == pygame.K_ESCAPE:
                self.go("menu")
                return
            if event.key == pygame.K_r:
                self.start_level(self.level_index)
                return
            if event.key == pygame.K_F3:
                self.debug = not self.debug
        if event.type == pygame.WINDOWFOCUSLOST and self.world:
            for p in self.world.players.values():  # Playing.windowsFocusLost
                p.set_input(False, False, False)
        for b in list(self.buttons()):
            if b.handle(event, self.sound):
                break

    def update(self):
        if self.state != "playing" or self.world is None:
            return
        world = self.world
        if not world.finished:
            pressed = pygame.key.get_pressed()
            if pygame.key.get_focused():
                world.set_inputs({h: tuple(pressed[k] for k in KEYS[h]) for h in C.HEROES})
        for name, _hero in world.update():
            if name == "jump":
                self.sound.play(C.P_SND_JUMP)
            elif name == "gem":
                self.sound.play(C.P_SND_GEM)
            elif name == "lever":
                self.sound.play(C.P_SND_LEVER)
            elif name == "die":
                self.sound.music(None)
                self.sound.play(C.P_SND_DIE)
            elif name == "level_won":
                self.sound.music(None)
                self.sound.play(C.P_FANFARE)
                self.overlay = "summary"
            elif name == "game_over":
                self.overlay = "game_over"

    def draw(self):
        s = self.screen
        mouse = pygame.mouse.get_pos()
        if self.state == "playing" and self.world is not None:
            if not self.world.finished and not any(p.death for p in self.world.players.values()):
                self.sound.music(C.P_MUSIC_GAME)
            self.renderer.draw(s, self.world, self.debug)
            if self.overlay:
                s.blit(self.dim, (0, 0))
                self.small.draw(s)
                self._draw_overlay(s)
        else:
            self.sound.music(C.P_MUSIC_MENU)
            s.blit(self.menu_bg, (0, 0))
            if self.state == "menu":
                self.menu_dialog.draw(s)
            elif self.state == "credits":
                self._draw_credits(s)
            elif self.state == "instructions":
                self._draw_instructions(s)
        for b in self.buttons():
            b.draw(s, mouse)

    def _draw_overlay(self, s):
        d = self.small
        if self.overlay == "game_over":
            draw_text(s, "Game Over", 60, (W // 2, H // 2 - T * 4), center=True)
        elif self.overlay == "summary":
            draw_text(s, "Congratulations!", 60, (W // 2, H // 2 - T * 4), center=True, max_width=d.w - 30)
            t = self.world.time_seconds()
            draw_text(s, f"Time: {t // 60:02d}:{t % 60:02d}", 50, (d.x + int(T * 1.5), d.y + int(d.h / 2.5) - 15))
            for i, hero in enumerate(C.HEROES):
                got, total = self.world.crystal_score(hero)
                label = f"{hero.capitalize()} gems: {got} of {total}"
                draw_text(s, label, 50, (d.x + int(T * 1.5), d.y + d.h // 2 + i * 36 - 20), max_width=d.w - T * 3)
        elif self.overlay == "end":
            draw_text(s, "Congratulations!", 60, (W // 2, H // 2 - T * 4 - 10), center=True, max_width=d.w - 30)
            draw_text(s, "You finished the game", 50, (W // 2, H // 2 - T * 2), center=True, max_width=d.w - 30)

    def _draw_credits(self, s):
        d = self.small
        d.draw(s)
        draw_text(s, "Credits:", 60, (d.x + d.w // 4, d.y + d.h // 9))
        y = d.y + int(d.h / 3.2)
        for line in ("Dylan Buitrago", "Kevin Gonzalez", "Python port"):
            draw_text(s, line, 50 if line != "Python port" else 40, (d.x + d.w // 4, y))
            y += 40

    def _draw_instructions(self, s):
        for i, img in enumerate(self.portraits):
            s.blit(img, (T * 5 + T * i * 15, T * 2))
        for i, row in enumerate(self.key_imgs):
            for j, img in enumerate(row):
                s.blit(img, (T * 15 * i + T * 2 + T * 2 * j, T * 5))
        draw_wrapped(s, INSTRUCTIONS_TEXT, 40, pygame.Rect(T, T * 7 + 10, W - T * 2, H - T * 11))


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Fire and Water (Python port)")
    parser.add_argument("--mute", action="store_true", help="no music or sound")
    parser.add_argument("--level", type=int, default=0, help="level to start with (0 or 1)")
    parser.add_argument("--debug", action="store_true", help="show hitboxes (toggle with F3)")
    args = parser.parse_args(argv)
    App(sound=not args.mute, start_level=args.level, debug=args.debug).run()
