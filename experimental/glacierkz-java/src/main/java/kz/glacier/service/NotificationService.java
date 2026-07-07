package kz.glacier.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.mail.SimpleMailMessage;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

@Service
@Slf4j
public class NotificationService {

    private final JavaMailSender mailSender;

    @Value("${glacier.notification.email.from:noreply@glacierkz.kz}")
    private String fromEmail;

    public NotificationService(JavaMailSender mailSender) {
        this.mailSender = mailSender;
    }

    @Async
    public CompletableFuture<Void> sendJobCompletionEmail(String to, String jobType, String glacierName, boolean success) {
        String subject = success
                ? "GlacierNET-KZ: Job Completed - " + jobType
                : "GlacierNET-KZ: Job Failed - " + jobType;

        String body = success
                ? "The %s job for glacier '%s' has completed successfully.".formatted(jobType, glacierName)
                : "The %s job for glacier '%s' has failed. Please check the dashboard for details.".formatted(jobType, glacierName);

        sendSimpleEmail(to, subject, body);
        return CompletableFuture.completedFuture(null);
    }

    @Async
    public CompletableFuture<Void> sendBatchCompletionEmail(String to, int totalJobs, int successfulJobs, int failedJobs) {
        String subject = "GlacierNET-KZ: Batch Processing Complete";
        String body = """
                Batch processing has completed.
                Total jobs: %d
                Successful: %d
                Failed: %d
                Success rate: %.1f%%
                """.formatted(totalJobs, successfulJobs, failedJobs,
                totalJobs > 0 ? (double) successfulJobs / totalJobs * 100.0 : 0.0);

        sendSimpleEmail(to, subject, body);
        return CompletableFuture.completedFuture(null);
    }

    @Async
    public CompletableFuture<Void> sendReportReadyEmail(String to, String reportType, String glacierName) {
        String subject = "GlacierNET-KZ: Report Ready - " + reportType;
        String body = "A new %s report for glacier '%s' is ready for review.".formatted(reportType, glacierName);
        sendSimpleEmail(to, subject, body);
        return CompletableFuture.completedFuture(null);
    }

    @Async
    public CompletableFuture<Void> sendAlertEmail(String to, String alertType, String message) {
        String subject = "GlacierNET-KZ Alert: " + alertType;
        sendSimpleEmail(to, subject, message);
        return CompletableFuture.completedFuture(null);
    }

    @Async
    public CompletableFuture<Void> sendHtmlEmail(String to, String subject, String htmlContent) {
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(fromEmail);
            helper.setTo(to);
            helper.setSubject(subject);
            helper.setText(htmlContent, true);
            mailSender.send(message);
            log.info("Sent HTML email to {}: {}", to, subject);
        } catch (MessagingException e) {
            log.error("Failed to send HTML email to {}: {}", to, e.getMessage());
        }
        return CompletableFuture.completedFuture(null);
    }

    public void sendSimpleEmail(String to, String subject, String text) {
        try {
            SimpleMailMessage message = new SimpleMailMessage();
            message.setFrom(fromEmail);
            message.setTo(to);
            message.setSubject(subject);
            message.setText(text);
            mailSender.send(message);
            log.info("Sent email to {}: {}", to, subject);
        } catch (Exception e) {
            log.error("Failed to send email to {}: {}", to, e.getMessage());
        }
    }

    @Async
    public CompletableFuture<Void> sendDailyDigest(String to, Map<String, Object> stats) {
        String subject = "GlacierNET-KZ: Daily Digest";
        String body = """
                Daily System Digest
                ====================
                Active Glaciers: %s
                Completed Jobs: %s
                Failed Jobs: %s
                Pending Jobs: %s
                Total Reports: %s
                Active Users: %s
                """.formatted(
                stats.getOrDefault("glaciers", 0),
                stats.getOrDefault("completedJobs", 0),
                stats.getOrDefault("failedJobs", 0),
                stats.getOrDefault("pendingJobs", 0),
                stats.getOrDefault("reports", 0),
                stats.getOrDefault("users", 0)
        );
        sendSimpleEmail(to, subject, body);
        return CompletableFuture.completedFuture(null);
    }
}
