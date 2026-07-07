package kz.glacier.model;

import jakarta.persistence.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.Instant;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

@Entity
@Table(name = "users", indexes = {
        @Index(name = "idx_user_email", columnList = "email", unique = true),
        @Index(name = "idx_user_username", columnList = "username", unique = true)
})
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(nullable = false, length = 100, unique = true)
    private String username;

    @Column(nullable = false, length = 255, unique = true)
    private String email;

    @Column(name = "password_hash", nullable = false, length = 255)
    private String passwordHash;

    @Column(name = "first_name", length = 100)
    private String firstName;

    @Column(name = "last_name", length = 100)
    private String lastName;

    @Column(name = "organization", length = 200)
    private String organization;

    @Column(name = "department", length = 100)
    private String department;

    @ElementCollection(fetch = FetchType.EAGER)
    @CollectionTable(name = "user_roles", joinColumns = @JoinColumn(name = "user_id"))
    @Column(name = "role")
    private Set<String> roles = new HashSet<>();

    @Column(name = "enabled")
    private Boolean enabled = true;

    @Column(name = "account_non_locked")
    private Boolean accountNonLocked = true;

    @Column(name = "failed_login_attempts")
    private Integer failedLoginAttempts = 0;

    @Column(name = "last_login_at")
    private Instant lastLoginAt;

    @Column(name = "last_password_change_at")
    private Instant lastPasswordChangeAt;

    @Column(name = "password_reset_token", length = 255)
    private String passwordResetToken;

    @Column(name = "api_key", length = 255)
    private String apiKey;

    @Column(name = "notification_email")
    private Boolean notificationEmail = true;

    @Column(name = "notification_kafka")
    private Boolean notificationKafka = false;

    @Column(name = "timezone", length = 50)
    private String timezone = "Asia/Almaty";

    @Column(name = "language", length = 10)
    private String language = "ru";

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private Instant updatedAt;

    @Version
    private Long version;

    public User() {
    }

    public User(String username, String email, String passwordHash) {
        this.username = username;
        this.email = email;
        this.passwordHash = passwordHash;
        this.roles.add("ROLE_USER");
    }

    public boolean hasRole(String role) {
        return roles.contains(role);
    }

    public void addRole(String role) {
        roles.add(role);
    }

    public void removeRole(String role) {
        roles.remove(role);
    }

    public boolean isAdmin() {
        return roles.contains("ROLE_ADMIN");
    }

    public void incrementFailedLoginAttempts() {
        this.failedLoginAttempts++;
        if (this.failedLoginAttempts >= 5) {
            this.accountNonLocked = false;
        }
    }

    public void resetFailedLoginAttempts() {
        this.failedLoginAttempts = 0;
        this.accountNonLocked = true;
    }

    public void recordLogin() {
        this.lastLoginAt = Instant.now();
        resetFailedLoginAttempts();
    }

    public String getFullName() {
        if (firstName != null && lastName != null) {
            return firstName + " " + lastName;
        } else if (firstName != null) {
            return firstName;
        }
        return username;
    }

    // Getters and Setters
    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }

    public String getPasswordHash() { return passwordHash; }
    public void setPasswordHash(String passwordHash) { this.passwordHash = passwordHash; }

    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }

    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }

    public String getOrganization() { return organization; }
    public void setOrganization(String organization) { this.organization = organization; }

    public String getDepartment() { return department; }
    public void setDepartment(String department) { this.department = department; }

    public Set<String> getRoles() { return roles; }
    public void setRoles(Set<String> roles) { this.roles = roles; }

    public Boolean getEnabled() { return enabled; }
    public void setEnabled(Boolean enabled) { this.enabled = enabled; }

    public Boolean getAccountNonLocked() { return accountNonLocked; }
    public void setAccountNonLocked(Boolean accountNonLocked) { this.accountNonLocked = accountNonLocked; }

    public Integer getFailedLoginAttempts() { return failedLoginAttempts; }
    public void setFailedLoginAttempts(Integer failedLoginAttempts) { this.failedLoginAttempts = failedLoginAttempts; }

    public Instant getLastLoginAt() { return lastLoginAt; }
    public void setLastLoginAt(Instant lastLoginAt) { this.lastLoginAt = lastLoginAt; }

    public Instant getLastPasswordChangeAt() { return lastPasswordChangeAt; }
    public void setLastPasswordChangeAt(Instant lastPasswordChangeAt) { this.lastPasswordChangeAt = lastPasswordChangeAt; }

    public String getPasswordResetToken() { return passwordResetToken; }
    public void setPasswordResetToken(String passwordResetToken) { this.passwordResetToken = passwordResetToken; }

    public String getApiKey() { return apiKey; }
    public void setApiKey(String apiKey) { this.apiKey = apiKey; }

    public Boolean getNotificationEmail() { return notificationEmail; }
    public void setNotificationEmail(Boolean notificationEmail) { this.notificationEmail = notificationEmail; }

    public Boolean getNotificationKafka() { return notificationKafka; }
    public void setNotificationKafka(Boolean notificationKafka) { this.notificationKafka = notificationKafka; }

    public String getTimezone() { return timezone; }
    public void setTimezone(String timezone) { this.timezone = timezone; }

    public String getLanguage() { return language; }
    public void setLanguage(String language) { this.language = language; }

    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }

    public Long getVersion() { return version; }
    public void setVersion(Long version) { this.version = version; }

    @Override
    public String toString() {
        return "User{id=" + id + ", username='" + username + "', email='" + email + "', roles=" + roles + '}';
    }
}
