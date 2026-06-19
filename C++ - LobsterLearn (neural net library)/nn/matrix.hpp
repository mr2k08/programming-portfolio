#pragma once
#include <vector>
#include <functional>
#include <algorithm>

struct Matrix {
    int rows, cols;
    std::vector<double> data;

    Matrix(int r, int c, double init = 0.0)
        : rows(r), cols(c), data(r * c, init) {}

    double&       at(int i, int j)       { return data[i * cols + j]; }
    const double& at(int i, int j) const { return data[i * cols + j]; }
    double&       flat_at(int i)         { return data[i]; }
    const double& flat_at(int i) const   { return data[i]; }

    Matrix operator+(const Matrix& B) const {
        Matrix C(rows, cols);
        for (int i = 0; i < rows * cols; ++i)
            C.data[i] = data[i] + B.data[i];
        return C;
    }

    Matrix operator-(const Matrix& B) const {
        Matrix C(rows, cols);
        for (int i = 0; i < rows * cols; ++i)
            C.data[i] = data[i] - B.data[i];
        return C;
    }

    Matrix operator*(double k) const {
        Matrix C(rows, cols);
        for (int i = 0; i < rows * cols; ++i)
            C.data[i] = data[i] * k;
        return C;
    }

    Matrix& operator+=(const Matrix& B) {
        for (int i = 0; i < rows * cols; ++i)
            data[i] += B.data[i];
        return *this;
    }

    Matrix& operator-=(const Matrix& B) {
        for (int i = 0; i < rows * cols; ++i)
            data[i] -= B.data[i];
        return *this;
    }

    Matrix& scale(double k) {
        for (int i = 0; i < rows * cols; ++i)
            data[i] *= k;
        return *this;
    }

    Matrix hadamard(const Matrix& B) const {
        Matrix C(rows, cols);
        for (int i = 0; i < rows * cols; ++i)
            C.data[i] = data[i] * B.data[i];
        return C;
    }

    template<typename F>
    Matrix apply(F f) const {
        Matrix C(rows, cols);
        for (int i = 0; i < rows * cols; ++i)
            C.data[i] = f(data[i]);
        return C;
    }

    Matrix dot(const Matrix& B) const {
        Matrix C(rows, B.cols, 0.0);
        constexpr int TILE = 32;
        for (int i0 = 0; i0 < rows; i0 += TILE)
        for (int k0 = 0; k0 < cols; k0 += TILE)
        for (int j0 = 0; j0 < B.cols; j0 += TILE)
        for (int i = i0, iE = std::min(i0+TILE, rows); i < iE; ++i)
        for (int k = k0, kE = std::min(k0+TILE, cols); k < kE; ++k) {
            double aik = data[i * cols + k];
            for (int j = j0, jE = std::min(j0+TILE, B.cols); j < jE; ++j)
                C.data[i * B.cols + j] += aik * B.data[k * B.cols + j];
        }
        return C;
    }

    Matrix T() const {
        Matrix A(cols, rows);
        for (int i = 0; i < rows; ++i)
            for (int j = 0; j < cols; ++j)
                A.data[j * rows + i] = data[i * cols + j];
        return A;
    }

    Matrix slice_cols(int start, int end) const {
        int n = end - start;
        Matrix S(rows, n);
        for (int i = 0; i < rows; ++i)
            for (int j = 0; j < n; ++j)
                S.data[i * n + j] = data[i * cols + start + j];
        return S;
    }
};