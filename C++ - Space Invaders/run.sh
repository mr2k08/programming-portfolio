#!/bin/zsh
cd "$(dirname "$0")"
g++ -std=c++17 Atari.cpp -o output/Atari \
    -I/opt/homebrew/include/SDL2 -L/opt/homebrew/lib \
    -lSDL2 -lSDL2_image -lSDL2_ttf -lSDL2_mixer && ./output/Atari
