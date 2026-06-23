#!/bin/bash
# Terminal equivalent of the VS Code button. Drives CMake — no flags to remember.
set -e
cd "$(dirname "$0")"

cmake -S . -B build
cmake --build build

echo "----- output -----"
./build/backtester
