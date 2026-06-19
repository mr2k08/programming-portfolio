#pragma once
#include "SDL_render.h"
#include <SDL.h>
#include <SDL_image.h>
#include <SDL_ttf.h>
#include <cstdlib>
#include <vector>
#include <unordered_map>
#include <random>
#include <SDL_mixer.h>
#include <optional>
#include <fstream>

#define SP "/Users/marcrubeiz/Library/Mobile Documents/com~apple~CloudDocs/Work/Programing/C && C++/testfiles/games/ATARI Space Invaders/sprites/"
#define HIGHSCORE_FILE "/Users/marcrubeiz/Library/Mobile Documents/com~apple~CloudDocs/Work/Programing/C && C++/testfiles/games/ATARI Space Invaders/highscore.txt"
#define AP "/Users/marcrubeiz/Library/Mobile Documents/com~apple~CloudDocs/Work/Programing/C && C++/testfiles/games/ATARI Space Invaders/audio/"

constexpr int ENEMY_ROWS         = 5;
constexpr int ENEMY_COLS         = 11;
constexpr int SHIELD_COUNT       = 4;
constexpr int SHIELD_COLS        = 10;
constexpr int SHIELD_ROWS        = 7;
constexpr int ENEMY_RIGHT_MARGIN = 60;
constexpr int ENEMY_LEFT_MARGIN  = 30;
constexpr int ENEMY_MOVE_THRESH  = 10;

struct Pos {
    int x, y;
    Pos(int x, int y) : x(x), y(y) {}
};

struct Enemy {
    Pos pos;
    bool alive = true;
    int type;
};

struct Shot {
    Pos pos;
    bool active = false;
};

inline int load_highscore() {
    std::ifstream f(HIGHSCORE_FILE);
    int hs = 0;
    if (f.is_open()) f >> hs;
    return hs;
}

inline void save_highscore(int score) {
    std::ofstream f(HIGHSCORE_FILE);
    f << score;
}

inline void draw_object(SDL_Renderer *renderer, SDL_Texture *tex, int w, int h, Pos pos) {
    SDL_Rect rect = {pos.x, pos.y, w, h};
    SDL_RenderCopy(renderer, tex, nullptr, &rect);
}

inline std::optional<Pos> kill_enemy(std::vector<Enemy> &enemies, Shot &shot, int enemy_w, int shot_w, int &score, int enemy_h, std::unordered_map<int, int> points) {
    for (auto &enemy : enemies) {
        if (enemy.alive &&
            shot.pos.y <= enemy.pos.y + enemy_h &&
            shot.pos.x < enemy.pos.x + enemy_w &&
            shot.pos.x + shot_w > enemy.pos.x) {
            enemy.alive = false;
            score += points[enemy.type];
            shot.active = false;
            return enemy.pos;
        }
    }
    return std::nullopt;
}

inline void shoot(Shot &shot, int ship_w, int ship_h, Pos pos, int window_h) {
    shot.active = true;
    shot.pos.x = pos.x + ship_w / 2 - 1;
    shot.pos.y = window_h - ship_h;
}

inline void draw_enemies(SDL_Renderer *renderer, const std::vector<Enemy> &enemies, bool anim_frame, SDL_Texture *enemy_textures[ENEMY_ROWS][2], int w, int h) {
    for (auto &enemy : enemies) {
        if (enemy.alive) {
            draw_object(renderer, enemy_textures[enemy.type][(int)anim_frame], w, h, enemy.pos);
        }
    }
}

inline void move_enemies(std::vector<Enemy> &enemies, int window_w, int &direction, int enemy_h, int step, int &move_distance) {
    bool shift = false;

    for (auto &enemy : enemies) {
        if (!enemy.alive) { continue; }
        if (direction > 0 && enemy.pos.x >= window_w - ENEMY_RIGHT_MARGIN) {
            direction = -direction;
            shift = true;
            break;
        }
        if (direction < 0 && enemy.pos.x <= ENEMY_LEFT_MARGIN) {
            direction = -direction;
            shift = true;
            break;
        }
    }

    for (auto &enemy : enemies) {
        if (shift) {
            enemy.pos.y += enemy_h;
        } else {
            enemy.pos.x += direction * step;
        }
    }
    move_distance = shift ? 0 : move_distance + 1;
}

inline std::vector<Enemy> get_column(const std::vector<Enemy> &enemies, int col) {
    std::vector<Enemy> column;
    for (int i = 0; i < ENEMY_ROWS; ++i) {
        Enemy enemy = enemies[ENEMY_COLS * i + col];
        if (enemy.alive) {
            column.push_back(enemy);
        }
    }
    return column;
}

inline bool enemies_crossed_line(const std::vector<Enemy> &enemies, int line_y, int enemy_h) {
    for (auto &enemy : enemies) {
        if (enemy.alive && enemy.pos.y + enemy_h >= line_y) {
            return true;
        }
    }
    return false;
}

inline void fire_enemy_shot(const std::vector<Enemy> &enemies, std::mt19937 &gen, std::uniform_int_distribution<> &dist, std::vector<Shot> &enemy_shots, int enemy_h, int enemy_w) {
    int col = dist(gen);
    std::vector<Enemy> column = get_column(enemies, col);
    while (column.empty()) {
        col = dist(gen);
        column = get_column(enemies, col);
    }
    Enemy shooter = column.back();
    Shot shot{Pos(shooter.pos.x + enemy_w / 2, shooter.pos.y + enemy_h)};
    shot.active = true;
    enemy_shots.push_back(shot);
}

inline void targeted_shot(std::vector<Enemy> enemies, std::vector<Shot> &shots, Pos ship, int ship_w) {
    int col = -1;
    int ship_center = ship.x + ship_w / 2;
    int min_dist = INT_MAX;
    for (int i = 0; i < (int)enemies.size(); ++i) {
        if (!enemies[i].alive) { continue; }
        int dist = std::abs(enemies[i].pos.x - ship_center);
        if (dist < min_dist) {
            col = i % ENEMY_COLS;
            min_dist = dist;
        }
    }
    if (col < 0) { return; }
    std::vector<Enemy> column = get_column(enemies, col);
    if (column.empty()) { return; }
    Enemy shooter = column.back();
    Shot shot{Pos(shooter.pos.x, shooter.pos.y)};
    shot.active = true;
    shots.push_back(shot);
}

inline std::vector<std::vector<Pos>> build_shields(int window_w, int ground_line, int block) {
    const int pattern[SHIELD_ROWS][SHIELD_COLS] = {
        {0,1,1,1,1,1,1,1,1,0},
        {1,1,1,1,1,1,1,1,1,1},
        {1,1,1,1,1,1,1,1,1,1},
        {1,1,1,1,1,1,1,1,1,1},
        {1,1,1,1,1,1,1,1,1,1},
        {1,1,0,0,1,1,0,0,1,1},
        {1,1,0,0,0,0,0,0,1,1},
    };
    int shield_w = SHIELD_COLS * block;
    int spacing  = (window_w - SHIELD_COUNT * shield_w) / (SHIELD_COUNT + 1);
    int shield_y = ground_line - SHIELD_ROWS * block - 20;

    std::vector<std::vector<Pos>> shields;
    for (int s = 0; s < SHIELD_COUNT; ++s) {
        std::vector<Pos> blocks;
        int ox = spacing + s * (shield_w + spacing);
        for (int r = 0; r < SHIELD_ROWS; ++r) {
            for (int c = 0; c < SHIELD_COLS; ++c) {
                if (pattern[r][c]) {
                    blocks.push_back(Pos(ox + c * block, shield_y + r * block));
                }
            }
        }
        shields.push_back(blocks);
    }
    return shields;
}

inline void draw_shields(SDL_Renderer *renderer, const std::vector<std::vector<Pos>> &shields, int block) {
    SDL_SetRenderDrawColor(renderer, 0, 255, 0, 255);
    for (auto &shield : shields) {
        for (auto &b : shield) {
            SDL_Rect rect = {b.x, b.y, block, block};
            SDL_RenderFillRect(renderer, &rect);
        }
    }
    SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
}

inline bool hit_shield(std::vector<std::vector<Pos>> &shields, Shot &shot, int shot_w, int shot_h, int block, int window_w, bool going_up) {
    int shield_w = SHIELD_COLS * block;
    int spacing  = (window_w - SHIELD_COUNT * shield_w) / (SHIELD_COUNT + 1);
    int s = (shot.pos.x - spacing) / (shield_w + spacing);
    if (s < 0 || s >= SHIELD_COUNT) { return false; }
    auto &blocks = shields[s];
    int start = going_up ? (int)blocks.size() - 1 : 0;
    int end   = going_up ? -1 : (int)blocks.size();
    int step  = going_up ? -1 : 1;
    for (int i = start; i != end; i += step) {
        if (shot.pos.x < blocks[i].x + block &&
            shot.pos.x + shot_w > blocks[i].x &&
            shot.pos.y < blocks[i].y + block &&
            shot.pos.y + shot_h > blocks[i].y) {
            blocks.erase(blocks.begin() + i);
            shot.active = false;
            return true;
        }
    }
    return false;
}

inline void draw_shots(SDL_Renderer *renderer, SDL_Texture *player_bullet_tex, SDL_Texture *enemy_bullet_tex, const std::vector<Shot> &enemy_shots, int w, int h, Shot player_bullet) {
    if (player_bullet.active) {
        draw_object(renderer, player_bullet_tex, w, h, player_bullet.pos);
    }
    for (auto &shot : enemy_shots) {
        if (shot.active) {
            draw_object(renderer, enemy_bullet_tex, w, h, shot.pos);
        }
    }
}

inline void update_enemy_shots(std::vector<Shot> &shots, int window_h, int speed) {
    for (auto &shot : shots) {
        if (shot.pos.y >= window_h) {
            shot = shots.back();
            shots.pop_back();
        } else {
            shot.pos.y += speed;
        }
    }
}

inline bool kill_ufo(Enemy &ufo, Shot &shot, int ufo_w, int ufo_h, int shot_w, int &score, int shot_counter) {
    if (!ufo.alive) { return false; }
    if (shot.pos.y <= ufo.pos.y + ufo_h &&
        shot.pos.x < ufo.pos.x + ufo_w &&
        shot.pos.x + shot_w > ufo.pos.x) {
        ufo.alive = false;
        shot.active = false;
        if (shot_counter % 3 == 0) { score += 300; }
        else if (shot_counter % 2 == 0) { score += 150; }
        else { score += 50; }
        return true;
    }
    return false;
}

inline bool ship_hit(std::vector<Shot> &enemy_shots, Pos ship_pos, int ship_w, int ship_h) {
    for (int i = 0; i < (int)enemy_shots.size(); ++i) {
        if (enemy_shots[i].pos.y >= ship_pos.y &&
            enemy_shots[i].pos.x >= ship_pos.x &&
            enemy_shots[i].pos.x <= ship_pos.x + ship_w &&
            enemy_shots[i].active) {
            enemy_shots.erase(enemy_shots.begin() + i);
            return true;
        }
    }
    return false;
}

inline void draw_hud_text(SDL_Renderer *renderer, const std::string &text, SDL_Color color, int x, TTF_Font *font) {
    SDL_Surface *surface = TTF_RenderText_Solid(font, text.c_str(), color);
    SDL_Texture *tex = SDL_CreateTextureFromSurface(renderer, surface);
    int w, h;
    SDL_QueryTexture(tex, nullptr, nullptr, &w, &h);
    SDL_Rect rect = {x, 10, w, h};
    SDL_RenderCopy(renderer, tex, nullptr, &rect);
    SDL_FreeSurface(surface);
    SDL_DestroyTexture(tex);
}

inline void draw_score(SDL_Renderer *renderer, int score, int highscore, SDL_Color color, int window_w, TTF_Font *font) {
    if (score > highscore) {
        highscore = score;
    }
    std::string text = "<score: " + std::to_string(score) + ">    <best: " + std::to_string(highscore) + ">  ";
    int w, h;
    TTF_SizeText(font, text.c_str(), &w, &h);
    draw_hud_text(renderer, text, color, (window_w / 2) - (w / 2) - 74, font);
}

inline void draw_lives(SDL_Renderer *renderer, int lives, SDL_Color color, int window_w, TTF_Font *font) {
    draw_hud_text(renderer, "                  <lives: " + std::to_string(lives) + ">", color, (window_w / 2) - 34, font);
}

inline std::vector<Enemy> build_enemy_grid() {
    constexpr int X_START = 40, X_STEP = 68;
    constexpr int Y_START = 90, Y_STEP = 56;
    std::vector<Enemy> enemies;
    for (int row = 0; row < ENEMY_ROWS; ++row) {
        for (int col = 0; col < ENEMY_COLS; ++col) {
            enemies.push_back({Pos(X_START + col * X_STEP, Y_START + row * Y_STEP), true, row});
        }
    }
    return enemies;
}

inline void reset_ship(Pos &ship_pos, int window_w, int window_h, int ship_h) {
    ship_pos.x = window_w / 2;
    ship_pos.y = window_h - ship_h - 4;
}

inline void reset_game(std::vector<Enemy> &enemies, Pos &ship_pos, std::vector<Shot> &enemy_shots,
                int &lives, int &score, int &enemy_step, int window_w, int window_h, int ship_h,
                int &highscore, int current_score) {
    if (current_score > highscore) {
        highscore = current_score;
        save_highscore(highscore);
    }
    reset_ship(ship_pos, window_w, window_h, ship_h);
    enemies = build_enemy_grid();
    enemy_shots.clear();
    lives = 10;
    score = 0;
    enemy_step = 5;
}
