package kz.glacier.config;

import org.springframework.batch.core.Job;
import org.springframework.batch.core.Step;
import org.springframework.batch.core.job.builder.JobBuilder;
import org.springframework.batch.core.launch.support.RunIdIncrementer;
import org.springframework.batch.core.repository.JobRepository;
import org.springframework.batch.core.step.builder.StepBuilder;
import org.springframework.batch.item.ItemProcessor;
import org.springframework.batch.item.ItemReader;
import org.springframework.batch.item.ItemWriter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.transaction.PlatformTransactionManager;

import kz.glacier.batch.BatchJobListener;
import kz.glacier.model.RasterJob;
import kz.glacier.model.SatelliteImage;

import java.util.Map;

@Configuration
public class BatchConfig {

    private final JobRepository jobRepository;
    private final PlatformTransactionManager transactionManager;
    private final BatchJobListener batchJobListener;

    public BatchConfig(JobRepository jobRepository,
                       PlatformTransactionManager transactionManager,
                       BatchJobListener batchJobListener) {
        this.jobRepository = jobRepository;
        this.transactionManager = transactionManager;
        this.batchJobListener = batchJobListener;
    }

    @Bean
    public Job satelliteImageProcessingJob(
            Step satelliteImageStep,
            Step rasterAnalysisStep) {
        return new JobBuilder("satelliteImageProcessingJob", jobRepository)
                .incrementer(new RunIdIncrementer())
                .listener(batchJobListener)
                .start(satelliteImageStep)
                .next(rasterAnalysisStep)
                .preventRestart()
                .build();
    }

    @Bean
    public Job glacierUpdateJob(Step glacierUpdateStep) {
        return new JobBuilder("glacierUpdateJob", jobRepository)
                .incrementer(new RunIdIncrementer())
                .listener(batchJobListener)
                .start(glacierUpdateStep)
                .build();
    }

    @Bean
    public Job reportGenerationJob(Step reportGenerationStep) {
        return new JobBuilder("reportGenerationJob", jobRepository)
                .incrementer(new RunIdIncrementer())
                .listener(batchJobListener)
                .start(reportGenerationStep)
                .build();
    }

    @Bean
    public Step satelliteImageStep(
            ItemReader<SatelliteImage> satelliteImageReader,
            ItemProcessor<SatelliteImage, Map<String, Object>> satelliteImageProcessor,
            ItemWriter<Map<String, Object>> satelliteImageWriter) {
        return new StepBuilder("satelliteImageStep", jobRepository)
                .<SatelliteImage, Map<String, Object>>chunk(100, transactionManager)
                .reader(satelliteImageReader)
                .processor(satelliteImageProcessor)
                .writer(satelliteImageWriter)
                .faultTolerant()
                .retryLimit(3)
                .retry(Exception.class)
                .skipLimit(10)
                .skip(Exception.class)
                .build();
    }

    @Bean
    public Step rasterAnalysisStep(
            ItemReader<RasterJob> rasterJobReader,
            ItemProcessor<RasterJob, RasterJob> rasterItemProcessor,
            ItemWriter<RasterJob> rasterItemWriter) {
        return new StepBuilder("rasterAnalysisStep", jobRepository)
                .<RasterJob, RasterJob>chunk(50, transactionManager)
                .reader(rasterJobReader)
                .processor(rasterItemProcessor)
                .writer(rasterItemWriter)
                .faultTolerant()
                .retryLimit(3)
                .retry(Exception.class)
                .skipLimit(5)
                .skip(Exception.class)
                .build();
    }

    @Bean
    public Step glacierUpdateStep(
            ItemReader<Map<String, Object>> glacierDataReader,
            ItemWriter<Map<String, Object>> glacierDataWriter) {
        return new StepBuilder("glacierUpdateStep", jobRepository)
                .<Map<String, Object>, Map<String, Object>>chunk(200, transactionManager)
                .reader(glacierDataReader)
                .writer(glacierDataWriter)
                .build();
    }

    @Bean
    public Step reportGenerationStep(
            ItemReader<RasterJob> reportDataReader,
            ItemWriter<RasterJob> reportWriter) {
        return new StepBuilder("reportGenerationStep", jobRepository)
                .<RasterJob, RasterJob>chunk(10, transactionManager)
                .reader(reportDataReader)
                .writer(reportWriter)
                .build();
    }
}
