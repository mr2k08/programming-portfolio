#pragma once
#include "matrix.hpp"
#include <fstream>
#include <stdexcept>
#include <cassert>
#include <string>

static int read_int32_be(std::ifstream& f) {
    unsigned char buf[4];
    f.read(reinterpret_cast<char*>(buf), 4);
    return (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3];
}

Matrix load_images(const std::string& path, int max = -1) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("Cannot open: " + path);
    assert(read_int32_be(f) == 2051);
    int n = read_int32_be(f);
    int dim = read_int32_be(f) * read_int32_be(f);
    if (max > 0 && max < n) n = max;
    Matrix X(dim, n);
    for (int j = 0; j < n; ++j)
        for (int i = 0; i < dim; ++i) {
            unsigned char px;
            f.read(reinterpret_cast<char*>(&px), 1);
            X.at(i, j) = px / 255.0;
        }
    return X;
}

Matrix load_labels(const std::string& path, int max = -1) {
    std::ifstream f(path, std::ios::binary);
    if (!f) throw std::runtime_error("Cannot open: " + path);
    assert(read_int32_be(f) == 2049);
    int n = read_int32_be(f);
    if (max > 0 && max < n) n = max;
    Matrix Y(10, n, 0.0);
    for (int j = 0; j < n; ++j) {
        unsigned char label;
        f.read(reinterpret_cast<char*>(&label), 1);
        Y.at(label, j) = 1.0;
    }
    return Y;
}
