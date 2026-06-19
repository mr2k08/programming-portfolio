#include <stdlib.h>
#include <cstdlib>
#include <SDL.h>
#include <time.h>

struct Pos{
    int x, y;
};

void draw_rect(SDL_Renderer* renderer, SDL_Rect rect, SDL_Color color){
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_RenderDrawRect(renderer, &rect);
    SDL_RenderFillRect(renderer, &rect);
}

void draw_apple(SDL_Renderer* renderer, Pos pos, int dim){
    SDL_Rect apple = {pos.x, pos.y, dim, dim};
    SDL_Color color = {255, 0, 0, 255};
    draw_rect(renderer, apple, color);
}

void draw_snake(SDL_Renderer *renderer, Pos *snake, int len, int dim) {
    SDL_Color color = {0, 255, 0, 255};
    for (int i = 0; i < len; i++) {
        SDL_Rect rect = {snake[i].x, snake[i].y, dim, dim};
        draw_rect(renderer, rect, color);
    }
}

Pos generate_apple(int min, int max, int len, Pos *snake, int dim){
    Pos apple;
    bool overlap = true;
    while (overlap){
        apple.x = (min + rand() % (max - min + 1)) * dim;
        apple.y = (min + rand() % (max - min + 1)) * dim;
        overlap = false;
        for (int i = 0; i < len; ++i){
            if (apple.x == snake[i].x && apple.y == snake[i].y){
                overlap = true;
                break;
            }
        }
    }
    return apple;
}

bool apple_eaten(Pos head, Pos apple){
    return head.x == apple.x && head.y == apple.y;
}

bool is_opposite(SDL_Keycode a, SDL_Keycode b){
    return (a == SDLK_UP    && b == SDLK_DOWN) ||
           (a == SDLK_DOWN  && b == SDLK_UP)   ||
           (a == SDLK_LEFT  && b == SDLK_RIGHT)||
           (a == SDLK_RIGHT && b == SDLK_LEFT);
}

void update_snake(int *len, Pos *positions, SDL_Keycode direction, Pos apple, int inc){
    Pos head = positions[*len - 1];
    switch (direction){
        case SDLK_UP:
            head.y -= inc;
            break;
        case SDLK_DOWN:
            head.y += inc;
            break;
        case SDLK_LEFT:
            head.x -= inc;
            break;
        case SDLK_RIGHT:
            head.x += inc;
            break;
    }
    if (apple_eaten(head, apple)){
        positions[*len] = head;   // grow: append new head, keep tail
        (*len)++;
    } else {
        for (int i = 0; i < *len - 1; ++i){
            positions[i] = positions[i + 1];
        }
        positions[*len - 1] = head;
    }
}

bool tail_collision(Pos *snake, int len) {
    Pos head = snake[len - 1];
    for (int i = 0; i < len - 1; i++) {
        if (snake[i].x == head.x && snake[i].y == head.y)
            return true;
    }
    return false;
}

int main(){
    const int GRID_SIZE = 50;
    const int SQUARE_SIZE = 10;
    const int GRID_SIDE = GRID_SIZE * SQUARE_SIZE;
    const int MAX_LEN = GRID_SIZE * GRID_SIZE;
    const int FRAME_DELAY = 80;

    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS);
    SDL_Window* window = SDL_CreateWindow("snake", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED, GRID_SIDE, GRID_SIDE, 0);
    SDL_Renderer* renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);

    srand(time(NULL));

    Pos snake[MAX_LEN];
    int len = 3;
    snake[0] = (Pos){GRID_SIZE / 2 * SQUARE_SIZE, GRID_SIZE / 2 * SQUARE_SIZE};
    snake[1] = (Pos){GRID_SIZE / 2 * SQUARE_SIZE + SQUARE_SIZE, GRID_SIZE / 2 * SQUARE_SIZE};
    snake[2] = (Pos){GRID_SIZE / 2 * SQUARE_SIZE + 2* SQUARE_SIZE, GRID_SIZE / 2 * SQUARE_SIZE};

    Pos apple = generate_apple(0, GRID_SIZE - 1, len, snake, SQUARE_SIZE);

    SDL_Keycode direction = SDLK_RIGHT;
    int running = 1;
    Uint32 last_update = SDL_GetTicks();

    while (running) {
        SDL_Event event;
        while (SDL_PollEvent(&event)) {
            if (event.type == SDL_QUIT) running = 0;
            if (event.type == SDL_KEYDOWN) {
                SDL_Keycode key = event.key.keysym.sym;
                if (key != direction && !is_opposite(key, direction)){
                    if (key == SDLK_UP || key == SDLK_DOWN ||
                        key == SDLK_LEFT || key == SDLK_RIGHT){
                        direction = key;
                    }
                }
                
            }
        }

        Uint32 now = SDL_GetTicks();
        if (now - last_update >= FRAME_DELAY) {
            update_snake(&len, snake, direction, apple, SQUARE_SIZE);

            Pos head = snake[len - 1];
            if (apple_eaten(head, apple))
                apple = generate_apple(0, GRID_SIZE - 1, len, snake, SQUARE_SIZE);

            if (head.x < 0 || head.x >= GRID_SIDE ||
                head.y < 0 || head.y >= GRID_SIDE ||
                tail_collision(snake, len))
                running = 0;

            last_update = now;
        }

        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        SDL_RenderClear(renderer);
        draw_snake(renderer, snake, len, SQUARE_SIZE);
        draw_apple(renderer, apple, SQUARE_SIZE);
        SDL_RenderPresent(renderer);
    }

    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
