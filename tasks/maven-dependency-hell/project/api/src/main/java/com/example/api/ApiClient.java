package com.example.api;

import com.google.common.cache.CacheBuilder;
import com.google.common.cache.CacheLoader;
import com.google.common.cache.LoadingCache;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.Map;
import java.util.HashMap;
import java.util.concurrent.TimeUnit;

public class ApiClient {
    private static final Logger logger = LoggerFactory.getLogger(ApiClient.class);
    private final LoadingCache<String, String> responseCache;
    private final ObjectMapper objectMapper;

    public ApiClient() {
        this.objectMapper = new ObjectMapper();
        this.responseCache = CacheBuilder.newBuilder()
                .maximumSize(100)
                .expireAfterWrite(5, TimeUnit.MINUTES)
                .recordStats()
                .build(new CacheLoader<String, String>() {
                    @Override
                    public String load(String key) {
                        return fetchFromApi(key);
                    }
                });
        logger.info("ApiClient initialized with cache");
    }

    private String fetchFromApi(String endpoint) {
        Map<String, Object> response = new HashMap<>();
        response.put("endpoint", endpoint);
        response.put("status", "success");
        try {
            return objectMapper.writeValueAsString(response);
        } catch (JsonProcessingException e) {
            return "{}";
        }
    }

    public String getData(String endpoint) {
        try {
            return responseCache.get(endpoint);
        } catch (Exception e) {
            return null;
        }
    }

    public String getCacheStats() {
        var stats = responseCache.stats();
        return String.format("Hits: %d, Misses: %d", stats.hitCount(), stats.missCount());
    }
}
