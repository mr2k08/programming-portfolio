#pragma once
#include "matrix.hpp"
#include <cmath>

// ============================================================
//  ACTIVATIONS
// ============================================================

double relu(double x)   { return x > 0 ? x : 0.0; }
double relu_d(double x) { return x > 0 ? 1.0 : 0.0; }
double linear(double x) { return x; }
double linear_d(double) { return 1.0; }

Matrix softmax(const Matrix& Z) {
    Matrix S(Z.rows, Z.cols);
    for (int j = 0; j < Z.cols; ++j) {
        double maxVal = Z.at(0, j);
        for (int i = 1; i < Z.rows; ++i)
            if (Z.at(i, j) > maxVal) maxVal = Z.at(i, j);
        double sumExp = 0.0;
        for (int i = 0; i < Z.rows; ++i) {
            S.at(i, j) = std::exp(Z.at(i, j) - maxVal);
            sumExp += S.at(i, j);
        }
        for (int i = 0; i < Z.rows; ++i)
            S.at(i, j) /= sumExp;
    }
    return S;
}

// ============================================================
//  LOSS FUNCTIONS
// ============================================================

double cross_entropy(const Matrix& Yhat, const Matrix& Y) {
    double loss = 0.0;
    for (int i = 0; i < Y.rows; ++i)
        for (int j = 0; j < Y.cols; ++j)
            loss -= Y.at(i, j) * std::log(Yhat.at(i, j) + 1e-9);
    return loss / Y.cols;
}

Matrix ce_grad(const Matrix& Yhat, const Matrix& Y) {
    Matrix G(Y.rows, Y.cols);
    for (int i = 0; i < Y.rows; ++i)
        for (int j = 0; j < Y.cols; ++j)
            G.at(i, j) = Yhat.at(i, j) - Y.at(i, j);
    return G;
}

double mse(const Matrix& Yhat, const Matrix& Y) {
    int n = Y.rows * Y.cols;
    double loss = 0.0;
    for (int i = 0; i < Yhat.rows; ++i)
        for (int j = 0; j < Yhat.cols; ++j) {
            double diff = Y.at(i, j) - Yhat.at(i, j);
            loss += diff * diff;
        }
    return loss / n;
}

Matrix mse_grad(const Matrix& Yhat, const Matrix& Y) {
    int n = Y.rows * Y.cols;
    Matrix G(Yhat.rows, Yhat.cols);
    for (int i = 0; i < Yhat.rows; ++i)
        for (int j = 0; j < Yhat.cols; ++j)
            G.at(i, j) = 2.0 * (Yhat.at(i, j) - Y.at(i, j)) / n;
    return G;
}
