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


def t(settings, key: str) -> str:
    return TEXT[settings.language][key]
