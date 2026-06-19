#include "game.h"

int main() {
    SDL_Init(SDL_INIT_EVERYTHING);
    IMG_Init(IMG_INIT_PNG);
    TTF_Init();
    Mix_OpenAudio(44100, MIX_DEFAULT_FORMAT, 2, 2048);

    Mix_Chunk *snd_shoot        = Mix_LoadWAV(AP "shoot.wav");
    Mix_Chunk *snd_kill         = Mix_LoadWAV(AP "invaderkilled.wav");
    Mix_Chunk *snd_explosion    = Mix_LoadWAV(AP "explosion.wav");
    Mix_Chunk *snd_enemy_shoot  = Mix_LoadWAV(AP "shoot_enemy.wav");

    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dist(0, 10);

    constexpr int ENEMY_W            = 32;
    constexpr int ENEMY_H            = 32;
    constexpr int SHOT_W             = 6;
    constexpr int SHOT_H             = 14;
    constexpr int WINDOW_WIDTH       = 896;
    constexpr int WINDOW_HEIGHT      = 700;
    constexpr int SHIP_W             = 56;
    constexpr int SHIP_H             = 36;
    constexpr int GROUND_LINE        = WINDOW_HEIGHT - 80;
    constexpr int BLOCK_SIZE         = 6;
    constexpr int SHIP_SPEED         = 4;
    constexpr int BULLET_SPEED       = 23;
    constexpr int ENEMY_SHOT_SPEED   = 9;
    constexpr int UFO_Y              = 50;
    constexpr int ANIM_INTERVAL      = 30;
    constexpr int UFO_SPAWN_INTERVAL = 1800;
    constexpr int INVINCIBILITY_DUR  = 120;
    constexpr int SHIP_WRECK_DUR     = 60;
    constexpr int EXPLOSION_DUR      = 20;
    constexpr int BONUS_LIFE_STEP    = 1000;

    TTF_Font *font = TTF_OpenFont("/Library/Fonts/Arial Unicode.ttf", 28);
    SDL_Color white = {255, 255, 255, 255};

    int  enemy_step    = 5;
    int  direction     = 1;
    int  move_distance = 0;
    bool anim_frame    = false;
    Shot player_bullet{Pos(0, 0)};
    int  score         = 0;
    int  highscore     = load_highscore();
    int  lives         = 10;
    int  next_goal     = BONUS_LIFE_STEP;
    std::vector<Shot> enemy_shots;

    SDL_Window   *window   = SDL_CreateWindow("Atari Space Invaders", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, WINDOW_WIDTH, WINDOW_HEIGHT, 0);
    SDL_Renderer *renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);

    SDL_Texture *enemy_textures[ENEMY_ROWS][2] = {
        {IMG_LoadTexture(renderer, SP "enemy1_1.png"), IMG_LoadTexture(renderer, SP "enemy1_2.png")},
        {IMG_LoadTexture(renderer, SP "enemy2_1.png"), IMG_LoadTexture(renderer, SP "enemy2_2.png")},
        {IMG_LoadTexture(renderer, SP "enemy3_1.png"), IMG_LoadTexture(renderer, SP "enemy3_2.png")},
        {IMG_LoadTexture(renderer, SP "enemy4_1.png"), IMG_LoadTexture(renderer, SP "enemy4_2.png")},
        {IMG_LoadTexture(renderer, SP "enemy5_1.png"), IMG_LoadTexture(renderer, SP "enemy5_2.png")},
    };

    SDL_Texture *spaceship        = IMG_LoadTexture(renderer, SP "spaceship.png");
    SDL_Texture *bonus            = IMG_LoadTexture(renderer, SP "bonus1.png");
    SDL_Texture *bullet_player    = IMG_LoadTexture(renderer, SP "bullet_player.png");
    SDL_Texture *bullet_enemy     = IMG_LoadTexture(renderer, SP "bullet_enemy.png");
    SDL_Texture *explosion_enemy  = IMG_LoadTexture(renderer, SP "explosion_enemy.png");
    SDL_Texture *explosion_player = IMG_LoadTexture(renderer, SP "explosion_player.png");

    std::unordered_map<int, int> points = {{4, 10}, {3, 20}, {2, 30}, {1, 40}, {0, 50}};

    std::vector<Enemy> enemies = build_enemy_grid();
    std::vector<std::vector<Pos>> shields = build_shields(WINDOW_WIDTH, GROUND_LINE, BLOCK_SIZE);
    Pos ship_pos(WINDOW_WIDTH / 2, WINDOW_HEIGHT - SHIP_H - 4);

    int   frame            = 0;
    int   invincibility    = 0;
    Pos   explosion_pos(0, 0);
    int   explosion_timer  = 0;
    int   ship_wreck_timer = 0;
    bool  running          = true;
    int   shoot_interval   = 60;
    int   shot_counter     = 0;
    int   enemy_step_copy  = 0;
    int   prev_alive_count = ENEMY_ROWS * ENEMY_COLS;
    constexpr int UFO_speed = 5;
    Enemy ufo{Pos(0, UFO_Y)};
    ufo.alive = false;
    SDL_Event event;

    while (running) {
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) {
                running = false;
            }
        }

        const Uint8 *keys = SDL_GetKeyboardState(nullptr);
        if (keys[SDL_SCANCODE_LEFT]  && ship_pos.x > 0) {
            ship_pos.x -= SHIP_SPEED;
        }
        if (keys[SDL_SCANCODE_RIGHT] && ship_pos.x < WINDOW_WIDTH - SHIP_W) {
            ship_pos.x += SHIP_SPEED;
        }
        if (keys[SDL_SCANCODE_SPACE] && !player_bullet.active && !ship_wreck_timer) {
            shoot(player_bullet, SHIP_W, SHIP_H, ship_pos, WINDOW_HEIGHT);
            Mix_PlayChannel(-1, snd_shoot, 0);
        }

        if (player_bullet.active) {
            player_bullet.pos.y -= BULLET_SPEED;
            if (auto pos = kill_enemy(enemies, player_bullet, ENEMY_W, SHOT_W, score, ENEMY_H, points)) {
                ++shot_counter;
                Mix_PlayChannel(-1, snd_kill, 0);
                explosion_pos   = pos.value();
                explosion_timer = EXPLOSION_DUR;
            }
            if (kill_ufo(ufo, player_bullet, ENEMY_W, ENEMY_H, SHOT_W, score, shot_counter)) {
                explosion_pos   = ufo.pos;
                explosion_timer = EXPLOSION_DUR;
                Mix_PlayChannel(-1, snd_kill, 0);
            }
            if (player_bullet.pos.y < 0) {
                player_bullet.active = false;
            }
        }

        if (frame % ANIM_INTERVAL == 0) {
            anim_frame = !anim_frame;
            move_enemies(enemies, WINDOW_WIDTH, direction, ENEMY_H, enemy_step, move_distance);
            if (dist(gen) > 7) {
                targeted_shot(enemies, enemy_shots, ship_pos, SHIP_W);
                Mix_PlayChannel(-1, snd_enemy_shoot, 0);
            }
        }
        if (frame % shoot_interval == 0) {
            fire_enemy_shot(enemies, gen, dist, enemy_shots, ENEMY_H, ENEMY_W);
            Mix_PlayChannel(-1, snd_enemy_shoot, 0);
        }

        if (frame % UFO_SPAWN_INTERVAL == 0 && !ufo.alive && dist(gen) < 2) {
            ufo.alive = true;
            ufo.pos = Pos(0, UFO_Y);
        }
        if (ufo.alive) {
            ufo.pos.x += UFO_speed;
            if (ufo.pos.x > WINDOW_WIDTH) {
                ufo.alive = false;
            }
        }
        ++frame;

        if (score > next_goal) {
            next_goal += BONUS_LIFE_STEP;
            ++lives;
        }

        if (enemies_crossed_line(enemies, GROUND_LINE, ENEMY_H)) {
            reset_game(enemies, ship_pos, enemy_shots, lives, score, enemy_step, WINDOW_WIDTH, WINDOW_HEIGHT, SHIP_H, highscore, score);
            enemy_step_copy = 0;
        }

        if (invincibility == 0) {
            if (ship_hit(enemy_shots, ship_pos, SHIP_W, SHIP_H)) {
                Mix_PlayChannel(-1, snd_explosion, 0);
                ship_wreck_timer = SHIP_WRECK_DUR;
                --lives;
                invincibility = INVINCIBILITY_DUR;
            }
        } else {
            --invincibility;
        }

        for (auto &shot : enemy_shots) {
            hit_shield(shields, shot, SHOT_W, SHOT_H, BLOCK_SIZE, WINDOW_WIDTH, false);
        }
        hit_shield(shields, player_bullet, SHOT_W, SHOT_H, BLOCK_SIZE, WINDOW_WIDTH, true);

        update_enemy_shots(enemy_shots, WINDOW_HEIGHT, ENEMY_SHOT_SPEED);

        if (!lives) {
            reset_game(enemies, ship_pos, enemy_shots, lives, score, enemy_step, WINDOW_WIDTH, WINDOW_HEIGHT, SHIP_H, highscore, score);
            enemy_step_copy = 0;
        }

        int alive_count = 0;
        for (auto &enemy : enemies) {
            if (enemy.alive) { ++alive_count; }
        }
        if (alive_count < prev_alive_count) {
            if (alive_count == 1) {
                enemy_step_copy = enemy_step;
                enemy_step += 6;
            }
            if (!alive_count) {
                enemy_step += 2;
                shoot_interval -= 6;
                reset_ship(ship_pos, WINDOW_WIDTH, WINDOW_HEIGHT, SHIP_H);
                enemies = build_enemy_grid();
                prev_alive_count = ENEMY_ROWS * ENEMY_COLS;
                enemy_step_copy = 0;
            } else {
                enemy_step += (ENEMY_ROWS * ENEMY_COLS / alive_count) * 0.05;
                prev_alive_count = alive_count;
            }
        }

        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        SDL_RenderClear(renderer);
        SDL_SetRenderDrawColor(renderer, 0, 255, 0, 255);
        SDL_RenderDrawLine(renderer, 0, GROUND_LINE, WINDOW_WIDTH, GROUND_LINE);
        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        draw_score(renderer, score, highscore, white, WINDOW_WIDTH, font);
        draw_lives(renderer, lives, white, WINDOW_WIDTH, font);
        draw_enemies(renderer, enemies, anim_frame, enemy_textures, ENEMY_W, ENEMY_H);
        if (!ship_wreck_timer) {
            draw_object(renderer, spaceship, SHIP_W, SHIP_H, ship_pos);
        }
        draw_shields(renderer, shields, BLOCK_SIZE);
        draw_shots(renderer, bullet_player, bullet_enemy, enemy_shots, SHOT_W, SHOT_H, player_bullet);
        if (ufo.alive) {
            draw_object(renderer, bonus, ENEMY_W, ENEMY_H, ufo.pos);
        }
        if (explosion_timer > 0) {
            draw_object(renderer, explosion_enemy, ENEMY_W, ENEMY_H, explosion_pos);
            --explosion_timer;
        }
        if (ship_wreck_timer > 0) {
            draw_object(renderer, explosion_player, SHIP_W, SHIP_H, ship_pos);
            --ship_wreck_timer;
        }

        SDL_RenderPresent(renderer);
        SDL_Delay(16);
    }

    for (int row = 0; row < ENEMY_ROWS; ++row) {
        for (int col = 0; col < 2; ++col) {
            SDL_DestroyTexture(enemy_textures[row][col]);
        }
    }
    SDL_DestroyTexture(spaceship);
    SDL_DestroyTexture(bonus);
    SDL_DestroyTexture(bullet_player);
    SDL_DestroyTexture(bullet_enemy);
    SDL_DestroyTexture(explosion_enemy);
    SDL_DestroyTexture(explosion_player);
    Mix_FreeChunk(snd_shoot);
    Mix_FreeChunk(snd_kill);
    Mix_FreeChunk(snd_explosion);
    Mix_FreeChunk(snd_enemy_shoot);
    Mix_CloseAudio();
    TTF_CloseFont(font);
    TTF_Quit();
    IMG_Quit();
    SDL_Quit();

    return 0;
}
