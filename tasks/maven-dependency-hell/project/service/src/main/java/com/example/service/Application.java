package com.example.service;

import com.example.core.DataProcessor;
import com.example.api.ApiClient;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.Arrays;
import java.util.List;

public class Application {
    private static final Logger logger = LoggerFactory.getLogger(Application.class);

    public static void main(String[] args) {
        logger.info("Application Starting");
        try {
            DataProcessor processor = new DataProcessor();
            List<String> testData = Arrays.asList("hello", "", "world", null, "test");
            List<String> processed = processor.processStrings(testData);
            logger.info("Processed: {}", processed);

            String testJson = "{\"name\": \"test\", \"value\": 42}";
            var jsonNode = processor.parseJson(testJson);
            logger.info("Parsed JSON: {}", jsonNode.get("name").asText());

            ApiClient client = new ApiClient();
            String data = client.getData("/users");
            logger.info("API Response: {}", data);
            logger.info("Cache stats: {}", client.getCacheStats());

            logger.info("Application Completed Successfully");
            System.out.println("SUCCESS: All modules working correctly");
        } catch (NoSuchMethodError e) {
            System.err.println("FAILURE: NoSuchMethodError - " + e.getMessage());
            System.exit(1);
        } catch (Exception e) {
            System.err.println("FAILURE: " + e.getMessage());
            System.exit(1);
        }
    }
}
