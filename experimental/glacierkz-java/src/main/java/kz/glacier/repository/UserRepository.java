package kz.glacier.repository;

import kz.glacier.model.User;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;
import java.util.UUID;

@Repository
public interface UserRepository extends JpaRepository<User, UUID> {

    Optional<User> findByUsername(String username);

    Optional<User> findByEmail(String email);

    boolean existsByUsername(String username);

    boolean existsByEmail(String email);

    @Query("SELECT u FROM User u WHERE u.enabled = true")
    Page<User> findActiveUsers(Pageable pageable);

    @Query("SELECT u FROM User u WHERE u.accountNonLocked = false")
    Page<User> findLockedUsers(Pageable pageable);

    @Query("SELECT u FROM User u WHERE u.lastLoginAt < :beforeDate OR u.lastLoginAt IS NULL")
    Page<User> findInactiveUsers(@Param("beforeDate") java.time.Instant beforeDate, Pageable pageable);

    @Query("SELECT u FROM User u WHERE u.organization = :organization")
    Page<User> findByOrganization(@Param("organization") String organization, Pageable pageable);

    @Query("SELECT u FROM User u JOIN u.roles r WHERE r = :role")
    Page<User> findByRole(@Param("role") String role, Pageable pageable);

    @Query("SELECT u FROM User u WHERE LOWER(u.username) LIKE LOWER(CONCAT('%', :query, '%')) OR LOWER(u.email) LIKE LOWER(CONCAT('%', :query, '%'))")
    Page<User> searchByUsernameOrEmail(@Param("query") String query, Pageable pageable);

    @Query("SELECT u FROM User u WHERE u.apiKey = :apiKey")
    Optional<User> findByApiKey(@Param("apiKey") String apiKey);

    @Query("SELECT COUNT(u) FROM User u WHERE u.enabled = true")
    long countActive();

    @Query("SELECT u FROM User u WHERE u.passwordResetToken IS NOT NULL AND u.passwordResetToken != ''")
    Page<User> findWithPasswordResetTokens(Pageable pageable);
}
