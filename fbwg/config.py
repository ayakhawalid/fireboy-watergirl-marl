"""Game constants, ported from utilities/Constants.java and main/Game.java."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "res"
LEVELS_DIR = ROOT / "levels"
LEVEL_FILES = ["01.txt", "02.txt"]

# Sizes (Game.java)
TILES_DEFAULT_SIZE = 10
SCALE = 3.0
TILES_WIDTH = 29
TILES_HEIGHT = 25
TILES_SIZE = int(TILES_DEFAULT_SIZE * SCALE)  # 30 px
GAME_WIDTH = TILES_SIZE * TILES_WIDTH  # 870
GAME_HEIGHT = TILES_SIZE * TILES_HEIGHT  # 750

# Loop rates (Game.run): physics runs at a fixed 200 updates per second.
UPS = 200
FPS = 120

# Heroes. PINK uses W/A/D in the original, DUDE uses the arrow keys.
PINK = "pink"
DUDE = "dude"
HEROES = (PINK, DUDE)

# Level tile codes (see levels/*.txt)
T_EMPTY = 0
T_FLOOR = 1
# Note: in the Java code FireTypes is (PURPLE, BLUE, GREEN) and tile = ordinal + 2,
# so tile 2 is the purple fire and tile 3 is the blue fire.
T_FIRE_PURPLE = 2  # kills DUDE
T_FIRE_BLUE = 3  # kills PINK
T_FIRE_GREEN = 4  # kills both
T_CRYSTAL_BLUE = 5  # collected by DUDE
T_CRYSTAL_PURPLE = 6  # collected by PINK
T_BOX = 7
T_DOOR_PINK = 8
T_DOOR_DUDE = 9
T_START_PINK = 10
T_START_DUDE = 11
T_SWING = 300
# 81-89: switch (button) for platform id = second digit
# 701-799: lever "7 <platform id> <is on>"
# 1001-2999: platform "<direction 1=vertical 2=horizontal> <id> <status> <size>"

# Image paths
P_HERO_DIR = {PINK: RES / "Heros" / "1 Pink_Monster", DUDE: RES / "Heros" / "3 Dude_Monster"}
P_HERO_PREFIX = {PINK: "Pink_Monster", DUDE: "Dude_Monster"}
# Animation order matches Constants.PlayerActions
HERO_ANIMS = ["Jump_8", "Run_Left_6", "Run_6", "Fall_4", "Idle_4", "Idle_Left_4", "Death_8"]
A_JUMP, A_RUN_LEFT, A_RUN_RIGHT, A_DOWN, A_IDLE, A_IDLE_LEFT, A_DIE = range(7)

P_BLUE_FIRE = RES / "Fires/blue/loops/1_burning_loop_8.png"
P_PURPLE_FIRE = RES / "Fires/purple/loops/1_burning_loop_8.png"
P_GREEN_FIRE = RES / "Fires/green/loops/1_burning_loop_8.png"
P_BLUE_CRYSTAL = RES / "Crystals/crystal_blue.png"
P_PURPLE_CRYSTAL = RES / "Crystals/crystal_purple.png"
P_DOOR = RES / "Doors_2.png"
P_LEVER = RES / "Lever_2.png"
P_SWITCH = RES / "Switch_4.png"
P_BOX = RES / "Box.png"
P_KEY = {PINK: RES / "key_01b.png", DUDE: RES / "key_01e.png"}
P_LEVEL_BUILD = RES / "Mainlev_Build.png"
P_BACKGROUND = RES / "Backgrounds/background1.png"
P_BACKGROUND_TWO = RES / "Backgrounds/background4b.png"
P_BACKGROUND_MENU = RES / "Backgrounds/background0.png"
P_DIALOG = RES / "Gui/Dialog.png"
P_BUTTONS = RES / "Gui/Buttons_3.png"
P_LINE = RES / "Gui/Line.png"
P_KEYS = RES / "Gui/Keyboard.png"
P_FONT = RES / "MinimalPixelFont.ttf"
P_NUMBERS = RES / "Numbers"

# Audio
P_MUSIC_MENU = RES / "audio/PGS Fantasy RPG Music Pack/town-village-theme-3.wav"
P_MUSIC_GAME = RES / "audio/PGS Fantasy RPG Music Pack/battle-music-1.wav"
P_FANFARE = RES / "audio/PGS Fantasy RPG Music Pack/Success Fanfare.wav"
P_SND_DIE = RES / "audio/Player/death.wav"
P_SND_GEM = RES / "audio/Player/gem.wav"
P_SND_JUMP = RES / "audio/Player/jump.wav"
P_SND_BUTTON = RES / "audio/GUI/button.wav"
P_SND_LEVER = RES / "audio/Player/lever pull.wav"
