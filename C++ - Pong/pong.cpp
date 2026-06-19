#include "SDL_render.h"
#include "SDL_surface.h"
#include "SDL_ttf.h"
#include <SDL.h>
#include <algorithm>
#include <random>
#include <string>

struct Coord2D{
    short x, y;
    Coord2D(short x_, short y_) : x(x_), y(y_) {}
};

void draw_pad(SDL_Renderer* renderer, Coord2D pos, SDL_Color color, const short W, const short H){
    SDL_Rect pad = {pos.x, pos.y, W, H};
    SDL_RenderFillRect(renderer, &pad);
}

void draw_ball(SDL_Renderer* renderer, Coord2D pos, const short size, SDL_Color color){
    SDL_Rect ball = {pos.x, pos.y, size, size};
    SDL_RenderFillRect(renderer, &ball);
}

void ceiling_collision(Coord2D pos, short H, Coord2D& vec, short radius){
    if (pos.y <= 0 || pos.y >= H - radius){
        vec.y = -vec.y;
    }
}

void left_pad_collision(Coord2D ball_pos, Coord2D pad_pos, const short H, const short W, Coord2D& vec, const short ball_size){
    if ((ball_pos.x + ball_size <= pad_pos.x + W) && (ball_pos.x >= pad_pos.x) &&
        (ball_pos.y <  pad_pos.y + H) && (ball_pos.y  + ball_size >  pad_pos.y)){
        vec.x = -vec.x;
    }
}

void right_pad_collision(Coord2D ball_pos, Coord2D pad_pos, const short H, const short W, Coord2D& vec, const short ball_size){
    if ((ball_pos.x + ball_size >= pad_pos.x) && (ball_pos.x <= pad_pos.x + W) &&
        (ball_pos.y <  pad_pos.y + H) && (ball_pos.y + ball_size >  pad_pos.y)){
        vec.x = -vec.x;
    }
}

void update_ball_pos(Coord2D& pos, Coord2D v){
    pos.x += v.x;
    pos.y += v.y;
}

void update_pad_pos(Coord2D& pos, int direction, short speed, short H, short pad_h){
    pos.y = std::clamp((int)pos.y + direction * speed, 0, H - pad_h);
}

bool left_wall_collision(Coord2D pos, short size){
    return pos.x + size <= 0;
}

bool right_wall_collision(Coord2D pos, short W, short size){
    return pos.x - size >= W;
}

void draw_score(SDL_Renderer* renderer, short score_l, short score_r, SDL_Color color, short W, short H, TTF_Font* font){
    SDL_Surface* surface = TTF_RenderText_Solid(font, (std::to_string(score_l) + "        " + std::to_string(score_r)).c_str(), color);   
    SDL_Texture* tex = SDL_CreateTextureFromSurface(renderer, surface);
    int w, h;
    SDL_QueryTexture(tex, nullptr, nullptr, &w, &h);
    //text pos : arg 1, 2 & HW - window
    SDL_Rect rect = {(W / 2) - (w / 2), 20, w, h};
    SDL_RenderCopy(renderer, tex, nullptr, &rect);
    SDL_FreeSurface(surface);
    SDL_DestroyTexture(tex);
}

int main(){
    SDL_Init(SDL_INIT_EVENTS | SDL_INIT_VIDEO);
    TTF_Init();
    //random device
    std::random_device rd;                         
    std::mt19937 gen(rd());                        
    std::uniform_int_distribution<int> dist(0, 1);
    int direction_x = (dist(gen) == 0) ? -1 : 1;
    int direction_y = (dist(gen) == 0) ? -1 : 1;

    TTF_Font* font = TTF_OpenFont("/System/Library/Fonts/Helvetica.ttc", 20);
    constexpr SDL_Color COLOR = {255, 255, 255, 255};

    constexpr short PAD_SPEED = 5;
    constexpr short WINDOW_WITDTH = 800;
    constexpr short WINDOW_HEIGHT = 600;

    SDL_Window* window = SDL_CreateWindow("Pong", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, WINDOW_WITDTH, WINDOW_HEIGHT, 0);
    SDL_Renderer* renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);
    Coord2D velocity(4 * direction_x, 3 * direction_y);

    constexpr short FRAME_RATE = 12; // ~60fps
    constexpr short BALL_SIZE = 10;
    constexpr short PAD_WIDTH = 10, PAD_HEIGHT = 75;

    constexpr short PADX = 20;
    const short middle = (WINDOW_HEIGHT / 2) - PAD_HEIGHT / 2;

    Coord2D left_pad(PADX, middle);
    Coord2D right_pad(WINDOW_WITDTH - PADX - PAD_WIDTH, middle);
    Coord2D ball_pos(WINDOW_WITDTH / 2, WINDOW_HEIGHT / 2);

    short score_left = 0, score_right = 0;
           
    bool running = true;
    SDL_Event event;
    while (running) {
        while (SDL_PollEvent(&event)){
            if (event.type == SDL_QUIT)
                running = false;
        }

        const Uint8* keys = SDL_GetKeyboardState(NULL);
        if (keys[SDL_SCANCODE_W])    update_pad_pos(left_pad,  -1, PAD_SPEED, WINDOW_HEIGHT, PAD_HEIGHT);
        if (keys[SDL_SCANCODE_S])    update_pad_pos(left_pad,   1, PAD_SPEED, WINDOW_HEIGHT, PAD_HEIGHT);
        if (keys[SDL_SCANCODE_UP])   update_pad_pos(right_pad, -1, PAD_SPEED, WINDOW_HEIGHT, PAD_HEIGHT);
        if (keys[SDL_SCANCODE_DOWN]) update_pad_pos(right_pad,  1, PAD_SPEED, WINDOW_HEIGHT, PAD_HEIGHT);

        ceiling_collision(ball_pos, WINDOW_HEIGHT, velocity, BALL_SIZE);
        left_pad_collision(ball_pos, left_pad, PAD_HEIGHT, PAD_WIDTH, velocity, BALL_SIZE);
        right_pad_collision(ball_pos, right_pad, PAD_HEIGHT, PAD_WIDTH, velocity, BALL_SIZE);
        update_ball_pos(ball_pos, velocity);

        if (left_wall_collision(ball_pos, BALL_SIZE) || right_wall_collision(ball_pos, WINDOW_WITDTH, BALL_SIZE)) {
            left_wall_collision(ball_pos, BALL_SIZE) ? score_right++ : score_left++;
            ball_pos = Coord2D(WINDOW_WITDTH / 2, WINDOW_HEIGHT / 2);
            velocity = Coord2D(4 * (dist(gen) ? 1 : -1), 3 * (dist(gen) ? 1 : -1));
        }

        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        SDL_RenderClear(renderer);
        SDL_SetRenderDrawColor(renderer, COLOR.r, COLOR.g, COLOR.b, COLOR.a);
        draw_score(renderer, score_left, score_right, COLOR, WINDOW_WITDTH, WINDOW_HEIGHT, font);
        draw_pad(renderer, left_pad, COLOR, PAD_WIDTH, PAD_HEIGHT);
        draw_pad(renderer, right_pad, COLOR, PAD_WIDTH, PAD_HEIGHT);
        draw_ball(renderer, ball_pos, BALL_SIZE, COLOR);
        SDL_RenderPresent(renderer);
        SDL_Delay(FRAME_RATE);
    }

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
