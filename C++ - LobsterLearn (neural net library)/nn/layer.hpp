#pragma once
#include "matrix.hpp"
#include <functional>
#include <random>
#include <cmath>

struct Layer {
    int input_size, output_size;
    std::function<double(double)> act, act_dx;
    Matrix W, b, dW, db, Z, A, A_prev;
    Matrix mW, vW, mb, vb;

    Layer(int in, int out,
          std::function<double(double)> activation_fct,
          std::function<double(double)> activation_dx,
          std::mt19937& rng)
        : input_size(in), output_size(out),
          act(activation_fct), act_dx(activation_dx),
          W(out, in), dW(out, in),
          b(out, 1), db(out, 1),
          A_prev(in, 1), Z(out, 1), A(out, 1),
          mW(out, in), vW(out, in),
          mb(out, 1),  vb(out, 1)
    {
        std::normal_distribution<double> dist(0.0, std::sqrt(2.0 / in));
        for (int i = 0; i < out; ++i)
            for (int j = 0; j < in; ++j)
                W.data[i * in + j] = dist(rng);
    }

    Matrix forward(const Matrix& A_in) {
        A_prev = A_in;
        Z = W.dot(A_in);
        for (int i = 0; i < Z.rows; ++i)
            for (int j = 0; j < Z.cols; ++j)
                Z.data[i * Z.cols + j] += b.data[i];
        A = Z.apply(act);
        return A;
    }

    Matrix backward(const Matrix& dA, int batch_size) {
        Matrix dZ = dA.hadamard(Z.apply(act_dx));
        dW = dZ.dot(A_prev.T());
        dW.scale(1.0 / batch_size);
        db = Matrix(output_size, 1, 0.0);
        for (int i = 0; i < dZ.rows; ++i)
            for (int j = 0; j < dZ.cols; ++j)
                db.data[i] += dZ.data[i * dZ.cols + j];
        db.scale(1.0 / batch_size);
        return W.T().dot(dZ);
    }

    void update_sgd(double lr) {
        for (int i = 0; i < W.rows * W.cols; ++i) W.data[i] -= lr * dW.data[i];
        for (int i = 0; i < b.rows;          ++i) b.data[i] -= lr * db.data[i];
    }

    void update_adam(double lr, int t, double beta1 = 0.9, double beta2 = 0.999, double eps = 1e-8) {
        double bc1 = 1.0 - std::pow(beta1, t);
        double bc2 = 1.0 - std::pow(beta2, t);
        for (int i = 0; i < W.rows * W.cols; ++i) {
            mW.data[i] = beta1 * mW.data[i] + (1.0 - beta1) * dW.data[i];
            vW.data[i] = beta2 * vW.data[i] + (1.0 - beta2) * dW.data[i] * dW.data[i];
            W.data[i] -= lr * (mW.data[i] / bc1) / (std::sqrt(vW.data[i] / bc2) + eps);
        }
        for (int i = 0; i < b.rows; ++i) {
            mb.data[i] = beta1 * mb.data[i] + (1.0 - beta1) * db.data[i];
            vb.data[i] = beta2 * vb.data[i] + (1.0 - beta2) * db.data[i] * db.data[i];
            b.data[i]  -= lr * (mb.data[i] / bc1) / (std::sqrt(vb.data[i] / bc2) + eps);
        }
    }
};
