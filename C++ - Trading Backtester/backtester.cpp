// Trading backtester — plug-in strategies scored by P&L.
// No libraries, no special flags. Build with exactly:
// clang++ backtester.cpp -std=c++20 -isystem /usr/local/include -isystem /opt/homebrew/include -L/opt/homebrew/lib -larrow -lparquet -o backtester && ./backtester
#include "parsers.h"
#include <arrow/api.h>   // keep: cpp-run greps this file for <arrow to link -larrow -lparquet
#include <iostream>
#include <algorithm>
#include <cmath>
#include <functional>
#include <stdexcept>
#include <vector>
#include <string>

// What a strategy is allowed to see: the full timeline, but gated at `today`.
// Any attempt to read a future bar throws — look-ahead is impossible, not just discouraged.
class MarketView{
    const std::vector<Candle> &tl;
    int today_;
    public:
    MarketView(const std::vector<Candle> &t, int today) : tl(t), today_(today) {}

    int today() const { return today_; }            // index of the current bar
    int size()  const { return today_ + 1; }        // how many bars are visible

    // bar(i): absolute index, must be 0..today. Future = throw.
    const Candle &bar(int i) const {
        if (i < 0 || i > today_)
            throw std::out_of_range("MarketView: no peeking past today");
        return tl[i];
    }
    const Candle &ago(int k) const { return bar(today_ - k); }   // k bars back (0 = today)
};

// Simple moving average of `type` over the last `window` bars ending today.
double sma(const MarketView &m, const std::string &type, int window){
    int end = m.today();
    int start = std::max(end - window + 1, 0);
    double total = 0;
    for (int i = start; i <= end; ++i) {
        total += m.bar(i).map.at(type);
    }
    return total / (end - start + 1);
}

// A strategy decides today's position from what it's allowed to see.
//   +1 = full long, -1 = full short, 0 = flat (values in between = sizing).
using Strategy = std::function<double(const MarketView &)>;

class Backtester{

    std::vector<Candle> timeline;

    public:

    Backtester(std::vector<Candle> tl) : timeline(std::move(tl)) {}

    // The ONE shared scorer. Written once, reused by every strategy.
    // Runs a real account: compounds each day's P&L and pays `fee` on every
    // change of position. Also reports directional accuracy.
    //   fee = cost per unit of turnover, e.g. 0.001 = 0.1% (a full flip costs 2x).
    void evaluate(const std::string &name, const Strategy &decide, double fee = 0.001){
        double equity = 1.0;            // account balance, starts at $1
        double prev_pos = 0.0;          // yesterday's position
        int correct = 0, traded = 0;

        for (int i = 0; i + 1 < (int)timeline.size(); ++i){
            // The strategy sees a view gated at today (i). The referee (this loop)
            // still reads tomorrow below to score the bet — but the player can't.
            MarketView view(timeline, i);
            double pos = decide(view);                   // strategy's call for the day

            double turnover = std::abs(pos - prev_pos);  // how much we changed our position
            equity *= (1.0 - fee * turnover);            // pay trading cost on the change
            prev_pos = pos;

            double c0  = timeline[i].map.at("c");
            double c1  = timeline[i + 1].map.at("c");
            double ret = (c1 - c0) / c0;                 // tomorrow's price move

            equity *= (1.0 + pos * ret);                 // compound the day's P&L

            if (pos != 0){                               // only score days we took a side
                bool right = (pos > 0 && ret > 0) || (pos < 0 && ret < 0);
                if (right){ 
                    ++correct;
                }
                ++traded;
            }
        }

        std::cout << name
                  << "  ->  P&L = " << (equity - 1.0) * 100 << "%"
                  << "  |  directional = " << (traded ? 100.0 * correct / traded : 0.0) << "%"
                  << "  (" << traded << " trades)\n";
    }
};

// ── Strategies ──────────────────────────────────────────────────────────
// Each returns a Strategy that captures its own parameters.

// SMA crossover with a neutral band (band = fraction of price, e.g. 0.03 = 3%).
Strategy sma_crossover(int slow, int fast, double band){
    return [slow, fast, band](const MarketView &m) -> double {
        double sa = sma(m, "c", slow);
        double fa = sma(m, "c", fast);
        double diff = fa - sa;
        double price = m.ago(0).map.at("c");          // today's close
        if (std::abs(diff) < band * price) return 0.0; // too close to call -> flat
        return diff > 0 ? 1.0 : -1.0;                 // fast above -> long, below -> short
    };
}

int main(int argc, char **argv){
    if (argc != 2){
        std::cerr << "usage: " << argv[0] << " <file.parquet>\n";
        return 1;
    }
    std::string file = argv[1];

    std::vector<Candle> data = parquet_to_candles(file);
    if (data.empty()){
        std::cerr << "No data loaded from '" << file << "'. "
                     "Check the path, or that it has date/open/high/low/close/volume columns.\n";
        return 1;
    }
    std::cout << "Loaded " << data.size() << " bars from " << file << ".\n";

    Backtester bt(std::move(data));

    // Each strategy is one line. The scorer above is shared — zero copy-paste.
    bt.evaluate("SMA 19/3  band 3%", sma_crossover(19, 3, 0.03));
    bt.evaluate("SMA 50/10 band 2%", sma_crossover(50, 10, 0.02));
    bt.evaluate("Buy & hold        ", [](const MarketView &){ return 1.0; });

    return 0;
}
