//  cd /Users/Programing/C++ && ./neural_network
#include "nn/network.hpp"
#include "nn/activations.hpp"
#include "nn/mnist.hpp"

int main() {
    std::cout << "Loading Fashion-MNIST...\n";
    Matrix X_train = load_images("../mnist_nn/fashion/train-images-idx3-ubyte", 10000);
    Matrix Y_train = load_labels("../mnist_nn/fashion/train-labels-idx1-ubyte", 10000);
    Matrix X_test  = load_images("../mnist_nn/fashion/t10k-images-idx3-ubyte",  1000);
    Matrix Y_test  = load_labels("../mnist_nn/fashion/t10k-labels-idx1-ubyte",  1000);
    std::cout << "Train: " << X_train.cols << " /Users/Programing/C++/LobsterLearn/nn Test: " << X_test.cols << "\n\n";

    std::mt19937 rng(42);
    NeuralNetwork net;
    net.add(Layer(784, 128, relu,   relu_d,   rng));
    net.add(Layer(128,  10, linear, linear_d, rng));

    std::cout << "=== Training (lr=0.001, 20 epochs, batch=64, Adam) ===\n";
    net.train(X_train, Y_train, 20, 0.001, 64, true, "fashion_checkpoint.txt");

    std::cout << "\n=== Test accuracy: "
              << std::fixed << std::setprecision(2)
              << net.accuracy(X_test, Y_test) * 100.0 << "% ===\n";

    return 0;
}
// cd /Users/Programing/C++/LobsterLearn && g++ -O3 -march=native -ffast-math -funroll-loops -flto -std=c++17 -o main main.cpp 2>&1 && ./main
