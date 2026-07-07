package kz.glacier.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import kz.glacier.dto.PageResponse;
import kz.glacier.model.User;
import kz.glacier.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
@Slf4j
@Tag(name = "User", description = "User management operations")
public class UserController {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @GetMapping
    @Operation(summary = "List users with pagination")
    public ResponseEntity<PageResponse<Map<String, Object>>> listUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<User> users = userRepository.findActiveUsers(PageRequest.of(page, size, Sort.by("username")));
        Page<Map<String, Object>> mapped = users.map(u -> Map.of(
                "id", u.getId(), "username", u.getUsername(), "email", u.getEmail(),
                "enabled", u.isEnabled(), "roles", u.getRoles(), "organization", u.getOrganization() != null ? u.getOrganization() : ""
        ));
        return ResponseEntity.ok(PageResponse.of(mapped));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Get user by ID")
    public ResponseEntity<Map<String, Object>> getUser(@PathVariable UUID id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
        return ResponseEntity.ok(Map.of(
                "id", user.getId(), "username", user.getUsername(), "email", user.getEmail(),
                "enabled", user.isEnabled(), "accountNonLocked", user.isAccountNonLocked(),
                "roles", user.getRoles(), "organization", user.getOrganization() != null ? user.getOrganization() : "",
                "lastLoginAt", user.getLastLoginAt() != null ? user.getLastLoginAt().toString() : "never"
        ));
    }

    @GetMapping("/search")
    @Operation(summary = "Search users by username or email")
    public ResponseEntity<PageResponse<Map<String, Object>>> searchUsers(
            @RequestParam String q,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<User> users = userRepository.searchByUsernameOrEmail(q, PageRequest.of(page, size));
        Page<Map<String, Object>> mapped = users.map(u -> Map.of(
                "id", u.getId(), "username", u.getUsername(), "email", u.getEmail(),
                "enabled", u.isEnabled(), "roles", u.getRoles()
        ));
        return ResponseEntity.ok(PageResponse.of(mapped));
    }

    @GetMapping("/locked")
    @Operation(summary = "List locked users")
    public ResponseEntity<PageResponse<Map<String, Object>>> lockedUsers(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<User> users = userRepository.findLockedUsers(PageRequest.of(page, size));
        Page<Map<String, Object>> mapped = users.map(u -> Map.of(
                "id", u.getId(), "username", u.getUsername(), "email", u.getEmail()
        ));
        return ResponseEntity.ok(PageResponse.of(mapped));
    }

    @PostMapping
    @Operation(summary = "Create a new user")
    public ResponseEntity<Map<String, Object>> createUser(@RequestBody Map<String, Object> body) {
        String username = (String) body.get("username");
        String email = (String) body.get("email");
        String password = (String) body.get("password");
        String organization = (String) body.get("organization");

        if (username == null || email == null || password == null) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "username, email, and password are required");
        }
        if (userRepository.existsByUsername(username)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Username already exists");
        }
        if (userRepository.existsByEmail(email)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Email already exists");
        }

        User user = new User();
        user.setUsername(username);
        user.setEmail(email);
        user.setPasswordHash(passwordEncoder.encode(password));
        user.setOrganization(organization);
        user.setEnabled(true);
        user.setAccountNonLocked(true);
        user.setRoles(new java.util.HashSet<>(java.util.List.of("ROLE_USER")));
        user.setLastLoginAt(null);

        User saved = userRepository.save(user);
        log.info("Created user: {} ({})", saved.getUsername(), saved.getId());
        return ResponseEntity.status(HttpStatus.CREATED).body(Map.of(
                "id", saved.getId(), "username", saved.getUsername(), "email", saved.getEmail(),
                "roles", saved.getRoles()
        ));
    }

    @PutMapping("/{id}")
    @Operation(summary = "Update user details")
    public ResponseEntity<Map<String, Object>> updateUser(@PathVariable UUID id, @RequestBody Map<String, Object> body) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));

        if (body.containsKey("email")) user.setEmail((String) body.get("email"));
        if (body.containsKey("organization")) user.setOrganization((String) body.get("organization"));
        if (body.containsKey("enabled")) user.setEnabled((Boolean) body.get("enabled"));
        if (body.containsKey("password") && body.get("password") != null) {
            user.setPasswordHash(passwordEncoder.encode((String) body.get("password")));
        }

        User saved = userRepository.save(user);
        log.info("Updated user: {} ({})", saved.getUsername(), id);
        return ResponseEntity.ok(Map.of("id", saved.getId(), "username", saved.getUsername(), "email", saved.getEmail()));
    }

    @PostMapping("/{id}/lock")
    @Operation(summary = "Lock a user account")
    public ResponseEntity<Void> lockUser(@PathVariable UUID id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
        user.setAccountNonLocked(false);
        userRepository.save(user);
        log.info("Locked user: {} ({})", user.getUsername(), id);
        return ResponseEntity.noContent().build();
    }

    @PostMapping("/{id}/unlock")
    @Operation(summary = "Unlock a user account")
    public ResponseEntity<Void> unlockUser(@PathVariable UUID id) {
        User user = userRepository.findById(id)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User not found"));
        user.setAccountNonLocked(true);
        userRepository.save(user);
        log.info("Unlocked user: {} ({})", user.getUsername(), id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/statistics")
    @Operation(summary = "Get user statistics")
    public ResponseEntity<Map<String, Object>> statistics() {
        Map<String, Object> stats = new java.util.HashMap<>();
        stats.put("activeUsers", userRepository.countActive());
        return ResponseEntity.ok(stats);
    }
}
