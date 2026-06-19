#include <assert.h>
#include <stdlib.h>
#include <math.h>
#include <stdio.h>

struct Matrix {
    int row, col;
    float *data;
};

struct Matrix mat_create(int r, int c) {
    struct Matrix A;
    A.row = r;
    A.col = c;
    A.data = calloc(r * c, sizeof(float));
    if (A.data == NULL){
        A.row = 0;
        A.col = 0;
    } 
    return A;
}

struct Matrix mat_add(const struct Matrix *A, const struct Matrix *B) {
    assert(A->col == B->col && A->row == B->row);
    struct Matrix C = mat_create(A->row, A->col);
    for (int i = 0; i < A->col * A->row; ++i){
        C.data[i] = A->data[i] + B->data[i];
    }
    return C;
}

struct Matrix mat_T(const struct Matrix *A) {
    struct Matrix C = mat_create(A->col, A->row);
    for (int i = 0; i < A->row; ++i) {
        for (int j = 0; j < A->col; ++j) {
            C.data[j * A->row + i] = A->data[i * A->col + j];
        }
    }
    return C;
}

struct Matrix mat_hadamard(const struct Matrix *A, const struct Matrix *B){
    assert(A->col == B->col && A->row == B->row);
    struct Matrix C = mat_create(A->row, A->col);
    for (int i = 0; i < A->col * A->row; ++i){
        C.data[i] = A->data[i] * B->data[i];
    }
    return C;
}

struct Matrix mat_scale(const struct Matrix *A, float k){
    struct Matrix C = mat_create(A->row, A->col);
    for (int i = 0; i < A->col * A->row; ++i){
        C.data[i] = A->data[i] * k;
    }
    return C;
}

struct Matrix mat_apply(struct Matrix *A, float (*f)(float)){
    struct Matrix C = mat_create(A->row, A->col);
    for (int i = 0; i < A->col * A->row; ++i){
        C.data[i] = f(A->data[i]);
    }
    return C;
}

struct Matrix slice_cols(struct Matrix *A, int start, int end) {
    int n = end - start;
    struct Matrix S = mat_create(A->row, n);
    for (int i = 0; i < A->row; ++i)
        for (int j = 0; j < n; ++j)
            S.data[i * n + j] = A->data[i * A->col + start + j];
    return S;
}

struct Matrix mat_dot(const struct Matrix *A, const struct Matrix *B){
    assert(A->col == B->row);
    const int BLOCK = 32;
    struct Matrix C = mat_create(A->row, B->col);
    for (int i0 = 0; i0 < A->row; i0 += BLOCK){
    for (int k0 = 0; k0 < A->col; k0 += BLOCK){
    for (int j0 = 0; j0 < B->col; j0 += BLOCK){
    for (int i = i0; i < ((A->row > i0 + BLOCK) ? i0 + BLOCK : A->row); ++i){
    for (int k = k0; k < ((A->col > k0 + BLOCK) ? k0 + BLOCK : A->col); ++k){
        float aik = A->data[i * A->col + k]; 
        for (int j = j0; j < ((j0 + BLOCK < B->col) ? j0 + BLOCK : B->col); ++j){
            C.data[i * C.col + j] += aik * B->data[k * B->col + j]; } } } } } }
    return C;
}

float relu(float x)    { return x > 0 ? x : 0; }
float relu_d(float x)  { return x > 0 ? 1.0f : 0.0f; }
float linear(float x)  { return x; }
float linear_d(float x){ (void)x; return 1.0f; }
float sigmoidf(float x){ return 1.0f / (1.0f + expf(-x)); }

struct Matrix softmax(const struct Matrix *A){
    struct Matrix S = mat_create(A->row, A->col);
    for (int i = 0; i < A->col; ++i){
        float max = A->data[i];
        for (int j = 0; j < A->row; ++j){
            if (max < A->data[j * A->col + i]) { max = A->data[j * A->col + i]; } 
        } 
    float sum = 0.0f; 
    for (int j = 0; j < A->row; ++j){
        S.data[j * A-> col + i] = expf(A->data[j * A->col + i] - max);
        sum += S.data[j * A-> col + i];
    }
    for (int j = 0; j < A->row; ++j){
        S.data[j * A-> col + i] /= sum;
    }
    }
    return S;
}

float cross_entropy(const struct Matrix *Yhat, const struct Matrix *Y) {
    float loss = 0;
    for (int i = 0; i < Yhat->row; ++i){
        for (int j = 0; j < Yhat->col; ++j){
            loss -= Y->data[i * Y->col + j] * logf(Yhat->data[i * Yhat->col + j] + 1e-9f);
        }
    }
    return loss / Y->col;
}

struct Matrix cross_entropy_grad(const struct Matrix *Yhat, const struct Matrix *Y){
    struct Matrix G = mat_create(Yhat->row, Yhat->col);
    for (int i = 0; i < Yhat->row; ++i){
        for (int j = 0; j < Yhat->col; ++j){
            G.data[i * G.col + j] = (Yhat->data[i * Yhat->col + j] - Y->data[i * Y->col + j]);
        }
    }
    return G;
}

struct Layer{
    int in, out;
    float lr;
    float (*act)(float);
    float (*act_g)(float);
    struct Matrix W, dW, b, db, Z, dZ, A, A_prev;
};

void mat_rand_init(struct Matrix *A) {
    int fan_in = A->col;
    float limit = sqrtf(6.0f / fan_in);
    for (int i = 0; i < A->row * A->col; ++i) {
        float r = (float)rand() / (float)RAND_MAX;   // [0, 1]
        A->data[i] = (2.0f * r - 1.0f) * limit;      // [-limit, limit]
    }
}

struct Layer make_layer(int in, int out, float (*act)(float), float (*act_g)(float), float lr){
    struct Layer layer;
    layer.in = in;
    layer.out = out;
    layer.dW = mat_create(out, in);
    layer.W = mat_create(out, in);
    layer.b = mat_create(out, 1);
    layer.db = mat_create(out, 1);
    layer.Z = mat_create(out, 1);
    layer.A = mat_create(out, 1);
    layer.dZ = mat_create(out, 1); 
    layer.act = act;
    layer.act_g = act_g;
    layer.lr = lr;
    mat_rand_init(&layer.W);
    return layer;
};

struct Matrix forward(struct Layer *layer, float (*act)(float)){
    free(layer->Z.data);                              // release last batch's Z
    layer->Z = mat_dot(&layer->W, &layer->A_prev);
    for (int i = 0; i < layer->Z.row ; ++i) {
        for (int j = 0; j < layer->Z.col ; ++j) {
            layer->Z.data[i * layer->Z.col + j] += layer->b.data[i];   // bias broadcasts across the batch
        }
    }
    free(layer->A.data);                              // release last batch's A
    layer->A = mat_apply(&layer->Z, act);
    return layer->A;
}

struct Matrix backward(struct Layer *layer, const struct Matrix *dA, int batch_size){
    struct Matrix dfz = mat_apply(&layer->Z, layer->act_g);
    free(layer->dZ.data);                             // release last batch's dZ
    layer->dZ = mat_hadamard(dA, &dfz);
    free(dfz.data);                                   // temp, done with it

    struct Matrix aT = mat_T(&layer->A_prev);
    free(layer->dW.data);                             // release last batch's dW
    layer->dW = mat_dot(&layer->dZ, &aT);
    free(aT.data);                                    // temp, done with it
    for (int i = 0; i < layer->dW.row * layer->dW.col; ++i)
        layer->dW.data[i] /= batch_size;              // scale in place, no realloc

    for (int i = 0; i < layer->db.row; ++i) layer->db.data[i] = 0.0f;   // reset each batch
    for (int i = 0; i < layer->dZ.row; ++i)
        for (int j = 0; j < layer->dZ.col; ++j)
            layer->db.data[i] += layer->dZ.data[i * layer->dZ.col + j]; // sum gradient over the batch
    for (int i = 0; i < layer->db.row; ++i) layer->db.data[i] /= batch_size;

    struct Matrix Wt = mat_T(&layer->W);
    struct Matrix dA_prev = mat_dot(&Wt, &layer->dZ);
    free(Wt.data);                                    // temp, done with it
    return dA_prev;                                   // caller owns this
}

void sgd(struct Layer *layer, float lr){
    for (int i = 0; i < layer->W.row * layer->W.col; ++i)
        layer->W.data[i] -= lr * layer->dW.data[i];
    for (int i = 0; i < layer->b.row * layer->b.col; ++i)
        layer->b.data[i] -= lr * layer->db.data[i];
}

struct NN{
    int len;
    struct Layer *layers;
};

// Returns a new heap array of size len+1: the old layers copied in, plus layer at the end.
struct Layer *append(int len, struct Layer *lst, struct Layer *layer){
    struct Layer *out = malloc((len + 1) * sizeof(struct Layer));
    for (int i = 0; i < len; ++i){
        out[i] = lst[i];
    }
    out[len] = *layer;
    return out;
}

// Appends a layer to the network, checking that its input matches the previous output.
void add_layer(struct NN *nn, struct Layer *layer){
    if (nn->len > 0)
        assert(nn->layers[nn->len - 1].out == layer->in);
    struct Layer *grown = append(nn->len, nn->layers, layer);
    free(nn->layers);
    nn->layers = grown;
    nn->len++;
}

// Runs X through every layer, then softmax on the final logits.
struct Matrix nn_forward(struct NN *nn, const struct Matrix *X){
    struct Matrix A = *X;
    for (int i = 0; i < nn->len; ++i){
        nn->layers[i].A_prev = A;
        A = forward(&nn->layers[i], nn->layers[i].act);
    }
    return softmax(&A);
}

// Propagates the loss gradient backward through the layers, last to first.
struct Matrix nn_backward(struct NN *nn, const struct Matrix *dLoss, int batch_size){
    struct Matrix g = *dLoss;
    for (int i = nn->len - 1; i >= 0; --i){
        struct Matrix next = backward(&nn->layers[i], &g, batch_size);
        if (i != nn->len - 1) free(g.data);   // free the intermediate gradient (not the caller's dLoss)
        g = next;
    }
    return g;
}

void update(float lr, struct NN *nn, int len){
    for (int i = 0; i < len; ++i){
        sgd(&nn->layers[i], lr);
    }
}

// Frees every buffer a layer owns. A_prev is NOT freed: it aliases the previous
// layer's A (or the input X), which is owned elsewhere.
void free_layer(struct Layer *l){
    free(l->W.data);  free(l->dW.data);
    free(l->b.data);  free(l->db.data);
    free(l->Z.data);  free(l->A.data);  free(l->dZ.data);
}

// Frees all layers and the layer array.
void free_nn(struct NN *nn){
    for (int i = 0; i < nn->len; ++i)
        free_layer(&nn->layers[i]);
    free(nn->layers);
    nn->layers = NULL;
    nn->len = 0;
}



// MNIST stores its header integers big-endian; rebuild one from 4 bytes.
static int read_int32_be(FILE *f) {
    unsigned char buf[4];
    fread(buf, 1, 4, f);
    return (buf[0] << 24) | (buf[1] << 16) | (buf[2] << 8) | buf[3];
}

// Loads the image file into a (dim x n) matrix: one column per image, pixels scaled to [0,1].
// max > 0 caps the number of images loaded.
struct Matrix load_images(const char *path, int max) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "Cannot open: %s\n", path);
        return (struct Matrix){0};
    }
    assert(read_int32_be(f) == 2051);      // magic number for image files
    int n    = read_int32_be(f);
    int rows = read_int32_be(f);
    int cols = read_int32_be(f);
    int dim  = rows * cols;                // 28 * 28 = 784
    if (max > 0 && max < n) n = max;

    struct Matrix X = mat_create(dim, n);
    for (int j = 0; j < n; ++j) {
        for (int i = 0; i < dim; ++i) {
            unsigned char px;
            fread(&px, 1, 1, f);
            X.data[i * X.col + j] = px / 255.0f;
        }
    }
    fclose(f);
    return X;
}

// Loads the label file into a (10 x n) one-hot matrix: column j is all zeros
// except a 1 in the row of that image's digit.
struct Matrix load_labels(const char *path, int max) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "Cannot open: %s\n", path);
        return (struct Matrix){0};
    }
    assert(read_int32_be(f) == 2049);      // magic number for label files
    int n = read_int32_be(f);
    if (max > 0 && max < n) n = max;

    struct Matrix Y = mat_create(10, n);   // calloc already zeroed it
    for (int j = 0; j < n; ++j) {
        unsigned char label;
        fread(&label, 1, 1, f);
        Y.data[label * Y.col + j] = 1.0f;
    }
    fclose(f);
    return Y;
}

// Applies one SGD step to every layer in the network.
void nn_update(struct NN *nn, float lr) {
    for (int i = 0; i < nn->len; ++i)
        sgd(&nn->layers[i], lr);
}

// Fraction of samples whose predicted digit (argmax of Yhat) matches the label.
float accuracy(struct NN *nn, const struct Matrix *X, const struct Matrix *Y) {
    struct Matrix Yhat = nn_forward(nn, X);
    int correct = 0;
    for (int j = 0; j < Yhat.col; ++j) {
        int pred = 0, label = 0;
        for (int i = 1; i < Yhat.row; ++i) {
            if (Yhat.data[i * Yhat.col + j] > Yhat.data[pred  * Yhat.col + j]) pred  = i;
            if (Y->data[i * Y->col + j]     > Y->data[label * Y->col + j])     label = i;
        }
        if (pred == label) ++correct;
    }
    free(Yhat.data);
    return (float)correct / Yhat.col;
}

// One full SGD training run: each epoch shuffles the data, walks it in
// mini-batches (forward -> loss gradient -> backward -> update), then reports.
void train(struct NN *nn, const struct Matrix *X, const struct Matrix *Y,
           int epochs, float lr, int batch_size) {
    int m = X->col;
    int *idx = malloc(m * sizeof(int));
    for (int i = 0; i < m; ++i) idx[i] = i;

    for (int e = 1; e <= epochs; ++e) {
        // Fisher-Yates shuffle of the column indices.
        for (int i = m - 1; i > 0; --i) {
            int k = rand() % (i + 1);
            int tmp = idx[i]; idx[i] = idx[k]; idx[k] = tmp;
        }
        // Build shuffled copies of X and Y by gathering columns in the new order.
        struct Matrix Xs = mat_create(X->row, m);
        struct Matrix Ys = mat_create(Y->row, m);
        for (int j = 0; j < m; ++j) {
            for (int i = 0; i < X->row; ++i) {
                Xs.data[i * m + j] = X->data[i * X->col + idx[j]];
            }
            for (int i = 0; i < Y->row; ++i) {
                Ys.data[i * m + j] = Y->data[i * Y->col + idx[j]];
            }
        }

        // Mini-batch loop.
        for (int start = 0; start < m; start += batch_size) {
            int end = (start + batch_size < m) ? start + batch_size : m;
            struct Matrix Xb   = slice_cols(&Xs, start, end);
            struct Matrix Yb   = slice_cols(&Ys, start, end);
            struct Matrix Yhat = nn_forward(nn, &Xb);
            struct Matrix g    = cross_entropy_grad(&Yhat, &Yb);
            struct Matrix gin  = nn_backward(nn, &g, end - start);
            nn_update(nn, lr);
            free(Xb.data); free(Yb.data); free(Yhat.data); free(g.data); free(gin.data);
        }
        free(Xs.data); free(Ys.data);

        // End-of-epoch metrics over the whole set.
        struct Matrix Yhat = nn_forward(nn, X);
        float loss = cross_entropy(&Yhat, Y);
        printf("Epoch %3d  Loss = %.4f  Acc = %.2f%%\n",
               e, loss, accuracy(nn, X, Y) * 100.0f);
        free(Yhat.data);
    }
    free(idx);
}

int main(){
    srand(42);   // fixed seed for reproducible runs; swap for time(NULL) to vary

    printf("Loading Fashion-MNIST...\n");
    struct Matrix X_train = load_images("fashion/train-images-idx3-ubyte", 10000);
    struct Matrix Y_train = load_labels("fashion/train-labels-idx1-ubyte", 10000);
    struct Matrix X_test  = load_images("fashion/t10k-images-idx3-ubyte",  1000);
    struct Matrix Y_test  = load_labels("fashion/t10k-labels-idx1-ubyte",  1000);
    printf("Train: %d   Test: %d\n\n", X_train.col, X_test.col);

    float lr = 0.1f;

    // 784 -> 128 (relu) -> 10 (linear logits; softmax is applied in nn_forward)
    struct NN net = {0};
    struct Layer l1 = make_layer(784, 128, relu,   relu_d,   lr);
    add_layer(&net, &l1);
    struct Layer l2 = make_layer(128,  10, linear, linear_d, lr);
    add_layer(&net, &l2);

    printf("=== Training (lr=%.3f, 20 epochs, batch=64, SGD) ===\n", lr);
    train(&net, &X_train, &Y_train, 30, lr, 64);

    printf("\n=== Test accuracy: %.2f%% ===\n",
           accuracy(&net, &X_test, &Y_test) * 100.0f);

    free(X_train.data); free(Y_train.data);
    free(X_test.data);  free(Y_test.data);
    free_nn(&net);
    return 0;
}