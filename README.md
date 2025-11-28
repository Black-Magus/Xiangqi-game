<!-- README.md for the Xiangqi game project -->

# Xiangqi Game (Chinese Chess)

This repository contains a **Xiangqi (Chinese Chess) game** implemented in **Python** using the [**Pygame**](https://www.pygame.org/) library.  It allows you to play against another human on the same machine or challenge a built‑in AI with multiple difficulty levels.  The project includes a fully featured graphical interface, game logic, configurable settings, player profiles with ELO ratings, and multilingual support.

## Features

| Category | Key features |
| --- | --- |
| **Game modes** | • Player vs. Player (PvP) and Player vs. AI.<br>• Switch sides during a match, take back moves, resign or start a new game. |
| **AI opponents** | • Several preset AI levels are provided (e.g., **Angry Man**, **Lỗ Tấn**, **Cờ Thủ**, etc.).<br>• Each level specifies search depth, randomness and evaluation noise; the AI uses a minimax search with heuristics defined in `core/engine/ai_engine.py`:contentReference[oaicite:0]{index=0}. |
| **Game engine** | • Complete Xiangqi rules are implemented in the `Board` class, including legal move generation and board evaluation.<br>• Piece values and positional heuristics are defined in `core/engine/evaluation.py`:contentReference[oaicite:1]{index=1}. |
| **Profiles & ELO** | • Player profiles and statistics are managed by `core/profiles_manager.py`, which records wins/losses, calculates ELO ratings using an expected‑score formula, and saves data in JSON:contentReference[oaicite:2]{index=2}.<br>• Built‑in avatars or custom images can be used for each profile. |
| **Customizable UI** | • Multiple board themes and piece color schemes (e.g. **Classic**, **Blue vs Gold**, **Crimson vs Gray**) are available through the themes module:contentReference[oaicite:3]{index=3}.<br>• Choose from various backgrounds and side‑panel backgrounds.<br>• Adjustable resolution ratios (e.g. windowed or full‑screen) and display modes.<br>• Optional piece animations and log box transparency settings. |
| **Sound & music** | • Background music and sound effects (move, capture, win, etc.).<br>• Volume for music and sound effects can be individually controlled in settings. |
| **Multilingual** | • User interface texts are translated into multiple languages, including **Vietnamese**, **English**, **Japanese**, **Cantonese**, **Traditional Chinese** and **Korean** (see `data/localisation.py`). |
| **Statistics & logs** | • Captured pieces and move history are displayed during the game.<br>• Timer options enable timed games with adjustable durations.<br>• Credits and game statistics are accessible from the menu. |

## Installation

### Prerequisites

- **Python 3.7+**
- **Pygame**: The game uses the Pygame library for rendering and input handling.  Install it via `pip`:

```bash
pip install pygame
