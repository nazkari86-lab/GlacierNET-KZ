package kz.glacier;

import io.micrometer.core.instrument.MeterRegistry;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.batch.core.configuration.annotation.EnableBatchProcessing;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;
import org.springframework.data.web.config.EnableSpringDataWebSupport;
import org.springframework.kafka.annotation.EnableKafka;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

import java.time.Instant;
import java.util.Map;

@SpringBootApplication
@EnableBatchProcessing
@EnableKafka
@EnableCaching
@EnableAsync
@EnableScheduling
@EnableJpaAuditing
@EnableSpringDataWebSupport
public class GlacierBatchApplication {

    private static final Logger log = LoggerFactory.getLogger(GlacierBatchApplication.class);

    public static void main(String[] args) {
        log.info("Starting GlacierNET-KZ Batch Processing Service at {}", Instant.now());
        SpringApplication.run(GlacierBatchApplication.class, args);
        log.info("GlacierNET-KZ service started successfully");
    }

    @Bean
    CommandLineRunner healthCheck(MeterRegistry meterRegistry) {
        return args -> {
            meterRegistry.gauge("glacier.service.startup", 1);
            log.info("Service health check passed. Active profiles: {}",
                    System.getenv().getOrDefault("SPRING_PROFILES_ACTIVE", "default"));
        };
    }

    @Bean
    public Map<String, Object> applicationMetadata() {
        return Map.of(
                "name", "GlacierNET-KZ",
                "version", "1.0.0-SNAPSHOT",
                "description", "Enterprise batch-processing service for glacier monitoring satellite data",
                "java.version", System.getProperty("java.version"),
                "startup.time", Instant.now().toString()
        );
    }
}
