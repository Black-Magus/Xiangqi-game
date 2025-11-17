TEXT = {
    "en": {
        "title": "Xiangqi",
        "subtitle": "Press Esc in game to return to menu",
        "menu_pvp": "Play PvP (local)",
        "menu_ai": "Play vs AI",
        "menu_settings": "Settings",
        "menu_exit": "Exit",

        "settings_title": "Settings",
        "btn_back": "Back",

        "btn_undo": "Undo",
        "btn_redo": "Redo",
        "btn_takeback": "Takeback",
        "btn_resign": "Resign",
        "btn_new_game": "New game",
        "btn_settings_in_game": "Settings",

        "mode_pvp": "Mode: PvP",
        "mode_ai": "Mode: vs AI",
        "turn_red": "Turn: RED",
        "turn_black": "Turn: BLACK",

        "check_on_red": "CHECK on RED",
        "check_on_black": "CHECK on BLACK",
        "red_wins": "RED wins",
        "black_wins": "BLACK wins",
        "game_over": "Game over",

        "settings_board_theme": "Board: {name}",
        "settings_piece_theme": "Pieces: {name}",
        "settings_display": "Display: {mode}",
        "settings_piece_body": "Piece body: {name}",
        "settings_piece_icons": "Piece icons: {name}",
        "settings_piece_symbol_color": "Symbol color: {name}",
        "display_window": "Window",
        "display_fullscreen": "Fullscreen",

        "settings_player_stats": "Player stats",
        "stats_title": "Player stats",
        "stats_overall": "Overall",
        "stats_vs_ai": "vs AI",
        "stats_vs_human": "vs human",
        "stats_games": "Games",
        "stats_wins": "Wins",
        "stats_losses": "Losses",
        "stats_draws": "Draws",
        "stats_winrate": "Winrate",

        "paused": "Paused",
        "main_menu": "Main menu",
        "resume": "Resume",
        
        "tab_moves": "Moves",
        "tab_captured": "Captured",

        "label_red_player": "RED: {name}",
        "label_black_player": "BLACK: {name}",
        "label_ai_player": "AI: {name}",
    },
    "vi": {
        "title": "Cờ tướng",
        "subtitle": "Nhấn Esc trong game để quay lại menu",
        "menu_pvp": "Chơi 2 người (cùng máy)",
        "menu_ai": "Chơi với máy",
        "menu_settings": "Cài đặt",
        "menu_exit": "Thoát",

        "settings_title": "Cài đặt",
        "btn_back": "Quay lại",

        "btn_undo": "Đi lại",
        "btn_redo": "Tiến tới",
        "btn_takeback": "Xin đi lại",
        "btn_resign": "Đầu hàng",
        "btn_new_game": "Ván mới",
        "btn_settings_in_game": "Cài đặt",

        "mode_pvp": "Chế độ: 2 người",
        "mode_ai": "Chế độ: Chơi với máy",
        "turn_red": "Lượt: ĐỎ",
        "turn_black": "Lượt: ĐEN",

        "check_on_red": "Chiếu tướng ĐỎ",
        "check_on_black": "Chiếu tướng ĐEN",
        "red_wins": "ĐỎ thắng",
        "black_wins": "ĐEN thắng",
        "game_over": "Ván cờ kết thúc",

        "settings_board_theme": "Bàn cờ: {name}",
        "settings_piece_theme": "Quân cờ: {name}",
        "settings_display": "Hiển thị: {mode}",
        "settings_piece_body": "Nền quân: {name}",
        "settings_piece_icons": "Biểu tượng: {name}",
        "settings_piece_symbol_color": "Màu biểu tượng: {name}",

        "display_window": "Cửa sổ",
        "display_fullscreen": "Toàn màn hình",
        "settings_player_stats": "Thống kê người chơi",
        "stats_title": "Thống kê người chơi",
        "stats_overall": "Tổng",
        "stats_vs_ai": "Vs máy",
        "stats_vs_human": "Vs người",
        "stats_games": "Số ván",
        "stats_wins": "Thắng",
        "stats_losses": "Thua",
        "stats_draws": "Hòa",
        "stats_winrate": "Tỉ lệ thắng",

        "paused": "Tạm dừng",
        "main_menu": "Màn hình chính",
        "resume": "Tiếp tục",

        "tab_moves": "Nước đi",
        "tab_captured": "Quân ăn được",

        "label_red_player": "ĐỎ: {name}",
        "label_black_player": "ĐEN: {name}",
        "label_ai_player": "AI: {name}",
    },
}

PIECE_BODY_THEMES = [
    {
        "key": "flat_light",
        "name": {"en": "Flat light", "vi": "Phẳng sáng"},
        "folder": "classic",
        "red_file": "flat_light_red.png",
        "black_file": "flat_light_black.png",
    },
    {
        "key": "flat_dark",
        "name": {"en": "Flat dark", "vi": "Phẳng tối"},
        "folder": "classic",
        "red_file": "flat_dark_red.png",
        "black_file": "flat_dark_black.png",
    },
]

PIECE_SYMBOL_SETS = [
    {
        "key": "hanzi_classic",
        "name": {"en": "Chinese classic", "vi": "Hán cổ điển"},
        "folder": "hanzi_classic",
        "files": {
            "red": {
                "general": "red_general.png",
                "advisor": "red_advisor.png",
                "elephant": "red_elephant.png",
                "horse":   "red_horse.png",
                "rook":    "red_rook.png",
                "cannon":  "red_cannon.png",
                "soldier": "red_soldier.png",
            },
            "black": {
                "general": "black_general.png",
                "advisor": "black_advisor.png",
                "elephant": "black_elephant.png",
                "horse":   "black_horse.png",
                "rook":    "black_rook.png",
                "cannon":  "black_cannon.png",
                "soldier": "black_soldier.png",
            },
        },
    },
]



def t(settings, key: str) -> str:
    return TEXT[settings.language][key]
