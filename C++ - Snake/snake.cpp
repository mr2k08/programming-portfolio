#include "SDL_keycode.h"
#include <cstddef>
#include <ios>
#include <iostream>
#include <SDL.h>
#include <SDL_ttf.h>
#include <deque>
#include <random>
#include <tuple>
#include <unordered_map>
#include <algorithm>
#include <set>
#include <string>
#include <fstream>

void draw_rect(SDL_Renderer* renderer, SDL_Rect rect, SDL_Color color){
    SDL_SetRenderDrawColor(renderer, color.r, color.g, color.b, color.a);
    SDL_RenderDrawRect(renderer, &rect);
    SDL_RenderFillRect(renderer, &rect);
}

void draw_apple(SDL_Renderer* renderer, std::tuple<int, int> coords, int dim, int offset){
    SDL_Rect apple = {std::get<0>(coords) * dim, std::get<1>(coords) * dim + offset, dim, dim};
    draw_rect(renderer, apple, {255, 0, 0, 255}); //RGBA
}

std::tuple<int, int> generate_apple(std::mt19937& gen, std::uniform_int_distribution<int>& dist, const std::deque<std::tuple<int, int>>& snake){
    std::tuple<int, int> apple = {dist(gen), dist(gen)};
    while (std::find(snake.begin(), snake.end(), apple) != snake.end())
        apple = {dist(gen), dist(gen)};
    return apple;
}

bool apple_eaten(const std::deque<std::tuple<int, int>>& snake, std::tuple<int, int> apple){
    return std::find(snake.begin(), snake.end(), apple) != snake.end();
}

void update_snake(std::deque<std::tuple<int, int>>& positions, SDL_Keycode direction, std::tuple<int, int> apple, bool ate_apple){
    auto head = positions.back();
    switch (direction){
        case SDLK_UP:
            positions.push_back({std::get<0>(head), std::get<1>(head) - 1});
            break;
        case SDLK_DOWN:
            positions.push_back({std::get<0>(head), std::get<1>(head) + 1});
            break;
        case SDLK_LEFT:
            positions.push_back({std::get<0>(head) - 1, std::get<1>(head)});
            break;
        case SDLK_RIGHT:
            positions.push_back({std::get<0>(head) + 1, std::get<1>(head)});
            break;
    }
    if (!apple_eaten(positions, apple)){
        positions.pop_front();
    }
}

bool tail_collision(const std::deque<std::tuple<int, int>>& snake){
    std::set<std::tuple<int,int>> unique(snake.begin(), snake.end());
    return unique.size() < snake.size();
    }

void wall_collision(std::deque<std::tuple<int, int>>& positions, int dim){
    auto& head = positions.back();
    if      (std::get<0>(head) > dim -1) std::get<0>(head) = 0;
    else if (std::get<0>(head) < 0)  std::get<0>(head) = dim - 1;   
    if      (std::get<1>(head) > dim -1) std::get<1>(head) = 0;
    else if (std::get<1>(head) < 0)  std::get<1>(head) = dim - 1;
}

void draw_snake(const std::deque<std::tuple<int, int>>& positions, SDL_Renderer* renderer, int dim, int offset){
    for (auto& [x, y] : positions){
        SDL_Rect snake_part = {x * dim, y * dim + offset, dim, dim};
        draw_rect(renderer, snake_part, {0, 255, 0, 255});
    }
}

void draw_score(SDL_Renderer* renderer, TTF_Font* font, int score, int high_score){
    if (score > high_score){
        high_score = score;
    }
    SDL_Surface* surface = TTF_RenderText_Blended(
        font, ("Score: " + std::to_string(score) + "     High Score : "+ std::to_string(high_score)).c_str(), {255, 255, 255, 255});
    SDL_Texture* texture = SDL_CreateTextureFromSurface(renderer, surface);
    SDL_FreeSurface(surface);
    int w, h;
    SDL_QueryTexture(texture, nullptr, nullptr, &w, &h);
    SDL_Rect dst = {10, 5, w, h};
    SDL_RenderCopy(renderer, texture, nullptr, &dst);
    SDL_DestroyTexture(texture);
}

void save_score(const int score){
    std::ofstream file("score.txt");
    if (file.is_open()){
        file << std::to_string(score) << std::endl;
        file.close();
    }
    else{
        std::cout << "score file cannot be opened" << std::endl;
    }
}

int load_high_score(const std::string file_name) {
      std::ifstream file(file_name);
      std::string line;
      std::getline(file, line);
      return line.empty() ? 0 : std::stoi(line);
  }

int main(){

    constexpr int GRID_SIZE = 50;
    constexpr int SQUARE_SIZE = 10;
    constexpr int frame_gap = 60;
    constexpr int SCOREBAR_HEIGHT = 30;
    const int GRID_SIDE = GRID_SIZE * SQUARE_SIZE;
    const std::string FILE_NAME = "score.txt";
    const int HIGH_SCORE = load_high_score(FILE_NAME);

    std::deque<std::tuple<int, int>> snake = {{10, 10}, {10, 11}, {10, 12}};
    std::unordered_map<SDL_Keycode, SDL_Keycode> opposites = {{SDLK_UP, SDLK_DOWN}, {SDLK_DOWN, SDLK_UP}, {SDLK_LEFT, SDLK_RIGHT}, {SDLK_RIGHT, SDLK_LEFT}};
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<int> dist(1, GRID_SIZE - 1);

    SDL_Keycode direction = SDLK_RIGHT;
    SDL_Event event;
    std::tuple<int, int> current_apple = generate_apple(gen, dist, snake);
    int score = 0;

    SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS);
    TTF_Init();
    SDL_Window* window = SDL_CreateWindow("Snake", SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                                          GRID_SIDE, GRID_SIDE + SCOREBAR_HEIGHT, 0);
    TTF_Font* font = TTF_OpenFont("/System/Library/Fonts/Helvetica.ttc", 20);

    SDL_Renderer* renderer = SDL_CreateRenderer(window, -1, SDL_RENDERER_ACCELERATED);

    bool running = true;
    while (running && !tail_collision(snake)){
        bool direction_changed = false;
        while (SDL_PollEvent(&event)){
            if (event.type == SDL_QUIT) running = false;
            if (!direction_changed && event.type == SDL_KEYDOWN && opposites[event.key.keysym.sym] != direction){
                direction = event.key.keysym.sym;
                direction_changed = true;
            }
        }
        bool apple_ate = apple_eaten(snake, current_apple);
        update_snake(snake, direction, current_apple, apple_ate);
        wall_collision(snake, GRID_SIZE);
        if (apple_ate){
            current_apple = generate_apple(gen, dist, snake);
            score++;
        }
        SDL_SetRenderDrawColor(renderer, 0, 0, 0, 255);
        SDL_RenderClear(renderer);
        draw_rect(renderer, {0, 0, GRID_SIDE, SCOREBAR_HEIGHT}, {30, 30, 30, 255});
        draw_score(renderer, font, score, HIGH_SCORE);
        draw_snake(snake, renderer, SQUARE_SIZE, SCOREBAR_HEIGHT);
        draw_apple(renderer, current_apple, SQUARE_SIZE, SCOREBAR_HEIGHT);
        SDL_RenderPresent(renderer);
        SDL_Delay(frame_gap);
    }

    save_score(score);
    TTF_CloseFont(font);
    TTF_Quit();
    SDL_DestroyRenderer(renderer);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
