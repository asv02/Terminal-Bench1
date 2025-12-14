package com.example.core;

import com.google.common.base.Strings;
import com.google.common.collect.ImmutableList;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.List;

public class DataProcessor {
    private static final Logger logger = LoggerFactory.getLogger(DataProcessor.class);
    private final ObjectMapper objectMapper;

    public DataProcessor() {
        this.objectMapper = new ObjectMapper();
        logger.info("DataProcessor initialized");
    }

    public List<String> processStrings(List<String> input) {
        if (input == null) return ImmutableList.of();
        ImmutableList.Builder<String> builder = ImmutableList.builder();
        for (String s : input) {
            if (!Strings.isNullOrEmpty(s)) {
                builder.add(s.trim());
            }
        }
        return builder.build();
    }

    public JsonNode parseJson(String json) throws Exception {
        return objectMapper.readTree(json);
    }

    public String toJson(Object obj) throws Exception {
        return objectMapper.writeValueAsString(obj);
    }
}
