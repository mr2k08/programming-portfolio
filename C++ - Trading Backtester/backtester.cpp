#include <iostream>
#include <sstream>
#include <algorithm>
#include <utility>
#include <vector>
#include <string>
#include <fstream>

struct DataPoint{
    std::string date;
    float high, low;
    float open, close;
    DataPoint(std::string d, float o, float c, float h, float l) : date(d), open(o), close(c), high(h), low(l) {}
};

std::vector<DataPoint> parseCSV(const std::string& file_name){
    std::vector<DataPoint> timeline = {};
    std::ifstream file(file_name);
    if (!file){
        return {};
    }
    std::string line;
    while (getline(file, line)){
        std::istringstream iss(line);
        std::string cells[5];          // presized static array, 5 fields

        for (int i = 0; i < 5; i++) { 
            std::getline(iss, cells[i], ',');   // each field lands in its slot
        }
        DataPoint P(
            cells[0],              // date  (stays string)
            std::stof(cells[1]),   // open
            std::stof(cells[2]),   // high
            std::stof(cells[3]),   // low
            std::stof(cells[4])    // close
        );
            timeline.push_back(P);
        }
    return timeline;
    }

class Backtester{

    private:

    int period;
    int slow, fast;
    std::vector<float> averages = {};

    std::vector<DataPoint> timeline;

    float get_average(int window, int current_day){
        // back door: asking for a day past the data = caller bug. fail loud.
        if (current_day >= (int)timeline.size()){
            std::cerr << "get_average: current_day out of range\n";
            return -1;
        }
        // front door: early days, not enough history behind. clamp start to 0.
        int start = std::max(current_day - window + 1, 0);

        float total = 0;
        for (int i = start; i <= current_day; ++i){
            DataPoint p = timeline[i];
            total += (p.open + p.high + p.low + p.close) / 4.0f;
        }
        int count = current_day - start + 1;   // bars actually summed
        return total / count;                  // divide by real count, not window
    }

    public:

    Backtester(std::vector<DataPoint> tl, int days, int s, int f) : timeline(tl), slow(s), fast(f) {}

    void signal(){
        for (int i{}; i < timeline.size(); ++i){
            std::cout << "day " << i << ": ";
            float sa = get_average(slow, i);
            float fa = get_average(fast, i);
            float diff = sa - fa;
        
        if (averages.size() > 1){
            if (averages.back() * diff < 0){
                if (diff > 0){ std::cout << "Sell\n"; }
                else{ std::cout << "Buy\n"; }
            }
            else{ std::cout<<"Hold\n"; }
        }
        else{ std::cout<<"Hold\n"; }
        averages.push_back(diff);
        std::cout << "-------------------------------------------------------\n";
        }
    }
};

int main(){
    // 1. load the data
    std::vector<DataPoint> data = parseCSV("test.csv");
    if (data.empty()){
        std::cerr << "No data loaded. Run from the backtester folder, "
                     "or check the test.csv path.\n";
        return 1;
    }
    std::cout << "Loaded " << data.size() << " bars.\n";

    // 2. build the backtester:  (data, days unused, slow=15, fast=5)
    Backtester bt(data, 0, 15, 5);

    // 3. run the strategy — prints a signal per bar
    bt.signal();
    std::cout << "\n";

    return 0;
}