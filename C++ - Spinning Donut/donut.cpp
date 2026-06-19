#include <cmath>
#include <cstdio>
#include <cstring>
#include <memory>
#include <string>
#include <unistd.h>

constexpr int   W = 80, H = 30;
constexpr float R1 = 1.0f, R2 = 2.0f, K2 = 45.0f;
constexpr float K1 = W * K2 * 2.5f / (8.0f * (R1 + R2));

const float THETA_SPACING = 0.02f;
const float PHI_SPACING   = 0.005f;
const std::string LUM = ".,-~:;=!*#$@";

void render(float A, float B){

    char  output[H][W];
    float zbuffer[H][W];
    float cosA = cosf(A);
    float cosB = cosf(B);
    float sinA = sinf(A);
    float sinB = sinf(B);

    memset(output, ' ', sizeof(output));
    memset(zbuffer, 0, sizeof(zbuffer));

    for (float theta = 0; theta < 2 * M_PI; theta += THETA_SPACING){

        float costheta = cosf(theta);
        float sintheta = sinf(theta);  

        for (float phi = 0; phi < 2 * M_PI; phi += THETA_SPACING){
            float cosphi = cosf(phi);
            float sinphi = sinf(phi);
            float circlex = R2 + R1 * costheta;
            float circley = R1 * sintheta;

            float x = circlex * (cosB * cosphi + sinA * sinB * sinphi) - circley * cosA * sinB;
            float y = circlex * (sinB * cosphi - sinA * cosB * sinphi) + circley * cosA * cosB;
            float z = K2 + cosA * circlex * sinphi + circley * sinA;

            float ooz = 1.0f / z;
            int xp = (int)(W / 2.0f + K1 * x * ooz);
            int yp = (int)(H / 2.0f - K1 * y * ooz * 0.5f); 

            if (ooz > zbuffer[yp][xp] && xp < W && yp < H){
                zbuffer[yp][xp] = ooz;
                float L = cosphi * costheta * sinB - cosA * costheta * sinphi - \
                sinA * sintheta + cosB * (cosA * sintheta - costheta * sinA * sinphi);
                int li = (int) (L * 8);
                output[yp][xp] = (li < 0) ? ' ' : LUM[li > 11 ? 11 : li];

            }

        }
    }
    printf("\x1b[H");
    for (auto& row : output){
        fwrite(row, 1, W, stdout);
        putchar('\n');
    }

}

int main(){
    float A = 0;
    float B = 0;
    for (;;){
        render(A, B);
        A += 0.02f;
        B += 0.01f;
        usleep(10000);
    }
    
}