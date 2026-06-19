#pragma once
#include "layer.hpp"
#include "activations.hpp"
#include <iostream>
#include <iomanip>
#include <cassert>
#include <fstream>
#include <stdexcept>
#include <numeric>
#include <algorithm>
#include <random>
#include <sstream>
#include <string>

struct NeuralNetwork {
    std::vector<Layer> layers;
    std::mt19937 rng;
    int t = 0;

    NeuralNetwork() : rng(42) {}

    void add(Layer&& layer) {
        if (!layers.empty())
            assert(layers.back().output_size == layer.input_size);
        layers.push_back(std::move(layer));
    }

    Matrix forward(const Matrix& X, bool use_softmax = true) {
        Matrix A = X;
        for (auto& l : layers)
            A = l.forward(A);
        return use_softmax ? softmax(A) : A;
    }

    Matrix backward(const Matrix& dLoss, int batch_size) {
        Matrix g = dLoss;
        for (int i = (int)layers.size() - 1; i >= 0; --i)
            g = layers[i].backward(g, batch_size);
        return g;
    }

    void update(double lr, bool use_adam = false) {
        if (use_adam) {
            ++t;
            for (auto& l : layers) l.update_adam(lr, t);
        } else {
            for (auto& l : layers) l.update_sgd(lr);
        }
    }

    void save(const std::string& path) const {
        std::ofstream f(path);
        if (!f) throw std::runtime_error("Cannot open for writing: " + path);
        f << std::setprecision(17);
        for (const auto& l : layers) {
            for (int i = 0; i < l.W.rows; ++i) {
                for (int j = 0; j < l.W.cols; ++j) {
                    if (j > 0) f << " ";
                    f << l.W.at(i, j);
                }
                if (i < l.W.rows - 1) f << ";";
            }
            f << "|";
            for (int i = 0; i < l.b.rows; ++i) {
                if (i > 0) f << " ";
                f << l.b.at(i, 0);
            }
            f << "\n";
        }
    }

    void load(const std::string& path) {
        std::ifstream f(path);
        if (!f) {
            std::cout << "Fichier pas trouve : " << path << " -- initialisation aleatoire.\n";
            return;
        }
        std::string line;
        int layer_idx = 0;
        while (std::getline(f, line) && layer_idx < (int)layers.size()) {
            auto& l = layers[layer_idx++];
            std::size_t sep = line.find('|');
            std::string w_block = line.substr(0, sep);
            std::string b_block = line.substr(sep + 1);
            int row = 0;
            std::stringstream wss(w_block);
            std::string w_row;
            while (std::getline(wss, w_row, ';')) {
                std::istringstream rs(w_row);
                double v; int col = 0;
                while (rs >> v) l.W.at(row, col++) = v;
                ++row;
            }
            std::istringstream bss(b_block);
            double v; int i = 0;
            while (bss >> v) l.b.at(i++, 0) = v;
        }
    }

    double accuracy(const Matrix& X, const Matrix& Y) {
        Matrix Yhat = forward(X);
        int correct = 0;
        for (int j = 0; j < Yhat.cols; ++j) {
            int pred = 0, label = 0;
            for (int i = 1; i < Yhat.rows; ++i) {
                if (Yhat.at(i, j) > Yhat.at(pred, j)){  
                    pred = i;
                }
                if (Y.at(i, j) > Y.at(label, j)) {    
                    label = i;
                }
            }
            if (pred == label) ++correct;
        }
        return (double)correct / Yhat.cols;
    }

    void train(const Matrix& X, const Matrix& Y, int epochs, double lr, int batch_size,
               bool use_adam = false, const std::string& checkpoint = "", bool save_params = true) {
        if (!checkpoint.empty()) load(checkpoint);
        int m = X.cols;
        for (int e = 1; e <= epochs; ++e) {
            std::vector<int> indices(m);
            std::iota(indices.begin(), indices.end(), 0);
            std::shuffle(indices.begin(), indices.end(), rng);
            Matrix X_s(X.rows, m), Y_s(Y.rows, m);
            for (int j = 0; j < m; ++j) {
                for (int i = 0; i < X.rows; ++i) X_s.at(i, j) = X.at(i, indices[j]);
                for (int i = 0; i < Y.rows; ++i) Y_s.at(i, j) = Y.at(i, indices[j]);
            }

            for (int start = 0; start < m; start += batch_size) {
                int end = std::min(start + batch_size, m);
                Matrix X_batch = X_s.slice_cols(start, end);
                Matrix Y_batch = Y_s.slice_cols(start, end);

                Matrix Yhat = forward(X_batch);
                backward(ce_grad(Yhat, Y_batch), end - start);
                update(lr, use_adam);
            }

            Matrix Yhat = forward(X);
            double loss = cross_entropy(Yhat, Y);
            std::cout << "Epoch " << std::setw(3) << e
                      << "  Loss = " << std::fixed << std::setprecision(4) << loss
                      << "  Acc = "  << std::setprecision(2) << accuracy(X, Y) * 100.0 << "%\n";
            if (save_params && !checkpoint.empty()) save(checkpoint);
        }
    }
};


