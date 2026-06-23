#pragma once
#include <algorithm>
#include <variant>
#include <arrow/api.h>
#include <arrow/io/api.h>
#include <memory>
#include <parquet/arrow/reader.h>
#include <string>
#include <fstream>
#include <filesystem>
#include <iostream>

struct Candle{
    std::variant<int64_t, std::string> date;
    double high, low;
    double open, close, adj_close = -1;
    double volume;
    std::unordered_map<std::string, double> map = {{"o", open}, {"c", close}, {"v", volume}, {"h", high}, {"l", low}};

    std::string label;
    Candle(std::variant<int64_t, std::string> d, double o, double c, double h, double l, double v, std::string lab)
      : date(d), high(h), low(l), open(o), close(c), volume(v), label(lab) {
      if (adj_close > 0){
        map["ac"] = adj_close;
      }
  }
};

void print_columns(const std::string& file_name){
      auto data = arrow::io::ReadableFile::Open(file_name);
      if (!data.ok()){ 
        std::cerr << data.status().message() << std::endl; return; 
    }
      auto reader_result = parquet::arrow::OpenFile(data.ValueOrDie(), arrow::default_memory_pool());
      if (!reader_result.ok()){ 
        std::cerr << reader_result.status().message() << std::endl; 
        return; 
    }
      auto reader = std::move(reader_result.ValueOrDie());
      std::shared_ptr<arrow::Schema> schema;
      auto schema_status = reader->GetSchema(&schema);
      if (!schema_status.ok()){ std::cerr << schema_status.message() << std::endl; return; }
      for (const auto& field : schema->fields()){
          std::cout << field->name() << " (" << field->type()->ToString() << ")" << std::endl;
      }
  }

static double extract_double(const std::shared_ptr<arrow::Array>& chunk, int i){
    switch (chunk->type_id()){
        case arrow::Type::DOUBLE: return std::static_pointer_cast<arrow::DoubleArray>(chunk)->Value(i);
        case arrow::Type::FLOAT:  return (double)std::static_pointer_cast<arrow::FloatArray>(chunk)->Value(i);
        case arrow::Type::INT64:  return (double)std::static_pointer_cast<arrow::Int64Array>(chunk)->Value(i);
        case arrow::Type::INT32:  return (double)std::static_pointer_cast<arrow::Int32Array>(chunk)->Value(i);
        default: return 0.0;
    }
}

static std::variant<int64_t, std::string> extract_date(const std::shared_ptr<arrow::Array>& chunk, int i){
    switch (chunk->type_id()){
        case arrow::Type::DATE32:
        case arrow::Type::DATE64:
        case arrow::Type::TIMESTAMP:
        case arrow::Type::INT64: return std::static_pointer_cast<arrow::Int64Array>(chunk)->Value(i);
        case arrow::Type::INT32: return (int64_t)std::static_pointer_cast<arrow::Int32Array>(chunk)->Value(i);
        case arrow::Type::STRING: return std::static_pointer_cast<arrow::StringArray>(chunk)->GetString(i);
        default: return (int64_t)0;
    }
}

static std::string extract_label(const std::shared_ptr<arrow::Array>& chunk, int i){
    switch (chunk->type_id()){
        case arrow::Type::STRING:
        case arrow::Type::LARGE_STRING: return std::static_pointer_cast<arrow::StringArray>(chunk)->GetString(i);
        case arrow::Type::DICTIONARY:   return std::static_pointer_cast<arrow::StringArray>(
            std::static_pointer_cast<arrow::DictionaryArray>(chunk)->dictionary()
        )->GetString(std::static_pointer_cast<arrow::DictionaryArray>(chunk)->GetValueIndex(i));
        default: return "";
    }
}

std::vector<Candle> parquet_to_candles(const std::string& file_name){
    auto data = arrow::io::ReadableFile::Open(file_name);
    if (!data.ok()){ std::cerr << data.status().message() << std::endl; return {}; }
    auto reader_result = parquet::arrow::OpenFile(data.ValueOrDie(), arrow::default_memory_pool());
    if (!reader_result.ok()){ std::cerr << reader_result.status().message() << std::endl; return {}; }
    auto reader = std::move(reader_result.ValueOrDie());
    auto table_result = reader->ReadTable();
    if (!table_result.ok()){ std::cerr << table_result.status().message() << std::endl; return {}; }
    auto table = table_result.ValueOrDie();

    auto col_date     = table->GetColumnByName("date");
    auto col_open     = table->GetColumnByName("open");
    auto col_high     = table->GetColumnByName("high");
    auto col_low      = table->GetColumnByName("low");
    auto col_close    = table->GetColumnByName("close");
    auto col_adjclose = table->GetColumnByName("adj_close");
    auto col_volume   = table->GetColumnByName("volume");
    auto col_label    = table->GetColumnByName("label");

    if (!col_date || !col_open || !col_high || !col_low || !col_close || !col_volume){
        std::cerr << "Missing required columns\n"; return {};
    }

    std::vector<Candle> candles;
    candles.reserve(table->num_rows());

    int64_t row = 0;
    for (int c = 0; c < col_open->num_chunks(); ++c){
        int len = col_open->chunk(c)->length();
        for (int i = 0; i < len; ++i, ++row){
            auto date  = extract_date(col_date->chunk(c), i);
            double o   = extract_double(col_open->chunk(c), i);
            double h   = extract_double(col_high->chunk(c), i);
            double l   = extract_double(col_low->chunk(c), i);
            double cl  = extract_double(col_close->chunk(c), i);
            double v   = extract_double(col_volume->chunk(c), i);
            double ac  = col_adjclose ? extract_double(col_adjclose->chunk(c), i) : -1.0;
            std::string lab = col_label ? extract_label(col_label->chunk(c), i) : "";
            Candle candle(date, o, cl, h, l, v, lab);
            candle.adj_close = ac;
            if (ac > 0) candle.map["ac"] = ac;
            candles.push_back(std::move(candle));
        }
    }
    return candles;
}

std::vector<Candle> parseCSV(const std::string& file_name){
    std::vector<Candle> timeline;
    std::ifstream file(file_name);
    if (!file){ return {}; }

    std::string line;
    while (getline(file, line)){
        if (line.empty()) continue;
        std::istringstream iss(line);
        // columns: date, open, high, low, close, adj_close, volume, label
        std::string cells[8];
        for (int i = 0; i < 8; i++){
            std::getline(iss, cells[i], ',');
        }
        // constructor order is (date, open, close, high, low, volume, label)
        Candle P(cells[0],
                    std::stod(cells[1]),   // open
                    std::stod(cells[4]),   // close
                    std::stod(cells[2]),   // high
                    std::stod(cells[3]),   // low
                    std::stod(cells[6]),   // volume
                    cells[7]);             // label
        timeline.push_back(P);
    }
    return timeline;
}




